"""Extract REFIT cleaned CSVs (20 UK homes, 8 s) to parquet, streaming one house at a time.

Source: data/raw/REFIT/CLEAN_REFIT_081116.7z -> CLEAN_House{1..20}.csv. Each house
is extracted to .scratch staging, converted, and deleted before the next, so
peak staging stays near one house. ts_us = UnixTime seconds * 1e6. The raw
variant archive (Processed_Data_CSV.7z) is left archived.
"""
import argparse, os, re, shutil, time
import zipfile
from xml.etree import ElementTree as ET
import numpy as np
import pandas as pd

from wattwiser import DATA, FND, RAW, ROOT, STAGE, done, ensure, load_manifest, log, record, save_manifest, stat_parquet, write_parquet
from wattwiser.labels import canonical_label, write_slice

def extract(force=False):
    import py7zr
    name = 'refit'
    notes = ['source: data/raw/REFIT/CLEAN_REFIT_081116.7z -> CLEAN_House{1..20}.csv, extracted one house at a time',
             'ts_us = UnixTime seconds * 1e6; all columns verbatim numeric; Processed_Data_CSV.7z (raw variant) left archived']
    man = load_manifest(name, notes)
    outdir = os.path.join(FND, name)
    ensure(outdir)
    ensure(STAGE)
    src7z = os.path.join(RAW, 'REFIT', 'CLEAN_REFIT_081116.7z')
    with py7zr.SevenZipFile(src7z) as z:
        names = [n for n in z.getnames() if n.endswith('.csv')]
    for n in sorted(names):
        key = n[:-4]
        if not force and done(man, key):
            continue
        t0 = time.time()
        # fresh archive handle per member: py7zr misbehaves on repeated targeted extracts
        with py7zr.SevenZipFile(src7z) as z:
            z.extract(targets=[n], path=STAGE)
        if True:
            src = os.path.join(STAGE, n)
            df = pd.read_csv(src)
            lower = {c.lower(): c for c in df.columns}
            tcol = next((lower[c] for c in ('unixtime', 'unix', 'unix_ts', 'unixts', 'time') if c in lower), None)
            if tcol is None:
                raise RuntimeError('no ts col in %s: %s' % (n, list(df.columns)[:5]))
            df.insert(0, 'ts_us', (pd.to_numeric(df.pop(tcol)) * 1e6).astype('int64'))
            df = df.apply(pd.to_numeric, errors='coerce')
            out = os.path.join(outdir, key + '.parquet')
            write_parquet(df, out)
            st = stat_parquet(out)
            if st['rows'] != len(df):
                raise RuntimeError('row mismatch %s' % key)
            record(man, name, key, out, 'CLEAN_REFIT_081116.7z:' + n, st, t0,
                   src_bytes=os.path.getsize(src))
            log('%s: %d rows x %d cols (%.0fs)' % (key, len(df), df.shape[1], time.time() - t0))
            os.remove(src)
    shutil.rmtree(STAGE, ignore_errors=True)

M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def _xlsx_cell(cell, shared):
    if cell.get('t') == 's':
        v = cell.find(M + 'v')
        return shared[int(v.text)] if v is not None else ''
    v = cell.find(M + 'v')
    return v.text if v is not None else ''


def extract_labels():
    """Appliance labels, brand and model from MetaData_Tables.xlsx sheets 'House N'."""
    src = os.path.join(RAW, 'REFIT', 'MetaData_Tables.xlsx')
    z = zipfile.ZipFile(src)
    shared = []
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    for si in root.iter(M + 'si'):
        shared.append(''.join(t.text or '' for t in si.iter(M + 't')))
    wb = z.read('xl/workbook.xml').decode('utf-8')
    sheet_names = [n for n, _ in re.findall(r'name="([^"]+)"[^>]*r:id="rId(\d+)"', wb)]
    out = {}
    for sf in sorted(
        [n for n in z.namelist() if n.startswith('xl/worksheets/sheet')],
        key=lambda n: int(re.search(r'(\d+)', n).group(1)),
    ):
        pos = int(re.search(r'(\d+)', sf).group(1)) - 1
        name = sheet_names[pos] if pos < len(sheet_names) else sf
        m = re.match(r'House (\d+)$', name)
        if not m:
            continue
        root = ET.fromstring(z.read(sf))
        rows = root.find(M + 'sheetData').findall(M + 'row')
        appliances = {}
        for r in rows:
            vals = [' '.join(str(_xlsx_cell(c, shared)).split()) for c in r.findall(M + 'c')]
            if len(vals) >= 2 and vals[0].strip().isdigit():
                idx = vals[0].strip()
                brand = vals[2] if len(vals) > 2 else None
                model = vals[3] if len(vals) > 3 else None
                appliance = {
                    'label': vals[1],
                    'canonical': canonical_label(vals[1]),
                    'brand': brand if brand and brand != 'Unknown' else None,
                    'model': model if model and model != 'Unknown' else None,
                }
                notes = [v for v in vals[4:] if v.startswith('(')]
                if notes:
                    appliance['notes'] = ' '.join(notes)
                appliances[idx] = appliance
        if appliances:
            out['house_' + m.group(1)] = {
                'source': 'data/raw/REFIT/MetaData_Tables.xlsx#%s' % name,
                'appliances': appliances,
            }
    z.close()
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_refit.json')
    a = ap.parse_args()
    if a.labels:
        log('=== refit labels ===')
        log('wrote %s' % write_slice('refit', extract_labels()))
        log('=== done refit labels ===')
    else:
        log('=== refit extract ===')
        extract(force=a.force)
        log('=== done refit ===')
