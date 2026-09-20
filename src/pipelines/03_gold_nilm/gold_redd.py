#!/usr/bin/env python3
"""Build the REDD gold tables (per-building mains + labeled appliances).

data/gold/redd/building_N/:
  mains.parquet              sum of the site meters (mains1 + mains2, native
                             ~3 s cadence; the two panel meters share one
                             timestamp grid per building)
  <name>[_N].parquet         every labeled submeter: canonical name for the
                             5 targets, label slug otherwise, _N for repeats
                             (e.g. building_1 has washing_machine,
                             washing_machine_2)

REDD site meters measure the two split-phase panels; their sum is the
whole-home aggregate.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import _common as C
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from wattwiser import FND, GOLD, load_manifest, record, save_manifest, setup_logging

log = logging.getLogger(__name__)

DS = 'redd'

NOTES = [
    'mains = sum of the site meters (mains1 + mains2, same timestamp grid '
    'within a building); dt_s is the measured median gap and varies by building',
    'appliances = every labeled submeter in data/gold/appliance_map.json '
    '(canonical name for the 5 targets, label slug otherwise; repeats get '
    '_2/_3 suffixes)',
    'native cadence preserved; no resampling',
]


def fnd_src(building: str, meter: str) -> str:
    return os.path.join(FND, DS, 'building%s_elec_meter%s.parquet' % (building.split('_')[1], meter))


def site_mains(building: str, site_meters: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Sum the site-meter channels into one mains series.

    Identical timestamp grids (the REDD case) sum directly; anything else
    falls back to a keyed sum on the union of timestamps so no sample is
    invented, and the cadence difference shows up in dt_s.
    """
    srcs = [fnd_src(building, m) for m in site_meters]
    tables = [pq.read_table(s, columns=['ts_us', 'value_0']) for s in srcs]
    ts = tables[0].column('ts_us').to_numpy().astype('int64')
    grids_equal = all((t.column('ts_us').to_numpy().astype('int64') == ts).all()
                      for t in tables[1:])
    if grids_equal:
        w = np.zeros(len(ts), dtype='float64')
        for t in tables:
            w += t.column('value_0').to_numpy().astype('float64')
    else:
        parts: list[pd.DataFrame] = []
        for t in tables:
            parts.append(pd.DataFrame({'ts_us': t.column('ts_us').to_numpy().astype('int64'),
                                       'w': t.column('value_0').to_numpy().astype('float64')}))
        g = pd.concat(parts).groupby('ts_us', sort=True).sum()
        ts = g.index.to_numpy().astype('int64')
        w = g['w'].to_numpy().astype('float64')
    return ts, w, srcs


def build(force: bool = False) -> None:
    bmap = C.load_map()[DS]
    man = load_manifest(DS, NOTES, root=GOLD)
    n = 0
    for b in sorted(bmap):
        bd: dict[str, Any] = bmap[b]
        site, meters = bd['site_meters'], bd['meters']
        thr: dict[str, dict[str, Any]] = {}
        # mains: sum of the panel meters
        key = '%s/mains' % b
        if not C.skip(man, key, force):
            t0 = time.time()
            ts, w, srcs = site_mains(b, site)
            st = C.write_gold(DS, b, 'mains', ts, w, srcs)
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD)
            log.info('  %-24s %10d rows  dt=%ss (site %s)' % (key, st['rows'], st['dt_s'], site))
            n += 1
        # appliances: every labeled submeter in meter-number order
        keys = [k for k in sorted(meters, key=int)
                if meters[k].get('label')
                and meters[k]['label'].lower() not in C.AGGREGATE_LABELS]
        names = C.names_for([meters[k] for k in keys])
        for k, name in zip(keys, names):
            key = '%s/%s' % (b, name)
            if C.skip(man, key, force):
                continue
            t0 = time.time()
            src = fnd_src(b, k)
            ts, val = C.read_fnd(src, ['ts_us', 'value_0'])
            st = C.write_gold(DS, b, name, ts, val['value_0'], [src])
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD,
                   label=meters[k]['label'], canonical=meters[k].get('canonical'))
            thr[name] = C.thr_record(val['value_0'], meters[k]['label'], meters[k].get('canonical'))
            log.info('  %-24s %10d rows  dt=%ss  thr=%sW (%s)'
                     % (key, st['rows'], st['dt_s'], thr[name]['thr_on_W'], meters[k]['label']))
            n += 1
        if thr:
            C.merge_thresholds(DS, b, thr)
    save_manifest(DS, man, root=GOLD)
    log.info('redd gold: %d new tables, %d recorded' % (n, len(man['files'])))


def main() -> None:
    a = C.parser('Build REDD gold tables (mains + labeled appliances).').parse_args()
    setup_logging()
    log.info('=== gold %s ===' % DS)
    build(force=a.force)


if __name__ == '__main__':
    main()
