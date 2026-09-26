"""FROZEN benchmark for the WattWiser NILM autoresearch loop.

Protocol is frozen: see .auto/prompt.md. Iterations may only change
src/experiments/04_autoresearch/model.py. Changing this file, measure.sh or
checks.sh invalidates the run log.
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
sys.path.insert(0, str(ROOT / 'src'))

from wattwiser.experiments import evaluation as ev  # noqa: E402

DATA = ROOT / 'data' / 'gold' / 'ukdale'
CACHE_DIR = ROOT / '.auto' / 'cache'
OUT_PATH = ROOT / '.auto' / 'last_bench.json'

# ------------------------------------------------------------ frozen protocol
TARGET_HOUSE = "house_1"
DEVICES = ["kettle", "microwave", "fridge", "washing_machine", "dishwasher"]
# gold thresholds.json ukdale/house_1 (half_p50) - snapshot; asserted vs file
THR = {"kettle": 1173.0, "microwave": 762.0, "fridge": 44.5,
       "washing_machine": 90.0, "dishwasher": 60.5}
SPLIT_US = 1380585600000000   # house_1 splits.csv contract (2013-10-01)
EVAL_DAYS = 30
CADENCE = '6s'
CADENCE_US = 6_000_000
WINDOW = 128
STRIDE = 32
K_CALIB = 5
CALIB_SEED = 2026
SOURCE_HOUSES = ('house_2', 'house_5')
SOURCE_VAL_FRAC = 0.2
TAU_ONSET_US = 12_000_000     # fhmm FROZEN tau_native_s = 2x cadence
DURATION_BAND = (1.0 / 3.0, 3.0)  # fhmm FROZEN dwell_band
MIN_EP_SAMPLES = 2
FFILL_LIMIT = 10
MODEL_PATH = ROOT / 'src' / 'experiments' / '04_autoresearch' / 'model.py'


def check_threshold_file() -> None:
    raw = json.loads((ROOT / 'data' / 'gold' / 'thresholds.json').read_text())
    h1 = raw.get('ukdale', raw)['house_1']
    for dev in DEVICES:
        got = float(h1[dev]['thr_on_W'])
        if abs(got - THR[dev]) > 1e-9:
            raise SystemExit('protocol drift: gold threshold changed for ' + dev)


def _resample(path: Path) -> pd.Series:
    df = pd.read_parquet(path, columns=['ts_us', 'w'])
    idx = pd.to_datetime(df['ts_us'].to_numpy(), unit='us')
    s = pd.Series(df['w'].to_numpy(dtype='float64'), index=idx).sort_index()
    return s.resample(CADENCE).mean()


def _index_us(idx: pd.DatetimeIndex) -> np.ndarray:
    vals = np.asarray(idx.astype('int64'), dtype=np.int64)
    unit = getattr(idx, 'unit', 'ns')
    if unit == 'us':
        return vals
    if unit == 'ns':
        return vals // 1000
    if unit == 'ms':
        return vals * 1000
    if unit == 's':
        return vals * 1_000_000
    raise ValueError('unsupported datetime resolution: ' + str(unit))


def load_house(house: str, lo_us, hi_us, tag: str) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / (house + '_' + tag + '.npz')
    names = ['mains'] + DEVICES
    files = [DATA / house / (n + '.parquet') for n in names]
    sig = ';'.join(f.name + ':' + str(int(f.stat().st_mtime)) for f in files)
    if cache.exists():
        z = np.load(cache)
        if str(z['sig']) == sig:
            return {'ts_us': z['ts_us'], 'mains': z['mains'],
                    'devices': {n: z[n] for n in DEVICES}}
    mains_s = _resample(files[0])
    idx = mains_s.index
    ts_full = _index_us(idx)
    mains_full = mains_s.to_numpy(dtype='float32')
    keep = np.ones(len(ts_full), dtype=bool)
    if lo_us is not None:
        keep &= ts_full >= lo_us
    if hi_us is not None:
        keep &= ts_full < hi_us
    devices = {}
    for n in DEVICES:
        s = _resample(DATA / house / (n + '.parquet'))
        devices[n] = s.reindex(idx).to_numpy(dtype='float32')[keep]
    out = {'ts_us': ts_full[keep], 'mains': mains_full[keep], 'devices': devices}
    np.savez(cache, sig=np.array(sig), ts_us=out['ts_us'], mains=out['mains'],
             **devices)
    print(f'   built cache {cache.name}: {int(keep.sum()):,} samples')
    return out


def runs_of(on: np.ndarray) -> list:
    d = np.diff(np.concatenate([[0], on.astype(np.int8), [0]]))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return list(zip(starts.tolist(), ends.tolist()))


def episodes_from_mask(on: np.ndarray, ts_us: np.ndarray) -> pd.DataFrame:
    pairs = []
    for a, b in runs_of(on):
        if b - a >= MIN_EP_SAMPLES:
            pairs.append((int(ts_us[a]), int(ts_us[b - 1]) + CADENCE_US))
    if not pairs:
        return pd.DataFrame({'t_on_us': np.empty(0, np.int64),
                             't_off_us': np.empty(0, np.int64)})
    return pd.DataFrame(np.asarray(pairs, dtype=np.int64),
                        columns=['t_on_us', 't_off_us'])


def build_calibration(pre: dict) -> dict:
    rng = np.random.default_rng(CALIB_SEED)
    # calibration windows use the same gap-filled feed the model gets at
    # inference (ffill limit FFILL_LIMIT, remainder 0)
    feed = (pd.Series(pre['mains']).ffill(limit=FFILL_LIMIT).fillna(0.0)
            .to_numpy(dtype='float32'))
    n = len(feed)
    half = WINDOW // 2
    calib = {}
    for dev in DEVICES:
        w = pre['devices'][dev]
        on = (np.nan_to_num(w, nan=0.0) > THR[dev]) & ~np.isnan(w)
        sessions = [(a, b) for a, b in runs_of(on) if b - a >= MIN_EP_SAMPLES]
        ok = []
        for a, b in sessions:
            c = (a + b) // 2
            lo, hi = c - half, c - half + WINDOW
            if lo < 0 or hi > n:
                continue
            if np.isnan(feed[lo:hi]).any():
                continue
            ok.append((lo, hi))
        if not ok:
            raise SystemExit('no valid calibration sessions found for ' + dev)
        take = min(K_CALIB, len(ok))
        sel = sorted(rng.permutation(len(ok))[:take].tolist())
        wins = [ok[i] for i in sel]
        calib[dev] = {
            'mains_win': np.stack([feed[lo:hi] for lo, hi in wins]).astype('float32'),
            'device_win': np.stack([w[lo:hi] for lo, hi in wins]).astype('float32'),
        }
        print(f'   calib {dev}: {take} sessions of {len(ok)} available')
    return calib


def run_score(evh: dict, predict, t_start: float, config: dict,
               prefix: str = '') -> dict:
    ts_eval = evh['ts_us']
    mains_raw = evh['mains']
    filled = (pd.Series(mains_raw).ffill(limit=FFILL_LIMIT).fillna(0.0)
              .to_numpy(dtype='float32'))
    label = 'predicting eval span ...' if not prefix else \
        'predicting expanded eval span ...'
    print(label)
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
        gt_eps = episodes_from_mask((gt_w > THR[dev]) & valid, ts_eval)
        pred_eps = episodes_from_mask(pred[dev] > THR[dev], ts_eval)
        sc = ev.score_episodes(pred_eps, gt_eps, TAU_ONSET_US, DURATION_BAND)
        nm = ev.nmae_for_device(ts_eval, pred[dev].astype('float64'),
                                ts_eval[valid], gt_w[valid].astype('float64'),
                                np.nan_to_num(mains_raw, nan=0.0).astype('float64'))
        per[dev] = {'n_gt': sc['n_gt'], 'n_pred': sc['n_pred'],
                    'n_matched': sc['n_matched'], 'precision': sc['precision'],
                    'recall': sc['recall'], 'f1': sc['f1'],
                    'mae_w': nm['mae_w'], 'nmae': nm['nmae'],
                    'n_common': nm['n_common'],
                    'nonnull_frac': float(valid.mean())}
        pred_energy_wh += float(np.sum(pred[dev], dtype='float64')) * 6.0 / 3600.0
        gt_energy_wh += float(np.nansum(gt_w, dtype='float64')) * 6.0 / 3600.0

    f1s = {d: per[d]['f1'] for d in DEVICES}
    maes = {d: per[d]['mae_w'] for d in DEVICES}
    nmaes = {d: per[d]['nmae'] for d in DEVICES}
    min_dev = min(f1s, key=f1s.get)
    pooled = ev.pool_scores([per[d] for d in DEVICES])

    print('')
    print('device            n_gt   n_pred  match     P      R      F1     MAE_W   nMAE')
    for d in DEVICES:
        s = per[d]
        print(f"{d:16s} {s['n_gt']:6d} {s['n_pred']:7d} {s['n_matched']:6d}   "
              f"{s['precision']:.3f}  {s['recall']:.3f}  {s['f1']:.3f}   "
              f"{s['mae_w']:7.1f}  {s['nmae']:.4f}")
    print(f"pooled: n_gt={pooled['n_gt']} n_pred={pooled['n_pred']} "
          f"n_matched={pooled['n_matched']} F1={pooled['f1']:.3f}")
    print(f"coverage: pred={pred_energy_wh / agg_energy_wh:.3f} "
          f"true={gt_energy_wh / agg_energy_wh:.3f} of aggregate")

    result = {'config': config, 'devices': per,
              'min_device_f1': float(f1s[min_dev]),
              'min_device': min_dev,
              'mean_device_f1': float(np.mean(list(f1s.values()))),
              'pooled_episode_f1': float(pooled['f1']),
              'mean_mae_w': float(np.mean(list(maes.values()))),
              'worst_mae_w': float(np.max(list(maes.values()))),
              'mean_nmae': float(np.mean(list(nmaes.values()))),
              'coverage_pred_share': pred_energy_wh / agg_energy_wh,
              'coverage_true_share': gt_energy_wh / agg_energy_wh,
              'elapsed_s': time.time() - t_start}

    print('')
    print(f"METRIC {prefix}min_device_f1={result['min_device_f1']:.6f}")
    print(f"METRIC {prefix}mean_device_f1={result['mean_device_f1']:.6f}")
    print(f"METRIC {prefix}pooled_episode_f1={result['pooled_episode_f1']:.6f}")
    print(f"METRIC {prefix}mean_mae_w={result['mean_mae_w']:.4f}")
    print(f"METRIC {prefix}worst_mae_w={result['worst_mae_w']:.4f}")
    print(f"METRIC {prefix}mean_nmae={result['mean_nmae']:.6f}")
    print(f"METRIC {prefix}coverage_pred_share={result['coverage_pred_share']:.6f}")
    print(f"METRIC {prefix}coverage_true_share={result['coverage_true_share']:.6f}")
    print(f"METRIC {prefix}min_device_f1={result['min_device_f1']:.6f}")
    return result


def main() -> None:
    t_start = time.time()
    check_threshold_file()
    eval_hi = SPLIT_US + EVAL_DAYS * 86_400_000_000

    print('loading data (cached under .auto/cache) ...')
    pre = load_house(TARGET_HOUSE, None, SPLIT_US, 'pre')
    evh = load_house(TARGET_HOUSE, SPLIT_US, eval_hi, 'eval')
    pretrain = {}
    for house in SOURCE_HOUSES:
        full = load_house(house, None, None, 'full')
        cut = int(len(full['ts_us']) * (1.0 - SOURCE_VAL_FRAC))
        pretrain[house] = {
            'train': {'mains': full['mains'][:cut],
                      'devices': {d: full['devices'][d][:cut] for d in DEVICES}},
            'val': {'mains': full['mains'][cut:],
                    'devices': {dev: full['devices'][dev][cut:] for dev in DEVICES}},
        }

    ts_eval = evh['ts_us']
    mains_raw = evh['mains']
    filled = (pd.Series(mains_raw).ffill(limit=FFILL_LIMIT).fillna(0.0)
              .to_numpy(dtype='float32'))

    ctx = {
        'meta': {'devices': list(DEVICES), 'thresholds': dict(THR),
                 'cadence_s': 6, 'window': WINDOW, 'stride': STRIDE,
                 'source_val_frac': SOURCE_VAL_FRAC, 'k_calib': K_CALIB,
                 'split_us': SPLIT_US, 'eval_span_us': [SPLIT_US, eval_hi],
                 'tau_onset_us': TAU_ONSET_US, 'duration_band': DURATION_BAND},
        'pretrain': pretrain,
        'calib': build_calibration(pre),
        'eval': {'ts_us': ts_eval, 'mains': filled},
    }

    print('building + training model (src/experiments/04_autoresearch/model.py) ...')
    spec = importlib.util.spec_from_file_location('ar_model', MODEL_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['ar_model'] = mod
    spec.loader.exec_module(mod)
    predict = mod.build_and_train(ctx)

    config = {'target_house': TARGET_HOUSE, 'devices': DEVICES,
              'thr_on_W': THR, 'split_us': SPLIT_US, 'eval_days': EVAL_DAYS,
              'cadence': CADENCE, 'window': WINDOW, 'stride': STRIDE,
              'k_calib': K_CALIB, 'tau_onset_us': TAU_ONSET_US,
              'duration_band': DURATION_BAND,
              'source_houses': list(SOURCE_HOUSES)}

    result = run_score(evh, predict, t_start, config)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=1))

    # expanded-eval confirmation: same trained model re-scored over the full
    # post-split house_1 span (or 90d/365d). The loop's primary trend metric
    # stays the frozen 30-day slice; expanded numbers confirm before declaring
    # a big improvement final.
    mode = os.environ.get('BENCH_EVAL', '30d')
    if mode not in ('30d', '90d', '365d', 'full'):
        raise SystemExit('BENCH_EVAL must be 30d|90d|365d|full, got ' + mode)
    if mode != '30d':
        days = {'90d': 90, '365d': 365, 'full': None}[mode]
        hi = None if days is None else SPLIT_US + days * 86_400_000_000
        evx = load_house(TARGET_HOUSE, SPLIT_US, hi, 'eval' + mode)
        print('')
        print('EXPANDED eval (BENCH_EVAL=' + mode + ') ...')
        rex = run_score(evx, predict, t_start, config, prefix='full_')
        result['expanded'] = {'mode': mode, 'devices': rex['devices'],
                              'min_device_f1': rex['min_device_f1'],
                              'mean_device_f1': rex['mean_device_f1'],
                              'worst_mae_w': rex['worst_mae_w'],
                              'mean_nmae': rex['mean_nmae']}
        OUT_PATH.write_text(json.dumps(result, indent=1))
        print(f"METRIC min_device_f1={result['min_device_f1']:.6f}")
    print(f"elapsed {result['elapsed_s']:.0f}s -> {OUT_PATH}")


if __name__ == '__main__':
    main()