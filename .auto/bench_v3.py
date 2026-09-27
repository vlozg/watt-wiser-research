"""BENCH v3 - segment-2 protocol (owner-directed, 2026 authorization).

Why v3 exists: the owner re-scored HEAD across 20 calibration seeds and
seed 2026 (the v2 single seed) ranks 1/20 - median 0.429 vs 0.590. The
v2 number was a lucky draw. v3 makes the metric honest:

1. PRIMARY = median of mean_device_f1 over the frozen seed list
   SEEDS = [2026, 1, .., 9]. Guardrails: p10 of the seed distribution
   and each device's median F1. METRIC names unchanged for the primary
   so the autoresearch session keeps tracking the same metric.
2. Transfer track (houses + device sets frozen on ground-truth
   usability BEFORE any pretraining work; no model score was looked at):
   - ukdale/house_2: kettle 1477, microwave 500, dishwasher 90
     (gold_annot thr_used_w). fridge EXCLUDED: gold threshold 5.5 W
     sits inside standby noise. washing_machine EXCLUDED after the
     gate ran: its smoothed-perfect ceiling is 0.889 (< 0.9; only 17
     eval cycles and median-3 absorbs short wm sub-cycles), so the
     pair is partially unlearnable - same principle that retired the
     v1 episode metric (H15). Excluded on GT evidence alone, before
     any bet used the transfer track; the measured ceiling stays on
     record here. Integrity note: the re-baseline had already scored
     this pair at 0.000 when the gate failure was diagnosed, and
     excluding a zero pair raises transfer_mean_f1 - the exclusion
     rule is the frozen gate applied as written (any pair under 0.9
     goes), and this note declares the direction.
   - ukdale/house_5: fridge 54, washing_machine 50, dishwasher 48.5.
     kettle EXCLUDED: 0 post-split eval cycles (owner-confirmed).
     microwave EXCLUDED: profile says constant ~50 W, no signal.
   - refit/house_5, house_3, house_2, house_9, house_20: every canonical
     device with >= 10 post-split eval cycles and a sane threshold
     (thr <= 0.5 * p50_on_W); canonical GT = union of mapped channels.
     REFIT split = floor-to-UTC-midnight of t0 + 75% of mains span (the
     same rule gold_annot ukdale splits state). Selection rule for the
     5 houses: among houses where both program devices are usable,
     maximize usable-device count then the minimum post-split eval
     count across devices (balanced coverage, GT-only criterion).
   - Transfer protocol: the house_1-calibrated predictor is applied to
     the transfer house's aggregate (ctx['eval'] stays house_1; no
     retraining on the target house - the product does get the target
     home's live aggregate at inference). Predictions are thresholded
     at the transfer house's own device threshold basis (gold_annot
     thr_used_w, or the first sane channel thr for REFIT unions).
   - Gates per device-house pair: median-3-smoothed perfect predictor
     must score >= 0.9; random-cycle floor (same cycle count, durations
     shuffled, random onsets, frozen seed) must score <= 0.2 for
     burst/program devices. The duty class (fridge) structurally
     overlaps random placement - its floor is reported, not gated.
   - transfer_mean_f1 = mean over all declared device-house pairs
     (median over the same 10 calibration seeds per pair).
3. --confirm re-runs the house_1 sweep on days 90-365. Once per claimed
   breakthrough, never per iteration.
4. ctx['pretrain'] exposes the frozen pretraining pool (every data/gold
   house except house_1 and the transfer-test houses; greend buildings
   dropped - see note at PRETRAIN_HOUSES) through a lazy loader. The
   model must take pretraining data ONLY through ctx.

Labelled-dev-set disclosure (owner-directed): house_1's PRE-split
submeter channels are the labelled dev set - diagnostics only, never a
model input. On the record: the segment-1 diagnostic scripts
diag_i51.py, diag_i52.py and diag_i52b.py already read those channels
(they informed the frozen rules but entered no model path).

The house_1 protocol is otherwise identical to v2: build_calibration_v3
is build_calibration_v2 with the seed as a parameter; scoring machinery
is imported from bench_v2. Consistency check: the seed-2026 row must
reproduce the v2 number exactly.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.auto'))
sys.path.insert(0, str(ROOT / 'src'))

import bench as v1  # noqa: E402
import bench_v2 as v2  # noqa: E402  (scoring machinery reused verbatim)
from wattwiser.experiments import evaluation as ev  # noqa: E402

MODEL_PATH = v2.MODEL_PATH
OUT_PATH = ROOT / '.auto' / 'last_bench_v3.json'
GOLD = ROOT / 'data' / 'gold'
DAY_US = 86_400_000_000

# ------------------------------------------------------------ frozen protocol
SEEDS = [2026, 1, 2, 3, 4, 5, 6, 7, 8, 9]
DEVICES = v1.DEVICES
THR = dict(v1.THR)                      # house_1 gold thresholds (asserted)
SPLIT_US = v1.SPLIT_US
EVAL_DAYS = 90
CONFIRM_DAYS = 365                      # --confirm scores days 90..365
SANITY_MIN = v2.SANITY_MIN
DURATION_BAND = v2.DURATION_BAND
DEVICE_CLASS = dict(v2.DEVICE_CLASS)
FLOOR_MAX = {'burst': 0.20, 'program': 0.20, 'duty': None}
FLOOR_SEED = 20260301                   # frozen rng base for random floors
REFIT_MIN_EVAL_CYCLES = 10

TRANSFER = {
    ('ukdale', 'house_2'): {
        'split_us': 1376265600000000,
        'devices': {'kettle': 1477.0, 'microwave': 500.0,
                    'dishwasher': 90.0},
        'excluded': {'fridge': 'gold thr 5.5 W inside standby noise',
                     'washing_machine': 'smoothed-perfect ceiling 0.889 '
                     '< 0.9 gate (17 eval cycles; median-3 absorbs short '
                     'sub-cycles) - pair excluded, GT-side, before any '
                     'bet touched the transfer track'},
    },
    ('ukdale', 'house_5'): {
        'split_us': 1412899200000000,
        'devices': {'fridge': 54.0, 'washing_machine': 50.0,
                    'dishwasher': 48.5},
        'excluded': {'kettle': '0 post-split eval cycles',
                     'microwave': 'no microwave signal (profile)'},
    },
    ('refit', 'house_5'): {'split_us': None},
    ('refit', 'house_3'): {'split_us': None},
    ('refit', 'house_2'): {'split_us': None},
    ('refit', 'house_9'): {'split_us': None},
    ('refit', 'house_20'): {'split_us': None},
}

PRETRAIN_HOUSES = (
    ['ukdale/house_3', 'ukdale/house_4']
    + ['refit/house_' + h for h in
       ('1', '4', '6', '7', '8', '10', '11', '12', '13', '15', '16', '17',
        '18', '19', '21')]
    + ['eco/house_0' + i for i in ('1', '2', '3', '5', '6')]
    + ['redd/building_' + str(i) for i in range(1, 7)]
    + ['ampds2/building_1']
)
# Pool correction (declared before any bet touched ctx['pretrain']): the
# 8 greend buildings were dropped from the pool - they have submeter
# channels but NO mains.parquet, so no aggregate exists to mine and the
# lazy loader would crash on them. Pool-side GT-integrity fix, same
# principle as the house_2 washing_machine exclusion; HEAD never reads
# ctx['pretrain'], so the re-baseline floor is unaffected. Second
# correction: eco/house_04 dropped - its mains.parquet has 0 rows.
# Usable pool: 29 houses (kettle 17 / fridge 27 / microwave 18 /
# dishwasher 18 / washing_machine 22 coverage).


def index_us(idx: pd.DatetimeIndex) -> np.ndarray:
    vals = np.asarray(idx.astype('int64'), dtype=np.int64)
    unit = getattr(idx, 'unit', 'ns')
    return {'ns': vals // 1000, 'us': vals, 'ms': vals * 1000,
            's': vals * 10 ** 6}[unit]


def split75_us(t0_us: int, t1_us: int) -> int:
    mid = pd.Timestamp(t0_us, unit='us') + pd.Timedelta(
        seconds=0.75 * (t1_us - t0_us) / 1e6)
    return int(mid.floor('D').value // 1000)


# ------------------------------------------------------------ data loading
def _resample(path: Path, idx=None):
    df = pd.read_parquet(path, columns=['ts_us', 'w'])
    i = pd.to_datetime(df['ts_us'].to_numpy(), unit='us')
    s = pd.Series(df['w'].to_numpy(dtype='float64'), index=i).sort_index()
    s = s.resample(v1.CADENCE).mean()
    return s.reindex(idx) if idx is not None else s


def _mains_bounds(ds: str, house: str) -> tuple[int, int]:
    df = pd.read_parquet(GOLD / ds / house / 'mains.parquet',
                         columns=['ts_us'])
    ts = df['ts_us'].to_numpy()
    return int(ts.min()), int(ts.max())


def load_span(ds: str, house: str, lo_us, hi_us, tag: str,
              channels) -> dict:
    """Mains + named channels over [lo_us, hi_us), cached as npz."""
    cache = v1.CACHE_DIR / (ds + '_' + house + '_' + tag + '.npz')
    names = ['mains'] + list(channels)
    files = [GOLD / ds / house / (n + '.parquet') for n in names]
    sig = ';'.join(f.name + ':' + str(int(f.stat().st_mtime)) for f in files)
    v1.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        z = np.load(cache)
        if str(z['sig']) == sig:
            out = {'ts_us': z['ts_us'], 'mains': z['mains'], 'devices': {}}
            for n in channels:
                out['devices'][n] = z['ch_' + n]
            return out
    t0, t1 = _mains_bounds(ds, house)
    if lo_us is None:
        lo_us = t0
    if hi_us is None:
        hi_us = t1
    idx = pd.date_range(pd.Timestamp(lo_us, unit='us'),
                        pd.Timestamp(hi_us, unit='us'),
                        freq=v1.CADENCE, inclusive='left')
    mains = _resample(GOLD / ds / house / 'mains.parquet',
                      idx).to_numpy(dtype='float32')
    devices = {}
    for n in channels:
        p = GOLD / ds / house / (n + '.parquet')
        devices[n] = (_resample(p, idx).to_numpy(dtype='float32')
                      if p.exists() else np.full(len(idx), np.nan, 'float32'))
    out = {'ts_us': index_us(idx), 'mains': mains, 'devices': devices}
    np.savez(cache, sig=np.array(sig), ts_us=out['ts_us'], mains=mains,
             **{'ch_' + n: devices[n] for n in channels})
    print(f'   built cache {cache.name}: {len(idx):,} samples '
          f'({time.strftime("%H:%M:%S")})')
    return out


# ------------------------------------------------------------ transfer GT
def refit_channels(house: str) -> dict:
    """canonical -> [(channel, thr, sane)] from thresholds.json."""
    tmap: dict = {}
    raw = json.loads((GOLD / 'thresholds.json').read_text())['refit'][house]
    for ch, m in raw.items():
        c = m.get('canonical')
        if c in DEVICES:
            t = float(m['thr_on_W'])
            p50 = m.get('p50_on_W')
            sane = p50 is None or t <= 0.5 * float(p50)
            tmap.setdefault(c, []).append((ch, t, sane))
    return tmap


def refit_gt(house: str, span: dict) -> tuple[dict, dict, dict]:
    """Canonical GT = union of on-masks over sane mapped channels.

    Returns (gt_masks, pred_thr per device, channel info)."""
    tmap = refit_channels(house)
    gt, thr, info = {}, {}, {}
    for dev, chans in sorted(tmap.items()):
        union = None
        used = []
        for ch, t, sane in chans:
            w = span['devices'].get(ch)
            if w is None or not sane:
                continue
            m = (np.nan_to_num(w) > t)
            union = m if union is None else (union | m)
            used.append(ch)
        if union is not None:
            gt[dev] = union
            thr[dev] = [t for ch, t, sane in chans if sane][0]
            info[dev] = '+'.join(used)
    return gt, thr, info


def smoothed_mask(w: np.ndarray) -> np.ndarray:
    x = np.nan_to_num(np.asarray(w, dtype='float32'), nan=0.0)
    xp = np.pad(x, 1, mode='edge')
    win = np.lib.stride_tricks.sliding_window_view(xp, 3)
    return np.median(win, axis=1).astype('float32')


def random_floor(gt_eps: pd.DataFrame, dev: str, ts_us: np.ndarray) -> float:
    """Random-onset cycles with the same count + duration distribution."""
    if not len(gt_eps):
        return float('nan')
    dur = (gt_eps['t_off_us'] - gt_eps['t_on_us']).to_numpy(np.int64)
    rng = np.random.default_rng(FLOOR_SEED + zlib.crc32(dev.encode()))
    lo, hi = int(ts_us[0]), int(ts_us[-1]) + v1.CADENCE_US
    dmax = int(dur.max())
    if hi - lo <= dmax:
        return float('nan')
    onsets = (lo + rng.random(len(dur)) * (hi - lo - dmax)).astype(np.int64)
    pred = pd.DataFrame({'t_on_us': onsets,
                         't_off_us': np.minimum(onsets + dur, hi)})
    return ev.score_episodes(pred, gt_eps, v2.TAU_ONSET_S[dev] * 1e6,
                             DURATION_BAND)['f1']


def pair_gate(tag: str, dev: str, sm_eps: pd.DataFrame,
              gt_eps: pd.DataFrame, ts_us: np.ndarray) -> tuple[bool, float, float]:
    """Smoothed-perfect sanity + random-cycle floor for one pair.

    sm_cycles is the caller's perfect-but-smoothed predictor under the
    same cycle rules: median-3-smoothed WATTS at the device threshold
    (ukdale single channel), or the union of per-channel smoothed masks
    (REFIT canonical unions) - never a smoothing of a boolean mask."""
    f1_sm = ev.score_episodes(sm_eps, gt_eps, v2.TAU_ONSET_S[dev] * 1e6,
                              DURATION_BAND)['f1']
    fl = random_floor(gt_eps, dev, ts_us)
    ok = f1_sm >= SANITY_MIN
    print(f'   GATE {tag}/{dev}: smoothed_perfect={f1_sm:.3f} '
          f'floor={fl:.3f} n_gt={len(gt_eps)} -> '
          f'{"ok" if ok else "FAIL"}')
    return ok, f1_sm, fl


def cycles_of(on: np.ndarray, ts_us: np.ndarray, dev: str):
    return v2.cycles_from_mask(np.asarray(on, dtype=bool), ts_us, dev)


# ------------------------------------------------------------ calibration
def build_calibration_v3(pre: dict, seed: int) -> dict:
    """bench_v2.build_calibration_v2 with the seed as a parameter."""
    rng = np.random.default_rng(seed)
    feed = (pd.Series(pre['mains']).ffill(limit=v1.FFILL_LIMIT).fillna(0.0)
            .to_numpy(dtype='float32'))
    n = len(feed)
    ts = pre['ts_us']
    jn = int(round(v2.PRESS_JITTER_S * 1e6 / v1.CADENCE_US))
    calib = {}
    for dev in DEVICES:
        if dev == 'fridge':
            lo = int(rng.integers(0, n - v2.PASSIVE_FRIDGE_H * 3600 // 6))
            hi = lo + v2.PASSIVE_FRIDGE_H * 3600 // 6
            calib[dev] = {'marks_us': np.empty((0, 2), dtype=np.int64),
                          'mains_seg': [feed[lo:hi]], 'passive': True}
            continue
        w = pre['devices'][dev]
        valid = ~np.isnan(w)
        cyc = v2.cycles_from_mask((np.nan_to_num(w) > THR[dev]) & valid,
                                  pre['ts_us'], dev)
        if not len(cyc):
            raise SystemExit('no pre-span cycles for ' + dev)
        take = min(v2.K_CALIB, len(cyc))
        idx = sorted(rng.permutation(len(cyc))[:take].tolist())
        marks, segs = [], []
        roll_us = v2.PRE_ROLL_S * 1_000_000
        for i in idx:
            s_us, e_us = int(cyc['t_on_us'].iloc[i]), int(cyc['t_off_us'].iloc[i])
            lo_us = s_us - roll_us + int(rng.integers(-jn, jn + 1)) * v1.CADENCE_US
            hi_us = e_us + roll_us + int(rng.integers(-jn, jn + 1)) * v1.CADENCE_US
            lo = int(np.searchsorted(ts, lo_us))
            hi = int(np.searchsorted(ts, hi_us))
            lo, hi = max(lo, 0), min(hi, n)
            if hi - lo < 2:
                continue
            seg = feed[lo:hi]
            if np.count_nonzero(seg == 0) > 0.9 * len(seg):
                continue
            marks.append((ts[lo], ts[min(hi, n - 1)]))
            segs.append(seg)
        calib[dev] = {'marks_us': np.asarray(marks, dtype=np.int64),
                      'mains_seg': segs, 'passive': False}
    return calib


# ------------------------------------------------------------ pretraining
def _canon_map(ds: str, house: str) -> dict:
    if ds == 'refit':
        out = {}
        for dev, chans in refit_channels(house).items():
            for ch, _t, _s in chans:
                out[ch] = dev
        return out
    raw = json.loads((GOLD / 'thresholds.json').read_text())[ds][house]
    return {ch: m.get('canonical') for ch, m in raw.items()
            if m.get('canonical') in DEVICES}


def make_pretrain_ctx() -> dict:
    def load(house_tag: str):
        ds, house = house_tag.split('/', 1)
        canon = _canon_map(ds, house)
        chans = sorted(canon)
        span = load_span(ds, house, None, None, 'full', chans)
        return {'ts_us': span['ts_us'], 'mains': span['mains'],
                'channels': {ch: span['devices'][ch] for ch in chans},
                'canonical': canon}
    return {'houses': list(PRETRAIN_HOUSES), 'load': load}


# ------------------------------------------------------------ main
def main() -> None:
    argv = sys.argv[1:]
    selftest = '--selftest' in argv
    confirm = '--confirm' in argv
    t_start = time.time()
    v1.check_threshold_file()

    # frozen-threshold drift guard for the ukdale transfer houses
    for (ds, house), cfg in TRANSFER.items():
        if ds != 'ukdale':
            continue
        prof = {}
        with open(ROOT / 'data' / 'gold_annot' / 'ukdale' / house /
                  'device_profile.csv') as f:
            for row in csv.DictReader(f):
                if row['device'] in DEVICES:
                    prof[row['device']] = row
        for dev, t in cfg['devices'].items():
            got = float(prof[dev]['thr_used_w'])
            if abs(got - t) > 1e-9:
                raise SystemExit(
                    f'v3 drift: {house} {dev} threshold {got} != {t}')

    print('loading house_1 (cached) ...')
    pre = v1.load_house(v1.TARGET_HOUSE, None, SPLIT_US, 'pre')
    ev_days = CONFIRM_DAYS if confirm else EVAL_DAYS
    evh = v1.load_house(v1.TARGET_HOUSE, SPLIT_US,
                        SPLIT_US + ev_days * DAY_US,
                        'eval90_365' if confirm else 'eval90d')

    print('building model module ...')
    spec = importlib.util.spec_from_file_location('ar_model', MODEL_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['ar_model'] = mod
    spec.loader.exec_module(mod)

    eval_hi = SPLIT_US + ev_days * DAY_US
    meta = {'devices': list(DEVICES), 'thresholds': dict(THR),
            'device_class': DEVICE_CLASS, 'cadence_s': 6,
            'cadence_us': v1.CADENCE_US, 'k_calib': v2.K_CALIB,
            'tau_onset_s': dict(v2.TAU_ONSET_S), 'dwell_s': dict(v2.DWELL_S),
            'merge_s': dict(v2.MERGE_S), 'duration_band': DURATION_BAND,
            'press_jitter_s': v2.PRESS_JITTER_S,
            'pre_roll_s': v2.PRE_ROLL_S, 'split_us': SPLIT_US,
            'eval_span_us': [SPLIT_US, eval_hi],
            'seeds': list(SEEDS), 'bench': 'v3', 'confirm': confirm}

    def _fill(a):
        return (pd.Series(a).ffill(limit=v1.FFILL_LIMIT).fillna(0.0)
                .to_numpy(dtype='float32'))

    h1_filled = _fill(evh['mains'])
    pretrain_ctx = make_pretrain_ctx()

    # ---- train once per seed
    predictors = {}
    for seed in SEEDS:
        calib = build_calibration_v3(pre, seed)
        ctx = {'meta': meta, 'calib': calib,
               'pre': {'ts_us': pre['ts_us'], 'mains': _fill(pre['mains'])},
               'eval': {'ts_us': evh['ts_us'], 'mains': h1_filled},
               'pretrain': pretrain_ctx}
        t0 = time.time()
        predictors[seed] = mod.build_and_train(ctx)
        print(f'--- seed {seed}: trained in {time.time() - t0:.1f}s')

    # ---- house_1 sweep
    f1_matrix = {}
    for seed in SEEDS:
        pred = predictors[seed](h1_filled)
        per = {}
        for dev in DEVICES:
            gt_w = evh['devices'][dev]
            valid = ~np.isnan(gt_w)
            gt_cyc = v2.cycles_from_mask((gt_w > THR[dev]) & valid,
                                         evh['ts_us'], dev)
            pe_cyc = v2.cycles_from_mask(pred[dev] > THR[dev],
                                         evh['ts_us'], dev)
            per[dev] = v2.score_cycles(pe_cyc, gt_cyc, dev)['f1']
        f1_matrix[seed] = per
        means = np.mean(list(per.values()))
        print(f'    seed {seed}: mean_f1={means:.4f} '
              + ' '.join(f'{d}={per[d]:.3f}' for d in DEVICES))

    seed_means = [float(np.mean(list(f1_matrix[s].values()))) for s in SEEDS]
    med = float(np.median(seed_means))
    p10 = float(np.percentile(seed_means, 10))
    dev_meds = {d: float(np.median([f1_matrix[s][d] for s in SEEDS]))
                for d in DEVICES}
    print('')
    print(f'house_1 v3 primary (median over {len(SEEDS)} seeds): {med:.6f}')
    print(f'  seed means: {[round(x, 4) for x in seed_means]}')
    print(f'  p10={p10:.6f}')
    for d, m in dev_meds.items():
        print(f'  median {d}: {m:.4f}')

    if selftest:
        print(f'elapsed {time.time() - t_start:.0f}s (selftest)')
        return

    print('')
    print(f'METRIC mean_device_f1={med:.6f}')
    print(f'METRIC mean_device_f1_p10={p10:.6f}')
    for d, m in dev_meds.items():
        print(f'METRIC median_{d}_f1={m:.6f}')
    for s, m in zip(SEEDS, seed_means):
        print(f'METRIC calib_seed{s}_mean_device_f1={m:.6f}')

    result = {'config': {'bench': 'v3', 'seeds': SEEDS, 'confirm': confirm,
                         'eval_days': ev_days},
              'house_1': {'seed_f1': {str(k): v for k, v in f1_matrix.items()},
                          'median_mean_device_f1': med, 'p10': p10,
                          'median_device_f1': dev_meds}}

    # ---- transfer track
    print('')
    print('=== transfer track ===')
    pair_scores = {}
    gates_ok = True
    floors = {}
    for (ds, house), cfg in TRANSFER.items():
        if ds == 'ukdale':
            thr_map = dict(cfg['devices'])
            chans = list(thr_map.keys())
            _t0, t1 = _mains_bounds(ds, house)
            hi = min(cfg['split_us'] + EVAL_DAYS * DAY_US, t1)
            span = load_span(ds, house, cfg['split_us'], hi, 'tr90d', chans)
            gt_masks = {dev: (span['devices'][dev] > t)
                        for dev, t in thr_map.items()}
            info = {dev: dev for dev in thr_map}
        else:
            t0, t1 = _mains_bounds(ds, house)
            split_us = split75_us(t0, t1)
            hi = min(split_us + EVAL_DAYS * DAY_US, t1)
            tmap = refit_channels(house)
            chans = sorted({ch for lst in tmap.values() for ch, _t, _s in lst})
            span = load_span(ds, house, split_us, hi, 'tr90d', chans)
            gt_masks, thr_map, info = refit_gt(house, span)
            for dev in sorted(thr_map):
                n = len(cycles_of(gt_masks[dev], span['ts_us'], dev))
                if n < REFIT_MIN_EVAL_CYCLES:
                    print(f'   {ds}/{house} {dev}: {n} eval cycles -> excluded')
                    gt_masks.pop(dev)
                    thr_map.pop(dev)
                else:
                    print(f'   {ds}/{house} {dev}: {n} eval cycles '
                          f'({info[dev]})')
        print(f'--- transfer {ds}/{house}: devices={sorted(thr_map)}')
        filled = _fill(span['mains'])
        dev_f1 = {dev: [] for dev in thr_map}
        for seed in SEEDS:
            pred = predictors[seed](filled)
            for dev in thr_map:
                gt_cyc = cycles_of(gt_masks[dev], span['ts_us'], dev)
                pe_cyc = cycles_of(pred[dev] > thr_map[dev],
                                   span['ts_us'], dev)
                dev_f1[dev].append(v2.score_cycles(pe_cyc, gt_cyc, dev)['f1'])
        for dev, f1s in dev_f1.items():
            m = float(np.median(f1s))
            pair_scores[f'{ds}/{house}/{dev}'] = m
            gt_eps = cycles_of(gt_masks[dev], span['ts_us'], dev)
            if ds == 'ukdale':
                sm_eps = cycles_of(smoothed_mask(span['devices'][dev])
                                   > thr_map[dev], span['ts_us'], dev)
            else:
                sm_union = None
                for ch, t, sane in refit_channels(house)[dev]:
                    if not sane or span['devices'].get(ch) is None:
                        continue
                    sm = (smoothed_mask(span['devices'][ch]) > t)
                    sm_union = sm if sm_union is None else (sm_union | sm)
                sm_eps = cycles_of(sm_union, span['ts_us'], dev)
            ok, _f1sm, fl = pair_gate(f'{ds}/{house}', dev, sm_eps,
                                      gt_eps, span['ts_us'])
            floors[f'{ds}/{house}/{dev}'] = fl
            if DEVICE_CLASS[dev] != 'duty' and fl > FLOOR_MAX[DEVICE_CLASS[dev]]:
                print(f'   GATE FAIL floor {ds}/{house}/{dev}: {fl:.3f}')
                gates_ok = False
            if not ok:
                gates_ok = False
            print(f'    {dev:16s} transfer_f1(median seeds)={m:.4f}')

    if pair_scores:
        tmean = float(np.mean(list(pair_scores.values())))
        print(f'transfer mean over {len(pair_scores)} device-house pairs: '
              f'{tmean:.4f}')
        print(f'METRIC transfer_mean_f1={tmean:.6f}')
        for k, v in pair_scores.items():
            print(f'METRIC transfer_{k.replace("/", "_")}_f1={v:.6f}')
        result['transfer'] = pair_scores
        result['floors'] = floors
        result['gates_ok'] = gates_ok
        if not gates_ok:
            print('GATE FAILURE: benchmark invalid (see GATE lines above)')
            sys.exit(2)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=1))
    print(f'elapsed {time.time() - t_start:.0f}s -> {OUT_PATH}')


if __name__ == '__main__':
    main()

