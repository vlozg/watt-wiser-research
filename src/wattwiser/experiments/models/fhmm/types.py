"""The types the model layer exchanges. They are declared here on purpose:
a model is handed plain arrays and numbers, so it never has to know where a
house, a file or a resampling step is defined.

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

    The dataset layer builds one of these from a parquet file and the
    transformation layer reads one; both have the same two fields, so either
    can be passed straight to a model.
    """

    ts_us: TimestampsUs
    w: PowerW

    def window(self, t0_us: int, t1_us: int) -> "PowerSeries":
        """The readings with t0_us <= ts_us < t1_us."""
        inside = (self.ts_us >= t0_us) & (self.ts_us < t1_us)
        return PowerSeries(self.ts_us[inside], self.w[inside])


class DeviceRule(NamedTuple):
    """What a model needs to know about how one appliance switches.

    min_on_s      episodes shorter than this are thrown away
    merge_gap_s   ON stretches closer than this are joined into one episode
    typical_on_s  ON length assumed when the device has no clear level
    """

    min_on_s: float
    merge_gap_s: float
    typical_on_s: float


class DeviceParams(NamedTuple):
    """What one appliance looks like in the aggregate, once fitted.

    level_w        watts the aggregate rises by while it is ON
    spread_w       typical wobble of those watts around level_w
    stay_on_prob   chance it is still ON at the next reading
    on_duration_s  typical ON length in seconds
    """

    level_w: float
    spread_w: float
    stay_on_prob: float
    on_duration_s: float


class FHMMParams(NamedTuple):
    """A whole fit: one row per set of devices, D devices per row.

    level_w / spread_w / stay_on_prob are (rows, D) float32; noise_w is
    (rows,) float32; floor_w is one number shared by every row.
    """

    level_w: npt.NDArray[np.float32]
    spread_w: npt.NDArray[np.float32]
    stay_on_prob: npt.NDArray[np.float32]
    noise_w: npt.NDArray[np.float32]
    floor_w: float


class Decoded(NamedTuple):
    """The answer for one window of readings, for every row of a fit.

    ts_us         (T,)      times of the decoded readings
    devices       (D,)      device names, in the order of the arrays
    on            (T, rows, D) 1 where that device is ON, else 0
    prob_on       (T, rows, D) how sure the decoder is that it is ON, 0..1
    unexplained   (T, rows) 1 where the readings do not fit the decoded states
    loglik        (rows,)   how well the fit explains the window, higher is better
    """

    ts_us: TimestampsUs
    devices: tuple[str, ...]
    on: npt.NDArray[np.int8]
    prob_on: npt.NDArray[np.float32]
    unexplained: npt.NDArray[np.int8]
    loglik: npt.NDArray[np.float64]
