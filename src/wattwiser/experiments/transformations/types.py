"""The types a transformation exchanges. They are declared here on purpose:
a transformation takes plain arrays and gives plain arrays back, so it never
has to know where a house, a model or a file is defined.

Units: timestamps are int64 UTC microseconds, power is float64 watts.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
import numpy.typing as npt

TimestampsUs = npt.NDArray[np.int64]
PowerW = npt.NDArray[np.float64]
# An interval list is two equal-length arrays: start times and end times.
IntervalArrays = tuple[TimestampsUs, TimestampsUs]


class PowerSeries(NamedTuple):
    """One power meter reading: times and watts, same length, sorted by time.

    The dataset and model layers declare the same two fields, so a series from
    any of them can be passed straight in.
    """

    ts_us: TimestampsUs
    w: PowerW

    def window(self, t0_us: int, t1_us: int) -> "PowerSeries":
        """The readings with t0_us <= ts_us < t1_us."""
        inside = (self.ts_us >= t0_us) & (self.ts_us < t1_us)
        return PowerSeries(self.ts_us[inside], self.w[inside])
