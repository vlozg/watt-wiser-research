#!/usr/bin/env python3
"""Build the GREEND gold tables (labeled plugs; no whole-home mains).

data/gold/greend/building_N/:
  <name>[_N].parquet        every labeled plug meter (native 1 s cadence);
                             canonical name for the 5 targets, label slug
                             otherwise, _N for repeats

GREEND records per-plug smart plugs only - no site meter exists, so there is
no mains.parquet for this dataset (noted in the manifest). Meter k in the
appliance map is the k-th MAC column of the fnd parquet (order preserved
from the raw CSVs).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import _common as C
import pyarrow.parquet as pq

from wattwiser import FND, GOLD, load_manifest, record, save_manifest, setup_logging

log = logging.getLogger(__name__)

DS = 'greend'

NOTES = [
    'no mains: GREEND has no site meter (per-plug metering only)',
    'appliances = every labeled plug (canonical name for the 5 targets, '
    'label slug otherwise); meter k = k-th MAC column of the fnd building '
    'parquet',
    'native cadence preserved (1 s); NULL cells kept verbatim',
]


def fnd_src(building: str) -> str:
    return os.path.join(FND, DS, 'building%s.parquet' % building.split('_')[1])


def build(force: bool = False) -> None:
    bmap = C.load_map()[DS]
    man = load_manifest(DS, NOTES, root=GOLD)
    n = 0
    for b in sorted(bmap):
        meters: dict[str, list[dict[str, Any]]] = bmap[b]['meters']   # {'1': [{label, canonical, room}], ...}
        src = fnd_src(b)
        # meter k -> k-th MAC column (after ts_us), 1-based
        cols = pq.ParquetFile(src).schema_arrow.names
        macs = [c for c in cols if c != 'ts_us']
        thr: dict[str, dict[str, Any]] = {}
        # flatten meters -> [(meter_key, entry)], keeping one gold table per
        # labeled entry (a meter normally carries exactly one label)
        labeled = [(k, e) for k in sorted(meters, key=int)
                   for e in meters[k] if e.get('label')]
        names = C.names_for([e for _, e in labeled])
        for (k, e), name in zip(labeled, names):
            key = '%s/%s' % (b, name)
            if C.skip(man, key, force):
                continue
            t0 = time.time()
            col = macs[int(k) - 1]
            ts, val = C.read_fnd(src, ['ts_us', col])
            st = C.write_gold(DS, b, name, ts, val[col], [src + '#' + col])
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD,
                   label=e['label'], canonical=e.get('canonical'))
            thr[name] = C.thr_record(val[col], e['label'], e.get('canonical'))
            log.info('  %-24s %10d rows  dt=%ss  thr=%sW (%s)'
                     % (key, st['rows'], st['dt_s'], thr[name]['thr_on_W'], e['label']))
            n += 1
        if thr:
            C.merge_thresholds(DS, b, thr)
    save_manifest(DS, man, root=GOLD)
    log.info('greend gold: %d new tables, %d recorded' % (n, len(man['files'])))


def main() -> None:
    a = C.parser('Build GREEND gold tables (labeled plugs, no mains).').parse_args()
    setup_logging()
    log.info('=== gold %s ===' % DS)
    build(force=a.force)


if __name__ == '__main__':
    main()
