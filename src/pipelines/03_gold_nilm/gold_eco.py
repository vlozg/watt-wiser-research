#!/usr/bin/env python3
"""Build the ECO gold tables (per-house mains + labeled plugs).

data/gold/eco/house_NN/:
  mains.parquet              smart-meter total power (powerallphases, native 1 s)
  <name>[_N].parquet         every labeled plug (native 1 s cadence)

ECO plugs are a partial meter set (only the measured outlets), so appliance
energy shares in thresholds.json are lower bounds, not whole-home shares.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import _common as C

from wattwiser import FND, GOLD, load_manifest, record, save_manifest, setup_logging

log = logging.getLogger(__name__)

DS = 'eco'

NOTES = [
    'mains = smart-meter powerallphases (all phases summed, as recorded); '
    'appliances = every labeled plug in data/gold/appliance_map.json '
    '(canonical name for the 5 targets, label slug otherwise)',
    'native cadence preserved (1 s); plugs cover a partial meter set',
]


def build(force: bool = False) -> None:
    bmap = C.load_map()[DS]
    man = load_manifest(DS, NOTES, root=GOLD)
    n = 0
    for b in sorted(bmap):
        plugs: dict[str, dict[str, Any]] = bmap[b]['plugs']   # {'01': {label, canonical}, ...}
        thr: dict[str, dict[str, Any]] = {}
        # mains: the house smart meter (whole home)
        key = '%s/mains' % b
        if not C.skip(man, key, force):
            t0 = time.time()
            src = os.path.join(FND, DS, b, 'sm.parquet')
            ts, val = C.read_fnd(src, ['ts_us', 'powerallphases'])
            st = C.write_gold(DS, b, 'mains', ts, val['powerallphases'], [src])
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD)
            if st['rows'] == 0:
                log.warning('  %s is empty (this house has no smart-meter data)' % key)
            log.info('  %-24s %10d rows  dt=%ss' % (key, st['rows'], st['dt_s']))
            n += 1
        # appliances: every labeled plug, in plug-number order
        keys = [k for k in sorted(plugs) if plugs[k].get('label')
                and plugs[k]['label'].lower() not in C.AGGREGATE_LABELS]
        names = C.names_for([plugs[k] for k in keys])
        for k, name in zip(keys, names):
            key = '%s/%s' % (b, name)
            if C.skip(man, key, force):
                continue
            t0 = time.time()
            src = os.path.join(FND, DS, b, 'plug_%s.parquet' % k)
            ts, val = C.read_fnd(src, ['ts_us', 'consumption'])
            st = C.write_gold(DS, b, name, ts, val['consumption'], [src])
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD,
                   label=plugs[k]['label'], canonical=plugs[k].get('canonical'))
            thr[name] = C.thr_record(val['consumption'], plugs[k]['label'], plugs[k].get('canonical'))
            log.info('  %-24s %10d rows  dt=%ss  thr=%sW (%s)'
                     % (key, st['rows'], st['dt_s'], thr[name]['thr_on_W'], plugs[k]['label']))
            n += 1
        if thr:
            C.merge_thresholds(DS, b, thr)
    save_manifest(DS, man, root=GOLD)
    log.info('eco gold: %d new tables, %d recorded' % (n, len(man['files'])))


def main() -> None:
    a = C.parser('Build ECO gold tables (mains + labeled plugs).').parse_args()
    setup_logging()
    log.info('=== gold %s ===' % DS)
    build(force=a.force)


if __name__ == '__main__':
    main()
