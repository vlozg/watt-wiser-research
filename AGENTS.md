# AGENTS.md - watt-wiser

NILM baseline research for the WattWiser client: whole-home energy disaggregation
for US homes with Shelly EM Gen3 submeters.

## Layout
- `docs/` - all analysis docs, grouped: `product/` (framing + assessments), `research/`
  (NILM methods + briefs), `knowledge/` (background primers: electricity + NILM feature basics),
  `datasets/` (data strategy + collection), `experiments/`
  (baseline campaign spec), `client/` (repo review + docx extraction; gitignored), `external/`
  (client-provided inputs; gitignored). Reading order: `README.md`.
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
- `figures/` shipped figures + `src/`.
- `repo/` client code as received (read-only); forensics in `deprecated/analysis/repo-forensics/`.
- `data/` - user-staged dataset downloads. Transient staging, gitignored, user-managed:
  never delete or reorganize anything in here without the user naming the exact files.
- `research-logs/` - early-research archive: datasets + notes + fetch scripts,
  including the V-I track (`vi/`, PLAID 30 kHz captures). Heavy dataset dirs are
  gitignored; scripts and notes are tracked.
- `.scratch/` - throwaway scripts only; docs must never reference anything in here.

## Environment
- Python deps tracked with uv (`pyproject.toml` + `uv.lock`). Setup: `uv sync`;
  run scripts with `uv run python3`. Add deps with `uv add`, never by hand-editing `uv.lock`.
- Headless matplotlib: `MPLCONFIGDIR=/tmp/mplcfg`, Agg backend.

## Rules
- No `git commit` unless the user explicitly asks.
- Chat replies: escape `$` as `\$` (LaTeX rendering) and avoid bare `~`.
- Doc paths must be exact and unambiguous; prefer project-relative paths.
- Code homes: one-off/throwaway scripts in `.scratch/`; tracked acquisition/fetch scripts in `research-logs/`; pipeline code in `src/pipelines/`; legacy analysis code in `deprecated/analysis/` (quarantined - do not extend). Never create a new top-level directory without updating this file and `README.md`.
