"""B2 m1+m2: signature library + paste engine + synthetic probe.

B2 bet (pre-registered in .auto/ideas.md): pasting baseline-subtracted
mark signatures into real pre-span aggregate backgrounds (amplitude /
time-stretch / overlap variation) builds synthetic supervision windows
that carry known-truth device spans in the target house's own
background. Eval-free by construction: signatures come from the K=5
calibration marks (the model's legal input), backgrounds from the
PRE-split aggregate span, and no post-split sample is read.

This module is a diagnostic instrument (H02-style simulation family),
not a model path. The probe answers: do the frozen rules recover a
known draw placed in a quiet real background at plausible variation?
Recovery failures localize the weak gate; fixes must stay derivable
from marks + synthetic evidence only.

Scenarios (all on 4 h quiet windows, quiet = each of the four
probe devices' real pre-span ON fraction < 1%):
- iso: per-device draws at scale U(0.85, 1.20) - inside the admission
  band REL_AMP = 0.20 - kettle 3/window, mw 2/window, programs 1/window
  with stretch U(0.85, 1.20).
- mix_burst: kettle x2 + mw x1 interleaved (burst interference).
- mix_prog: wm x1 + dw x1 (program cross-naming).
Scoring: predicted ON (pred[dev] > house_1 THR) vs pasted span minus
the 60 s mark roll; per-scenario pooled precision/recall/F1 plus the
cross-fire matrix (other devices' predicted ON inside the pasted span).

Usage: uv run python3 .auto/b2_synth.py [--seeds 2026,1,2]
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.auto'))
sys.path.insert(0, str(ROOT / 'src'))

import bench_v3 as B  # noqa: E402
import bench as v1  # noqa: E402
import bench_v2 as v2  # noqa: E402

PROBE_DEVICES = ('kettle', 'microwave', 'washing_machine', 'dishwasher')
WIN_N = 3600          # 6 h at 6 s
EDGE = 150            # keep pastes away from window edges
PROG_EDGE = 780       # programs pasted >= 2 h in: the dw run detector's
                      # trailing p10 baseline (240 x 30 s grid samples)
                      # needs DW_BASE_MIN trusted samples before a paste
MIN_GAP = 30          # min samples between pastes (3 min)
QUIET_FRAC = 0.01
SCALE_LO, SCALE_HI = 0.85, 1.20
STRETCH_LO, STRETCH_HI = 0.85, 1.20


def load_ctx(seed: int):
    pre = v1.load_house(v1.TARGET_HOUSE, None, B.SPLIT_US, 'pre')
    calib = B.build_calibration_v3(pre, seed)
    filled = (pd.Series(pre['mains']).ffill(limit=v1.FFILL_LIMIT)
              .fillna(0.0).to_numpy(dtype='float32'))
    meta = {'devices': list(B.DEVICES), 'thresholds': dict(B.THR),
            'device_class': dict(B.DEVICE_CLASS), 'cadence_s': 6,
            'cadence_us': v1.CADENCE_US, 'k_calib': v2.K_CALIB,
            'tau_onset_s': dict(v2.TAU_ONSET_S), 'dwell_s': dict(v2.DWELL_S),
            'merge_s': dict(v2.MERGE_S), 'duration_band': B.DURATION_BAND,
            'press_jitter_s': v2.PRESS_JITTER_S,
            'pre_roll_s': v2.PRE_ROLL_S, 'split_us': B.SPLIT_US,
            'eval_span_us': [B.SPLIT_US, B.SPLIT_US], 'seeds': list(B.SEEDS),
            'bench': 'v3', 'confirm': False}
    ctx = {'meta': meta, 'calib': calib,
           'pre': {'ts_us': pre['ts_us'], 'mains': filled},
           'eval': {'ts_us': pre['ts_us'], 'mains': filled},
           'pretrain': B.make_pretrain_ctx()}
    return ctx, pre, filled


def signatures(ctx: dict) -> dict:
    """m1: baseline-subtracted mark signatures per device.

    Validation: a usable mark must hold a pre-ON baseline stretch -
    calibration clips the 60 s roll at the pre-span edge, and a
    segment that starts at (or inside) the ON plateau would subtract
    the plateau itself, pasting a negative dip instead of a draw
    (seed-2026 microwave mark 2 was exactly this). ON start = first
    sample over 0.3 x p90; baseline = median of the pre-ON samples
    that sit below 0.3 x p90; fewer than 3 such samples -> drop the
    mark. Trim the head to 10 samples before ON when a longer roll
    exists, so every signature carries the same window convention."""
    out = {}
    for dev in PROBE_DEVICES:
        segs = []
        for seg in ctx['calib'][dev]['mains_seg']:
            s = np.asarray(seg, dtype='float32')
            if len(s) < 12:
                continue
            p90 = float(np.percentile(s, 90))
            if p90 <= 10.0:
                continue
            above = np.flatnonzero(s > 0.3 * p90)
            on0, on1 = int(above[0]), int(above[-1]) + 1
            pre = s[:on0]
            pre = pre[pre <= 0.3 * p90]
            if len(pre) < 3:
                continue
            base = float(np.median(pre))
            sg = np.nan_to_num(s - base, nan=0.0).astype('float32')
            # keep the full validated segment; scoring uses the sig's
            # own ON extent, so the roll convention is irrelevant here
            segs.append({'sg': sg, 'on0': on0, 'on1': on1})
        out[dev] = segs
    return out


def quiet_windows(pre: dict, filled: np.ndarray, rng, want: int):
    """Starts of 4 h windows where every probe device's real pre-span
    ON fraction is under 1% (fridge exempt - continuous background)."""
    on = {d: (np.nan_to_num(pre['devices'][d]) > B.THR[d])
          for d in PROBE_DEVICES}
    n = len(filled)
    starts = []
    order = rng.permutation(max(1, n - WIN_N - 1))
    for s0 in order.tolist():
        if len(starts) >= want:
            break
        sl = slice(s0, s0 + WIN_N)
        if np.count_nonzero(filled[sl] == 0) > 0.15 * WIN_N:
            continue  # gappy stretch
        if any(on[d][sl].mean() >= QUIET_FRAC for d in PROBE_DEVICES):
            continue
        starts.append(int(s0))
    return starts


def _place(rng, occupied, n, hi, lo=None):
    """Random non-overlapping position; None if the window is full."""
    lo = EDGE if lo is None else lo
    for _ in range(50):
        pos = int(rng.integers(lo, max(lo + 1, hi - n)))
        if all(pos + n + MIN_GAP <= a or pos >= b + MIN_GAP
               for a, b in occupied):
            return pos
    return None


def _runs(on: np.ndarray):
    d = np.diff(np.concatenate([[0], on.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(),
                    np.flatnonzero(d == -1).tolist()))


def paste_scenario(sig_lib: dict, dev_plan: list, bg: np.ndarray, rng,
                   trace=None):
    """dev_plan: [(dev, n_draws, stretch: bool), ...] -> synthetic
    window + truth spans {dev: [(a, b), ...]}.

    Truth follows the bench GT semantics exactly: ON = raw watts above
    the house_1 threshold, restricted to each device's pasted ranges
    (the only contributor there - quiet-window backgrounds stay under
    every probe THR). A sub-threshold chunk (mw magnetron dip at low
    scale) is correctly GT-OFF."""
    syn = bg.copy()
    occupied = {d: [] for d in PROBE_DEVICES}
    occ_spans = []  # flat span list for placement collision checks
    trace = [] if trace is None else trace
    for dev, k, stretch in dev_plan:
        for _ in range(k):
            sigs = sig_lib[dev]
            item = sigs[int(rng.integers(0, len(sigs)))]
            sig = item['sg']
            scale = float(rng.uniform(SCALE_LO, SCALE_HI))
            st = float(rng.uniform(STRETCH_LO, STRETCH_HI)) if stretch else 1.0
            n = max(2, int(round(len(sig) * st)))
            lo = PROG_EDGE if stretch else EDGE
            pos = _place(rng, occ_spans, n, WIN_N - EDGE, lo)
            if pos is None:
                continue
            x = np.linspace(0.0, 1.0, len(sig))
            sg = (np.interp(np.linspace(0.0, 1.0, n), x, sig)
                  .astype('float32') * scale)
            syn[pos:pos + n] += sg
            occupied[dev].append((pos, pos + n))
            occ_spans.append((pos, pos + n))
            trace.append({'dev': dev, 'pos': pos, 'n': n,
                          'sig_i': next(i for i, it in
                                        enumerate(sig_lib[dev])
                                        if it is item),
                          'scale': round(scale, 3)})
    truth = {d: [] for d in PROBE_DEVICES}
    for d in PROBE_DEVICES:
        if not occupied[d]:
            continue
        allow = np.zeros(WIN_N, dtype=bool)
        for a, b in occupied[d]:
            allow[a:b] = True
        m = (syn > B.THR[d]) & allow
        truth[d] = [(a, b) for a, b in _runs(m)]
    return syn, truth


def score(pred: dict, truth: dict) -> dict:
    rows = {}
    for dev, spans in truth.items():
        tmask = np.zeros(WIN_N, dtype=bool)
        for a, b in spans:
            tmask[a:b] = True
        pmask = np.asarray(pred[dev]) > B.THR[dev]
        tp = int(np.count_nonzero(pmask & tmask))
        p = tp / max(1, int(np.count_nonzero(pmask)))
        r = tp / max(1, int(np.count_nonzero(tmask)))
        f1 = 2 * p * r / max(1e-9, p + r)
        cross = {}
        for e in PROBE_DEVICES:
            if e == dev or not spans:
                continue
            pe = np.asarray(pred[e])
            cross[e] = round(float(np.mean([(pe[a:b] > B.THR[e]).mean()
                                            for a, b in spans])), 3)
        rows[dev] = {'P': p, 'R': r, 'F1': f1, 'n_spans': len(spans),
                     'cross': cross}
    return rows


def run(seed: int) -> None:
    t0 = time.time()
    ctx, pre, filled = load_ctx(seed)
    spec = importlib.util.spec_from_file_location('ar_model', B.MODEL_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['ar_model'] = mod
    spec.loader.exec_module(mod)
    predict = mod.build_and_train(ctx)
    sig_lib = signatures(ctx)
    print('B2 probe seed %d: signatures %s' % (
        seed, ' '.join('%s=%d' % (d, len(sig_lib[d])) for d in PROBE_DEVICES)))

    rng = np.random.default_rng(1000 + seed)
    starts = quiet_windows(pre, filled, rng, 60)
    print('  quiet 6h windows found: %d' % len(starts))
    if len(starts) < 27:
        print('  NOT ENOUGH QUIET WINDOWS - aborting scenarios')
        return

    scen = {
        'iso_kettle': [(s, [('kettle', 3, False)]) for s in starts[0:5]],
        'iso_microwave': [(s, [('microwave', 2, False)])
                          for s in starts[5:10]],
        'iso_wm': [(s, [('washing_machine', 1, True)]) for s in starts[10:15]],
        'iso_dw': [(s, [('dishwasher', 1, True)]) for s in starts[15:20]],
        'mix_burst': [(s, [('kettle', 2, False), ('microwave', 1, False)])
                      for s in starts[20:24]],
        'mix_prog': [(s, [('washing_machine', 1, True),
                          ('dishwasher', 1, True)]) for s in starts[24:27]],
    }
    dbg = os.environ.get('B2_DEBUG')
    if dbg:
        print('  DBG starts: %s' % (starts,))
    for name, wins in scen.items():
        agg = {d: {'tp': 0, 'p': 0, 't': 0} for d in PROBE_DEVICES}
        for s0, plan in wins:
            bg = filled[s0:s0 + WIN_N].copy()
            syn, truth = paste_scenario(sig_lib, plan, bg, rng)
            pred = predict(syn)
            for d in PROBE_DEVICES:
                pmask = np.asarray(pred[d]) > B.THR[d]
                tmask = np.zeros(WIN_N, dtype=bool)
                for a, b in truth[d]:
                    tmask[a:b] = True
                agg[d]['tp'] += int(np.count_nonzero(pmask & tmask))
                agg[d]['p'] += int(np.count_nonzero(pmask))
                agg[d]['t'] += int(np.count_nonzero(tmask))
        line = '  %s: ' % name
        for d in PROBE_DEVICES:
            a = agg[d]
            if a['t'] == 0 and a['p'] == 0:
                continue
            p = a['tp'] / max(1, a['p'])
            r = a['tp'] / max(1, a['t'])
            f1 = 2 * p * r / max(1e-9, p + r)
            line += '%s P%.2f/R%.2f/F1 %.2f  ' % (d, p, r, f1)
        print(line)
        if name.startswith('mix'):
            cross = {d: [] for d in PROBE_DEVICES}
            for s0, plan in wins:
                bg = filled[s0:s0 + WIN_N].copy()
                syn, truth = paste_scenario(sig_lib, plan, bg, rng)
                pred = predict(syn)
                for d, spans in truth.items():
                    for e in PROBE_DEVICES:
                        if e == d or not spans:
                            continue
                        pe = np.asarray(pred[e])
                        fr = float(np.mean([(pe[a:b] > B.THR[e]).mean()
                                            for a, b in spans]))
                        if dbg:
                            print('  DBG xf %s win[%s] dev=%s spans=%s %s->%.2f'
                                  % (name, s0, d, spans, e, fr))
                        if fr > 0.02:
                            cross[d].append('%s->%.2f' % (e, fr))
            for d, v in cross.items():
                if v:
                    print('    cross-fire on %s spans: %s' % (d, v))
    print('  probe elapsed %.0fs' % (time.time() - t0))


def main() -> None:
    argv = sys.argv[1:]
    seeds = [2026]
    if '--seeds' in argv:
        seeds = [int(x) for x in argv[argv.index('--seeds') + 1].split(',')]
    for s in seeds:
        run(s)


if __name__ == '__main__':
    main()
