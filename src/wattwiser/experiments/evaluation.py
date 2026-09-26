"""Scoring a model's episodes against the true ones, and its watts against energy.

Everything here reads episode tables (columns t_on_us / t_off_us) or a decoded
power array. Three questions are answered:

  did it find the right episodes   greedy one-to-one onset matching within a
                                   tolerance, then precision/recall/F1; counts
                                   are summed over devices before dividing
  are the episodes the right shape signed onset and offset errors, length
                                   ratio and overlap over the matched pairs; a
                                   pair whose lengths disagree too much counts
                                   as a miss on both sides
  do the watts add up             per-device mean absolute error against that
                                   device's own meter, and a whole-span energy
                                   balance (total vs attributed vs floor)

Nothing here fits or predicts anything; it only scores what a model produced.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd

from wattwiser.experiments.energy import step_energy_cumsum_wh, window_energy_wh
from wattwiser.experiments.units import TimestampsUs


def match_onsets(
    gt_on_us: TimestampsUs, pred_on_us: TimestampsUs, tau_us: float
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]:
    """Greedy one-to-one matching of predicted onsets to true onsets within tau_us.

    Scans both (sorted-ascending) arrays; a true onset and a predicted
    onset pair when they differ by at most tau_us and neither side is
    matched yet. Returns the matched (gt_indices, pred_indices).
    """
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


def precision_recall_f1(n_matched: int, n_pred: int, n_gt: int) -> tuple[float, float, float]:
    """Precision, recall, F1 from match counts; 0.0 whenever a denominator is 0."""
    p = n_matched / n_pred if n_pred else 0.0
    r = n_matched / n_gt if n_gt else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


# ------------------------------------------------- finding the right episodes


def overlapping_gt(gt_by_device: dict[str, pd.DataFrame], device: str) -> np.ndarray:
    """For each true episode of one device: is it overlapped by another device?

    Used to report a device separately for its clean episodes and for the ones
    that ran at the same time as something else.
    """
    episodes = gt_by_device[device]
    overlapped = np.zeros(len(episodes), bool)
    if episodes.empty:
        return overlapped
    own_on = episodes["t_on_us"].to_numpy(np.int64)
    own_off = episodes["t_off_us"].to_numpy(np.int64)
    for other, other_episodes in gt_by_device.items():
        if other == device or other_episodes.empty:
            continue
        other_on = other_episodes["t_on_us"].to_numpy(np.int64)
        other_off = other_episodes["t_off_us"].to_numpy(np.int64)
        for k in range(len(episodes)):
            overlap = np.minimum(other_off, own_off[k]) - np.maximum(other_on, own_on[k])
            overlapped[k] |= bool((overlap > 0).any())
    return overlapped


def score_episodes(pred_episodes: pd.DataFrame, gt_episodes: pd.DataFrame,
                   onset_tolerance_us: float,
                   duration_band: tuple[float, float]) -> dict:
    """How well one device's predicted episodes match its true episodes.

    Onsets are matched one-to-one within onset_tolerance_us. A matched pair
    whose lengths differ outside duration_band counts as a miss on both sides,
    so a lucky short hit does not earn credit. Errors are signed: predicted
    minus true, in seconds.
    """
    n_pred, n_gt = len(pred_episodes), len(gt_episodes)
    result = {"n_pred": n_pred, "n_gt": n_gt, "n_matched": 0,
              "precision": None, "recall": None, "f1": None, "span": None}
    if n_gt == 0 and n_pred == 0:
        return result
    if n_pred == 0 or n_gt == 0:
        result.update({"precision": 0.0, "recall": 0.0, "f1": 0.0})
        return result
    gt_on = gt_episodes["t_on_us"].to_numpy(np.int64)
    gt_off = gt_episodes["t_off_us"].to_numpy(np.int64)
    pred_on = pred_episodes["t_on_us"].to_numpy(np.int64)
    pred_off = pred_episodes["t_off_us"].to_numpy(np.int64)
    gt_index, pred_index = match_onsets(gt_on, pred_on, onset_tolerance_us)
    keep = np.ones(len(gt_index), bool)
    if len(gt_index):
        length_ratio = ((pred_off[pred_index] - pred_on[pred_index])
                        / np.maximum(gt_off[gt_index] - gt_on[gt_index], 1))
        keep = (length_ratio >= duration_band[0]) & (length_ratio <= duration_band[1])
    result["n_matched"] = int(keep.sum())
    precision, recall, f1 = precision_recall_f1(result["n_matched"], n_pred, n_gt)
    result.update({"precision": precision, "recall": recall, "f1": f1})
    if result["n_matched"]:
        matched_gt_on, matched_gt_off = gt_on[gt_index[keep]], gt_off[gt_index[keep]]
        matched_pred_on = pred_on[pred_index[keep]]
        matched_pred_off = pred_off[pred_index[keep]]
        overlap = np.maximum(0, np.minimum(matched_pred_off, matched_gt_off)
                             - np.maximum(matched_pred_on, matched_gt_on))
        union = ((matched_pred_off - matched_pred_on)
                 + (matched_gt_off - matched_gt_on) - overlap)
        result["span"] = {
            "onset_error_s": (matched_pred_on - matched_gt_on) / 1e6,
            "offset_error_s": (matched_pred_off - matched_gt_off) / 1e6,
            "duration_ratio": ((matched_pred_off - matched_pred_on)
                              / np.maximum(matched_gt_off - matched_gt_on, 1)),
            "iou": overlap / np.maximum(union, 1),
        }
    return result


def pool_scores(scores: list[dict]) -> dict:
    """Combine per-device scores into one line: add the counts, then divide."""
    n_pred = sum(s["n_pred"] for s in scores)
    n_gt = sum(s["n_gt"] for s in scores)
    n_matched = sum(s["n_matched"] for s in scores)
    precision, recall, f1 = precision_recall_f1(n_matched, n_pred, n_gt)
    return {"n_pred": n_pred, "n_gt": n_gt, "n_matched": n_matched,
            "precision": precision, "recall": recall, "f1": f1}


def pool_span_stats(scores: list[dict]) -> dict:
    """Combine the timing errors over all matched pairs of every device."""
    onset = np.concatenate([s["span"]["onset_error_s"] for s in scores if s["span"]])
    offset = np.concatenate([s["span"]["offset_error_s"] for s in scores if s["span"]])
    ratio = np.concatenate([s["span"]["duration_ratio"] for s in scores if s["span"]])
    iou = np.concatenate([s["span"]["iou"] for s in scores if s["span"]])
    if onset.size == 0:
        return {"n_pairs": 0}
    return {
        "n_pairs": int(onset.size),
        "onset_median_s": float(np.median(onset)),
        "onset_p90_abs_s": float(np.percentile(np.abs(onset), 90)),
        "offset_median_s": float(np.median(offset)),
        "offset_p90_abs_s": float(np.percentile(np.abs(offset), 90)),
        "duration_ratio_median": float(np.median(ratio)),
        "iou_median": float(np.median(iou)),
    }


# --------------------------------------------------------- do the watts add up


def nmae_for_device(grid_ts_us: TimestampsUs, predicted_w: npt.NDArray[np.float64],
                    gt_ts_us: TimestampsUs, gt_w: npt.NDArray[np.float64],
                    aggregate_grid_w: npt.NDArray[np.float64]) -> dict:
    """Mean absolute error of one device's watts, scaled by the average load.

    The two series are lined up by exact timestamp - readings the true meter
    does not have are skipped, not filled in. The error is divided by the mean
    aggregate watts over the window, which makes nMAE comparable across houses.
    """
    mean_aggregate_w = float(np.mean(aggregate_grid_w)) if len(aggregate_grid_w) else float("nan")
    if gt_ts_us.size == 0:
        return {"mae_w": None, "nmae": None, "n_common": 0, "mean_aggregate_w": mean_aggregate_w}
    position = np.searchsorted(gt_ts_us, grid_ts_us)
    position_clipped = np.minimum(position, len(gt_ts_us) - 1)
    same_time = (position < len(gt_ts_us)) & (gt_ts_us[position_clipped] == grid_ts_us)
    if not same_time.any():
        return {"mae_w": None, "nmae": None, "n_common": 0, "mean_aggregate_w": mean_aggregate_w}
    difference_w = np.abs(predicted_w[same_time] - gt_w[position_clipped[same_time]])
    mae_w = float(difference_w.mean())
    return {"mae_w": mae_w, "nmae": mae_w / mean_aggregate_w if mean_aggregate_w else None,
            "n_common": int(same_time.sum()), "mean_aggregate_w": mean_aggregate_w}


def energy_wh(ts_us: TimestampsUs, w: npt.NDArray[np.float64], t0_us: int, t1_us: int,
              max_hold_s: float = 60.0) -> float:
    """Energy in Wh of a series inside [t0_us, t1_us).

    Each reading counts as if it held until the next one, but never longer
    than max_hold_s, so a gap in the meter does not invent energy.
    """
    cumulative_wh = step_energy_cumsum_wh(ts_us, w, max_hold_s=max_hold_s)
    return window_energy_wh(ts_us, cumulative_wh, t0_us, t1_us)


def energy_balance(total_wh: float, attributed_wh: float, floor_wh: float) -> dict:
    """Check that the claimed energy plus the floor adds up to the measured energy.

    residual = measured - claimed - floor. A large positive residual means the
    model is claiming too little of what the house actually used.
    """
    residual_wh = total_wh - attributed_wh - floor_wh
    return {"total_wh": total_wh, "attributed_wh": attributed_wh, "floor_wh": floor_wh,
            "residual_wh": residual_wh,
            "residual_share": residual_wh / total_wh if total_wh else None}
