#!/usr/bin/env python3
"""Shared helpers for the 03_gold_nilm gold builders.

Gold layer contract (details in docs/datasets/gold-layer.md):

- data/gold/<dataset>/<building>/mains.parquet
      (ts_us, w) whole-home aggregate; omitted when a dataset has no site
      meter (GREEND has none).
- data/gold/<dataset>/<building>/<name>[_N].parquet
      (ts_us, w) one file per labeled appliance meter - ALL of them, not just
      the 5 client targets (gold is a source of trust; filter downstream).
      Name = canonical label for target appliances, else slug of the original
      device label; repeats get an ordinal suffix (_2, _3, ...) in stable
      meter order. Manifest entries carry label + canonical for filtering.
- data/gold/<dataset>/manifest.json
      provenance + row/cadence stats per table, same resume bookkeeping as
      the fnd manifests (root=GOLD).
- data/gold/thresholds.json
      per-appliance ON thresholds derived from the gold data with a fixed,
      documented rule.

Tables are copied through from data/fnd at native sampling: no resampling,
no gap filling, no rounding - gold adds uniform naming/schema and labels only.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

from wattwiser import GOLD, done, stat_parquet, write_parquet

log = logging.getLogger(__name__)

AGGREGATE_LABELS = {'aggregate', 'site_meter', 'mains'}  # never appliance tables

MAP_PATH = os.path.join(GOLD, 'appliance_map.json')
THRESH_PATH = os.path.join(GOLD, 'thresholds.json')
NOISE_FLOOR_W = 5.0      # readings at/below this are standby/off, never ON
MIN_SAMPLES = 100        # need at least this many above-floor samples to trust the stats

THRESH_METHOD = ('thr_on_W = max(5.0, 0.5 * p50_on_W), where p50_on_W is the '
                 'median of samples above the 5 W noise floor; '
                 'ON := w > thr_on_W (reference ground truth)')


def load_map() -> dict[str, Any]:
    """The merged appliance map written by 01_extract_dataset/labels.py."""
    with open(MAP_PATH) as fh:
        return json.load(fh)


def read_fnd(path: str, cols: list[str]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Read selected columns of one fnd parquet as numpy arrays.

    Returns (ts_us int64, {name: float64 array}); every value column becomes
    plain watts. NaN cells (GREEND NULLs) are preserved verbatim.
    """
    t = pq.read_table(path, columns=cols)
    if t.column('ts_us').null_count:
        # a sample without a timestamp cannot be indexed; fnd keeps it, gold drops it
        log.info('  note: dropping %d un-timestamped row(s) from %s'
                 % (t.column('ts_us').null_count, path))
        t = t.filter(pc.is_valid(t.column('ts_us')))
    ts = t.column('ts_us').to_numpy().astype('int64')
    vals = {c: t.column(c).to_numpy().astype('float64') for c in cols[1:]}
    return ts, vals


def dt_of(ts_us: np.ndarray) -> float:
    """Median sampling interval in seconds (3 significant digits)."""
    if len(ts_us) < 2:
        return 0.0
    d = np.diff(ts_us)
    d = d[d > 0]
    return round(float(np.median(d)) / 1e6, 3)


def write_gold(ds: str, building: str, name: str, ts_us: np.ndarray, w: np.ndarray,
               src: list[str]) -> dict[str, Any]:
    """Write one gold table (ts_us, w) and return its stats dict.

    The 'src' argument is the list of fnd parquet paths the table was
    derived from.
    """
    out = os.path.join(GOLD, ds, building, name + '.parquet')
    df = pd.DataFrame({'ts_us': np.asarray(ts_us, dtype='int64'),
                       'w': np.asarray(w, dtype='float64')})
    write_parquet(df, out)
    entry: dict[str, Any] = asdict(stat_parquet(out))
    entry.pop('cols', None)
    entry['dt_s'] = dt_of(ts_us)
    entry['path'] = out
    entry['src'] = src
    return entry


def slug(label: str) -> str:
    """Filesystem-safe slug of a device label ('Coffee machine' -> coffee_machine)."""
    return re.sub(r'[^a-z0-9]+', '_', str(label).lower()).strip('_') or 'unlabeled'


def names_for(entries: list[dict[str, Any]]) -> list[str]:
    """Gold file names for labeled entries: canonical first, then slugs.

    Target appliances keep their canonical name (fridge); other devices use
    a slug of the original label (electric_oven). Any repeat inside one
    building gets an ordinal suffix in stable meter order.
    """
    used: set[str] = set()
    out: list[str | None] = [None] * len(entries)
    for i, e in enumerate(entries):
        c = e.get('canonical')
        if c and c not in used:
            used.add(c)
            out[i] = c
    for i, e in enumerate(entries):
        if out[i] is not None:
            continue
        base = slug(e.get('canonical') or e.get('label'))
        n, cand = 2, base
        while cand in used:
            cand = '%s_%d' % (base, n)
            n += 1
        used.add(cand)
        out[i] = cand
    return out  # every entry gets a name; None placeholders are all filled


def thr_record(w: np.ndarray, label: str, canonical: str | None) -> dict[str, Any]:
    """ON-threshold entry + the identity fields gold records for filtering."""
    rec = thr_entry(w)
    rec['label'] = label
    rec['canonical'] = canonical
    return rec


def thr_entry(w: np.ndarray) -> dict[str, Any]:
    """ON-threshold stats for one appliance channel (see THRESH_METHOD).

    Channels with too few above-floor samples keep the plain noise floor as
    their threshold (flagged via method='noise_floor').
    """
    nz = w[np.isfinite(w)]
    nz = nz[nz > NOISE_FLOOR_W]
    if len(nz) < MIN_SAMPLES:
        return {'thr_on_W': NOISE_FLOOR_W,
                'p50_on_W': round(float(np.median(nz)), 1) if len(nz) else 0.0,
                'n_above_floor': int(len(nz)), 'method': 'noise_floor'}
    p50 = float(np.percentile(nz, 50))
    thr = round(max(NOISE_FLOOR_W, 0.5 * p50), 1)
    on = int(np.sum(w[np.isfinite(w)] > thr))
    return {'thr_on_W': thr, 'p50_on_W': round(p50, 1),
            'n_above_floor': int(len(nz)),
            'on_share_pct': round(100.0 * on / len(w), 2), 'method': 'half_p50'}


def merge_thresholds(ds: str, building: str, entries: dict[str, dict[str, Any]]) -> None:
    """Merge {appliance_name: stats} into data/gold/thresholds.json."""
    data: dict[str, Any] = {}
    if os.path.exists(THRESH_PATH):
        with open(THRESH_PATH) as fh:
            data = json.load(fh)
    data.setdefault('_meta', {'method': THRESH_METHOD, 'noise_floor_W': NOISE_FLOOR_W})
    data.setdefault(ds, {}).setdefault(building, {}).update(entries)
    with open(THRESH_PATH, 'w') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)


def parser(desc: str) -> argparse.ArgumentParser:
    """Argparse builder shared by the gold scripts (--force)."""
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument('--force', action='store_true',
                    help='rebuild gold tables even if they already exist')
    return ap


def skip(man: dict[str, Any], key: str, force: bool) -> bool:
    """Resume check: log and skip unless --force or the entry is missing."""
    if force or not done(man, key):
        return False
    log.info('  %-28s already present, skip' % key)
    return True
