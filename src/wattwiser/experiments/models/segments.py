"""Finding ON stretches in a list of yes/no flags, and joining nearby ones.

This is the model layer's own copy of that logic. The data layer has a
parallel copy in wattwiser.experiments.segmentation for submeter channels;
models keep their own so they do not import from the layers above them.
"""

from __future__ import annotations

import numpy as np

from wattwiser.experiments.models.fhmm.types import TimestampsUs


def runs(ts_us: TimestampsUs, is_on: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """First and last index of every stretch of True in is_on."""
    idx = np.flatnonzero(is_on)
    if idx.size == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    breaks = np.flatnonzero(np.diff(idx) > 1)
    return np.r_[idx[0], idx[breaks + 1]], np.r_[idx[breaks], idx[-1]]


def merge_runs(ts_us: TimestampsUs, starts: np.ndarray, ends: np.ndarray,
               merge_gap_us: int, masked_count: np.ndarray | None = None,
               split_at_masked: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Join stretches whose OFF gap is at most merge_gap_us.

    masked_count, when given, is the running total of unexplained readings; a
    gap holding at least split_at_masked of them is kept apart even if short.
    Returns the start, end and first-stretch index of every merged episode.
    """
    start_us, end_us = ts_us[starts], ts_us[ends]
    new_episode = np.concatenate(([True], (start_us[1:] - end_us[:-1]) > merge_gap_us))
    if masked_count is not None and len(starts) > 1:
        gap_hi = np.searchsorted(ts_us, start_us[1:], side="left")
        gap_lo = np.searchsorted(ts_us, end_us[:-1], side="right")
        masked_in_gap = masked_count[gap_hi] - masked_count[gap_lo]
        new_episode[1:] |= masked_in_gap >= split_at_masked
    first = np.flatnonzero(new_episode)
    last = np.r_[first[1:] - 1, len(start_us) - 1]
    return start_us[first], end_us[last], first
