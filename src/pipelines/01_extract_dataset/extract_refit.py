"""Extract REFIT cleaned CSVs (20 UK homes, 8 s) to parquet, streaming one house at a time.

Source: data/raw/REFIT/CLEAN_REFIT_081116.7z -> CLEAN_House{1..20}.csv. Each house
is extracted to .scratch staging, converted, and deleted before the next, so
peak staging stays near one house. ts_us = UnixTime seconds * 1e6 (UTC epoch).
ts_local_us = true UK local wall clock as naive local epoch microseconds,
reconstructed as Europe/London tz conversion of ts_us. Verified finding: the
cleaned release Time column is a string rendering of the SAME corrected
timeline (identical to Unix for every row of houses 1 and 5, no DST repeat),
so the wall clock is reconstructed rather than copied; the RAW variant's Time
column is the uncorrected logger clock. Raw variant archive
(Processed_Data_CSV.7z) is left archived.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import time
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import py7zr

from wattwiser import FND, RAW, STAGE, done, ensure, load_manifest, record, setup_logging, stat_parquet, write_parquet
from wattwiser.labels import RefitApplianceLabel, RefitBuilding, canonical_label, write_slice

log = logging.getLogger(__name__)

M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def extract(force: bool = False) -> None:
    """Convert every CLEAN_House{1..20}.csv to one parquet (resumable, one house staged at a time)."""
    name = 'refit'
    notes = ['source: data/raw/REFIT/CLEAN_REFIT_081116.7z -> CLEAN_House{1..20}.csv, extracted one house at a time',
             'ts_us = UnixTime seconds * 1e6 (UTC); ts_local_us = true UK local wall clock (Europe/London conversion of ts_us) as naive local epoch us - the release Time column is the same corrected timeline (verified identical to Unix, no DST repeat) and is dropped; all measurement columns verbatim numeric; Processed_Data_CSV.7z (raw variant) left archived']
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
        src = os.path.join(STAGE, n)
        df = pd.read_csv(src)
        # column names vary slightly across REFIT releases -> resolve
        # unix/time columns case-insensitively
        lower = {c.lower(): c for c in df.columns}
        tcol = next((lower[c] for c in ('unixtime', 'unix', 'unix_ts', 'unixts', 'time') if c in lower), None)
        if tcol is None:
            raise RuntimeError('no ts col in %s: %s' % (n, list(df.columns)[:5]))
        dcol = lower.get('time')  # release 'Time' column (string rendering of the corrected clock)
        if dcol is None:
            raise RuntimeError('no Time col in %s: %s' % (n, list(df.columns)[:5]))
        # UnixTime (int seconds) -> ts_us; the string Time column is popped and
        # parsed as UTC (module docstring: same corrected timeline as Unix)
        df.insert(0, 'ts_us', (pd.to_numeric(df.pop(tcol)) * 1e6).astype('int64'))
        dts = pd.to_datetime(df.pop(dcol), errors='coerce', utc=True)
        if dts.isna().any():
            raise RuntimeError('unparseable Time rows in %s: %d' % (n, int(dts.isna().sum())))
        # verify the release claim: Time renders the SAME corrected timeline as Unix
        # (houses 1 and 5 checked: identical, no DST repeat). Skew vs ts_us must stay < 1 h.
        # resolution-safe: pandas 3 may return datetime64[s]/[us], not [ns]
        t_us = dts.to_numpy().astype('datetime64[us]').astype('int64')
        skew = np.abs(t_us - df['ts_us'].to_numpy())
        if skew.max() > int(3600 * 1e6):
            raise RuntimeError('Time/ts_us skew > 1 h in %s: %d us' % (n, int(skew.max())))
        # true UK local wall clock: Europe/London conversion of the UTC timeline
        loc = dts.dt.tz_convert('Europe/London').dt.tz_localize(None)
        dts_us = loc.to_numpy().astype('datetime64[us]').astype('int64')
        dskew = np.abs(dts_us - df['ts_us'].to_numpy())
        if dskew.max() > int(3600 * 1e6):
            raise RuntimeError('local/ts_us offset > 1 h in %s: %d us' % (n, int(dskew.max())))
        df.insert(1, 'ts_local_us', dts_us)
        # measurement columns: an unparseable cell must stop the build, not
        # silently become NaN (coerce only demotes cells that read_csv parsed)
        nan_before = df.isna().sum()
        df = df.apply(pd.to_numeric, errors='coerce')
        coerced = int((df.isna().sum() - nan_before).sum())
        if coerced:
            raise RuntimeError('%s: %d non-numeric measurement cell(s) -> NaN'
                                % (key, coerced))
        out = os.path.join(outdir, key + '.parquet')
        write_parquet(df, out)
        st = stat_parquet(out)
        if st.rows != len(df):
            raise RuntimeError('row mismatch %s' % key)
        record(man, name, key, out, 'CLEAN_REFIT_081116.7z:' + n, st, t0,
               src_bytes=os.path.getsize(src))
        log.info('%s: %d rows x %d cols (%.0fs)' % (key, len(df), df.shape[1], time.time() - t0))
        os.remove(src)
    shutil.rmtree(STAGE, ignore_errors=True)


def _xlsx_cell(cell: ET.Element, shared: list[str]) -> str:
    """One xlsx cell as text: shared-string cells resolved via the table."""
    if cell.get('t') == 's':
        v = cell.find(M + 'v')
        return shared[int(v.text)] if v is not None else ''
    v = cell.find(M + 'v')
    return v.text if v is not None else ''


def extract_labels() -> dict[str, RefitBuilding]:
    """Appliance labels, brand and model from MetaData_Tables.xlsx sheets 'House N'."""
    src = os.path.join(RAW, 'REFIT', 'MetaData_Tables.xlsx')
    # xlsx is a zip of xml: read shared strings + sheet order from workbook.xml,
    # then walk each 'House N' worksheet directly (no openpyxl dependency)
    z = zipfile.ZipFile(src)
    shared: list[str] = []
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    for si in root.iter(M + 'si'):
        shared.append(''.join(t.text or '' for t in si.iter(M + 't')))
    wb = z.read('xl/workbook.xml').decode('utf-8')
    sheet_names = [n for n, _ in re.findall(r'name="([^"]+)"[^>]*r:id="rId(\d+)"', wb)]
    out: dict[str, RefitBuilding] = {}
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
        appliances: dict[str, RefitApplianceLabel] = {}
        for r in rows:
            # house sheet rows: idx | label | brand | model | (free-text notes)
            vals = [' '.join(str(_xlsx_cell(c, shared)).split()) for c in r.findall(M + 'c')]
            if len(vals) >= 2 and vals[0].strip().isdigit():
                idx = vals[0].strip()
                brand = vals[2] if len(vals) > 2 else None
                model = vals[3] if len(vals) > 3 else None
                appliance = RefitApplianceLabel(
                    label=vals[1],
                    canonical=canonical_label(vals[1]),
                    brand=brand if brand and brand != 'Unknown' else None,
                    model=model if model and model != 'Unknown' else None)
                notes = [v for v in vals[4:] if v.startswith('(')]
                if notes:
                    appliance.notes = ' '.join(notes)
                appliances[idx] = appliance
        if appliances:
            out['house_' + m.group(1)] = RefitBuilding(
                source='data/raw/REFIT/MetaData_Tables.xlsx#%s' % name,
                appliances=appliances)
    z.close()
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_refit.json')
    a = ap.parse_args()
    setup_logging()
    if a.labels:
        log.info('=== refit labels ===')
        log.info('wrote %s' % write_slice('refit', extract_labels()))
        log.info('=== done refit labels ===')
    else:
        log.info('=== refit extract ===')
        extract(force=a.force)
        log.info('=== done refit ===')
