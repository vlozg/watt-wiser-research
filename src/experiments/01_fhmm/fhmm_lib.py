"""Session-supervised additive FHMM (family B, v1) and the rules anchor.

Implements docs/experiments/fhmm-session-supervised-plan.md as frozen
2026-09-22: arm A0 (threshold + hysteresis + dwell) and arm B1
(session-supervised FHMM), the H02 button-press instrument, the H06
interference flag, and the three-axis metric surface (episode
classification / span localization / regression). Submeters are used for
evaluation GT and for *selecting* calibration windows only - never inside
any model input. All constants come from FROZEN; changing them after the
first decode is a protocol break.

Gold-layer contract: one parquet per meter with columns ts_us (int64, UTC
microseconds) and w (float64, watts). All timestamps are UTC microseconds.
"""

from __future__ import annotations

import baseline_lib as bl
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Frozen constants (plan SS8, 2026-09-22). Do not edit without a protocol-break entry.
FROZEN = {
    "k_grid": (1, 2, 3, 5, 10, 20),
    "n_draws": 20,
    "seed_base": 20260922,
    "knee_margin_f1": 0.05,
    "margin_over_anchor_f1": 0.05,
    "sigma_floor_w": 5.0,            # emission sd floor
    "dwell_clamp_s": (30.0, 86400.0),
    "off_dwell_prior_s": 7200.0,     # E[OFF dwell] prior, all devices
    "innov_c": 4.0,                  # innovation gate, ambient-sd units
    "unknown_theta": 0.5,            # marginal rejection threshold
    "tau_native_s": 12.0,            # onset tolerance = 2x cadence
    "tau_60_s": 120.0,
    "dwell_band": (1.0 / 3.0, 3.0),
    "interference_max_cover": 0.20,  # H06 flag
    "residual_share_gate": 0.20,
    "gate_split_s": 60.0,            # gated run that must split an ON-span
    "warmup_s": 7200.0,              # decode-chunk warmup, both sides
    "chunk_steps": 25600,            # ~1.8 days at 6 s
    "mu_min_w": 5.0,                 # enrolled level must clear the floor
    "anchor_off_factor": 0.9,        # hysteresis: OFF at 0.9 x thr
    "energy_hold_s": 60.0,
}


# ---------------------------------------------------------------------------
# House configuration and gold layers

def house_config(dataset: str, house: str) -> dict:
    """In-focus devices with frozen rule parameters, plus the split point."""
    prof = pd.read_csv(bl.gold_annot_file(dataset, house, "device_profile"))
    inf = prof[prof["in_focus"] == True]  # noqa: E712
    devices = {
        r["device"]: {
            "class": r["class"],
            "thr_w": float(r["thr_used_w"]),
            "dwell_s": float(r["dwell_s"]),
            "merge_s": float(r["merge_s"]),
        }
        for _, r in inf.iterrows()
    }
    split_us = int(pd.read_csv(bl.gold_annot_file(dataset, house, "splits"))["split_us"].iloc[0])
    return {"devices": devices, "split_us": split_us}


def eval_episodes(dataset: str, house: str, device: str, dev: dict,
                  t0_us: int | None = None, t1_us: int | None = None) -> pd.DataFrame:
    """Evaluation GT: episodes from the device submeter channel with its
    profile rule (submeters here are evaluation-only)."""
    df = bl.load_series(bl.gold_file(dataset, house, device))
    if t0_us is not None:
        df = df[(df.ts_us >= t0_us) & (df.ts_us < t1_us)].reset_index(drop=True)
    return bl.build_episodes(df, dev["thr_w"], min_dwell_s=dev["dwell_s"],
                             merge_gap_s=dev["merge_s"],
                             max_hold_s=FROZEN["energy_hold_s"])


def press_pool(dataset: str, house: str, device: str, before_us: int) -> pd.DataFrame:
    """Pre-split gold_annot marks of one device = simulated start/stop presses."""
    gt = bl.gt_cycles(dataset, house)
    d = gt[gt["device"] == device]
    return d[d["t_on_us"] < before_us].sort_values("t_on_us").reset_index(drop=True)


def background_estimates(dataset: str, house: str, t_end_us: int, subsample: int = 7) -> dict:
    """Always-on floor (p10) and ambient sd (1.4826 x MAD of w - floor),
    estimated aggregate-only over the pre-split span. MAD keeps a
    minority-duty fridge from inflating the OFF emission width."""
    df = bl.load_series(bl.gold_file(dataset, house, "mains"))
    df = df[df.ts_us < t_end_us]
    w = df["w"].to_numpy(float)[::subsample]
    floor = float(np.percentile(w, 10))
    resid = w - floor
    mad = float(np.median(np.abs(resid - np.median(resid))))
    return {"floor_w": floor, "sigma_off_w": float(max(1.4826 * mad, 1.0))}


# ---------------------------------------------------------------------------
# Sessions -> parameters (H02 instrument; parity-clean by construction)

def local_baseline(ts: np.ndarray, w: np.ndarray, t_on_us: int,
                   span_s: float = 120.0, gap_s: float = 10.0,
                   fallback: float = 0.0) -> float:
    """Median aggregate just before a press (the instrument's local level)."""
    i0 = int(np.searchsorted(ts, t_on_us - span_s * 1_000_000, side="left"))
    i1 = int(np.searchsorted(ts, t_on_us - gap_s * 1_000_000, side="left"))
    if i1 - i0 < 3:
        return fallback
    return float(np.median(w[i0:i1]))


def flag_interference(sessions: pd.DataFrame, others: dict[str, pd.DataFrame],
                      max_cover: float) -> np.ndarray:
    """H06 rule (frozen): a session is invalid if other in-focus devices'
    GT episodes cover more than max_cover of its interval (per-device overlap
    summed; conservative)."""
    t_on = sessions["t_on_us"].to_numpy(np.int64)
    t_off = sessions["t_off_us"].to_numpy(np.int64)
    dur = np.maximum(t_off - t_on, 1).astype(float)
    covers = np.zeros(len(sessions), float)
    for eps in others.values():
        if eps.empty:
            continue
        e_on = eps["t_on_us"].to_numpy(np.int64)
        e_off = eps["t_off_us"].to_numpy(np.int64)
        for k in range(len(t_on)):
            inter = np.minimum(e_off, t_off[k]) - np.maximum(e_on, t_on[k])
            covers[k] += float(np.maximum(inter, 0).sum())
    return covers / dur > max_cover


def sample_valid_sessions(pool: pd.DataFrame, k: int, rng: np.random.Generator,
                          others: dict[str, pd.DataFrame],
                          max_cover: float) -> tuple[pd.DataFrame, int]:
    """Bootstrap-draw sessions (with replacement) until k valid ones; flagged
    sessions do not count toward k. Returns (valid_df, attempts)."""
    if len(pool) == 0 or k <= 0:
        return pool.iloc[:0], 0
    kept: list[pd.DataFrame] = []
    attempts = 0
    cap = max(4 * k, 8)  # yield guard
    while sum(len(x) for x in kept) < k and attempts < cap:
        idx = rng.integers(0, len(pool), size=k)
        draw = pool.iloc[idx]
        attempts += len(draw)
        bad = flag_interference(draw, others, max_cover)
        kept.append(draw[~bad])
    out = pd.concat(kept, ignore_index=True) if kept else pool.iloc[:0]
    return out.head(k), attempts


def estimate_device_params(ts: np.ndarray, w: np.ndarray, floor_w: float,
                           sessions: pd.DataFrame,
                           cadence_s: float) -> dict | None:
    """Emissions and dwell from valid sessions: the aggregate over the
    interval only (parity rule). mu = mean level minus floor; sd = mean
    within-session sd; dwell from session durations, clamped. Returns None
    when the level does not clear the floor (not separable)."""
    if len(sessions) == 0:
        return None
    t_on = sessions["t_on_us"].to_numpy(np.int64)
    t_off = sessions["t_off_us"].to_numpy(np.int64)
    mus: list[float] = []
    sds: list[float] = []
    durs: list[float] = []
    for a, b in zip(t_on, t_off):
        i0 = int(np.searchsorted(ts, a + 10_000_000, side="left"))
        i1 = int(np.searchsorted(ts, max(b - 10_000_000, a + 10_000_000), side="right"))
        if i1 - i0 < 2:
            continue
        seg = w[i0:i1]
        mus.append(float(seg.mean()) - floor_w)
        sds.append(float(seg.std()))
        durs.append((b - a) / 1e6)
    if not mus:
        return None
    mu = float(np.mean(mus))
    if mu < FROZEN["mu_min_w"]:
        return None
    sd = max(float(np.mean(sds)), FROZEN["sigma_floor_w"])
    dwell = float(np.clip(float(np.mean(durs)), *FROZEN["dwell_clamp_s"]))
    return {
        "mu_w": mu,
        "sd_w": sd,
        "p_on_stay": 1.0 - 1.0 / max(dwell / cadence_s, 1.0),
        "dwell_s": dwell,
    }


def fridge_passive_params(dataset: str, house: str, dev: dict, floor_w: float,
                          sigma_off_w: float,
                          before_us: int, cadence_s: float) -> dict | None:
    """Fridge profile: aggregate-only over pre-split GT duty intervals
    (parity-clean; K-independent). Median for robustness to co-occurring
    loads."""
    eps = eval_episodes(dataset, house, "fridge", dev, None, before_us)
    if len(eps) == 0:
        return None
    df = bl.load_series(bl.gold_file(dataset, house, "mains"))
    ts = df["ts_us"].to_numpy(np.int64)
    w = df["w"].to_numpy(float)
    vals: list[float] = []
    durs: list[float] = []
    for a, b in zip(eps["t_on_us"].to_numpy(np.int64), eps["t_off_us"].to_numpy(np.int64)):
        i0 = int(np.searchsorted(ts, a, side="left"))
        i1 = int(np.searchsorted(ts, b, side="right"))
        if i1 <= i0:
            continue
        vals.append(float(np.median(w[i0:i1])) - floor_w)
        durs.append((b - a) / 1e6)
    if not vals:
        return None
    mu = float(np.median(vals))
    if mu < FROZEN["mu_min_w"]:
        return None
    dwell = float(np.clip(float(np.median(durs)), 30.0, 86400.0))
    return {
        "mu_w": mu,
        "sd_w": max(8.0, FROZEN["sigma_floor_w"]),
        "p_on_stay": 1.0 - 1.0 / max(dwell / cadence_s, 1.0),
        "dwell_s": dwell,
    }


# ---------------------------------------------------------------------------
# Decoding: batched chunked Viterbi + forward-backward

def _joint_maps(n_dev: int):
    j = np.arange(1 << n_dev, dtype=np.int64)
    bits = ((j[None, :] >> np.arange(n_dev)[:, None]) & 1).astype(np.int8)  # (D, J)
    return bits, bits.T.astype(np.float32)  # (D, J), ON-indicator (J, D)


def _gaussian_ll(obs: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return -0.5 * ((obs - mu) ** 2 / sd**2 + np.log(2.0 * np.pi * sd**2))


def decode_batch(ts: np.ndarray, w: np.ndarray, t0_us: int, t1_us: int,
                 devices: list[str], params: dict, cadence_s: float) -> dict:
    """Decode [t0_us, t1_us) for a batch of parameter sets (one shared pass).

    params keys: mu (B,D) float32, sd (B,D) float32, p_on_stay (B,D) float32,
    sigma_off (B,) float32, floor_w float. The joint space is 2^D states;
    device d owns bit d of the joint index. Chunks are decoded independently
    with warmup on both sides and concatenated; boundary merging happens
    downstream in spans_to_episodes. Returns ts (T,), on (T,B,D) int8,
    marg (T,B,D) float32 posteriors P(device ON), gated (T,B) int8,
    loglik (B,)."""
    mu = params["mu"].astype(np.float32)
    sd = params["sd"].astype(np.float32)
    p_on = params["p_on_stay"].astype(np.float32)
    sig_off = params["sigma_off"].astype(np.float32)
    B, D = mu.shape
    J = 1 << D
    bits, ON = _joint_maps(D)

    mu_on = mu @ ON.T                                 # (B, J)
    # joint transition logT[b, i, j] = log P(next=j | cur=i), product of per-device 2x2 chains
    n_off_steps = max(FROZEN["off_dwell_prior_s"] / cadence_s, 1.0)
    p_oo = np.float32(1.0 - 1.0 / n_off_steps)
    logT = np.zeros((B, J, J), np.float32)
    for d in range(D):
        logT_d = np.log(np.stack([
            np.stack([np.full(B, p_oo, np.float32), np.full(B, 1.0 - p_oo, np.float32)], axis=-1),
            np.stack([(1.0 - p_on[:, d]).astype(np.float32), p_on[:, d]], axis=-1),
        ], axis=1))                                   # (B, 2, 2) rows=from
        logT += logT_d[:, bits[d], :][:, :, bits[d]]
    # stationary init per chain (per device column)
    init = np.ones((B, J), np.float32)
    for d in range(D):
        rate_d = (1.0 - p_oo) / ((1.0 - p_oo) + (1.0 - p_on[:, d]))  # (B,)
        init *= np.where(bits[d][None, :] > 0, rate_d[:, None], 1.0 - rate_d[:, None])
    eT = np.exp(logT)

    g0 = int(np.searchsorted(ts, t0_us, side="left"))
    g1 = int(np.searchsorted(ts, t1_us, side="right"))
    T_total = g1 - g0
    if T_total <= 0:
        raise ValueError("empty decode window")
    warm = int(FROZEN["warmup_s"] / cadence_s)
    chunk = int(FROZEN["chunk_steps"])
    on_out = np.zeros((T_total, B, D), np.int8)
    marg_out = np.zeros((T_total, B, D), np.float32)
    gated_out = np.zeros((T_total, B), np.int8)
    loglik = np.zeros(B, np.float64)
    pos = 0
    while pos < T_total:
        core0, core1 = pos, min(pos + chunk, T_total)
        w0 = max(0, core0 - warm)
        w1 = min(T_total, core1 + warm)
        seg_obs = (w[g0 + w0 : g0 + w1] - params["floor_w"]).astype(np.float32)
        nseg = w1 - w0
        # additive joint emission (exact sum constraint): ONE Gaussian over the
        # aggregate per joint state - mean = sum of member means (OFF members
        # sit at 0). Variance: the ambient floor is ONE shared noise source
        # counted once, ON members add their own excess (session sd includes
        # ambient, so each contributes sd_d^2 - sigma_off^2):
        #   var_j = sigma_off^2 + sum_ON (sd_d^2 - sigma_off^2)
        # exact for all-OFF, single-ON and pairwise states under independence.
        # (Protocol break, logged pre-run 2026-09-22: the draft's D*sigma_off^2
        # made the all-OFF width sqrt(D)*sigma_off - on house_5 that is 292 W
        # vs the true 130 W, and the quiet gate became c*sqrt(D)*sigma_off,
        # contradicting the frozen 'quiet reduces exactly to c*sigma_off'.)
        mean_j = mu_on                                   # (B, J)
        var_j = sig_off[:, None]**2 + \
            (np.maximum(sd**2 - sig_off[:, None]**2, 0.0) @ ON.T)  # (B, J)
        sd_j = np.sqrt(np.maximum(var_j, 1e-12))
        em = _gaussian_ll(seg_obs[None, None, :], mean_j[:, :, None], sd_j[:, :, None]).astype(np.float32)
        # Viterbi
        bp = np.zeros((nseg, B, J), np.int8)
        prev = init + em[:, :, 0]
        prev -= prev.max(axis=1, keepdims=True)
        for t in range(1, nseg):
            tmp = prev[:, :, None] + logT
            bp[t] = tmp.argmax(axis=1).astype(np.int8)
            prev = tmp.max(axis=1) + em[:, :, t]
            prev -= prev.max(axis=1, keepdims=True)
        states = np.zeros((nseg, B), np.int8)
        states[nseg - 1] = prev.argmax(axis=1).astype(np.int8)
        bidx = np.arange(B)
        for t in range(nseg - 1, 0, -1):
            states[t - 1] = bp[t][bidx, states[t]]
        # forward-backward (scaled; per-step max-shift for numerical stability)
        em_max = em.max(axis=1)                          # (B, nseg)
        em_s = em - em_max[:, None, :]
        alpha = np.zeros((nseg, B, J), np.float32)
        a0 = init * np.exp(em_s[:, :, 0])
        c0 = np.maximum(a0.sum(axis=1), 1e-38)
        alpha[0] = a0 / c0[:, None]
        loglik += em_max[:, 0] + np.log(c0)
        for t in range(1, nseg):
            at = np.einsum("bi,bij->bj", alpha[t - 1], eT) * np.exp(em_s[:, :, t])
            ct = np.maximum(at.sum(axis=1), 1e-38)
            alpha[t] = at / ct[:, None]
            loglik += em_max[:, t] + np.log(ct)
        beta = np.ones((nseg, B, J), np.float32)
        for t in range(nseg - 2, -1, -1):
            bt = np.einsum("bij,bj->bi", eT, beta[t + 1] * np.exp(em_s[:, :, t + 1]))
            beta[t] = bt / np.maximum(bt.sum(axis=1, keepdims=True), 1e-38)
        gam = alpha * beta
        gam /= np.maximum(gam.sum(axis=2, keepdims=True), 1e-38)
        marg = gam @ ON                                  # (nseg, B, D)
        # innovation gate: the residual is compared against the decoded
        # state's own emission spread, floored at the ambient sd. In quiet
        # (all-OFF) regions this reduces exactly to the frozen c*sigma_off
        # rule; ON regions of high-variance devices are not self-gated.
        mu_seg = mu_on[bidx[None, :], states]            # (nseg, B)
        sd_seg = sd_j[bidx[None, :], states]             # (nseg, B)
        resid = seg_obs[:, None] - mu_seg
        gate_sd = np.maximum(sd_seg, sig_off[None, :])
        gated = (np.abs(resid) > FROZEN["innov_c"] * gate_sd).astype(np.int8)
        c0i, c1i = core0 - w0, core1 - w0
        on_out[core0:core1] = (states[c0i:c1i][:, :, None] >> np.arange(D)[None, None, :]) & 1
        marg_out[core0:core1] = marg[c0i:c1i]
        gated_out[core0:core1] = gated[c0i:c1i]
        pos = core1
    return {"ts": ts[g0:g1], "on": on_out, "marg": marg_out,
            "gated": gated_out, "loglik": loglik}


# ---------------------------------------------------------------------------
# Episode extraction

def _runs(ts: np.ndarray, on: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Start and inclusive-end indices of ON runs in a boolean indicator."""
    idx = np.flatnonzero(on)
    if idx.size == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    brk = np.flatnonzero(np.diff(idx) > 1)
    return np.r_[idx[0], idx[brk + 1]], np.r_[idx[brk], idx[-1]]


def _merge_runs(ts: np.ndarray, starts: np.ndarray, ends: np.ndarray,
                merge_gap_us: int, gated_cum: np.ndarray | None,
                gate_split_steps: int) -> tuple[np.ndarray, np.ndarray]:
    """Merge runs whose OFF gap is at most merge_gap_us - except gaps that
    carry at least gate_split_steps gated samples, which must split."""
    t_on, t_off = ts[starts], ts[ends]
    new_run = np.concatenate(([True], (t_on[1:] - t_off[:-1]) > merge_gap_us))
    if gated_cum is not None and len(starts) > 1:
        gap_hi = np.searchsorted(ts, t_on[1:], side="left")
        gap_lo = np.searchsorted(ts, t_off[:-1], side="right")
        gated_in_gap = gated_cum[gap_hi] - gated_cum[gap_lo]
        new_run[1:] |= gated_in_gap >= gate_split_steps
    bnd = np.flatnonzero(new_run)
    grp_end = np.r_[bnd[1:] - 1, len(t_on) - 1]
    return t_on[bnd], t_off[grp_end]


def spans_to_episodes(dec: dict, b: int, devices: list[str], dev_params: dict,
                      merge_us_by_dev: dict[str, int], dwell_s_by_dev: dict[str, float],
                      cadence_s: float) -> pd.DataFrame:
    """Decoded state sequence -> per-device episodes for one batch element.
    A timestep is claimed by device d when its state bit is ON, its posterior
    marginal is >= theta, and it is not innovation-gated. Episodes merge over
    gaps <= merge_gap_s unless a >= gate_split_s gated run sits in the gap; 
    episodes shorter than min dwell are dropped."""
    ts = dec["ts"]
    gate_steps = max(int(FROZEN["gate_split_s"] / cadence_s), 1)
    rows = []
    for d, dev in enumerate(devices):
        on = (dec["on"][:, b, d] == 1) & (dec["marg"][:, b, d] >= FROZEN["unknown_theta"]) \
             & (dec["gated"][:, b] == 0)
        starts, ends = _runs(ts, on)
        if len(starts) == 0:
            continue
        gated_cum = np.concatenate(([0], np.cumsum(dec["gated"][:, b])))
        t_on, t_off = _merge_runs(ts, starts, ends, merge_us_by_dev[dev],
                                  gated_cum, gate_steps)
        dur_s = (t_off - t_on) / 1e6
        keep = dur_s >= dwell_s_by_dev[dev]
        for a, bnd in zip(t_on[keep], t_off[keep]):
            rows.append({"device": dev, "t_on_us": int(a), "t_off_us": int(bnd),
                         "mu_w": float(dev_params[dev]["mu_w"])})
    if not rows:
        return pd.DataFrame(columns=["device", "t_on_us", "t_off_us", "mu_w"])
    return pd.DataFrame(rows)


def anchor_episodes(ts: np.ndarray, w: np.ndarray, t0_us: int, t1_us: int,
                    thr_w: float, min_dwell_s: float, merge_gap_s: float,
                    cadence_s: float) -> pd.DataFrame:
    """Arm A0: threshold + hysteresis (OFF at anchor_off_factor x thr) +
    min dwell + merge, on the aggregate. Vectorized state machine."""
    g0 = int(np.searchsorted(ts, t0_us, side="left"))
    g1 = int(np.searchsorted(ts, t1_us, side="right"))
    seg = w[g0:g1]
    gts = ts[g0:g1]
    thr_on = thr_w
    thr_off = thr_w * FROZEN["anchor_off_factor"]
    mark = np.where(seg > thr_on, 1, np.where(seg < thr_off, 0, -1))
    force = mark != -1
    last = np.where(force, np.arange(len(mark)), -1)
    last = np.maximum.accumulate(last)
    state = np.where(last >= 0, mark[np.maximum(last, 0)], 0)
    starts, ends = _runs(gts, state == 1)
    if len(starts) == 0:
        return pd.DataFrame(columns=["device", "t_on_us", "t_off_us", "mu_w"])
    t_on, t_off = _merge_runs(gts, starts, ends, int(merge_gap_s * 1e6), None, 0)
    dur_s = (t_off - t_on) / 1e6
    keep = dur_s >= min_dwell_s
    return pd.DataFrame({"device": "", "t_on_us": t_on[keep],
                         "t_off_us": t_off[keep], "mu_w": thr_w})


# ---------------------------------------------------------------------------
# Metrics (three axes)

def tag_cooccurring(gt_by_dev: dict[str, pd.DataFrame], device: str) -> np.ndarray:
    """Per GT episode of `device`: True when it overlaps any other device's
    GT episode (the overlapped stratum)."""
    eps = gt_by_dev[device]
    out = np.zeros(len(eps), bool)
    if eps.empty:
        return out
    e_on = eps["t_on_us"].to_numpy(np.int64)
    e_off = eps["t_off_us"].to_numpy(np.int64)
    for other, df in gt_by_dev.items():
        if other == device or df.empty:
            continue
        o_on = df["t_on_us"].to_numpy(np.int64)
        o_off = df["t_off_us"].to_numpy(np.int64)
        for k in range(len(eps)):
            inter = np.minimum(o_off, e_off[k]) - np.maximum(o_on, e_on[k])
            out[k] |= bool((inter > 0).any())
    return out


def score_device(pred: pd.DataFrame, gt: pd.DataFrame, tau_us: float,
                 dwell_band: tuple[float, float]) -> dict:
    """Axis 1 (classification) + Axis 2 (span localization) for one device.
    Onset matching is greedy one-to-one within tau; matched pairs outside the
    dwell-ratio band count as a miss on BOTH sides (conservative). Onset/offset
    errors are signed (pred - gt)."""
    n_pred, n_gt = len(pred), len(gt)
    out = {"n_pred": n_pred, "n_gt": n_gt, "n_matched": 0,
           "precision": None, "recall": None, "f1": None, "span": None}
    if n_gt == 0 and n_pred == 0:
        return out
    if n_pred == 0 or n_gt == 0:
        out.update({"precision": 0.0, "recall": 0.0, "f1": 0.0})
        return out
    gt_on = gt["t_on_us"].to_numpy(np.int64)
    gt_off = gt["t_off_us"].to_numpy(np.int64)
    pr_on = pred["t_on_us"].to_numpy(np.int64)
    pr_off = pred["t_off_us"].to_numpy(np.int64)
    gi, pi = bl.match_onsets(gt_on, pr_on, tau_us)
    keep = np.ones(len(gi), bool)
    if len(gi):
        ratio = (pr_off[pi] - pr_on[pi]) / np.maximum(gt_off[gi] - gt_on[gi], 1)
        keep = (ratio >= dwell_band[0]) & (ratio <= dwell_band[1])
    out["n_matched"] = int(keep.sum())
    p, r, f = bl.prf(out["n_matched"], n_pred, n_gt)
    out.update({"precision": p, "recall": r, "f1": f})
    if out["n_matched"]:
        g_on, g_off = gt_on[gi[keep]], gt_off[gi[keep]]
        q_on, q_off = pr_on[pi[keep]], pr_off[pi[keep]]
        inter = np.maximum(0, np.minimum(q_off, g_off) - np.maximum(q_on, g_on))
        union = (q_off - q_on) + (g_off - g_on) - inter
        out["span"] = {
            "onset_err_s": (q_on - g_on) / 1e6,
            "offset_err_s": (q_off - g_off) / 1e6,
            "dur_ratio": (q_off - q_on) / np.maximum(g_off - g_on, 1),
            "iou": inter / np.maximum(union, 1),
        }
    return out


def nmae_for_device(grid_ts: np.ndarray, pred_power: np.ndarray,
                    gt_dev: pd.DataFrame, agg_w_grid: np.ndarray) -> dict:
    """Axis 3: per-device nMAE over the decode grid (GT device power aligned
    by exact timestamp; denominator = mean aggregate power over the grid)."""
    den = float(np.mean(agg_w_grid)) if len(agg_w_grid) else float("nan")
    if gt_dev.empty:
        return {"mae_w": None, "nmae": None, "n_common": 0, "den_w": den}
    gt_ts = gt_dev["ts_us"].to_numpy(np.int64)
    gt_w = gt_dev["w"].to_numpy(float)
    pos = np.searchsorted(gt_ts, grid_ts)
    pos_c = np.minimum(pos, len(gt_ts) - 1)
    ok = (pos < len(gt_ts)) & (gt_ts[pos_c] == grid_ts)
    if not ok.any():
        return {"mae_w": None, "nmae": None, "n_common": 0, "den_w": den}
    diff = np.abs(pred_power[ok] - gt_w[pos_c[ok]])
    mae = float(diff.mean())
    return {"mae_w": mae, "nmae": mae / den if den else None,
            "n_common": int(ok.sum()), "den_w": den}


def energy_wh(ts: np.ndarray, w: np.ndarray, t0_us: int, t1_us: int) -> float:
    """Step-rule energy (Wh) of a series inside [t0, t1)."""
    cum = bl.step_energy_cumsum_wh(ts, w, max_hold_s=FROZEN["energy_hold_s"])
    return bl.window_energy_wh(ts, cum, t0_us, t1_us)


def books_close(total_wh: float, attributed_wh: float, floor_wh: float) -> dict:
    """Whole-span energy balance: residual = total - attributed - floor."""
    resid = total_wh - attributed_wh - floor_wh
    return {"total_wh": total_wh, "attributed_wh": attributed_wh,
            "floor_wh": floor_wh, "residual_wh": resid,
            "residual_share": resid / total_wh if total_wh else None}


def to_rung(ts: np.ndarray, w: np.ndarray, bucket_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Cadence rung (H03): bucket-mean the series onto a coarser grid; the
    timestamp is the bucket midpoint."""
    bid = ts // int(bucket_s * 1e6)
    ub, first = np.unique(bid, return_index=True)
    counts = np.diff(np.r_[first, len(bid)]).astype(float)
    return ub * int(bucket_s * 1e6) + int(bucket_s * 1e6) // 2, np.add.reduceat(w, first) / counts


def pred_power_series(dec: dict, b: int, d: int, mu_w: float) -> np.ndarray:
    """Decoded power claim of device d in batch b: mu when claimed ON, else 0."""
    return np.where((dec["on"][:, b, d] == 1)
                    & (dec["marg"][:, b, d] >= FROZEN["unknown_theta"])
                    & (dec["gated"][:, b] == 0), mu_w, 0.0)


def unknown_share(dec: dict, b: int, grid_w: np.ndarray) -> float:
    """Share of window energy sitting on innovation-gated timesteps."""
    hold = np.minimum(np.diff(dec["ts"], append=dec["ts"][-1]),
                      FROZEN["energy_hold_s"] * 1_000_000)
    e = grid_w * hold
    tot = e.sum()
    return float(e[dec["gated"][:, b] == 1].sum() / tot) if tot else 0.0


def pooled_prf(scores: list[dict]) -> dict:
    """Pool per-device score dicts into one P/R/F1 (sum counts, then compute)."""
    n_pred = sum(s["n_pred"] for s in scores)
    n_gt = sum(s["n_gt"] for s in scores)
    n_m = sum(s["n_matched"] for s in scores)
    p, r, f = bl.prf(n_m, n_pred, n_gt)
    return {"n_pred": n_pred, "n_gt": n_gt, "n_matched": n_m,
            "precision": p, "recall": r, "f1": f}


def collect_span(scores: list[dict]) -> dict:
    """Pool span stats over matched pairs; signed medians + absolute p90s."""
    on = np.concatenate([s["span"]["onset_err_s"] for s in scores if s["span"]])
    off = np.concatenate([s["span"]["offset_err_s"] for s in scores if s["span"]])
    dr = np.concatenate([s["span"]["dur_ratio"] for s in scores if s["span"]])
    iou = np.concatenate([s["span"]["iou"] for s in scores if s["span"]])
    if on.size == 0:
        return {"n_pairs": 0}
    return {
        "n_pairs": int(on.size),
        "onset_med_s": float(np.median(on)),
        "onset_p90_abs_s": float(np.percentile(np.abs(on), 90)),
        "offset_med_s": float(np.median(off)),
        "offset_p90_abs_s": float(np.percentile(np.abs(off), 90)),
        "dur_ratio_med": float(np.median(dr)),
        "iou_med": float(np.median(iou)),
    }

def jsonable(obj):
    """Numpy -> plain types for metrics.json."""
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if np.isnan(v) else v
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj