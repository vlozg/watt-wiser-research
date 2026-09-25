# NOTE: exploratory decode viewer for the session-supervised FHMM. Companion
# to 02_run_kcurve.py (the frozen batch runner) - this notebook is for looking
# at what the model says on a window you choose; it never writes metrics.
#
# Open interactively:
#   uv run marimo edit src/experiments/01_fhmm/03_fhmm_explore.py
#
# Knobs: house, K (button-press sessions per device), window start (days
# after the train/test split), span. Two figures answer the questions:
#   1. which device is running at any moment -> probe line + ON readout
#   2. how much -> two panels: claims and submeter measurements vs aggregate
#   3. span view -> aggregate (grey), estimated load (black), ON windows shaded
#
# Calibration mirrors 02_run_kcurve.build_param_rows for one (K, draw) row at
# the native 6 s cadence; the runner is not importable (its module name
# starts with a digit), so the mirrored lines are marked "mirror:" and must
# be kept in sync by hand.

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
    # FHMM decode explorer

    Every knob change re-runs: calibrate (K valid press sessions per device,
    one seeded draw) -> decode the window at the native 6 s cadence -> draw.
    Press play to sweep the window: the start advances one chosen step per
    tick (step and interval selectable) and loops over the slider range.
    Three questions, two figures:

    1. **Which device is running at any moment?** - drag the probe line; the
       readout lists what is ON, and in the breakdown view a device claims
       only while its step line is off zero.
    2. **How much?** - breakdown view, two panels: top = per-device claimed
       W vs the aggregate; bottom = submeter-measured W vs the aggregate.
    3. **Span view** - aggregate (grey), estimated load (black), measured
       load (dashed), ON windows shaded per device.
    """)
    return


@app.cell(hide_code=True)
def _():
    # Headless-safe matplotlib + fhmm_lib (same directory).
    import matplotlib

    matplotlib.use("Agg")
    import fhmm_lib as fl
    import matplotlib.pyplot as plt
    import numpy as np

    from wattwiser.experiments.data_loader import gold_parquet_path, load_power_series

    return fl, gold_parquet_path, load_power_series, matplotlib, np, plt


@app.cell(hide_code=True)
def _(fl):
    # Constants mirrored from 02_run_kcurve.py (not importable: module name
    # starts with a digit). Keep in sync by hand. mirror:.
    DATASET = "ukdale"
    CAD = 6.0  # native cadence, s
    DAY_US = 24 * 3600 * 1_000_000
    ENROLLED = {
        "house_1": ["washing_machine", "kettle", "microwave", "fridge"],
        "house_2": ["washing_machine", "dishwasher", "kettle", "microwave", "fridge"],
        "house_5": ["washing_machine", "dishwasher", "kettle", "fridge"],
    }
    DEV_COLOR = {"fridge": "tab:blue", "kettle": "tab:orange",
                 "microwave": "tab:green", "washing_machine": "tab:red",
                 "dishwasher": "tab:purple"}
    SPANS = {"1 h": 1 * 3600.0, "3 h": 3 * 3600.0, "6 h": 6 * 3600.0,
             "12 h": 12 * 3600.0, "24 h": 24 * 3600.0,
             "3 d": 3 * 24 * 3600.0, "7 d": 7 * 24 * 3600.0}
    SLIDER_MIN, SLIDER_MAX = -90, 400  # start-slider range, days after split
    ADV_STEPS = {"1 min": 1 / 60, "5 min": 5 / 60, "15 min": 0.25,
                 "30 min": 0.5, "1 h": 1.0, "3 h": 3.0}
    COVER = fl.FROZEN["interference_max_cover"]
    return (ADV_STEPS, CAD, COVER, DATASET, DAY_US, DEV_COLOR, ENROLLED,
            SLIDER_MAX, SLIDER_MIN, SPANS)


@app.cell(hide_code=True)
def _(SLIDER_MAX, SLIDER_MIN, SPANS, mo):
    house_dd = mo.ui.dropdown(
        options=["house_1", "house_2", "house_5"], value="house_1", label="house")
    k_dd = mo.ui.dropdown(
        options=[1, 2, 3, 5, 10, 20], value=10, label="K sessions/device")
    span_dd = mo.ui.dropdown(
        options=list(SPANS), value="24 h", label="span")
    start_slider = mo.ui.slider(
        start=SLIDER_MIN, stop=SLIDER_MAX, value=0, step=1,
        label="start: days after split")
    # hours of auto-advance accumulated by the play control below
    start_adv, set_start_adv = mo.state(0)
    mo.hstack([house_dd, k_dd, span_dd, start_slider])
    return (house_dd, k_dd, span_dd, start_adv, start_slider)


@app.cell(hide_code=True)
def _(ADV_STEPS, mo, set_start_adv, start_adv):
    # play: adds the chosen step to the start offset per tick; this marimo has
    # no native play element, so refresh + state is the documented pattern
    step_dd = mo.ui.dropdown(
        options=list(ADV_STEPS), value="5 min", label="play step per tick")
    probe_show = mo.ui.checkbox(value=True, label="show probe line")
    play_refresh = mo.ui.refresh(
        options=[0.5, 1, 2, 5], default_interval=1,
        label="play (interval in s)",
        on_change=lambda _v: set_start_adv(
            start_adv() + ADV_STEPS[step_dd.value]))
    mo.hstack([play_refresh, step_dd, probe_show])
    return (play_refresh, probe_show)


@app.cell(hide_code=True)
def _(DATASET, ENROLLED, fl, gold_parquet_path, house_dd, load_power_series, np):
    # --- Per-house setup: config, floor/noise, full native aggregate ---------
    house = house_dd.value
    cfg = fl.house_config(DATASET, house)
    split_us = int(cfg["split_us"])
    devices = list(ENROLLED[house])
    floor_est = fl.estimate_floor_noise(DATASET, house, split_us)
    floor_w = floor_est["floor_w"]
    sigma_off_w = floor_est["sigma_off_w"]
    mains = load_power_series(gold_parquet_path(DATASET, house, "mains"))
    ts = mains["ts_us"].to_numpy(np.int64)
    w = mains["w"].to_numpy(float)
    # submeters: evaluation-only reference for the figures (the model never
    # reads them - the aggregate is its only input)
    subs = {d: load_power_series(gold_parquet_path(DATASET, house, d))
            for d in devices}
    return cfg, devices, floor_w, house, sigma_off_w, split_us, subs, ts, w


@app.cell(hide_code=True)
def _(DAY_US, SLIDER_MAX, SLIDER_MIN, SPANS, np, span_dd, split_us, start_adv,
      start_slider, ts):
    # --- Window [t0_us, t1_us) from the start/span knobs, clamped to series --
    span_s = SPANS[span_dd.value]
    span_us = int(span_s * 1e6)
    # effective start = manual slider + played hours, wrapped over the slider
    # range so play loops around instead of stalling at the data edge
    off_h = (start_slider.value - SLIDER_MIN) * 24 + start_adv()
    start_days = SLIDER_MIN + (off_h % ((SLIDER_MAX - SLIDER_MIN) * 24)) / 24.0
    t0_us = int(np.clip(split_us + start_days * DAY_US,
                        int(ts[0]), int(ts[-1]) - span_us))
    t1_us = t0_us + span_us
    return (span_s, t0_us, t1_us)


@app.cell(hide_code=True)
def _(CAD, COVER, DATASET, cfg, devices, floor_w, fl, house, k_dd, np,
      sigma_off_w, split_us, ts, w):
    # --- Calibration: one seeded (K, draw) row, the runner's frozen path -----
    # mirror: 02_run_kcurve.build_param_rows for k_grid=[k], n_draws=1, native
    # cadence. Fridge comes from its passive profile (K-independent); every
    # other device draws K valid press sessions and fits (mu_w, sd_w,
    # p_on_stay); a device with no pool, no separable level, or too few
    # sessions falls back to never-claims (mu pinned so it can never win).
    k = k_dd.value
    rng = np.random.default_rng([fl.FROZEN["seed_base"], k, 0])
    pools = {d: fl.simulated_presses(DATASET, house, d, split_us) for d in devices}
    mu = np.zeros((1, len(devices)), np.float32)
    sd = np.zeros((1, len(devices)), np.float32)
    p_on = np.zeros((1, len(devices)), np.float32)
    for _i, _dev in enumerate(devices):
        dwell_s = cfg["devices"][_dev]["dwell_s"]
        if _dev == "fridge":
            prof = fl.fridge_passive_params(
                DATASET, house, cfg["devices"][_dev], floor_w, sigma_off_w,
                split_us, CAD)
            if prof is None:  # no pre-split duty intervals -> never claims
                mu[0, _i], sd[0, _i], p_on[0, _i] = floor_w, fl.FROZEN["sigma_floor_w"], 1.0 - CAD / 86400.0
            else:
                mu[0, _i], sd[0, _i], p_on[0, _i] = prof["mu_w"], prof["sd_w"], prof["p_on_stay"]
            continue
        est = None
        if len(pools[_dev]):
            others = {o: q for o, q in pools.items() if o != _dev and len(q)}
            # other devices' pools feed the H06 interference flag
            valid, _att = fl.sample_valid_sessions(pools[_dev], k, rng, others, COVER)
            est = fl.estimate_device_params(ts, w, floor_w, valid, CAD)
        if est is None:
            mu[0, _i], sd[0, _i], p_on[0, _i] = floor_w, fl.FROZEN["sigma_floor_w"], 1.0 - CAD / dwell_s
        else:
            mu[0, _i], sd[0, _i], p_on[0, _i] = est["mu_w"], est["sd_w"], est["p_on_stay"]
    params = {"mu": mu, "sd": sd, "p_on_stay": p_on,
              "sigma_off": np.array([sigma_off_w], np.float32), "floor_w": floor_w}
    return (k, params)


@app.cell(hide_code=True)
def _(CAD, devices, fl, params, t0_us, t1_us, ts, w):
    # --- Decode the window: Viterbi bits + posteriors, one batch row ---------
    dec = fl.decode_batch(ts, w, t0_us, t1_us, devices, params, CAD)
    return (dec,)


@app.cell(hide_code=True)
def _(dec, devices, fl, np, params, subs, t0_us, t1_us, ts, w):
    # --- Aligned series over the window: claimed W per device + ON bits ------
    x_h = (dec["ts"] - t0_us) / 3.6e9  # hours since window start
    g0 = int(np.searchsorted(ts, t0_us))
    g1 = int(np.searchsorted(ts, t1_us, side="right"))
    agg_win = w[g0:g1]
    pred = {d: fl.pred_power_series(dec, 0, i, float(params["mu"][0, i]))
            for i, d in enumerate(devices)}
    total_pred = np.zeros(len(dec["ts"]), float)
    for d in devices:
        total_pred = total_pred + pred[d]
    on = dec["on"][:, 0, :]  # (T, D) decoded ON bits
    # measured per-device load, interpolated onto the decode grid
    gt = {}
    for d in devices:
        sdf = subs[d]
        gt[d] = np.interp(dec["ts"], sdf["ts_us"].to_numpy(np.int64),
                          sdf["w"].to_numpy(float))
    return (agg_win, gt, on, pred, total_pred, x_h)


@app.cell(hide_code=True)
def _(mo, span_s):
    probe_slider = mo.ui.slider(
        start=0.0, stop=span_s, value=span_s / 2.0, step=0.25,
        label="probe (h into window)")
    probe_slider
    return (probe_slider,)


@app.cell(hide_code=True)
def _(devices, mo, np, on, probe_slider, span_s):
    # --- Probe readout: which devices are ON at the probe instant ------------
    i_probe = min(int(probe_slider.value / span_s * (len(on) - 1)), len(on) - 1)
    on_now = [d for i, d in enumerate(devices) if on[i_probe, i] == 1]
    mo.md("probe at **+" + f"{probe_slider.value:.2f} h** -> ON: "
          + (", ".join(on_now) if on_now else "*nothing*"))
    return (i_probe,)


@app.cell(hide_code=True)
def _(DEV_COLOR, agg_win, devices, floor_w, gt, i_probe, plt, probe_show, pred, x_h):
    # --- Figure 2: claims vs measurements, two panels over the aggregate -----
    # Step lines, not a stacked area: the fridge claims a flat mu_w for hours,
    # which a fill paints as one solid block, and short claims (kettle) vanish
    # into it. Two panels so claim and measurement never overplot: top = what
    # the model claims per device, bottom = what each submeter measured; the
    # grey aggregate (above floor) is the same on both for comparison.
    fig_stack, (ax_p, ax_m) = plt.subplots(
        2, 1, figsize=(12.5, 7.2), sharex=True, gridspec_kw={"hspace": 0.10})
    for _dev in devices:
        ax_p.plot(x_h, pred[_dev], drawstyle="steps-post", color=DEV_COLOR[_dev],
                  lw=1.4, label=_dev)
        ax_m.plot(x_h, gt[_dev], drawstyle="steps-post", color=DEV_COLOR[_dev],
                  lw=1.4, label=_dev + " (measured)")
    for _ax in (ax_p, ax_m):
        _ax.plot(x_h, agg_win - floor_w, color="0.25", lw=0.9,
                 label="aggregate (above floor)")
        _ax.axhline(0.0, color="0.6", lw=0.8)
        if probe_show.value:
            _ax.axvline(x_h[i_probe], color="tab:orange", ls="--", lw=1.2)
        _ax.grid(alpha=0.25)
    ax_p.set_ylabel("claimed W (above floor)")
    ax_p.set_title("top = model claims, bottom = submeter-measured; "
                   "grey = aggregate", fontsize=10)
    ax_p.legend(fontsize=8, ncol=3, loc="upper right")
    ax_m.set_xlabel("hours into window")
    ax_m.set_ylabel("measured W (submeter)")
    ax_m.legend(fontsize=8, ncol=3, loc="upper right")
    fig_stack
    return (fig_stack,)


@app.cell(hide_code=True)
def _(DEV_COLOR, agg_win, devices, floor_w, gt, i_probe, np, on, plt,
      probe_show, total_pred, x_h):
    # --- Figure 3: aggregate vs estimated load, ON windows shaded ------------
    fig_zoom, ax_z = plt.subplots(figsize=(12.5, 4.4))
    for _i, _dev in enumerate(devices):
        ax_z.fill_between(x_h, 0, 1, where=on[:, _i] == 1, color=DEV_COLOR[_dev],
                          alpha=0.18, lw=0, transform=ax_z.get_xaxis_transform())
    gt_total = np.zeros(len(x_h), float)
    for _d in devices:
        gt_total = gt_total + gt[_d]
    ax_z.plot(x_h, agg_win, color="0.65", lw=0.9, label="aggregate")
    ax_z.plot(x_h, total_pred + floor_w, color="0.05", lw=1.3,
              label="estimated load")
    ax_z.plot(x_h, gt_total + floor_w, color="0.35", lw=1.1, ls="--",
              label="measured load (floor + submeters)")
    if probe_show.value:
        ax_z.axvline(x_h[i_probe], color="tab:orange", ls="--", lw=1.2)
    ax_z.set_xlabel("hours into window")
    ax_z.set_ylabel("W (absolute)")
    ax_z.set_title("grey = aggregate, black = estimated, dashed = measured, "
                   "shade = claimed ON", fontsize=10)
    ax_z.legend(fontsize=8, ncol=2)
    ax_z.grid(alpha=0.25)
    fig_zoom
    return (fig_zoom,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Reading the figures.** A device claims its mu_w above the floor while
    its decoded bit is ON, its posterior clears the frozen unknown gate, and
    the step is not innovation-gated (pred_power_series). In the breakdown
    view the top panel draws each device's claim (0 when not claiming, its
    mu_w while claiming) and the bottom panel the submeter-measured load -
    evaluation-only reference, the model never reads it. In the span view
    the shaded bands are exactly those ON bits. The aggregate line above
    the claims is load the model does not attribute.

    Calibration mirrors the runner's frozen path: pre-split press pools, K
    valid sessions per device (seed = [seed_base, K, 0]), the H06
    interference flag, the fridge from its passive profile, fallback =
    never claims. Decode: chunked forward-backward + Viterbi with warmup on
    both sides.
    """)
    return


if __name__ == "__main__":
    app.run()
