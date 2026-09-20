"""Fnd integrity check: verify every landed parquet against its manifest.

Read-only quality gate for the extract output (data/fnd): re-reads every
manifest.json under data/fnd/, verifies each recorded file exists with the
recorded row count, and prints the per-dataset table that feeds
docs/datasets/parquet-foundations.md.

Usage:
  uv run python3 src/pipelines/01_extract_dataset/qa_fnd.py
"""
import datetime
import json
import os

import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FND = os.path.join(ROOT, 'data', 'fnd')


def dir_size_mb(path):
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(dirpath, f))
    return total / 1e6


print('%-8s %5s %14s %10s  %-21s %s' % ('dataset', 'files', 'rows', 'out_MB', 'ts_range', 'ok'))
grand = 0
for name in ['ukdale', 'ampds2', 'redd', 'refit', 'greend', 'eco']:
    man = json.load(open(os.path.join(FND, name, 'manifest.json')))
    total, bad = 0, []
    for key, e in sorted(man['files'].items()):
        if 'path' not in e:
            continue  # summary-only entry (eco per-house plug counts)
        if not os.path.exists(e['path']):
            bad.append(key + ':missing')
            continue
        n = pq.ParquetFile(e['path']).metadata.num_rows
        if n != e['rows']:
            bad.append('%s:%d!=%d' % (key, n, e['rows']))
        total += n
    lo = min(e['ts_min_us'] for e in man['files'].values() if e.get('ts_min_us'))
    hi = max(e['ts_max_us'] for e in man['files'].values() if e.get('ts_max_us'))
    utc = datetime.timezone.utc
    lo_s = datetime.datetime.fromtimestamp(lo / 1e6, tz=utc).strftime('%Y-%m-%d') if lo > -6e16 else 'NULL-ok'
    hi_s = datetime.datetime.fromtimestamp(hi / 1e6, tz=utc).strftime('%Y-%m-%d')
    du = dir_size_mb(os.path.join(FND, name))
    print('%-8s %5d %14d %10.0f  %s..%s  %s' % (name, len(man['files']), total, du, lo_s, hi_s, 'OK' if not bad else 'BAD ' + '; '.join(bad[:4])))
    grand += total
print('TOTAL rows:', grand)
