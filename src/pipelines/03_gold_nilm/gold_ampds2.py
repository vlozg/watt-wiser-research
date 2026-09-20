#!/usr/bin/env python3
"""Build the AMPds2 gold tables (whole-home mains + labeled appliances).

data/gold/ampds2/building_1/:
  mains.parquet              WHE (whole home electric, real power P, 60 s)
  <name>[_N].parquet         every labeled submeter: canonical name for the
                             5 targets (DWE -> dishwasher, ...), label slug
                             otherwise, _N for repeats

AMPds2 is a single-building dataset sampled at 60 s; fnd stores one parquet
per meter column (Electricity_<label>.parquet), and the appliance map's
meter numbers map to those label stems (site meter 1 = WHE).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import _common as C

from wattwiser import FND, GOLD, load_manifest, record, save_manifest, setup_logging

log = logging.getLogger(__name__)

DS = 'ampds2'

# Per-channel annotations from the EDA (docs/reports/dataset_eda/06_ampds2_eda.ipynb):
# release labels the data contradicts, or channels that are sub-panels, not devices.
NOTES_BY_LABEL = {
    'RSE': 'rental-suite sub-panel: a second household on one meter, not a '
           'single appliance; 22.5% of mains energy (its threshold reflects a '
           'whole suite, not one appliance)',
    'GRE': 'detached-garage sub-panel (27 kWh over 2 years), not a device; '
           'inside WHE but outside the MHE alternative aggregate',
    'HTE': "release label 'Instant Hot Water Unit' is contradicted by the "
           'data (p50 22 W, max 74 W) - the water-heating behaviour lives in '
           'the computed Unmetered remainder instead; treat the label as false',
}

NOTES = [
    'mains = site meter 1 = WHE (whole home electric, column P); '
    'appliances = every labeled submeter, keyed by their label stem '
    '(Electricity_<label>.parquet; canonical name for the 5 targets, '
    'label slug otherwise)',
    'native cadence preserved (60 s); no resampling',
    'coverage: the 20 labeled submeters integrate to 82.1% of mains energy '
    '(16,006 of 19,488 kWh over 2 years); the remaining 17.9% is the '
    "release-computed 'Unmetered' remainder (UNE) - published only in the fnd "
    'wide files, not carried here because it is not a meter (violates S >= P '
    'on 99.3% of minutes) and is water-heating shaped. Model it as the '
    'unknown class, never zero it - see '
    'docs/reports/dataset_eda/06_ampds2_eda.ipynb Q5/Q6',
    'data quality: mains and every appliance share the same 6 all-zero minutes '
    'at the two register incidents (wipe 2012-05-04, meltdown 2013-06-17) - '
    'corrupt logger rows, not outages, copied through per the pass-through '
    'contract; when ingesting our own deployment data, suspect zeros near '
    'register discontinuities',
    'label quality: per-record notes flag release labels contradicted by the '
    'data (HTE) or channels that are sub-panels rather than single devices '
    '(RSE, GRE) - see NOTES_BY_LABEL',
]


def fnd_src(label: str) -> str:
    return os.path.join(FND, DS, 'Electricity_%s.parquet' % label)


def build(force: bool = False) -> None:
    bmap = C.load_map()[DS]
    man = load_manifest(DS, NOTES, root=GOLD)
    n = 0
    for b in sorted(bmap):
        bd: dict[str, Any] = bmap[b]
        meters: dict[str, list[dict[str, Any]]] = bd['meters']
        thr: dict[str, dict[str, Any]] = {}
        # mains: site meter 1 = WHE (the map's meters dict holds submeters only)
        site_label = 'WHE'
        key = '%s/mains' % b
        if not C.skip(man, key, force):
            t0 = time.time()
            src = fnd_src(site_label)
            ts, val = C.read_fnd(src, ['ts_us', 'P'])
            st = C.write_gold(DS, b, 'mains', ts, val['P'], [src])
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD,
                   note='contains the 6 all-zero register-incident minutes '
                        '(2012-05-04, 2013-06-17) - corrupt logger rows, copied '
                        'through per the pass-through contract; see NOTES')
            log.info('  %-24s %10d rows  dt=%ss (site %s)' % (key, st['rows'], st['dt_s'], site_label))
            n += 1
        # appliances: every labeled submeter, flattened
        labeled = [(k, e) for k in sorted(meters, key=int)
                   for e in meters[k] if e.get('label')]
        names = C.names_for([e for _, e in labeled])
        for (_k, e), name in zip(labeled, names):
            key = '%s/%s' % (b, name)
            if C.skip(man, key, force):
                continue
            t0 = time.time()
            src = fnd_src(e['label'])
            ts, val = C.read_fnd(src, ['ts_us', 'P'])
            st = C.write_gold(DS, b, name, ts, val['P'], [src])
            extra: dict[str, Any] = {'label': e['label'], 'canonical': e.get('canonical')}
            if e['label'] in NOTES_BY_LABEL:
                extra['note'] = NOTES_BY_LABEL[e['label']]
            record(man, DS, key, st.pop('path'), st.pop('src'), st, t0, root=GOLD, **extra)
            thr[name] = C.thr_record(val['P'], e['label'], e.get('canonical'))
            log.info('  %-24s %10d rows  dt=%ss  thr=%sW (%s)'
                     % (key, st['rows'], st['dt_s'], thr[name]['thr_on_W'], e['label']))
            n += 1
        if thr:
            C.merge_thresholds(DS, b, thr)
    save_manifest(DS, man, root=GOLD)
    log.info('ampds2 gold: %d new tables, %d recorded' % (n, len(man['files'])))


def main() -> None:
    a = C.parser('Build AMPds2 gold tables (mains + labeled appliances).').parse_args()
    setup_logging()
    log.info('=== gold %s ===' % DS)
    build(force=a.force)


if __name__ == '__main__':
    main()
