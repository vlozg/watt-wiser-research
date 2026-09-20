# Watt-wiser research workflows. `make` / `make help` lists targets.
#
# Everything runs through `uv run python3`: deps and the wattwiser helper
# package resolve from the uv-managed venv (uv sync installs the project
# editable, so imports work from any directory).

MPLCONFIGDIR ?= /tmp/mplcfg
export MPLCONFIGDIR

PY ?= uv run python3
FORCE ?=

.PHONY: help setup download download-force raw-manifest extract extract-force labels gold gold-force fnd-check xcheck baseline plan-runs export-eda export-baseline export-gt-cycle eda-pdfs lint check

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## uv sync (install deps + wattwiser editable)
	uv sync

download: ## stage all six datasets from the Drive zips (skips verified trees)
	$(PY) src/pipelines/00_download_dataset/download.py

download-force: ## re-download + replace existing trees (old tree kept as .bak_<dataset>)
	$(PY) src/pipelines/00_download_dataset/download.py --force

raw-manifest: ## re-snapshot data/raw/ file sizes into raw_manifest.json
	$(PY) src/pipelines/00_download_dataset/make_manifest.py

extract: ## run all six dataset extractors -> data/fnd/ (resumable; FORCE=--force to redo)
	for f in src/pipelines/01_extract_dataset/extract_*.py; do \
		$(PY) $$f $(FORCE) || exit 1; \
	done

labels: ## rebuild data/gold/appliance_map.json + per-dataset slices
	$(PY) src/pipelines/01_extract_dataset/labels.py

gold: ## build gold NILM tables -> data/gold/<ds>/<building>/ (resumable; FORCE=--force to redo)
	$(PY) src/pipelines/03_gold_nilm/gold_all.py $(FORCE)

gold-force: ## rebuild every gold table from fnd
	$(PY) src/pipelines/03_gold_nilm/gold_all.py --force

fnd-check: ## verify every fnd parquet (rows / sizes vs the fnd manifests)
	$(PY) src/pipelines/01_extract_dataset/qa_fnd.py

xcheck: ## NILMTK cross-checks: others, mains, greend2
	$(PY) deprecated/analysis/xcheck/xcheck_others.py
	$(PY) deprecated/analysis/xcheck/xcheck_mains.py
	$(PY) deprecated/analysis/xcheck/xcheck_greend2.py

baseline: ## R1 baseline campaign on all substrates (quarantined legacy; do not extend)
	$(PY) deprecated/analysis/baseline_ukdale.py --dataset all

plan-runs: ## R2-R6 planned runs (plan section 6; quarantined legacy; do not extend)
	$(PY) deprecated/analysis/plan_runs.py --run all

EDA_NOTEBOOKS := 01_ukdale_eda 02_refit_eda 02b_refit_eda_localtime 03_redd_eda 04_eco_eda 05_greend_eda 06_ampds2_eda

export-eda: ## export dataset EDA notebooks: all 7, or one via NOTEBOOK=01_ukdale_eda
	nb="$(NOTEBOOK)"; \
	if [ -n "$$nb" ]; then list="$$nb"; else list="$(EDA_NOTEBOOKS)"; fi; \
	for n in $$list; do \
		[ -f src/pipelines/02_fnd_eda_notebooks/$$n.py ] || { echo "unknown notebook $$n"; exit 1; }; \
		echo "=== exporting $$n ($$(date +%H:%M:%S))"; \
		(cd /tmp && UV_CACHE_DIR=/tmp/uv-cache XDG_CONFIG_HOME=/tmp/xdg-config \
			uv run --project $(CURDIR) marimo export ipynb --include-outputs \
			-f $(CURDIR)/src/pipelines/02_fnd_eda_notebooks/$$n.py \
			-o $(CURDIR)/docs/reports/dataset_eda/$$n.ipynb) \
		|| { echo "FAIL $$n"; exit 1; }; \
		echo "=== done $$n ($$(date +%H:%M:%S))"; \
	done

eda-pdfs: ## export dataset EDA PDFs: all 6, or some via NOTEBOOK="02_refit_eda 06_ampds2_eda"
	(cd /tmp && UV_CACHE_DIR=/tmp/uv-cache XDG_CONFIG_HOME=/tmp/xdg-config \
		uv run --project $(CURDIR) python3 $(CURDIR)/src/pipelines/02_fnd_eda_notebooks/export_pdfs.py $(NOTEBOOK)) \
	|| { echo "FAIL eda-pdfs"; exit 1; }

BASELINE_NOTEBOOKS := 01_ukdale_baseline

export-baseline: ## export baseline experiment notebooks: all, or one via NOTEBOOK=01_ukdale_baseline
	nb="$(NOTEBOOK)"; \
	if [ -n "$$nb" ]; then list="$$nb"; else list="$(BASELINE_NOTEBOOKS)"; fi; \
	for n in $$list; do \
		[ -f src/experiments/00_baseline/$$n.py ] || { echo "unknown notebook $$n"; exit 1; }; \
		echo "=== exporting $$n ($$(date +%H:%M:%S))"; \
		(cd /tmp && UV_CACHE_DIR=/tmp/uv-cache XDG_CONFIG_HOME=/tmp/xdg-config \
			uv run --project $(CURDIR) marimo export ipynb --include-outputs \
			-f $(CURDIR)/src/experiments/00_baseline/$$n.py \
			-o $(CURDIR)/docs/reports/baseline/$$n.ipynb) \
		|| { echo "FAIL $$n"; exit 1; }; \
		echo "=== done $$n ($$(date +%H:%M:%S))"; \
	done

GT_CYCLE_NOTEBOOKS := 01_ukdale_gt_cycle_eda 02_synthetic_shelly_cycle_eda

export-gt-cycle: ## export GT-cycle EDA notebooks: all, or one via NOTEBOOK=01_ukdale_gt_cycle_eda
	nb="$(NOTEBOOK)"; \
	if [ -n "$$nb" ]; then list="$$nb"; else list="$(GT_CYCLE_NOTEBOOKS)"; fi; \
	for n in $$list; do \
		[ -f src/pipelines/04_eda_annot_gt_cycle/$$n.py ] || { echo "unknown notebook $$n"; exit 1; }; \
		echo "=== exporting $$n ($$(date +%H:%M:%S))"; \
		(cd /tmp && UV_CACHE_DIR=/tmp/uv-cache XDG_CONFIG_HOME=/tmp/xdg-config \
			uv run --project $(CURDIR) marimo export ipynb --include-outputs \
			-f $(CURDIR)/src/pipelines/04_eda_annot_gt_cycle/$$n.py \
			-o $(CURDIR)/docs/reports/gt_cycle/$$n.ipynb) \
		|| { echo "FAIL $$n"; exit 1; }; \
		echo "=== done $$n ($$(date +%H:%M:%S))"; \
	done

test: ## pytest suite for the analysis battery (data-dependent tests skip when inputs are absent)
	uv run pytest tests/ -q

lint: ## ruff over all code trees (config in pyproject.toml)
	uv run ruff check deprecated/analysis src figures/src figures

check: fnd-check lint ## aggregate: fnd verification, then lint
