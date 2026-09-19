"""Extract UK-DALE full release (5 houses, 1 s mains + 6 s channels) to parquet.

Source: data/raw/ukdale-full/house_{1..5}/*.dat (whitespace-separated float unix
seconds + float watts). Every .dat converted, including *_button_press event
logs. ts_us = round(unix_seconds * 1e6).

Usage: uv run python3 src/pipelines/01_extract_dataset/extract_ukdale.py [--force]
Writes: data/fnd/ukdale/*.parquet + manifest.json
"""
import argparse, glob, os, re, shutil, time
import numpy as np
import pandas as pd

from wattwiser import DATA, FND, RAW, ROOT, done, ensure, load_manifest, log, record, save_manifest, stat_parquet, write_parquet
from wattwiser.labels import canonical_label, write_slice

def extract(force=False):
    name = 'ukdale'
    notes = ['source: data/raw/ukdale-full/house_{1..5}/*.dat; whitespace-separated float ts + watts',
             'ts_us = round(unix_seconds * 1e6); all .dat files converted (incl. button_press event logs)',
             'float32-safe: values stored float64 exactly as parsed']
    man = load_manifest(name, notes)
    for house in sorted(glob.glob(os.path.join(RAW, 'ukdale-full', 'house_*'))):
        hname = os.path.basename(house)
        outdir = os.path.join(FND, name, hname)
        ensure(outdir)
        # labels.dat maps channel_N -> appliance name; keep verbatim + README
        for aux in ('labels.dat', 'README.txt'):
            p = os.path.join(house, aux)
            if os.path.exists(p):
                shutil.copy(p, os.path.join(outdir, aux))
        for src in sorted(glob.glob(os.path.join(house, '*.dat'))):
            if os.path.basename(src) == 'labels.dat':
                continue
            base = os.path.basename(src)[:-4]
            base = os.path.basename(src)[:-4]
            key = hname + '/' + base
            if not force and done(man, key):
                continue
            t0 = time.time()
            with open(src) as fh:
                ncol = len(fh.readline().split())
            names = ['ts'] + ['v%d' % i for i in range(ncol - 1)]
            df = pd.read_csv(src, sep=r'\s+', header=None, names=names,
                             dtype=np.float64, engine='c')
            df.insert(0, 'ts_us', np.round(df.pop('ts') * 1e6).astype(np.int64))
            out = os.path.join(outdir, base + '.parquet')
            write_parquet(df, out)
            st = stat_parquet(out)
            if st['rows'] != len(df):
                raise RuntimeError('row mismatch %s: %d vs %d' % (key, st['rows'], len(df)))
            record(man, name, key, out, src, st, t0, src_bytes=os.path.getsize(src))
            log('%s: %d rows, %.0f MB -> %.0f MB (%.0fs)' % (
                key, len(df), os.path.getsize(src) / 1e6, st['bytes'] / 1e6, time.time() - t0))

def extract_labels():
    """Channel labels verbatim from house_N/labels.dat plus canonical mapping."""
    out = {}
    for f in sorted(glob.glob(os.path.join(RAW, 'ukdale-full', 'house_*', 'labels.dat'))):
        house = 'house_' + re.search(r'house_(\d+)', f).group(1)
        channels = {}
        for line in open(f, encoding='utf-8'):
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                label = ' '.join(parts[1].split())
                channels[parts[0]] = {'label': label, 'canonical': canonical_label(label)}
        out[house] = {'source': os.path.relpath(f, ROOT), 'channels': channels}
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_ukdale.json')
    a = ap.parse_args()
    if a.labels:
        log('=== ukdale labels ===')
        log('wrote %s' % write_slice('ukdale', extract_labels()))
        log('=== done ukdale labels ===')
    else:
        log('=== ukdale extract ===')
        extract(force=a.force)
        log('=== done ukdale ===')
