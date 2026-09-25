"""E2E experiment runner: anchor (A0), session-supervised FHMM K-curve (B1),
EM ablation (B0) - plan arms, frozen protocol.

Per house writes docs/reports/fhmm/metrics_kcurve_<house>.json with the
three-axis surface per arm/K/draw: pooled + per-device episode F1, span
stats pooled over matched pairs (overall + solo/co-occurring strata),
nMAE, whole-span energy balance (serialized key "books_close"), unknown share, session yield.

Conventions (frozen):
- evaluation GT = submeter episodes via build_episodes + the profile rule;
  scoring window = post-split (house_1: first 12 months); submeters are
  evaluation-only, every model reads the aggregate.
- axis 3 power series: B1/EM claim mu_w while claimed ON; the anchor
  claims the aggregate restricted to its spans (it asserts intervals,
  not levels), so its overlap double-counts - visible in the energy balance.
- B1 decodes parameter rows in slices to bound memory; metrics reduce
  per slice. p_on_stay is rescaled for the 60 s cadence (same dwell).

Run: .venv/bin/python3 src/experiments/01_fhmm/02_run_kcurve.py
      --houses house_2,house_5 [--cadences native,60] [--skip-em]
      [--slice 16] [--draws 20]

Reading order: constants and type aliases -> numerical helpers (60 s
grid, parameters, scoring) -> cadence plumbing -> the three arms (A0 anchor,
B1 K-curve, B0 EM) -> orchestration (prepare_house, run_house, main).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fhmm_lib as fhmm  # noqa: E402

from wattwiser.experiments.data_loader import gold_parquet_path, load_power_series  # noqa: E402
from wattwiser.experiments.evaluation import match_onsets, precision_recall_f1  # noqa: E402

DATASET = "ukdale"
ENROLLED: dict[str, list[str]] = {
    "house_1": ["washing_machine", "kettle", "microwave", "fridge"],
    "house_2": ["washing_machine", "dishwasher", "kettle", "microwave", "fridge"],
    "house_5": ["washing_machine", "dishwasher", "kettle", "fridge"],
}
CAD_NATIVE = 6.0
CAD_60S = 60.0
DWELL_BAND = fhmm.FROZEN["dwell_band"]
YEAR_US = 365 * 24 * 3600 * 1_000_000
DAY_US = 24 * 3600 * 1_000_000
# Matching tolerance per cadence (frozen), pre-multiplied to microseconds.
TAU_US = {"native": int(fhmm.FROZEN["tau_native_s"] * 1e6),
          "60": int(fhmm.FROZEN["tau_60_s"] * 1e6)}

# The parameter block handed to fhmm_lib.decode_batch (mu/sd/p_on_stay rows).
Params = dict[str, np.ndarray]
# A nested JSON-able metric bundle.
Metrics = dict[str, object]


def log(*args: object) -> None:
    """Flush-printing progress line (the runner is watched live, not parsed)."""
    print(*args, flush=True)


# ------------------------------------------------------------------ 60 s observation grid


def rescale_p_on(p_on: np.ndarray, cad_from: float, cad_to: float) -> np.ndarray:
    """Same expected dwell in seconds at a coarser step grid."""
    q = (1.0 - p_on.astype(np.float64)) * (cad_from / cad_to)
    # OFF chance per step scales by the step-length ratio; E[dwell] seconds preserved
    return (1.0 - q).astype(np.float32)


def floor_noise_60s(ts_all: np.ndarray, w_all: np.ndarray, split_us: int):
    """The frozen floor/noise estimator (p10 floor, 1.4826 x MAD) re-run on
    the 60 s bucket-mean aggregate: averaging shrinks ambient noise by
    sqrt(6/60), so sigma_off for the 60 s cadence must be estimated on the
    bucket-mean series, not carried over from the native one.

    Pre-split span only. Returns (floor_w, sigma_off_w).
    """
    bucket_ts, bucket_w = fhmm.bucket_mean(ts_all, w_all, CAD_60S)
    pre = bucket_w[bucket_ts < split_us]
    # same p10 / 1.4826-MAD recipe as the native estimator, on the bucketed series
    floor = float(np.percentile(pre, 10))
    resid = pre - floor
    mad = float(np.median(np.abs(resid - np.median(resid))))
    return floor, max(1.4826 * mad, 1.0)


def params_at_60s(params: Params, sigma_native: float, sigma_60s: float) -> Params:
    """Emission widths at the 60 s observation scale: device session sd is
    phase spread plus ambient; only the ambient component shrinks with
    bucket-meaning. Levels are unchanged (bucket-means preserve means).
    """
    out = dict(params)
    sd6 = params["sd"].astype(np.float64)**2
    excess = np.maximum(sd6 - sigma_native**2, 0.0)
    # strip the native ambient, re-add at 60 s: sd' = sqrt(excess + sigma_60s^2)
    out["sd"] = np.sqrt(excess + sigma_60s**2).astype(np.float32)
    if "sigma_off" in out:
        out["sigma_off"] = np.full(len(params["sigma_off"]), sigma_60s, np.float32)
    return out


# ---------------------------------------------------------------- sessions


def never_claims_row(floor_w: float, dwell_s: float) -> tuple[float, float, float]:
    """Fallback (mu_w, sd_w, p_on_stay) for a device with no separable level:
    mu pinned to the floor so it never claims, sigma at the frozen floor
    width, and a dwell prior consistent with one on-step every dwell_s.
    """
    # flow: (floor, frozen width, dwell prior) -> (mu, sd, p_on) that never claims
    return floor_w, fhmm.FROZEN["sigma_floor_w"], 1.0 - CAD_NATIVE / dwell_s


def build_param_rows(dataset: str, house: str, cfg: dict, ts: np.ndarray,
                     w: np.ndarray, floor_w: float, sigma_off_w: float,
                     k_grid: list[int], n_draws: int, cover: float):
    """Per (K, draw) parameter rows: mu/sd/p_on_stay per enrolled device.
    Fridge is the fixed passive profile in every row (K-independent). Rows
    where a device has no separable session level get mu = floor (never
    claims) and the profile dwell prior; the yield is recorded.

    Row order is K-major then draw: row i = i // n_draws is the K index and
    i % n_draws the draw index. Each (K, draw) draws its own RNG, consumed
    device by device in enrollment order (fridge consumes nothing).

    Returns (params, press_pools, yield_rows, devices); press_pools is
    returned for callers that need the raw simulated presses.
    """
    # flow: per (K, draw): press pool -> k valid sessions -> per-device params
    #   -> one row of (mu, sd, p_on_stay); rows ordered K-major
    split = cfg["split_us"]                     # train/test boundary: calibration = presses strictly before it
    devices = ENROLLED[house]                   # fixed enrollment order -> column order in every row
    n_dev = len(devices)
    press_pools = {device: fhmm.simulated_presses(dataset, house, device, split) for device in devices}
    # raw material: every pre-split GT cycle mark as a simulated press
    passive = {}                                # fridge: one profile, reused in every row (K-independent)
    for device in devices:
        if device == "fridge":
            passive[device] = fhmm.fridge_passive_params(
                dataset, house, cfg["devices"][device], floor_w, sigma_off_w,
                split, CAD_NATIVE)
    n_rows = len(k_grid) * n_draws              # one row per (K, draw)
    mu = np.zeros((n_rows, n_dev), np.float32)  # emission tensors, filled one cell at a time below
    sd = np.zeros((n_rows, n_dev), np.float32)
    p_on = np.zeros((n_rows, n_dev), np.float32)
    sigma_off = np.full(n_rows, sigma_off_w, np.float32)   # ambient width: same constant in every row
    yield_rows = []                             # per (K, draw, device): how many sessions survived the draw
    i = 0                                       # flat row index; loops below fill rows in K-major order
    for k in k_grid:
        for r in range(n_draws):
            rng = np.random.default_rng([fhmm.FROZEN["seed_base"], k, r])
            # one seeded stream per (K, draw); consumed device by device, in order
            for d_i, device in enumerate(devices):
                if device == "fridge":
                    prof = passive.get(device)
                    if prof is None:            # no fridge profile -> a device that never claims
                        mu[i, d_i], sd[i, d_i], p_on[i, d_i] = \
                            never_claims_row(floor_w, 86400.0)
                    else:
                        # same numbers in every row: the fridge K-curve stays flat by design
                        mu[i, d_i] = prof["mu_w"]
                        sd[i, d_i] = prof["sd_w"]
                        p_on[i, d_i] = prof["p_on_stay"]
                    continue
                dwell_prof = cfg["devices"][device]["dwell_s"]   # dwell prior for never-claims rows
                presses = press_pools[device]
                if len(presses) == 0:           # zero pre-split marks -> nothing to fit -> never claims
                    mu[i, d_i], sd[i, d_i], p_on[i, d_i] = \
                        never_claims_row(floor_w, dwell_prof)
                    yield_rows.append({"k": k, "draw": r, "device": device,
                                       "valid": 0, "attempts": 0})
                    continue
                others = {o: q for o, q in press_pools.items() if o != device and len(q)}
                # other devices' sessions feed the H06 interference flag
                valid, att = fhmm.sample_valid_sessions(presses, k, rng, others, cover)
                # draw k sessions, drop interference-flagged ones, fit the rest
                est = fhmm.estimate_device_params(ts, w, floor_w, valid, CAD_NATIVE)
                if est is None:                 # < k separable sessions, or the level sits under the floor
                    mu[i, d_i], sd[i, d_i], p_on[i, d_i] = \
                        never_claims_row(floor_w, dwell_prof)
                else:
                    mu[i, d_i] = est["mu_w"]    # fitted emission lands in this (K, draw) cell
                    sd[i, d_i] = est["sd_w"]
                    p_on[i, d_i] = est["p_on_stay"]
                yield_rows.append({"k": k, "draw": r, "device": device,
                                   "valid": int(len(valid)), "attempts": int(att)})
            i += 1                              # next (K, draw) row; all devices share the same row
    params = {"mu": mu, "sd": sd, "p_on_stay": p_on, "sigma_off": sigma_off}
    # row i = K i // n_draws, draw i % n_draws (the K-major contract)
    return params, press_pools, yield_rows, devices


# ---------------------------------------------------------------- scoring


def gt_eps_by_device(dataset: str, house: str, cfg: dict, t0: int, t1: int) -> dict[str, pd.DataFrame]:
    """Evaluation GT episodes per enrolled device (submeters, eval-only)."""
    # flow: per enrolled device -> GT episodes clipped to the scoring window
    out = {}
    for device in ENROLLED[house]:
        out[device] = fhmm.evaluation_gt_episodes(dataset, house, device, cfg["devices"][device], t0, t1)
    return out


def score_row(pred_eps: pd.DataFrame, gt_eps: dict[str, pd.DataFrame],
              tau_us: int, devices: list[str]) -> tuple[dict, dict]:
    """Per-device score dicts + pooled P/R/F1 over scored devices."""
    # flow: pred episodes + per-device GT -> score dicts -> pooled counts
    per_device = {}
    for device in devices:
        if len(pred_eps):
            pred = pred_eps[pred_eps["device"] == device].reset_index(drop=True)
        else:
            pred = pred_eps
        per_device[device] = fhmm.score_device(pred, gt_eps[device].reset_index(drop=True),
                                         tau_us, DWELL_BAND)
    scored = [per_device[device] for device in devices
              if per_device[device]["n_gt"] or per_device[device]["n_pred"]]
    if scored:
        pooled = fhmm.pooled_precision_recall_f1(scored)
    else:
        pooled = {"n_pred": 0, "n_gt": 0, "n_matched": 0,
                  "precision": None, "recall": None, "f1": None}
    return per_device, pooled


def row_span(per_device: dict[str, dict]) -> dict:
    """Span metrics pooled over the matched pairs of one row."""
    spans = [s["span"] for s in per_device.values() if s.get("span")]
    if not spans:
        return {"n_pairs": 0}
    return fhmm.pooled_span_stats([{"span": s} for s in spans])


def strata_scores(pred_eps: pd.DataFrame, gt_eps: dict[str, pd.DataFrame],
                  tau_us: int, devices: list[str]) -> dict:
    """Solo vs co-occurring pooled counts (preds inherit the stratum of
    their matched GT episode; unmatched preds are not attributed)."""
    # flow: per device: onset matches -> stratum of the matched GT episode ->
    #   pooled counts per stratum (solo / co-occurring)
    strata = {"solo": {"n_pred": 0, "n_gt": 0, "n_matched": 0},
              "co": {"n_pred": 0, "n_gt": 0, "n_matched": 0}}
    for device in devices:
        gt = gt_eps[device].reset_index(drop=True)
        if len(pred_eps):
            pred = pred_eps[pred_eps["device"] == device].reset_index(drop=True)
        else:
            pred = pred_eps
        if gt.empty:
            continue
        co_occurring = fhmm.tag_cooccurring(gt_eps, device)
        strata["solo"]["n_gt"] += int((~co_occurring).sum())
        strata["co"]["n_gt"] += int(co_occurring.sum())
        if len(pred) == 0:
            continue
        gt_on = gt["t_on_us"].to_numpy(np.int64)
        gt_off = gt["t_off_us"].to_numpy(np.int64)
        pred_on = pred["t_on_us"].to_numpy(np.int64)
        pred_off = pred["t_off_us"].to_numpy(np.int64)
        gt_idx, pred_idx = match_onsets(gt_on, pred_on, tau_us)
        if len(gt_idx) == 0:
            continue
        ratio = (pred_off[pred_idx] - pred_on[pred_idx]) / \
            np.maximum(gt_off[gt_idx] - gt_on[gt_idx], 1)
        keep = (ratio >= DWELL_BAND[0]) & (ratio <= DWELL_BAND[1])
        # same dwell-band rule as score_device
        for gt_i in gt_idx[keep]:
            strata["co" if co_occurring[gt_i] else "solo"]["n_matched"] += 1
    for stratum in strata.values():
        stratum["n_pred"] = stratum["n_matched"]
        p, r, f1 = precision_recall_f1(stratum["n_matched"], stratum["n_pred"], stratum["n_gt"])
        stratum.update({"precision": p, "recall": r, "f1": f1})
    return strata


def align_to_grid(dev_ts: np.ndarray, dev_w: np.ndarray, grid_ts: np.ndarray,
               step_s: float) -> np.ndarray:
    """Bucket-mean a device series onto the observation grid (grid_ts, step_s)."""
    # flow: device (ts, w) + obs grid -> shared bucket ids -> grouped sums ->
    #   mean W per grid point (0 where the device has no samples)
    bucket_us = int(step_s * 1e6)
    half = bucket_us // 2
    grid_ids = (grid_ts - half) // bucket_us
    dev_ids = dev_ts // bucket_us
    pos = np.searchsorted(grid_ids, dev_ids)
    # grid ids sit half a bucket early so the midpoints land on grid_ts
    pos_c = np.minimum(pos, len(grid_ids) - 1)
    matched = (pos < len(grid_ids)) & (grid_ids[pos_c] == dev_ids)
    acc = np.zeros(len(grid_ts))
    cnt = np.zeros(len(grid_ts))
    np.add.at(acc, pos_c[matched], dev_w[matched])
    np.add.at(cnt, pos_c[matched], 1.0)
    return acc / np.maximum(cnt, 1.0)


def axis3(pred_power_by_device: dict[str, np.ndarray], grid_ts: np.ndarray,
          agg_w: np.ndarray, gt_power_by_device: dict[str, pd.DataFrame], step_s: float,
          at_60s: bool, total_wh: float, floor_wh: float) -> dict:
    """Axis 3 (regression): per-device nMAE, attributed energy, and the
    whole-span energy balance (serialized under the legacy key
    "books_close"). nMAE denominator is the mean aggregate power over the
    shared grid, so a never-claiming predictor scores
    mean(device)/mean(aggregate), not 1.0. At the 60 s cadence (at_60s)
    the device GT is bucket-meanned onto the same grid.
    """
    # flow: per device: pred W vs GT (+ step-rule energy) -> per-device dict;
    #   then one whole-span balance: total vs attributed vs floor
    den_w = float(np.mean(agg_w)) if len(agg_w) else float("nan")
    out = {"den_w": round(den_w, 2), "per_device": {}}
    attributed_wh = 0.0
    for device, pred_power in pred_power_by_device.items():
        if at_60s:
            gt_on_grid = align_to_grid(gt_power_by_device[device]["ts_us"].to_numpy(np.int64),
                                 gt_power_by_device[device]["w"].to_numpy(float), grid_ts, step_s)
            mae_w = float(np.abs(pred_power - gt_on_grid).mean())
        else:
            mae_w = fhmm.nmae_for_device(grid_ts, pred_power, gt_power_by_device[device], agg_w)["mae_w"]
        e_wh = fhmm.energy_wh(grid_ts, pred_power, int(grid_ts[0]), int(grid_ts[-1]) + 1)
        # attributed energy: the Wh the device's claims account for
        attributed_wh += e_wh
        out["per_device"][device] = {
            "mae_w": None if mae_w is None else round(mae_w, 2),
            "nmae": None if (mae_w is None or not den_w) else round(mae_w / den_w, 4),
            "energy_wh": round(e_wh, 1)}
    out["books_close"] = fhmm.energy_balance(round(total_wh, 1), round(attributed_wh, 1),
                                       round(floor_wh, 1))
    # legacy key "books_close": residual = total - attributed - floor Wh
    return out


def reduce_rows(rows: list[dict], k_grid: list[int]) -> dict:
    """Rows -> per-K aggregates over draws (mean/std across the seeded draws).

    Key order here is the serialized contract of the K-curve block; keep it.
    """
    # flow: raw rows (K-major) -> group by K -> mean/std across the seeded draws
    out = {}
    for k in k_grid:
        selected = [r for r in rows if r["k"] == k]
        # every seeded draw at this K
        if not selected:
            continue
        f1s = [r["pooled"]["f1"] for r in selected if r["pooled"]["f1"] is not None]
        span_stats = [r["span"] for r in selected if r["span"].get("n_pairs", 0)]
        agg = {
            "n_rows": len(selected),
            "pooled_f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "pooled_f1_std": round(float(np.std(f1s)), 4) if f1s else None,
            "per_device_f1_mean": {},
            "strata_f1_mean": {},
            "onset_med_s": round(float(np.median([s["onset_med_s"] for s in span_stats])), 1) if span_stats else None,
            "onset_p90_abs_s": round(float(np.median([s["onset_p90_abs_s"] for s in span_stats])), 1) if span_stats else None,
            "iou_med_med": round(float(np.median([s["iou_med"] for s in span_stats])), 3) if span_stats else None,
            "nmae_mean": {},
            "unknown_share_mean": round(float(np.mean([r["unknown_share"] for r in selected])), 4),
            "residual_share_mean": None,
        }
        residual_shares = [r["axis3"]["books_close"]["residual_share"] for r in selected
                           if r["axis3"]["books_close"]["residual_share"] is not None]
        if residual_shares:
            agg["residual_share_mean"] = round(float(np.mean(residual_shares)), 4)
        for device in selected[0]["per"].keys():
            dev_f1 = [r["per"][device]["f1"] for r in selected if r["per"][device]["f1"] is not None]
            agg["per_device_f1_mean"][device] = round(float(np.mean(dev_f1)), 4) if dev_f1 else None
            dev_nmae = [r["axis3"]["per_device"][device]["nmae"] for r in selected
                        if r["axis3"]["per_device"][device]["nmae"] is not None]
            agg["nmae_mean"][device] = round(float(np.mean(dev_nmae)), 4) if dev_nmae else None
            for stratum_name in ("solo", "co"):
                stratum_f1 = [r["strata"][stratum_name]["f1"] for r in selected
                              if r["strata"][stratum_name]["f1"] is not None]
                agg["strata_f1_mean"].setdefault(stratum_name, {})[device] = \
                    round(float(np.mean(stratum_f1)), 4) if stratum_f1 else None
        out[str(k)] = agg
    return out


def window_grids(ts_all: np.ndarray, w_all: np.ndarray, t0: int, t1: int,
                 cad_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Full series + window grid for a cadence (native slices, 60 s re-buckets)."""
    # flow: full series -> (native: searchsorted slice | 60 s: bucket then mask)
    #   -> (full_ts, full_w, grid_ts, grid_w)
    if cad_name == "60":
        bucket_ts, bucket_w = fhmm.bucket_mean(ts_all, w_all, CAD_60S)
        m = (bucket_ts >= t0) & (bucket_ts < t1)
        return bucket_ts, bucket_w, bucket_ts[m], bucket_w[m]
    i0 = int(np.searchsorted(ts_all, t0, side="left"))
    i1 = int(np.searchsorted(ts_all, t1, side="right"))
    return ts_all, w_all, ts_all[i0:i1], w_all[i0:i1]


# ---------------------------------------------------------------- EM ablation


def em_fit(ts: np.ndarray, w: np.ndarray, t0_us: int, t1_us: int,
           devices: list[str], floor_w: float, sigma_off_w: float,
           rng: np.random.Generator, restarts: int = 2,
           iters: int = 3) -> dict | None:
    """Unsupervised factorial EM on the aggregate: soft-count emissions,
    Viterbi-training transitions; best restart by loglik. mu/sd/p are
    per-component at the native cadence.
    """
    # flow: pre-split aggregate watts -> mus seeded at power percentiles ->
    #   [decode -> posterior-weighted update] x iters; best-loglik restart wins
    n_dev = len(devices)
    g0 = int(np.searchsorted(ts, t0_us, side="left"))
    g1 = int(np.searchsorted(ts, t1_us, side="right"))
    obs = (w[g0:g1] - floor_w).astype(np.float32)
    pcts = [60, 75, 88, 96, 99.5] + [100] * max(n_dev - 5, 0)
    qs = np.percentile(obs, pcts[:n_dev])
    # seed the mus spread across the observed level distribution
    best = None
    for restart in range(restarts):
        mu = (qs + rng.uniform(-30, 30, n_dev)).astype(np.float32)
        sd = np.full(n_dev, 20.0, np.float32)
        p_on = np.full(n_dev, 0.99, np.float32)
        params = {"mu": mu[None, :], "sd": sd[None, :], "p_on_stay": p_on[None, :],
                  "sigma_off": np.array([sigma_off_w], np.float32), "floor_w": floor_w}
        loglik = None
        for it in range(iters):
            dec = fhmm.decode_batch(ts, w, t0_us, t1_us, devices, params, CAD_NATIVE)
            loglik = float(dec["loglik"][0])
            log("    em restart", restart, "iter", it, "ll", round(loglik, 1))
            for di in range(n_dev):
                gamma = dec["marg"][:, 0, di].astype(np.float64)
                # M step, device di: posterior-weighted mean/sd of the watts
                mass = gamma.sum()
                if mass < 10:
                    continue
                mu[di] = np.float32((gamma * obs).sum() / mass)
                resid2 = float((gamma * (obs - mu[di]) ** 2).sum() / mass)
                sd[di] = np.float32(max(np.sqrt(max(resid2, 0.0)), fhmm.FROZEN["sigma_floor_w"]))
                z = dec["on"][:, 0, di] == 1
                # Viterbi-training step: hard-state transitions -> empirical p_on
                stays = int((z[:-1] & z[1:]).sum())
                flips = int((z[:-1] & ~z[1:]).sum()) + int((~z[:-1] & z[1:]).sum())
                p_on[di] = np.float32(min(max(stays / max(stays + flips, 1), 0.5), 0.9999))
        if best is None or (loglik is not None and loglik > best["loglik"]):
            best = {"loglik": loglik, "mu": mu.copy(), "sd": sd.copy(),
                    "p_on_stay": p_on.copy()}
    return best


def hungarian_match(mu_em: np.ndarray, mu_hat: np.ndarray) -> np.ndarray:
    """Match EM components to enrolled devices by level (analysis-only).

    Returns, for each EM component index, the enrolled-device index it is
    assigned to; callers index it as component_of_device[dev_idx].
    """
    from scipy.optimize import linear_sum_assignment
    # flow: |component mu - device mu| cost matrix -> 1:1 min-cost assignment
    cost = np.abs(np.asarray(mu_em)[:, None] - np.asarray(mu_hat)[None, :])
    _rows, component_of_col = linear_sum_assignment(cost)
    return component_of_col


# ------------------------------------------------------------ run scaffolding


@dataclass(frozen=True)
class CadenceSetup:
    """One cadence of one house: grid, background and energy book-ends.

    Resolving this once per arm removes the three-way duplication the arms
    used to carry; is_60s drives every native-vs-60 s branch in the arms.
    """
    name: str
    step_s: float
    tau_us: int
    is_60s: bool
    floor_w: float
    sigma_off_w: float
    full_ts: np.ndarray
    full_w: np.ndarray
    grid_ts: np.ndarray
    grid_w: np.ndarray
    total_wh: float
    floor_wh: float


@dataclass(frozen=True)
class HouseRun:
    """House-level inputs every arm shares, loaded once per house."""
    house: str
    cfg: dict
    devices: list[str]
    k_grid: list[int]
    n_draws: int
    n_rows: int
    t0_us: int
    t1_us: int
    split_us: int
    ts_all: np.ndarray
    w_all: np.ndarray
    floor_w: float
    sigma_off_w: float
    params: Params
    session_yield: list[dict]
    gt_eps: dict[str, pd.DataFrame]
    gt_power_by_device: dict[str, pd.DataFrame]


def cadence_setup(ts_all: np.ndarray, w_all: np.ndarray, cad_name: str,
                  t0: int, t1: int, split: int, floor_w: float,
                  sigma_off_w: float) -> CadenceSetup:
    """Resolve one cadence: step, match tolerance, background, grids, energy.

    The 60 s cadence re-estimates floor/noise on the bucketed series (ambient
    noise shrinks by sqrt(6/60)); the native cadence carries the house values.
    """
    # flow: cadence name -> step, tau, floor/noise (re-estimated at 60 s),
    #   full + window grids, and the window's energy book-ends
    is_60s = cad_name == "60"
    step_s = CAD_60S if is_60s else CAD_NATIVE
    if is_60s:
        step_floor_w, step_sigma_off_w = floor_noise_60s(ts_all, w_all, split)
    else:
        step_floor_w, step_sigma_off_w = floor_w, sigma_off_w
    full_ts, full_w, grid_ts, grid_w = window_grids(ts_all, w_all, t0, t1, cad_name)
    total_wh = fhmm.energy_wh(grid_ts, grid_w, int(grid_ts[0]), int(grid_ts[-1]) + 1)
    floor_wh = step_floor_w * len(grid_ts) * step_s / 3600.0
    # floor Wh = floor W x window seconds / 3600 (the always-on book-end)
    return CadenceSetup(name=cad_name, step_s=step_s, tau_us=TAU_US[cad_name],
                        is_60s=is_60s, floor_w=step_floor_w,
                        sigma_off_w=step_sigma_off_w, full_ts=full_ts, full_w=full_w,
                        grid_ts=grid_ts, grid_w=grid_w, total_wh=total_wh,
                        floor_wh=floor_wh)


def prepare_house(house: str, n_draws: int) -> HouseRun:
    """Load one house and build everything its three arms share.

    Scoring window starts at the frozen split; house_1 is capped to the first
    12 months, other houses run to the end of the mains series.
    """
    # flow: dataset + house -> rules, split, floor/noise, mains series, GT
    #   episodes, GT power, per-(K, draw) parameter rows -> HouseRun
    cfg = fhmm.house_config(DATASET, house)
    split = cfg["split_us"]
    floor_noise = fhmm.estimate_floor_noise(DATASET, house, split)
    floor_w, sigma_off_w = floor_noise["floor_w"], floor_noise["sigma_off_w"]
    # native-cadence floor/noise: the frozen estimator on the pre-split span
    t0 = split
    mains = load_power_series(gold_parquet_path(DATASET, house, "mains"))
    t1 = split + YEAR_US if house == "house_1" else int(mains["ts_us"].iloc[-1]) + 1
    ts_all = mains["ts_us"].to_numpy(np.int64)
    w_all = mains["w"].to_numpy(float)
    log(house, "window days", round((t1 - t0) / DAY_US, 1),
        "| floor", round(floor_w, 1), "W, sig_off", round(sigma_off_w, 1), "W")
    gt_eps = gt_eps_by_device(DATASET, house, cfg, t0, t1)
    gt_power_by_device = {}
    for device in ENROLLED[house]:
        df = load_power_series(gold_parquet_path(DATASET, house, device))
        gt_power_by_device[device] = df[(df.ts_us >= t0) & (df.ts_us < t1)].reset_index(drop=True)
    k_grid = list(fhmm.FROZEN["k_grid"])
    params, _press_pools, yield_rows, devices = build_param_rows(
        DATASET, house, cfg, ts_all, w_all, floor_w, sigma_off_w,
        k_grid, n_draws, fhmm.FROZEN["interference_max_cover"])
    n_rows = len(k_grid) * n_draws
    return HouseRun(house=house, cfg=cfg, devices=devices, k_grid=k_grid,
                    n_draws=n_draws, n_rows=n_rows, t0_us=int(t0), t1_us=int(t1),
                    split_us=int(split), ts_all=ts_all, w_all=w_all,
                    floor_w=floor_w, sigma_off_w=sigma_off_w, params=params,
                    session_yield=yield_rows, gt_eps=gt_eps, gt_power_by_device=gt_power_by_device)


def score_decode_row(run: HouseRun, setup: CadenceSetup, decode: dict,
                     batch_idx: int, mu_row: np.ndarray) -> dict:
    """Score one decoded batch: episodes -> the metric bundle both B1 and B0
    report.

    Shared by the K-curve and EM arms, which differ only in how mu_row is
    obtained. The bundle is returned in a fixed key order; each arm builds
    its own output dict so the serialized key order per arm stays explicit.
    """
    # flow: one decoded batch row -> episodes -> the shared metric bundle
    #   (per-device, pooled, span, strata, axis3)
    dev_params = {device: {"mu_w": float(mu_row[d_i])} for d_i, device in enumerate(run.devices)}
    dwell = {device: run.cfg["devices"][device]["dwell_s"] for device in run.devices}
    merge = {device: int(run.cfg["devices"][device]["merge_s"] * 1e6) for device in run.devices}
    pred = fhmm.spans_to_episodes(decode, batch_idx, run.devices, dev_params, merge, dwell,
                               setup.step_s)
    per_device, pooled = score_row(pred, run.gt_eps, setup.tau_us, run.devices)
    strata = strata_scores(pred, run.gt_eps, setup.tau_us, run.devices)
    pred_power = {device: fhmm.pred_power_series(decode, batch_idx, d_i, float(mu_row[d_i]))
                  for d_i, device in enumerate(run.devices)}
    return {
        "pooled": pooled,
        "per": per_device,
        "span": row_span(per_device),
        "strata": strata,
        "axis3": axis3(pred_power, setup.grid_ts, setup.grid_w, run.gt_power_by_device,
                       setup.step_s, setup.is_60s, setup.total_wh, setup.floor_wh),
    }


def run_anchor_arm(run: HouseRun, cadences: list[str]) -> dict:
    """A0: per-device threshold + dwell episodes on the raw aggregate.

    The anchor asserts intervals, not levels: inside its spans the claimed
    power series is the aggregate itself, which double-counts overlapping
    devices. That is deliberate and why the energy balance is part of the surface.
    """
    # flow: per cadence: threshold+hysteresis episodes per device -> score
    #   bundle, keyed by cadence name
    anchor = {}
    for cad_name in cadences:
        setup = cadence_setup(run.ts_all, run.w_all, cad_name, run.t0_us, run.t1_us,
                              run.split_us, run.floor_w, run.sigma_off_w)
        pred = pd.DataFrame(columns=["device", "t_on_us", "t_off_us", "mu_w"])
        for device in run.devices:
            rule = run.cfg["devices"][device]
            eps = fhmm.anchor_episodes(setup.full_ts, setup.full_w, run.t0_us, run.t1_us,
                                  rule["thr_w"], rule["dwell_s"], rule["merge_s"], setup.step_s)
            eps["device"] = device
            pred = pd.concat([pred, eps], ignore_index=True)
        per_device, pooled = score_row(pred, run.gt_eps, setup.tau_us, run.devices)
        strata = strata_scores(pred, run.gt_eps, setup.tau_us, run.devices)
        pred_power_by_device = {}
        for device in run.devices:
            episodes = pred[pred["device"] == device]
            # each claimed span copies the aggregate watts (double-count by design)
            series = np.zeros(len(setup.grid_ts))
            for on_us, off_us in zip(episodes["t_on_us"].to_numpy(np.int64),
                                     episodes["t_off_us"].to_numpy(np.int64)):
                j0 = int(np.searchsorted(setup.grid_ts, on_us, side="left"))
                j1 = int(np.searchsorted(setup.grid_ts, off_us, side="right"))
                series[j0:j1] = setup.grid_w[j0:j1]
            pred_power_by_device[device] = series
        a3 = axis3(pred_power_by_device, setup.grid_ts, setup.grid_w, run.gt_power_by_device,
                   setup.step_s, setup.is_60s, setup.total_wh, setup.floor_wh)
        anchor[cad_name] = {"pooled": pooled, "per_device": per_device,
                            "strata": strata, "axis3": a3,
                            "span": row_span(per_device)}
        log("  anchor", cad_name, "| pooled F1", pooled["f1"],
            "| onset med", anchor[cad_name]["span"].get("onset_med_s"))
    return anchor


def run_kcurve_arm(run: HouseRun, cadences: list[str], slice_rows: int) -> dict:
    """B1: session-supervised parameters swept over K x seeded draws.

    One decode covers slice_rows parameter rows at a time to bound memory;
    metrics are reduced per slice and concatenated before the per-K reduction.
    """
    # flow: per cadence: decode slice_rows parameter rows per pass -> score
    #   each row -> rows list -> per-K reduction
    kcurve = {}
    for cad_name in cadences:
        setup = cadence_setup(run.ts_all, run.w_all, cad_name, run.t0_us, run.t1_us,
                              run.split_us, run.floor_w, run.sigma_off_w)
        if setup.is_60s:
            rows_params = params_at_60s(run.params, run.sigma_off_w, setup.sigma_off_w)
        else:
            rows_params = run.params
        rows = []
        for b0 in range(0, run.n_rows, slice_rows):
            b1 = min(b0 + slice_rows, run.n_rows)
            sl = {k: v[b0:b1].copy() for k, v in rows_params.items()}
            # one slice = slice_rows parameter sets, decoded in one shared pass
            sl["floor_w"] = setup.floor_w
            if setup.is_60s:
                sl["p_on_stay"] = rescale_p_on(sl["p_on_stay"], CAD_NATIVE, setup.step_s)
            dec = fhmm.decode_batch(setup.full_ts, setup.full_w, run.t0_us, run.t1_us,
                                 run.devices, sl, setup.step_s)
            for batch_idx in range(b1 - b0):
                bi = b0 + batch_idx
                k = run.k_grid[bi // run.n_draws]
                # flat row index -> (K, draw): K = bi // n_draws, draw = bi % n_draws
                bundle = score_decode_row(run, setup, dec, batch_idx, sl["mu"][batch_idx])
                rows.append({"k": k, "draw": bi % run.n_draws,
                             "pooled": bundle["pooled"], "per": bundle["per"],
                             "span": bundle["span"], "strata": bundle["strata"],
                             "axis3": bundle["axis3"],
                             "unknown_share": fhmm.unknown_share(dec, batch_idx, setup.grid_w)})
            log("  kcurve", cad_name, "rows", b1, "/", run.n_rows,
                "| F1 K=" + str(rows[-1]["k"]), rows[-1]["pooled"]["f1"])
        kcurve[cad_name] = reduce_rows(rows, run.k_grid)
        log("  kcurve", cad_name, "done")
    return kcurve


def run_em_arm(run: HouseRun, cadences: list[str]) -> dict:
    """B0: unsupervised factorial EM on the aggregate, one draw, no sessions.

    Trained on the 30 days before the split, then matched to enrolled devices
    by level (hungarian_match) so the ablation reads the same metric surface.
    """
    # flow: EM on the 30 pre-split days -> components -> matched to enrolled
    #   devices by level -> decoded + scored per cadence
    tr0, tr1 = run.split_us - 30 * DAY_US, run.split_us
    best = em_fit(run.ts_all, run.w_all, tr0, tr1, run.devices, run.floor_w,
                  run.sigma_off_w,
                  np.random.default_rng(fhmm.FROZEN["seed_base"] + 1))
    mu_hat = run.params["mu"][-1]
    # reference levels: the final (K, draw) row of the session params
    component_of_device = hungarian_match(best["mu"], mu_hat)
    # per enrolled device: the EM component that shares its level
    em_out: dict[str, object] = {}
    em_out["train"] = {
        "t0_us": int(tr0), "t1_us": int(tr1), "loglik": best["loglik"],
        "components_mu_w": [round(float(x), 1) for x in best["mu"]],
        "components_sd_w": [round(float(x), 1) for x in best["sd"]],
        "match_component_per_device": {device: int(component_of_device[d_i])
                                       for d_i, device in enumerate(run.devices)},
    }
    log("  em train ll", round(best["loglik"], 1),
        "| components", [round(float(x), 1) for x in best["mu"]])
    for cad_name in cadences:
        setup = cadence_setup(run.ts_all, run.w_all, cad_name, run.t0_us, run.t1_us,
                              run.split_us, run.floor_w, run.sigma_off_w)
        mu_m = np.array([[best["mu"][component_of_device[d_i]]
                          for d_i in range(len(run.devices))]], np.float32)
        sd_m = np.array([[best["sd"][component_of_device[d_i]]
                          for d_i in range(len(run.devices))]], np.float32)
        po_m = np.array([[best["p_on_stay"][component_of_device[d_i]]
                          for d_i in range(len(run.devices))]], np.float32)
        if setup.is_60s:
            po_m = rescale_p_on(po_m, CAD_NATIVE, setup.step_s)
            sd_m = params_at_60s({"sd": sd_m}, run.sigma_off_w, setup.sigma_off_w)["sd"]
            # 60 s arm: rescale p_on_stay and shrink the ambient sd, as in B1
        pm = {"mu": mu_m, "sd": sd_m, "p_on_stay": po_m,
              "sigma_off": np.array([setup.sigma_off_w], np.float32),
              "floor_w": setup.floor_w}
        dec = fhmm.decode_batch(setup.full_ts, setup.full_w, run.t0_us, run.t1_us,
                             run.devices, pm, setup.step_s)
        bundle = score_decode_row(run, setup, dec, 0, mu_m[0])
        em_out[cad_name] = {"pooled": bundle["pooled"], "per_device": bundle["per"],
                            "strata": bundle["strata"], "axis3": bundle["axis3"],
                            "span": bundle["span"],
                            "unknown_share": fhmm.unknown_share(dec, 0, setup.grid_w)}
        log("  em", cad_name, "| pooled F1", bundle["pooled"]["f1"])
    return em_out


def write_metrics(house: str, metrics: Metrics) -> str:
    """Dump the metric bundle to docs/reports/fhmm/metrics_kcurve_<house>.json."""
    # flow: metric bundle -> numpy stripped -> one JSON per house
    out_path = "docs/reports/fhmm/metrics_kcurve_" + house + ".json"
    with open(out_path, "w") as fh:
        json.dump(fhmm.jsonable(metrics), fh, indent=1)
    log("wrote", out_path)
    return out_path


def run_house(house: str, cadences: list[str], slice_rows: int, n_draws: int,
              skip_em: bool) -> str:
    """Run all three arms for one house and write its metrics JSON.

    Arm key order in the output is anchor, kcurve, em - the report order.
    """
    # flow: load once -> arms in report order (anchor, kcurve, em) -> write JSON
    run = prepare_house(house, n_draws)
    arms: dict[str, object] = {}
    metrics: Metrics = {
        "house": house,
        "window": {"t0_us": run.t0_us, "t1_us": run.t1_us,
                   "days": round((run.t1_us - run.t0_us) / DAY_US, 1)},
        "floor_w": round(run.floor_w, 2), "sigma_off_w": round(run.sigma_off_w, 2),
        "session_yield": run.session_yield, "arms": arms}
    arms["anchor"] = run_anchor_arm(run, cadences)
    arms["kcurve"] = run_kcurve_arm(run, cadences, slice_rows)
    if not skip_em:
        arms["em"] = run_em_arm(run, cadences)
    return write_metrics(house, metrics)


def main() -> None:
    """CLI entry point: one metrics JSON per house named by --houses."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--houses", default="house_2,house_5")
    ap.add_argument("--cadences", default="native,60")
    ap.add_argument("--slice", type=int, default=16)
    ap.add_argument("--draws", type=int, default=fhmm.FROZEN["n_draws"])
    ap.add_argument("--skip-em", action="store_true")
    args = ap.parse_args()
    for house in args.houses.split(","):
        run_house(house.strip(), args.cadences.split(","), args.slice,
                  args.draws, args.skip_em)


if __name__ == "__main__":
    main()
