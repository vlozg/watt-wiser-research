"""Shared helpers for the 00_download_dataset pipeline.

Each download_<dataset>.py pulls one public Google Drive zip (uploaded by the
user), extracts it, normalizes the layout to data/raw/<dataset>/, and verifies
the resulting tree against raw_manifest.json (file names + byte sizes captured
from the original staged copy). Extraction is layout-agnostic: whatever
top-level wrapper the zip uses is resolved by moving the single root directory
(or its entries) into place.

If any download fails, the original hosts are listed in docs/Data source note.md.
"""
import argparse
import json
import os
import shutil
import time
import zipfile

from wattwiser import RAW, ensure, human, log

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, 'raw_manifest.json')
HINT = ('download failed - fetch the zip manually or check the original hosts listed in '
        'docs/Data source note.md; the Drive links live in '
        'src/pipelines/00_download_dataset/README.md')


def _load_expected():
    """raw_manifest.json -> {dataset_key: {relative path: expected bytes}}."""
    with open(MANIFEST, encoding='utf-8') as f:
        return json.load(f)


def verify_tree(target, expected):
    """Compare a staged tree against {relpath: bytes}; returns a problem list."""
    bad = []
    seen = {}
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


def download_dataset(dataset, url, manifest_key=None, force=False, dest=None):
    """Stage one dataset; see the module docstring for the full flow.

    Steps:
      1. existing target, verified against the manifest -> skip
      2. --force: move the existing tree aside to .bak_<dataset> (never deleted)
      3. download the zip into .staging_<dataset>/
      4. extract + normalize the layout to <root>/<dataset>
      5. verify every file name + size against raw_manifest.json
      6. remove staging

    `dest` overrides the data root (testing only); `manifest_key` is the
    raw_manifest.json key when the staged dir name differs (e.g. ukdale-full).
    """
    root = dest if dest is not None else RAW
    mkey = manifest_key or dataset
    target = os.path.join(root, dataset)

    # 1. skip fast path: existing tree that already matches the manifest
    if os.path.exists(target) and not force:
        expected = _load_expected().get(mkey, {})
        bad = verify_tree(target, expected) if expected else ['no manifest entry']
        if not bad:
            log('%s: already present and verified, skip' % dataset)
            return target
        log('%s: already present but differs from the manifest (%d problems) - re-run with --force' % (dataset, len(bad)))
        for b in bad[:5]:
            log('  %s' % b)
        return target

    # 2. --force: keep the old tree, never delete user data
    bak = os.path.join(root, '.bak_%s' % dataset)
    if force and os.path.exists(target):
        if os.path.exists(bak):
            shutil.rmtree(bak)
        os.replace(target, bak)
        log('%s: moved existing tree to %s' % (dataset, bak))

    # 3. download into staging (atomic: the target only appears once verified)
    staging = os.path.join(root, '.staging_%s' % dataset)
    shutil.rmtree(staging, ignore_errors=True)
    ensure(staging)
    zpath = os.path.join(staging, dataset + '.zip')
    try:
        import gdown
    except ImportError:
        log('ERROR: gdown is not installed (uv sync should provide it)')
        log(HINT)
        raise
    t0 = time.time()
    log('%s: downloading from Google Drive...' % dataset)
    try:
        gdown.download(url=url, output=zpath, quiet=True)
    except Exception as exc:
        log('ERROR: gdown failed for %s: %s' % (dataset, exc))
        log(HINT)
        raise RuntimeError('download failed for %s' % dataset) from exc
    if not os.path.exists(zpath) or os.path.getsize(zpath) == 0:
        log('ERROR: could not download %s' % url)
        log(HINT)
        raise RuntimeError('download failed for %s' % dataset)
    log('%s: downloaded %s in %.0fs' % (dataset, human(os.path.getsize(zpath)), time.time() - t0))

    # 4. extract + normalize: fold the zip's top-level wrapper into <dataset>
    extract_dir = os.path.join(staging, 'extract')
    ensure(extract_dir)
    log('%s: extracting zip...' % dataset)
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
    expected = _load_expected().get(mkey, {})
    if not expected:
        log('WARNING: no manifest entry for %s - layout not verified' % mkey)
    else:
        bad = verify_tree(target, expected)
        if bad:
            log('ERROR: %s tree does not match raw_manifest.json:' % dataset)
            for b in bad[:10]:
                log('  %s' % b)
            raise RuntimeError('verification failed for %s (zip content differs from the staged layout?)' % dataset)
        log('%s: verified %d files, %s' % (dataset, len(expected), human(sum(expected.values()))))

    # 6. cleanup
    shutil.rmtree(staging, ignore_errors=True)
    log('%s: staged at %s' % (dataset, target))
    return target


def make_parser():
    """argparse for the download scripts: --force / --dest."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='re-download and replace an existing staged copy')
    ap.add_argument('--dest', default=None, help='override the data root (testing only)')
    return ap
