"""Device-wide enrollment validation, F2 disaggregation, and the weak-class experiment sweep.

Extends the R1 protocol (baseline_ukdale.py) from 4 archetypes to EVERY labeled channel:
  - context builder: streams every channel once, caches signatures + GT episodes
    (gap-merge variants 0 / 12 s / 600 s) + per-device fallback enrollment;
  - experiment registry E00-E19: plan 3.2-3.4 features M0 lacked (gap merge, dwell
    prior, signature statistic, local baseline, relative threshold, hysteresis) and
    the F2 event-then-classify family;
  - every experiment writes baseline_runs/experiments/E##_slug/{report.md,metrics.json}.

Usage:
  uv run python3 analysis/device_campaign.py --build
  uv run python3 analysis/device_campaign.py --enrollment
  uv run python3 analysis/device_campaign.py --run-experiments
"""
import argparse
import json
import os
import pickle
import re
import time

import numpy as np
import pandas as pd
from baseline_ukdale import (
    AMPDS2_CSV,
    CAL_DAYS,
    GT_MIN_SAMP,
    ROOT,
    UKDALE_FULL,
    align_to_grid,
    dense_start,
    episodes,
    log,
    match,
    overlap_hits,
    read_dat,
)
from eda_shelly import load_ukdale, on_mask, run_lengths

CACHE = os.path.join(ROOT, ".scratch", "exp_cache")
OUT = os.path.join(ROOT, "baseline_runs", "experiments")
ENROLL_OUT = os.path.join(ROOT, "baseline_runs", "enrollment")

AMPDS2_AGG = "WHE"
AMPDS2_LABELS = {
    "FGE": "fridge", "DWE": "dish_washer", "CWE": "washing_machine", "CDE": "clothes_dryer",
    "DNE": "clothes_dryer_2", "FRE": "furnace_fan", "HPE": "heat_pump", "WOE": "oven",
    "TVE": "tv_theatre", "B1E": "bedroom_1", "B2E": "bedroom_2", "BME": "basement",
    "EBE": "workbench", "EQE": "equipment", "GRE": "garage", "HTE": "hot_water",
    "MHE": "mains_panel_sub", "OFE": "office", "OUE": "outside_utility",
    "RSE": "receptacles_small", "UTE": "utility", "UNE": "unknown_1",
}


# ----------------------------------------------------------------- episode helpers

def merge_eps(eps, gap_samp):
    """Merge episodes separated by <= gap_samp samples (plan 3.2 gap merge)."""
    if gap_samp <= 0 or not eps:
        return list(eps)
    out = [list(eps[0])]
    for s, l in eps[1:]:
        if s - (out[-1][0] + out[-1][1]) <= gap_samp:
            out[-1][1] = max(out[-1][1], s + l - out[-1][0])
        else:
            out.append([s, l])
    return [(int(e[0]), int(e[1])) for e in out]


def detect_eps(x, hi, lo, min_samp, gap_samp=0, dt_s=6.0):
    """Hysteresis detector with configurable enter/exit fractions."""
    if hi <= 0:
        return []
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
    eps = []
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
    return merge_eps(eps, int(round(gap_samp / dt_s)))


def rolling_median(x, win):
    if win <= 1 or len(x) <= win:
        return np.zeros_like(x)
    return pd.Series(x).rolling(win, center=True, min_periods=1).median().values


def score_eps(gt, det, dt_s):
    tol_s = 2 * dt_s
    m = match(gt, det, tol_s, dt_s)
    p = len(m) / len(det) if det else 0.0
    r = len(m) / len(gt) if gt else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {'gt': len(gt), 'det': len(det), 'matched': len(m),
            'P': round(p, 3), 'R': round(r, 3), 'F1': round(f1, 3)}


def is_weak(name):
    return bool(re.search(r'dish|wash', name, re.I)) or name in ('CWE', 'DWE', 'CDE', 'DNE')


def is_kettle(name):
    return 'kettle' in name.lower()


def is_fridge(name):
    return bool(re.search(r'fridge|freezer', name, re.I)) or name in ('FGE',)


# ----------------------------------------------------------------- context builder

def _sig_from_arr(arr, dt_s):
    m = on_mask(arr)
    st, ln = run_lengths(m)
    keep = ln >= GT_MIN_SAMP
    lens = ln[keep] * dt_s
    on_p = arr[m]
    return {
        'on_W': float(np.median(on_p)) if len(on_p) else 0.0,
        'on_p25_W': float(np.percentile(on_p, 25)) if len(on_p) else 0.0,
        'on_p90_W': float(np.percentile(on_p, 90)) if len(on_p) else 0.0,
        'dwell_p10_s': float(np.percentile(lens, 10)) if len(lens) else 0.0,
        'dwell_p50_s': float(np.percentile(lens, 50)) if len(lens) else 0.0,
        'dwell_p90_s': float(np.percentile(lens, 90)) if len(lens) else 0.0,
        'n_cal_eps': int(keep.sum()),
        'cal_energy_kwh': round(float(arr.sum()) * dt_s / 3.6e6, 3),
    }


def _gt_variants(arr, dt_s):
    gt_raw = episodes(on_mask(arr), GT_MIN_SAMP)
    return {'gm0': gt_raw,
            'gm12': merge_eps(gt_raw, int(round(12 / dt_s))),
            'gm600': merge_eps(gt_raw, int(round(600 / dt_s)))}


def _house_daily_floor(agg, grid, dt_s, days):
    m = int(days * 86400 / dt_s)
    day = grid[:m] // 86400
    a = agg[:m]
    return float(np.median([np.percentile(a[day == d], 10) for d in sorted(set(day))]))


def n_cal_per(grid, i0, days):
    return int(np.searchsorted(grid, grid[i0] + int(days * 86400))) - i0


def build_house(n):
    """Stream every channel of a UK-DALE house once; cache signatures + GT episodes."""
    base = os.path.join(UKDALE_FULL, 'house_%d' % n)
    labels = {}
    with open(os.path.join(base, 'labels.dat')) as f:
        for line in f:
            parts = line.split(None, 1)
            if len(parts) == 2:
                labels[parts[0]] = parts[1].strip()
    agg_ts, agg_w = read_dat(os.path.join(base, 'channel_1.dat'))
    # common span exactly as R1: aggregate + weak/archetype-like channels
    arch_pat = re.compile(r'fridge|freezer|dish|wash|kettle', re.I)
    arch_ds = []
    ch_files = []
    for ch, lab in sorted(labels.items(), key=lambda t: int(t[0])):
        p = os.path.join(base, 'channel_%s.dat' % ch)
        if ch == '1' or lab == 'aggregate' or not os.path.exists(p):
            continue
        if os.path.getsize(p) < 1e6:
            continue
        ch_files.append((ch, lab, p))
        if arch_pat.search(lab):
            t, _ = read_dat(p)
            arch_ds.append(dense_start(t))
            del t
    ds_agg = dense_start(agg_ts)
    starts = [s for s in [ds_agg] + arch_ds if s is not None]
    common = max(starts) if starts else int(agg_ts[0])
    m = agg_ts >= common
    grid = agg_ts[m]
    agg = agg_w[m].astype(np.float64)
    N = len(grid)
    dt_s = 6.0
    n_cal = int(np.searchsorted(grid, grid[0] + int(CAL_DAYS * 86400)))
    log('house%d: grid %d samples, n_cal %d' % (N, len(grid), n_cal))

    channels = {}
    for _ch, lab, p in ch_files:
        ts, w = read_dat(p)
        arr = align_to_grid(ts, w, grid, dt_s)
        del ts, w
        nz = grid[arr > 0]
        ds = dense_start(nz) if len(nz) else None
        own_ds_idx = int(np.searchsorted(grid, ds)) if ds is not None else None
        sig = _sig_from_arr(arr[:n_cal], dt_s)
        gt = _gt_variants(arr[n_cal:], dt_s)
        ref_energy_kwh = round(float(arr[n_cal:].sum()) * dt_s / 3.6e6, 2)
        ent = {'label': lab, 'sig': sig, 'gt': gt, 'ref_energy_kwh': ref_energy_kwh,
               'own_ds': int(grid[own_ds_idx]) if own_ds_idx is not None else None,
               'fallback': None, 'app': None}
        # per-device fallback: enroll the device from its own first dense 7 d
        if sig.get('n_cal_eps', 0) == 0 and own_ds_idx is not None:
            i0 = own_ds_idx
            i1 = i0 + n_cal_per(grid, i0, CAL_DAYS)
            if i1 < N - int(1 * 86400 / dt_s):
                fsig = _sig_from_arr(arr[i0:i1], dt_s)
                if fsig['n_cal_eps'] > 0:
                    ent['fallback'] = {'i0': i1, 'sig': fsig, 'gt': _gt_variants(arr[i1:], dt_s)}
        channels[lab] = ent
        del arr
    ctx = {'name': 'house%d' % n, 'dt_s': dt_s, 'n_cal': n_cal, 'channels': channels,
           'always_on_W': _house_daily_floor(agg, grid, dt_s, CAL_DAYS)}
    save_ctx(ctx, agg)
    return ctx


def build_slice():
    df, apps = load_ukdale()
    grid = df.ts.values.astype('datetime64[s]').astype(np.int64)
    agg = df.power.values.astype(np.float64)
    dt_s = 6.0
    n_cal = int(np.searchsorted(grid, grid[0] + int(CAL_DAYS * 86400)))
    channels = {}
    for k, arr0 in apps.items():
        if k == 'monitor':
            continue
        arr = arr0.astype(np.float64)
        sig = _sig_from_arr(arr[:n_cal], dt_s)
        channels[k] = {'label': k, 'sig': sig, 'gt': _gt_variants(arr[n_cal:], dt_s),
                       'ref_energy_kwh': round(float(arr[n_cal:].sum()) * dt_s / 3.6e6, 2),
                       'own_ds': None, 'fallback': None, 'app': arr.astype(np.float32)}
    ctx = {'name': 'slice', 'dt_s': dt_s, 'n_cal': n_cal, 'channels': channels,
           'always_on_W': _house_daily_floor(agg, grid, dt_s, CAL_DAYS)}
    save_ctx(ctx, agg)
    return ctx


def build_ampds2():
    df = pd.read_csv(AMPDS2_CSV)
    grid = df['UNIX_TS'].values.astype(np.int64)
    agg = df[AMPDS2_AGG].values.astype(np.float64)
    dt_s = 60.0
    n_cal = int(np.searchsorted(grid, grid[0] + int(CAL_DAYS * 86400)))
    channels = {}
    for col in df.columns:
        if col in (AMPDS2_AGG, 'UNIX_TS'):
            continue
        arr = df[col].values.astype(np.float64)
        sig = _sig_from_arr(arr[:n_cal], dt_s)
        channels[col] = {'label': AMPDS2_LABELS.get(col) or col,
                         'sig': sig, 'gt': _gt_variants(arr[n_cal:], dt_s),
                         'ref_energy_kwh': round(float(arr[n_cal:].sum()) * dt_s / 3.6e6, 2),
                         'own_ds': None, 'fallback': None, 'app': arr.astype(np.float32)}
    ctx = {'name': 'ampds2', 'dt_s': dt_s, 'n_cal': n_cal, 'channels': channels,
           'always_on_W': _house_daily_floor(agg, grid, dt_s, CAL_DAYS)}
    save_ctx(ctx, agg)
    return ctx


def save_ctx(ctx, agg):
    os.makedirs(CACHE, exist_ok=True)
    name = ctx['name']
    np.save(os.path.join(CACHE, name + '_agg.npy'), agg)
    with open(os.path.join(CACHE, name + '_meta.pkl'), 'wb') as f:
        pickle.dump(ctx, f)
    log('cached %s (%d channels, agg %d samples)' % (name, len(ctx['channels']), len(agg)))


def load_ctx(name):
    with open(os.path.join(CACHE, name + '_meta.pkl'), 'rb') as f:
        ctx = pickle.load(f)
    ctx['agg'] = np.load(os.path.join(CACHE, name + '_agg.npy'))
    return ctx


# ----------------------------------------------------------------- experiment core

def variant_detect(x, sig, cfg, dt_s, always_on):
    """Detection episodes for one channel under an experiment config."""
    stat = cfg.get('sig_stat', 'median')
    p = sig['on_W'] if stat == 'median' else sig['on_p25_W'] if stat == 'p25' else sig['on_p90_W']
    if p <= 0:
        return []
    thr = cfg.get('thr_frac', 0.5) * p
    lo = cfg.get('exit_frac', cfg.get('thr_frac', 0.5) / 2.0) * p
    degenerate = sig['on_W'] < always_on
    if cfg.get('local_baseline_min'):
        x = x - rolling_median(x, int(cfg['local_baseline_min'] * 60 / dt_s))
    if degenerate and cfg.get('rel_thr_degenerate'):
        if not cfg.get('local_baseline_min'):
            x = x - rolling_median(x, int(5 * 60 / dt_s))
        thr = 0.5 * max(sig['on_W'], 5.0)
        lo = 0.25 * max(sig['on_W'], 5.0)
    eps = detect_eps(x, thr, lo, cfg.get('min_dwell', GT_MIN_SAMP),
                     cfg.get('det_gap_merge_s', 0), dt_s)
    if cfg.get('dwell_prior'):
        d10, d90 = sig['dwell_p10_s'], sig['dwell_p90_s']
        if d90 > 0:
            eps = [e for e in eps if 0.5 * d10 <= e[1] * dt_s <= 2.0 * d90]
    return eps


def run_experiment(ctx, cfg, f2=False):
    """Run one experiment config on one substrate."""
    dt_s = ctx['dt_s']
    n_cal, agg = ctx['n_cal'], ctx['agg']
    ao = ctx['always_on_W']
    x = agg[n_cal:] - ao
    gtm = 'gm%d' % int(cfg.get('gt_gap_merge_s', 0))
    if cfg.get('f2'):
        res, conf, diag = run_f2(ctx, cfg, x, gtm)
        return res, None, conf, diag
    dets, res = {}, {}
    for k, c in ctx['channels'].items():
        gt = c['gt'][gtm]
        det = variant_detect(x, c['sig'], cfg, dt_s, ao)
        dets[k] = det
        res[k] = score_eps(gt, det, dt_s)
        if c.get('app') is not None:
            ap = c['app'][n_cal:]
            en = []
            for gi, di, _, _ in match(gt, det, 2 * dt_s, dt_s):
                s, l = gt[gi]
                g_e = float(ap[s:s + l].sum()) * dt_s / 3.6e6
                e_e = c['sig']['on_W'] * det[di][1] * dt_s / 3.6e6
                en.append(e_e / g_e if g_e > 0 else np.nan)
            res[k]['energy_ratio_p50'] = round(float(np.nanmedian(en)), 2) if en else None
    # union of GT episodes across channels; count dets overlapping none of them
    all_gt = sorted(e for k in res for e in ctx['channels'][k]['gt'][gtm])
    if all_gt:
        gs = np.array([e[0] for e in all_gt], dtype=np.int64)
        ge = gs + np.array([e[1] for e in all_gt], dtype=np.int64)
        endmax = np.maximum.accumulate(ge)
    else:
        gs = np.zeros(0, dtype=np.int64)
        endmax = gs
    fp = tot = 0
    for det in dets.values():
        tot += len(det)
        if not det or not all_gt:
            fp += len(det)
            continue
        arr = np.array(det, dtype=np.int64)
        # last gt episode starting before this det's end
        j = np.searchsorted(gs, arr[:, 0] + arr[:, 1], 'left') - 1
        has = (j >= 0) & (endmax[np.maximum(j, 0)] > arr[:, 0])
        fp += int((~has).sum())
    fp_rate = round(100 * fp / max(tot, 1), 1)
    return res, fp_rate, None, None


def run_f2(ctx, cfg, x, gtm):
    """F2 event-then-classify: one generic detector + nearest-signature attribution."""
    dt_s = ctx['dt_s']
    ao = ctx['always_on_W']
    lib = {k: c['sig'] for k, c in ctx['channels'].items()
           if c['sig']['n_cal_eps'] > 0 and c['sig']['on_W'] >= ao}
    diag0 = {'thr_W': 0, 'lib': [], 'events': 0, 'reject_margin': 0, 'reject_plaus': 0}
    if not lib:
        return {}, {}, diag0
    thr_g = cfg.get('f2_thr_W') or 0.5 * min(s['on_W'] for s in lib.values())
    det_g = detect_eps(x, thr_g, thr_g / 2, cfg.get('min_dwell', GT_MIN_SAMP),
                       cfg.get('det_gap_merge_s', 12), dt_s)
    ks = sorted(lib)
    on = np.array([lib[k]['on_W'] for k in ks])
    dw = np.array([max(lib[k]['dwell_p50_s'], 30.0) for k in ks])
    d10 = np.array([max(lib[k]['dwell_p10_s'], 10.0) for k in ks])
    d90 = np.array([max(lib[k]['dwell_p90_s'], 30.0) for k in ks])
    margin = cfg.get('f2_margin', 0.0)
    norm = cfg.get('f2_norm', 'abs')
    plaus = cfg.get('f2_plaus', False)
    use_dwell_prior = cfg.get('f2_dwell_prior', False)
    attr = {k: [] for k in ks}
    n_reject_margin = n_reject_plaus = 0
    logdw = np.log(2)
    for s, l in det_g:
        seg = x[s:s + l]
        level = float(seg.mean()) if len(seg) else 0.0
        dwell = l * dt_s
        dl = np.abs(level - on) / (on if norm == 'iqr' else np.maximum(on, 1.0))
        dd = np.abs(np.log(dwell + 1) - np.log(dw + 1)) / logdw
        d = dl + 0.5 * dd
        order = np.argsort(d)
        b = order[0]
        s2 = order[1] if len(order) > 1 else b
        if margin and (d[s2] / max(d[b], 1e-9)) < margin:
            n_reject_margin += 1
            continue
        if plaus and on[b] < 0.6 * level:
            n_reject_plaus += 1
            continue
        if use_dwell_prior and not (0.5 * d10[b] <= dwell <= 2.0 * d90[b]):
            n_reject_plaus += 1
            continue
        attr[ks[b]].append((s, l))
    res = {}
    for k in ks:
        res[k] = score_eps(ctx['channels'][k]['gt'][gtm], attr.get(k, []), dt_s)
    diag = {'thr_W': round(thr_g, 1), 'lib': ks, 'events': len(det_g),
            'reject_margin': n_reject_margin, 'reject_plaus': n_reject_plaus}
    # event-centric accuracy: among attributed events, how many land on the
    # right device (largest-overlap GT), how many explain nothing at all
    union = sorted(e for k in ctx['channels'] for e in ctx['channels'][k]['gt'][gtm])
    us = np.array([e[0] for e in union], dtype=np.int64)
    ue = us + np.array([e[1] for e in union], dtype=np.int64)
    uendmax = np.maximum.accumulate(ue)
    n_correct = n_spurious = 0
    for k in ks:
        gk = ctx['channels'][k]['gt'][gtm]
        gks = np.array([e[0] for e in gk], dtype=np.int64)
        gke = gks + np.array([e[1] for e in gk], dtype=np.int64)
        gendmax = np.maximum.accumulate(gke)
        for s, l in attr.get(k, []):
            j = np.searchsorted(us, s + l, 'left') - 1
            over_union = j >= 0 and uendmax[j] > s
            j2 = np.searchsorted(gks, s + l, 'left') - 1
            over_k = j2 >= 0 and gendmax[j2] > s
            if over_k:
                n_correct += 1
            elif not over_union:
                n_spurious += 1
    diag['event_correct'] = n_correct
    diag['event_spurious'] = n_spurious
    diag['event_accuracy'] = round(n_correct / max(len(det_g) - n_reject_margin - n_reject_plaus, 1), 3)
    conf_counts = {}
    for k in ks:
        for o in ks:
            if o == k:
                continue
            c = sum(1 for h in overlap_hits(ctx['channels'][k]['gt'][gtm], attr.get(o, [])) if h)
            if c:
                conf_counts.setdefault(k, {})[o] = c
    return res, conf_counts, diag


# ----------------------------------------------------------------- registry + runner

EXPERIMENTS = [
    ('E00', 'anchor', 'R1 M0 config (delta baseline)', {}),
    ('E01', 'gap_merge_12s', 'plan 3.2 gap merge 12 s on episodes (det + GT)', {'det_gap_merge_s': 12, 'gt_gap_merge_s': 12}),
    ('E02', 'activity_windows', 'gap merge 600 s: multi-state programs become one window', {'det_gap_merge_s': 600, 'gt_gap_merge_s': 600}),
    ('E03', 'sig_p25', 'signature from ON p25 instead of median', {'sig_stat': 'p25'}),
    ('E04', 'sig_p90', 'signature from ON p90 (upper level)', {'sig_stat': 'p90'}),
    ('E05', 'thr_p25', 'enter at 0.25x signature (lower entry)', {'thr_frac': 0.25}),
    ('E06', 'dwell_prior', 'reject detections outside signature dwell [p10,p90] x [0.5,2]', {'dwell_prior': True}),
    ('E07', 'local_baseline_5min', 'subtract 5-min rolling median before thresholding', {'local_baseline_min': 5}),
    ('E08', 'local_baseline_30min', '30-min rolling baseline', {'local_baseline_min': 30}),
    ('E09', 'rel_thr_degenerate', 'relative-threshold 2nd pass for sub-floor signatures', {'rel_thr_degenerate': True}),
    ('E10', 'hyst_040_020', 'wider hysteresis (enter .40, exit .20)', {'thr_frac': 0.40}),
    ('E11', 'hyst_060_030', 'narrower hysteresis (enter .60, exit .30)', {'thr_frac': 0.60, 'exit_frac': 0.30}),
    ('E12', 'min_dwell_3', 'detector min dwell 3 samples', {'min_dwell': 3}),
    ('E13', 'stack_best', 'p25 signature + dwell prior + gap merge 12 s', {'sig_stat': 'p25', 'dwell_prior': True, 'det_gap_merge_s': 12, 'gt_gap_merge_s': 12}),
    ('E14', 'f2_lib', 'F2 disaggregation: generic events + nearest signature (level+dwell)', {'f2': True, 'f2_norm': 'abs', 'gt_gap_merge_s': 12}),
    ('E15', 'f2_margin', 'F2 + ambiguity margin (second-best/best >= 1.3)', {'f2': True, 'f2_norm': 'abs', 'f2_margin': 1.3, 'gt_gap_merge_s': 12}),
    ('E16', 'f2_norm', 'F2 with IQR-normalized distance', {'f2': True, 'f2_norm': 'iqr', 'gt_gap_merge_s': 12}),
    ('E17', 'f2_plaus', 'F2 + plausibility (signature >= 60% of event level)', {'f2': True, 'f2_norm': 'abs', 'f2_plaus': True, 'gt_gap_merge_s': 12}),
    ('E18', 'f2_dwellprior', 'F2 + dwell-prior rejection of misfit events', {'f2': True, 'f2_norm': 'abs', 'f2_dwell_prior': True, 'gt_gap_merge_s': 12}),
    ('E19', 'f2_stack', 'F2 + plausibility + dwell prior + margin', {'f2': True, 'f2_norm': 'abs', 'f2_margin': 1.3, 'f2_plaus': True, 'f2_dwell_prior': True, 'gt_gap_merge_s': 12}),
]

SWEEP_SUBSTRATES = ['slice', 'house2', 'house5', 'ampds2']


def weak_metrics(res):
    w = [v['F1'] for k, v in res.items() if is_weak(k) and v['gt'] > 0]
    kt = [v['F1'] for k, v in res.items() if is_kettle(k) and v['gt'] > 0]
    fr = [v['F1'] for k, v in res.items() if is_fridge(k) and v['gt'] > 0]
    allf = [v['F1'] for v in res.values() if v['gt'] > 0]
    return {'weak_mean_f1': round(float(np.mean(w)), 3) if w else None,
            'kettle_f1': round(float(np.mean(kt)), 3) if kt else None,
            'fridge_f1': round(float(np.mean(fr)), 3) if fr else None,
            'all_mean_f1': round(float(np.mean(allf)), 3) if allf else None,
            'n_devices': sum(1 for v in res.values() if v['gt'] > 0)}


def run_all(experiment_ids=None, substrates=None):
    substrates = substrates or SWEEP_SUBSTRATES
    ids = experiment_ids or [e[0] for e in EXPERIMENTS]
    ctxs = {s: load_ctx(s) for s in substrates}
    base = {}
    a_path = os.path.join(OUT, 'E00_anchor', 'metrics.json')
    if os.path.exists(a_path):
        base = json.load(open(a_path))['substrates']
    for eid, slug, hyp, cfg in EXPERIMENTS:
        if eid not in ids:
            continue
        out_dir = os.path.join(OUT, '%s_%s' % (eid, slug))
        os.makedirs(out_dir, exist_ok=True)
        prev_p = os.path.join(out_dir, 'metrics.json')
        prev = json.load(open(prev_p))['substrates'] if os.path.exists(prev_p) else {}
        metrics = {'id': eid, 'slug': slug, 'hypothesis': hyp, 'cfg': cfg,
                   'substrates': {k: v for k, v in prev.items() if k not in substrates}}
        rows = []
        for s in substrates:
            ctx = ctxs[s]
            t0 = time.time()
            res, fp_rate, conf, diag = run_experiment(ctx, cfg, f2=bool(cfg.get('f2')))
            log('%s on %s done' % (eid, s))
            wm = weak_metrics(res)
            wm['fp_rate_pct'] = fp_rate
            wm['seconds'] = round(time.time() - t0, 1)
            metrics['substrates'][s] = {'devices': res, 'summary': wm, 'f2_diag': diag, 'confusion': conf}
            rows.append((s, wm, res, conf, diag))

        def d(a, c):
            return round(a - c, 3) if (a is not None and c is not None) else None

        L = ['# %s %s' % (eid, slug), '', 'Hypothesis: ' + hyp, '',
             'Config: ' + json.dumps(cfg), '']
        for s, wm, res, conf, diag in rows:
            b = (base.get(s) or {}).get('summary', {})
            def fmt_delta(a, c, tag):
                dd = d(a, c)
                return (' (%+.3f' % dd + tag + ')') if dd is not None else ''
            L.append('## %s (weak %s%s, all %s%s, devices %d, fp %s%%, %.1fs)' % (
                s, wm['weak_mean_f1'],
                ('%s' % fmt_delta(wm['weak_mean_f1'], b.get('weak_mean_f1'), ' vs E00')) if b else '',
                wm['all_mean_f1'],
                ('%s' % fmt_delta(wm['all_mean_f1'], b.get('all_mean_f1'), '')) if b else '',
                wm['n_devices'], wm['fp_rate_pct'], wm['seconds']))
            L += ['', '| device | GT | det | P | R | F1 | dF1 vs E00 |', '|---|---|---|---|---|---|---|']
            for k in sorted(res, key=lambda k: -res[k]['gt']):
                v = res[k]
                if v['gt'] == 0:
                    continue
                bd = None
                if b and k in (base.get(s) or {}).get('devices', {}):
                    bd = d(v['F1'], base[s]['devices'][k]['F1'])
                L.append('| %s | %d | %d | %.2f | %.2f | %.2f | %s |' % (
                    k, v['gt'], v['det'], v['P'], v['R'], v['F1'],
                    ('%+.2f' % bd) if bd is not None else '-'))
            L.append('')
            if diag and diag.get('events'):
                L.append('F2: threshold %.0f W, library %d devices, %d generic events, rejected: margin %d / plaus-dwell %d.' % (
                    diag['thr_W'], len(diag['lib']), diag['events'], diag['reject_margin'], diag['reject_plaus']))
                L.append('')
            if conf:
                L.append('Top confusion (GT device <- events attributed to):')
                for k, cf in sorted(conf.items(), key=lambda t: -sum(t[1].values()))[:6]:
                    L.append('- %s <- %s' % (k, ', '.join('%s %d' % (a, c) for a, c in sorted(cf.items(), key=lambda t: -t[1])[:4])))
                L.append('')
        with open(os.path.join(out_dir, 'report.md'), 'w') as f:
            f.write("\n".join(L) + "\n")
        with open(os.path.join(out_dir, 'metrics.json'), 'w') as f:
            json.dump(metrics, f, indent=1, default=float)
        log('wrote %s (%s)' % (out_dir, eid))
    write_leaderboard()


def write_leaderboard():
    rows = []
    for eid, slug, hyp, _cfg in EXPERIMENTS:
        p = os.path.join(OUT, '%s_%s' % (eid, slug), 'metrics.json')
        if not os.path.exists(p):
            continue
        m = json.load(open(p))
        for s, sub in m['substrates'].items():
            sm = sub['summary']
            rows.append((eid, s, sm['weak_mean_f1'], sm['all_mean_f1'],
                         sm['kettle_f1'], sm['fridge_f1'], hyp))
    L = ['# Experiment leaderboard', '',
         'weak = mean F1 over dish/washer-class devices with GT episodes; guards: kettle, fridge.', '',
         '| exp | substrate | weak F1 | all F1 | kettle | fridge | hypothesis |', '|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda t: (t[0], t[1])):
        L.append('| %s | %s | %s | %s | %s | %s | %s |' % (
            r[0], r[1], r[2] if r[2] is not None else '-', r[3] if r[3] is not None else '-',
            r[4] if r[4] is not None else '-', r[5] if r[5] is not None else '-', r[6]))
    with open(os.path.join(OUT, 'leaderboard.md'), 'w') as f:
        f.write("\n".join(L) + "\n")
    log('wrote leaderboard')


# ----------------------------------------------------------------- enrollment tables

def enrollment():
    """Per-device enrollment effectiveness across every channel of every substrate."""
    os.makedirs(ENROLL_OUT, exist_ok=True)
    names = ['slice', 'house1', 'house2', 'house3', 'house4', 'house5', 'ampds2']
    summary = []
    for nm in names:
        if not os.path.exists(os.path.join(CACHE, nm + '_meta.pkl')):
            continue
        ctx = load_ctx(nm)
        dt_s = ctx['dt_s']
        ao = ctx['always_on_W']
        L = ['# Enrollment: %s' % nm, '',
             'Calibration = first %.0f d of the common span; always-on floor %.0f W; dt = %g s.' % (CAL_DAYS, ao, dt_s),
             'A device enrolls when its calibration window locks a signature (plan 3.0).', '',
             '| device | cal eps | on W | dwell p50 s | ref eps | ref eps gm12 | ref kWh | P | R | F1 | enrolled via |', '|---|---|---|---|---|---|---|---|---|---|---|']
        n_ok = n_fb = 0
        energy_ok = energy_fb = 0.0
        for k, c in sorted(ctx['channels'].items(), key=lambda t: -t[1]['ref_energy_kwh']):
            sig, gt = c['sig'], c['gt']['gm0']
            fb = '-'
            if sig.get('n_cal_eps', 0) > 0 and sig['on_W'] > 0:
                det = detect_eps(ctx['agg'][ctx['n_cal']:] - ao, 0.5 * sig['on_W'], 0.25 * sig['on_W'], GT_MIN_SAMP, 0, dt_s)
                sc = score_eps(gt, det, dt_s)
                n_ok += 1
                energy_ok += c['ref_energy_kwh']
            elif c.get('fallback'):
                e0, fsig = c['fallback']['i0'], c['fallback']['sig']
                fgt = c['fallback']['gt']['gm0']
                det = detect_eps(ctx['agg'][e0:] - ao, 0.5 * fsig['on_W'], 0.25 * fsig['on_W'], GT_MIN_SAMP, 0, dt_s)
                sc = score_eps(fgt, det, dt_s)
                fb = 'own dense start'
                n_fb += 1
                energy_fb += c['ref_energy_kwh']
            else:
                sc = {'gt': len(gt), 'det': 0, 'matched': 0, 'P': 0.0, 'R': 0.0, 'F1': 0.0}
                fb = 'no dense window'
            L.append('| %s | %d | %.0f | %.0f | %d | %d | %.1f | %.2f | %.2f | %.2f | %s |' % (
                k, sig.get('n_cal_eps', 0), sig['on_W'], sig['dwell_p50_s'],
                len(gt), len(c['gt']['gm12']), c['ref_energy_kwh'],
                sc['P'], sc['R'], sc['F1'], fb))
        L += ['', 'Enrolled from house calibration: %d devices (%.1f kWh ref energy); from own dense start: %d (%.1f kWh); not enrollable: %d.' % (
            n_ok, energy_ok, n_fb, energy_fb, len(ctx['channels']) - n_ok - n_fb)]
        with open(os.path.join(ENROLL_OUT, '%s.md' % nm), 'w') as f:
            f.write("\n".join(L) + "\n")
        summary.append((nm, len(ctx['channels']), n_ok, n_fb))
        log('enrollment table: %s' % nm)
    L = ['# Enrollment across the device universe', '',
         'Per-house tables: enrollment/slice.md, enrollment/houseN.md, enrollment/ampds2.md.',
         'A device enrolls when its calibration window contains episodes strong enough to lock a signature (plan 3.0).', '',
         '| substrate | devices | enrolled (house cal) | fallback (own dense start) |', '|---|---|---|---|']
    for nm, tot, ok, fb in summary:
        L.append('| %s | %d | %d | %d |' % (nm, tot, ok, fb))
    with open(os.path.join(ENROLL_OUT, 'enrollment.md'), 'w') as f:
        f.write("\n".join(L) + "\n")
    log('wrote enrollment summary')


# ----------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', nargs='*', default=None,
                    help='build context caches: slice house1..5 ampds2 (default all)')
    ap.add_argument('--enrollment', action='store_true')
    ap.add_argument('--run-experiments', nargs='*', default=None)
    ap.add_argument('--substrates', nargs='*', default=None)
    args = ap.parse_args()
    if args.build is not None:
        todo = args.build or ['slice', 'house1', 'house2', 'house3', 'house4', 'house5', 'ampds2']
        for nm in todo:
            t0 = time.time()
            if nm == 'slice':
                build_slice()
            elif nm == 'ampds2':
                build_ampds2()
            else:
                build_house(int(nm[-1]))
            log('%s built in %.0f s' % (nm, time.time() - t0))
    if args.enrollment:
        enrollment()
    if args.run_experiments is not None:
        run_all(args.run_experiments or None, args.substrates)


if __name__ == '__main__':
    main()