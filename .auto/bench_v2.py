"""FROZEN-v2 benchmark for the WattWiser NILM autoresearch loop.

Owner-approved protocol change (benchmark-integrity review, this session):
the v1 episode metric was verified unlearnable - a perfect-but-smoothed
predictor scores fridge 0.043 / dishwasher 0.006 because ~68k single-sample
recording gaps shred the GT into p50=30 s fragments (ceiling test,
.scratch/ceiling_test.py). v2 scores WHOLE CYCLES.

Protocol v2 (all constants frozen here; do not tune):
- Target house_1, eval span 90 days after SPLIT_US.
- Events = cycles: ON mask at the v1 thresholds, gaps <= MERGE_S[dev]
  bridged, merged spans kept if >= DWELL_S[dev]. Rules are the pre-split
  data/gold_annot/ukdale/house_1/device_profile.csv per-class rules
  (program 600/600 s, burst 30 s dwell / 60 s merge, fridge 30 s / 12 s).
- Matching: one-to-one, onset tolerance TAU_ONSET_S[dev] (burst 60 s,
  duty 120 s, program 600 s), duration band (1/3, 3.0) relative to the
  GT cycle duration.
- Primary metric: mean_device_f1 (cycle level); guardrail min_device_f1.
- Sanity gate: a median-3-smoothed perfect predictor must score >= 0.9
  per device under this scorer, else the benchmark reports invalid.
- Calibration per docs/PROBLEM_STATEMENTS.md FAQ Q1: aggregate-only.
  K_CALIB=5 whole-cycle intervals per device taken from the PRE span
  (simulated user button marks; boundaries jittered +-PRESS_JITTER_S
  with CALIB_SEED); the model receives ONLY aggregate slices over the
  marks - never a submeter trace. Fridge gets a passive 3 h aggregate
  window (it cannot be button-calibrated).
- ctx.pre (owner-approved review backlog, "mine a year of unlabeled
  events"): the model additionally receives the PRE-span AGGREGATE
  mains (ts_us + mains, same fill treatment as eval). Device channels
  are never passed for any span; the PRE-span aggregate is the product's
  own unlabeled signal, so mining it is FAQ-Q1-legal.
Changing this file or measure_v2.sh must be stopped and documented, as
with v1. Iterations change src/experiments/04_autoresearch/model.py.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.auto'))
sys.path.insert(0, str(ROOT / 'src'))

import bench as v1  # noqa: E402  (episode machinery + data loading reused)
from wattwiser.experiments import evaluation as ev  # noqa: E402

TARGET_HOUSE = "house_1"
DEVICES = v1.DEVICES
THR = dict(v1.THR)
SPLIT_US = v1.SPLIT_US
CADENCE_US = v1.CADENCE_US
CADENCE = v1.CADENCE
FFILL_LIMIT = v1.FFILL_LIMIT
MODEL_PATH = ROOT / 'src' / 'experiments' / '04_autoresearch' / 'model.py'
OUT_PATH = ROOT / '.auto' / 'last_bench.json'

# ------------------------------------------------------------ frozen protocol
EVAL_DAYS = 90                  # v2 scores the full reserved span
K_CALIB = 5
CALIB_SEED = 2026
PRESS_JITTER_S = 30             # simulated button-press error (H10 regime)
PRE_ROLL_S = 60.0               # mark starts before switch-on (session
# records the aggregate first; exceeds the press jitter so a clean
# pre-onset baseline exists inside every mark)
PASSIVE_FRIDGE_H = 3            # fridge cannot be button-calibrated (FAQ Q12)
DURATION_BAND = (1.0 / 3.0, 3.0)
DEVICE_CLASS = {'kettle': 'burst', 'microwave': 'burst', 'fridge': 'duty',
                'washing_machine': 'program', 'dishwasher': 'program'}
MERGE_S = {'kettle': 60.0, 'microwave': 60.0, 'fridge': 12.0,
           'washing_machine': 600.0, 'dishwasher': 600.0}
DWELL_S = {'kettle': 30.0, 'microwave': 30.0, 'fridge': 30.0,
           'washing_machine': 600.0, 'dishwasher': 600.0}
TAU_ONSET_S = {'kettle': 60.0, 'microwave': 60.0, 'fridge': 120.0,
               'washing_machine': 600.0, 'dishwasher': 600.0}
SANITY_MIN = 0.9


def cycles_from_mask(on: np.ndarray, ts_us: np.ndarray, dev: str):
    """Merge gaps <= MERGE_S, keep merged spans >= DWELL_S."""
    on = on.astype(bool).copy()
    merge_n = int(round(MERGE_S[dev] * 1e6 / CADENCE_US))
    for a, b in v1.runs_of(~on):
        if 0 < a and b < len(on) and (b - a) <= merge_n:
            on[a:b] = True
    eps = v1.episodes_from_mask(on, ts_us)
    if not len(eps):
        return eps
    keep = (eps['t_off_us'] - eps['t_on_us']) >= DWELL_S[dev] * 1e6
    return eps[keep].reset_index(drop=True)


def score_cycles(pred_eps, gt_eps, dev: str) -> dict:
    return ev.score_episodes(pred_eps, gt_eps,
                             TAU_ONSET_S[dev] * 1e6, DURATION_BAND)


def build_calibration_v2(pre: dict) -> dict:
    """Aggregate-only marks (FAQ Q1): the PRE-span device channel is used
    ONLY to place simulated button marks around whole cycles; the model
    receives jittered aggregate slices, never the submeter trace."""
    rng = np.random.default_rng(CALIB_SEED)
    feed = (pd.Series(pre['mains']).ffill(limit=FFILL_LIMIT).fillna(0.0)
            .to_numpy(dtype='float32'))
    n = len(feed)
    ts = pre['ts_us']
    jn = int(round(PRESS_JITTER_S * 1e6 / CADENCE_US))
    calib = {}
    for dev in DEVICES:
        if dev == 'fridge':
            lo = int(rng.integers(0, n - PASSIVE_FRIDGE_H * 3600 // 6))
            hi = lo + PASSIVE_FRIDGE_H * 3600 // 6
            calib[dev] = {'marks_us': np.empty((0, 2), dtype=np.int64),
                          'mains_seg': [feed[lo:hi]], 'passive': True}
            print(f'   calib {dev}: passive {PASSIVE_FRIDGE_H} h window')
            continue
        w = pre['devices'][dev]
        valid = ~np.isnan(w)
        cyc = cycles_from_mask((np.nan_to_num(w) > THR[dev]) & valid,
                               pre['ts_us'], dev)
        if not len(cyc):
            raise SystemExit('no pre-span cycles for ' + dev)
        take = min(K_CALIB, len(cyc))
        idx = sorted(rng.permutation(len(cyc))[:take].tolist())
        marks, segs = [], []
        roll_us = PRE_ROLL_S * 1_000_000
        for i in idx:
            s_us, e_us = int(cyc['t_on_us'].iloc[i]), int(cyc['t_off_us'].iloc[i])
            lo_us = s_us - roll_us + int(rng.integers(-jn, jn + 1)) * CADENCE_US
            hi_us = e_us + roll_us + int(rng.integers(-jn, jn + 1)) * CADENCE_US
            lo = int(np.searchsorted(ts, lo_us))
            hi = int(np.searchsorted(ts, hi_us))
            lo, hi = max(lo, 0), min(hi, n)
            if hi - lo < 2:
                continue
            seg = feed[lo:hi]
            if np.count_nonzero(seg == 0) > 0.9 * len(seg):
                print(f'   calib {dev}: dropped 1 mark (recording gap)')
                continue
            marks.append((ts[lo], ts[min(hi, n - 1)]))
            segs.append(seg)
        calib[dev] = {'marks_us': np.asarray(marks, dtype=np.int64),
                      'mains_seg': segs, 'passive': False}
        print(f'   calib {dev}: {len(segs)} marks of {len(cyc)} pre-span'
              f' cycles, jitter +- {PRESS_JITTER_S} s')
    return calib


def run_score_v2(evh: dict, predict, t_start: float, config: dict,
                 prefix: str = '') -> dict:
    ts_eval = evh['ts_us']
    mains_raw = evh['mains']
    filled = (pd.Series(mains_raw).ffill(limit=FFILL_LIMIT).fillna(0.0)
              .to_numpy(dtype='float32'))
    print('predicting eval span ...' if not prefix else
          'predicting expanded eval span ...')
    t_pred = time.time()
    pred = predict(filled)
    print(f'   prediction done in {time.time() - t_pred:.1f}s')

    per = {}
    agg_energy_wh = float(np.nansum(mains_raw.astype('float64'))) * 6.0 / 3600.0
    pred_energy_wh = 0.0
    gt_energy_wh = 0.0
    for dev in DEVICES:
        gt_w = evh['devices'][dev]
        valid = ~np.isnan(gt_w)
        gt_cyc = cycles_from_mask((gt_w > THR[dev]) & valid, ts_eval, dev)
        pe_cyc = cycles_from_mask(pred[dev] > THR[dev], ts_eval, dev)
        sc = score_cycles(pe_cyc, gt_cyc, dev)
        nm = ev.nmae_for_device(ts_eval, pred[dev].astype('float64'),
                                ts_eval[valid], gt_w[valid].astype('float64'),
                                np.nan_to_num(mains_raw, nan=0.0).astype('float64'))
        per[dev] = {'n_gt': sc['n_gt'], 'n_pred': sc['n_pred'],
                    'n_matched': sc['n_matched'], 'precision': sc['precision'],
                    'recall': sc['recall'], 'f1': sc['f1'],
                    'mae_w': nm['mae_w'], 'nmae': nm['nmae'],
                    'nonnull_frac': float(valid.mean())}
        pred_energy_wh += float(np.sum(pred[dev], dtype='float64')) * 6.0 / 3600.0
        gt_energy_wh += float(np.nansum(gt_w, dtype='float64')) * 6.0 / 3600.0

    f1s = {d: per[d]['f1'] for d in DEVICES}
    pooled = ev.pool_scores([per[d] for d in DEVICES])
    print('')
    print('device            n_cyc  n_pred  match     P      R      F1'
          '     MAE_W   nMAE')
    for d in DEVICES:
        s = per[d]
        print(f"{d:16s} {s['n_gt']:6d} {s['n_pred']:7d} {s['n_matched']:6d}   "
              f"{s['precision']:.3f}  {s['recall']:.3f}  {s['f1']:.3f}   "
              f"{s['mae_w']:7.1f}  {s['nmae']:.4f}")
    print(f"pooled cycles: n_gt={pooled['n_gt']} n_pred={pooled['n_pred']} "
          f"n_matched={pooled['n_matched']} F1={pooled['f1']:.3f}")
    print(f"coverage: pred={pred_energy_wh / agg_energy_wh:.3f} "
          f"true={gt_energy_wh / agg_energy_wh:.3f} of aggregate")

    result = {'config': config, 'devices': per,
              'mean_device_f1': float(np.mean(list(f1s.values()))),
              'min_device_f1': float(min(f1s.values())),
              'min_device': min(f1s, key=f1s.get),
              'pooled_cycle_f1': float(pooled['f1']),
              'mean_mae_w': float(np.mean([per[d]['mae_w'] for d in DEVICES])),
              'worst_mae_w': float(np.max([per[d]['mae_w'] for d in DEVICES])),
              'mean_nmae': float(np.mean([per[d]['nmae'] for d in DEVICES])),
              'coverage_pred_share': pred_energy_wh / agg_energy_wh,
              'coverage_true_share': gt_energy_wh / agg_energy_wh,
              'elapsed_s': time.time() - t_start}
    print('')
    print(f"METRIC {prefix}mean_device_f1={result['mean_device_f1']:.6f}")
    print(f"METRIC {prefix}min_device_f1={result['min_device_f1']:.6f}")
    print(f"METRIC {prefix}pooled_cycle_f1={result['pooled_cycle_f1']:.6f}")
    print(f"METRIC {prefix}mean_mae_w={result['mean_mae_w']:.4f}")
    print(f"METRIC {prefix}worst_mae_w={result['worst_mae_w']:.4f}")
    print(f"METRIC {prefix}mean_nmae={result['mean_nmae']:.6f}")
    print(f"METRIC {prefix}coverage_pred_share={result['coverage_pred_share']:.6f}")
    print(f"METRIC {prefix}coverage_true_share={result['coverage_true_share']:.6f}")
    return result


def smoothed_perfect(evh: dict) -> dict:
    """Median-3-smoothed GT per device: what any real model produces."""
    out = {}
    for dev in DEVICES:
        x = np.nan_to_num(evh['devices'][dev].astype('float32'), nan=0.0)
        xp = np.pad(x, 1, mode='edge')
        win = np.lib.stride_tricks.sliding_window_view(xp, 3)
        out[dev] = np.median(win, axis=1).astype('float32')
    return out


def sanity_check(evh: dict) -> bool:
    ts = evh['ts_us']
    print('sanity gate: smoothed-perfect predictor under v2 cycle scoring')
    f1s = {}
    for dev in DEVICES:
        gt_w = evh['devices'][dev]
        valid = ~np.isnan(gt_w)
        gt = cycles_from_mask((gt_w > THR[dev]) & valid, ts, dev)
        pe = cycles_from_mask(smoothed_perfect(evh)[dev] > THR[dev], ts, dev)
        f1s[dev] = score_cycles(pe, gt, dev)['f1']
        print(f'   SANITY {dev}: n_gt={len(gt)} f1={f1s[dev]:.3f}')
    ok = min(f1s.values()) >= SANITY_MIN
    print(f'   SANITY_GATE={"PASS" if ok else "FAIL"} (min {min(f1s.values()):.3f}'
          f' < {SANITY_MIN})' if not ok else
          f'   SANITY_GATE=PASS (min {min(f1s.values()):.3f})')
    return ok


def main() -> None:
    selftest = '--selftest' in sys.argv
    t_start = time.time()
    v1.check_threshold_file()
    eval_hi = SPLIT_US + EVAL_DAYS * 86_400_000_000

    print('loading data (cached under .auto/cache) ...')
    pre = v1.load_house(TARGET_HOUSE, None, SPLIT_US, 'pre')
    evh = v1.load_house(TARGET_HOUSE, SPLIT_US, eval_hi, 'eval90d')

    calib = build_calibration_v2(pre)
    meta = {'devices': list(DEVICES), 'thresholds': dict(THR),
            'device_class': dict(DEVICE_CLASS),
            'cadence_s': 6, 'cadence_us': CADENCE_US, 'k_calib': K_CALIB,
            'tau_onset_s': dict(TAU_ONSET_S), 'dwell_s': dict(DWELL_S),
            'merge_s': dict(MERGE_S), 'duration_band': DURATION_BAND,
            'press_jitter_s': PRESS_JITTER_S, 'pre_roll_s': PRE_ROLL_S,
            'split_us': SPLIT_US,
            'eval_span_us': [SPLIT_US, eval_hi]}

    if selftest:
        print('')
        if not sanity_check(evh):
            raise SystemExit(2)
        print(f'elapsed {time.time() - t_start:.0f}s (selftest)')
        return

    def _fill(a):
        return (pd.Series(a).ffill(limit=FFILL_LIMIT).fillna(0.0)
                .to_numpy(dtype='float32'))
    ctx = {'meta': meta, 'calib': calib,
           'pre': {'ts_us': pre['ts_us'], 'mains': _fill(pre['mains'])},
           'eval': {'ts_us': evh['ts_us'],
                    'mains': _fill(evh['mains'])}}
    print('building model (src/experiments/04_autoresearch/model.py) ...')
    spec = importlib.util.spec_from_file_location('ar_model', MODEL_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['ar_model'] = mod
    spec.loader.exec_module(mod)
    predict = mod.build_and_train(ctx)

    config = {'benchmark': 'v2-cycles', 'target_house': TARGET_HOUSE,
              'devices': DEVICES, 'thr_on_W': THR, 'eval_days': EVAL_DAYS,
              'cadence': CADENCE, 'k_calib': K_CALIB,
              'tau_onset_s': TAU_ONSET_S, 'dwell_s': DWELL_S,
              'merge_s': MERGE_S, 'duration_band': DURATION_BAND,
              'calibration': 'aggregate-only marks (FAQ Q1)',
              'ctx_pre_aggregate': True,
              'press_jitter_s': PRESS_JITTER_S,
              'passive_fridge_h': PASSIVE_FRIDGE_H}
    if not sanity_check(evh):
        raise SystemExit('sanity gate failed - benchmark invalid')
    result = run_score_v2(evh, predict, t_start, config)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=1))
    print(f"elapsed {result['elapsed_s']:.0f}s -> {OUT_PATH}")


if __name__ == '__main__':
    main()
