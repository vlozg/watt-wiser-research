"""Power-to-energy accounting for metered power series.

The gap policy (one rule everywhere): a reading holds its value until
the next reading of the same channel, but for at most max_hold_s;
anything past that hold is left unintegrated (unknown, not zero). The
same rule prices mains and submeter energy, so shares are like-for-like.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from wattwiser.experiments.units import US_PER_S, WUS_PER_WH, PowerW, TimestampsUs


def hold_us(ts_us: TimestampsUs, max_hold_s: float) -> npt.NDArray[np.float64]:
    """Hold duration of each sample under the gap policy, in microseconds.

    Sample i holds for min(dt_i, max_hold_s), dt_i being the gap to the
    next sample; the last sample of a series holds for zero time.
    """
    dt_us = np.diff(ts_us, append=ts_us[-1])
    return np.minimum(dt_us, max_hold_s * US_PER_S)


def step_energy_cumsum_wh(
    ts_us: TimestampsUs, w: PowerW, max_hold_s: float = 60.0
) -> npt.NDArray[np.float64]:
    """Prefix sums of step-rule energy (Wh) per sample.

    cum[i] integrates samples 0..i, so a window's energy is
    cum[i1] - cum[i0] via window_energy_wh.
    """
    return np.cumsum(w * hold_us(ts_us, max_hold_s)) / WUS_PER_WH


def window_energy_wh(
    ts_us: TimestampsUs, cum_wh: npt.NDArray[np.float64], t0_us: int, t1_us: int
) -> float:
    """Step-rule energy of a series inside [t0_us, t1_us] from its prefix sums."""
    i0 = int(np.searchsorted(ts_us, t0_us, side="left"))
    i1 = int(np.searchsorted(ts_us, t1_us, side="right"))
    hi = float(cum_wh[i1 - 1]) if i1 > 0 else 0.0
    lo = float(cum_wh[i0 - 1]) if i0 > 0 else 0.0
    return max(hi - lo, 0.0)
