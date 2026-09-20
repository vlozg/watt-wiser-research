"""Extract GREEND (8 Italian homes, 1 s per-plug readings) to parquet.

Source: data/raw/GREEND_0-2_300615/GREEND_0-2_300615/building{0..7}/dataset_YYYY-MM-DD.csv
(columns = timestamp + raw plug MAC ids; NULL cells; labels need GREEND metadata).

Quirk handled exactly (no rows dropped): GREEND files embed repeated header
rows ('timestamp,<macs>'). Some buildings (0, 5, 6) re-write the header every
~15 min with an unchanged plug set, and any plug-set change mid-day adds a
header row whose column list differs (e.g. building0 2013-12-07: plug
000D6F0002906FA7 joins at 12:13, matching the next day's header). This parser
maps every header block's rows onto the building-wide union of plug MACs;
plugs absent from a block are null for that interval.
ts_us = round(unix_seconds * 1e6).
"""
from __future__ import annotations

import argparse
import glob
import logging
import os
import re
import time
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from wattwiser import FND, RAW, ROOT, done, ensure, load_manifest, record, setup_logging, stat_parquet
from wattwiser.labels import GreendBuilding, GreendMeterLabel, canonical_label, write_slice

log = logging.getLogger(__name__)

# per-building plug->label metadata copied into this pipeline dir (from the GREEND repo)
HERE = os.path.dirname(os.path.abspath(__file__))
GREEND_YAML_DIR = os.path.join(HERE, 'metadata', 'greend')


def _slow_blocks(d: str) -> list[pd.DataFrame]:
    """Block-aware parse keyed on every 'timestamp' header line (incl. the first)."""
    cur_cols: list[str] | None = None
    cur_rows: list[list[str]] | None = None
    blocks: list[tuple[list[str], list[list[str]]]] = []
    with open(d) as fh:
        for line in fh:
            line = line.rstrip('\r\n')
            if not line:
                continue
            if line.startswith('timestamp'):
                if cur_cols is not None:
                    blocks.append((cur_cols, cur_rows))
                cur_cols, cur_rows = line.split(',')[1:], []
            elif cur_cols is not None:
                cur_rows.append(line.split(','))
    if cur_cols is not None:
        blocks.append((cur_cols, cur_rows))
    # block -> frame: ts cell via to_numeric (degenerate lines -> NaN ts), plug
    # cells padded to the block's width, NULL/empty -> NaN, junk -> NaN (none
    # found by qa_raw.py)
    out: list[pd.DataFrame] = []
    for cols, rows in blocks:
        if not rows:
            continue
        data: dict[str, Any] = {'timestamp': pd.to_numeric([r[0] for r in rows], errors='coerce')}
        for j, c in enumerate(cols):
            data[c] = pd.to_numeric(
                [r[j + 1] if j + 1 < len(r) else None for r in rows],
                errors='coerce')
        out.append(pd.DataFrame(data))
    return out


def read_day(d: str) -> tuple[list[pd.DataFrame], int]:
    """Return (list of block DataFrames each with 'timestamp' first col, extra_headers).

    Fast path: uniform file via pandas C parser. Slow paths (re-headered files,
    ragged widths): block-aware parse keyed on every mid-file 'timestamp' row.
    """
    if os.path.getsize(d) < 2:
        return [], 0  # some building6 days are empty files
    try:
        # fast path assumes one uniform header; NULL is GREEND's missing marker
        df = pd.read_csv(d, na_values=['NULL'])
        # any string dtype in a plug column means a mid-file header was parsed
        # as data (same-width re-header) -> redo with the block-aware parser
        if any(not pd.api.types.is_numeric_dtype(df[c]) for c in df.columns[1:]):
            # same-width re-header: mid-file header row parsed as data -> redo block-aware
            blocks = _slow_blocks(d)
            log.info('re-headered file (same width): %s (%d blocks)' % (os.path.basename(d), len(blocks)))
            return blocks, len(blocks) - 1
        return [df], 0
    except pd.errors.ParserError:
        return _slow_blocks(d), len(_slow_blocks(d)) - 1


def extract(force: bool = False) -> None:
    """Convert every building's daily CSVs to one parquet (resumable via the manifest)."""
    name = 'greend'
    notes = ['source: data/raw/GREEND_0-2_300615/GREEND_0-2_300615/building{0..7}/dataset_YYYY-MM-DD.csv',
             '1 s per-plug readings; columns are raw plug MAC ids (labels need GREEND metadata); NULL -> null',
             'files embed repeated header rows (routine ~15 min checkpoints; plug-set changes add a header row '
             'with a new column list): every block mapped onto the building-wide MAC union; no rows skipped; '
             'midfile_header_rows counts mid-file header rows across a building\'s files',
             'ts_us = round(unix_seconds * 1e6); rows whose ts cannot parse (2 degenerate whitespace lines: '
             'building4 2014-02-03, building7 2015-03-05) keep ts null, never dropped']
    man = load_manifest(name, notes)
    src_root = os.path.join(RAW, 'GREEND_0-2_300615', 'GREEND_0-2_300615')
    outdir = os.path.join(FND, name)
    ensure(outdir)
    for bdir in sorted(glob.glob(os.path.join(src_root, 'building*'))):
        bname = os.path.basename(bdir)
        if not force and done(man, bname):
            continue
        t0 = time.time()
        days = sorted(glob.glob(os.path.join(bdir, '*.csv')))
        # pass 1: building-wide union of plug MACs across every header line
        union: list[str] = []
        seen: set[str] = set()
        for d in days:
            with open(d) as fh:
                for line in fh:
                    if line.startswith('timestamp'):
                        for c in line.rstrip('\r\n').split(',')[1:]:
                            if c and c not in seen:
                                seen.add(c)
                                union.append(c)
        out = os.path.join(outdir, bname + '.parquet')
        schema = pa.schema([('ts_us', pa.int64())] + [(c, pa.float64()) for c in union])
        writer = pq.ParquetWriter(out, schema, compression='zstd', compression_level=3)
        nrows = 0
        reheaders = 0
        for d in days:
            day_blocks, extra = read_day(d)
            reheaders += extra
            if not day_blocks:
                continue  # empty daily file
            w = pd.concat(day_blocks, ignore_index=True) if len(day_blocks) > 1 else day_blocks[0]
            tsf = np.round(pd.to_numeric(w['timestamp'], errors='coerce').values * 1e6)
            ts = pd.array(tsf, dtype='Int64')  # NaN ts (degenerate whitespace line) -> null, row kept
            # blocks may not carry every union MAC: plugs absent from a block
            # become all-NaN for that interval (raw fidelity, no rows dropped)
            arrs = [pa.array(ts)] + [
                pa.array(w[c].values, type=pa.float64()) if c in w.columns
                else pa.array(np.full(len(w), np.nan), type=pa.float64())
                for c in union]
            writer.write_table(pa.Table.from_arrays(arrs, schema=schema))
            nrows += len(w)
        writer.close()
        st = stat_parquet(out)
        if st.rows != nrows:
            raise RuntimeError('row mismatch %s: %d vs %d' % (bname, st.rows, nrows))
        record(man, name, bname, out, bdir, st, t0, src_days=len(days),
               src_bytes=sum(os.path.getsize(d) for d in days), cols=len(union),
               midfile_header_rows=reheaders)
        log.info('%s: %d rows x %d plug cols from %d days, %d mid-file header rows (%.0fs)' % (
            bname, nrows, len(union), len(days), reheaders, time.time() - t0))


def extract_labels() -> dict[str, GreendBuilding]:
    """Meter labels from the vendored NILMTK metadata YAMLs (metadata/greend/README.md).

    Meter k = k-th MAC column of the raw CSVs (column order preserved in fnd).
    """
    out: dict[str, GreendBuilding] = {}
    for f in sorted(glob.glob(os.path.join(GREEND_YAML_DIR, 'building*.yaml'))):
        nb = int(re.search(r'building(\d+)', f).group(1))
        txt = open(f, encoding='utf-8').read()
        name = re.search(r'original_name:\s*(\S+)', txt)
        meters: dict[str, list[GreendMeterLabel]] = {}
        # each appliance block: 'type: ...' first line then meters: [ids]
        for blk in re.split(r'\n- type:', txt)[1:]:
            label = blk.split('\n')[0].strip()
            m = re.search(r'meters:\s*\[([^\]]+)\]', blk)
            room = re.search(r'\broom:\s*(\S+)', blk)
            for mid in ([int(x) for x in m.group(1).replace(' ', '').split(',')] if m else []):
                meters.setdefault(str(mid), []).append(GreendMeterLabel(
                    label=label, canonical=canonical_label(label),
                    room=room.group(1) if room else None))
        out['building_%d' % (nb - 1)] = GreendBuilding(
            source=os.path.relpath(f, ROOT),
            house_name=name.group(1) if name else None,
            meters=meters)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_greend.json')
    a = ap.parse_args()
    setup_logging()
    if a.labels:
        log.info('=== greend labels ===')
        log.info('wrote %s' % write_slice('greend', extract_labels()))
        log.info('=== done greend labels ===')
    else:
        log.info('=== greend extract ===')
        extract(force=a.force)
        log.info('=== done greend ===')
