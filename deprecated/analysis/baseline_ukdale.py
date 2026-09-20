#!/usr/bin/env python3
"""R1 baseline: M0 detector, deployment-parity protocol (plan section 3.0), multi-substrate.

Protocol: calibration = first 7.0 d wall-clock (signatures locked there);
reference = the remainder; the detector sees ONLY the aggregate (+ locked
signatures). Submeters are ground truth for the scoring harness only.

Substrates (--dataset):
  slice          UK-DALE house-1 70.66 d slice (custom aggregate; the reported R1)
  house1..house5 UK-DALE FULL download, data/raw/ukdale-full/house_N (REAL mains, 6 s)
  ampds2         AMPds2 Electricity_P.csv: WHE whole house + FGE/DWE/CWE apps, 60 s
  all            house1..house5 + ampds2

Detector M0 (F1 rung): x = agg - always_on; enter ON at x >= 0.5*p_k,
exit at x <= 0.25*p_k (hysteresis); keep episodes with dwell >= 2 samples.

Metrics/matching (plan sections 5.2/5.3): greedy one-to-one by onset,
|onset err| <= 2*dt, dwell ratio in [0.5, 2.0]; per-appliance P/R/F1,
onset/offset error, energy attribution, confusability, negative control
(false detections w.r.t. all archetypes), residual honesty.

Usage: uv run python3 analysis/baseline_ukdale.py --dataset all
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from eda_shelly import load_ukdale, on_mask, run_lengths

log = logging.getLogger(__name__)

ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UKDALE_FULL: str = os.path.join(ROOT, 'data', 'raw', 'ukdale-full')
AMPDS2_CSV: str = os.path.join(ROOT, 'data', 'raw', 'AMPds2', 'Electricity_P.csv')
CAL_DAYS: float = 7.0
GT_MIN_SAMP: int = 2
DWELL_RATIO: tuple[float, float] = (0.5, 2.0)

# archetype -> exact labels.dat names accepted (verbatim from the release)
ARCHETYPES: dict[str, tuple[str, ...]] = {
    'fridge': ('fridge', 'fridge_freezer', 'freezer'),
    'dish_washer': ('dishwasher', 'dish_washer'),
    'washing_machine': ('washing_machine', 'washer_dryer', 'washing_machine_microwave_breadmaker'),
    'kettle': ('kettle', 'kettle_radio'),
}
AMPDS2_MAP: dict[str, str] = {'fridge': 'FGE', 'dish_washer': 'DWE', 'washing_machine': 'CWE'}


# ---------------------------------------------------------------- loading

def read_dat(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Read one UK-DALE .dat (unix seconds, watts) as int64/float64 numpy arrays."""
    a = pd.read_csv(path, sep=' ', header=None, names=['ts', 'w']).values
    return a[:, 0].astype(np.int64), a[:, 1].astype(np.float64)


def align_to_grid(ts: np.ndarray, w: np.ndarray, grid_ts: np.ndarray, dt_s: float) -> np.ndarray:
    """Nearest-sample alignment; samples farther than dt/2 -> 0.0 (no data = OFF)."""
    idx = np.clip(np.searchsorted(ts, grid_ts), 0, len(ts) - 1)
    left = np.clip(idx - 1, 0, len(ts) - 1)
    pick = np.where(np.abs(ts[idx] - grid_ts) <= np.abs(ts[left] - grid_ts), idx, left)
    out = w[pick].copy()
    out[np.abs(ts[pick] - grid_ts) > dt_s / 2.0] = 0.0
    return out


def dense_start(ts: np.ndarray, dt_s: float = 6.0, need_days: float = 7.0,
                frac: float = 0.9) -> int | None:
    """First epoch where the NEXT need_days hold >= frac of the expected sample count.
    Houses roll out channels over months (h1 fridge +34 d, h2 apps +3 mo); the
    calibration window must sit where every archetype channel is actually dense."""
    need = int(need_days * 86400 / dt_s * frac)
    if len(ts) < need:
        return None
    span = int(need_days * 86400)
    lo = np.searchsorted(ts, ts - span)
    ok = np.flatnonzero((np.arange(len(ts)) - lo + 1) >= need)
    return int(ts[ok[0]]) if len(ok) else None


def load_house(n: int) -> tuple[pd.DataFrame, dict[str, tuple[np.ndarray, np.ndarray]],
                                 dict[str, str], pd.Timestamp]:
    """Load one UK-DALE full house: aggregate df, archetype channels, composite labels."""
    base = os.path.join(UKDALE_FULL, 'house_%d' % n)
    labels: dict[int, str] = {}
    with open(os.path.join(base, 'labels.dat')) as f:
        for line in f:
            parts = line.split(None, 1)
            if len(parts) == 2:
                labels[int(parts[0])] = parts[1].strip()
    agg_ts, agg_w = read_dat(os.path.join(base, 'channel_1.dat'))
    raw: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    comp: dict[str, str] = {}
    for arch, names in ARCHETYPES.items():
        for ch, lab in sorted(labels.items()):
            if lab in names:
                ts, w = read_dat(os.path.join(base, 'channel_%d.dat' % ch))
                raw[arch] = (ts, w)
                if lab != arch:
                    comp[arch] = lab
                break
    # plan 3.1: truncate to the common time span before anything else.
    starts = [dense_start(agg_ts)] + [dense_start(t) for t, _ in raw.values()]
    starts = [s for s in starts if s is not None]
    common = max(starts) if starts else int(agg_ts[0])
    m = agg_ts >= common
    agg_ts, agg_w = agg_ts[m], agg_w[m]
    grid = agg_ts
    df = pd.DataFrame({'ts': pd.to_datetime(grid, unit='s'), 'power': agg_w})
    apps = {k: align_to_grid(t, w, grid, 6.0) for k, (t, w) in raw.items()}
    return df, apps, comp, pd.to_datetime(common, unit='s')


def load_ampds2() -> tuple[pd.DataFrame, dict[str, np.ndarray], dict[str, str]]:
    """Load the AMPds2 60 s substrate: WHE aggregate + the three archetype columns."""
    df = pd.read_csv(AMPDS2_CSV)
    grid = df['UNIX_TS'].values.astype(np.int64)
    out = pd.DataFrame({'ts': pd.to_datetime(grid, unit='s'), 'power': df['WHE'].values.astype(float)})
    apps = {arch: df[col].values.astype(float) for arch, col in AMPDS2_MAP.items()}
    return out, apps, {}


# ---------------------------------------------------------------- protocol core

def wall_split(df: pd.DataFrame, cal_days: float) -> int:
    """Row index of the wall-clock calibration/reference boundary."""
    t0 = df.ts.values[0]
    return int(np.searchsorted(df.ts.values, t0 + np.timedelta64(int(cal_days * 86400), 's')))


def calibrate(df: pd.DataFrame, apps: dict[str, np.ndarray], names: Sequence[str],
              n_cal: int) -> dict[str, Any]:
    """Lock signatures on the calibration window only (deployment parity)."""
    agg_cal = df.power.values[:n_cal]
    day = df.ts.dt.date.values[:n_cal]
    daily_p10 = [np.percentile(agg_cal[day == d], 10) for d in sorted(set(day))]
    sig: dict[str, Any] = {'always_on_W': float(np.median(daily_p10))}
    for k in names:
        ap = apps[k][:n_cal]
        m = on_mask(ap)
        st, ln = run_lengths(m)
        keep = ln >= GT_MIN_SAMP
        on_p = ap[m]
        sig[k] = {
            'on_W': float(np.median(on_p)) if len(on_p) else 0.0,
            'on_p10_W': float(np.percentile(on_p, 10)) if len(on_p) else 0.0,
            'n_cal_episodes': int(keep.sum()),
            'energy_share_pct': round(100 * float(ap.sum()) / max(float(agg_cal.sum()), 1.0), 1),
        }
    return sig


def detect_sig(x: np.ndarray, p: float, min_samp: int) -> list[tuple[int, int]]:
    """Vectorized M0 hysteresis for one signature; returns [(start, len), ...]."""
    if p <= 0:
        return []
    hi, lo = 0.5 * p, 0.25 * p
    xp = np.empty_like(x)
    xp[0] = x[0]
    xp[1:] = x[:-1]
    rises = np.flatnonzero((x >= hi) & (xp < hi))
    falls = np.flatnonzero((x <= lo) & (xp > lo))
    ev = np.zeros(len(rises) + len(falls), dtype=[('i', np.int64), ('t', np.int8)])
    ev['i'][:len(rises)] = rises
    ev['t'][:len(rises)] = 1
    ev['i'][len(rises):] = falls
    ev['t'][len(rises):] = -1
    ev.sort(order='i')
    eps: list[tuple[int, int]] = []
    state = bool(x[0] >= hi)
    start = 0
    for i, t in zip(ev['i'], ev['t']):
        if not state and t == 1:
            state, start = True, int(i)
        elif state and t == -1:
            state = False
            if int(i) - start >= min_samp:
                eps.append((start, int(i) - start))
    if state and len(x) - start >= min_samp:
        eps.append((start, len(x) - start))
    return eps


def match(gt: list[tuple[int, int]], det: list[tuple[int, int]], tol_s: float,
          dt_s: float) -> list[tuple[int, int, float, float]]:
    """Greedy one-to-one by onset; |onset err| <= tol_s, dwell ratio in [0.5, 2]."""
    if not gt or not det:
        return []
    gs = np.array([g[0] for g in gt])
    order = np.argsort(gs)
    gs_sorted = gs[order]
    cands: list[tuple[float, int, int, int, float, float]] = []
    for di, d in enumerate(det):
        lo = np.searchsorted(gs_sorted, d[0] - tol_s, 'left')
        hi = np.searchsorted(gs_sorted, d[0] + tol_s + 1, 'left')
        for oi in range(lo, hi):
            gi = int(order[oi])
            g = gt[gi]
            err = (g[0] - d[0]) * dt_s
            if abs(err) > tol_s:
                continue
            ratio = g[1] / max(d[1], 1)
            if DWELL_RATIO[0] <= ratio <= DWELL_RATIO[1]:
                cands.append((abs(err), g[0], gi, di, err, (g[1] - d[1]) * dt_s))
    cands.sort(key=lambda c: (c[0], c[1]))
    used_g, used_d, matched = set(), set(), []
    for _, _, gi, di, err, off in cands:
        if gi in used_g or di in used_d:
            continue
        used_g.add(gi)
        used_d.add(di)
        matched.append((gi, di, err, off))
    return matched


def overlap_hits(dets: list[tuple[int, int]], gt_eps: list[tuple[int, int]]) -> list[tuple[int, ...]]:
    """For each det interval, the gt indices it overlaps (gt may be huge)."""
    if not gt_eps or not dets:
        return [()] * len(dets)
    gs = np.array([g[0] for g in gt_eps])
    gl = np.array([g[1] for g in gt_eps])
    order = np.argsort(gs)
    gs, gl = gs[order], gl[order]
    max_len = int(gl.max())
    out: list[tuple[int, ...]] = []
    for s, l in dets:
        lo = np.searchsorted(gs, s - max_len, 'right')
        hi = np.searchsorted(gs, s + l, 'left')
        out.append(tuple(int(order[k]) for k in range(lo, hi)
                         if gs[k] < s + l and gs[k] + gl[k] > s))
    return out


def score_run(df: pd.DataFrame, apps: dict[str, np.ndarray], names: Sequence[str], dt_s: float,
              out_dir: str, title: str, notes: Sequence[str] = ()) -> dict[str, Any]:
    """Run the full protocol on one substrate and write metrics.json + report.md."""
    os.makedirs(out_dir, exist_ok=True)
    n = len(df)
    n_cal = wall_split(df, CAL_DAYS)
    ref_wall_d = float((df.ts.values[-1] - df.ts.values[0]) / np.timedelta64(1, 'D')) - CAL_DAYS
    ref_row_d = (n - n_cal) * dt_s / 86400.0
    log.info('%s: %d rows, cal %d rows, ref %.1f d wall / %.2f d rows' %
             (title, n, n_cal, ref_wall_d, ref_row_d))

    sig = calibrate(df, apps, names, n_cal)
    log.info('always-on floor: %.0f W' % sig['always_on_W'])
    for k in names:
        log.info('  %-28s on=%.0f W  cal episodes=%d  share=%.1f%%' %
                 (k, sig[k]['on_W'], sig[k]['n_cal_episodes'], sig[k]['energy_share_pct']))

    sl = slice(n_cal, n)
    agg = df.power.values[sl]
    x = agg - sig['always_on_W']
    gt = {k: episodes(on_mask(apps[k][sl]), GT_MIN_SAMP) for k in names}
    det = {k: detect_sig(x, sig[k]['on_W'], GT_MIN_SAMP) for k in names}
    tol_s = 2 * dt_s

    res: dict[str, Any] = {
        'protocol': {'title': title, 'calibration_days': CAL_DAYS,
                     'reference_days_wall': round(ref_wall_d, 2),
                     'reference_days_rows': round(ref_row_d, 2),
                     'dt_s': dt_s, 'always_on_W': sig['always_on_W'],
                     'detector': 'M0 threshold+hysteresis+dwell',
                     'notes': list(notes)},
        'signatures': {k: sig[k] for k in names},
        'per_appliance': {}, 'confusability': {}, 'negative_control': {}, 'residual': {},
    }

    for k in names:
        matched = match(gt[k], det[k], tol_s, dt_s)
        ngt, ndet, nmatch = len(gt[k]), len(det[k]), len(matched)
        prec = nmatch / ndet if ndet else 0.0
        rec = nmatch / ngt if ngt else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        on_err = [m[2] for m in matched]
        off_err = [m[3] for m in matched]
        ratios: list[float] = []
        for gi, di, _, _ in matched:
            gs_, gl_ = gt[k][gi]
            g_energy = float(np.sum(apps[k][n_cal + gs_: n_cal + gs_ + gl_])) * dt_s / 3600.0
            est = sig[k]['on_W'] * det[k][di][1] * dt_s / 3600.0
            ratios.append(est / g_energy if g_energy > 0 else np.nan)
        res['per_appliance'][k] = {
            'gt_episodes': ngt, 'det_episodes': ndet, 'matched': nmatch,
            'precision': round(prec, 3), 'recall': round(rec, 3), 'f1': round(f1, 3),
            'onset_err_s_p50': round(float(np.median(np.abs(on_err))), 1) if on_err else None,
            'onset_err_s_p90': round(float(np.percentile(np.abs(on_err), 90)), 1) if on_err else None,
            'offset_err_s_p50': round(float(np.median(np.abs(off_err))), 1) if off_err else None,
            'energy_est_over_gt_p50': round(float(np.nanmedian(ratios)), 2) if ratios else None,
            'gt_energy_kwh': round(float(np.sum(apps[k][sl]) * dt_s) / 3.6e6, 1),
        }

    # confusability: for GT appliance k, how many of its GT episodes are overlapped
    # by detector o != k (GT-centric per plan 5.3: "which detector claimed it").
    conf: dict[str, dict[str, int]] = {}
    for k in names:
        conf[k] = {}
        for o in names:
            if o == k:
                continue
            c = sum(1 for h in overlap_hits(gt[k], det[o]) if h)
            if c:
                conf[k][o] = c
    res['confusability'] = {k: v for k, v in conf.items() if v}

    # negative control: detections overlapping no archetype GT of ANY appliance
    all_gt_eps = sorted(e for k in names for e in gt[k])
    fp_count = 0
    fp_energy = 0.0
    total_det = 0
    for k in names:
        for e, h in zip(det[k], overlap_hits(det[k], all_gt_eps)):
            total_det += 1
            if not h:
                fp_count += 1
                fp_energy += sig[k]['on_W'] * e[1] * dt_s / 3600.0
    res['negative_control'] = {
        'detections_total': total_det, 'false_positives': fp_count,
        'fp_rate_pct': round(100 * fp_count / max(total_det, 1), 1),
        'fp_energy_kwh': round(fp_energy / 1000.0, 2),
    }

    cover = np.zeros(len(agg), bool)
    for k in names:
        for s, l in det[k]:
            cover[s: s + l] = True
    above = np.maximum(x, 0)
    res['residual'] = {
        'above_always_on_kwh': round(float(above.sum() * dt_s) / 3.6e6, 1),
        'covered_pct_of_above_on': round(100 * float(above[cover].sum() / max(above.sum(), 1)), 1),
        'residual_kwh': round(float(above[~cover].sum() * dt_s) / 3.6e6, 1),
    }

    with open(os.path.join(out_dir, 'metrics.json'), 'w') as f:
        json.dump(res, f, indent=1)

    L = ['# R1 baseline: ' + title, '',
         'Calibration %.1f d / reference %.1f d wall (%.2f d of sampled rows). Detector sees only the aggregate.' % (CAL_DAYS, ref_wall_d, ref_row_d),
         'Always-on floor %.0f W. Matching: greedy one-to-one, onset tol %d s, dwell ratio 0.5-2.0, min dwell %d samples.' % (sig['always_on_W'], tol_s, GT_MIN_SAMP),
         '']
    if notes:
        L += ['Notes: ' + ' | '.join(notes), '']
    L += ['| appliance | GT ep | det ep | P | R | F1 | onset err p50/p90 s | est/GT energy | GT kWh |',
          '|---|---|---|---|---|---|---|---|---|']
    for k in names:
        r = res['per_appliance'][k]
        L.append('| %s | %d | %d | %.2f | %.2f | %.2f | %s / %s | %.2f | %.1f |' %
                 (k, r['gt_episodes'], r['det_episodes'], r['precision'], r['recall'], r['f1'],
                  r['onset_err_s_p50'], r['onset_err_s_p90'],
                  r['energy_est_over_gt_p50'] if r['energy_est_over_gt_p50'] is not None else 0.0,
                  r['gt_energy_kwh']))
    nc = res['negative_control']
    L += ['', 'Negative control: %d/%d detections false (%.1f%%), %.2f kWh spurious.' %
          (nc['false_positives'], nc['detections_total'], nc['fp_rate_pct'], nc['fp_energy_kwh'])]
    rs = res['residual']
    L += ['Residual honesty: %.1f kWh above always-on; %.1f%% covered; %.1f kWh residual.' %
          (rs['above_always_on_kwh'], rs['covered_pct_of_above_on'], rs['residual_kwh'])]
    L += ['', '## Confusability (GT episodes overlapped by another signature)', '',
          '| GT vs claimed | counts |', '|---|---|']
    for k, cf in res['confusability'].items():
        if cf:
            L.append('| %s | %s |' % (k, ', '.join('%s %d' % (a, b) for a, b in sorted(cf.items(), key=lambda t: -t[1]))))
    with open(os.path.join(out_dir, 'report.md'), 'w') as f:
        f.write("\n".join(L) + "\n")
    log.info('wrote %s' % out_dir)
    return res


def episodes(mask: np.ndarray, min_samp: int) -> list[tuple[int, int]]:
    """[(start, len), ...] runs of True with length >= min_samp."""
    st, ln = run_lengths(mask)
    keep = ln >= min_samp
    return list(zip(st[keep], ln[keep]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', default='slice',
                    choices=['slice', 'house1', 'house2', 'house3', 'house4', 'house5', 'ampds2', 'all'])
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    runs: list[tuple[str, str, float]] = []
    if args.dataset == 'slice':
        runs.append(('slice', 'UK-DALE house-1 70.66 d slice (custom aggregate)', 6.0))
    elif args.dataset == 'ampds2':
        runs.append(('ampds2', 'AMPds2 single house 730 d (WHE + FGE/DWE/CWE)', 60.0))
    elif args.dataset.startswith('house'):
        runs.append((args.dataset, 'UK-DALE FULL ' + args.dataset + ' (real mains, 6 s)', 6.0))
    else:
        runs = [('house%d' % i, 'UK-DALE FULL house%d (real mains, 6 s)' % i, 6.0) for i in range(1, 6)]
        runs.append(('ampds2', 'AMPds2 single house 730 d (WHE + FGE/DWE/CWE)', 60.0))

    for name, title, dt_s in runs:
        out_dir = args.out or os.path.join(ROOT, 'baseline_runs', name)
        log.info('=== ' + name)
        if name == 'slice':
            df, apps = load_ukdale()
            names = ['fridge', 'dish_washer', 'kettle', 'washing_machine']
            notes = ['channel_1 = custom aggregate = sum of ch2-6 (no real residual)']
        elif name == 'ampds2':
            df, apps, comp = load_ampds2()
            names = list(AMPDS2_MAP)
            notes = ['60 s rung: onset tol 120 s, min dwell 120 s',
                     'no kettle class in AMPds2; FRE = furnace fan, not used']
        else:
            df, apps, comp, cal_start = load_house(int(name[-1]))
            names = [k for k in ARCHETYPES if k in apps]
            notes = ['channel_1 = real aggregate mains',
                     'calibration starts %s: first 7-d window where aggregate + all archetype channels are dense (house rollout artifact)' % cal_start]
            for k in names:
                if k in comp:
                    notes.append('house label for %s is composite: %s' % (k, comp[k]))
            if not names:
                log.info('no archetype channels; skipping')
                continue
        score_run(df, apps, names, dt_s, out_dir, title, notes)


if __name__ == '__main__':
    from wattwiser import setup_logging

    setup_logging()
    main()
