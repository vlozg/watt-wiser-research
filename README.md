# watt-wiser

Whole-home electricity monitoring via Shelly EM Gen3 + NILM. Consulting engagement for the
WattWiser project: feasibility assessment, product framing, EDA tooling, and the
client's code + data as received.

## Layout

| Path | What |
|---|---|
| `docs/` | All research + assessment docs (reading order below). Problem grounding: `PROBLEM_STATEMENTS.md`; hypothesis registry: `hypotheses/` |
| `docs/client/` | My analysis of client material: `repo-review.md`, docx extraction (`brief-extract/`) - gitignored, kept out of history |
| `docs/product/` | Product framing: use-case reassessment, core reframe, post-meeting assessment |
| `docs/research/` | NILM research: `research-brief.md`, `nilm-visual-reading.md`, `analog-problems.md`, `vi-trajectory-hardware.md` |
| `docs/knowledge/` | Background primers: `ELI5_NILM.md` (electricity basics), `ELI5_COMMON_NILM_FEATURES.md` (common NILM features, with repo figures) |
| `docs/datasets/` | Data strategy: `data-collection.md`, `dataset-walkthrough.md`, `experiment-data-strategy.md`, `parquet-foundations.md`, `gold-layer.md` |
| `docs/experiments/` | Baseline campaign: `baseline-ukdale-plan.md` (the spec: rungs, metrics, gates, run matrix) |
| `docs/reports/` | Report set: `phase1-report-draft.md` (consolidated phase-1 report draft) + `dataset_eda/` (00 overview, `01`-`07` per-dataset EDA notebooks + PDF exports + review/peer-review notes) + `baseline/` (00_baseline experiment renders) + `gt_cycle/` (GT-cycle EDA notebook renders) |
| `deprecated/` | Quarantined legacy trees the owner has not reviewed - do not extend. `deprecated/analysis/`: EDA battery + domain-shift judge (`eda_shelly.py` CLI with schema-checked inputs + `eda_shelly_interactive.py` marimo UI - single implementation, edit the CLI not the UI), UK-DALE reference metrics (`eda_reference_ukdale.json`), UK-DALE computation scripts (`q123_*.py`), baseline campaign drivers (`baseline_ukdale.py`, `device_campaign.py`, `plan_runs.py`), NILMTK cross-checks (`xcheck/`), client-repo forensics (`repo-forensics/`: `analyze_synthetic.py` (12 checks), `an1`-`an5.py`, `findings.txt`). `deprecated/baseline_runs/`: baseline campaign outputs (R2-R6, enrollment, experiments, per-house): top-level `campaign.md`, `summary.md`, `report.md`, `metrics.json`. `deprecated/eda_runs/`: saved EDA-battery run outputs (`ukdale_reference/`, `synthetic_vs_reference/` - each `report.md`, `metrics.json`, 4 figures; quarantine provenance notes in each `report.md`). **Deprecated 2026-09-20** - kept as quarantined comparison points, superseded by the H02 button-press calibration simulation |
| `tests/` | pytest suite for the EDA battery in `deprecated/analysis/`: schema checks, reference round-trips, CLI end-to-end (`uv run pytest tests/ -q`; data-dependent tests skip when user-staged data is absent) |
| `figures/` | Shipped figures (`fig01`-`fig09`) + `src/` - the scripts that generate them |
| `ref/` | Client-shared reference notebooks, unrelated to NILM (`house-price/`, `news-pred/`) - kept pending a keep/drop decision |
| `repo/WattWiser/` | Client repo as received (github.com/AdibReza/WattWiser, commit `d39f0e0`, 31 files, one commit). Read-only reference; keeps its own `.git`. The 49 MB synthetic dataset is `repo/WattWiser/data/raw/synthetic_shelly_data.csv` |
| `research-logs/` | Early-research archive (139 MB): UK-DALE slice, PLAID upstream zip + metadata, the V-I track (`vi/`: 16 PLAID 30 kHz captures + `plaid_cd.json` + fetchers + `SOURCE.md`), second NILM dataset clone (`xingyang990210`), Kaggle 1-min data, OA bibliography stores (`training-approaches-key.json`), community-research captures, early notes (`low-frequency-nilm.md`, `training-approaches.md`) + fetcher scripts |
| `data/` | User-staged dataset downloads (UK-DALE full, REFIT, AMPds2, REDD, GREEND) - transient staging, gitignored, intake procedure in `docs/datasets/data-collection.md`. Exception: `gold_annot/` is git-tracked - the manual-curation store (`gold_annot/<dataset>/<house>/cycles.csv`, schema + provenance in `data/gold_annot/README.md`) |
| `src/` | `wattwiser/` helper package (labels, manifest, IO) + `pipelines/`: `00_download_dataset` (raw zips -> `data/raw/`), `01_extract_dataset` (-> `data/fnd/` parquet foundations + appliance map), `02_fnd_eda_notebooks` (marimo notebook sources behind `docs/reports/dataset_eda/`), `03_gold_nilm` (-> `data/gold/` NILM tables), `04_eda_annot_gt_cycle` (GT-cycle EDA notebook source, rendered to `docs/reports/gt_cycle/` via `make export-gt-cycle`), `experiments/00_baseline` (baseline scaffold notebook + `baseline_lib.py`, rendered to `docs/reports/baseline/` via `make export-baseline`) |
| `pyproject.toml` + `uv.lock` | uv-tracked Python deps (numpy / pandas / matplotlib / scipy / h5py / py7zr / pytables / pyarrow / pypdf; dev: ruff); setup: `uv sync` |
| `AGENTS.md` | Working rules + layout conventions for agents |
| `.agents/` | Vendored agent skills for marimo notebooks (authoring, ipynb conversion, headless runs, wasm sharing), layout `.agents/skills/<skill>/SKILL.md` - from github.com/marimo-team/skills |

## Reading order (docs)

Optional primers: `docs/knowledge/ELI5_NILM.md` - electricity basics (V, I, W, kWh, AC,
power factor) in plain language, then `docs/knowledge/ELI5_COMMON_NILM_FEATURES.md` -
the features NILM methods compute (delta power, duty cycles, V-I trajectories).

1. `docs/research/research-brief.md` - scope + literature
2. `docs/product/feasibility-verdicts.md` - feasibility verdict chain
3. `docs/PROBLEM_STATEMENTS.md` - the grounded problem statement: inputs, outputs, calibration protocol, evaluation contract, FAQ (every claim trust-tagged: reviewed / client / quarantined / owner)
4. `docs/hypotheses/` - the hypothesis registry (read the `README.md` index first): H01-H13, each with status drafted/proved/rejected
5. `docs/datasets/dataset-walkthrough.md` - client data + UK-DALE / PLAID
6. `docs/reports/dataset_eda/` - per-dataset EDA set (read `00_overview.md` first, then `01`-`07` in any order)
7. `docs/product/product-core-reframe.md`, `docs/research/analog-problems.md`, `docs/product/use-case-reassessment.md` - the core loop
8. `docs/datasets/experiment-data-strategy.md` - three-tier data plan + EDA usage
9. `docs/datasets/data-collection.md` - what to download, from where, intake procedure (live checklist)
10. `docs/datasets/parquet-foundations.md` + `docs/datasets/gold-layer.md` - the parquet foundation and gold layers, with the NILMTK cross-check evidence
11. `docs/experiments/baseline-ukdale-plan.md` - the baseline experiment spec: inputs, rungs, metrics, gates, run matrix, literature position

## Prerequisites

- **git** - this repo; plus the client repo subcheckout under `repo/WattWiser/` (read-only, keeps its own `.git`).
- **[uv](https://docs.astral.sh/uv)** - the only Python requirement. `uv sync` builds `.venv` from `uv.lock` (pins Python >= 3.13); everything runs through `uv run` (`uv run python3`, `uv run pytest`, `uv run marimo`).
- **make** - optional but convenient; `make help` lists the workflow targets (setup, download, extract, gold, fnd-check, lint, test, export-*).
- **No display needed** - plotting is headless Agg; the Makefile exports `MPLCONFIGDIR=/tmp/mplcfg` for you (export it manually when running scripts outside make).
- **Heavy data is not in git** - `data/`, `repo/` and the large `research-logs/` datasets are gitignored and re-downloadable (`make download`; intake in `docs/datasets/data-collection.md`). Docs and code review need none of it; the EDA and gold layers need the six datasets staged and extracted (`make extract`). REFIT alone extracts to ~6.7 GB in scratch - storage budget in `docs/datasets/data-collection.md` section 7.

## Reproduce

```bash
uv sync                        # one-time: build .venv from uv.lock
export MPLCONFIGDIR=/tmp/mplcfg   # matplotlib Agg

# EDA on real Shelly data, judged against the UK-DALE reference:
uv run python3 deprecated/analysis/eda_shelly.py shelly_export.csv --reference deprecated/analysis/eda_reference_ukdale.json --out deprecated/eda_runs/real_shelly

# Rebuild the reference from the UK-DALE slice:
uv run python3 deprecated/analysis/eda_shelly.py ukdale --make-reference --out deprecated/eda_runs/ukdale_reference

# Client-repo forensics:
uv run python3 deprecated/analysis/repo-forensics/analyze_synthetic.py repo/WattWiser/data/raw/synthetic_shelly_data.csv

# Make targets wrap the common runs (see Makefile; `make help` lists all):
make setup          # uv sync - installs deps + the wattwiser helper package (editable)
make download       # stage raw from the public Drive zips (00_download_dataset)
make extract        # all six extractors -> data/fnd/ (resumable)
make labels         # rebuild data/gold/appliance_map.json
make gold           # build gold NILM tables -> data/gold/ (resumable)
make fnd-check      # verify the parquet foundations
make lint           # ruff over all code trees
make check          # aggregate: fnd-check + lint

# Raw data staging from the public Google Drive zips (see src/pipelines/00_download_dataset/README.md):
uv run python3 src/pipelines/00_download_dataset/download.py

# Dataset extraction into parquet foundations (data/fnd/, see docs/datasets/parquet-foundations.md):
uv run python3 src/pipelines/01_extract_dataset/extract_ukdale.py   # likewise extract_redd/refit/eco/greend/ampds2

# Fnd integrity check (per-dataset table: files / rows / out_MB / ts_range):
uv run python3 src/pipelines/01_extract_dataset/qa_fnd.py

# Baseline campaign (spec: docs/experiments/baseline-ukdale-plan.md) - deprecated legacy, do not extend:
uv run python3 deprecated/analysis/baseline_ukdale.py --dataset all
uv run python3 deprecated/analysis/device_campaign.py --build
uv run python3 deprecated/analysis/device_campaign.py --enrollment
uv run python3 deprecated/analysis/device_campaign.py --run-experiments
uv run python3 deprecated/analysis/plan_runs.py --run all
```

Interactive EDA: `uv run marimo edit deprecated/analysis/eda_shelly_interactive.py` - a thin marimo UI over the
same battery (single implementation; no notebook copy to keep in sync). Tests: `uv run pytest tests/ -q`
or `make test`.
Figures regenerate from `figures/src/` - one script per figure, `fig01_resolution_ladder.py` through
`fig09_real_vs_synthetic.py` (shared boot: `_figcommon.py`). PLAID captures re-fetch via
`research-logs/vi/plaid_fetch.py`.

## Conventions

- Paths in docs are repo-relative and exact (`docs/...`, `deprecated/...`, `research-logs/...`).
- UK-DALE slice used for calibration: `research-logs/sakunrasilka_nilm-test2/` (6 s, 70.7 d, 5 channels + aggregate) - raw capture, re-downloadable from UK-DALE if ever lost. Provenance corrected 2026-09-21: the signals are **house-5** channels relabeled house_1-style and channel 1 is a synthetic aggregate - see `docs/datasets/dataset-walkthrough.md` section 8.
- `.scratch/` is throwaway-only: project assets belong in this folder.
- `.gitignore` excludes the heavy raw data (`repo/`, everything under `data/`, the large
  `research-logs/` datasets, the extracted PLAID captures). Everything ignored is
  re-downloadable; the small `research-logs/` scripts, notes, and bibliography stores are tracked.
- `repo/WattWiser/` is the client's code as received - do not modify; forensics output goes to
  `deprecated/analysis/repo-forensics/`.
