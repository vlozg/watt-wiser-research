"""The FHMM itself: fit it on calibration intervals, then read a power series.

    model = FHMM(devices, rules, cadence_s=6.0, floor_w=..., noise_w=...)
    model.fit(calibration_series, sessions, passive)
    decoded = model.predict(series)
    episodes = model.episodes(decoded, "kettle")
    watts = model.claimed_power(decoded, "kettle")

The whole object is small: it keeps the device list, the per-device switching
rules, the cadence, the floor and noise, and one row of fitted parameters.
It never reads a file and never sees a house.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
import pandas as pd

from wattwiser.experiments.models.fhmm import calibrate
from wattwiser.experiments.models.fhmm.config import DEFAULT_CONFIG, FHMMConfig
from wattwiser.experiments.models.fhmm.decode import decode as decode_window
from wattwiser.experiments.models.fhmm.episodes import (
    claimed_power,
    device_episodes,
    unexplained_share,
)
from wattwiser.experiments.models.fhmm.types import (
    Decoded,
    DeviceRule,
    FHMMParams,
    IntervalArrays,
    PowerSeries,
)


@dataclass
class FHMM:
    """A model that explains the aggregate as a sum of ON/OFF devices.

    devices    device names; the decode columns follow this order
    rules      per-device switching rule (min ON length, merge gap, typical ON)
    cadence_s  how many seconds between readings
    floor_w    the watts the house draws when nothing is on
    noise_w    how much a quiet reading wobbles, in watts
    config     the frozen numbers
    params     what fit() measured, one row per device
    """

    devices: tuple[str, ...]
    rules: Mapping[str, DeviceRule]
    cadence_s: float
    floor_w: float
    noise_w: float
    config: FHMMConfig = DEFAULT_CONFIG
    params: FHMMParams | None = field(default=None, init=False)

    # ---------------------------------------------------------------- fitting

    def fit(self, series: PowerSeries, sessions: Mapping[str, IntervalArrays],
            passive: Mapping[str, IntervalArrays] | None = None) -> "FHMM":
        """Measure every device and keep the result in self.params.

        sessions: device -> switch-on intervals to measure it from.
        passive:  device -> ON intervals, for a device that cycles on its own.
        A device with nothing to measure, or one that does not rise above the
        floor, is set to never claim.
        """
        # measure each device in order and line the results up as one row
        n_dev = len(self.devices)
        level = np.zeros((1, n_dev), np.float32)
        spread = np.zeros((1, n_dev), np.float32)
        stay_on = np.zeros((1, n_dev), np.float32)
        passive = passive or {}
        for i, device in enumerate(self.devices):
            measured = None
            if device in passive:
                measured = calibrate.from_duty_intervals(
                    series, passive[device], self.floor_w, self.cadence_s,
                    config=self.config)
            if measured is None and device in sessions:
                measured = calibrate.from_press_sessions(
                    series, sessions[device], self.floor_w, self.cadence_s,
                    config=self.config)
            if measured is None:
                measured = calibrate.never_claims(
                    self.floor_w, self.rules[device].typical_on_s,
                    self.cadence_s, self.config)
            level[0, i] = measured.level_w
            spread[0, i] = measured.spread_w
            stay_on[0, i] = measured.stay_on_prob
        self.params = FHMMParams(
            level_w=level, spread_w=spread, stay_on_prob=stay_on,
            noise_w=np.full(1, self.noise_w, np.float32), floor_w=self.floor_w)
        return self

    # -------------------------------------------------------------- decoding

    def decode(self, series: PowerSeries, params: FHMMParams,
               t0_us: int, t1_us: int) -> Decoded:
        """Decode a window with parameters you supply (one row per fit)."""
        return decode_window(series, params, t0_us, t1_us, self.devices,
                             self.cadence_s, self.config)

    def predict(self, series: PowerSeries, t0_us: int | None = None,
                t1_us: int | None = None) -> Decoded:
        """Decode the whole series, or the part inside [t0_us, t1_us)."""
        if self.params is None:
            raise RuntimeError("call fit() before predict()")
        start = int(series.ts_us[0]) if t0_us is None else t0_us
        end = int(series.ts_us[-1]) + 1 if t1_us is None else t1_us
        return self.decode(series, self.params, start, end)

    # -------------------------------------------------------------- readings

    def level_of(self, device: str, params_row: int = 0) -> float:
        """The fitted level in watts of one device in one row."""
        if self.params is None:
            raise RuntimeError("call fit() before reading level_of()")
        return float(self.params.level_w[params_row, self.devices.index(device)])

    def claimed_power(self, decoded: Decoded, device: str,
                      params_row: int = 0) -> np.ndarray:
        """Watts of one device over the decoded window: its level while claimed,
        else zero."""
        return claimed_power(decoded, device, self.level_of(device, params_row),
                             params_row, self.config)

    def episodes(self, decoded: Decoded, device: str,
                 params_row: int = 0) -> pd.DataFrame:
        """Episodes of one device (columns: device, t_on_us, t_off_us, level_w)."""
        return device_episodes(decoded, device, self.level_of(device, params_row),
                               self.rules[device], self.cadence_s, params_row,
                               self.config)

    def unexplained_share(self, decoded: Decoded, grid_w: np.ndarray,
                          params_row: int = 0) -> float:
        """Share of the window's energy the decoder does not account for."""
        return unexplained_share(decoded, grid_w, params_row, self.config)
