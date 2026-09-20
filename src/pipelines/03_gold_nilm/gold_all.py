#!/usr/bin/env python3
"""Build gold tables for all six datasets.

Calls the per-dataset builders in src/pipelines/03_gold_nilm/. Existing gold
tables (per data/gold/<ds>/manifest.json) are skipped, so this is safe to
re-run; pass --force to rebuild. Stops at the first failure unless
--continue-on-error.
"""
from __future__ import annotations

import argparse
import logging
import sys

import gold_ampds2
import gold_eco
import gold_greend
import gold_redd
import gold_refit
import gold_ukdale

from wattwiser import setup_logging

log = logging.getLogger(__name__)

DATASETS = [
    ('ukdale', gold_ukdale),
    ('refit', gold_refit),
    ('eco', gold_eco),
    ('greend', gold_greend),
    ('redd', gold_redd),
    ('ampds2', gold_ampds2),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='rebuild even if gold tables exist')
    ap.add_argument('--continue-on-error', action='store_true')
    a = ap.parse_args()
    log.info('=== gold layer: all datasets ===')
    failures: list[str] = []
    for key, mod in DATASETS:
        log.info('--- %s ---' % key)
        try:
            mod.build(force=a.force)
        except Exception as exc:
            log.error('%s FAILED: %s' % (key, exc))
            failures.append(key)
            if not a.continue_on_error:
                break
    if failures:
        log.error('FAILED: %s' % ', '.join(failures))
        sys.exit(1)
    log.info('=== gold layer complete ===')


if __name__ == '__main__':
    setup_logging()
    main()
