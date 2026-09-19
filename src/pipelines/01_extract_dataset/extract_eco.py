"""Extract ECO (6 Swiss households, 1 Hz aggregate + plugs + occupancy) to parquet.

Source: data/raw/ECO/{NN}_sm_csv.zip, {NN}_plugs_csv.zip, {NN}_occupancy_csv.zip, {NN}_doc.txt.

- smart meter: headerless daily CSVs (86,400 one-per-second rows; 16 columns in
  doc.txt order: powerallphases ... phaseanglecurrentvoltagel3); -1 marks a
  missing measurement and is preserved verbatim.
- plugs: headerless daily single-value CSVs (consumption W) under NN/PP/;
  one parquet per plug + plug labels parsed from NN_doc.txt -> eco_labels.json.
- occupancy: day-matrix CSVs (header line of 86,400 time labels; one row per
  day, first col date, then 0/1 presence per second) -> long ts_us + occupancy.
- ts_us = local wall-clock day (from filename / row) + second index, i.e. the
  dataset's native CET/CEST clock without DST correction; documented in notes.
- Matlab zip variants are not converted; doc.txt is copied verbatim per house.
"""
import argparse, glob, io, json, os, re, shutil, time
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from wattwiser import DATA, FND, RAW, ROOT, done, ensure, load_manifest, log, record, save_manifest, stat_parquet
from wattwiser.labels import canonical_label, write_slice

SM_COLS = ['powerallphases', 'powerl1', 'powerl2', 'powerl3', 'currentneutral',
           'currentl1', 'currentl2', 'currentl3', 'voltagel1', 'voltagel2',
           'voltagel3', 'phaseanglevoltagel2l1', 'phaseanglevoltagel3l1',
           'phaseanglecurrentvoltagel1', 'phaseanglecurrentvoltagel2',
           'phaseanglecurrentvoltagel3']
LABEL_RE = re.compile(r'^\s*(\d{2}):\s*(.+?)\s*\(no[.,]?\s*days:\s*(\d+),\s*coverage:\s*([\d.]+)%\)')


def ts_of_date(base, n):
    start = pd.to_datetime(base).value // 1000
    return (start + np.arange(n, dtype=np.int64) * 1000000).astype(np.int64)


def extract(force=False):
    name = 'eco'
    notes = ['source: data/raw/ECO/{NN}_sm_csv.zip + {NN}_plugs_csv.zip + {NN}_occupancy_csv.zip (+ doc.txt)',
             'sm: headerless 16-col daily CSVs in doc.txt order; missing = -1 preserved verbatim',
             'plugs: per-plug daily single-value CSVs (consumption W) -> plug_PP.parquet; labels -> eco_labels.json',
             'occupancy: 86,400 s/day day-matrix -> long ts_us + occupancy (0/1); summer and winter kept separate',
             'ts_us = local wall-clock second index per day (CET/CEST as measured, no DST correction)',
             'ts anchor: file date (naive local) at midnight + row index seconds',
             'matlab zips not converted; doc.txt copied verbatim per house']
    man = load_manifest(name, notes)
    root = os.path.join(RAW, 'ECO')
    outroot = os.path.join(FND, name)
    ensure(outroot)
    import zipfile

    for zpath in sorted(glob.glob(os.path.join(root, '*_sm_csv.zip'))):
        house = os.path.basename(zpath)[:2]
        hdir = os.path.join(outroot, 'house_' + house)
        ensure(hdir)
        shutil.copy(os.path.join(root, house + '_doc.txt'), os.path.join(hdir, 'doc.txt'))
        labels = {}
        lsrc = os.path.join(root, house + '_doc.txt')
        if os.path.exists(lsrc):
            for m in LABEL_RE.finditer(open(lsrc).read()):
                labels[m.group(1)] = {'name': m.group(2), 'days': int(m.group(3)),
                                      'coverage_pct': float(m.group(4))}
        if labels:
            with open(os.path.join(hdir, 'eco_labels.json'), 'w') as fh:
                json.dump(labels, fh, indent=1)

        key = 'house_' + house + '/sm'
        if force or not done(man, key):
            t0 = time.time()
            out = os.path.join(hdir, 'sm.parquet')
            z = zipfile.ZipFile(zpath)
            members = sorted(n for n in z.namelist()
                             if re.match(r'%s/\d{4}-\d{2}-\d{2}\.csv$' % house, n)
                             and '__MACOSX' not in n)
            schema = pa.schema([('ts_us', pa.int64())] + [(c, pa.float64()) for c in SM_COLS])
            writer = pq.ParquetWriter(out, schema, compression='zstd', compression_level=3)
            nrows, ndays = 0, 0
            for n in members:
                df = pd.read_csv(io.BytesIO(z.read(n)), header=None, names=SM_COLS)
                date = os.path.basename(n)[:-4]
                ts = pd.Timestamp(date).value // 1000
                arrs = [pa.array((ts + np.arange(len(df), dtype=np.int64) * 1000000).astype(np.int64))]
                arrs += [pa.array(df[c].values, type=pa.float64()) for c in SM_COLS]
                writer.write_table(pa.Table.from_arrays(arrs, schema=schema))
                nrows += len(df)
                ndays += 1
            writer.close()
            st = stat_parquet(out)
            record(man, name, key, out, zpath, st, t0, days=ndays)
            log('%s: %d rows from %d days (%.0fs)' % (key, nrows, ndays, time.time() - t0))

        key = 'house_' + house + '/plugs'
        if force or not done(man, key):
            t0 = time.time()
            pz = zipfile.ZipFile(os.path.join(root, house + '_plugs_csv.zip'))
            by_plug = {}
            for n in sorted(pz.namelist()):
                m = re.match(r'%s/(\d{2})/\d{4}-\d{2}-\d{2}\.csv$' % house, n)
                if m and '__MACOSX' not in n:
                    by_plug.setdefault(m.group(1), []).append(n)
            written = 0
            for pid, members in sorted(by_plug.items()):
                pkey = 'house_' + house + '/plug_' + pid
                if not force and done(man, pkey):
                    continue
                out = os.path.join(hdir, 'plug_' + pid + '.parquet')
                with pz.open(members[0]) as fh:
                    ncols = len(fh.readline().strip(b'\r\n').split(b','))
                plug_cols = ['consumption'] + ['col_%d' % i for i in range(ncols - 1)]
                schema = pa.schema([('ts_us', pa.int64())] + [(c, pa.float64()) for c in plug_cols])
                writer = pq.ParquetWriter(out, schema, compression='zstd', compression_level=3)
                nrows = 0
                for n in members:
                    df = pd.read_csv(io.BytesIO(pz.read(n)), header=None, names=plug_cols)
                    date = n.split('/')[-1][:-4]
                    ts = pd.Timestamp(date).value // 1000
                    tbl = pa.Table.from_arrays(
                        [pa.array((ts + np.arange(len(df), dtype=np.int64) * 1000000).astype(np.int64))]
                        + [pa.array(df[c].values, type=pa.float64()) for c in plug_cols], schema=schema)
                    writer.write_table(tbl)
                    nrows += len(df)
                writer.close()
                st = stat_parquet(out)
                record(man, name, pkey, out, house + '_plugs_csv.zip:' + pid, st, t0)
                written += 1
            done_all = all(done(man, 'house_' + house + '/plug_' + pid) for pid in by_plug)
            if done_all:
                man['files'][key] = {'plug_count': len(by_plug),
                                     'note': 'per-plug parquets plug_PP.parquet'}
                save_manifest(name, man)
            log('%s: %d plugs (%.0fs)' % (key, len(by_plug), time.time() - t0))

        occ_z = os.path.join(root, house + '_occupancy_csv.zip')
        if os.path.exists(occ_z):
            for season in ('summer', 'winter'):
                key = 'house_' + house + '/occupancy_' + season
                if not force and done(man, key):
                    continue
                t0 = time.time()
                z = zipfile.ZipFile(occ_z)
                member = house + '_' + season + '.csv'
                if member not in z.namelist():
                    continue
                df = pd.read_csv(io.BytesIO(z.read(member)), header=None, skiprows=1, dtype=str)
                dates = pd.to_datetime(df[0], format='%d-%b-%Y')
                vals = df.iloc[:, 1:].astype(np.int8).values
                out = os.path.join(hdir, 'occupancy_' + season + '.parquet')
                schema = pa.schema([('ts_us', pa.int64()), ('occupancy', pa.int8())])
                writer = pq.ParquetWriter(out, schema, compression='zstd', compression_level=3)
                nrows = 0
                for i, d in enumerate(dates):
                    ts = d.value // 1000
                    tbl = pa.Table.from_arrays(
                        [pa.array((ts + np.arange(86400, dtype=np.int64) * 1000000).astype(np.int64)),
                         pa.array(vals[i], type=pa.int8())], schema=schema)
                    writer.write_table(tbl)
                    nrows += len(vals[i])
                writer.close()
                st = stat_parquet(out)
                record(man, name, key, out, house + '_occupancy_csv.zip:' + season, st, t0, days=len(dates))
                log('%s: %d rows (%.0fs)' % (key, nrows, time.time() - t0))


def extract_labels():
    """Plug labels from NN_doc.txt plug tables (plug id -> appliance name)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(RAW, 'ECO', '*_doc.txt'))):
        house = 'house_' + os.path.basename(f).split('_')[0]
        plugs = {}
        for line in open(f, encoding='utf-8', errors='ignore'):
            m = re.match(r'^(\d\d):\s*([^(*]+?)(?:\s*\(|\s*\(no|$)', line.strip())
            if m and int(m.group(1)) <= 20:
                label = m.group(2).strip().rstrip(',')
                plugs[m.group(1)] = {'label': label, 'canonical': canonical_label(label)}
        if plugs:
            out[house] = {'source': os.path.relpath(f, ROOT), 'plugs': plugs}
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_eco.json')
    a = ap.parse_args()
    if a.labels:
        log('=== eco labels ===')
        log('wrote %s' % write_slice('eco', extract_labels()))
        log('=== done eco labels ===')
    else:
        log('=== eco extract ===')
        extract(force=a.force)
        log('=== done eco ===')
