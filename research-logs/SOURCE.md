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
- `eda_datasets.ipynb` / `eda_datasets_summary.json`: executed staged-datasets EDA
  sweep (2026-09-19) over the then-staged raw data, ending in the dataset-pool
  inventory used by `docs/experiments/baseline-ukdale-plan.md`. Moved here from
  `analysis/` on 2026-09-20, then removed 2026-09-20: the six fnd-layer dataset
  sections were superseded by `docs/reports/dataset_eda/` (which also covers the
  Kaggle 1-min synthetic replay fixture via `07_synthetic_shelly_eda`), and the
  inventory JSON was stale (predates `data/fnd/`; ECO missing). The first-pass
  PLAID vi section went with it; the 30 kHz captures and fetchers remain under
  `vi/` (provenance in `vi/SOURCE.md`).
- Tracked scripts (this directory): the surviving one-shot fetch/inspection
  scripts of the early phase - literature sweeps (`openalex.py`, `oa_abstracts.py`,
  `oa_anomaly.py`, `s2_abstracts.py`, `arxiv.py`, `arxiv_probe.py`,
  `ping_arxiv.py`, `bing.py`, `anomaly_lit.py`-`anomaly_lit3.py`, `lit2.py` /
  `lit3.py`, `ha_topic.py`), UK-DALE inspection runs (`inspect_ukdale.py`,
  `ukdale_demo.py`-`ukdale_demo3.py`, `check1min.py`), and extraction helpers
  (`extract_docx.py`, `dump_media.py`). Separate one-shot chains, not recoveries
  of the removed `tools/` scripts above - none touch the bibliography stores.
