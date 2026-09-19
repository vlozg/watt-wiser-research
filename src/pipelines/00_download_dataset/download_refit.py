#!/usr/bin/env python3
# Download the REFIT dataset zip from Google Drive and stage it at data/raw/REFIT/.
#
# Zip uploaded publicly by the user; if the download fails, the original hosts are
# listed in docs/Data source note.md.
import os
import sys

from wattwiser import log
from _common import download_dataset, make_parser

DATASET = "REFIT"      # staged directory under data/raw/
MANIFEST_KEY = "refit"  # key inside raw_manifest.json
DRIVE_URL = "https://drive.google.com/file/d/1wQTWXumWQoeavS58gmorDYTWV4OPlayi/view?usp=drive_link"


def download(force=False, dest=None):
    return download_dataset(DATASET, DRIVE_URL, manifest_key=MANIFEST_KEY, force=force, dest=dest)


if __name__ == '__main__':
    ap = make_parser()
    a = ap.parse_args()
    log('=== %s download ===' % DATASET)
    try:
        download(force=a.force, dest=a.dest)
    except Exception as exc:
        log('ERROR: %s' % exc)
        sys.exit(1)
    log('=== done %s download ===' % DATASET)