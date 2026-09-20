# 02_fnd_eda_notebooks — dataset EDA notebook sources

marimo notebook sources (`<NN>_<dataset>_eda.py`) behind the generated report
artifacts in `docs/reports/dataset_eda/`. Each notebook walks one dataset of
the raw-fidelity fnd layer (`data/fnd/`), computes every number it prints, and
ends with a machine-readable summary (rendered as markdown, raw JSON collapsed
in a `<details>` block). Shared helpers live next to the notebooks:
`eda_fnd_lib.py` (the markdown formatters `md_table` / `md_scan_stats` /
`md_summary` feed `mo.md` cells; the `print_*` variants are for terminal use).
All cells carry `hide_code=True`: the marimo editor opens in report view
(toggle code with the editor's hide-code button); the exported `.ipynb` keeps
code and outputs regardless.

## Regenerating the docs artifacts

    uv run marimo export ipynb --include-outputs --sort top-down -f src/pipelines/02_fnd_eda_notebooks/07_synthetic_shelly_eda.py -o docs/reports/dataset_eda/07_synthetic_shelly_eda.ipynb

Exports run the notebook headless against `data/fnd/` (repo root cwd) and
embed the outputs. See `docs/reports/dataset_eda/00_overview.md` for the
report set and its reading order.
