"""Interactive judge -- thin marimo UI over the analysis/eda_shelly.py battery.

The battery exists ONCE, in eda_shelly.py (the CLI); this notebook imports it and
adds parameterized inputs for interactive / client sessions. To change any metric,
edit the CLI, not this file. Schema warnings surface as a callout and are recorded
into the generated report exactly as the CLI does.

Run interactively:  uv run marimo edit analysis/eda_shelly_interactive.py
Run headless:       uv run python3 analysis/eda_shelly_interactive.py
"""
import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell(hide_code=True)
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import json
    import os

    import eda_shelly
    return eda_shelly, json, os


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        # eda_shelly -- interactive judge

        Thin UI over the `analysis/eda_shelly.py` battery (single implementation).
        Pick an input, an optional reference JSON, and an output dir; every metric,
        verdict and figure below is recomputed from these settings.
        """
    )
    return


@app.cell
def _(mo):
    inp = mo.ui.text(value="ukdale", label="INPUT ('ukdale' or CSV path)", full_width=True)
    outdir = mo.ui.text(value="/tmp/eda_interactive", label="OUTDIR")
    ref = mo.ui.text(value="", label="REFERENCE json (blank = no comparison)", full_width=True)
    make_ref = mo.ui.checkbox(value=False, label="MAKE_REFERENCE (also write reference_metrics.json)")
    mo.vstack([inp, outdir, ref, make_ref])
    return inp, make_ref, outdir, ref


@app.cell
def _(eda_shelly, inp, json, make_ref, os, outdir, ref):
    os.makedirs(outdir.value, exist_ok=True)
    if inp.value == "ukdale":
        df, apps, schema = eda_shelly.load_ukdale()
    else:
        df, apps, schema = eda_shelly.load_csv(inp.value)
    m = eda_shelly.compute_metrics(df, apps)
    m["schema"] = schema
    cmp_rows = eda_shelly.compare(m, json.load(open(ref.value))) if ref.value.strip() else None
    eda_shelly.make_figures(df, apps, outdir.value)
    eda_shelly.write_report(m, cmp_rows, outdir.value, inp.value, ref.value.strip() or None)
    if make_ref.value:
        json.dump(m, open(os.path.join(outdir.value, "reference_metrics.json"), "w"), indent=1)
    s = m["sampling"]
    headline = "rows=%d  span=%.2fd  dt=%.1fs  steps30/day=%.1f" % (
        s["rows"], s["span_days"], s["dt_median_s"], m["steps"]["steps_per_day_gt30W"],
    )
    return cmp_rows, headline, outdir, schema


@app.cell
def _(headline, mo):
    mo.md("`%s`" % headline)
    return


@app.cell
def _(mo, schema):
    if schema is not None and schema["warnings"]:
        _schema_out = mo.callout(
            mo.md("\n".join("- **WARN:** %s" % w for w in schema["warnings"])), kind="warn"
        )
    elif schema is not None:
        _schema_out = mo.callout(mo.md("Schema check: no warnings."), kind="nice")
    else:
        _schema_out = mo.md("*(ukdale slice: schema gate not applicable)*")
    _schema_out  # noqa: B018 -- bare name is marimo's cell-display idiom
    return


@app.cell
def _(cmp_rows, mo):
    if cmp_rows is None:
        _verdict_out = mo.md("*No reference configured -- set REFERENCE to see domain-shift verdicts.*")
    else:
        n_flag = sum(1 for r in cmp_rows if r["verdict"] == "FLAG")
        _verdict_out = mo.vstack([
            mo.md("**Domain shift: %d of %d metrics FLAG.**" % (n_flag, len(cmp_rows))),
            mo.ui.table(cmp_rows, label="verdicts vs reference"),
        ])
    _verdict_out  # noqa: B018 -- bare name is marimo's cell-display idiom
    return


@app.cell
def _(mo, os, outdir):
    figs = ["eda_fig01_ladder.png", "eda_fig02_week.png", "eda_fig03_day.png", "eda_fig04_events.png"]
    mo.vstack([mo.image(src=os.path.join(outdir.value, f), width=880) for f in figs])
    return


if __name__ == "__main__":
    app.run()
