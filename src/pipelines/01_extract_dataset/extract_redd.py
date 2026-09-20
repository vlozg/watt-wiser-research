"""Extract REDD NILMTK HDF5 store (6 US homes) to parquet.

Source: data/raw/redd/redd.h5. pandas read fails on its pytables metadata (written
by an old pandas), so conversion walks every Table node via pytables directly:
/buildingN/elec/meterM/table -> buildingN_elec_meterM.parquet, plus the NILMTK
cache tables (good_sections, total_energy). ts_us = index ns // 1000. Meter
attrs go to redd_meta.json. Source values are float32 and stored float32.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import Any

import numpy as np
import pandas as pd
import tables

from wattwiser import FND, RAW, done, ensure, load_manifest, record, setup_logging, stat_parquet, write_parquet
from wattwiser.labels import ReddBuilding, ReddMeterLabel, canonical_label, h5_metadata, write_slice

log = logging.getLogger(__name__)


def extract(force: bool = False) -> None:
    """Convert every /buildingN/elec/meterM table to one parquet (resumable via the manifest)."""
    name = 'redd'
    notes = ['source: data/raw/redd/redd.h5 (NILMTK pytables store); converted via pytables',
             'each /buildingN/elec/meterM/table -> ts_us (index ns -> us) + value_0 (float32, source dtype)',
             'nilmtk cache tables (good_sections/total_energy) included; meter attrs -> redd_meta.json']
    man = load_manifest(name, notes)
    outdir = os.path.join(FND, name)
    ensure(outdir)
    meta_out: dict[str, Any] = {}
    with tables.open_file(os.path.join(RAW, 'redd', 'redd.h5'), 'r') as h:
        # NILMTK layout: every data node sits at <path>/table with an 'index'
        # column (datetime64[ns] as int ns) and a 'values_block_0' value column
        for node in h.walk_nodes('/', classname='Table'):
            path = node._v_pathname
            if not path.endswith('/table'):
                continue
            # flat parquet key: building1/elec/meter1/table -> building1_elec_meter1
            key = path.lstrip('/').replace('/table', '').replace('/', '_')
            if not force and done(man, key):
                continue
            t0 = time.time()
            arr = node.read()
            # ns -> us: REDD timestamps land on whole seconds
            idx = arr['index'].astype(np.int64) // 1000
            vals = arr['values_block_0']
            # single-meter tables store a 2-D (n, 1) block -> flatten to 1-D
            if vals.ndim == 2:
                vals = vals[:, 0]
            df = pd.DataFrame({'ts_us': idx, 'value_0': vals})
            out = os.path.join(outdir, key + '.parquet')
            write_parquet(df, out)
            st = stat_parquet(out)
            if st.rows != len(df):
                raise RuntimeError('row mismatch %s' % key)
            # keep meter attrs (frequency, timezone, device info) minus pytables
            # housekeeping keys, so redd_meta.json documents each table
            attrs = {k: str(node._v_attrs[k]) for k in node._v_attrs._v_attrnames
                     if not k.startswith(('NRT', 'pandas', 'TITLE', 'CLASS', 'VERSION', 'FLAVOR'))}
            meta_out[key] = attrs
            record(man, name, key, out, 'redd.h5:' + path, st, t0)
            log.info('%s: %d rows (%.0fs)' % (key, len(df), time.time() - t0))
        # store-level metadata nodes (description, labels) -> merged into the
        # same json under store_metadata
        md: dict[str, str] = {}
        for node in h.walk_nodes('/'):
            nm = node._v_name or ''
            if 'meta' in nm.lower():
                try:
                    md[node._v_pathname] = str(node.read()) if isinstance(node, tables.Array) else str(node._v_attrs)
                except Exception as e:
                    md[node._v_pathname] = 'unreadable: %s' % e
    if md:
        meta_out['store_metadata'] = md
    with open(os.path.join(FND, name, 'redd_meta.json'), 'w') as fh:
        json.dump(meta_out, fh, indent=1, default=str)


def extract_labels() -> dict[str, ReddBuilding]:
    """Meter labels from the NILMTK store metadata (site meters + appliance types)."""
    src = 'data/raw/redd/redd.h5'
    out: dict[str, ReddBuilding] = {}
    with tables.open_file(os.path.join(RAW, 'redd', 'redd.h5'), 'r') as h:
        for b in range(1, 7):
            md = h5_metadata(h.get_node('/building%d' % b))
            site = [k for k, v in md.get('elec_meters', {}).items() if v.get('site_meter')]
            meters: dict[str, ReddMeterLabel] = {}
            # REDD labels are coarse: appliance 'type' per meter; a meter can
            # serve several appliances -> count multiplicity
            for a in md.get('appliances', []):
                for m in a.get('meters') or []:
                    label = str(a.get('type'))
                    e = meters.setdefault(str(m), ReddMeterLabel(label=label, canonical=canonical_label(label), count=0))
                    e.count += 1
            out['building_%d' % b] = ReddBuilding(source=src, site_meters=site, meters=meters)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--labels', action='store_true',
                    help='extract appliance labels only -> data/gold/appliance_map_redd.json')
    a = ap.parse_args()
    setup_logging()
    if a.labels:
        log.info('=== redd labels ===')
        log.info('wrote %s' % write_slice('redd', extract_labels()))
        log.info('=== done redd labels ===')
    else:
        log.info('=== redd extract ===')
        extract(force=a.force)
        log.info('=== done redd ===')
