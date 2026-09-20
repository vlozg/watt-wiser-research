#!/usr/bin/env python3
"""Build the UK-DALE gold tables (per-house mains + labeled appliances).

data/gold/ukdale/house_N/:
  mains.parquet              channel_1 aggregate (native 1 s cadence)
  <name>[_N].parquet         every other labeled channel (native 6 s cadence)

Channels are copied through from data/fnd/ukdale at full fidelity; gold only
applies the label resolution from data/gold/appliance_map.json and the
uniform (ts_us, w) schema.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import _common as C

from wattwiser import FND, GOLD, load_manifest, record, save_manifest, setup_logging

log = logging.getLogger(__name__)

DS = 'ukdale'

NOTES = [
    'mains = channel_1 (aggregate); appliances = every other labeled channel '
    'in data/gold/appliance_map.json (canonical name for the 5 targets, '
    'label slug otherwise; repeats get _N suffixes)',
    'native cadence preserved (6 s nominal; dt_s is the measured median gap)'
]


def fnd_src(building: str, channel: str) -> str:
    """fnd parquet path of one UK-DALE power channel."""
    return os.path.join(FND, DS, building, 'channel_%s.parquet' % channel)


def build(force: bool = False) -> None:
    bmap = C.load_map()[DS]
    man = load_manifest(DS, NOTES, root=GOLD)
    n = 0
    for b in sorted(bmap):
        ch: dict[str, dict[str, Any]] = bmap[b]['channels']
        thr: dict[str, dict[str, Any]] = {}
        # mains: the single aggregate channel (channel 1)
        agg = next((k for k, v in ch.items() if v.get('label') == 'aggregate'), None)
        if agg is not None:
            key = '%s/mains' % b
            if not C.skip(man, key, force):
                t0 = time.time()
                src = fnd_src(b, agg)
                ts, val = C.read_fnd(src, ['ts_us', 'v0'])
                st = C.write_gold(DS, b, 'mains', ts, val['v0'], [src])
                record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD)
                log.info('  %-24s %10d rows  dt=%ss' % (key, st['rows'], st['dt_s']))
                n += 1
        # appliances: every labeled channel except the aggregate, in numeric
        # channel order so repeat naming is stable
        keys = [k for k in sorted(ch, key=int)
                if ch[k].get('label') and ch[k]['label'].lower() not in C.AGGREGATE_LABELS]
        names = C.names_for([ch[k] for k in keys])
        for k, name in zip(keys, names):
            key = '%s/%s' % (b, name)
            if C.skip(man, key, force):
                continue
            t0 = time.time()
            src = fnd_src(b, k)
            ts, val = C.read_fnd(src, ['ts_us', 'v0'])
            st = C.write_gold(DS, b, name, ts, val['v0'], [src])
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD,
                   label=ch[k]['label'], canonical=ch[k].get('canonical'))
            thr[name] = C.thr_record(val['v0'], ch[k]['label'], ch[k].get('canonical'))
            log.info('  %-24s %10d rows  dt=%ss  thr=%sW (%s)'
                     % (key, st['rows'], st['dt_s'], thr[name]['thr_on_W'], ch[k]['label']))
            n += 1
        if thr:
            C.merge_thresholds(DS, b, thr)
    save_manifest(DS, man, root=GOLD)
    log.info('ukdale gold: %d new tables, %d recorded' % (n, len(man['files'])))


def main() -> None:
    a = C.parser('Build UK-DALE gold tables (mains + labeled appliances).').parse_args()
    setup_logging()
    log.info('=== gold %s ===' % DS)
    build(force=a.force)


if __name__ == '__main__':
    main()
