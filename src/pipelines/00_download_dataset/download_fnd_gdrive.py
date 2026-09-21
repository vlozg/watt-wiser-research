#!/usr/bin/env python3
"""Download and/or extract the processed FND parquet layer from Google Drive.

The FND staging tree (data/fnd/) is archived as one zip per dataset in
data/fnd_zips/ (fnd-ampds2.zip, fnd-eco.zip, fnd-greend.zip, fnd-qa.zip,
fnd-redd.zip, fnd-refit.zip, fnd-ukdale.zip). Every zip has arcname root
fnd/<dataset>/, so extracting into data/ recreates data/fnd/<dataset>/.

This is the shortcut for machines that only need the processed parquet layer:
about 12 GB of zips instead of the about 47 GB raw download plus re-running
01_extract_dataset. download.py in this directory stages the raw layer
(data/raw/); this script restores the already-extracted data/fnd/ trees.

Workflow
--------
Producer: upload each zip in data/fnd_zips/ to Google Drive, then record the
share links in data/fnd_zips/gdrive_ids.txt, one per line (the current links
are also listed in this directory's README.md):

    fnd-ukdale.zip https://drive.google.com/file/d/FILE_ID/view?usp=sharing

Consumer (any machine with this repo, after 'uv sync'):

    uv run python3 src/pipelines/00_download_dataset/download_fnd_gdrive.py              # download + extract everything
    uv run python3 src/pipelines/00_download_dataset/download_fnd_gdrive.py ukdale eco   # subset by name
    uv run python3 src/pipelines/00_download_dataset/download_fnd_gdrive.py fnd-eco.zip=<share link>   # one-off link
    uv run python3 src/pipelines/00_download_dataset/download_fnd_gdrive.py --download-only   # fetch + verify, skip extract
    uv run python3 src/pipelines/00_download_dataset/download_fnd_gdrive.py --extract-only    # verify + unpack local zips, no download
    uv run python3 src/pipelines/00_download_dataset/download_fnd_gdrive.py --check           # sha256-verify local zips only

Default: download with gdown (handles Drive's large-file confirmation flow),
SHA-256-verify against data/fnd_zips/SHA256SUMS, and unpack into data/.
An existing zip that already matches SHA256SUMS skips the download. Existing
non-empty data/fnd/<dataset> dirs are never clobbered without --force. gdown
does not resume partial downloads, so an interrupted fetch restarts from zero.

Requires: the uv environment (the wattwiser helper package provides logging
setup; gdown is already a project dependency). --check and --extract-only
run without gdown.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import zipfile
from pathlib import Path

from wattwiser import setup_logging

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "fnd_zips"
DEFAULT_EXTRACT_TO = REPO_ROOT / "data"

log = logging.getLogger(__name__)


def canonical_name(item: str) -> str:
    """Normalize 'ukdale', 'fnd-ukdale', 'fnd-ukdale.zip' to 'fnd-ukdale.zip'."""
    slug = item.strip()
    if slug.startswith("fnd-"):
        slug = slug[len("fnd-"):]
    if slug.endswith(".zip"):
        slug = slug[: -len(".zip")]
    return "fnd-" + slug + ".zip"


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_sums(path: Path) -> dict[str, str]:
    """Parse a sha256sum-style file: '<digest>  <name>' per line."""
    sums: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                log.warning("unparseable SHA256SUMS line: %r", line)
                continue
            sums[parts[1].strip()] = parts[0].lower()
    else:
        log.warning("%s not found; checksum verification disabled", path)
    return sums


def load_mapping(path: Path) -> dict[str, str]:
    """Parse gdrive_ids.txt: '<zip name> <share url or file id>' per line."""
    mapping: dict[str, str] = {}
    if not path.exists():
        log.warning("mapping file %s not found", path)
        return mapping
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        name = canonical_name(parts[0])
        link = parts[1].strip() if len(parts) > 1 else ""
        if not link:
            log.warning("%s:%d: no link yet for %s, skipping", path.name, lineno, name)
            continue
        mapping[name] = link
    return mapping


def parse_items(items: list[str], mapping: dict[str, str], out_dir: Path) -> list[tuple[str, str]]:
    """Resolve positional args ('name' or 'name=link') to (name, link) pairs."""
    targets: list[tuple[str, str]] = []
    for item in items:
        if "=" in item:
            name, link = item.split("=", 1)
            targets.append((canonical_name(name), link.strip()))
            continue
        name = canonical_name(item)
        if name in mapping:
            targets.append((name, mapping[name]))
        elif (out_dir / name).exists():
            log.info("no link for %s; using local copy in %s", name, out_dir)
            targets.append((name, None))
        else:
            raise SystemExit(
                "no Google Drive link for " + name
                + ": add it to the mapping file or pass '" + name + "=<share link>'"
            )
    return targets


def extract_zip(dest: Path, args) -> bool:
    if args.download_only:
        log.info("%s verified, not extracted", dest)
        return True
    with zipfile.ZipFile(dest) as z:
        members = z.namelist()
        roots = sorted({m.split("/")[0] for m in members if m.strip()})
        if roots != ["fnd"]:
            log.error("%s: unexpected arcname root(s) %s", dest.name, roots)
            return False
        dataset = sorted({m.split("/")[1] for m in members if "/" in m and m.split("/")[1]})
        if len(dataset) != 1:
            log.error("%s: expected exactly one dataset inside, got %s", dest.name, dataset)
            return False
        # members already start with 'fnd/<dataset>/', so extract at the root
        extract_root = args.extract_to
        final_dir = extract_root / "fnd" / dataset[0]
        if final_dir.exists() and any(final_dir.iterdir()) and not args.force:
            log.error("%s already exists; re-run with --force to overwrite", final_dir)
            return False
        log.info("unzip %s -> %s (%d entries)", dest, extract_root, len(members))
        extract_root.mkdir(parents=True, exist_ok=True)
        # extractall CRC-checks every member as it is written
        z.extractall(extract_root)
    log.info("restored %s (%d files)", final_dir, len(members))
    return True


def fetch_one(name: str, link: str, sums: dict[str, str], args) -> bool:
    dest = args.out_dir / name
    if args.extract_only:
        if not dest.exists():
            log.error("%s: not found in %s; run without --extract-only to download it",
                      name, args.out_dir)
            return False
        if name in sums:
            digest = sha256_file(dest)
            if digest != sums[name]:
                log.error("%s: sha256 mismatch: got %s, expected %s", name, digest, sums[name])
                return False
            log.info("%s: sha256 ok (%s)", name, digest)
        else:
            log.warning("%s not in SHA256SUMS; extracting unverified zip", name)
        return extract_zip(dest, args)
    if dest.exists():
        if name in sums and sha256_file(dest) == sums[name]:
            log.info("%s already matches SHA256SUMS, skipping download", dest)
            return extract_zip(dest, args)
        if not args.force:
            log.error("%s exists but does not match SHA256SUMS; re-run with --force to overwrite", dest)
            return False
        log.warning("overwriting existing %s (--force)", dest)

    if link is None:
        log.error("%s: no Google Drive link in the mapping file and no valid local zip", name)
        return False

    import gdown  # deferred so --check works without gdown installed

    log.info("downloading %s <- %s", name, link)
    got = gdown.download(url=link, output=str(dest), quiet=False)
    if not got or not Path(got).exists():
        log.error("download failed for %s", name)
        return False

    digest = sha256_file(dest)
    if name in sums:
        if digest != sums[name]:
            log.error("%s: sha256 mismatch: got %s, expected %s", name, digest, sums[name])
            return False
        log.info("%s: sha256 ok (%s)", name, digest)
    else:
        log.warning("%s not in SHA256SUMS; downloaded sha256=%s", name, digest)
    return extract_zip(dest, args)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items", nargs="*",
                    help="zip name (ukdale or fnd-ukdale.zip) or NAME=<share link> pair")
    ap.add_argument("--mapping", type=Path, default=DEFAULT_OUT_DIR / "gdrive_ids.txt",
                    help="name-to-link map (default: data/fnd_zips/gdrive_ids.txt)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                    help="where zips land (default: data/fnd_zips)")
    ap.add_argument("--extract-to", type=Path, default=DEFAULT_EXTRACT_TO,
                    help="extraction root; zips contain fnd/<dataset>/ (default: data)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--download-only", "--no-extract", dest="download_only", action="store_true",
                      help="download and sha256-verify the zips, do not unpack")
    mode.add_argument("--extract-only", action="store_true",
                      help="no download: sha256-verify and unpack already-present local zips")
    ap.add_argument("--force", action="store_true",
                    help="re-download and overwrite existing zips/restored dirs")
    ap.add_argument("--check", action="store_true",
                    help="only sha256-verify existing local zips, no download")
    args = ap.parse_args(argv)

    setup_logging()
    sums = load_sums(args.out_dir / "SHA256SUMS")

    if args.check:
        names = [canonical_name(i) for i in args.items] or sorted(sums)
        failures = 0
        for n in names:
            p = args.out_dir / n
            if not p.exists():
                log.error("missing: %s", p)
                failures += 1
                continue
            if n not in sums:
                log.error("%s has no entry in SHA256SUMS", n)
                failures += 1
                continue
            digest = sha256_file(p)
            if digest == sums[n]:
                log.info("%s: sha256 ok (%s)", n, digest)
            else:
                log.error("%s: sha256 MISMATCH: got %s, expected %s", n, digest, sums[n])
                failures += 1
        return 1 if failures else 0

    if args.extract_only:
        if any("=" in i for i in args.items):
            ap.error("--extract-only takes zip names only, not links")
        names = ([canonical_name(i) for i in args.items]
                 or sorted(p.name for p in args.out_dir.glob("fnd-*.zip")))
        targets = [(n, None) for n in names]
    else:
        mapping = load_mapping(args.mapping)
        targets = parse_items(args.items, mapping, args.out_dir) if args.items else sorted(mapping.items())
        if not targets:
            local = sorted(p.name for p in args.out_dir.glob("fnd-*.zip"))
            if local:
                log.info("no links configured; falling back to local zips in %s", args.out_dir)
                targets = [(n, None) for n in local]
    if not targets:
        ap.error("nothing to do: pass zip names/links or fill in the mapping file")

    failures = 0
    for name, link in targets:
        log.info("=== %s ===", name)
        try:
            ok = fetch_one(name, link, sums, args)
        except Exception as exc:  # noqa: BLE001 - report and continue with next zip
            log.error("%s: %s", name, exc)
            ok = False
        if not ok:
            failures += 1
    if failures:
        log.error("%d/%d zip(s) failed", failures, len(targets))
        return 1
    log.info("all %d zip(s) fetched and unpacked", len(targets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
