# AGENTS.md - watt-wiser

NILM baseline research for the WattWiser client: whole-home energy disaggregation
for US homes with Shelly EM Gen3 submeters.

## Layout
- `docs/` - all analysis docs, grouped: `product/` (framing + assessments), `research/`
  (NILM methods + briefs), `datasets/` (data strategy + collection), `experiments/`
  (baseline campaign spec), `client/` (repo review + docx extraction; gitignored), `external/`
  (client-provided inputs; gitignored). Reading order: `README.md`.
- `analysis/` - all analysis code: EDA twins (`eda_shelly.py` / `.ipynb` +
  `eda_reference_ukdale.json`), `q123_*` scripts, `nb_validate.py`, client-repo
  forensics (`repo-forensics/`).
- `figures/` shipped figures + `src/`; `eda_runs/` saved run outputs.
- `repo/` client code as received (read-only); forensics in `analysis/repo-forensics/`.
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
- Code homes: one-off/throwaway scripts in `.scratch/`; tracked acquisition/fetch scripts in `research-logs/`; pipeline code in `src/pipelines/`; analysis code in `analysis/`. Never create a new top-level directory without updating this file and `README.md`.
