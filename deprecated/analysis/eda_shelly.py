#!/usr/bin/env python3
"""
eda_shelly.py -- rigorous EDA battery for a low-rate power series, with a
domain-shift comparison against a real-data reference.

WHY
  The question is never "is this CSV pretty" but "does this data behave like a real
  house at the rate this sensor actually delivers". That is answered by a fixed
  battery of computable statistics, compared against a reference computed once on
  the local UK-DALE slice (6 s, 70.66 days - provenance under INPUT) and stored as JSON.

USAGE
  # 1) build the reference once (local UK-DALE slice):
  python3 eda_shelly.py ukdale --make-reference --out OUTDIR
  # 2) judge any future CSV against it:
  python3 eda_shelly.py shelly_export.csv --reference eda_reference_ukdale.json --out OUTDIR

INPUT
  A CSV with a timestamp column and a whole-house power column (any of:
  active_power_W, power_W, power, Power_W, active_power, load_W) plus optional
  per-appliance columns named <name>_power_W. The *_on flags are ignored; ON states
  are recomputed from power, so the script is rate-agnostic and label-free.
  A schema check runs before any metric: every guess or contract deviation emits a
  WARN line on stderr and is recorded in the report's Schema section.
  Or the keyword 'ukdale' to load the local UK-DALE slice. PROVENANCE (forensics
  2026-09-21): the slice (research-logs/sakunrasilka_nilm-test2) is UK-DALE
  house-5 data relabeled house_1-style -- channel_2/3/4/6 are byte-exact copies of
  h5 fridge_freezer / dishwasher / kettle / i7_desktop; channel_5 matches no
  house_1-5 channel verbatim. channel_1 is a synthetic aggregate = sum of 2-6 plus
  a flat injected base (about 27 W), so the slice has NO real residual and is NOT
  house_1; authoritative UK-DALE numbers: docs/reports/dataset_eda/01_ukdale_eda_review.md;
  the full house-1 download adds the real mains.

OUTPUTS (in --out)
  report.md, metrics.json, reference_metrics.json (with --make-reference),
  eda_fig01_ladder.png, eda_fig02_week.png, eda_fig03_day.png, eda_fig04_events.png

Event detection here is deliberately simple (thresholds + run-length encoding).
The production upgrade path is PELT via 'ruptures' -- see
docs/research/analog-problems.md section 2.5. Domain-shift judging does not need it.

Context numbers this battery is calibrated against
(docs/product/product-core-reframe.md, docs/client/repo-review.md): the slice has 715.7 aggregate steps
above 30 W per day vs about 111 genuine appliance transitions; 2+ appliances
simultaneously ON 32.6% of the time (monitor-dominated: the 'monitor' channel is h5's
always-on i7_desktop; gold-EDA house-1 2+ ON is 3.0% of 60 s buckets - see
docs/reports/dataset_eda/01_ukdale_eda_review.md); the WattWiser synthetic set has 1.71% and a
daily-template base load (lag-1day autocorr of the base 0.893, identical every day).
"""
import argparse
import json
import os
import re
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt

POWER_KEYS = ['active_power_W', 'power_W', 'Power_W', 'power', 'active_power', 'load_W']
TS_KEYS = ['timestamp', 'Timestamp', 'time', 'Time', 'datetime']
APP_RE = re.compile(r'^([A-Za-z0-9_]+)_power_?[Ww]$')

_HERE = os.path.dirname(os.path.abspath(__file__))
UKDALE_CANDIDATES = [
    # repo-relative, independent of cwd / machine
    os.path.join(os.path.dirname(os.path.dirname(_HERE)), 'research-logs', 'sakunrasilka_nilm-test2'),
]
# Labels below are the slice's own house_1-style names. Signal identities (forensics
# 2026-09-21): house-5 channels - 2=fridge_freezer, 3=dishwasher, 4=kettle,
# 6=i7_desktop; 5 matches no house_1-5 channel verbatim. Dict kept for output-label
# stability; see the module docstring INPUT section.
UKDALE_CH = {2: 'fridge', 3: 'dish_washer', 4: 'kettle', 5: 'washing_machine', 6: 'monitor'}

# ---------------------------------------------------------------- loading

def load_ukdale():
    base = next((b for b in UKDALE_CANDIDATES if os.path.isdir(b)), None)
    if base is None:
        sys.exit('UK-DALE slice not found in: %s' % ', '.join(UKDALE_CANDIDATES))
    arrays = {}
    for c in range(1, 7):
        arrays[c] = np.loadtxt(os.path.join(base, 'channel_%d.dat' % c), ndmin=2)
    cstart = max(a[0, 0] for a in arrays.values())
    cend = min(a[-1, 0] for a in arrays.values())
    keep = {}
    for c, a in arrays.items():
        msk = (a[:, 0] >= cstart) & (a[:, 0] <= cend)
        keep[c] = a[msk]
    n = min(len(v) for v in keep.values())
    df = pd.DataFrame({'ts': pd.to_datetime(keep[1][:n, 0], unit='s'),
                       'power': keep[1][:n, 1].astype(float)})
    apps = {nm: keep[c][:n, 1].astype(float) for c, nm in UKDALE_CH.items()}
    return df, apps, None

def schema_check(raw, ts_col, ts_guessed, pow_col, pow_guessed, app_cols):
    """Validate the raw CSV against the input contract before any metric runs.

    Contract (module docstring INPUT): a timestamp column, a whole-house power
    column, optional <name>_power_W per-appliance columns. Anything that had to be
    GUESSED, or deviates from the contract, is a WARN on stderr and is recorded in
    the returned dict -- which lands in metrics.json and report.md so the column
    interpretation is auditable next to the verdicts. Warnings never abort the run
    except where the data is unusable (unparseable timestamps).
    """
    S = {'ts_column': ts_col, 'power_column': pow_col,
         'appliance_columns': sorted(app_cols), 'ignored_columns': [], 'warnings': []}

    def warn(msg):
        S['warnings'].append(msg)
        print('WARN [schema] %s' % msg, file=sys.stderr)

    if ts_guessed:
        warn("timestamp column guessed as '%s' (no exact match in %s) -- verify it is the time axis"
             % (ts_col, TS_KEYS))
    if pow_guessed:
        warn("power column guessed by heuristic as '%s' (no exact match in %s)"
             % (pow_col, POWER_KEYS))

    ts_parsed = pd.to_datetime(raw[ts_col], errors='coerce')
    n_bad = int(ts_parsed.isna().sum())
    if n_bad == len(raw):
        sys.exit("timestamp column '%s' has no parseable values" % ts_col)
    if n_bad:
        warn('%d of %d timestamp values unparseable -> NaT' % (n_bad, len(raw)))
    tz = getattr(ts_parsed.dtype, 'tz', None)
    S['tz'] = str(tz) if tz is not None else 'naive'
    if ts_parsed.duplicated().any():
        warn('%d duplicate timestamps' % int(ts_parsed.duplicated().sum()))
    if len(ts_parsed) > 1 and not ts_parsed.is_monotonic_increasing:
        warn('timestamps not monotonically increasing')

    pv = pd.to_numeric(raw[pow_col], errors='coerce')
    n_nan = int(pv.isna().sum())
    if n_nan:
        warn("power column '%s' has %d non-numeric/missing values" % (pow_col, n_nan))
    med = float(pv.median()) if len(pv) else float('nan')
    if med == med:
        if med < 0:
            warn('median power %.1f W is negative' % med)
        elif med < 20:
            warn('median power %.1f W looks like kW, not W -- unit mismatch?' % med)

    for c in raw.columns:
        if c in (ts_col, pow_col) or APP_RE.match(c):
            continue
        if c.endswith('_on'):
            name = c[:-3]
            if name + '_power_W' not in raw.columns and (name + '_power') not in raw.columns:
                warn("ON flag '%s' has no matching '%s_power_W' column; flag ignored "
                     '(ON states are recomputed from power)' % (c, name))
        elif c.lower().endswith(('_w', '_va', '_kw', '_watt')) or 'power_w' in c.lower():
            warn("column '%s' looks like a power channel but does not match the "
                 '<name>_power_W convention; ignored' % c)
        S['ignored_columns'].append(c)
    return S


def load_csv(path):
    raw = pd.read_csv(path)
    ts_col = next((c for c in TS_KEYS if c in raw.columns), raw.columns[0])
    ts_guessed = ts_col not in TS_KEYS
    pow_col = next((c for c in POWER_KEYS if c in raw.columns), None)
    pow_guessed = False
    if pow_col is None:
        cand = [c for c in raw.columns if 'power' in c.lower() and not c.endswith('_on')]
        if not cand:
            sys.exit('no power column found; columns: %s' % list(raw.columns))
        pow_col = cand[0]
        pow_guessed = True
    app_cols = {}
    for c in raw.columns:
        mth = APP_RE.match(c)
        if mth and c != pow_col:
            app_cols[mth.group(1)] = pd.to_numeric(raw[c], errors='coerce').values.astype(float)
    S = schema_check(raw, ts_col, ts_guessed, pow_col, pow_guessed, app_cols)
    out = pd.DataFrame({'ts': pd.to_datetime(raw[ts_col]),
                        'power': pd.to_numeric(raw[pow_col], errors='coerce').values.astype(float)})
    return out, app_cols, S

# ---------------------------------------------------------------- primitives

def run_lengths(mask):
    d = np.diff(mask.astype(np.int8))
    starts = np.where(d == 1)[0] + 1
    ends = np.where(d == -1)[0] + 1
    if mask[0]:
        starts = np.r_[0, starts]
    if mask[-1]:
        ends = np.r_[ends, len(mask)]
    if len(starts) == 0:
        return np.empty(0, int), np.empty(0, int)
    return starts, ends - starts

def psi(new, ref, bins=10):
    """Population Stability Index over quantile bins of ref.
    <0.1 no shift, 0.1-0.25 moderate, >0.25 major (credit-scoring convention)."""
    ref = np.asarray(ref, float); new = np.asarray(new, float)
    edges = np.quantile(ref, np.linspace(0, 1, bins + 1))
    edges[0] = -np.inf; edges[-1] = np.inf
    edges = np.maximum.accumulate(edges)
    refp = np.histogram(ref, edges)[0] / max(len(ref), 1)
    newp = np.histogram(new, edges)[0] / max(len(new), 1)
    refp = np.clip(refp, 1e-6, None); newp = np.clip(newp, 1e-6, None)
    return float(np.sum((newp - refp) * np.log(newp / refp)))

def on_mask(ap):
    """ON = power above a per-appliance floor: 5 W or 2% of p95, whichever is larger."""
    p95 = np.percentile(ap, 95) if len(ap) else 0.0
    return ap > max(5.0, 0.02 * p95)

# ---------------------------------------------------------------- the battery

def compute_metrics(df, apps):
    m = {}
    ts = df['ts'].values
    p = df['power'].values.astype(float)
    n = len(p)
    sec = (ts[-1] - ts[0]) / np.timedelta64(1, 's')
    days = sec / 86400.0
    dt_all = np.diff(ts) / np.timedelta64(1, 's')
    dt_med = float(np.median(dt_all))
    m['sampling'] = {
        'rows': int(n), 'span_days': round(days, 2), 'dt_median_s': dt_med,
        'dt_min_s': float(dt_all.min()), 'dt_max_s': float(dt_all.max()),
        'gap_fraction': round(float(np.mean(dt_all > 3 * dt_med)), 4),
    }
    pct = np.percentile(p, [1, 5, 25, 50, 75, 95, 99])
    day_key = df['ts'].dt.date
    dp10 = df.groupby(day_key)['power'].quantile(0.10).dropna()
    m['power'] = {
        'mean_W': round(float(p.mean()), 1), 'p1_W': round(float(pct[0]), 1),
        'p5_W': round(float(pct[1]), 1), 'p25_W': round(float(pct[2]), 1),
        'p50_W': round(float(pct[3]), 1), 'p75_W': round(float(pct[4]), 1),
        'p95_W': round(float(pct[5]), 1), 'p99_W': round(float(pct[6]), 1),
        'max_W': round(float(p.max()), 1),
        'always_on_W': round(float(np.median(dp10.values)), 1) if len(dp10) else round(float(pct[1]), 1),
    }
    d = np.abs(np.diff(p))
    quiet = (p[:-1] < pct[2]) & (p[1:] < pct[2])
    m['steps'] = {
        'dP_p50_W': round(float(np.percentile(d, 50)), 1),
        'dP_p90_W': round(float(np.percentile(d, 90)), 1),
        'dP_p99_W': round(float(np.percentile(d, 99)), 1),
        'noise_floor_W': round(float(np.median(d[quiet])), 1) if quiet.any() else None,
        'steps_per_day_gt30W': round(float(np.sum(d > 30) / days), 1),
        'steps_per_day_gt100W': round(float(np.sum(d > 100) / days), 1),
        'steps_per_day_gt300W': round(float(np.sum(d > 300) / days), 1),
    }
    hr = df['ts'].dt.hour.values
    prof = [float(p[hr == h].mean()) for h in range(24)]
    L = int(round(86400.0 / dt_med))
    m['diurnal'] = {
        'hourly_mean_W': [round(x, 1) for x in prof],
        'peak_hour': int(int(np.argmax(prof))), 'trough_hour': int(int(np.argmin(prof))),
        'peak_over_trough': round(float(max(prof) / max(min(prof), 1e-9)), 2),
    }
    if n > 2 * L:
        m['diurnal']['lag1day_autocorr'] = round(float(np.corrcoef(p[:-L], p[L:])[0, 1]), 3)
    wd = df['ts'].dt.dayofweek.values
    m['diurnal']['weekday_mean_W'] = round(float(p[wd < 5].mean()), 1)
    m['diurnal']['weekend_mean_W'] = round(float(p[wd >= 5].mean()), 1)
    tot_e = float(p.sum() * dt_med)
    m['appliances'] = {}
    masks = {}
    for nm, ap in apps.items():
        mask = on_mask(ap)
        masks[nm] = mask
        starts, lens = run_lengths(mask)
        on_p = ap[mask]
        durs = lens * dt_med / 60.0
        dap = np.abs(np.diff(ap))
        tr = np.where(np.diff(mask.astype(np.int8)) != 0)[0]
        m['appliances'][nm] = {
            'energy_share_pct': round(100 * float(ap.sum() * dt_med) / tot_e, 1) if tot_e else None,
            'duty_pct': round(100 * float(mask.mean()), 1),
            'median_on_W': round(float(np.median(on_p)), 0) if len(on_p) else 0,
            'events_per_day': round(float(len(lens) / days), 2) if days else 0,
            'on_minutes_p50': round(float(np.percentile(durs, 50)), 1) if len(durs) else None,
            'on_minutes_p90': round(float(np.percentile(durs, 90)), 1) if len(durs) else None,
            'transition_step_p50_W': round(float(np.median(dap[tr])), 0) if len(tr) else None,
        }
    if masks:
        non = np.zeros(n, int)
        for mask in masks.values():
            non += mask.astype(int)
        m['overlap'] = {
            'frac_0_on_pct': round(100 * float(np.mean(non == 0)), 1),
            'frac_1_on_pct': round(100 * float(np.mean(non == 1)), 1),
            'frac_2plus_on_pct': round(100 * float(np.mean(non >= 2)), 1),
        }
    return m

# ---------------------------------------------------------------- comparison

def compare(m, ref):
    rows = []
    def row(metric, a, b, lo, hi, fmt='{:.2f}'):
        if a is None or b is None:
            return
        ratio = float(a) / float(b) if b else float('inf')
        verdict = 'PASS' if lo <= ratio <= hi else 'FLAG'
        rows.append({'metric': metric, 'input': fmt.format(a), 'reference': fmt.format(b),
                     'ratio': round(ratio, 2), 'verdict': verdict})
    s, rs = m['sampling'], ref['sampling']
    row('dt median (s)', s['dt_median_s'], rs['dt_median_s'], 0.99, 1.01, '{:.1f}')
    row('span (days)', s['span_days'], rs['span_days'], 0.3, 30.0, '{:.1f}')
    pw, rpw = m['power'], ref['power']
    row('mean power (W)', pw['mean_W'], rpw['mean_W'], 0.3, 3.0, '{:.0f}')
    row('always-on estimate (W)', pw['always_on_W'], rpw['always_on_W'], 0.25, 4.0, '{:.0f}')
    st, rst = m['steps'], ref['steps']
    row('steps/day >30 W', st['steps_per_day_gt30W'], rst['steps_per_day_gt30W'], 0.25, 4.0, '{:.1f}')
    row('steps/day >300 W', st['steps_per_day_gt300W'], rst['steps_per_day_gt300W'], 0.1, 10.0, '{:.1f}')
    row('noise floor (W)', st['noise_floor_W'], rst['noise_floor_W'], 0.25, 4.0, '{:.1f}')
    row('lag-1day autocorr', m['diurnal'].get('lag1day_autocorr'),
        ref['diurnal'].get('lag1day_autocorr'), 0.05, 20.0, '{:.2f}')
    if 'overlap' in m and 'overlap' in ref:
        row('2+ appliances ON (%)', m['overlap']['frac_2plus_on_pct'],
            ref['overlap']['frac_2plus_on_pct'], 0.25, 4.0, '{:.1f}')
    pv = psi(np.array(m['diurnal']['hourly_mean_W']), np.array(ref['diurnal']['hourly_mean_W']), bins=8)
    rows.append({'metric': 'diurnal profile PSI', 'input': '%.3f' % pv, 'reference': '0.000',
                 'ratio': None,
                 'verdict': 'PASS' if pv < 0.1 else ('MODERATE' if pv < 0.25 else 'FLAG')})
    return rows

# ---------------------------------------------------------------- figures

def make_figures(df, apps, outdir):
    p = df['power'].values.astype(float)
    ts = df['ts']
    day0 = ts.min().normalize()
    d0 = df[(ts >= day0) & (ts < day0 + pd.Timedelta(days=1))]
    dt_med = float(np.median(np.diff(ts.values) / np.timedelta64(1, 's')))
    # fig01: resolution ladder
    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    y0 = d0['power'].values
    for ax, (ttl, k) in zip(axes, [('native', 1), ('60 s', max(int(round(60 / dt_med)), 1)),
                                   ('300 s', max(int(round(300 / dt_med)), 1))]):
        if k <= 1:
            ax.plot(d0['ts'], y0, lw=0.6, color='tab:red')
        else:
            kk = min(k, max(len(y0) // 2, 1))
            yb = y0[:len(y0) // kk * kk].reshape(-1, kk).mean(axis=1)
            ax.plot(d0['ts'].values[::kk][:len(yb)], yb, lw=0.8, color='tab:red')
        ax.set_ylabel('W'); ax.set_title('sampling: %s' % ttl, fontsize=9)
    fig.suptitle('fig01 analogue: one day at three sampling rates (the ladder)')
    fig.tight_layout(); fig.savefig(os.path.join(outdir, 'eda_fig01_ladder.png'), dpi=150); plt.close(fig)
    # fig02: the week
    wk = df[ts < ts.min() + pd.Timedelta(days=7)]
    fig, ax = plt.subplots(figsize=(11, 3.2))
    ax.plot(wk['ts'], wk['power'], lw=0.4, color='tab:blue')
    ax.set_ylabel('W'); ax.set_title('fig02 analogue: the week unrolled')
    fig.tight_layout(); fig.savefig(os.path.join(outdir, 'eda_fig02_week.png'), dpi=150); plt.close(fig)
    # fig03: one day with appliances
    fig, ax = plt.subplots(figsize=(11, 3.4))
    ax.plot(d0['ts'], d0['power'], lw=0.5, color='k', label='whole house')
    for nm, ap in apps.items():
        ax.plot(d0['ts'].values, np.asarray(ap, float)[:len(d0)], lw=0.4, alpha=0.7, label=nm)
    ax.legend(fontsize=7, ncol=6); ax.set_ylabel('W')
    ax.set_title('fig03 analogue: one day, whole house + appliances')
    fig.tight_layout(); fig.savefig(os.path.join(outdir, 'eda_fig03_day.png'), dpi=150); plt.close(fig)
    # fig04: event view
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    ax = axes[0][0]
    d = np.abs(np.diff(p)); d = d[d > 0.5]
    if len(d):
        ax.hist(d, bins=np.logspace(0, np.log10(max(d.max(), 10.0)), 60), color='tab:red')
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_title('(a) whole-house step sizes |dP|'); ax.set_xlabel('W')
    ax = axes[0][1]
    prof = [float(p[df['ts'].dt.hour.values == h].mean()) for h in range(24)]
    ax.plot(range(24), prof, 'o-', color='tab:blue', ms=3)
    ax.set_title('(b) hourly profile'); ax.set_xlabel('hour'); ax.set_ylabel('mean W')
    ax = axes[1][0]
    for nm, ap in apps.items():
        ap = np.asarray(ap, float); mask = on_mask(ap)
        tr = np.where(np.diff(mask.astype(np.int8)) != 0)[0]
        if len(tr):
            xs = np.sort(np.abs(np.diff(ap))[tr])
            ax.plot(xs, np.linspace(0, 1, len(xs)), label=nm, lw=1.2)
    ax.set_xscale('log'); ax.set_title('(c) appliance transition steps, ECDF'); ax.set_xlabel('|dP| W')
    ax.legend(fontsize=7)
    ax = axes[1][1]
    for nm, ap in apps.items():
        ap = np.asarray(ap, float); mask = on_mask(ap)
        starts, lens = run_lengths(mask)
        if len(lens):
            xs = np.sort(lens) * dt_med / 60.0
            ax.plot(xs, np.linspace(0, 1, len(xs)), label=nm, lw=1.2)
    ax.set_xscale('log'); ax.set_title('(d) ON durations, ECDF'); ax.set_xlabel('minutes')
    ax.legend(fontsize=7)
    fig.suptitle('fig04 analogue: reading events, not shapes')
    fig.tight_layout(); fig.savefig(os.path.join(outdir, 'eda_fig04_events.png'), dpi=150); plt.close(fig)

# ---------------------------------------------------------------- report

def fmt_table(rows, header):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join(['---'] * len(header)) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(r.get(h, '')) for h in header) + ' |')
    return '\n'.join(out)

def write_report(m, cmp_rows, outdir, src, ref_name):
    L = []
    L.append('# EDA report -- %s' % src)
    if ref_name:
        L.append('')
        L.append('Compared against reference: %s (UK-DALE slice, 6 s, one UK home, 70.66 days).' % ref_name)
    L.append('')
    L.append('Generated by eda_shelly.py (watt-wiser research repo). Fixed metrics battery; '
             'verdicts PASS/FLAG are ratio bands around the reference, PSI follows the '
             'credit-scoring convention (<0.1 none, 0.1-0.25 moderate, >0.25 major).')
    L.append('')
    if m.get('schema') is not None:
        S = m['schema']
        L.append('## Schema')
        L.append('')
        L.append('timestamp column: `%s` | power column: `%s` | appliance columns: %s'
                 % (S['ts_column'], S['power_column'],
                    ', '.join('`%s`' % c for c in S['appliance_columns']) or 'none'))
        if S['ignored_columns']:
            L.append('')
            L.append('ignored columns: %s' % ', '.join('`%s`' % c for c in S['ignored_columns']))
        L.append('')
        if S['warnings']:
            L.append('**%d schema warning(s):**' % len(S['warnings']))
            L.append('')
            for w in S['warnings']:
                L.append('- WARN: %s' % w)
            L.append('')
        else:
            L.append('No schema warnings.')
            L.append('')
    s = m['sampling']
    L.append('## Sampling')
    L.append(fmt_table([s], ['rows', 'span_days', 'dt_median_s', 'dt_min_s', 'dt_max_s', 'gap_fraction']))
    L.append('')
    L.append('## Power')
    L.append(fmt_table([m['power']], list(m['power'].keys())))
    L.append('')
    L.append('## Steps and events')
    L.append(fmt_table([m['steps']], list(m['steps'].keys())))
    L.append('')
    dd = {k: v for k, v in m['diurnal'].items() if k != 'hourly_mean_W'}
    L.append('## Diurnal')
    L.append(fmt_table([dd], list(dd.keys())))
    L.append('')
    if m['appliances']:
        L.append('## Appliances')
        first = next(iter(m['appliances'].values()))
        L.append(fmt_table([dict(r, appliance=nm) for nm, r in m['appliances'].items()],
                           ['appliance'] + list(first.keys())))
        L.append('')
    if 'overlap' in m:
        L.append('## Simultaneity')
        L.append(fmt_table([m['overlap']], list(m['overlap'].keys())))
        L.append('')
    if cmp_rows is not None:
        n_flag = sum(1 for r in cmp_rows if r['verdict'] == 'FLAG')
        L.append('## Domain shift vs reference')
        L.append('')
        L.append('%d of %d metrics FLAG. PASS = within the ratio band of the UK-DALE reference; '
                 'FLAG = this data does not behave like the reference on that axis.' % (n_flag, len(cmp_rows)))
        L.append('')
        L.append(fmt_table(cmp_rows, ['metric', 'input', 'reference', 'ratio', 'verdict']))
        L.append('')
    open(os.path.join(outdir, 'report.md'), 'w').write('\n'.join(L))
    json.dump(m, open(os.path.join(outdir, 'metrics.json'), 'w'), indent=1)

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', help="CSV path, or 'ukdale' for the local UK-DALE slice")
    ap.add_argument('--out', default='eda_out')
    ap.add_argument('--reference', default=None)
    ap.add_argument('--make-reference', action='store_true')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.input == 'ukdale':
        df, apps, schema = load_ukdale()
    else:
        df, apps, schema = load_csv(args.input)
    m = compute_metrics(df, apps)
    m['schema'] = schema
    make_figures(df, apps, args.out)
    cmp_rows = None
    if args.reference:
        cmp_rows = compare(m, json.load(open(args.reference)))
    write_report(m, cmp_rows, args.out, args.input, args.reference)
    if args.make_reference:
        json.dump(m, open(os.path.join(args.out, 'reference_metrics.json'), 'w'), indent=1)
    s = m['sampling']
    print('rows=%d span=%.2fd dt=%.1fs steps30/day=%.1f overlap2+=%s%%' % (
        s['rows'], s['span_days'], s['dt_median_s'], m['steps']['steps_per_day_gt30W'],
        m.get('overlap', {}).get('frac_2plus_on_pct')))
    if cmp_rows:
        flags = [r['metric'] for r in cmp_rows if r['verdict'] == 'FLAG']
        print('FLAG (%d): %s' % (len(flags), '; '.join(flags) if flags else 'none'))

if __name__ == '__main__':
    main()
