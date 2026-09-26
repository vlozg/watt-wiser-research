"""Turning calibration intervals into what each appliance looks like.

Two ways to measure a device, both using only the aggregate meter:

  presses  each interval is a time someone switched the device on. We skip a
           few seconds at both ends, then read the average watts and how much
           they wobble.
  duty     for a device that cycles on its own (a fridge), read the middle
           watts of each ON stretch and take the middle of those readings,
           which is not thrown off by other devices running at the same time.

The caller supplies the intervals; nothing here opens a file.
"""

from __future__ import annotations

import numpy as np

from wattwiser.experiments.models.fhmm.config import DEFAULT_CONFIG, FHMMConfig
from wattwiser.experiments.models.fhmm.types import (
    DeviceParams,
    IntervalArrays,
    PowerSeries,
)

EDGE_TRIM_S: float = 10.0   # seconds skipped at each end of an interval
MIN_READINGS: int = 2       # an interval shorter than this tells us nothing


def never_claims(floor_w: float, typical_on_s: float, cadence_s: float,
                 config: FHMMConfig = DEFAULT_CONFIG) -> DeviceParams:
    """A fit that stays quiet: the level sits on the floor, so the device can
    never be claimed. Used when there is nothing to measure."""
    return DeviceParams(level_w=floor_w, spread_w=config.min_spread_w,
                        stay_on_prob=1.0 - cadence_s / typical_on_s,
                        on_duration_s=typical_on_s)


def from_press_sessions(series: PowerSeries, sessions: IntervalArrays, floor_w: float,
                        cadence_s: float,
                        config: FHMMConfig = DEFAULT_CONFIG) -> DeviceParams | None:
    """Measure a device from its switch-on intervals.

    Level = average watts above the floor; spread = how much those watts
    wobble; ON length = average interval length. Returns None when the device
    does not rise clearly above the floor, or when no interval is long enough.
    """
    # for each interval: skip the ends, then read average watts, wobble and length
    t_on, t_off = sessions
    if t_on.size == 0:
        return None
    trim_us = int(EDGE_TRIM_S * 1e6)
    levels_w: list[float] = []
    spreads_w: list[float] = []
    durations_s: list[float] = []
    for on_us, off_us in zip(t_on, t_off):
        i0 = int(np.searchsorted(series.ts_us, on_us + trim_us, side="left"))
        i1 = int(np.searchsorted(series.ts_us, max(off_us - trim_us, on_us + trim_us),
                                 side="right"))
        if i1 - i0 < MIN_READINGS:
            continue
        watts = series.w[i0:i1]
        levels_w.append(float(watts.mean()) - floor_w)
        spreads_w.append(float(watts.std()))
        durations_s.append((off_us - on_us) / 1e6)
    if not levels_w:
        return None
    level_w = float(np.mean(levels_w))
    if level_w < config.min_level_w:
        return None
    spread_w = max(float(np.mean(spreads_w)), config.min_spread_w)
    on_duration_s = float(np.clip(float(np.mean(durations_s)), *config.dwell_clamp_s))
    return DeviceParams(
        level_w=level_w,
        spread_w=spread_w,
        stay_on_prob=1.0 - 1.0 / max(on_duration_s / cadence_s, 1.0),
        # a device ON for n readings stays ON again with chance 1 - 1/n
        on_duration_s=on_duration_s,
    )


def from_duty_intervals(series: PowerSeries, intervals: IntervalArrays, floor_w: float,
                        cadence_s: float, spread_floor_w: float = 8.0,
                        config: FHMMConfig = DEFAULT_CONFIG) -> DeviceParams | None:
    """Measure a cycling device from its ON intervals, aggregate only."""
    # middle watts of each ON stretch, minus the floor -> middle of those numbers
    t_on, t_off = intervals
    if t_on.size == 0:
        return None
    levels_w: list[float] = []
    durations_s: list[float] = []
    for on_us, off_us in zip(t_on, t_off):
        i0 = int(np.searchsorted(series.ts_us, on_us, side="left"))
        i1 = int(np.searchsorted(series.ts_us, off_us, side="right"))
        if i1 <= i0:
            continue
        levels_w.append(float(np.median(series.w[i0:i1])) - floor_w)
        durations_s.append((off_us - on_us) / 1e6)
    if not levels_w:
        return None
    level_w = float(np.median(levels_w))
    if level_w < config.min_level_w:
        return None
    on_duration_s = float(np.clip(float(np.median(durations_s)), *config.dwell_clamp_s))
    return DeviceParams(
        level_w=level_w,
        spread_w=max(spread_floor_w, config.min_spread_w),
        stay_on_prob=1.0 - 1.0 / max(on_duration_s / cadence_s, 1.0),
        on_duration_s=on_duration_s,
    )
