"""Shared helpers for the fnd-layer dataset EDA notebooks (src/pipelines/02_fnd_eda_notebooks/).

Every dataset notebook imports this module for: repo-root resolution, parquet
reading/streaming, the common EDA battery (inventory, cadence/gaps, power
distribution, diurnal/weekly shape, steps, appliance ON-statistics,
simultaneity), and the shared figure style. Label metadata comes from the
project's gold appliance map (data/gold/appliance_map_<ds>.json, read-only).

Markdown formatters (md_table, md_scan_stats) feed mo.md cells in the marimo
notebooks; the print_* variants remain for terminal / scratch use.
Nothing here modifies anything under data/.
"""

import json
import math
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# ---------------------------------------------------------------- repo paths

def repo_root():
    # anchored at this file's own location so runs are cwd-independent
    # (marimo export/editor may launch from anywhere)
    root = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(root, "pyproject.toml")):
        parent = os.path.dirname(root)
        if parent == root:
            raise RuntimeError("repo root (pyproject.toml) not found above %s" % root)
        root = parent
    return root


ROOT = repo_root()
FND = os.path.join(ROOT, "data", "fnd")
GOLD = os.path.join(ROOT, "data", "gold")
SYNTHETIC_CSV = os.path.join(ROOT, "repo", "WattWiser", "data", "raw", "synthetic_shelly_data.csv")

# canonical target appliances (the client's five) and stable colours
CANON = ["kettle", "fridge", "microwave", "washing_machine", "dishwasher"]
CANON_COLORS = {
    "mains": "#222222",
    "kettle": "#d95f02",
    "fridge": "#1b6ca8",
    "washing_machine": "#2e8b57",
    "dishwasher": "#b2182b",
    "microwave": "#7b3294",
    "other": "#888888",
}


def canon_color(label):
    key = str(label).lower()
    for c in CANON:
        if c in key:
            return CANON_COLORS[c]
    return CANON_COLORS["other"]


def appliance_map(ds):
    """The project's canonical meter->label map (gold layer metadata)."""
    with open(os.path.join(GOLD, "appliance_map_" + ds + ".json")) as f:
        return json.load(f)


def fnd_file(*parts):
    return os.path.join(FND, *parts)


def ts_index(ts_us):
    return pd.to_datetime(ts_us, unit="us", utc=True)


def fmt_span(ts_us):
    if len(ts_us) == 0:
        return "-"
    return "%s -> %s (%.1f d)" % (
        pd.Timestamp(ts_us[0], unit="us", tz="UTC").strftime("%Y-%m-%d"),
        pd.Timestamp(ts_us[-1], unit="us", tz="UTC").strftime("%Y-%m-%d"),
        (ts_us[-1] - ts_us[0]) / 86400e6,
    )


def fmt_int(x):
    return "{:,}".format(int(round(x)))


# ---------------------------------------------------------------- reading

def read_channel(path, value_col="v0", ts_col="ts_us"):
    """Full read of one appliance channel (ts_us int64, watts float)."""
    t = pq.read_table(path, columns=[ts_col, value_col])
    ts = np.asarray(t[ts_col], dtype=np.int64)
    v = np.asarray(t[value_col], dtype=np.float64)
    return ts, v


def read_mains(paths_valuecols, join="outer"):
    """Load 2+ power series, align them on the timestamp grid, and sum.

    Used for split-phase mains (REDD meter1 + meter2): the whole-home
    aggregate is the sum of the two panel meters. Args: [(path, col), ...].
    """
    frames = []
    for i, (path, col) in enumerate(paths_valuecols):
        t = pq.read_table(path, columns=["ts_us", col])
        v = np.asarray(t[col], dtype=np.float64)
        frames.append(pd.Series(v, index=np.asarray(t["ts_us"], dtype=np.int64), name="m%d" % i))
    df = pd.concat(frames, axis=1, join=join)
    ts = df.index.to_numpy()
    w = df.sum(axis=1, skipna=True).to_numpy()
    return ts, w


# ---------------------------------------------------------------- streaming scan

def _scan_state():
    return {
        "n": 0, "n_missing": 0, "n_neg": 0,
        "vmin": math.inf, "vmax": -math.inf,
        "total_w": 0.0, "energy_ws": 0.0,
        "last_ts": None, "last_v": None, "t0": None,
        "hist": np.zeros(1200, dtype=np.int64),
        "diurnal_sum": np.zeros(24), "diurnal_n": np.zeros(24),
        "weekday_sum": np.zeros(7), "weekday_n": np.zeros(7),
        "q_res": [], "diffs_res": [], "step_res": [],
        "steps": {30: 0, 100: 0, 300: 0},
        "zoom_ts": [], "zoom_v": [],
        "week_sum": np.zeros(int(21 * 86400 // 60) + 1),
        "week_cnt": np.zeros(int(21 * 86400 // 60) + 1),
    }


def _acc_batch(st, ts, v, missing_values, local_offset_hours, stride,
               zoom_seconds, max_zoom_pts):
    """Accumulate one chunk (ts_us int64, watts float64) into the state."""
    hist_edges = np.arange(0.0, 6001.0, 5.0)
    n = len(ts)
    if n == 0:
        return
    st["n"] += n
    miss = np.isnan(v)
    for mval in missing_values:
        miss = miss | (v == mval)
    st["n_missing"] += int(miss.sum())
    vv = v[~miss]
    if len(vv):
        st["n_neg"] += int((vv < 0).sum())
        st["vmin"] = min(st["vmin"], float(vv.min()))
        st["vmax"] = max(st["vmax"], float(vv.max()))
        st["total_w"] += float(vv.sum())
        st["hist"] += np.histogram(vv, bins=hist_edges)[0]
        st["q_res"].append(vv[::stride])
        di = ((ts[~miss] // 3_600_000_000 + int(local_offset_hours)) % 24).astype(np.int64)
        st["diurnal_sum"] += np.bincount(di, weights=vv, minlength=24)
        st["diurnal_n"] += np.bincount(di, minlength=24)
        days = ts[~miss] // 86_400_000_000
        wd = (days + 3) % 7  # 1970-01-01 was a Thursday; Monday=0
        st["weekday_sum"] += np.bincount(wd, weights=vv, minlength=7)
        st["weekday_n"] += np.bincount(wd, minlength=7)
    if st["t0"] is None:
        st["t0"] = int(ts[0])
    t0 = st["t0"]
    in_week = ts < (t0 + 21 * 86400 * 1_000_000)
    if in_week.any():
        b = ((ts[in_week] - t0) // 60_000_000).astype(np.int64)
        ok = (b >= 0) & (b < len(st["week_sum"])) & ~miss[in_week]
        if ok.any():
            st["week_sum"] += np.bincount(b[ok], weights=v[in_week][ok], minlength=len(st["week_sum"]))
            st["week_cnt"] += np.bincount(b[ok], minlength=len(st["week_sum"]))
    in_zoom = (ts < (t0 + zoom_seconds * 1_000_000)) & ~miss
    if in_zoom.any():
        st["zoom_ts"].append(ts[in_zoom])
        st["zoom_v"].append(v[in_zoom])
    # segment contributions (left Riemann): pairs (v[i-1], v[i]) inside the
    # chunk, plus the boundary pair across the previous chunk.
    dts_in = np.diff(ts).astype(np.float64) / 1e6
    pair_ok = (~miss[1:]) & (~miss[:-1])
    if len(dts_in):
        st["energy_ws"] += float(np.sum(v[:-1][pair_ok] * dts_in[pair_ok]))
        dP = np.abs(v[1:] - v[:-1])[pair_ok]
        st["steps"][30] += int((dP >= 30).sum())
        st["steps"][100] += int((dP >= 100).sum())
        st["steps"][300] += int((dP >= 300).sum())
        st["step_res"].append(dP[::max(1, len(dP) // 30_000)])
        st["diffs_res"].append(dts_in[::max(1, len(dts_in) // 100_000)])
    if st["last_ts"] is not None and np.isfinite(st["last_v"]) and not miss[0]:
        dt_b = (ts[0] - st["last_ts"]) / 1e6
        st["energy_ws"] += float(st["last_v"] * dt_b)
        dP_b = abs(float(v[0]) - st["last_v"])
        if dP_b >= 30:
            st["steps"][30] += 1
        if dP_b >= 100:
            st["steps"][100] += 1
        if dP_b >= 300:
            st["steps"][300] += 1
    st["last_ts"] = int(ts[-1])
    st["last_v"] = vv[-1] if len(vv) else None


def _scan_finish(st, path, max_zoom_pts=400_000):
    hist_edges = np.arange(0.0, 6001.0, 5.0)
    dt_res = np.concatenate(st["diffs_res"]) if st["diffs_res"] else np.array([np.nan])
    dt_med = float(np.median(dt_res))
    gap_frac = float((dt_res > max(3.0, 3 * dt_med)).mean())
    q = np.concatenate(st["q_res"]) if st["q_res"] else np.array([np.nan])
    if st["zoom_ts"]:
        zt = np.concatenate(st["zoom_ts"])
        zv = np.concatenate(st["zoom_v"])
        zstride = max(1, len(zt) // max_zoom_pts)
        zoom = (zt[::zstride], zv[::zstride])
    else:
        zoom = (np.array([]), np.array([]))
    wk = st["week_cnt"] > 0
    t0 = st["t0"]
    week = (np.arange(len(st["week_sum"]))[wk] * 60 * 1e6 + t0,
            st["week_sum"][wk] / np.maximum(st["week_cnt"][wk], 1))
    step_sample = np.concatenate(st["step_res"]) if st["step_res"] else np.array([])
    return {
        "path": path, "n": st["n"], "n_missing": st["n_missing"], "n_neg": st["n_neg"],
        "t0": st["t0"], "t1": st["last_ts"],
        "span_days": (st["last_ts"] - st["t0"]) / 86400e6 if st["last_ts"] else float("nan"),
        "dt_med_s": dt_med, "dt_p90_s": float(np.percentile(dt_res, 90)),
        "gap_frac": gap_frac,
        "vmin": st["vmin"] if st["vmin"] != math.inf else np.nan, "vmax": st["vmax"],
        "mean_w": st["total_w"] / max(1, st["n"] - st["n_missing"]),
        "energy_kwh": st["energy_ws"] / 3.6e6,
        "quantiles": {("p%d" % qq): float(np.percentile(q, qq)) for qq in (1, 5, 10, 25, 50, 75, 90, 95, 99)},
        "hist_edges": hist_edges, "hist": st["hist"],
        "diurnal": st["diurnal_sum"] / np.maximum(st["diurnal_n"], 1),
        "diurnal_n": st["diurnal_n"],
        "weekday": st["weekday_sum"] / np.maximum(st["weekday_n"], 1),
        "steps": st["steps"], "step_sample": step_sample,
        "zoom": zoom, "week": week,
    }


def scan_power_series(path, value_col="v0", ts_col="ts_us", batch_rows=4_000_000,
                      missing_values=(-1.0,), local_offset_hours=0.0,
                      zoom_seconds=3 * 86400, max_zoom_pts=400_000):
    """Stream a ts+value parquet file and accumulate the EDA battery.

    Designed for large site-meter files (up to ~130M rows) that must not be
    materialised whole. Quantiles / dt-median use uniform decimation (at most
    ~2M values); sums and counts stay exact. Pass ECO's -1 sentinel in
    "missing_values" to exclude it from W statistics.
    """
    pf = pq.ParquetFile(path)
    stride = max(1, pf.metadata.num_rows // 2_000_000)
    st = _scan_state()
    for batch in pf.iter_batches(batch_size=batch_rows, columns=[ts_col, value_col]):
        ts = np.asarray(batch.column(ts_col), dtype=np.int64)
        v = np.asarray(batch.column(value_col), dtype=np.float64)
        _acc_batch(st, ts, v, missing_values, local_offset_hours, stride, zoom_seconds, max_zoom_pts)
    return _scan_finish(st, path, max_zoom_pts=max_zoom_pts)


def scan_arrays(ts, v, missing_values=(), local_offset_hours=0.0,
                zoom_seconds=3 * 86400, max_zoom_pts=400_000, name=""):
    """Same battery on an in-memory series (e.g. summed split-phase mains)."""
    ts = np.asarray(ts, dtype=np.int64)
    v = np.asarray(v, dtype=np.float64)
    stride = max(1, len(ts) // 2_000_000)
    st = _scan_state()
    CH = 8_000_000
    for i in range(0, len(ts), CH):
        _acc_batch(st, ts[i:i + CH], v[i:i + CH], missing_values,
                   local_offset_hours, stride, zoom_seconds, max_zoom_pts)
    return _scan_finish(st, name)


def print_scan_stats(scan, name="series"):
    q = scan["quantiles"]
    print("series            : %s" % name)
    print("rows              : %s (missing %s)" % (fmt_int(scan["n"]), fmt_int(scan["n_missing"])))
    print("span              : %.1f days" % scan["span_days"])
    print("cadence           : median %.2f s, p90 %.2f s, gap fraction %.3f"
          % (scan["dt_med_s"], scan["dt_p90_s"], scan["gap_frac"]))
    print("power W           : mean %.1f | p50 %.1f | p95 %.1f | p99 %.1f | max %.0f"
          % (scan["mean_w"], q["p50"], q["p95"], q["p99"], scan["vmax"]))
    print("energy            : %.1f kWh" % scan["energy_kwh"])
    print("steps per day     : >=30 W %.1f | >=100 W %.1f | >=300 W %.1f"
          % (scan["steps"][30] / scan["span_days"], scan["steps"][100] / scan["span_days"],
             scan["steps"][300] / scan["span_days"]))


def channel_stats(ts, v, missing_values=(-1.0,), noise_floor_w=5.0, gap_tol_samples=2,
                  thr_rule="legacy"):
    """Per-appliance-channel statistics from the raw channel.

    ON rule mirrors the project's gold convention (data/gold/thresholds.json):
    p50_on = median of samples above the 5 W noise floor; ON := w > max(5, 0.5*p50_on).
    Episodes are ON run-lengths with gaps <= gap_tol_samples bridged.

    thr_rule="floor" guards against meters with a standing draw (e.g. an IAM
    idling at 11 W, which the legacy rule reads as always-ON): floor = p5 of
    valid samples, p50_on = median above floor + noise_floor, and
    ON := w > floor + max(noise_floor, 0.5 * (p50_on - floor)).
    """
    miss = np.isnan(v)
    for mval in missing_values:
        miss = miss | (v == mval)
    vv = v[~miss]
    out = {
        "n": len(v), "n_missing": int(miss.sum()),
        "vmin": float(np.min(vv)) if len(vv) else np.nan,
        "vmax": float(np.max(vv)) if len(vv) else np.nan,
        "n_neg": int((vv < 0).sum()) if len(vv) else 0,
        "floor_w": float(np.percentile(vv, 5)) if len(vv) else np.nan,
        "thr_rule": thr_rule,
    }
    if len(ts) > 1:
        dt = np.diff(ts) / 1e6
        dt_pos = dt[dt > 0]
        out["dt_med_s"] = float(np.median(dt_pos)) if len(dt_pos) else np.nan
        out["gap_frac"] = float((dt > 3 * out["dt_med_s"]).mean()) if len(dt_pos) else np.nan
        out["span_days"] = (ts[-1] - ts[0]) / 86400e6
    if thr_rule == "floor" and len(vv):
        floor = out["floor_w"]
        above = vv[vv > floor + noise_floor_w]
        p50_on = float(np.median(above)) if len(above) else floor + noise_floor_w
        thr = floor + max(noise_floor_w, 0.5 * (p50_on - floor))
    else:
        above = vv[vv > noise_floor_w] if len(vv) else np.array([])
        p50_on = float(np.median(above)) if len(above) else np.nan
        thr = max(noise_floor_w, 0.5 * p50_on) if not np.isnan(p50_on) else noise_floor_w
    on = vv > thr
    out.update({
        "p50_on_w": p50_on, "thr_on_w": thr,
        "on_share": float(on.mean()) if len(on) else np.nan,
        "mean_w": float(vv.mean()) if len(vv) else np.nan,
        "energy_kwh": float(np.nansum(vv) * (out.get("dt_med_s") or np.nan) / 3.6e6) if len(vv) else np.nan,
    })
    # episodes = ON runs with short gaps bridged (vectorised run-length)
    n_ep = 0
    dwells = np.array([])
    if len(on):
        d = np.diff(on.astype(np.int8))
        starts = np.flatnonzero(d == 1) + 1
        ends = np.flatnonzero(d == -1) + 1
        if on[0]:
            starts = np.concatenate([[0], starts])
        if on[-1]:
            ends = np.concatenate([ends, [len(on)]])
        if len(starts):
            merged = []
            cur_start = starts[0]
            cur_end = ends[0]
            for s, e in zip(starts[1:], ends[1:]):
                if s - cur_end <= gap_tol_samples:
                    cur_end = e
                else:
                    merged.append(cur_end - cur_start)
                    cur_start, cur_end = s, e
            merged.append(cur_end - cur_start)
            n_ep = len(merged)
            dwells = np.asarray(merged, dtype=np.float64) * (out["dt_med_s"] or 1.0)
    out["episodes"] = n_ep
    out["episodes_per_day"] = n_ep / max(out.get("span_days") or np.nan, 1e-9)
    if len(dwells):
        out["dwell_p10_s"] = float(np.percentile(dwells, 10))
        out["dwell_p50_s"] = float(np.percentile(dwells, 50))
        out["dwell_p90_s"] = float(np.percentile(dwells, 90))
    out["dwell_array"] = dwells
    return out


def onset_steps(ts, v, missing_values=(-1.0,), min_step_w=30.0, gap_tol_s=None):
    """|dP| at every rising transition >= min_step_w (step-size ECDFs).

    gap_tol_s: drop transitions spanning a sampling gap longer than this
    (seconds) — a step measured across missing time is not an appliance step.
    """
    miss = np.isnan(v)
    for mval in missing_values:
        miss = miss | (v == mval)
    vv = np.where(miss, np.nan, v)
    dP = np.diff(vv)
    ok = np.isfinite(dP) & (dP >= min_step_w)
    if gap_tol_s is not None and len(ts) > 1:
        ok = ok & (np.diff(np.asarray(ts, dtype=np.int64)) / 1e6 <= float(gap_tol_s))
    return dP[ok]


def simultaneity(ts_list, on_list, bucket_s=60):
    """Share of time with 0/1/2+ appliances ON, on a common bucket grid.

    Args: lists of (ts_us) and (on_mask) per channel. Resampled by mean over
    the bucket, then ON := mean > 0.5 (majority of the bucket's samples).
    """
    valid = [(t, o) for t, o in zip(ts_list, on_list) if len(t)]
    if not valid:
        return {"shares": {}, "two_plus": np.nan, "n_buckets": 0}
    t0 = min(int(t[0]) for t, _ in valid)
    t1 = max(int(t[-1]) for t, _ in valid)
    grid_n = int((t1 - t0) // (bucket_s * 1_000_000)) + 1
    acc = np.zeros(grid_n, dtype=np.int16)
    for ts, on in valid:
        idx = ((ts - t0) // (bucket_s * 1_000_000)).astype(np.int64)
        ok = (idx >= 0) & (idx < grid_n)
        cnt = np.bincount(idx[ok], weights=on[ok].astype(float), minlength=grid_n)
        nb = np.bincount(idx[ok], minlength=grid_n)
        acc[(cnt / np.maximum(nb, 1)) > 0.5] += 1
    vals, counts = np.unique(acc, return_counts=True)
    share = {int(v): float(c) / len(acc) for v, c in zip(vals, counts)}
    return {"shares": share, "two_plus": float((acc >= 2).mean()), "n_buckets": len(acc)}


def resample_grid(ts, v, bucket_s, t0, n):
    """Mean-pool onto a FIXED-LENGTH bucket grid (no compaction) so several
    channels align by array index. Returns (grid_ts, mean_or_nan) of length n.
    Empty buckets stay NaN (use nansum / nan-aware ops downstream)."""
    ts = np.asarray(ts, dtype=np.int64)
    v = np.asarray(v, dtype=np.float64)
    idx = ((ts - t0) // (bucket_s * 1_000_000)).astype(np.int64)
    ok = (idx >= 0) & (idx < n) & np.isfinite(v)
    s = np.bincount(idx[ok], weights=v[ok], minlength=n)
    c = np.bincount(idx[ok], minlength=n)
    m = c > 0
    out = np.full(n, np.nan)
    out[m] = s[m] / c[m]
    return (np.arange(n) * bucket_s * 1e6 + t0), out


def resample_mean(ts, v, bucket_s, t0=None, t1=None):
    """Mean-pool a series onto a fixed bucket grid (int floor-div, no resample())."""
    if t0 is None:
        t0 = int(ts[0])
    if t1 is None:
        t1 = int(ts[-1])
    n = int((t1 - t0) // (bucket_s * 1_000_000)) + 1
    idx = ((ts - t0) // (bucket_s * 1_000_000)).astype(np.int64)
    ok = (idx >= 0) & (idx < n) & np.isfinite(v)
    s = np.bincount(idx[ok], weights=v[ok], minlength=n)
    c = np.bincount(idx[ok], minlength=n)
    m = c > 0
    return (np.arange(n)[m] * bucket_s * 1e6 + t0), (s[m] / c[m])


def kwh_of(ts, v, missing_values=(-1.0,), dt_cap_s=None):
    """Energy of one channel, dt-weighted (kWh).

    dt_cap_s bounds the weight of a single sample across a long gap (a
    sparse-cadence guard); None keeps the uncapped legacy behaviour.
    """
    miss = np.isnan(v)
    for mval in missing_values:
        miss = miss | (v == mval)
    dt = np.diff(ts) / 1e6
    if dt_cap_s is not None:
        dt = np.minimum(dt, float(dt_cap_s))
    valid_pairs = (~miss[:-1]) & (~miss[1:])
    return float(np.sum(v[:-1][valid_pairs] * dt[valid_pairs]) / 3.6e6)




def load_thresholds():
    """Project ON thresholds per dataset/building/appliance (gold metadata)."""
    with open(os.path.join(GOLD, "thresholds.json")) as f:
        return json.load(f)


def read_labels_dat(path):
    """UK-DALE labels.dat -> {channel(int): label(str)}."""
    out = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                out[int(parts[0])] = parts[1]
    return out


# ---------------------------------------------------------------- figures

def apply_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.figsize": (11.0, 3.0), "figure.dpi": 110,
        "axes.grid": True, "grid.alpha": 0.3, "font.size": 9,
        "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
    })
    return plt


def fig_zoom(scan, ax=None, title="", ylabel="W (active)"):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 3.0))
    zt, zv = scan["zoom"]
    if len(zt):
        ax.plot(pd.to_datetime(zt, unit="us", utc=True), zv, lw=0.3, color=CANON_COLORS["mains"])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    return ax


def fig_week(scan, ax=None, title="", ylabel="W (60 s means)"):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 2.6))
    wt, wv = scan["week"]
    if len(wt):
        ax.plot(pd.to_datetime(wt, unit="us", utc=True), wv, lw=0.6, color=CANON_COLORS["mains"])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    return ax


def fig_hist_power(scan, ax=None, title="", clip_w=2000):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 2.8))
    edges = scan["hist_edges"]
    counts = scan["hist"]
    centers = (edges[:-1] + edges[1:]) / 2
    m = centers <= clip_w
    ax.bar(centers[m], np.maximum(counts[m], 0.5), width=5.0, color="#5a7fa5", log=True)
    for name in ("p50", "p95", "p99"):
        qv = scan["quantiles"][name]
        if qv <= clip_w:
            ax.axvline(qv, color="#b2182b", lw=1, ls="--")
            ax.text(qv, 1, " " + name, color="#b2182b", fontsize=8, rotation=90, va="bottom")
    ax.set_xlabel("power (W)")
    ax.set_ylabel("samples")
    ax.set_title(title)
    return ax


def fig_diurnal(scan, ax=None, title=""):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 2.6))
    ax.bar(np.arange(24), scan["diurnal"], color="#2e8b57")
    ax.set_xticks(np.arange(0, 24, 2))
    ax.set_xlabel("hour of day (local clock, fixed offset)")
    ax.set_ylabel("mean W")
    ax.set_title(title)
    return ax


def fig_weekday(scan, ax=None, title=""):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 2.4))
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    ax.bar(np.arange(7), scan["weekday"], color="#5a7fa5")
    ax.set_xticks(np.arange(7))
    ax.set_xticklabels(days)
    ax.set_ylabel("mean W")
    ax.set_title(title)
    return ax


def fig_steps(scan, ax=None, title="", clip_w=1000):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 2.8))
    s = np.asarray(scan["step_sample"])
    s = s[s > 0]
    ax.hist(s[s <= clip_w], bins=150, log=True, color="#7b3294")
    ax.set_xlabel("|dP| between consecutive samples (W)")
    ax.set_ylabel("steps")
    ax.set_title(title)
    return ax


def fig_energy_share(items, ax=None, title=""):
    """items: list of (label, kWh, color), descending; barh chart."""
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 0.4 * max(3, len(items)) + 1))
    labels = [k for k, _, _ in items][::-1]
    vals = [v for _, v, _ in items][::-1]
    cols = [c for _, _, c in items][::-1]
    ax.barh(np.arange(len(labels)), vals, color=cols)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    total = sum(v for _, v, _ in items)
    for i, v in enumerate(vals):
        ax.text(v, i, "  %.0f kWh (%.1f%%)" % (v, 100 * v / total), va="center", fontsize=8)
    ax.set_xlabel("energy (kWh) over the channel's own span")
    ax.set_title(title)
    return ax


def fig_duty_vs_power(rows, ax=None, title=""):
    """rows: list of dicts(label, duty(0..1), p50_on_w, energy_kwh, color)."""
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 3.4))
    for r in rows:
        ax.scatter(r["p50_on_w"], 100 * r["duty"],
                   s=max(10, 3 * math.sqrt(max(r["energy_kwh"], 0.01))),
                   color=r["color"], alpha=0.75, edgecolor="k", linewidth=0.3)
        ax.annotate(r["label"], (r["p50_on_w"], 100 * r["duty"]),
                    textcoords="offset points", xytext=(5, 3), fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("median ON power (W, log scale)")
    ax.set_ylabel("duty cycle (% of samples ON)")
    ax.set_title(title)
    return ax


def fig_dwell_ecdf(dwell_lists, ax=None, title=""):
    """dwell_lists: list of (label, dwell_s array, color); semilog-x ECDF."""
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 2.8))
    for label, dw, color in dwell_lists:
        if len(dw) == 0:
            continue
        x = np.sort(dw)
        ax.plot(x, np.arange(1, len(x) + 1) / len(x), label=label, color=color, lw=1.2)
    ax.set_xscale("log")
    ax.set_xlabel("episode duration (s, log)")
    ax.set_ylabel("ECDF")
    ax.legend(loc="lower right")
    ax.set_title(title)
    return ax


def fig_simultaneity(sim, ax=None, title=""):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 2.4))
    shares = sim["shares"]
    maxk = max(int(k) for k in shares) if shares else 0
    xs = np.arange(maxk + 1)
    ys = [100 * shares.get(k, 0.0) for k in xs]
    ax.bar(xs, ys, color="#5a7fa5")
    for k in xs:
        ax.text(k, ys[k], "%.1f" % ys[k], ha="center", va="bottom", fontsize=8)
    ax.set_xlabel("number of monitored appliances ON at once")
    ax.set_ylabel("% of time")
    ax.set_title(title)
    return ax


def fig_overlay_zoom(base_ts, base_v, series, ax=None, title="", days=3, base_label="mains"):
    """Overlay mains zoom + appliance submeters for the same first days."""
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 3.2))
    t0 = int(base_ts[0])
    t1 = t0 + days * 86400 * 1_000_000
    m = base_ts < t1
    ax.plot(pd.to_datetime(base_ts[m], unit="us", utc=True), base_v[m], lw=0.3,
            color=CANON_COLORS["mains"], label=base_label)
    for label, ts, v in series:
        mm = ts < t1
        ax.plot(pd.to_datetime(ts[mm], unit="us", utc=True), v[mm], lw=0.5,
                label=label, color=canon_color(label))
    ax.legend(loc="upper right", ncol=min(5, 1 + len(series)))
    ax.set_ylabel("W")
    ax.set_title(title)
    return ax


def print_table(headers, rows):
    widths = [max([len(str(h))] + [len(str(r[i])) for r in rows]) if rows else len(str(h))
              for i, h in enumerate(headers)]
    line = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(str(x).ljust(w) for x, w in zip(r, widths)))


# ------------------------------------------------------------ markdown formatters

def md_table(headers, rows):
    """Render a table as a markdown string (pipe to mo.md in marimo notebooks)."""

    def _cell(x):
        return str(x).replace("|", "\\|").replace("\n", " ")

    hdr = "| " + " | ".join(_cell(h) for h in headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_cell(x) for x in r) + " |" for r in rows]
    return "\n".join([hdr, sep] + body)


def md_summary(s):
    """Render the notebook's machine-readable SUMMARY dict as markdown.

    Top-level scalars and the appliance rows become tables; the raw JSON is
    kept in a collapsed <details> block so the notebook stays readable while
    the machine-readable summary contract is preserved.
    """
    agg = s.get("aggregate", {})
    rows = [
        ("dataset", s.get("dataset", "-")),
        ("rows", fmt_int(s["rows"]) if s.get("rows") is not None else "-"),
        ("span", "%.1f days" % s["span_days"] if "span_days" in s else "-"),
        ("cadence", "%.2f s" % s["cadence_s"] if "cadence_s" in s else "-"),
        ("power W (mean / p50 / p95)",
         "%.1f / %.1f / %.1f" % (agg.get("mean_w", float("nan")),
                                 agg.get("p50_w", float("nan")),
                                 agg.get("p95_w", float("nan"))) if agg else "-"),
        ("energy", "%.1f kWh" % agg["energy_kwh"] if "energy_kwh" in agg else "-"),
    ]
    if "additivity_residual_mean_w" in s:
        rows.append(("additivity residual (mean / std)",
                     "%.1f / %.1f W" % (s["additivity_residual_mean_w"],
                                        s.get("additivity_residual_std_w", 0.0))))
    if "current_identity_max_abs_err_a" in s:
        rows.append(("current identity max |err|", "%.3g A" % s["current_identity_max_abs_err_a"]))
    if "unlabeled_base_pct" in s:
        rows.append(("unlabeled base", "%.1f%% of samples" % s["unlabeled_base_pct"]))
    if "simultaneity_two_plus_pct" in s:
        sim = s["simultaneity_two_plus_pct"]
        if isinstance(sim, dict):
            for k2, v2 in sim.items():
                try:
                    rows.append(("simultaneity (2+ ON) - %s" % str(k2).replace("_", " "),
                                 "%.1f%% of 60 s buckets" % float(v2)))
                except (TypeError, ValueError):
                    rows.append(("simultaneity (2+ ON) - %s" % str(k2).replace("_", " "), str(v2)))
        else:
            rows.append(("simultaneity (2+ ON)", "%.1f%% of 60 s buckets" % sim))
    if s.get("role"):
        rows.append(("role", str(s["role"])))
    md = ["**Summary**", "", md_table(["metric", "value"], rows)]
    apps = s.get("appliances") or []
    if apps:
        headers = ["label", "p50_on_W", "thr_on_W", "duty_%", "kWh", "eps/day", "dwell_p50_s"][:len(apps[0])]
        md += ["", "Appliances:", "", md_table(headers, apps)]
    md += [
        "",
        "<details><summary>raw JSON (machine-readable)</summary>",
        "",
        "```json",
        json.dumps(s, indent=2, default=str),
        "```",
        "",
        "</details>",
    ]
    return "\n".join(md)


def md_scan_stats(scan, name="series"):
    """Same content as print_scan_stats, rendered as a markdown string."""
    q = scan["quantiles"]
    rows = [
        ("series", name),
        ("rows", "%s (missing %s)" % (fmt_int(scan["n"]), fmt_int(scan["n_missing"]))),
        ("span", "%.1f days" % scan["span_days"]),
        ("cadence", "median %.2f s, p90 %.2f s, gap fraction %.3f"
         % (scan["dt_med_s"], scan["dt_p90_s"], scan["gap_frac"])),
        ("power W", "mean %.1f, p50 %.1f, p95 %.1f, p99 %.1f, max %.0f"
         % (scan["mean_w"], q["p50"], q["p95"], q["p99"], scan["vmax"])),
        ("energy", "%.1f kWh" % scan["energy_kwh"]),
        ("steps per day", ">=30 W %.1f, >=100 W %.1f, >=300 W %.1f"
         % (scan["steps"][30] / scan["span_days"], scan["steps"][100] / scan["span_days"],
            scan["steps"][300] / scan["span_days"])),
    ]
    return md_table(["metric", "value"], rows)

