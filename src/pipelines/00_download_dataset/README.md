# 00_download_dataset

Reproduces the raw data layer from six public Google Drive zips (uploaded by the user).
Each zip contains one dataset directory; the script downloads it, extracts, normalizes
the layout to `data/raw/<dataset>/`, and verifies the tree against `raw_manifest.json`
(file names + byte sizes captured from the originally staged copies).

| Dataset | Staged at | Size (manifest) | Files | Drive link |
|---|---|---|---|---|
| UK-DALE full | `data/raw/ukdale-full/` | 23.3 GB | 212 | https://drive.google.com/file/d/18gaDLfUJ5YdrkSMUqG_FbVhiBfUTjVHo/view?usp=drive_link |
| REFIT | `data/raw/REFIT/` | 979.4 MB | 5 | https://drive.google.com/file/d/1wQTWXumWQoeavS58gmorDYTWV4OPlayi/view?usp=drive_link |
| ECO | `data/raw/ECO/` | 3.8 GB | 36 | https://drive.google.com/file/d/1GA_lPkp1mxPioV_bKlQHjv_uUdkooJQQ/view?usp=drive_link |
| GREEND | `data/raw/GREEND_0-2_300615/` | 15.9 GB | 4787 | https://drive.google.com/file/d/1DB8Hmqg3-MWH6y4K3SxjgKS3dUqjF6uU/view?usp=drive_link |
| REDD | `data/raw/redd/` | 382.7 MB | 1 | https://drive.google.com/file/d/1N33acJ_MG2JyCz4sm-g98e-nZ9jEtokK/view?usp=drive_link |
| AMPds2 | `data/raw/AMPds2/` | 2.1 GB | 89 | https://drive.google.com/file/d/1j8jNWANQqVM0uG7-6-TgFzDEsw8OivBZ/view?usp=drive_link |

## Usage

```bash
make download                                                    # all six (skips verified)
uv run python3 src/pipelines/00_download_dataset/download.py redd        # one dataset
uv run python3 src/pipelines/00_download_dataset/download.py redd --force  # re-download, replaces the tree
```

`--force` moves an existing tree to `data/raw/.bak_<dataset>/` before staging the new
copy; the `.staging_<dataset>/` work dir is cleaned up automatically.

## Verification

- After extraction, every file name and byte size is checked against
  `raw_manifest.json` (`_meta` records when it was generated and per-dataset totals).
- If the zip is stale or a file differs, the run fails with a diff list rather than
  staging a wrong tree.
- Probe record: the redd zip's `redd/redd.h5` (401,317,829 B) is sha256-identical to
  the originally staged copy (`757e694a4201...`), confirming the zips are faithful
  copies of the raw layout.

## If a download fails

The original hosts are listed in `docs/datasets/data-collection.md (original-host list in section 3)`. Download the files there,
reproduce the layout under `data/raw/<dir>/`, then `uv run python3
src/pipelines/00_download_dataset/make_manifest.py` if the content changed.

## Manifest regeneration

```bash
uv run python3 src/pipelines/00_download_dataset/make_manifest.py   # re-snapshot data/raw/
```

Downstream: `src/pipelines/01_extract_dataset/` consumes `data/raw/` and writes
`data/fnd/`; label extraction writes `data/gold/`.