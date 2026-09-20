#!/usr/bin/env python3
"""Download + stage the six datasets from the public Google Drive zips.

With no dataset arguments, all six are staged in registry order. Each zip is
extracted, normalized to data/raw/<staged>/ and verified against
raw_manifest.json (file names + byte sizes), so an existing verified tree is
skipped and re-runs are safe. --force re-downloads and replaces an existing
tree (the old tree is kept as .bak_<staged>, never deleted). --dest overrides
the data root (testing only).

Every zip was uploaded publicly by the user; if a download fails, fetch it
manually or check the original hosts listed in
docs/datasets/data-collection.md (original-host list in section 3).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass

import gdown

from wattwiser import RAW, ensure, human, setup_logging

log = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, 'raw_manifest.json')
HINT = ('download failed - fetch the zip manually or check the original hosts listed in '
        'docs/datasets/data-collection.md (original-host list in section 3); the Drive links live in '
        'src/pipelines/00_download_dataset/README.md')


@dataclass(frozen=True)
class DriveZip:
    """One dataset's public Drive zip: staged dir name, raw_manifest key, URL."""

    manifest_key: str  # key inside raw_manifest.json (differs from the CLI name for ukdale)
    staged: str        # directory under data/raw/
    url: str


# static registry (no dynamic imports) - one entry per dataset, staged in dict order
DATASETS: dict[str, DriveZip] = {
    'ukdale': DriveZip(manifest_key='ukdale', staged='ukdale-full',
                       url='https://drive.google.com/file/d/18gaDLfUJ5YdrkSMUqG_FbVhiBfUTjVHo/view?usp=drive_link'),
    'refit': DriveZip(manifest_key='refit', staged='REFIT',
                      url='https://drive.google.com/file/d/1wQTWXumWQoeavS58gmorDYTWV4OPlayi/view?usp=drive_link'),
    'eco': DriveZip(manifest_key='eco', staged='ECO',
                    url='https://drive.google.com/file/d/1GA_lPkp1mxPioV_bKlQHjv_uUdkooJQQ/view?usp=drive_link'),
    'greend': DriveZip(manifest_key='greend', staged='GREEND_0-2_300615',
                       url='https://drive.google.com/file/d/1DB8Hmqg3-MWH6y4K3SxjgKS3dUqjF6uU/view?usp=drive_link'),
    'redd': DriveZip(manifest_key='redd', staged='redd',
                     url='https://drive.google.com/file/d/1N33acJ_MG2JyCz4sm-g98e-nZ9jEtokK/view?usp=drive_link'),
    'ampds2': DriveZip(manifest_key='ampds2', staged='AMPds2',
                       url='https://drive.google.com/file/d/1j8jNWANQqVM0uG7-6-TgFzDEsw8OivBZ/view?usp=drive_link'),
}


def _load_expected() -> dict[str, dict[str, int]]:
    """raw_manifest.json -> {dataset_key: {relative path: expected bytes}}."""
    with open(MANIFEST, encoding='utf-8') as f:
        return json.load(f)


def verify_tree(target: str, expected: dict[str, int]) -> list[str]:
    """Compare a staged tree against {relpath: bytes}; returns a problem list."""
    bad: list[str] = []
    seen: dict[str, int] = {}
    for root, _dirs, files in os.walk(target):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, target)
            seen[rel] = os.path.getsize(full)
            want = expected.get(rel)
            if want is None:
                bad.append('unexpected file %s' % rel)
            elif want != seen[rel]:
                bad.append('size %s: %d != %d' % (rel, seen[rel], want))
    for rel in expected:
        if rel not in seen:
            bad.append('missing file %s' % rel)
    return bad


def download_one(ds: DriveZip, *, force: bool = False, dest: str | None = None) -> str:
    """Stage one dataset; see the module docstring for the full flow.

    Steps:
      1. existing target, verified against the manifest -> skip
      2. --force: move the existing tree aside to .bak_<staged> (never deleted)
      3. download the zip into .staging_<staged>/
      4. extract + normalize the layout to <root>/<staged>
      5. verify every file name + size against raw_manifest.json
      6. remove staging

    Returns the staged target directory.
    """
    root = dest if dest is not None else RAW
    target = os.path.join(root, ds.staged)

    # 1. skip fast path: existing tree that already matches the manifest
    if os.path.exists(target) and not force:
        expected = _load_expected().get(ds.manifest_key, {})
        bad = verify_tree(target, expected) if expected else ['no manifest entry']
        if not bad:
            log.info('%s: already present and verified, skip' % ds.staged)
            return target
        log.warning('%s: already present but differs from the manifest (%d problems) - re-run with --force',
                    ds.staged, len(bad))
        for b in bad[:5]:
            log.info('  %s' % b)
        return target

    # 2. --force: keep the old tree, never delete user data
    bak = os.path.join(root, '.bak_%s' % ds.staged)
    if force and os.path.exists(target):
        if os.path.exists(bak):
            shutil.rmtree(bak)
        os.replace(target, bak)
        log.info('%s: moved existing tree to %s' % (ds.staged, bak))

    # 3. download into staging (atomic: the target only appears once verified)
    staging = os.path.join(root, '.staging_%s' % ds.staged)
    shutil.rmtree(staging, ignore_errors=True)
    ensure(staging)
    zpath = os.path.join(staging, ds.staged + '.zip')
    t0 = time.time()
    log.info('%s: downloading from Google Drive...' % ds.staged)
    try:
        gdown.download(url=ds.url, output=zpath, quiet=True)
    except Exception as exc:
        log.error('gdown failed for %s: %s' % (ds.staged, exc))
        log.error(HINT)
        raise RuntimeError('download failed for %s' % ds.staged) from exc
    if not os.path.exists(zpath) or os.path.getsize(zpath) == 0:
        log.error('could not download %s' % ds.url)
        log.error(HINT)
        raise RuntimeError('download failed for %s' % ds.staged)
    log.info('%s: downloaded %s in %.0fs' % (ds.staged, human(os.path.getsize(zpath)), time.time() - t0))

    # 4. extract + normalize: fold the zip's top-level wrapper into <staged>
    extract_dir = os.path.join(staging, 'extract')
    ensure(extract_dir)
    log.info('%s: extracting zip...' % ds.staged)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(extract_dir)
    entries = sorted(os.listdir(extract_dir))
    ensure(os.path.dirname(target))
    if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
        os.replace(os.path.join(extract_dir, entries[0]), target)
    else:
        ensure(target)
        for e in entries:
            os.replace(os.path.join(extract_dir, e), os.path.join(target, e))

    # 5. verify every file name + byte size against raw_manifest.json
    expected = _load_expected().get(ds.manifest_key, {})
    if not expected:
        log.warning('no manifest entry for %s - layout not verified' % ds.manifest_key)
    else:
        bad = verify_tree(target, expected)
        if bad:
            log.error('%s tree does not match raw_manifest.json:' % ds.staged)
            for b in bad[:10]:
                log.info('  %s' % b)
            raise RuntimeError('verification failed for %s (zip content differs from the staged layout?)' % ds.staged)
        log.info('%s: verified %d files, %s' % (ds.staged, len(expected), human(sum(expected.values()))))

    # 6. cleanup
    shutil.rmtree(staging, ignore_errors=True)
    log.info('%s: staged at %s' % (ds.staged, target))
    return target


def make_parser() -> argparse.ArgumentParser:
    """argparse for the download CLI: dataset subset / --force / --continue-on-error / --dest."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('datasets', nargs='*', choices=tuple(DATASETS), metavar='dataset',
                    help='stage only these (default: all of: %s)' % ' '.join(DATASETS))
    ap.add_argument('--force', action='store_true', help='re-download and replace existing trees')
    ap.add_argument('--continue-on-error', action='store_true', help='keep going after a failure')
    ap.add_argument('--dest', default=None, help='override the data root (testing only)')
    return ap


def main(argv: list[str] | None = None) -> None:
    """Stage the requested datasets; exit 1 if any failed."""
    a = make_parser().parse_args(argv)
    setup_logging()
    keys = a.datasets or list(DATASETS)
    log.info('=== download: %s ===' % ', '.join(keys))
    failures: list[str] = []
    for key in keys:
        log.info('--- %s ---' % key)
        try:
            download_one(DATASETS[key], force=a.force, dest=a.dest)
        except Exception as exc:
            log.error('%s FAILED: %s' % (key, exc))
            failures.append(key)
            if not a.continue_on_error:
                break
    if failures:
        log.error('FAILED: %s' % ', '.join(failures))
        sys.exit(1)
    log.info('=== staged: %s ===' % ', '.join(keys))


if __name__ == '__main__':
    main()
