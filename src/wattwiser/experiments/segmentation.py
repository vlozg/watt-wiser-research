"""Segmenting a power series into appliance ON/OFF intervals.

An episode is one continuous ON period of an appliance: from the first
sample above a power threshold to the last sample above it. This module
detects and merges threshold runs; the repo docs and metrics all say
"episode" for the resulting intervals. on_runs/merge_runs are the
primitives the FHMM decode path reuses (src/experiments/01_fhmm), so run
detection and merging each have one implementation.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import pandas as pd

from wattwiser.experiments.energy import hold_us
from wattwiser.experiments.units import US_PER_S, WUS_PER_WH, TimestampsUs

EPISODE_COLS: list[str] = ["t_on_us", "t_off_us", "dur_s", "energy_wh"]
EDGE_EPISODE_COLS: list[str] = ["t_on_us", "t_off_us", "dur_s"]


class MergedRuns(NamedTuple):
    """Episode times after merging adjacent ON-runs, plus the grouping.

    t_on_us/t_off_us hold one entry per merged episode; group_bounds[i]
    is the index, in run order, of the first ON-run of episode i, so
    np.add.reduceat(run_values, group_bounds) reduces run-level values
    to episode level.
    """

    t_on_us: TimestampsUs
    t_off_us: TimestampsUs
    group_bounds: npt.NDArray[np.int64]


def rising_edges(step: npt.NDArray, thr: float) -> npt.NDArray[np.int64]:
    """Indices where step crosses above thr from at-or-below."""
    above = step > thr
    prev = np.concatenate(([False], above[:-1]))
    return np.flatnonzero(above & ~prev)


def on_runs(on: npt.NDArray[np.bool_]) -> tuple[TimestampsUs, TimestampsUs]:
    """Start and inclusive-end sample indices of contiguous True runs in on."""
    idx = np.flatnonzero(on)
    if idx.size == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[breaks + 1]]
    ends = np.r_[idx[breaks], idx[-1]]  # inclusive last ON sample per run
    return starts, ends


def merge_runs(
    ts_us: TimestampsUs,
    starts: TimestampsUs,
    ends: TimestampsUs,
    merge_gap_s: float,
    force_split: npt.NDArray[np.bool_] | None = None,
) -> MergedRuns:
    """Merge adjacent ON-runs whose OFF gap is at most merge_gap_s.

    The gap runs from a run's last ON sample to the next run's first ON
    sample. force_split, when given, has one entry per gap
    (len(starts) - 1); a True boundary starts a new episode even when the
    gap is small (the FHMM innovation-gate split uses this).
    """
    t_on, t_off = ts_us[starts], ts_us[ends]
    if t_on.size == 0:
        return MergedRuns(np.empty(0, np.int64), np.empty(0, np.int64), np.empty(0, np.int64))
    new_run = np.concatenate(([True], (t_on[1:] - t_off[:-1]) > merge_gap_s * US_PER_S))
    if force_split is not None:
        new_run[1:] |= force_split
    bounds = np.flatnonzero(new_run)
    group_ends = np.r_[bounds[1:] - 1, len(t_on) - 1]
    return MergedRuns(t_on[bounds], t_off[group_ends], bounds)


def build_episodes(
    series: pd.DataFrame,
    thr_w: float,
    min_dwell_s: float = 30.0,
    merge_gap_s: float = 12.0,
    max_hold_s: float = 60.0,
) -> pd.DataFrame:
    """Episodes (ON periods) from one submeter channel.

    ON := w > thr_w; rows at or below threshold, and any gap between rows,
    are OFF. ON-runs separated by at most merge_gap_s merge into one
    episode (bridges dropped samples); episodes shorter than min_dwell_s
    are dropped. energy_wh sums the ON-run samples only - bridged OFF gaps
    contribute nothing - under the step rule with the max_hold_s cap.
    Returns [t_on_us, t_off_us, dur_s, energy_wh].
    """
    ts = series["ts_us"].to_numpy(np.int64)
    w = series["w"].to_numpy(float)
    starts, ends = on_runs(w > thr_w)
    if starts.size == 0:
        return pd.DataFrame(columns=EPISODE_COLS)
    prefix_wus = np.concatenate(([0.0], np.cumsum(w * hold_us(ts, max_hold_s))))
    run_wh = (prefix_wus[ends + 1] - prefix_wus[starts]) / WUS_PER_WH
    merged = merge_runs(ts, starts, ends, merge_gap_s)
    dur_s = (merged.t_off_us - merged.t_on_us) / US_PER_S
    keep = dur_s >= min_dwell_s
    return pd.DataFrame(
        {
            "t_on_us": merged.t_on_us[keep],
            "t_off_us": merged.t_off_us[keep],
            "dur_s": dur_s[keep],
            "energy_wh": np.add.reduceat(run_wh, merged.group_bounds)[keep],
        }
    )


def episodes_from_edges(
    ts_us: TimestampsUs, rise_idx: npt.NDArray[np.int64], fall_times_us: TimestampsUs, min_dwell_s: float
) -> pd.DataFrame:
    """Pair each rising edge with the next falling edge after it; keep
    episodes at least min_dwell_s long. Returns [t_on_us, t_off_us, dur_s]."""
    if rise_idx.size == 0 or fall_times_us.size == 0:
        return pd.DataFrame(columns=EDGE_EPISODE_COLS)
    pos = np.searchsorted(fall_times_us, ts_us[rise_idx], side="right")
    ok = pos < len(fall_times_us)
    rise_idx, pos = rise_idx[ok], pos[ok]
    t_on = ts_us[rise_idx]
    t_off = fall_times_us[pos]
    dur_s = (t_off - t_on) / US_PER_S
    keep = dur_s >= min_dwell_s
    return pd.DataFrame(
        {"t_on_us": t_on[keep], "t_off_us": t_off[keep], "dur_s": dur_s[keep]}
    )
