"""Unit constants and series dtypes shared by the power-data primitives.

Conventions: timestamps are int64 UTC microseconds (ts_us), power is
float64 active watts (w), durations are seconds at function boundaries,
energy is watt-hours (Wh). Names carry their unit as a suffix: _us, _s,
_w, _wh.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

US_PER_S: int = 1_000_000
WUS_PER_WH: float = 3.6e9  # 1 Wh = 3600 W*s = 3.6e9 W*microsecond

# A timestamp array and a power array, of equal length.
TimestampsUs = npt.NDArray[np.int64]
PowerW = npt.NDArray[np.float64]
