# AGENTS.md - watt-wiser

NILM baseline research for the WattWiser client: whole-home energy disaggregation
for US homes with Shelly EM Gen3 submeters.

## Layout
- `docs/` - all analysis docs, grouped: `product/` (framing + assessments), `research/`
  (NILM methods + briefs), `knowledge/` (background primers: electricity + NILM feature basics + phases/solar/aircon),
  `datasets/` (data strategy + collection + layer docs), `experiments/`
  (baseline campaign spec), `hypotheses/` (hypothesis registry, one `H<nn>_<slug>.md` per hypothesis
  with status drafted/proved/rejected, index `hypotheses/README.md`, grounded by top-level
  `PROBLEM_STATEMENTS.md` - problem inputs/outputs/calibration/FAQ with trust tags), `reports/`
  (consolidated report set: `phase1-report-draft.md` +
  `dataset_eda/` - 00 overview, per-dataset EDA notebooks (generated from the marimo
  sources in `src/pipelines/02_fnd_eda_notebooks/` - edit the sources, re-export) + PDF
  exports + review/peer-review notes) + `baseline/` (00_baseline experiment renders) +
  `gt_cycle/` (GT-cycle EDA notebook renders, from `src/pipelines/04_eda_annot_gt_cycle/`),
  `client/` (repo review + docx extraction; gitignored), `external/`
  (client-provided inputs; gitignored). Reading order: `README.md`.
- `src/` - pipeline + experiment code: `pipelines/` (00 download, 01 extract,
  02 fnd EDA notebook sources, 03 gold, 04 GT-cycle EDA notebook source), `experiments/00_baseline` (baseline
  scaffold: marimo notebook source + `baseline_lib.py` shared helpers; renders to
  `docs/reports/baseline/` via `make export-baseline` - edit the source, re-export),
  `experiments/01_fhmm` (session-supervised FHMM: `fhmm_lib.py` shared helpers + frozen
  runner `02_run_kcurve.py` + analysis notebook `01_fhmm_session_supervised.py`; renders to
  `docs/reports/fhmm/` via `make export-fhmm` - edit the source, re-export),
  `experiments/02_seq2seq` (target-home seq2seq power model; it trains on the home's own
  submeter, so it is a supervised upper-bound reference, not deployment-parity code),
  `experiments/03_pattern_matching` (pattern-matching detector),
  `experiments/04_autoresearch` (rules + event-mining model, the benchmarked deliverable:
  scored only by the frozen `.auto/measure.sh`, terminal record in `.auto/dossier.md`),
  `experiments/05_method_compare` (cross-method comparison + marimo explorer: rules, rules
  with ground-truth thresholds, FHMM, and a mark-free cross-home seq2seq; holdout readout
  only) and `experiments/06_transfer_dl` (cross-home transfer learning: standalone
  `transfer_lib.py` + backbone pretraining, capacity review in
  `backbone_capacity_review.md`).
  Experiments are isolated from one another: never import across these directories.
- `deprecated/` - quarantined legacy trees the owner has not reviewed; do not extend.
  `deprecated/analysis/`: EDA judge (`eda_shelly.py` CLI + `eda_shelly_interactive.py`
  marimo UI + `eda_reference_ukdale.json`; schema-checked inputs, single implementation -
  edit the CLI, not the UI), `q123_*` scripts,
  baseline campaign drivers (`baseline_ukdale.py`, `device_campaign.py`, `plan_runs.py`),
  NILMTK cross-checks (`xcheck/`), client-repo forensics (`repo-forensics/`).
  `deprecated/baseline_runs/`: baseline campaign outputs (R2-R6, enrollment, experiments, per-house
  trees + top-level `campaign.md`, `summary.md`, `report.md`, `metrics.json`).
  `deprecated/eda_runs/`: saved EDA-battery run outputs (`ukdale_reference/`,
  `synthetic_vs_reference/` - each `report.md` + `metrics.json` + figures; quarantine
  provenance notes in each `report.md`).
  **Deprecated 2026-09-20:** kept as quarantined comparison points
  (upper-bound anchors cited by the hypothesis registry); superseded by the button-press
  calibration simulation (H02 spec) — do not extend.
- `tests/` - pytest suite for the EDA battery in `deprecated/analysis/` (`uv run pytest tests/ -q` or `make test`;
  data-dependent tests skip cleanly when user-staged data is absent).
- `figures/` shipped figures + `src/`.
- `ref/` - client-shared reference notebooks unrelated to NILM (`house-price/`,
  `news-pred/`); pending a keep/drop decision - do not reference from code or docs.
- `repo/` client code as received (read-only); forensics in `deprecated/analysis/repo-forensics/`.
- `data/` - user-staged dataset downloads. Transient staging, gitignored, user-managed:
  never delete or reorganize anything in here without the user naming the exact files.
  Exception: `data/gold_annot/` is git-tracked - the manual-curation store
  (per-dataset hand-marked cycle annotations; layout + schema in
  `data/gold_annot/README.md`, loaded via `baseline_lib.gold_annot_file`).
- `research-logs/` - early-research archive: datasets + notes + fetch scripts,
  including the V-I track (`vi/`, PLAID 30 kHz captures).
  Heavy dataset dirs are gitignored; scripts and notes are tracked.
- `.scratch/` - throwaway scripts only; docs must never reference anything in here.
- `.auto/` - autoresearch loop scaffold (frozen benchmark + task prompt + ideas backlog + run log), plugin-managed; iteration model code in `src/experiments/04_autoresearch/`
- `.agents/` - vendored agent skills for marimo notebooks, from github.com/marimo-team/skills
  (provenance + upstream commit in `.agents/PROVENANCE.md`), in the standard skills-CLI
  layout `.agents/skills/<skill>/SKILL.md`: `marimo-notebook` (authoring),
  `jupyter-to-marimo` (ipynb conversion), `marimo-batch` (headless/batch runs),
  `wasm-compatibility` (browser-runnable sharing). Read the relevant SKILL.md before
  authoring or converting marimo notebooks.

## Environment
- Python deps tracked with uv (`pyproject.toml` + `uv.lock`). Setup: `uv sync`;
  run scripts with `uv run python3`. Add deps with `uv add`, never by hand-editing `uv.lock`.
- Headless matplotlib: `MPLCONFIGDIR=/tmp/mplcfg`, Agg backend.

## Rules
- No `git commit` unless the user explicitly asks.
- Chat replies: escape `$` as `\$` (LaTeX rendering) and avoid bare `~`.
- Doc paths must be exact and unambiguous; prefer project-relative paths.
- Code homes: one-off/throwaway scripts in `.scratch/`; tracked acquisition/fetch scripts in `research-logs/`; pipeline code in `src/pipelines/`; legacy analysis code in `deprecated/analysis/` (quarantined - do not extend). Never create a new top-level directory without updating this file and `README.md`.
