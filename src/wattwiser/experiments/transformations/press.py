"""Choosing which calibration intervals a device is measured on.

Two steps of the press-calibration instrument, kept here because they pick
data rather than fit anything:

  overlap_flagged   a session counts as unusable when other devices are on
                    for more than max_cover of its length
  draw_sessions     draw sessions at random until k usable ones are found;
                    unusable draws do not count toward k

Intervals in, intervals out: nothing here reads a file or knows about a model.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from wattwiser.experiments.transformations.types import IntervalArrays


def intervals_of(episodes: pd.DataFrame) -> IntervalArrays:
    """The (t_on_us, t_off_us) arrays of an episode or cycle table."""
    return (episodes["t_on_us"].to_numpy(np.int64),
            episodes["t_off_us"].to_numpy(np.int64))


def overlap_flagged(sessions: IntervalArrays, others: Mapping[str, IntervalArrays],
                    max_cover: float) -> np.ndarray:
    """Which sessions are unusable because other devices cover too much of them.

    For each session, add up how long the other devices were on inside it;
    flag the session when that is more than max_cover of its length.
    """
    # session (t_on, t_off) + other devices intervals -> covered share -> flags
    t_on, t_off = sessions
    duration_us = np.maximum(t_off - t_on, 1).astype(float)
    covered_us = np.zeros(len(t_on), float)
    for other_on, other_off in others.values():
        if other_on.size == 0:
            continue
        for k in range(len(t_on)):
            overlap = np.minimum(other_off, t_off[k]) - np.maximum(other_on, t_on[k])
            covered_us[k] += float(np.maximum(overlap, 0).sum())
    return covered_us / duration_us > max_cover


def draw_sessions(pool: IntervalArrays, k: int, rng: np.random.Generator,
                  others: Mapping[str, IntervalArrays],
                  max_cover: float) -> tuple[IntervalArrays, int]:
    """Draw k usable sessions at random (with replacement), as a calibration set.

    Returns the intervals and how many draws it took. Repeated draws are
    allowed; a draw of a session already used is fine."""
    # press pool -> draw k at a time -> drop flagged rows -> join, keep first k
    t_on, t_off = pool
    nothing = (np.empty(0, np.int64), np.empty(0, np.int64))
    if t_on.size == 0 or k <= 0:
        return nothing, 0
    kept: list[IntervalArrays] = []
    attempts = 0
    max_attempts = max(4 * k, 8)
    while sum(len(x[0]) for x in kept) < k and attempts < max_attempts:
        picked = rng.integers(0, len(t_on), size=k)
        draw = (t_on[picked], t_off[picked])
        attempts += len(picked)
        flagged = overlap_flagged(draw, others, max_cover)
        kept.append((draw[0][~flagged], draw[1][~flagged]))
    if not kept:
        return nothing, attempts
    joined = (np.concatenate([x[0] for x in kept]),
              np.concatenate([x[1] for x in kept]))
    return (joined[0][:k], joined[1][:k]), attempts
