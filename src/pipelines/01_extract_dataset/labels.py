"""Merge the per-dataset appliance-label extractors into data/gold/appliance_map.json.

Each extract_<dataset>.py owns its dataset's labels (extract_labels() plus a
--labels CLI writing its own slice); this driver imports all six and writes
the combined map consumed by the gold layer.

Usage: .venv/bin/python3 src/pipelines/01_extract_dataset/labels.py
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import extract_ampds2
import extract_eco
import extract_greend
import extract_redd
import extract_refit
import extract_ukdale

from wattwiser import ensure, setup_logging
from wattwiser.labels import GOLD_DIR, TARGETS, BuildingLabels

log = logging.getLogger(__name__)

MODULES = [('ukdale', extract_ukdale), ('refit', extract_refit), ('eco', extract_eco),
           ('redd', extract_redd), ('ampds2', extract_ampds2), ('greend', extract_greend)]

NOTES = [
    'canonical=None means a labeled appliance outside the 5 client targets.',
    'refit: Washer Dryer mapped to washing_machine (combined machine).',
    'greend: meter k = k-th MAC column of the raw CSVs; House#5 m1-m2 and'
    'House#7 m8-m9 are total outlets / total lights aggregates (unlabeled).',
    'No kettle exists in redd or ampds2 (US datasets); verified in metadata.',
    'Per-dataset slices also written by each extract script: --labels flag.',
]


def main() -> None:
    out: dict[str, Any] = {'_meta': {
        'generated_by': 'src/pipelines/01_extract_dataset/labels.py',
        'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'canonical_targets': TARGETS,
        'notes': NOTES,
    }}
    # every dataset contributes its slice: extract_labels() -> dataclass
    # record dicts (schema in wattwiser/labels.py)
    for name, mod in MODULES:
        buildings: dict[str, BuildingLabels] = mod.extract_labels()
        out[name] = {k: b.record() for k, b in buildings.items()}
        log.info('%s: %d buildings' % (name, len(buildings)))
    ensure(GOLD_DIR)
    outp = os.path.join(GOLD_DIR, 'appliance_map.json')
    with open(outp, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    log.info('wrote %s' % outp)


if __name__ == '__main__':
    setup_logging()
    main()
