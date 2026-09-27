"""BENCH v4 pool eligibility + freeze (owner-directed, segment 2).

GT-ONLY. This module reads NO model score. It runs once; the result is
frozen in .auto/pool_v4.json and bench_v4.py only ever reads that file.

Why v4 exists: bench v3's transfer track applies house_1's predictor to
other homes. The product never does that - it re-calibrates on the target
home with that home's K=5 marks, its own pre-split history and a fresh
build_and_train. v4 makes the benchmark match the product: every pool
house is scored re-calibrated.

Pool rule per (house, device) pair - ALL must hold:
  P1  sane threshold: thresholds.json p50_on_W is None, or
      thr_on_W <= 0.5 * p50_on_W            (the half_p50 contract)
  P2  >= K_CALIB (5) device cycles in the pre-split span (marks exist)
  P3  >= MIN_EVAL_CYCLES (10) cycles in the first EVAL_DAYS post-split
  P4  smoothed-perfect F1 >= SANITY_MIN on that eval span (v3 gate)
  P5  random-cycle floor <= FLOOR_MAX for burst/program devices
A house joins the pool iff >= 1 pair holds.

Structural exclusions (recorded, never gated on a model score):
  - greend has submeter channels but no mains.parquet -> no aggregate.
  - the 7 v3 transfer houses are the v4 HOLDOUT (scored at milestones).

Threshold source is thresholds.json for EVERY house (thr_on_W + p50_on_W +
canonical), so ukdale/house_1 reproduces the frozen v1.THR exactly and no
house needs a hand-set constant.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.auto'))
sys.path.insert(0, str(ROOT / 'src'))

import bench as v1  # noqa: E402
import bench_v2 as v2  # noqa: E402
import bench_v3 as v3  # noqa: E402
from wattwiser.experiments import evaluation as ev  # noqa: E402

GOLD = ROOT / 'data' / 'gold'
OUT = ROOT / '.auto' / 'pool_v4.json'
DAY_US = 86_400_000_000

K_CALIB = v1.K_CALIB                      # 5
MIN_EVAL_CYCLES = v3.REFIT_MIN_EVAL_CYCLES  # 10
SANITY_MIN = v3.SANITY_MIN
FLOOR_MAX = v3.FLOOR_MAX
DEVICE_CLASS = v3.DEVICE_CLASS
EVAL_DAYS = v3.EVAL_DAYS                  # 90 (upper bound, see below)
MIN_TEST_DAYS = 7                         # eval window floor for short houses
PRE_PROBE_DAYS = 180                      # P2 probe window (see below)
SEEDS = [2026, 1, 2, 3, 4]                # v4 scoring seeds (freeze here)

HOLDOUT = [('ukdale', 'house_2'), ('ukdale', 'house_5'), ('refit', 'house_5'),
           ('refit', 'house_3'), ('refit', 'house_2'), ('refit', 'house_9'),
           ('refit', 'house_20')]


def ds_houses(ds: str) -> list:
    return sorted(p.name for p in (GOLD / ds).iterdir() if p.is_dir())


def canon_channels(ds: str, house: str) -> dict:
    """canonical -> [(channel, thr_on_W, p50_on_W)] from thresholds.json."""
    raw = json.loads((GOLD / 'thresholds.json').read_text())[ds][house]
    out: dict = {}
    for ch, m in raw.items():
        c = m.get('canonical')
        if c in v1.DEVICES:
            out.setdefault(c, []).append(
                (ch, float(m['thr_on_W']), m.get('p50_on_W')))
    return out


def split_of(ds: str, house: str, t0: int, t1: int) -> int:
    """ukdale: the gold_annot splits.csv contract; else v3's split75 rule."""
    if ds == 'ukdale':
        p = ROOT / 'data' / 'gold_annot' / 'ukdale' / house / 'splits.csv'
        if p.exists():
            with open(p) as f:
                return int(next(csv.DictReader(f))['split_us'])
    return v3.split75_us(t0, t1)


def _sane(thr: float, p50) -> bool:
    return p50 is None or thr <= 0.5 * float(p50)


def _union_mask(chans: list, span_devs: dict, smooth: bool):
    union = None
    used = []
    for ch, t, p in chans:
        if not _sane(t, p):
            continue
        w = span_devs.get(ch)
        if w is None:
            continue
        x = v3.smoothed_mask(w) if smooth else np.nan_to_num(w)
        m = x > t
        union = m if union is None else (union | m)
        used.append(ch)
    return union, used


def eval_house(job: tuple) -> dict:
    ds, house = job
    tag = ds + '/' + house
    try:
        cmap = canon_channels(ds, house)
    except Exception as exc:                       # noqa: BLE001
        return {'tag': tag, 'error': 'thresholds: ' + repr(exc)}
    if not cmap:
        return {'tag': tag, 'error': 'no canonical channel'}
    try:
        t0, t1 = v3._mains_bounds(ds, house)
    except Exception as exc:                       # noqa: BLE001
        return {'tag': tag, 'error': 'mains bounds: ' + repr(exc)}
    split = split_of(ds, house, t0, t1)
    # Eval window = the first EVAL_DAYS post-split days, clamped to the
    # house's data. Houses shorter than that are scored on what exists;
    # a floor of MIN_TEST_DAYS keeps the window from being degenerate.
    hi = min(split + EVAL_DAYS * DAY_US, t1)
    if hi - split < MIN_TEST_DAYS * DAY_US:
        return {'tag': tag, 'error': 'post-split ' + str(int((hi - split)
                / DAY_US)) + 'd < ' + str(MIN_TEST_DAYS) + 'd'}
    ev_days = round((hi - split) / DAY_US, 1)
    chans = sorted({ch for lst in cmap.values() for ch, _t, _p in lst})
    span = v3.load_span(ds, house, split, hi, 'v4eval90d', chans)
    ts = span['ts_us']
    pairs, rejected = {}, {}
    need_pre = []
    for dev in sorted(cmap):
        chans_d = cmap[dev]
        sane = [c for c in chans_d if _sane(c[1], c[2])]
        if not sane:
            rejected[dev] = 'P1 thr not <= 0.5*p50'
            continue
        thr = sane[0][1]
        gt_mask, used = _union_mask(chans_d, span['devices'], smooth=False)
        gt_eps = v3.cycles_of(gt_mask, ts, dev)
        n_eval = len(gt_eps)
        if n_eval < MIN_EVAL_CYCLES:
            rejected[dev] = 'P3 ' + str(n_eval) + ' eval cycles < ' \
                + str(MIN_EVAL_CYCLES)
            continue
        sm_mask, _su = _union_mask(chans_d, span['devices'], smooth=True)
        sm_eps = v3.cycles_of(sm_mask, ts, dev)
        f1_sm = ev.score_episodes(sm_eps, gt_eps,
                                  v2.TAU_ONSET_S[dev] * 1e6,
                                  v3.DURATION_BAND)['f1']
        if f1_sm < SANITY_MIN:
            rejected[dev] = 'P4 smoothed_perfect ' + ('%.3f' % f1_sm) \
                + ' < ' + str(SANITY_MIN)
            continue
        fl = v3.random_floor(gt_eps, dev, ts)
        cls = DEVICE_CLASS[dev]
        if cls != 'duty' and np.isfinite(fl) and fl > FLOOR_MAX[cls]:
            rejected[dev] = 'P5 floor ' + ('%.3f' % fl) + ' > ' \
                + str(FLOOR_MAX[cls])
            continue
        pairs[dev] = {'thr': thr, 'n_eval': n_eval, 'f1_sm': float(f1_sm),
                      'floor': float(fl), 'channels': '+'.join(used),
                      'class': cls}
        need_pre.append(dev)
    if not need_pre:
        return {'tag': tag, 'split_us': split, 'eval_days': ev_days,
                'pairs': {}, 'rejected': rejected}
    # P2: marks must exist. Probe the last PRE_PROBE_DAYS of the pre-split
    # span (a subset of the real mark pool, so a pass is sound); fall back
    # to the full pre-span only for pairs still short there.
    plo = max(t0, split - PRE_PROBE_DAYS * DAY_US)
    pspan = v3.load_span(ds, house, plo, split, 'v4pre' + str(PRE_PROBE_DAYS) + 'd',
                         chans)
    pts = pspan['ts_us']
    short = []
    for dev in list(need_pre):
        gt_mask, _u = _union_mask(cmap[dev], pspan['devices'], smooth=False)
        n_pre = len(v3.cycles_of(gt_mask, pts, dev))
        if n_pre >= K_CALIB:
            pairs[dev]['n_pre'] = n_pre
            pairs[dev]['n_pre_window_d'] = PRE_PROBE_DAYS
        else:
            short.append(dev)
    if short:
        fspan = v3.load_span(ds, house, t0, split, 'v4prefull', chans)
        fts = fspan['ts_us']
        for dev in short:
            gt_mask, _u = _union_mask(cmap[dev], fspan['devices'], smooth=False)
            n_pre = len(v3.cycles_of(gt_mask, fts, dev))
            if n_pre >= K_CALIB:
                pairs[dev]['n_pre'] = n_pre
                pairs[dev]['n_pre_window_d'] = 'full'
            else:
                rejected[dev] = 'P2 ' + str(n_pre) + ' pre cycles < ' + str(K_CALIB)
                pairs.pop(dev, None)
    return {'tag': tag, 'split_us': split, 'eval_days': ev_days,
            'pairs': pairs, 'rejected': rejected}


def main() -> None:
    t0 = time.time()
    jobs, skipped = [], []
    for ds in sorted(p.name for p in GOLD.iterdir() if p.is_dir()):
        for h in ds_houses(ds):
            if (ds, h) in HOLDOUT:
                continue
            if not (GOLD / ds / h / 'mains.parquet').exists():
                skipped.append(ds + '/' + h + ': no mains.parquet (greend)')
                continue
            jobs.append((ds, h))
    print('v4 eligibility: ' + str(len(jobs)) + ' candidate houses ('
          + str(len({j[0] for j in jobs})) + ' datasets), '
          + str(len(skipped)) + ' structural skips')
    recs = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(eval_house, jobs):
            recs.append(r)
            if 'error' in r:
                print('  SKIP ' + r['tag'] + ': ' + r['error'])
            else:
                print('  ' + r['tag'] + ': pairs=' + str(sorted(r['pairs']))
                      + (' rejected=' + str(sorted(r['rejected']))
                         if r['rejected'] else ''))
    pool_pairs, pool_houses, rej = {}, [], {}
    for r in recs:
        if r.get('pairs'):
            pool_houses.append(r['tag'])
            for dev, info in r['pairs'].items():
                pool_pairs[r['tag'] + '/' + dev] = info
        if r.get('rejected'):
            for dev, why in r['rejected'].items():
                rej[r['tag'] + '/' + dev] = why
    by_dev = {d: sum(1 for k in pool_pairs if k.endswith('/' + d))
              for d in v1.DEVICES}
    result = {
        'frozen': True, 'created': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'bench': 'v4-eligibility', 'model_score_read': False,
        'seeds': SEEDS, 'eval_days': EVAL_DAYS,
        'rules': {'P1': 'thr <= 0.5*p50 (or p50 None)',
                  'P2': '>= ' + str(K_CALIB) + ' pre-split cycles',
                  'P3': '>= ' + str(MIN_EVAL_CYCLES) + ' post-split '
                  'cycles in the first ' + str(EVAL_DAYS) + ' post-split '
                  'days (window floor ' + str(MIN_TEST_DAYS) + 'd)',
                  'P4': 'smoothed_perfect >= ' + str(SANITY_MIN),
                  'P5': 'random floor <= ' + str(FLOOR_MAX)
                  + ' (duty class reported only)',
                  'threshold_source': 'data/gold/thresholds.json thr_on_W',
                  'pre_probe_days': PRE_PROBE_DAYS},
        'holdout': [d + '/' + h for d, h in HOLDOUT],
        'structural_skips': skipped,
        'pool_houses': sorted(pool_houses),
        'pairs': pool_pairs,
        'rejected_pairs': rej,
        'coverage_by_device': by_dev,
        'n_pairs': len(pool_pairs), 'n_houses': len(pool_houses),
    }
    OUT.write_text(json.dumps(result, indent=1))
    print('')
    print('POOL FROZEN: ' + str(len(pool_houses)) + ' houses, '
          + str(len(pool_pairs)) + ' device-house pairs')
    print('  coverage: ' + str(by_dev))
    print('  -> ' + str(OUT))
    print('elapsed %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
