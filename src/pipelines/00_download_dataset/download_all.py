#!/usr/bin/env python3
"""Download + stage all six datasets from the public Google Drive zips.

Each dataset stages to data/raw/<dir>/ and is verified against raw_manifest.json
(file names + byte sizes). An existing verified tree is skipped, so this is safe
to re-run. Stops at the first failure unless --continue-on-error.

If any download fails, the original hosts are listed in docs/Data source note.md.
"""
import argparse
import importlib
import os
import sys

from wattwiser import log
from _common import HINT

DATASETS = [
    ('ukdale', 'download_ukdale'),
    ('refit', 'download_refit'),
    ('eco', 'download_eco'),
    ('greend', 'download_greend'),
    ('redd', 'download_redd'),
    ('ampds2', 'download_ampds2'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='re-download and replace existing trees')
    ap.add_argument('--continue-on-error', action='store_true')
    ap.add_argument('--dest', default=None, help='override the data root (testing only)')
    a = ap.parse_args()
    log('=== download all datasets ===')
    failures = []
    for key, mod in DATASETS:
        log('--- %s ---' % key)
        try:
            importlib.import_module(mod).download(force=a.force, dest=a.dest)
        except Exception as exc:
            log('%s FAILED: %s' % (key, exc))
            failures.append(key)
            if not a.continue_on_error:
                break
    if failures:
        log('FAILED: %s' % ', '.join(failures))
        log(HINT)
        sys.exit(1)
    log('=== all datasets staged ===')


if __name__ == '__main__':
    main()