# Watt-wiser research workflows. `make` / `make help` lists targets.
#
# Everything runs through `uv run python3`: deps and the wattwiser helper
# package resolve from the uv-managed venv (uv sync installs the project
# editable, so imports work from any directory).

MPLCONFIGDIR ?= /tmp/mplcfg
export MPLCONFIGDIR

PY ?= uv run python3
FORCE ?=

.PHONY: help setup download download-force raw-manifest extract extract-force labels fnd-check xcheck baseline plan-runs

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## uv sync (install deps + wattwiser editable)
	uv sync

download: ## stage all six datasets from the Drive zips (skips verified trees)
	$(PY) src/pipelines/00_download_dataset/download_all.py

download-force: ## re-download + replace existing trees (old tree kept as .bak_<dataset>)
	$(PY) src/pipelines/00_download_dataset/download_all.py --force

raw-manifest: ## re-snapshot data/raw/ file sizes into raw_manifest.json
	$(PY) src/pipelines/00_download_dataset/make_manifest.py

extract: ## run all six dataset extractors -> data/fnd/ (resumable; FORCE=--force to redo)
	for f in src/pipelines/01_extract_dataset/extract_*.py; do \
		$(PY) $$f $(FORCE) || exit 1; \
	done

labels: ## rebuild data/gold/appliance_map.json + per-dataset slices
	$(PY) src/pipelines/01_extract_dataset/labels.py

fnd-check: ## verify every fnd parquet (rows / sizes vs the fnd manifests)
	$(PY) analysis/xcheck/verify_all.py

xcheck: ## NILMTK cross-checks: others, mains, greend2
	$(PY) analysis/xcheck/xcheck_others.py
	$(PY) analysis/xcheck/xcheck_mains.py
	$(PY) analysis/xcheck/xcheck_greend2.py

baseline: ## R1 baseline campaign on all substrates
	$(PY) analysis/baseline_ukdale.py --dataset all

plan-runs: ## R2-R6 planned runs (plan section 6)
	$(PY) analysis/plan_runs.py --run all
