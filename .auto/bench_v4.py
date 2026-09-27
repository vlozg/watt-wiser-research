'''BENCH v4 - per-home re-calibrated scoring over the frozen eligibility pool.

Why v4: bench v3's transfer track applies house_1's predictor to other homes,
which the product never does. v4 re-calibrates on every pool house with that
house's own K=5 marks, its own pre-split history and a fresh build_and_train -
exactly the deployment path. Which houses and which (house, device) pairs are
scorable is frozen GT-only in .auto/pool_v4.json by .auto/pool_v4.py; this
module reads that file and never re-decides eligibility.

Primary metric: median over seeds of the mean F1 over the pool's (house,
device) pairs. Reported alongside it: the device-balanced mean (the mean of the
five per-device means - fridge is 18 of 66 pairs, so the pair-mean alone
understates the program devices), the house_1 subset readout, and the
per-device medians.

Declared global choices (no per-house hand-set constant):
  - calibration marks come from the last p4.PRE_PROBE_DAYS before the split,
    the same window P2 proved holds >= K_CALIB cycles, falling back to the full
    pre-split span for pairs P2 only passed there;
  - K_CALIB marks per device, sampled with the seed, exactly as v3 does;
  - GT is the union of sane canonical channels above their own threshold,
    identical to pool_v4._union_mask;
  - device iteration order is v1.DEVICES order filtered to the house's devices,
    so the RNG stream does not depend on which devices happen to be absent.

Holdout mode (--holdout) scores the 7 frozen transfer houses. That is a
milestone-only readout: run it for a claimed breakthrough, never per iteration,
and never tune on it.
'''
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.auto'))
sys.path.insert(0, str(ROOT / 'src'))

import bench as v1                                    # noqa: E402
import bench_v2 as v2                                 # noqa: E402
import bench_v3 as v3                                 # noqa: E402
import pool_v4 as p4                                  # noqa: E402
from wattwiser.experiments import evaluation as ev     # noqa: E402

POOL = ROOT / '.auto' / 'pool_v4.json'
MODEL = ROOT / 'src' / 'experiments' / '04_autoresearch' / 'model.py'
DAY_US = 86_400_000_000
WORKERS = 8
DEV_ORDER = ('kettle', 'microwave', 'fridge', 'washing_machine', 'dishwasher')


def _fill(a):
    return (pd.Series(a).ffill(limit=v1.FFILL_LIMIT).fillna(0.0)
            .to_numpy(dtype='float32'))


def load_pool():
    return json.loads(POOL.read_text())


def pairs_of(pool, tag):
    return {d: pool['pairs'][tag + '/' + d] for d in DEV_ORDER
            if tag + '/' + d in pool['pairs']}


def make_plan(tag, pairs):
    ds, house = tag.split('/', 1)
    t0, t1 = v3._mains_bounds(ds, house)
    split = p4.split_of(ds, house, t0, t1)
    cmap = p4.canon_channels(ds, house)
    devs = [d for d in DEV_ORDER if d in pairs]
    chans = sorted({c for d in devs for c, _t, _p in cmap[d]})
    full = any(pairs[d].get('n_pre_window_d') == 'full' for d in devs)
    return {'tag': tag, 'ds': ds, 'house': house, 'split_us': int(split),
            'chans': chans, 'devs': devs,
            'thr': {d: float(pairs[d]['thr']) for d in devs},
            'ev_lo': int(split),
            'ev_hi': int(min(split + p4.EVAL_DAYS * DAY_US, t1)),
            'pre_lo': int(t0 if full
                          else max(t0, split - p4.PRE_PROBE_DAYS * DAY_US)),
            'pre_hi': int(split),
            'pre_tag': 'v4prefull' if full else 'v4pre180d',
            'full': full}


def _calib(ts, feed, mask, devs, thr, seed):
    '''v3.build_calibration_v3 over an explicit device set + boolean marks.'''
    rng = np.random.default_rng(seed)
    n = len(feed)
    jn = int(round(v2.PRESS_JITTER_S * 1e6 / v1.CADENCE_US))
    out = {}
    for dev in DEV_ORDER:                 # v1 order: RNG stream is fixed
        if dev not in devs:
            continue
        if dev == 'fridge':
            lo = int(rng.integers(0, n - v2.PASSIVE_FRIDGE_H * 3600 // 6))
            hi = lo + v2.PASSIVE_FRIDGE_H * 3600 // 6
            out[dev] = {'marks_us': np.empty((0, 2), dtype=np.int64),
                        'mains_seg': [feed[lo:hi]], 'passive': True}
            continue
        cyc = v2.cycles_from_mask(mask[dev], ts, dev)
        if not len(cyc):
            return None
        take = min(v2.K_CALIB, len(cyc))
        idx = sorted(rng.permutation(len(cyc))[:take].tolist())
        marks, segs = [], []
        roll_us = v2.PRE_ROLL_S * 1_000_000
        for i in idx:
            s_us = int(cyc['t_on_us'].iloc[i])
            e_us = int(cyc['t_off_us'].iloc[i])
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
        out[dev] = {'marks_us': np.asarray(marks, dtype=np.int64),
                    'mains_seg': segs, 'passive': False}
    return out


def _load_model():
    spec = importlib.util.spec_from_file_location('ar_v4', MODEL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['ar_v4'] = mod
    spec.loader.exec_module(mod)
    return mod


def run_job(job):
    plan, seed = job
    ds, house, tag = plan['ds'], plan['house'], plan['tag']
    pspan = v3.load_span(ds, house, plan['pre_lo'], plan['pre_hi'],
                         plan['pre_tag'], plan['chans'])
    espan = v3.load_span(ds, house, plan['ev_lo'], plan['ev_hi'],
                         'v4eval90d', plan['chans'])
    cmap = p4.canon_channels(ds, house)
    feed_p = _fill(pspan['mains'])
    mask = {}
    for d in plan['devs']:
        m, _u = p4._union_mask(cmap[d], pspan['devices'], smooth=False)
        mask[d] = m
    calib = _calib(pspan['ts_us'], feed_p, mask, plan['devs'], plan['thr'],
                   seed)
    if calib is None:
        return {'tag': tag, 'seed': seed, 'error': 'no calibration marks'}
    meta = {'devices': list(plan['devs']), 'thresholds': dict(plan['thr']),
            'device_class': {d: v2.DEVICE_CLASS[d] for d in plan['devs']},
            'cadence_s': 6, 'cadence_us': v1.CADENCE_US,
            'k_calib': v2.K_CALIB, 'tau_onset_s': dict(v2.TAU_ONSET_S),
            'merge_s': dict(v2.MERGE_S), 'duration_band': v2.DURATION_BAND,
            'press_jitter_s': v2.PRESS_JITTER_S, 'pre_roll_s': v2.PRE_ROLL_S,
            'split_us': plan['split_us'], 'seeds': [seed], 'bench': 'v4'}
    ctx = {'meta': meta, 'calib': calib,
           'pre': {'ts_us': pspan['ts_us'], 'mains': feed_p},
           'pretrain': v3.make_pretrain_ctx()}
    t0 = time.time()
    fn = _load_model().build_and_train(ctx)
    feed_e = _fill(espan['mains'])
    pred = fn(feed_e)
    f1 = {}
    for d in plan['devs']:
        gt_mask, _u = p4._union_mask(cmap[d], espan['devices'], smooth=False)
        gt = v2.cycles_from_mask(gt_mask, espan['ts_us'], d)
        w = np.nan_to_num(np.asarray(pred[d], dtype='float32'))
        pe = v2.cycles_from_mask(w > plan['thr'][d], espan['ts_us'], d)
        f1[d] = float(ev.score_episodes(pe, gt, v2.TAU_ONSET_S[d] * 1e6,
                                        v2.DURATION_BAND)['f1'])
    return {'tag': tag, 'seed': seed, 'f1': f1, 'secs': time.time() - t0}


def _dev_means(v):
    out = {}
    for d in DEV_ORDER:
        xs = [f for k, f in v.items() if k.endswith('/' + d)]
        if xs:
            out[d] = float(np.mean(xs))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--houses', default='')
    ap.add_argument('--seeds', default='')
    ap.add_argument('--workers', type=int, default=WORKERS)
    ap.add_argument('--holdout', action='store_true')
    args = ap.parse_args()
    if 'ALL_DEVICES' not in MODEL.read_text():
        raise SystemExit('model.py is missing the device-subset refactor '
                         '(ALL_DEVICES); re-apply it before running v4')
    pool = load_pool()
    tags = list(pool['holdout'] if args.holdout else pool['pool_houses'])
    if args.houses:
        want = set(args.houses.split(','))
        tags = [t for t in tags if t in want]
    seeds = ([int(s) for s in args.seeds.split(',')] if args.seeds
             else list(pool['seeds']))
    plans = []
    for tag in tags:
        if args.holdout:
            ds, house = tag.split('/', 1)
            pairs = p4.eval_house((ds, house)).get('pairs') or {}
        else:
            pairs = pairs_of(pool, tag)
        if pairs:
            plans.append(make_plan(tag, pairs))
    t0 = time.time()
    jobs = [(pl, s) for s in seeds for pl in plans]
    print('bench v4 ' + ('HOLDOUT' if args.holdout else 'pool') + ': '
          + str(len(plans)) + ' houses x ' + str(len(seeds)) + ' seeds = '
          + str(len(jobs)) + ' builds, ' + str(args.workers) + ' workers')
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(run_job, jobs):
            rows.append(r)
    per_seed = {}
    for r in rows:
        if 'error' in r:
            print('  SKIP ' + r['tag'] + ' seed ' + str(r['seed']) + ': '
                  + r['error'])
            continue
        per_seed.setdefault(r['seed'], {}).update(
            {r['tag'] + '/' + d: f for d, f in r['f1'].items()})
    seed_means = {s: float(np.mean(list(v.values())))
                  for s, v in per_seed.items() if v}
    sm = list(seed_means.values())
    primary = float(np.median(sm))
    p10 = float(np.percentile(sm, 10))
    dev_med = {d: float(np.median([m[d] for m in
                                   [_dev_means(v) for v in per_seed.values()]
                                   if d in m]))
               for d in DEV_ORDER}
    dev_med = {d: v for d, v in dev_med.items() if np.isfinite(v)}
    bal = [_dev_means(v) for v in per_seed.values()]
    balanced = float(np.median([np.mean(list(m.values()))
                                for m in bal if m]))
    h1 = [np.mean([f for k, f in v.items() if k.startswith('ukdale/house_1/')])
          for v in per_seed.values()
          if any(k.startswith('ukdale/house_1/') for k in v)]
    h1_med = float(np.median(h1)) if h1 else float('nan')
    npairs = len(next(iter(per_seed.values()))) if per_seed else 0
    print('---- scored ' + str(npairs) + ' pairs on ' + str(len(per_seed))
          + ' seeds in ' + ('%.0fs' % (time.time() - t0)))
    for d in DEV_ORDER:
        if d in dev_med:
            print('  %-16s F1 (median over seeds of the pair mean) = %.4f'
                  % (d, dev_med[d]))
    for s in sorted(seed_means):
        print('  seed %-5d mean_device_f1 = %.6f' % (s, seed_means[s]))
    print('  pair-mean          median=%.6f p10=%.6f' % (primary, p10))
    print('  device-balanced    median=%.6f' % balanced)
    print('  house_1 subset     median=%.6f' % h1_med)
    met = [('mean_device_f1', primary), ('mean_device_f1_p10', p10),
           ('device_balanced_mean', balanced), ('house_1_v4_mean', h1_med),
           ('v4_n_pairs', float(npairs)), ('v4_n_houses', float(len(plans)))]
    for d in DEV_ORDER:
        if d in dev_med:
            met.append(('median_' + d + '_f1', dev_med[d]))
    if args.holdout:
        met.append(('holdout_mean_f1', primary))
    summary = {'bench': 'v4', 'mode': 'holdout' if args.holdout else 'pool',
               'created': time.time(), 'seeds': list(seeds),
               'primary': primary, 'p10': p10,
               'device_balanced': balanced, 'house_1_v4_mean': h1_med,
               'n_pairs': int(npairs), 'n_houses': len(plans),
               'dev_med': dev_med, 'seed_means': seed_means}
    (ROOT / '.auto' / 'last_bench_v4.json').write_text(
        json.dumps(summary, indent=1, sort_keys=True))
    for name, val in met:
        print('METRIC ' + name + '=%.6f' % val)


if __name__ == '__main__':
    main()