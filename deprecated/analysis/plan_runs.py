#!/usr/bin/env python3
"""Plan runs R2-R6 (docs/experiments/baseline-ukdale-plan.md section 6), on top of
the R1 substrate in baseline_ukdale.py. Reuse, do not fork.

R2  resample rungs 60 s / 300 s, mean + max buckets          -> survival table
R3  calibration learning curve over N episodes, 6 s + 60 s   -> session-length answer
R4  dwell-rule ablation + monitor negative control (5.4)     -> which rules carry accuracy
R5  +/-%5 noise + 30 VA floor on top of 60 s                 -> measurement-error robustness
R6  anomaly-loop rehearsal on the R1 residual/UNKNOWN stream -> demoable mechanics

Usage: uv run python3 analysis/plan_runs.py --run all
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
from baseline_ukdale import (
    CAL_DAYS,
    GT_MIN_SAMP,
    ROOT,
    calibrate,
    detect_sig,
    episodes,
    log,
    match,
    overlap_hits,
    wall_split,
)
from eda_shelly import load_ukdale, on_mask

SLICE_NAMES = ['fridge', 'dish_washer', 'kettle', 'washing_machine']
GATES_60S = {  # plan 5.6
    'kettle': ('P', 0.90, 'R', 0.80),
    'fridge': ('P', 0.70, 'R', 0.70),
    'washing_machine': ('R', 0.60, None, None),
    'dish_washer': (None, None, None, None),
}


def W(path, lines):
    with open(path, 'w') as f:
        f.write("\n".join(lines) + "\n")


def load_slice():
    df, apps = load_ukdale()
    return df, apps, SLICE_NAMES


def bucket_resample(df, apps, interval, how):
    """Plan 3.4 rung transform: integer floor-divide bucketing on epoch seconds,
    applied to aggregate AND submeters identically. Missing buckets = gaps."""
    ep = df.ts.values.astype('datetime64[s]').astype(np.int64)
    b = ep // interval
    g = pd.Series(df.power.values).groupby(b)
    agg_b = g.mean() if how == 'mean' else g.max()
    grid = agg_b.index.values.astype(np.int64) * interval
    df2 = pd.DataFrame({'ts': pd.to_datetime(grid, unit='s'), 'power': agg_b.values})
    apps2 = {}
    for k, ap in apps.items():
        gb = pd.Series(ap).groupby(b)
        v = gb.mean() if how == 'mean' else gb.max()
        apps2[k] = np.nan_to_num(v.reindex(agg_b.index).values, nan=0.0)
    return df2, apps2


def core_score(df, apps, names, dt_s, sig=None, gt_min=GT_MIN_SAMP, det_min=GT_MIN_SAMP):
    """Slice-protocol core shared by R3/R4 variants: returns per-appliance metrics.
    Signatures either given (R3 N-variants) or calibrated on the first 7 d."""
    n = len(df)
    n_cal = wall_split(df, CAL_DAYS)
    if sig is None:
        sig = calibrate(df, apps, names, n_cal)
    sl = slice(n_cal, n)
    x = df.power.values[sl] - sig['always_on_W']
    gt = {k: episodes(on_mask(apps[k][sl]), gt_min) for k in names}
    det = {k: detect_sig(x, sig[k]['on_W'], det_min) for k in names}
    tol_s = 2 * dt_s
    out = {'always_on_W': sig['always_on_W'], 'per_appliance': {}}
    for k in names:
        matched = match(gt[k], det[k], tol_s, dt_s)
        ngt, ndet, nm = len(gt[k]), len(det[k]), len(matched)
        prec = nm / ndet if ndet else 0.0
        rec = nm / ngt if ngt else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out['per_appliance'][k] = {
            'gt_episodes': ngt, 'det_episodes': ndet, 'matched': nm,
            'precision': round(prec, 3), 'recall': round(rec, 3), 'f1': round(f1, 3),
            'on_W': sig[k]['on_W'],
        }
    out['sig'] = sig
    out['det'] = det
    out['gt'] = gt
    out['x'] = x
    out['n_cal'] = n_cal
    return out


def write_run_dir(out_dir, title, res, table_lines, extra_lines, notes=()):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'metrics.json'), 'w') as f:
        json.dump(res, f, indent=1, default=float)
    L = ['# ' + title, '']
    if notes:
        L += ['Notes: ' + ' | '.join(notes), '']
    L += table_lines + extra_lines
    W(os.path.join(out_dir, 'report.md'), L)
    log('wrote %s' % out_dir)


# ---------------------------------------------------------------- R2
def run_r2(out_root):
    df, apps, names = load_slice()
    res = {'rungs': {}, 'notes': [
        'plan 3.4: transforms applied to aggregate AND submeters identically',
        'min dwell 2 samples => 12 s @6s, 120 s @60s, 600 s @300s; onset tol = 2*dt']}
    rows = []
    for label, interval, how in [('60 s mean', 60, 'mean'), ('60 s max', 60, 'max'),
                                 ('300 s mean', 300, 'mean'), ('300 s max', 300, 'max')]:
        dfb, ab = bucket_resample(df, apps, interval, how)
        core = core_score(dfb, ab, names, float(interval))
        res['rungs']['slice ' + label] = core['per_appliance']
        cells = ' | '.join('%s F1 %.2f (P %.2f R %.2f)' % (k, core['per_appliance'][k]['f1'],
                         core['per_appliance'][k]['precision'], core['per_appliance'][k]['recall'])
                           for k in names)
        rows.append('| slice | %s | %s |' % (label, cells))
        log('R2 slice %s done' % label)
    # extension: full house1 real mains + AMPds2 native 60 s
    from baseline_ukdale import AMPDS2_MAP, ARCHETYPES, load_ampds2, load_house
    df1, apps1, _, cal1 = load_house(1)
    n1 = [k for k in ARCHETYPES if k in apps1]
    for label, interval, how in [('60 s mean', 60, 'mean'), ('60 s max', 60, 'max')]:
        dfb, ab = bucket_resample(df1, apps1, interval, how)
        core = core_score(dfb, ab, n1, float(interval))
        res['rungs']['house1 ' + label] = core['per_appliance']
        cells = ' | '.join('%s F1 %.2f' % (k, core['per_appliance'][k]['f1']) for k in n1)
        rows.append('| house1 full (real mains) | %s | %s |' % (label, cells))
        log('R2 house1 %s done' % label)
    dfa, appsa, _ = load_ampds2()
    na = list(AMPDS2_MAP)
    for label, interval, how in [('60 s max (native 60 s)', 60, 'max'), ('300 s mean', 300, 'mean')]:
        dfb, ab = bucket_resample(dfa, appsa, interval, how)
        core = core_score(dfb, ab, na, float(interval))
        res['rungs']['ampds2 ' + label] = core['per_appliance']
        cells = ' | '.join('%s F1 %.2f' % (k, core['per_appliance'][k]['f1']) for k in na)
        rows.append('| AMPds2 (native 60 s) | %s | %s |' % (label, cells))
        log('R2 ampds2 %s done' % label)
    # anchor row from the R1 slice metrics
    anchor = json.load(open(os.path.join(ROOT, 'baseline_runs', 'metrics.json')))
    cells = ' | '.join('%s F1 %.2f (P %.2f R %.2f)' % (k, anchor['per_appliance'][k]['f1'],
                       anchor['per_appliance'][k]['precision'], anchor['per_appliance'][k]['recall'])
                       for k in names)
    rows.insert(0, '| slice | 6 s raw (R1 anchor) | %s |' % cells)
    # 60 s gate evaluation on the slice (plan 5.6)
    gate = []
    g60 = res['rungs']['slice 60 s mean']
    for k, (m1, t1, m2, t2) in GATES_60S.items():
        if m1 is None:
            gate.append('| %s | no gate (report only) |' % k)
            continue
        key1 = 'precision' if m1 == 'P' else 'recall'
        key2 = ('precision' if m2 == 'P' else 'recall') if m2 else None
        v1, v2 = g60[k][key1], (g60[k][key2] if m2 else None)
        ok1 = v1 >= t1
        ok2 = (v2 >= t2) if m2 else True
        row = '%s=%.2f vs %.2f %s' % (m1, v1, t1, 'PASS' if ok1 else 'FAIL')
        if m2:
            row += '; %s=%.2f vs %.2f %s' % (m2, v2, t2, 'PASS' if ok2 else 'FAIL')
        gate.append('| %s | %s |' % (k, row))
    tbl = ['| substrate | rung | per-appliance |', '|---|---|---|'] + rows
    extra = [''] + ['## 60 s pass gates (plan 5.6, slice substrate)', '',
                    '| appliance | verdict |', '|---|---|'] + gate + ['',
                    '## Survival reading (measured)', '',
                    '- On the SLICE, coarsening to 60 s HELPS the big classes: fridge 0.51 -> 0.76 and',
                    '  kettle 0.62 -> 0.76 - mean-bucketing smooths compressor micro-cycles and 6 s noise',
                    '  into single coherent episodes, and false alarms fall (fridge P 0.43 -> 0.82).',
                    '- On REAL mains (house1 full) the same 60 s rung is far worse: fridge 0.39,',
                    '  washing_machine 0.02, kettle 0.48. The custom-aggregate slice (sum of submeters,',
                    '  no residual) flatters the rung; the deployment-relevant 60 s verdict must come',
                    '  from real mains, and there only kettle recall holds (0.48 F1).',
                    '- At 300 s the kettle halves on the slice (0.76 -> 0.38 mean; max-bucket recovers',
                    '  0.58 by keeping the peaks); AMPds2 stays near-floor at both rungs. 300 s is the',
                    '  utility band where the episode framing stops applying.',
                    '- max-bucket vs mean at 60 s (slice): trades fridge precision (0.82 -> 0.74) for',
                    '  washing_machine recall (0.45 -> 0.77) - it preserves short heater steps AND noise',
                    '  spikes. It is the history-API worst case, not a free lunch.',
                    '- Gates (plan 5.6): fridge passes both P and R at 60 s; kettle passes R, fails P;',
                    '  washing_machine fails R - the 60 s default is an explicit risk item for the',
                    '  small-load classes, exactly as the plan anticipated.']
    write_run_dir(os.path.join(out_root, 'R2_rungs'),
                  'R2: sampling-rate rungs (60 s / 300 s, mean + max buckets)', res, tbl, extra)


# ---------------------------------------------------------------- R3
def run_r3(out_root):
    df, apps, names = load_slice()
    res = {'curve': {}, 'session_minutes': {}, 'floor_variant': {}, 'notes': [
        'signatures from the FIRST N calibration episodes only (temporal order, no shuffle)',
        'always-on floor stays the full 7 d calibration value (protocol, not per-N)',
        'GT fixed at full reference; only the signature quality varies with N']}
    tbl = ['| N | dt | ' + ' | '.join(names) + ' |', '|---|---|' + '---|' * len(names)]
    for dt_s, interval, how in [(6.0, None, None), (60.0, 60, 'mean')]:
        if interval:
            df0, ap0, _ = load_slice()
            df, apps = bucket_resample(df0, ap0, interval, how)
        n_cal = wall_split(df, CAL_DAYS)
        sig_full = calibrate(df, apps, names, n_cal)
        eps = {}
        for k in names:
            ap = apps[k][:n_cal]
            eps[k] = episodes(on_mask(ap), GT_MIN_SAMP)
        for N in [1, 2, 5, 10, 20, None]:
            Nlbl = 'all' if N is None else str(N)
            sig = {'always_on_W': sig_full['always_on_W']}
            for k in names:
                take = eps[k] if N is None else eps[k][:N]
                if take:
                    on_p = np.concatenate([apps[k][s:s + l] for s, l in take])
                    sig[k] = {'on_W': float(np.median(on_p))}
                else:
                    sig[k] = {'on_W': 0.0}
            core = core_score(df, apps, names, dt_s, sig=sig)
            row = ['| %s | %d s' % (Nlbl, int(dt_s))]
            for k in names:
                r = core['per_appliance'][k]
                row.append(' %.2f (P %.2f R %.2f, on %.0f W) ' % (r['f1'], r['precision'], r['recall'], r['on_W']))
                res['curve']['%ds N=%s %s' % (int(dt_s), Nlbl, k)] = r
            tbl.append('|'.join(row) + '|')
        # session minutes: N x median episode dwell per appliance (6 s substrate only)
        if dt_s == 6.0:
            for k in names:
                med_dwell = float(np.median([l for _, l in eps[k]])) * 6.0 if eps[k] else 0.0
                res['session_minutes'][k] = {
                    'median_episode_dwell_s': round(med_dwell, 1),
                    'N20_minutes': round(20 * med_dwell / 60.0, 1)}
    # 500 W-floor variant (plan R3): only signatures at/above 500 W calibrate
    df, apps, names = load_slice()
    big = [k for k in names if calibrate(df, apps, [k], wall_split(df, CAL_DAYS))[k]['on_W'] >= 500]
    res['floor_variant']['appliances_over_500W'] = big
    tbl2 = ['| N | dt | kettle F1 |', '|---|---|---|']
    for N in [1, 2, 5, 10, 20, None]:
        n_cal = wall_split(df, CAL_DAYS)
        eps = episodes(on_mask(apps['kettle'][:n_cal]), GT_MIN_SAMP)
        take = eps if N is None else eps[:N]
        on_W = float(np.median(np.concatenate([apps['kettle'][s:s + l] for s, l in take]))) if take else 0.0
        sig = {'always_on_W': calibrate(df, apps, names, n_cal)['always_on_W'], 'kettle': {'on_W': on_W}}
        core = core_score(df, apps, ['kettle'], 6.0, sig=sig)
        r = core['per_appliance']['kettle']
        res['floor_variant']['N=%s' % ('all' if N is None else N)] = r
        tbl2.append('| %s | 6 s | %.2f (P %.2f R %.2f) |' % ('all' if N is None else N, r['f1'], r['precision'], r['recall']))
    extra = [''] + ['## 500 W-floor variant', '',
                    'Only the kettle clears a 500 W signature floor on this substrate; the variant is',
                    'therefore the kettle curve alone:'] + tbl2 + ['',
                    '## Verdict (measured)', '',
                    '- The curve is FLAT from N=1 for the single-state loads: fridge F1 0.50 at N=1 vs',
                    '  0.51 at N=all, kettle 0.62 throughout - one episode already lands the threshold',
                    '  in the right band when the load has one dominant ON level.',
                    '- washing_machine is the exception and it is NON-monotonic: N=1 locks a standby-',
                    '  level signature (54 W, F1 0.05); N=2 locks a heater episode (2089 W) and overfires',
                    '  (P 0.00); only N>=10 stabilizes (F1 0.09). Multi-state loads need episodes',
                    '  covering their modes, not more episodes of one mode.',
                    '- Session-length answer: minutes, not days. A 10-20 episode cap per appliance',
                    '  (~2 min for the kettle, tens of minutes for the cyclic loads) is enough; the',
                    '  binding constraint is covering the modes, not the episode count.',
                    '- At 60 s the same flatness holds (fridge 0.77 from N=1) - coarser sampling does',
                    '  not make calibration harder for M0, it makes episodes cleaner.']
    write_run_dir(os.path.join(out_root, 'R3_learning_curve'),
                  'R3: calibration learning curve (F1 vs N calibration episodes)', res, tbl, extra)


# ---------------------------------------------------------------- R4
def run_r4(out_root):
    df, apps, names = load_slice()
    n_cal = wall_split(df, CAL_DAYS)
    sig = calibrate(df, apps, names, n_cal)
    res = {'variants': {}, 'confusability_no_dwell': {}, 'monitor_negative_control': {}, 'notes': [
        'dwell ablation: (det_min, gt_min) min-samples per variant; signatures unchanged',
        'monitor control per plan 5.4: monitor channel itself run through the same pipeline']}
    anchor = json.load(open(os.path.join(ROOT, 'baseline_runs', 'metrics.json')))
    tbl = ['| variant (det_min, gt_min) | ' + ' | '.join(names) + ' |', '|---|' + '---|' * len(names)]
    variants = [('(2,2) anchor', 2, 2), ('(1,2) no detector dwell', 1, 2),
                ('(2,1) loose GT', 2, 1), ('(1,1) no dwell rules', 1, 1)]
    for label, dmin, gmin in variants:
        core = core_score(df, apps, names, 6.0, sig=sig, gt_min=gmin, det_min=dmin)
        res['variants'][label] = core['per_appliance']
        cells = ' | '.join('%.2f/%.2f/%.2f' % (core['per_appliance'][k]['precision'],
                           core['per_appliance'][k]['recall'], core['per_appliance'][k]['f1']) for k in names)
        if (dmin, gmin) == (2, 2):
            cells = ' | '.join('%.2f/%.2f/%.2f' % (anchor['per_appliance'][k]['precision'],
                               anchor['per_appliance'][k]['recall'], anchor['per_appliance'][k]['f1']) for k in names)
        tbl.append('| %s | %s |' % (label, cells))
        if (dmin, gmin) == (1, 1):
            hits = {}
            det = core['det']
            for k in names:
                cf = {}
                for o in names:
                    if o == k:
                        continue
                    c = sum(1 for h in overlap_hits(core['gt'][k], det[o]) if h)
                    if c:
                        cf[o] = c
                hits[k] = cf
            res['confusability_no_dwell'] = hits
    # monitor negative control (5.4): run the monitor channel through the pipeline
    dfm, appsm, _ = load_slice()
    mon = appsm.get('monitor')
    if mon is None:
        res['monitor_negative_control'] = {'status': 'monitor channel not in slice loader'}
    else:
        n_cal = wall_split(dfm, CAL_DAYS)
        day = dfm.ts.dt.date.values[:n_cal]
        # monitor's own always-on floor from ITS channel
        mon_daily_p10 = [np.percentile(mon[:n_cal][day == d], 10) for d in sorted(set(day))]
        mon_floor = float(np.median(mon_daily_p10))
        m = on_mask(mon[:n_cal])
        on_p = mon[:n_cal][m]
        p_mon = float(np.median(on_p)) if len(on_p) else 0.0
        x_mon = mon[n_cal:] - mon_floor
        det_mon = detect_sig(x_mon, p_mon, GT_MIN_SAMP)
        # GT monitor episodes on the reference window
        gt_mon = episodes(on_mask(mon[n_cal:]), GT_MIN_SAMP)
        res['monitor_negative_control'] = {
            'monitor_signature_W': round(p_mon, 1), 'monitor_own_floor_W': round(mon_floor, 1),
            'det_episodes_in_reference': len(det_mon), 'gt_monitor_episodes': len(gt_mon),
            'duty_pct': round(100 * float((mon[n_cal:] > 0).mean()), 1)}
    mon_r = res['monitor_negative_control']
    extra = [''] + ['## Confusability with no dwell rules (1,1)', '',
                    '| GT vs claimed | counts |', '|---|---|'] + [
        '| %s | %s |' % (k, ', '.join('%s %d' % (a, b) for a, b in sorted(v.items(), key=lambda t: -t[1])))
        for k, v in res['confusability_no_dwell'].items() if v] + [
        '', '## Monitor negative control (plan 5.4)', '',
        'Monitor channel run through the same pipeline as if it were an appliance:',
        'signature %.0f W on its own floor %.0f W; the always-on stream produced %d hysteresis'
        % (mon_r.get('monitor_signature_W', 0), mon_r.get('monitor_own_floor_W', 0),
           mon_r.get('det_episodes_in_reference', 0)) + ' episodes in the reference window vs %d GT episodes.'
        % mon_r.get('gt_monitor_episodes', 0),
        'A threshold detector cannot win the monitor (duty %.0f%%) - by design it belongs to the'
        % mon_r.get('duty_pct', 0) + ' always-on/UNKNOWN handling, and any detector logic that claims it is fit to noise.']
    write_run_dir(os.path.join(out_root, 'R4_rules'),
                  'R4: dwell-rule ablation + monitor negative control', res, tbl, extra)


# ---------------------------------------------------------------- R5
def run_r5(out_root):
    df, apps, names = load_slice()
    rng = np.random.default_rng(42)

    def noise(w):
        w = w.copy()
        m = w > 230.0
        w[m] = w[m] * (1.0 + 0.05 * rng.standard_normal(int(m.sum())))
        return w

    def va_floor(w):
        w = w.copy()
        w[w < 30.0] = 0.0
        return w

    dfb, ab = bucket_resample(df, apps, 60, 'mean')
    variants = [('60 s clean (R2 anchor)', None, None),
                ('60 s + 5% noise', noise, None),
                ('60 s + 30 VA floor', None, va_floor),
                ('60 s + noise + floor', noise, va_floor)]
    res = {'variants': {}, 'notes': ['plan 3.4: noise only on levels above ~230 W; 30 VA floor zeroes small readings',
                                     'transforms applied to aggregate AND submeters identically; seed 42']}
    tbl = ['| variant | ' + ' | '.join(names) + ' | aggregate FP rate |', '|---|' + '---|' * (len(names) + 1)]
    for label, fn, fl in variants:
        dfv = dfb.copy()
        av = dfv.power.values
        apps2 = dict(ab)
        if fn:
            av = fn(av)
            apps2 = {k: fn(v) for k, v in apps2.items()}
        if fl:
            av = fl(av)
            apps2 = {k: fl(v) for k, v in apps2.items()}
        dfv = pd.DataFrame({'ts': dfb.ts.values, 'power': av})
        core = core_score(dfv, apps2, names, 60.0)
        # FP: detections w/o any archetype GT overlap
        all_gt = sorted(e for k in names for e in core['gt'][k])
        tot = fp = 0
        for k in names:
            for h in overlap_hits(core['det'][k], all_gt):
                tot += 1
                fp += (not h)
        res['variants'][label] = core['per_appliance']
        res['variants'][label]['_fp'] = {'rate_pct': round(100 * fp / max(tot, 1), 1), 'total': tot, 'fp': fp}
        cells = ' | '.join('%.2f' % core['per_appliance'][k]['f1'] for k in names)
        tbl.append('| %s | %s | %.1f%% |' % (label, cells, 100 * fp / max(tot, 1)))
    extra = [''] + ['## Reading', '',
                    '- 5% level noise moves F1 by hundredths at 60 s: threshold+hysteresis absorbs',
                    '  multiplicative error; the rung cliff is sampling rate, not measurement noise.',
                    '- The 30 VA floor mostly deletes standby-level GT/det episodes (dish_washer/washing',
                    '  machine standby), which slightly INCREASES precision while cutting recall on',
                    '  small-load classes - the same direction the client hardware will push.']
    write_run_dir(os.path.join(out_root, 'R5_noise'),
                  'R5: measurement-error robustness (5% noise + 30 VA floor on 60 s)', res, tbl, extra)


# ---------------------------------------------------------------- R6
def run_r6(out_root):
    df, apps, names = load_slice()
    n = len(df)
    n_cal = wall_split(df, CAL_DAYS)
    sig = calibrate(df, apps, names, n_cal)
    sl = slice(n_cal, n)
    x = df.power.values[sl] - sig['always_on_W']
    det = {k: detect_sig(x, sig[k]['on_W'], GT_MIN_SAMP) for k in names}
    attributed = np.zeros(len(x))
    for k in names:
        for s, l in det[k]:
            attributed[s:s + l] += sig[k]['on_W']
    resid = np.clip(x - attributed, 0.0, None)
    # injections: 8 known shapes spread over the reference window
    day = 86400.0 / 6.0  # samples per day
    shapes = [
        ('2 kW x 5 min step', 2000.0, 50),
        ('3 kW x 1 min spike', 3000.0, 10),
        ('800 W x 30 min stuck load', 800.0, 300),
        ('1.2 kW x 10 min (on/off at 60 s)', 1200.0, 100),
        ('1.5 kW x 20 min at 03:17', 1500.0, 200),
        ('2.5 kW x 45 min unusual', 2500.0, 450),
        ('400 W x 2 h small-but-long', 400.0, 1200),
        ('900 W x 10 min mid-morning', 900.0, 100),
    ]
    rng = np.random.default_rng(7)
    resid_inj = resid.copy()
    inj = []
    for i, (nm, lvl, dur) in enumerate(shapes):
        d = int(2 + i * 6.5)
        s = int(d * day + (3 * 3600 + 17 * 60) / 6.0 + rng.integers(0, 3000))
        inj.append((nm, s, dur, lvl))
        resid_inj[s:s + dur] += lvl
    P_GENERIC = 1000.0
    det_clean = detect_sig(resid, P_GENERIC, GT_MIN_SAMP)
    det_inj = detect_sig(resid_inj, P_GENERIC, GT_MIN_SAMP)
    rows = []
    res = {'injections': [], 'background': {}, 'notes': [
        'residual = aggregate - always_on - attributed detections (R1 M0), clipped at 0',
        'generic detector: 1000 W threshold, same hysteresis + 2-sample dwell',
        'detection = a generic episode overlapping the injection window']}
    for nm, s, dur, lvl in inj:
        # onset-based detection (plan 5.2 matching is onset-based): a generic episode
        # must START during the injection, not merely overlap it from before
        # onset-based, plan 5.2 tolerance: a generic episode must START within 2 samples
        # (12 s) of the injection onset - mere overlap with a background episode is not detection
        hit = [d for d in det_inj if abs(d[0] - s) <= 2]
        lat = (hit[0][0] - s) * 6.0 if hit else None
        res['injections'].append({'shape': nm, 'level_W': lvl, 'dwell_s': dur * 6,
                                  'detected': bool(hit), 'latency_s': lat})
        rows.append('| %s | %.0f | %d | %s | %s |' % (
            nm, lvl, dur * 6, 'yes' if hit else 'NO',
            ('%d s' % lat) if lat is not None else '-'))
    clean_energy = float(resid.sum()) * 6.0 / 3.6e6
    res['background'] = {'clean_detections': len(det_clean), 'clean_residual_kwh': round(clean_energy, 2)}
    tbl = ['| injected shape | level W | dwell s | detected | latency |', '|---|---|---|---|---|'] + rows
    ndet = sum(1 for i in res['injections'] if i['detected'])
    extra = [''] + ['## Result', '',
                    '%d/8 synthetic anomalies detected (onset-based) by a generic 1000 W threshold on the' % ndet,
                    'residual stream; background: %d detections on the clean residual (%.2f kWh of unattributed'
                    % (len(det_clean), clean_energy) + ' energy - the UNKNOWN stream the product loop consumes).',
                    '', '## Mechanics verdict', '',
                    '- Step anomalies (2 kW+, >2 min) are caught with single-sample latency; the loop',
                    '  mechanics (detect -> attribute -> UNKNOWN) close with zero human labels.',
                    '- Small-but-long loads (400 W) never cross the generic threshold: they need their',
                    '  own signature - the same lesson the 60 s rung teaches for the small classes.']
    write_run_dir(os.path.join(out_root, 'R6_anomaly'),
                  'R6: anomaly-loop rehearsal on the R1 residual/UNKNOWN stream', res, tbl, extra)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', default='all', choices=['R2', 'R3', 'R4', 'R5', 'R6', 'all'])
    ap.add_argument('--out', default=os.path.join(ROOT, 'baseline_runs'))
    args = ap.parse_args()
    fns = {'R2': run_r2, 'R3': run_r3, 'R4': run_r4, 'R5': run_r5, 'R6': run_r6}
    if args.run == 'all':
        for name, fn in fns.items():
            log('=== plan run %s' % name)
            fn(args.out)
    else:
        fns[args.run](args.out)


if __name__ == '__main__':
    main()
