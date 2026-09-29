# NOTE: explorer for the method comparison (rules vs FHMM vs seq2seq).
# Companion to 01_run_compare.py (the batch runner, which writes every
# number and prediction this notebook shows); this notebook never writes.
#
# Open interactively:
#   uv run marimo edit src/experiments/05_method_compare/02_compare_explore.py
#
# Two parts:
#   1. Summary over all homes: per-device metric table and bars per method,
#      with the all-zero reference beside every regression metric.
#   2. Home explorer: any of the 27 homes (UK-DALE, REFIT, ECO); aggregate,
#      ground truth and every method's prediction on one time axis, plus
#      daily energy over the whole 90-day evaluation span.

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Method comparison: rules vs FHMM vs seq2seq

    Every method sees only the aggregate at run time and is scored the same
    way on the same homes: 90 days after each home's split, 6 s cadence,
    against the device's own submeters.

    | Method | What it is | What it learns from |
    |---|---|---|
    | **rules** | autoresearch `model.py`, product-safe (scorer thresholds withheld) | the home's 5 simulated presses per device + its unlabeled history |
    | **rules_gt_thr** | the same model as benchmarked, reading the scorer's threshold | the same, plus the submeter-derived device level |
    | **fhmm** | `fhmm_lib` factorial HMM | the same presses (level, spread, dwell per device) |
    | **seq2seq** | dilated 1-D CNN | submeter data of the 20 development homes; no presses |
    | **zero** | predicts 0 W | nothing; the reference line |

    **Development homes** are the 20 homes the autoresearch loop tuned on;
    seq2seq was also trained on their earlier history, so there it is a
    seen-home test. **Unseen homes** are the 7 holdout homes nobody tuned on;
    that is the fair comparison (6 of them have scored devices: ukdale/house_2
    fails bench v4's eligibility rules).

    **Reading the regression metrics.** A kettle is off 99% of the time, so
    predicting 0 W everywhere gets a small MAE. Every metric below is
    either normalized by the device's own energy or shown beside the
    all-zero value, so the zero predictor lands at a fixed, bad score:
    NDE = 1, EA = 0.5, total and daily energy error = 1.
    """)
    return


@app.cell(hide_code=True)
def _():
    import sys
    from pathlib import Path

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import compare_lib as cl

    return cl, np, pd, plt


@app.cell(hide_code=True)
def _(cl, mo):
    mo.stop(not cl.METRICS_CSV.exists(),
            mo.md("**No results yet.** Run `uv run python3 "
                  "src/experiments/05_method_compare/01_run_compare.py` first."))
    raw = cl.load_metrics()
    # median over calibration seeds per (home, device, method), then pairs are
    # the unit every summary averages over
    per_pair = (raw.groupby(["group", "dataset", "tag", "device", "method"],
                            as_index=False).median(numeric_only=True))
    METHOD_ORDER = ["rules", "rules_gt_thr", "fhmm", "seq2seq", "zero"]
    METHOD_STYLE = {
        "rules": {"color": "#1f5fa8", "ls": "-"},
        "rules_gt_thr": {"color": "#6aa6d8", "ls": "--"},
        "fhmm": {"color": "#c0392b", "ls": "-"},
        "seq2seq": {"color": "#2e8b57", "ls": "-"},
        "zero": {"color": "0.55", "ls": ":"},
    }
    METRICS = {
        "f1": ("Cycle F1", "higher is better", False),
        "precision": ("Cycle precision", "higher is better", False),
        "recall": ("Cycle recall", "higher is better", False),
        "daily_energy_err": ("Daily energy error", "lower is better; zero = 1", True),
        "total_energy_err": ("Total energy error (90 d)", "lower is better; zero = 1", True),
        "nde": ("NDE", "lower is better; zero = 1", True),
        "ea": ("Energy accuracy (EA)", "higher is better; zero = 0.5", True),
        "mae_w": ("MAE (W)", "lower is better; compare with zero", True),
        "mae_on_w": ("MAE while ON (W)", "lower is better", True),
    }
    return METHOD_ORDER, METHOD_STYLE, METRICS, per_pair, raw


@app.cell(hide_code=True)
def _(METRICS, mo):
    group_dd = mo.ui.dropdown(
        options={"Unseen homes (7)": "unseen", "Development homes (20)": "dev",
                 "All homes (27)": "all"},
        value="Unseen homes (7)", label="homes")
    metric_dd = mo.ui.dropdown(
        options={v[0]: k for k, v in METRICS.items()},
        value="Cycle F1", label="metric")
    agg_dd = mo.ui.dropdown(options=["median", "mean"], value="median",
                            label="over pairs")
    mo.hstack([group_dd, metric_dd, agg_dd], justify="start", gap=2)
    return agg_dd, group_dd, metric_dd


@app.cell(hide_code=True)
def _(METHOD_ORDER, METRICS, agg_dd, cl, group_dd, metric_dd, mo, per_pair):
    # --- Summary table: median (or mean) over device-home pairs -------------
    # a few runaway pairs (e.g. hundreds of false kettle runs in one home)
    # dominate a mean of ratio metrics; the median is the default for that
    sel = per_pair if group_dd.value == "all" else per_pair[per_pair.group == group_dd.value]
    metric = metric_dd.value
    devs_present = [d for d in cl.DEVICES if d in set(sel.device)]
    tab = (sel.pivot_table(index="method", columns="device", values=metric,
                           aggfunc=agg_dd.value)
              .reindex(index=[m for m in METHOD_ORDER if m in set(sel.method)],
                       columns=devs_present))
    tab["ALL pairs"] = sel.groupby("method")[metric].agg(agg_dd.value)
    npairs = sel.groupby("device")["tag"].nunique()
    label, direction, _ = METRICS[metric]
    mo.vstack([
        mo.md(f"**{label}** ({direction}); {agg_dd.value} over device-home pairs. "
              "Pairs per device: " + ", ".join(f"{d} {int(npairs[d])}" for d in devs_present)),
        tab.round(3),
    ])
    return devs_present, metric, sel


@app.cell(hide_code=True)
def _(METHOD_ORDER, METHOD_STYLE, METRICS, agg_dd, devs_present, metric, np,
      plt, sel):
    # --- Summary bars: one group per device, one bar per method -------------
    _methods = [m for m in METHOD_ORDER if m in set(sel.method)]
    _cols = devs_present + ["ALL"]
    fig_sum, _ax = plt.subplots(figsize=(12.5, 4.2))
    _wbar = 0.8 / len(_methods)
    for _j, _m in enumerate(_methods):
        _sub = sel[sel.method == _m]
        _vals = [_sub[_sub.device == d][metric].agg(agg_dd.value) for d in devs_present]
        _vals.append(_sub[metric].agg(agg_dd.value))
        _x = np.arange(len(_cols)) + (_j - (len(_methods) - 1) / 2) * _wbar
        _ax.bar(_x, _vals, _wbar * 0.95, color=METHOD_STYLE[_m]["color"],
                label=_m, alpha=0.55 if _m == "zero" else 0.95)
    _ax.set_xticks(np.arange(len(_cols)), _cols)
    _ax.set_ylabel(METRICS[metric][0] + f" ({agg_dd.value} over pairs)")
    _ax.set_title(METRICS[metric][1], fontsize=10)
    if metric in ("daily_energy_err", "total_energy_err", "nde"):
        _ax.axhline(1.0, color="0.4", ls=":", lw=1)
        _ax.set_ylim(0, min(3.0, _ax.get_ylim()[1]))
    _ax.grid(axis="y", alpha=0.25)
    _ax.legend(fontsize=8, ncol=len(_methods), loc="upper right")
    fig_sum
    return


@app.cell(hide_code=True)
def _(METHOD_ORDER, METHOD_STYLE, plt, sel):
    # --- Per pair: does finding the cycles buy the energy? ------------------
    fig_sc, _ax = plt.subplots(figsize=(7.5, 4.6))
    for _m in METHOD_ORDER:
        if _m == "zero" or _m not in set(sel.method):
            continue
        _s = sel[sel.method == _m]
        _ax.scatter(_s["f1"], _s["daily_energy_err"].clip(upper=3.0), s=22,
                    color=METHOD_STYLE[_m]["color"], alpha=0.75, label=_m)
    _ax.axhline(1.0, color="0.4", ls=":", lw=1, label="zero predictor")
    _ax.set_xlabel("cycle F1 (per device-home pair)")
    _ax.set_ylabel("daily energy error (clipped at 3)")
    _ax.set_title("each dot = one device in one home", fontsize=10)
    _ax.grid(alpha=0.25)
    _ax.legend(fontsize=8)
    fig_sc
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Home explorer

    Pick a home, the methods to overlay and a window. The top panel is the
    whole-home view: the aggregate (grey), the sum of the submetered target
    devices (black dashed) and each method's total claim. One panel per
    device below it: ground truth filled grey, each method as a line, the
    scorer's ON threshold dotted. Windows longer than 12 h are drawn with
    the maximum per bin so short kettle runs stay visible. (The enrollment
    presses sit in each home's pre-split history, so they never appear in
    these evaluation windows.)
    """)
    return


@app.cell(hide_code=True)
def _(METHOD_ORDER, cl, mo, per_pair):
    # only homes with at least one scored device (ukdale/house_2 has none
    # under bench v4's eligibility rules); unseen homes first
    _scored = set(per_pair.tag)
    _homes = [h for h in cl.home_list() if h["tag"] in _scored]
    _n = per_pair.groupby("tag").device.nunique()
    # unseen homes first, the ones with the most scored devices on top
    _homes = sorted(_homes, key=lambda h: (h["group"] != "unseen", -_n[h["tag"]], h["tag"]))
    _opts = {f"{h['tag']}  ({h['group']}, {_n[h['tag']]} devices)": h["tag"]
             for h in _homes}
    home_dd = mo.ui.dropdown(options=_opts, value=next(iter(_opts)), label="home")
    methods_ms = mo.ui.multiselect(
        options=[m for m in METHOD_ORDER if m != "zero"],
        value=["rules", "fhmm", "seq2seq"], label="methods")
    SPANS = {"1 h": 1, "3 h": 3, "6 h": 6, "12 h": 12, "24 h": 24,
             "3 d": 72, "7 d": 168, "30 d": 720, "90 d": 2160}
    span_dd = mo.ui.dropdown(options=list(SPANS), value="24 h", label="span")
    start_sl = mo.ui.slider(start=0, stop=89.5, step=0.25, value=10,
                            label="start: days after split")
    mo.hstack([home_dd, methods_ms, span_dd, start_sl], justify="start", gap=2)
    return SPANS, home_dd, methods_ms, span_dd, start_sl


@app.cell(hide_code=True)
def _(cl, home_dd, mo):
    mo.stop(not cl.pred_file(home_dd.value).exists(),
            mo.md(f"No prediction file for {home_dd.value}; re-run the runner."))
    P = cl.load_preds(home_dd.value)
    home_devs = [str(d) for d in P["devices"]]
    home_thr = dict(zip(home_devs, [float(t) for t in P["thr"]]))
    dev_ms = mo.ui.multiselect(options=home_devs, value=home_devs, label="devices")
    dev_ms
    return P, dev_ms, home_devs, home_thr


@app.cell(hide_code=True)
def _(P, SPANS, np, span_dd, start_sl):
    # --- Window over the eval span -----------------------------------------
    ts_all = P["ts_us"]
    t0_us = int(ts_all[0] + start_sl.value * 86_400e6)
    t1_us = int(t0_us + SPANS[span_dd.value] * 3600e6)
    i0 = int(np.searchsorted(ts_all, t0_us))
    i1 = int(np.searchsorted(ts_all, t1_us))
    n_win = i1 - i0
    # bin to at most 3000 points; max per bin keeps short spikes visible
    nb = int(np.ceil(n_win / 3000)) if n_win > 3000 else 1

    def win(a):
        x = np.asarray(a[i0:i1], np.float32)
        if nb == 1:
            return x
        m = (len(x) // nb) * nb
        return np.nanmax(x[:m].reshape(-1, nb), axis=1)

    x_h = (ts_all[i0:i1][::nb][: (n_win // nb if nb > 1 else n_win)] - t0_us) / 3.6e9
    return i0, i1, nb, t0_us, t1_us, win, x_h


@app.cell(hide_code=True)
def _(METHOD_STYLE, P, dev_ms, home_dd, home_thr, methods_ms, mo, nb, np, plt,
      win, x_h):
    # --- Figure 1: aggregate view + one panel per device -------------------
    _devs = list(dev_ms.value)
    mo.stop(not _devs, mo.md("Select at least one device."))
    _meths = [m for m in methods_ms.value if any(f"pred_{m}_{d}" in P for d in _devs)]
    fig_home, _axes = plt.subplots(
        len(_devs) + 1, 1, figsize=(13, 2.3 * (len(_devs) + 1) + 0.6),
        sharex=True, gridspec_kw={"hspace": 0.12})
    _axes = np.atleast_1d(_axes)
    _a0 = _axes[0]
    _a0.plot(x_h, win(P["mains"]), color="0.65", lw=0.8, label="aggregate")
    _gt_sum = sum(np.asarray(P["gt_" + d], np.float32) for d in _devs)
    _a0.plot(x_h, win(_gt_sum), color="0.1", lw=1.0, ls="--",
             label="target devices, measured")
    for _m in _meths:
        _s = sum(np.asarray(P[f"pred_{_m}_{d}"], np.float32) for d in _devs
                 if f"pred_{_m}_{d}" in P)
        _a0.plot(x_h, win(_s), color=METHOD_STYLE[_m]["color"],
                 ls=METHOD_STYLE[_m]["ls"], lw=1.1, label=f"{_m}, claimed")
    _a0.set_ylabel("W")
    _a0.set_title(f"{home_dd.value}: whole home"
                  + ("" if nb == 1 else f"  (max per {nb * 6} s bin)"), fontsize=10)
    _a0.legend(fontsize=8, ncol=4, loc="upper right")
    for _ax, _d in zip(_axes[1:], _devs):
        _g = win(P["gt_" + _d])
        _ax.fill_between(x_h, 0, _g, step="post", color="0.75", lw=0,
                         label="measured")
        for _m in _meths:
            _k = f"pred_{_m}_{_d}"
            if _k in P:
                _ax.plot(x_h, win(P[_k]), drawstyle="steps-post",
                         color=METHOD_STYLE[_m]["color"],
                         ls=METHOD_STYLE[_m]["ls"], lw=1.2, label=_m)
        _ax.axhline(home_thr[_d], color="0.3", ls=":", lw=0.9, label="ON threshold")
        _ax.set_ylabel(f"{_d}\nW", fontsize=9)
        _ax.grid(alpha=0.2)
        _ax.legend(fontsize=7, ncol=6, loc="upper right")
    _axes[-1].set_xlabel("hours into window")
    fig_home
    return


@app.cell(hide_code=True)
def _(METHOD_STYLE, P, dev_ms, methods_ms, mo, np, plt):
    # --- Figure 2: daily energy over the whole eval span, all at once -------
    _devs = list(dev_ms.value)
    mo.stop(not _devs)
    _ts = P["ts_us"]
    _day = (_ts - _ts[0]) // 86_400_000_000
    _h = 6.0 / 3600.0 / 1000.0  # W per 6 s sample -> kWh
    fig_daily, _axes = plt.subplots(len(_devs), 1, figsize=(13, 2.0 * len(_devs) + 0.6),
                                    sharex=True, gridspec_kw={"hspace": 0.15})
    _axes = np.atleast_1d(_axes)
    for _ax, _d in zip(_axes, _devs):
        _g = np.bincount(_day, weights=np.asarray(P["gt_" + _d], np.float64)) * _h
        _ax.bar(np.arange(len(_g)), _g, color="0.75", width=0.9, label="measured")
        for _m in methods_ms.value:
            _k = f"pred_{_m}_{_d}"
            if _k in P:
                _p = np.bincount(_day, weights=np.maximum(np.asarray(P[_k], np.float64), 0)) * _h
                _ax.plot(np.arange(len(_p)), _p, color=METHOD_STYLE[_m]["color"],
                         ls=METHOD_STYLE[_m]["ls"], lw=1.2, marker=".", ms=3, label=_m)
        _ax.set_ylabel(f"{_d}\nkWh/day", fontsize=9)
        _ax.grid(alpha=0.2)
        _ax.legend(fontsize=7, ncol=5, loc="upper right")
    _axes[-1].set_xlabel("day after split")
    fig_daily
    return


@app.cell(hide_code=True)
def _(home_dd, per_pair):
    # --- This home's numbers (median over seeds) ----------------------------
    _cols = ["device", "method", "f1", "precision", "recall", "n_pred", "n_gt",
             "daily_energy_err", "total_energy_err", "nde", "ea", "mae_w",
             "mae_zero_w", "energy_true_kwh", "energy_pred_kwh"]
    home_tab = (per_pair[per_pair.tag == home_dd.value][_cols]
                .sort_values(["device", "method"]).round(3))
    home_tab
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Notes.**
    - F1 is bench v4's cycle scorer: a predicted run matches a true run when
      its start is within the device's tolerance (1 min kettle/microwave,
      2 min fridge, 10 min washer/dishwasher) and its duration is within
      a third to three times the true duration.
    - Energy errors are |predicted - measured| energy over the whole span
      (total) or averaged per UTC day (daily), divided by the measured
      energy. The daily one is what a usage screen would show.
    - The rules model emits a fitted level per device, not a measured one,
      so its watts are coarse even when its timing is right. FHMM claims its
      calibrated mean level. seq2seq regresses watts directly.
    - fhmm's fridge level comes from upward steps in the passive 3 h window
      (the original `fhmm_lib` fridge profile reads GT duty intervals).
    """)
    return


if __name__ == "__main__":
    app.run()
