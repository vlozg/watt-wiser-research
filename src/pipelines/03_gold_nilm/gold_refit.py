#!/usr/bin/env python3
"""Build the REFIT gold tables (per-house mains + labeled appliances).

data/gold/refit/house_N/:
  mains.parquet              the Aggregate column (native 8 s cadence)
  <name>[_N].parquet         every labeled ApplianceN column: canonical name
                             for the 5 targets, label slug otherwise, _N for
                             repeats (e.g. Fridge + Freezer -> fridge,
                             fridge_2)

REFIT stores one wide parquet per house in fnd (Aggregate + ApplianceN
columns); gold slices the labeled ones out per data/gold/appliance_map.json.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import _common as C

from wattwiser import FND, GOLD, load_manifest, record, save_manifest, setup_logging

log = logging.getLogger(__name__)

DS = 'refit'

NOTES = [
    'mains = Aggregate column; appliances = every other labeled ApplianceN '
    'column in data/gold/appliance_map.json (canonical name for the 5 '
    'targets, label slug otherwise)',
    'native cadence preserved (8 s nominal; dt_s is the measured median gap);'
    ' Issues column stays in fnd'
]


def fnd_src(building: str) -> str:
    return os.path.join(FND, DS, 'CLEAN_House%s.parquet' % building.split('_')[1])


def build(force: bool = False) -> None:
    bmap = C.load_map()[DS]
    man = load_manifest(DS, NOTES, root=GOLD)
    n = 0
    for b in sorted(bmap):
        aps: dict[str, dict[str, Any]] = bmap[b]['appliances']   # {'0': Aggregate, '1': ..., ...}
        src = fnd_src(b)
        cols = ['ts_us'] + ['Appliance%s' % k for k in sorted(aps, key=int) if k != '0']
        # one wide read per house; slice the columns gold needs
        ts, vals = C.read_fnd(src, cols + (['Aggregate'] if '0' in aps else []))
        thr: dict[str, dict[str, Any]] = {}
        if '0' in aps:
            key = '%s/mains' % b
            if not C.skip(man, key, force):
                t0 = time.time()
                st = C.write_gold(DS, b, 'mains', ts, vals['Aggregate'], [src])
                record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD)
                log.info('  %-24s %10d rows  dt=%ss' % (key, st['rows'], st['dt_s']))
                n += 1
        keys = [k for k in sorted(aps, key=int)
                if k != '0' and aps[k].get('label')
                and aps[k]['label'].lower() not in C.AGGREGATE_LABELS]
        names = C.names_for([aps[k] for k in keys])
        for k, name in zip(keys, names):
            key = '%s/%s' % (b, name)
            if C.skip(man, key, force):
                continue
            t0 = time.time()
            col = 'Appliance%s' % k
            st = C.write_gold(DS, b, name, ts, vals[col], [src + '#' + col])
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD,
                   label=aps[k]['label'], canonical=aps[k].get('canonical'))
            thr[name] = C.thr_record(vals[col], aps[k]['label'], aps[k].get('canonical'))
            log.info('  %-24s %10d rows  dt=%ss  thr=%sW (%s)'
                     % (key, st['rows'], st['dt_s'], thr[name]['thr_on_W'], aps[k]['label']))
            n += 1
        if thr:
            C.merge_thresholds(DS, b, thr)
    save_manifest(DS, man, root=GOLD)
    log.info('refit gold: %d new tables, %d recorded' % (n, len(man['files'])))


def main() -> None:
    a = C.parser('Build REFIT gold tables (mains + labeled appliances).').parse_args()
    setup_logging()
    log.info('=== gold %s ===' % DS)
    build(force=a.force)


if __name__ == '__main__':
    main()
