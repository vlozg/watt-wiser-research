"""E2E experiment runner: anchor (A0), session-supervised FHMM K-curve (B1),
EM ablation (B0) - plan arms, frozen protocol.

Per house writes docs/reports/fhmm/metrics_kcurve_<house>.json with the
three-axis surface per arm/K/draw: pooled + per-device episode F1, span
stats pooled over matched pairs (overall + solo/co-occurring strata),
nMAE, whole-span energy (books-close), unknown share, session yield.

Conventions (frozen):
- evaluation GT = submeter episodes via build_episodes + the profile rule;
  scoring window = post-split (house_1: first 12 months); submeters are
  evaluation-only, every model reads the aggregate.
- axis 3 power series: B1/EM claim mu_w while claimed ON; the anchor
  claims the aggregate restricted to its spans (it asserts intervals,
  not levels), so its overlap double-counts - visible in books-close.
- B1 decodes parameter rows in slices to bound memory; metrics reduce
  per slice. p_on_stay is rescaled for the 60 s rung (same dwell).

Run: .venv/bin/python3 src/experiments/01_fhmm/02_run_kcurve.py
      --houses house_2,house_5 [--cadences native,60] [--skip-em]
      [--slice 16] [--draws 20]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '00_baseline'))
import baseline_lib as bl  # noqa: E402
import fhmm_lib as f  # noqa: E402

DATASET = "ukdale"
ENROLLED = {
    "house_1": ["washing_machine", "kettle", "microwave", "fridge"],
    "house_2": ["washing_machine", "dishwasher", "kettle", "microwave", "fridge"],
    "house_5": ["washing_machine", "dishwasher", "kettle", "fridge"],
}
CAD_NATIVE = 6.0
CAD_RUNG = 60.0
DWELL_BAND = f.FROZEN["dwell_band"]
MONTH_US = 30 * 24 * 3600 * 1_000_000
YEAR_US = 365 * 24 * 3600 * 1_000_000
DAY_US = 24 * 3600 * 1_000_000


def log(*a):
    print(*a, flush=True)


def rescale_p_on(p_on: np.ndarray, cad_from: float, cad_to: float) -> np.ndarray:
    """Same expected dwell in seconds at a coarser step grid."""
    q = (1.0 - p_on.astype(np.float64)) * (cad_from / cad_to)
    return (1.0 - q).astype(np.float32)


def rung_background(ts_all: np.ndarray, w_all: np.ndarray, split_us: int):
    """The frozen background estimator (p10 floor, 1.4826 x MAD) applied to
    the 60 s bucket-mean observation: ambient noise shrinks by sqrt(6/60)
    when the series is averaged, so the rung sigma_off must be re-estimated
    on the rung series, not carried over from the native cadence."""
    r_ts, r_w = f.to_rung(ts_all, w_all, CAD_RUNG)
    pre = r_w[r_ts < split_us]
    floor = float(np.percentile(pre, 10))
    resid = pre - floor
    mad = float(np.median(np.abs(resid - np.median(resid))))
    return floor, max(1.4826 * mad, 1.0)


def rung_params(params: dict, sig_native: float, sig_rung: float) -> dict:
    """Emission widths at the 60 s observation scale: device session sd is
    phase spread plus ambient; only the ambient component shrinks with
    bucket-meaning. Levels are unchanged (bucket-means preserve means)."""
    out = dict(params)
    sd6 = params["sd"].astype(np.float64)**2
    excess = np.maximum(sd6 - sig_native**2, 0.0)
    out["sd"] = np.sqrt(excess + sig_rung**2).astype(np.float32)
    if "sigma_off" in out:
        out["sigma_off"] = np.full(len(params["sigma_off"]), sig_rung, np.float32)
    return out


# ---------------------------------------------------------------- sessions


def build_param_rows(dataset, house, cfg, ts, w, floor_w, sig_off,
                     k_grid, n_draws, cover):
    """Per (K, draw) parameter rows: mu/sd/p_on_stay per enrolled device.
    Fridge is the fixed passive profile in every row (K-independent). Rows
    where a device has no separable session level get mu = floor (never
    claims) and the profile dwell prior; the yield is recorded."""
    split = cfg["split_us"]
    devices = ENROLLED[house]
    D = len(devices)
    pools = {dev: f.press_pool(dataset, house, dev, split) for dev in devices}
    passive = {}
    for dev in devices:
        if dev == "fridge":
            passive[dev] = f.fridge_passive_params(
                dataset, house, cfg["devices"][dev], floor_w, sig_off,
                split, CAD_NATIVE)
    B = len(k_grid) * n_draws
    mu = np.zeros((B, D), np.float32)
    sd = np.zeros((B, D), np.float32)
    p_on = np.zeros((B, D), np.float32)
    sigma_off = np.full(B, sig_off, np.float32)
    yield_rows = []
    i = 0
    for k in k_grid:
        for r in range(n_draws):
            rng = np.random.default_rng([f.FROZEN["seed_base"], k, r])
            for d_i, dev in enumerate(devices):
                if dev == "fridge":
                    p = passive.get(dev)
                    if p is None:
                        mu[i, d_i] = floor_w
                        sd[i, d_i] = f.FROZEN["sigma_floor_w"]
                        p_on[i, d_i] = 1.0 - CAD_NATIVE / 86400.0
                    else:
                        mu[i, d_i] = p["mu_w"]
                        sd[i, d_i] = p["sd_w"]
                        p_on[i, d_i] = p["p_on_stay"]
                    continue
                dwell_prof = cfg["devices"][dev]["dwell_s"]
                pool = pools[dev]
                if len(pool) == 0:
                    mu[i, d_i] = floor_w
                    sd[i, d_i] = f.FROZEN["sigma_floor_w"]
                    p_on[i, d_i] = 1.0 - CAD_NATIVE / dwell_prof
                    yield_rows.append({"k": k, "draw": r, "device": dev,
                                       "valid": 0, "attempts": 0})
                    continue
                others = {o: q for o, q in pools.items() if o != dev and len(q)}
                valid, att = f.sample_valid_sessions(pool, k, rng, others, cover)
                est = f.estimate_device_params(ts, w, floor_w, valid, CAD_NATIVE)
                if est is None:
                    mu[i, d_i] = floor_w
                    sd[i, d_i] = f.FROZEN["sigma_floor_w"]
                    p_on[i, d_i] = 1.0 - CAD_NATIVE / dwell_prof
                else:
                    mu[i, d_i] = est["mu_w"]
                    sd[i, d_i] = est["sd_w"]
                    p_on[i, d_i] = est["p_on_stay"]
                yield_rows.append({"k": k, "draw": r, "device": dev,
                                   "valid": int(len(valid)), "attempts": int(att)})
            i += 1
    params = {"mu": mu, "sd": sd, "p_on_stay": p_on, "sigma_off": sigma_off}
    return params, pools, yield_rows, devices


# ---------------------------------------------------------------- scoring


def gt_by_dev(dataset, house, cfg, t0, t1):
    out = {}
    for dev in ENROLLED[house]:
        out[dev] = f.eval_episodes(dataset, house, dev, cfg["devices"][dev], t0, t1)
    return out


def score_row(pred_eps, gt_eps, tau_us, devices):
    """Per-device score dicts + pooled P/R/F1 over scored devices."""
    per = {}
    for dev in devices:
        if len(pred_eps):
            p = pred_eps[pred_eps["device"] == dev].reset_index(drop=True)
        else:
            p = pred_eps
        per[dev] = f.score_device(p, gt_eps[dev].reset_index(drop=True),
                                  tau_us, DWELL_BAND)
    scored = [per[d] for d in devices if per[d]["n_gt"] or per[d]["n_pred"]]
    if scored:
        pooled = f.pooled_prf(scored)
    else:
        pooled = {"n_pred": 0, "n_gt": 0, "n_matched": 0,
                  "precision": None, "recall": None, "f1": None}
    return per, pooled


def row_span(per):
    spans = [s["span"] for s in per.values() if s.get("span")]
    if not spans:
        return {"n_pairs": 0}
    return f.collect_span([{"span": s} for s in spans])


def strata_scores(pred_eps, gt_eps, tau_us, devices):
    """Solo vs co-occurring pooled counts (preds inherit the stratum of
    their matched GT episode; unmatched preds are not attributed)."""
    res = {"solo": {"n_pred": 0, "n_gt": 0, "n_matched": 0},
           "co": {"n_pred": 0, "n_gt": 0, "n_matched": 0}}
    for dev in devices:
        g = gt_eps[dev].reset_index(drop=True)
        p = pred_eps[pred_eps["device"] == dev].reset_index(drop=True) if len(pred_eps) else pred_eps
        if g.empty:
            continue
        tag = f.tag_cooccurring(gt_eps, dev)
        res["solo"]["n_gt"] += int((~tag).sum())
        res["co"]["n_gt"] += int(tag.sum())
        if len(p) == 0:
            continue
        gt_on = g["t_on_us"].to_numpy(np.int64)
        gt_off = g["t_off_us"].to_numpy(np.int64)
        pr_on = p["t_on_us"].to_numpy(np.int64)
        pr_off = p["t_off_us"].to_numpy(np.int64)
        gi, pi = bl.match_onsets(gt_on, pr_on, tau_us)
        if len(gi) == 0:
            continue
        ratio = (pr_off[pi] - pr_on[pi]) / np.maximum(gt_off[gi] - gt_on[gi], 1)
        keep = (ratio >= DWELL_BAND[0]) & (ratio <= DWELL_BAND[1])
        for gk in gi[keep]:
            res["co" if tag[gk] else "solo"]["n_matched"] += 1
    for st in res.values():
        st["n_pred"] = st["n_matched"]
        p, r, f1 = bl.prf(st["n_matched"], st["n_pred"], st["n_gt"])
        st.update({"precision": p, "recall": r, "f1": f1})
    return res


def align_rung(dev_ts, dev_w, grid_ts, cad):
    """Bucket-mean the device series onto the mains rung grid."""
    bs = int(cad * 1e6)
    half = bs // 2
    gids = (grid_ts - half) // bs
    dids = dev_ts // bs
    pos = np.searchsorted(gids, dids)
    pos_c = np.minimum(pos, len(gids) - 1)
    ok = (pos < len(gids)) & (gids[pos_c] == dids)
    acc = np.zeros(len(grid_ts))
    cnt = np.zeros(len(grid_ts))
    np.add.at(acc, pos_c[ok], dev_w[ok])
    np.add.at(cnt, pos_c[ok], 1.0)
    return acc / np.maximum(cnt, 1.0)


def axis3(pred_power_by_dev, grid_ts, agg_w, gt_dev_raw, cad, rung,
          total_wh, floor_wh):
    """nMAE + per-device attributed energy + books-close."""
    den = float(np.mean(agg_w)) if len(agg_w) else float("nan")
    out = {"den_w": round(den, 2), "per_device": {}}
    attrib = 0.0
    for dev, pp in pred_power_by_dev.items():
        if rung:
            gt_r = align_rung(gt_dev_raw[dev]["ts_us"].to_numpy(np.int64),
                              gt_dev_raw[dev]["w"].to_numpy(float), grid_ts, cad)
            mae = float(np.abs(pp - gt_r).mean())
        else:
            r = f.nmae_for_device(grid_ts, pp, gt_dev_raw[dev], agg_w)
            mae = r["mae_w"]
        e_wh = f.energy_wh(grid_ts, pp, int(grid_ts[0]), int(grid_ts[-1]) + 1)
        attrib += e_wh
        out["per_device"][dev] = {"mae_w": None if mae is None else round(mae, 2),
                                  "nmae": None if (mae is None or not den) else round(mae / den, 4),
                                  "energy_wh": round(e_wh, 1)}
    out["books_close"] = f.books_close(round(total_wh, 1), round(attrib, 1),
                                       round(floor_wh, 1))
    return out


def reduce_rows(rows, k_grid):
    """Rows -> per-K aggregates over draws."""
    out = {}
    for k in k_grid:
        sel = [r for r in rows if r["k"] == k]
        if not sel:
            continue
        f1s = [r["pooled"]["f1"] for r in sel if r["pooled"]["f1"] is not None]
        sp = [r["span"] for r in sel if r["span"].get("n_pairs", 0)]
        agg = {
            "n_rows": len(sel),
            "pooled_f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "pooled_f1_std": round(float(np.std(f1s)), 4) if f1s else None,
            "per_device_f1_mean": {},
            "strata_f1_mean": {},
            "onset_med_s": round(float(np.median([s["onset_med_s"] for s in sp])), 1) if sp else None,
            "onset_p90_abs_s": round(float(np.median([s["onset_p90_abs_s"] for s in sp])), 1) if sp else None,
            "iou_med_med": round(float(np.median([s["iou_med"] for s in sp])), 3) if sp else None,
            "nmae_mean": {},
            "unknown_share_mean": round(float(np.mean([r["unknown_share"] for r in sel])), 4),
            "residual_share_mean": None,
        }
        rs = [r["axis3"]["books_close"]["residual_share"] for r in sel
              if r["axis3"]["books_close"]["residual_share"] is not None]
        if rs:
            agg["residual_share_mean"] = round(float(np.mean(rs)), 4)
        for dev in sel[0]["per"].keys():
            f1d = [r["per"][dev]["f1"] for r in sel if r["per"][dev]["f1"] is not None]
            agg["per_device_f1_mean"][dev] = round(float(np.mean(f1d)), 4) if f1d else None
            nm = [r["axis3"]["per_device"][dev]["nmae"] for r in sel
                  if r["axis3"]["per_device"][dev]["nmae"] is not None]
            agg["nmae_mean"][dev] = round(float(np.mean(nm)), 4) if nm else None
            for st in ("solo", "co"):
                fs = [r["strata"][st]["f1"] for r in sel if r["strata"][st]["f1"] is not None]
                agg["strata_f1_mean"].setdefault(st, {})[dev] = \
                    round(float(np.mean(fs)), 4) if fs else None
        out[str(k)] = agg
    return out


def window_grids(ts_all, w_all, t0, t1, cad_name):
    """Full series + window grid for a cadence."""
    if cad_name == "60":
        r_ts, r_w = f.to_rung(ts_all, w_all, CAD_RUNG)
        m = (r_ts >= t0) & (r_ts < t1)
        return r_ts, r_w, r_ts[m], r_w[m]
    i0 = int(np.searchsorted(ts_all, t0, side="left"))
    i1 = int(np.searchsorted(ts_all, t1, side="right"))
    return ts_all, w_all, ts_all[i0:i1], w_all[i0:i1]


# ---------------------------------------------------------------- EM ablation


def em_fit(ts, w, t0_us, t1_us, devices, floor_w, sig_off, rng,
           restarts=2, iters=3):
    """Unsupervised factorial EM on the aggregate: soft-count emissions,
    Viterbi-training transitions; best restart by loglik. mu/sd/p are
    per-component at the native cadence."""
    D = len(devices)
    g0 = int(np.searchsorted(ts, t0_us, side="left"))
    g1 = int(np.searchsorted(ts, t1_us, side="right"))
    obs = (w[g0:g1] - floor_w).astype(np.float32)
    pcts = [60, 75, 88, 96, 99.5] + [100] * max(D - 5, 0)
    qs = np.percentile(obs, pcts[:D])
    best = None
    for restart in range(restarts):
        mu = (qs + rng.uniform(-30, 30, D)).astype(np.float32)
        sd = np.full(D, 20.0, np.float32)
        p_on = np.full(D, 0.99, np.float32)
        params = {"mu": mu[None, :], "sd": sd[None, :], "p_on_stay": p_on[None, :],
                  "sigma_off": np.array([sig_off], np.float32), "floor_w": floor_w}
        ll = None
        for it in range(iters):
            dec = f.decode_batch(ts, w, t0_us, t1_us, devices, params, CAD_NATIVE)
            ll = float(dec["loglik"][0])
            log("    em restart", restart, "iter", it, "ll", round(ll, 1))
            for d in range(D):
                gam = dec["marg"][:, 0, d].astype(np.float64)
                s = gam.sum()
                if s < 10:
                    continue
                mu[d] = np.float32((gam * obs).sum() / s)
                resid2 = float((gam * (obs - mu[d]) ** 2).sum() / s)
                sd[d] = np.float32(max(np.sqrt(max(resid2, 0.0)), f.FROZEN["sigma_floor_w"]))
                z = dec["on"][:, 0, d] == 1
                stays = int((z[:-1] & z[1:]).sum())
                flips = int((z[:-1] & ~z[1:]).sum()) + int((~z[:-1] & z[1:]).sum())
                p_on[d] = np.float32(min(max(stays / max(stays + flips, 1), 0.5), 0.9999))
        if best is None or (ll is not None and ll > best["loglik"]):
            best = {"loglik": ll, "mu": mu.copy(), "sd": sd.copy(),
                    "p_on_stay": p_on.copy()}
    return best


def hungarian_match(mu_em, mu_hat):
    """Match EM components to enrolled devices by level (analysis-only)."""
    from scipy.optimize import linear_sum_assignment
    cost = np.abs(np.asarray(mu_em)[:, None] - np.asarray(mu_hat)[None, :])
    _ri, ci = linear_sum_assignment(cost)
    return ci


# ---------------------------------------------------------------- main


def run_house(house, cadences, slice_b, n_draws, skip_em):
    cfg = f.house_config(DATASET, house)
    split = cfg["split_us"]
    bg = f.background_estimates(DATASET, house, split)
    floor_w, sig_off = bg["floor_w"], bg["sigma_off_w"]
    t0 = split
    mains = bl.load_series(bl.gold_file(DATASET, house, "mains"))
    t1 = split + YEAR_US if house == "house_1" else int(mains["ts_us"].iloc[-1]) + 1
    ts_all = mains["ts_us"].to_numpy(np.int64)
    w_all = mains["w"].to_numpy(float)
    log(house, "window days", round((t1 - t0) / DAY_US, 1),
        "| floor", round(floor_w, 1), "W, sig_off", round(sig_off, 1), "W")
    gt_eps = gt_by_dev(DATASET, house, cfg, t0, t1)
    gt_dev_raw = {}
    for dev in ENROLLED[house]:
        df = bl.load_series(bl.gold_file(DATASET, house, dev))
        gt_dev_raw[dev] = df[(df.ts_us >= t0) & (df.ts_us < t1)].reset_index(drop=True)
    k_grid = list(f.FROZEN["k_grid"])
    cover = f.FROZEN["interference_max_cover"]
    params, pools, yield_rows, devices = build_param_rows(
        DATASET, house, cfg, ts_all, w_all, floor_w, sig_off,
        k_grid, n_draws, cover)
    B = len(k_grid) * n_draws
    tau_map = {"native": f.FROZEN["tau_native_s"], "60": f.FROZEN["tau_60_s"]}
    metrics = {"house": house,
               "window": {"t0_us": int(t0), "t1_us": int(t1),
                          "days": round((t1 - t0) / DAY_US, 1)},
               "floor_w": round(floor_w, 2), "sigma_off_w": round(sig_off, 2),
               "session_yield": yield_rows, "arms": {}}
    # ---------------- anchor A0
    anchor = {}
    for cad_name in cadences:
        cad = CAD_NATIVE if cad_name == "native" else CAD_RUNG
        tau_us = int(tau_map[cad_name] * 1e6)
        if cad_name == "60":
            floor_c, _sig_c = rung_background(ts_all, w_all, split)
        else:
            floor_c = floor_w
        full_ts, full_w, g_ts, g_w = window_grids(ts_all, w_all, t0, t1, cad_name)
        total_wh = f.energy_wh(g_ts, g_w, int(g_ts[0]), int(g_ts[-1]) + 1)
        floor_wh = floor_c * len(g_ts) * cad / 3600.0
        pred = pd.DataFrame(columns=["device", "t_on_us", "t_off_us", "mu_w"])
        for dev in devices:
            d = cfg["devices"][dev]
            e = f.anchor_episodes(full_ts, full_w, int(t0), int(t1),
                                  d["thr_w"], d["dwell_s"], d["merge_s"], cad)
            e["device"] = dev
            pred = pd.concat([pred, e], ignore_index=True)
        per, pooled = score_row(pred, gt_eps, tau_us, devices)
        strata = strata_scores(pred, gt_eps, tau_us, devices)
        ppow = {}
        for dev in devices:
            e = pred[pred["device"] == dev]
            p = np.zeros(len(g_ts))
            for a, bnd in zip(e["t_on_us"].to_numpy(np.int64),
                              e["t_off_us"].to_numpy(np.int64)):
                j0 = int(np.searchsorted(g_ts, a, side="left"))
                j1 = int(np.searchsorted(g_ts, bnd, side="right"))
                p[j0:j1] = g_w[j0:j1]
            ppow[dev] = p
        a3 = axis3(ppow, g_ts, g_w, gt_dev_raw, cad, cad_name == "60",
                   total_wh, floor_wh)
        anchor[cad_name] = {"pooled": pooled, "per_device": per,
                            "strata": strata, "axis3": a3,
                            "span": row_span(per)}
        log("  anchor", cad_name, "| pooled F1", pooled["f1"],
            "| onset med", anchor[cad_name]["span"].get("onset_med_s"))
    metrics["arms"]["anchor"] = anchor
    # ---------------- B1 K-curve
    kcurve = {}
    for cad_name in cadences:
        cad = CAD_NATIVE if cad_name == "native" else CAD_RUNG
        tau_us = int(tau_map[cad_name] * 1e6)
        if cad_name == "60":
            floor_c, sig_c = rung_background(ts_all, w_all, split)
            rows_params = rung_params(params, sig_off, sig_c)
        else:
            floor_c, sig_c, rows_params = floor_w, sig_off, params
        full_ts, full_w, g_ts, g_w = window_grids(ts_all, w_all, t0, t1, cad_name)
        total_wh = f.energy_wh(g_ts, g_w, int(g_ts[0]), int(g_ts[-1]) + 1)
        floor_wh = floor_c * len(g_ts) * cad / 3600.0
        rows = []
        for b0 in range(0, B, slice_b):
            b1 = min(b0 + slice_b, B)
            sl = {k: v[b0:b1].copy() for k, v in rows_params.items()}
            sl["floor_w"] = floor_c
            if cad_name == "60":
                sl["p_on_stay"] = rescale_p_on(sl["p_on_stay"], CAD_NATIVE, cad)
            dec = f.decode_batch(full_ts, full_w, int(t0), int(t1), devices, sl, cad)
            for b in range(b1 - b0):
                bi = b0 + b
                k = k_grid[bi // n_draws]
                dev_params = {dev: {"mu_w": float(sl["mu"][b, d_i])}
                              for d_i, dev in enumerate(devices)}
                dwell = {dev: cfg["devices"][dev]["dwell_s"] for dev in devices}
                merge = {dev: int(cfg["devices"][dev]["merge_s"] * 1e6)
                         for dev in devices}
                pred = f.spans_to_episodes(dec, b, devices, dev_params, merge, dwell, cad)
                per, pooled = score_row(pred, gt_eps, tau_us, devices)
                strata = strata_scores(pred, gt_eps, tau_us, devices)
                ppow = {dev: f.pred_power_series(dec, b, d_i, float(sl["mu"][b, d_i]))
                        for d_i, dev in enumerate(devices)}
                a3 = axis3(ppow, g_ts, g_w, gt_dev_raw, cad, cad_name == "60",
                           total_wh, floor_wh)
                rows.append({"k": k, "draw": bi % n_draws, "pooled": pooled,
                             "per": per, "span": row_span(per), "strata": strata,
                             "axis3": a3,
                             "unknown_share": f.unknown_share(dec, b, g_w)})
            log("  kcurve", cad_name, "rows", b1, "/", B,
                "| F1 K=" + str(k), rows[-1]["pooled"]["f1"])
        kcurve[cad_name] = reduce_rows(rows, k_grid)
        log("  kcurve", cad_name, "done")
    metrics["arms"]["kcurve"] = kcurve
    # ---------------- B0 EM ablation
    if not skip_em:
        em_out = {}
        tr0, tr1 = split - 30 * DAY_US, split
        best = em_fit(ts_all, w_all, tr0, tr1, devices, floor_w, sig_off,
                      np.random.default_rng(f.FROZEN["seed_base"] + 1))
        mu_hat = params["mu"][-1]
        ci = hungarian_match(best["mu"], mu_hat)
        em_out["train"] = {
            "t0_us": int(tr0), "t1_us": int(tr1), "loglik": best["loglik"],
            "components_mu_w": [round(float(x), 1) for x in best["mu"]],
            "components_sd_w": [round(float(x), 1) for x in best["sd"]],
            "match_component_per_device": {dev: int(ci[d_i])
                                           for d_i, dev in enumerate(devices)},
        }
        log("  em train ll", round(best["loglik"], 1),
            "| components", [round(float(x), 1) for x in best["mu"]])
        for cad_name in cadences:
            cad = CAD_NATIVE if cad_name == "native" else CAD_RUNG
            tau_us = int(tau_map[cad_name] * 1e6)
            if cad_name == "60":
                floor_c, sig_c = rung_background(ts_all, w_all, split)
            else:
                floor_c, sig_c = floor_w, sig_off
            full_ts, full_w, g_ts, g_w = window_grids(ts_all, w_all, t0, t1, cad_name)
            total_wh = f.energy_wh(g_ts, g_w, int(g_ts[0]), int(g_ts[-1]) + 1)
            floor_wh = floor_c * len(g_ts) * cad / 3600.0
            mu_m = np.array([[best["mu"][ci[d_i]] for d_i in range(len(devices))]], np.float32)
            sd_m = np.array([[best["sd"][ci[d_i]] for d_i in range(len(devices))]], np.float32)
            po_m = np.array([[best["p_on_stay"][ci[d_i]] for d_i in range(len(devices))]], np.float32)
            if cad_name == "60":
                po_m = rescale_p_on(po_m, CAD_NATIVE, cad)
                sd_m = rung_params({"sd": sd_m}, sig_off, sig_c)["sd"]
            pm = {"mu": mu_m, "sd": sd_m, "p_on_stay": po_m,
                  "sigma_off": np.array([sig_c], np.float32), "floor_w": floor_c}
            dec = f.decode_batch(full_ts, full_w, int(t0), int(t1), devices, pm, cad)
            dev_params = {dev: {"mu_w": float(mu_m[0, d_i])}
                          for d_i, dev in enumerate(devices)}
            dwell = {dev: cfg["devices"][dev]["dwell_s"] for dev in devices}
            merge = {dev: int(cfg["devices"][dev]["merge_s"] * 1e6)
                     for dev in devices}
            pred = f.spans_to_episodes(dec, 0, devices, dev_params, merge, dwell, cad)
            per, pooled = score_row(pred, gt_eps, tau_us, devices)
            strata = strata_scores(pred, gt_eps, tau_us, devices)
            ppow = {dev: f.pred_power_series(dec, 0, d_i, float(mu_m[0, d_i]))
                    for d_i, dev in enumerate(devices)}
            a3 = axis3(ppow, g_ts, g_w, gt_dev_raw, cad, cad_name == "60",
                       total_wh, floor_wh)
            em_out[cad_name] = {"pooled": pooled, "per_device": per,
                                "strata": strata, "axis3": a3,
                                "span": row_span(per),
                                "unknown_share": f.unknown_share(dec, 0, g_w)}
            log("  em", cad_name, "| pooled F1", pooled["f1"])
        metrics["arms"]["em"] = em_out
    out_path = "docs/reports/fhmm/metrics_kcurve_" + house + ".json"
    with open(out_path, "w") as fh:
        json.dump(f.jsonable(metrics), fh, indent=1)
    log("wrote", out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--houses", default="house_2,house_5")
    ap.add_argument("--cadences", default="native,60")
    ap.add_argument("--slice", type=int, default=16)
    ap.add_argument("--draws", type=int, default=f.FROZEN["n_draws"])
    ap.add_argument("--skip-em", action="store_true")
    args = ap.parse_args()
    for house in args.houses.split(","):
        run_house(house.strip(), args.cadences.split(","), args.slice,
                  args.draws, args.skip_em)


if __name__ == "__main__":
    main()