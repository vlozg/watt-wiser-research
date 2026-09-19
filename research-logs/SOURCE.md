# research-logs provenance

The tracked artifacts in this directory are the durable layer of the early
research phase; heavy data files are gitignored and re-downloadable.

- `training-approaches-key.json` / `training-approaches-raw.json`: bibliography
  stores behind `training-approaches.md`. Built by one-off OpenAlex / GitHub
  sweep scripts that lived in `tools/` (`oa_scan*.py`, `oa_sweep.py`,
  `oa_full.py`, `oa_deep.py`, `oa_loc.py`, `oa_pdf.py`, `oa_res.py`,
  `ds_papers.py`, `ds_sent.py`, `gh_raw.py`, `gh_repos.py`, `inspect_key.py`,
  `datasets.py`) plus the docx extractors (`extract2.py`, `media.py`). The
  scripts were one-shot, cwd-dependent chains, removed on 2026-09-19; recoverable
  from git history. The durable provenance is the attributed notes in this
  directory (32 and 17 DOI references respectively) plus these stores.
- `download_uk_dale_2017.sh`: wget/aria2 staging script for the full UK-DALE
  2017 release from the ceda host, moved here from `tools/` on 2026-09-19.
  Usage context: `docs/datasets/data-collection.md`.
