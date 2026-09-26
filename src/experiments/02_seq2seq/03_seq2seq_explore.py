# Explore viewer for the seq2seq (EXP-02) experiment - the companion to the
# frozen batch runner 02_run_kcurve.py in this directory. This notebook is for
# looking at what the model says on a window you choose; it never writes metrics.
#
# Open interactively:
#   uv run marimo edit src/experiments/02_seq2seq/03_seq2seq_explore.py
#
# Knobs: appliance, K (calibration sessions), draw (which K-session draw),
# window start (days after the train/test split), span, probe, and an optional
# full-test scoring pass.
#
# The two figures answer two questions:
#   1. how much does the model claim, against the aggregate it is shown
#   2. does the estimate track the appliance, against the submeter (test period
#      only - the model never sees a submeter)
# The readouts put the selected window's MAE/nMAE in context; predict-zero is
# the nMAE = 1.000 reference.
#
# 02_run_kcurve.py cannot be imported by name (its module name starts with a
# digit), so it is loaded by path with importlib and every constant/helper below
# is the frozen runner's own object, not a copy. The calibration block mirrors
# 02_run_kcurve.run_one for a single (appliance, K, draw) row and is marked
# "mirror:" - keep it in sync with the runner by hand.

import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell(hide_code=True)
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # seq2seq (EXP-02) explore

    One model per appliance. The **aggregate (mains) is the only input**; the
    output is appliance power in watts, so this model emits no ON/OFF state -
    every ON/OFF or above-50 W quantity shown here is a threshold on the
    *submeter*, used for evaluation only.

    Calibration uses **K windows of 128 samples** centred on appliance-ON
    sessions drawn from the train period; training is 5 epochs. Everything
    plotted is held-out test period. The runner in this directory scores the
    whole test period - this notebook scores the window you pick, with the same
    seeds, session draw, scalers and training loop.

    - **Figure 1** - model claims vs submeter measured, both against the aggregate.
    - **Figure 2** - a zoom around the probe, with measured ON windows shaded.

    `K` and `draw` are the runner's own knobs: for a fixed appliance
    the pair `(K, draw)` reproduces exactly the row the batch runner reports.
    """)
    return


@app.cell(hide_code=True)
def _():
    import importlib.util
    from pathlib import Path

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from torch.utils.data import DataLoader

    runner_path = Path(__file__).resolve().parent / "02_run_kcurve.py"
    if not runner_path.exists():
        raise FileNotFoundError(
            f"this notebook reuses the frozen runner next to it, but {runner_path} is missing"
        )
    spec = importlib.util.spec_from_file_location("seq2seq_kcurve", runner_path)
    K = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(K)

    return DataLoader, K, np, plt


@app.cell(hide_code=True)
def _(K):
    # All knobs and thresholds come from the frozen runner, so nothing here can
    # drift from the reported experiment.
    HOUSE = K.HOUSE
    APPLIANCES = list(K.APPLIANCES)
    CAD = float(K.CADENCE_SECONDS)
    WINDOW_SIZE = int(K.WINDOW_SIZE)
    EPOCHS = int(K.EPOCHS)
    K_GRID = list(K.K_GRID)
    N_DRAWS = int(K.N_DRAWS)
    ON_THRESHOLD_W = 50.0  # K.detect_sessions default -> matches the runner

    APP_COLOR = {
        "kettle": "tab:orange",
        "microwave": "tab:green",
        "fridge": "tab:blue",
        "washing_machine": "tab:red",
    }

    SPANS = {"1 h": 3600, "6 h": 21600, "24 h": 86400, "7 d": 604800}
    SLIDER_MIN, SLIDER_MAX = 0, 1290
    ADV_STEPS = {"5 min": 1 / 12, "30 min": 0.5, "1 h": 1.0, "1 d": 24.0}
    ZOOM_H = 1.0
    return (
        ADV_STEPS,
        APPLIANCES,
        APP_COLOR,
        CAD,
        EPOCHS,
        HOUSE,
        K_GRID,
        N_DRAWS,
        ON_THRESHOLD_W,
        SLIDER_MAX,
        SLIDER_MIN,
        SPANS,
        WINDOW_SIZE,
        ZOOM_H,
    )


@app.cell(hide_code=True)
def _(APPLIANCES, K_GRID, N_DRAWS, SLIDER_MAX, SLIDER_MIN, SPANS, mo):
    appliance_dd = mo.ui.dropdown(options=APPLIANCES, value="kettle", label="appliance")
    k_dd = mo.ui.dropdown(options=K_GRID, value=3, label="K calibration sessions")
    draw_dd = mo.ui.dropdown(options=list(range(N_DRAWS)), value=0, label="draw")
    span_dd = mo.ui.dropdown(options=list(SPANS), value="24 h", label="span")
    start_slider = mo.ui.slider(
        start=SLIDER_MIN,
        stop=SLIDER_MAX,
        value=0,
        step=1,
        label="start: days after split",
    )
    # hours of auto-advance accumulated by the play control below
    start_adv, set_start_adv = mo.state(0)
    mo.hstack([appliance_dd, k_dd, draw_dd, span_dd, start_slider])
    return (appliance_dd, draw_dd, k_dd, set_start_adv, span_dd, start_adv, start_slider)


@app.cell(hide_code=True)
def _(ADV_STEPS, mo, set_start_adv, start_adv):
    # play: adds the chosen step to the start offset per tick; this marimo has no
    # native play element, so refresh + state is the documented pattern
    step_dd = mo.ui.dropdown(options=list(ADV_STEPS), value="1 h", label="play step per tick")
    probe_show = mo.ui.checkbox(value=True, label="show probe line")
    play_refresh = mo.ui.refresh(
        options=[0.5, 1, 2, 5],
        default_interval=1,
        label="play (interval in s)",
        on_change=lambda _v: set_start_adv(start_adv() + ADV_STEPS[step_dd.value]),
    )
    mo.hstack([play_refresh, step_dd, probe_show])
    return (probe_show,)


@app.cell(hide_code=True)
def _(APP_COLOR, appliance_dd):
    dev_color = APP_COLOR.get(appliance_dd.value, "tab:blue")
    return (dev_color,)


@app.cell(hide_code=True)
def _(HOUSE, K, appliance_dd):
    # --- Split, then the runner's own session detection over the train period --
    train_df, test_df = K.load_series(HOUSE, appliance_dd.value)
    sessions = K.valid_sessions(K.detect_sessions(train_df), train_df)
    return sessions, test_df, train_df


@app.cell(hide_code=True)
def _(CAD, SLIDER_MAX, SLIDER_MIN, SPANS, span_dd, start_adv, start_slider, test_df):
    # --- Window [t0, t0 + span) in test-period rows, clamped to the series -----
    n = len(test_df)
    span_s = SPANS[span_dd.value]
    span_samples = max(int(round(span_s / CAD)), 1)
    # effective start = manual slider + played hours, wrapped over the slider
    # range so play loops around instead of stalling at the data edge
    off_h = (start_slider.value - SLIDER_MIN) * 24 + start_adv()
    start_days = SLIDER_MIN + (off_h % ((SLIDER_MAX - SLIDER_MIN) * 24)) / 24.0
    t0 = int(round(start_days * 86400 / CAD))
    t0 = max(0, min(t0, n - span_samples))
    win_df = test_df.iloc[t0:t0 + span_samples].reset_index(drop=True)
    return span_s, span_samples, win_df


@app.cell(hide_code=True)
def _(DataLoader, EPOCHS, K, draw_dd, k_dd, np, sessions, train_df):
    # mirror: 02_run_kcurve.run_one, calibration + training. Same seed, same
    # K-session draw (unsorted, as the runner draws it), same scalers fitted on
    # train_df only, same model and 5-epoch loop. Only the prediction target
    # differs: this notebook scores the window you picked.
    seed = K.SEED_BASE + k_dd.value * 100 + draw_dd.value
    K.set_seed(seed)
    rng = np.random.default_rng(seed)

    picked = list(rng.choice(len(sessions), size=min(k_dd.value, len(sessions)), replace=False))
    selected = [sessions[i] for i in picked]

    mains_scaler = K.PowerScaler()
    appliance_scaler = K.PowerScaler()
    mains_scaler.fit(train_df["mains_w"])
    appliance_scaler.fit(train_df["appliance_w"])

    dataset = K.SessionDataset(train_df, selected, mains_scaler, appliance_scaler)
    loader = DataLoader(dataset, batch_size=K.BATCH_SIZE, shuffle=True, num_workers=0)
    model = K.Seq2SeqCNN(channels=64)
    model, _history = K.train_model(model, loader, EPOCHS)
    return appliance_scaler, dataset, mains_scaler, model


@app.cell(hide_code=True)
def _(K, appliance_scaler, mains_scaler, model, win_df):
    # the runner's own tiling (non-overlapping 128-sample windows) over the
    # slice, inverted back to watts
    pred = K.predict_test(model, win_df, mains_scaler, appliance_scaler)
    return (pred,)


@app.cell(hide_code=True)
def _(CAD, ON_THRESHOLD_W, np, pred, win_df):
    x_h = np.arange(len(win_df)) * CAD / 3600.0
    agg = win_df["mains_w"].to_numpy(float)
    measured = win_df["appliance_w"].to_numpy(float)
    on = measured > ON_THRESHOLD_W
    return agg, measured, on, x_h


@app.cell(hide_code=True)
def _(mo, span_s):
    probe_slider = mo.ui.slider(
        start=0,
        stop=max(int(span_s // 3600), 1),
        value=max(int(span_s // 3600) // 2, 0),
        step=1,
        label="probe (h into window)",
    )
    probe_slider  # noqa: B018 - final expression is how marimo renders a widget
    return (probe_slider,)


@app.cell(hide_code=True)
def _(CAD, np, probe_slider, win_df):
    probe_i = int(np.clip(round(probe_slider.value * 3600 / CAD), 0, len(win_df) - 1))
    return (probe_i,)


@app.cell(hide_code=True)
def _(agg, appliance_dd, measured, mo, pred, probe_i, x_h):
    mo.md(f"""
    **probe at +{x_h[probe_i]:.2f} h** - aggregate **{agg[probe_i]:.0f} W**,
    submeter **{measured[probe_i]:.0f} W**, model estimate **{pred[probe_i]:.0f} W**
    (`{appliance_dd.value}`)
    """)
    return


@app.cell(hide_code=True)
def _(agg, dev_color, measured, plt, pred, x_h):
    fig_breakdown, (ax_p, ax_m) = plt.subplots(
        2, 1, figsize=(12.5, 7.2), sharex=True, gridspec_kw={"hspace": 0.10}
    )

    ax_p.plot(x_h, agg, color="0.75", lw=0.7, label="aggregate (model input)")
    ax_p.plot(
        x_h,
        pred,
        color="black",
        lw=1.2,
        drawstyle="steps-post",
        label="model estimate",
    )
    ax_p.axhline(0.0, color="0.85", lw=0.8, zorder=0)
    ax_p.set_ylabel("W")
    ax_p.set_title("model claims", loc="left")
    ax_p.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.9)

    ax_m.plot(x_h, agg, color="0.75", lw=0.7, label="aggregate (model input)")
    ax_m.plot(
        x_h,
        measured,
        color=dev_color,
        lw=1.0,
        drawstyle="steps-post",
        label="submeter measured",
    )
    ax_m.axhline(0.0, color="0.85", lw=0.8, zorder=0)
    ax_m.set_ylabel("W")
    ax_m.set_xlabel("hours into window")
    ax_m.set_title("submeter measured (evaluation only)", loc="left")
    ax_m.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.9)

    fig_breakdown  # noqa: B018 - final expression is how marimo renders a figure
    return (fig_breakdown,)


@app.cell(hide_code=True)
def _(CAD, ON_THRESHOLD_W, ZOOM_H, agg, dev_color, measured, on, plt, pred, probe_i, probe_show, x_h):
    half = int(round(ZOOM_H * 3600 / CAD))
    lo = max(probe_i - half, 0)
    hi = min(probe_i + half, len(x_h))

    fig_zoom, ax_z = plt.subplots(figsize=(12.5, 4.4))
    ax_z.fill_between(
        x_h[lo:hi],
        0,
        1,
        where=on[lo:hi],
        alpha=0.18,
        color=dev_color,
        transform=ax_z.get_xaxis_transform(),
        label=f"submeter ON (above {ON_THRESHOLD_W:g} W, evaluation only)",
    )
    ax_z.plot(x_h[lo:hi], agg[lo:hi], color="0.75", lw=0.8, label="aggregate")
    ax_z.plot(
        x_h[lo:hi],
        pred[lo:hi],
        color="black",
        lw=1.4,
        drawstyle="steps-post",
        label="model estimate",
    )
    ax_z.plot(
        x_h[lo:hi],
        measured[lo:hi],
        color="tab:red",
        lw=1.2,
        ls="--",
        drawstyle="steps-post",
        label="submeter measured",
    )
    ax_z.axhline(0.0, color="0.85", lw=0.8)
    if probe_show.value:
        ax_z.axvline(x_h[probe_i], color="tab:orange", ls="--", lw=1.0)
    ax_z.set_xlim(x_h[lo], x_h[hi - 1])
    ax_z.set_xlabel("hours into window")
    ax_z.set_ylabel("W")
    ax_z.set_title(f"+/-{ZOOM_H:g} h around the probe", loc="left")
    ax_z.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.9)

    fig_zoom  # noqa: B018 - final expression is how marimo renders a figure
    return (fig_zoom,)


@app.cell(hide_code=True)
def _(CAD, K, ON_THRESHOLD_W, WINDOW_SIZE, appliance_dd, dataset, draw_dd, k_dd, measured, mo, np, pred, span_samples):
    win = K.regression_metrics(measured, pred)
    win.update(K.detection_metrics(measured, pred))
    mo.md(f"""
    ### selected window - {appliance_dd.value}, K={k_dd.value}, draw={draw_dd.value}

    {span_samples} samples ({span_samples * CAD / 3600:.2f} h), {len(dataset)} training
    windows of {WINDOW_SIZE} samples

    | metric | value |
    |---|---|
    | MAE | {win['mae_w']:.2f} W |
    | nMAE (MAE / mean measured) | **{win['nmae']:.3f}** |
    | energy error (relative) | {win['energy_error']:.3f} |
    | precision / recall / F1 (above {ON_THRESHOLD_W:g} W) | {win['precision']:.3f} / {win['recall']:.3f} / {win['f1']:.3f} |
    | mean estimate / mean measured | {pred.mean():.2f} W / {measured.mean():.2f} W |
    | share above {ON_THRESHOLD_W:g} W (estimate / measured) | {np.mean(pred > ON_THRESHOLD_W):.4f} / {np.mean(measured > ON_THRESHOLD_W):.4f} |

    A window's nMAE is volatile on short spans, because the denominator is the
    *window's* mean measured power; on a quiet span it can be very large even when
    the absolute error is small. Predicting zero gives nMAE exactly 1.000 on any span.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    full_test_cb = mo.ui.checkbox(value=False, label="score the whole test period with this model (slow)")
    full_test_cb  # noqa: B018 - final expression is how marimo renders a widget
    return (full_test_cb,)


@app.cell(hide_code=True)
def _(K, appliance_scaler, full_test_cb, mains_scaler, mo, model, test_df):
    mo.stop(
        not full_test_cb.value,
        mo.md("_tick the box above to score the whole test period - that is the runner's own metric, the row it reports_"),
    )
    full_pred = K.predict_test(model, test_df, mains_scaler, appliance_scaler)
    return (full_pred,)


@app.cell(hide_code=True)
def _(CAD, K, full_pred, mo, test_df):
    true_full = test_df["appliance_w"].to_numpy(float)
    full = K.regression_metrics(true_full, full_pred)
    full.update(K.detection_metrics(true_full, full_pred))
    mo.md(f"""
    ### whole test period - the runner's own scoring

    {len(true_full)} samples ({len(true_full) * CAD / 3600 / 24:.1f} days) - this is the
    number that appears in the experiment doc's table.

    | metric | value | predict-zero reference |
    |---|---|---|
    | MAE | {full['mae_w']:.2f} W | {true_full.mean():.2f} W |
    | nMAE | **{full['nmae']:.3f}** | 1.000 |
    | energy error (relative) | {full['energy_error']:.3f} | 1.000 |
    | precision / recall / F1 (above 50 W) | {full['precision']:.3f} / {full['recall']:.3f} / {full['f1']:.3f} | 0.000 / 0.000 / 0.000 |
    | mean estimate / mean measured | {full_pred.mean():.2f} W / {true_full.mean():.2f} W | 0.00 W / {true_full.mean():.2f} W |
    | share above 50 W (estimate / measured) | {(full_pred > 50).mean():.4f} / {(true_full > 50).mean():.4f} | 0.0000 / {(true_full > 50).mean():.4f} |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### How to read this

    - **The aggregate is the only input.** A flat estimate is not a bug in the
      plot: with this few training windows the model has almost nothing to
      condition on, so it tends toward one level. The readouts above make that
      quantitative - compare *share above 50 W* for the estimate against the
      submeter.
    - **nMAE is relative to mean measured power**, so it is only comparable across
      appliances at the same split and period, and it inflates as the appliance
      gets quieter. Predict-zero is nMAE 1.000: a value above 1.000 means the
      estimate is worse than claiming the appliance is simply off.
    - **F1 is a threshold on the submeter.** The model has no ON/OFF head, so
      precision/recall/F1 here only measure whether its power crosses 50 W when the
      appliance does.
    - **The estimate is stitched, not continuous.** The runner tiles the test series
      into non-overlapping 128-sample windows (12.8 min), so the estimate can step at
      every seam - the small regular teeth in the figures are that seam, not the
      appliance - and up to 127 trailing samples of the series are never predicted
      (they show as 0).
    - **K and draw are the batch runner's knobs.** Raising K changes only how many
      128-sample training windows are drawn, not the architecture or the number of
      epochs; comparing two K values means comparing very few training windows
      against slightly more.
    """)
    return


if __name__ == "__main__":
    app.run()
