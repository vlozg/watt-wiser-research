"""Extract AMPds2 CSVs (electricity channels + aggregate + gas/water/climate) to parquet.

Source: data/raw/AMPds2/{Electricity,NaturalGas,Water,Climate}_*.csv. First column
is unix seconds as stored by the dataset (Edmonton home; semantics preserved).
Non-numeric timestamp columns (Climate) are parsed as datetime, else kept as
nullable Int64 with a manifest note. h5/PDF files are not converted.
ts_us = unix_seconds * 1e6.

Usage: uv run python3 src/pipelines/01_extract_dataset/extract_ampds2.py [--force]
Writes: data/fnd/ampds2/*.parquet + manifest.json
"""
import argparse, glob, os, time
import numpy as np
import pandas as pd

from wattwiser import DATA, FND, RAW, done, ensure, load_manifest, log, record, save_manifest, stat_parquet, write_parquet
from wattwiser.labels import canonical_label, h5_metadata, write_slice

def extract(force=False):
    name = 'ampds2'
    notes = ['source: data/raw/AMPds2/*.csv (Electricity/NaturalGas/Water/Climate); first col = unix seconds as stored',
             'ts_us = unix_seconds * 1e6; all other columns verbatim numeric; h5/PDFs not converted',
             'Climate CSVs use datetime strings or unparseable first cols - see per-file note field']
    man = load_manifest(name, notes)
    outdir = os.path.join(FND, name)
    ensure(outdir)
    for src in sorted(glob.glob(os.path.join(RAW, 'AMPds2', '*.csv'))):
        base = os.path.basename(src)[:-4]
        if not force and done(man, base):
            continue
        t0 = time.time()
        df = pd.read_csv(src)
        first = df.columns[0]
        ts_raw = df.pop(first)
        num = pd.to_numeric(ts_raw, errors='coerce')
        note = ''
        if num.notna().mean() > 0.999 and num.abs().median() > 1e8:
            ts_us = (num * 1e6).astype('int64')
        else:
            dt = pd.to_datetime(ts_raw, errors='coerce')
            if dt.notna().mean() > 0.999:
                ts_us = (dt.astype('int64') // 1000)
                note = 'first col %r parsed as datetime -> ts_us' % first
            else:
                ts_us = ((num * 1e6).round()).astype('Int64')
                note = 'first col %r unparseable; ts_us nullable' % first
        df.insert(0, 'ts_us', ts_us)
        df = df.apply(pd.to_numeric, errors='coerce')
        out = os.path.join(outdir, base + '.parquet')
        write_parquet(df, out)
        st = stat_parquet(out)
        if st['rows'] != len(df):
            raise RuntimeError('row mismatch %s' % base)
        record(man, name, base, out, src, st, t0, src_cols=first, note=note,
               src_bytes=os.path.getsize(src))
        log('%s: %d rows x %d cols (%.0fs) %s' % (base, len(df), df.shape[1], time.time() - t0, note))

def extract_labels():
    """Meter labels from the NILMTK building1 metadata (abbrev names + descriptions)."""
    import tables
    src = 'data/raw/AMPds2/AMPds2.h5'
    with tables.open_file(os.path.join(RAW, 'AMPds2', 'AMPds2.h5'), 'r') as h:
        md = h5_metadata(h.get_node('/building1'))
    site = [k for k, v in md.get('elec_meters', {}).items() if v.get('site_meter')]
    meters = {}
    for a in md.get('appliances', []):
        # AMPds2 stores abbreviations (CWE/DWE/FGE) as original_name; the human
        # name lives in 'description' (type is just 'unknown'/'light'/'sockets')
        label = str(a.get('original_name') or a.get('type'))
        canon = canonical_label(label + ' ' + str(a.get('description') or ''))
        for m in a.get('meters') or []:
            meters.setdefault(str(m), []).append({
                'label': label, 'canonical': canon,
                'type': a.get('type'), 'description': a.get('description'),
                'room': a.get('room')})
    return {'building_1': {'source': src, 'site_meters': site, 'meters': meters}}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_ampds2.json')
    a = ap.parse_args()
    if a.labels:
        log('=== ampds2 labels ===')
        log('wrote %s' % write_slice('ampds2', extract_labels()))
        log('=== done ampds2 labels ===')
    else:
        log('=== ampds2 extract ===')
        extract(force=a.force)
        log('=== done ampds2 ===')
