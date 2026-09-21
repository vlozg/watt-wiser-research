"""Shared helpers for the 00_baseline experiment notebooks.

The baseline scaffold notebook (01_ukdale_baseline.py) imports this module;
keeping the functions here lets future pytest tests exercise the same
implementations without loading data. Gold-layer contract: one Parquet per
meter under data/gold/<dataset>/<house>/ with columns ts_us (int64, UTC
microseconds) and w (float64, active watts).

Gap policy (provisional, one rule everywhere): a reading holds its value
until the next reading of the same channel, but for at most max_hold_s;
anything past that hold is left unintegrated (unknown, not zero). The same
rule prices mains and submeter energy.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

WUS_PER_WH = 3.6e9  # 1 Wh = 3600 W*s = 3.6e9 W*microsecond


def gold_file(dataset: str, house: str, name: str) -> str:
    """Path of one gold-layer parquet."""
    return os.path.join(ROOT, "data", "gold", dataset, house, f"{name}.parquet")


def gold_annot_file(dataset: str, house: str, name: str) -> str:
    """Path of one gold_annot manual-annotation csv (see data/gold_annot/README.md)."""
    return os.path.join(ROOT, "data", "gold_annot", dataset, house, f"{name}.csv")


def gt_cycles(dataset: str, house: str) -> pd.DataFrame:
    """All GT cycle marks for one house: manual + rule, with a provenance column.

    Union of manual_cycles.csv (human-curated, source manual_*) and
    rule_cycles.csv (regenerable rule output, source rule_*); missing or
    empty files are skipped. 'provenance' is 'manual' or 'rule'. See
    data/gold_annot/README.md for the store policy.
    """
    frames = []
    for name, prov in (("manual_cycles", "manual"), ("rule_cycles", "rule")):
        try:
            df = pd.read_csv(gold_annot_file(dataset, house, name))
        except (FileNotFoundError, pd.errors.EmptyDataError):
            continue
        df["provenance"] = prov
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["device", "t_on_us", "t_off_us", "source", "provenance"])
    return pd.concat(frames, ignore_index=True)


def load_series(path: str) -> pd.DataFrame:
    """Load a gold parquet as a timestamp-sorted [ts_us, w] frame."""
    return pd.read_parquet(path)[["ts_us", "w"]].sort_values("ts_us").reset_index(drop=True)


def step_energy_cumsum_wh(
    ts_us: np.ndarray, w: np.ndarray, max_hold_s: float = 60.0
) -> np.ndarray:
    """Prefix sums of step-rule energy (Wh) per sample.

    Sample i holds w[i] for min(dt_i, max_hold_s) where dt_i is the gap to
    the next sample of the same channel. Cumulative, so the energy of a
    window is cum[i1] - cum[i0] (see window_energy_wh).
    """
    dt_us = np.diff(ts_us, append=ts_us[-1])
    hold_us = np.minimum(dt_us, max_hold_s * 1_000_000)
    return np.cumsum(w * hold_us) / WUS_PER_WH


def window_energy_wh(
    ts_us: np.ndarray, cum_wh: np.ndarray, t0_us: int, t1_us: int
) -> float:
    """Step-rule energy of a series inside [t0_us, t1_us] from its prefix sums."""
    i0 = int(np.searchsorted(ts_us, t0_us, side="left"))
    i1 = int(np.searchsorted(ts_us, t1_us, side="right"))
    hi = float(cum_wh[i1 - 1]) if i1 > 0 else 0.0
    lo = float(cum_wh[i0 - 1]) if i0 > 0 else 0.0
    return max(hi - lo, 0.0)


def build_episodes(
    df: pd.DataFrame,
    thr_w: float,
    min_dwell_s: float = 30.0,
    merge_gap_s: float = 12.0,
    max_hold_s: float = 60.0,
) -> pd.DataFrame:
    """Ground-truth episodes from one submeter channel.

    ON := w > thr_w; rows at or below threshold, and any gap between rows,
    are OFF. ON-runs separated by at most merge_gap_s merge into one
    episode (single dropped samples); merged episodes shorter than
    min_dwell_s are dropped. Episode energy uses the step rule with the
    max_hold_s cap. Returns [t_on_us, t_off_us, dur_s, energy_wh].
    """
    ts = df["ts_us"].to_numpy(np.int64)
    w = df["w"].to_numpy(float)
    idx = np.flatnonzero(w > thr_w)
    if idx.size == 0:
        return pd.DataFrame(columns=["t_on_us", "t_off_us", "dur_s", "energy_wh"])
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[breaks + 1]]
    ends = np.r_[idx[breaks], idx[-1]]  # inclusive last ON index per run
    e_sample = w * np.minimum(np.diff(ts, append=ts[-1]), max_hold_s * 1_000_000)
    cs = np.concatenate(([0.0], np.cumsum(e_sample)))
    run_wh = (cs[ends + 1] - cs[starts]) / WUS_PER_WH
    t_on, t_off = ts[starts], ts[ends]
    # merge runs whose OFF gap is at most merge_gap_s
    new_run = np.concatenate(([True], (t_on[1:] - t_off[:-1]) > merge_gap_s * 1_000_000))
    bnd = np.flatnonzero(new_run)
    grp_end = np.r_[bnd[1:] - 1, len(t_on) - 1]
    t_on_m, t_off_m = t_on[bnd], t_off[grp_end]
    wh_m = np.add.reduceat(run_wh, bnd)
    dur_s = (t_off_m - t_on_m) / 1e6
    keep = dur_s >= min_dwell_s
    return pd.DataFrame(
        {
            "t_on_us": t_on_m[keep],
            "t_off_us": t_off_m[keep],
            "dur_s": dur_s[keep],
            "energy_wh": wh_m[keep],
        }
    )


def rising_edges(step: np.ndarray, thr: float) -> np.ndarray:
    """Indices where step crosses above thr (previous sample not above)."""
    above = step > thr
    prev = np.concatenate(([False], above[:-1]))
    return np.flatnonzero(above & ~prev)


def episodes_from_edges(
    ts_us: np.ndarray, rise_idx: np.ndarray, fall_times_us: np.ndarray, min_dwell_s: float
) -> pd.DataFrame:
    """Pair each rising edge with the next falling edge after it; keep
    episodes at least min_dwell_s long. Returns [t_on_us, t_off_us, dur_s]."""
    if rise_idx.size == 0 or fall_times_us.size == 0:
        return pd.DataFrame(columns=["t_on_us", "t_off_us", "dur_s"])
    pos = np.searchsorted(fall_times_us, ts_us[rise_idx], side="right")
    ok = pos < len(fall_times_us)
    rise_idx, pos = rise_idx[ok], pos[ok]
    t_on = ts_us[rise_idx]
    t_off = fall_times_us[pos]
    dur_s = (t_off - t_on) / 1e6
    keep = dur_s >= min_dwell_s
    return pd.DataFrame(
        {"t_on_us": t_on[keep], "t_off_us": t_off[keep], "dur_s": dur_s[keep]}
    )


def match_onsets(
    gt_on_us: np.ndarray, pred_on_us: np.ndarray, tau_us: float
) -> tuple[np.ndarray, np.ndarray]:
    """Greedy one-to-one matching of predicted onsets to ground-truth onsets
    within tau_us. Returns (gt_indices, pred_indices) of matched pairs."""
    gi: list[int] = []
    pi: list[int] = []
    i = j = 0
    while i < len(gt_on_us) and j < len(pred_on_us):
        if pred_on_us[j] < gt_on_us[i] - tau_us:
            j += 1
        elif pred_on_us[j] > gt_on_us[i] + tau_us:
            i += 1
        else:
            gi.append(i)
            pi.append(j)
            i += 1
            j += 1
    return np.asarray(gi, dtype=np.int64), np.asarray(pi, dtype=np.int64)


def prf(n_matched: int, n_pred: int, n_gt: int) -> tuple[float, float, float]:
    """Precision / recall / F1 from match counts."""
    p = n_matched / n_pred if n_pred else 0.0
    r = n_matched / n_gt if n_gt else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def md_table(headers: list[str], rows: list[list]) -> str:
    """Minimal markdown table renderer for mo.md cells."""
    head = "| " + " | ".join(str(h) for h in headers) + " |"
    sep = "|" + "|".join("---" for _ in headers) + "|"
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return "\n".join([head, sep, body])
