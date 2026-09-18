# watt-wiser

Whole-home electricity monitoring via Shelly EM Gen3 + NILM. Consulting engagement for the
WattWiser project: feasibility assessment, product framing, EDA tooling, and the
client's code + data as received.

## Layout

| Path | What |
|---|---|
| `docs/` | All research + assessment docs (reading order below) |
| `docs/external/` | Client-provided inputs: project brief + calibration deck (.docx) - gitignored |
| `docs/client/` | My analysis of client material: `repo-review.md`, docx extraction (`brief-extract/`) - gitignored, kept out of history |
| `docs/product/` | Product framing: use-case reassessment, core reframe, post-meeting assessment |
| `docs/research/` | NILM research: `research-brief.md`, `nilm-visual-reading.md`, `analog-problems.md`, `vi-trajectory-hardware.md` |
| `docs/datasets/` | Data strategy: `data-collection.md`, `dataset-walkthrough.md`, `experiment-data-strategy.md` |
| `docs/experiments/` | Baseline campaign: `baseline-ukdale-plan.md` (the spec: rungs, metrics, gates, run matrix) |
| `analysis/` | All analysis code: EDA battery + domain-shift judge twins (`eda_shelly.py` CLI / `eda_shelly.ipynb` interactive; edit only the config cell in the notebook), UK-DALE reference metrics (`eda_reference_ukdale.json`), UK-DALE computation scripts (`q123_stats.py`, `q123_stats2.py`, `q123_cites.py`), notebook validator (`nb_validate.py`), client-repo forensics (`repo-forensics/`: `analyze_synthetic.py` (12 checks), `an1`-`an5.py`, `findings.txt`) |
| `figures/` | Shipped figures (`fig01`-`fig09`) + `src/` - the scripts that generate them |
| `eda_runs/` | Saved runs: `ukdale_reference/`, `synthetic_vs_reference/` - each `report.md`, `metrics.json`, 4 figures |
| `repo/WattWiser/` | Client repo as received (github.com/AdibReza/WattWiser, commit `d39f0e0`, 31 files, one commit). Read-only reference; keeps its own `.git`. The 49 MB synthetic dataset is `repo/WattWiser/data/raw/synthetic_shelly_data.csv` |
| `tools/` | Dataset/bibliography acquisition scripts behind the verified DOIs: OpenAlex (`oa_*.py`), GitHub (`gh_*.py`), docx extraction (`extract2.py`, `media.py`), dataset lookups (`datasets.py`, `ds_*.py`) |
| `research-logs/` | Early-research archive (139 MB): UK-DALE slice, PLAID upstream zip + metadata, the V-I track (`vi/`: 16 PLAID 30 kHz captures + `plaid_cd.json` + fetchers + `SOURCE.md`), second NILM dataset clone (`xingyang990210`), Kaggle 1-min data, OA bibliography stores (`training-approaches-key.json`), community-research captures, early notes (`low-frequency-nilm.md`, `training-approaches.md`) + fetcher scripts |
| `data/` | User-staged dataset downloads (UK-DALE full, REFIT, AMPds2, REDD, GREEND) - transient staging, gitignored, intake procedure in `docs/datasets/data-collection.md` |
| `pyproject.toml` + `uv.lock` | uv-tracked Python deps (numpy / pandas / matplotlib / scipy / h5py / py7zr); setup: `uv sync` |
| `AGENTS.md` | Working rules + layout conventions for agents |

## Reading order (docs)

1. `docs/research/research-brief.md` - scope + literature
2. `docs/product/feasibility-verdicts.md` - feasibility verdict chain
3. `docs/datasets/dataset-walkthrough.md` - client data + UK-DALE / PLAID
4. `docs/product/product-core-reframe.md`, `docs/research/analog-problems.md`, `docs/product/use-case-reassessment.md` - the core loop
5. `docs/datasets/experiment-data-strategy.md` - three-tier data plan + EDA usage
6. `docs/datasets/data-collection.md` - what to download, from where, intake procedure (live checklist)
7. `docs/experiments/baseline-ukdale-plan.md` - the baseline experiment spec: inputs, rungs, metrics, gates, run matrix, literature position
8. `docs/research/nilm-visual-reading.md` - visual methods + the figures
9. `docs/research/vi-trajectory-hardware.md` - V-I rig requirements
10. `docs/client/repo-review.md` - code review of `repo/WattWiser/`

## Reproduce

```bash
uv sync                        # one-time: build .venv from uv.lock
export MPLCONFIGDIR=/tmp/mplcfg   # matplotlib Agg

# EDA on real Shelly data, judged against the UK-DALE reference:
uv run python3 analysis/eda_shelly.py shelly_export.csv --reference analysis/eda_reference_ukdale.json --out eda_runs/real_shelly

# Rebuild the reference from the UK-DALE slice:
uv run python3 analysis/eda_shelly.py ukdale --make-reference --out eda_runs/ukdale_reference

# Client-repo forensics:
uv run python3 analysis/repo-forensics/analyze_synthetic.py repo/WattWiser/data/raw/synthetic_shelly_data.csv
```

Interactive EDA: open `analysis/eda_shelly.ipynb`, edit the config cell, run top-to-bottom.
Figures regenerate from `figures/src/fig_a.py` through `fig_g.py`; PLAID captures re-fetch via
`research-logs/vi/plaid_fetch.py`.

## Conventions

- Paths in docs are repo-relative and exact (`docs/...`, `analysis/...`, `research-logs/...`).
- UK-DALE slice used for calibration: `research-logs/sakunrasilka_nilm-test2/` (6 s, 70.7 d, 5 channels + aggregate) - raw capture, re-downloadable from UK-DALE if ever lost.
- `.scratch/` is throwaway-only: project assets belong in this folder.
- `.gitignore` excludes the heavy raw data (`repo/`, everything under `data/`, the large
  `research-logs/` datasets, the extracted PLAID captures). Everything ignored is
  re-downloadable; the small `research-logs/` scripts, notes, and bibliography stores are tracked.
- `repo/WattWiser/` is the client's code as received - do not modify; analysis output goes to
  `analysis/repo-forensics/`.
