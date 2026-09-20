#!/usr/bin/env python3
"""Gold quality gate: verify gold tables against their fnd sources.

Runs after the gold build (src/pipelines/03_gold_nilm) the way qa_raw.py
(01_extract_dataset) runs after extract: read-only, and imports nothing
from the builders, so a builder bug cannot hide behind shared code.

For every table recorded in data/gold/<ds>/manifest.json this re-derives the
expected series from fnd and checks:

- rows: gold rows == source rows (minus un-timestamped rows gold drops)
- endpoints: first/last ts_us match the source
- values: sum(w) matches exactly for copy-throughs (redd mains: sum of the
  site meters, same convention as the builder)
- labels: every labeled meter in appliance_map.json has a gold table under
  the documented naming rule (canonical for the 5 targets, label slug
  otherwise) with matching label/canonical identity fields; the on-threshold
  recomputes to the stored thresholds.json value

Prints one line per dataset and a TOTAL; exits 1 on any failure.

Usage:
  uv run python3 src/pipelines/03_gold_nilm/qa_gold.py
"""
import json
import os
import sys

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
GOLD = os.path.join(ROOT, 'data', 'gold')
NOISE_FLOOR_W = 5.0
MIN_SAMPLES = 100
AGGREGATE_LABELS = {'aggregate', 'site_meter', 'mains'}


def slug(label):
    import re
    return re.sub(r'[^a-z0-9]+', '_', str(label).lower()).strip('_') or 'unlabeled'


def expected_names(entries):
    """The documented gold naming rule: canonical first, then slugs."""
    used, out = set(), [None] * len(entries)
    for i, e in enumerate(entries):
        c = e.get('canonical')
        if c and c not in used:
            used.add(c)
            out[i] = c
    for i, e in enumerate(entries):
        if out[i]:
            continue
        base = slug(e.get('canonical') or e.get('label'))
        n, cand = 2, base
        while cand in used:
            cand = '%s_%d' % (base, n)
            n += 1
        used.add(cand)
        out[i] = cand
    return out


def labeled_entries(bd):
    """All labeled meter entries of one building, excluding aggregate labels.

    Map values may be a single dict or a list (GREEND meters can carry
    several plug labels) - every entry counts.
    """
    out = []
    for src in ('channels', 'meters', 'appliances', 'plugs'):
        for k in sorted(bd.get(src) or {}):
            v = bd[src][k]
            for vv in (v if isinstance(v, list) else [v]):
                if isinstance(vv, dict) and vv.get('label') \
                        and vv['label'].lower() not in AGGREGATE_LABELS:
                    out.append(vv)
    return out

# per-dataset value column conventions (mirror 03_gold_nilm/_common.py)
MAINS_COL = {'ukdale': 'v0', 'eco': 'powerallphases', 'redd': 'value_0',
             'ampds2': 'P', 'refit': 'Aggregate'}
VALUE_COL = {'ukdale': 'v0', 'eco': 'consumption', 'redd': 'value_0', 'ampds2': 'P'}


def fnd_series(src, ds, is_mains):
    """Load one fnd source ('path' or 'path#col') -> (ts, w) with null ts dropped."""
    path, col = src.split('#', 1) if '#' in src else (src, None)
    if col is None:
        col = MAINS_COL[ds] if is_mains else VALUE_COL[ds]
    t = pq.read_table(path, columns=['ts_us', col])
    m = np.asarray(pc.is_valid(t.column('ts_us')))
    ts = t.column('ts_us').to_numpy(zero_copy_only=False)[m].astype('int64')
    w = t.column(col).to_numpy(zero_copy_only=False).astype('float64')[m]
    return ts, w


def read_gold(path):
    t = pq.read_table(path, columns=['ts_us', 'w'])
    return (t.column('ts_us').to_numpy().astype('int64'),
            t.column('w').to_numpy().astype('float64'))


def check_table(ds, key, rec, fails):
    ts_g, w_g = read_gold(rec['path'])
    srcs = rec['src'] if isinstance(rec['src'], list) else [rec['src']]
    is_mains = key.endswith('/mains')
    if is_mains and ds == 'redd':
        # mains = keyed sum of the site meters (identical timestamp grids)
        ts_exp, w_exp = fnd_series(srcs[0], ds, True)
        for s in srcs[1:]:
            _, wv = fnd_series(s, ds, True)
            w_exp = w_exp + wv
    else:
        ts_exp, w_exp = fnd_series(srcs[0], ds, is_mains)
    ok = True
    if len(ts_g) != len(ts_exp):
        ok, msg = False, 'rows %d != %d' % (len(ts_g), len(ts_exp))
    elif len(ts_g) and (ts_g[0] != ts_exp[0] or ts_g[-1] != ts_exp[-1]):
        ok, msg = False, 'endpoints differ (%d..%d vs %d..%d)' % (
            ts_g[0], ts_g[-1], ts_exp[0], ts_exp[-1])
    elif abs(w_g.sum() - w_exp.sum()) > 1e-6 * max(1.0, abs(w_exp.sum())):
        ok, msg = False, 'sum(w) differs: %.6e vs %.6e' % (w_g.sum(), w_exp.sum())
    else:
        msg = 'rows=%d sum=%.6e' % (len(ts_g), w_g.sum())
    if not ok:
        fails.append('%s/%s: %s' % (ds, key, msg))
    return ok, msg


def recompute_thr(w):
    """The documented threshold rule (thresholds.json _meta.method)."""
    nz = w[np.isfinite(w)]
    nz = nz[nz > NOISE_FLOOR_W]
    if len(nz) < MIN_SAMPLES:
        return NOISE_FLOOR_W, round(float(np.median(nz)), 1) if len(nz) else 0.0
    p50 = float(np.percentile(nz, 50))
    return round(max(NOISE_FLOOR_W, 0.5 * p50), 1), round(p50, 1)


def main():
    amap = json.load(open(os.path.join(GOLD, 'appliance_map.json')))
    th = json.load(open(os.path.join(GOLD, 'thresholds.json')))
    fails, total = [], 0
    for ds in sorted(k for k in amap if k != '_meta'):
        with open(os.path.join(GOLD, ds, 'manifest.json')) as fh:
            man = json.load(fh)
        n_ok = 0
        for key, rec in sorted(man['files'].items()):
            total += 1
            ok, msg = check_table(ds, key, rec, fails)
            n_ok += ok
            if not ok:
                print('  FAIL %-28s %s' % (key, msg))
        # label coverage: every labeled meter has a gold table under the
        # documented naming rule, with matching identity fields
        n_labeled = 0
        n_canon = 0
        for b, bd in amap[ds].items():
            entries = labeled_entries(bd)
            n_labeled += len(entries)
            n_canon += sum(1 for e in entries if e.get('canonical'))
            for e, name in zip(entries, expected_names(entries)):
                rec = man['files'].get('%s/%s' % (b, name))
                if not rec:
                    fails.append('%s/%s: no gold table for labeled meter %r'
                                 % (ds, b, e['label']))
                    continue
                if rec.get('label') != e['label'] \
                        or rec.get('canonical') != e.get('canonical'):
                    fails.append('%s/%s: identity mismatch %r: gold (%r/%r)'
                                 ' vs map (%r/%r)'
                                 % (ds, b, name, rec.get('label'), rec.get('canonical'),
                                    e['label'], e.get('canonical')))
        n_gold = len([k for k in man['files'] if not k.endswith('/mains')])
        if n_gold != n_labeled:
            fails.append('%s: %d gold appliance tables != %d labeled meters'
                         % (ds, n_gold, n_labeled))
        # thresholds present and reproducible from the source data
        for key, rec in sorted(man['files'].items()):
            if key.endswith('/mains'):
                continue
            b, name = key.split('/', 1)
            srcs = rec['src'] if isinstance(rec['src'], list) else [rec['src']]
            _, w = fnd_series(srcs[0], ds, False)
            thr, p50 = recompute_thr(w)
            stored = th.get(ds, {}).get(b, {}).get(name)
            if not stored or abs(stored['thr_on_W'] - thr) > 1e-9 \
                    or abs(stored['p50_on_W'] - p50) > 1e-9:
                fails.append('%s/%s: threshold mismatch (recomputed %s/%s, stored %s)'
                             % (ds, key, thr, p50, stored and stored['thr_on_W']))
        print('%-8s %3d/%3d tables verified, %d labeled meters (%d canonical)' % (ds, n_ok, len(man['files']), n_labeled, n_canon))
    print('TOTAL %d tables, %d failures' % (total, len(fails)))
    for f in fails:
        print('FAIL ' + f)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
