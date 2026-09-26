"""The house as one experiment task: series, device rules, split and labels.

One call assembles everything an experiment needs from the curated tree - the
aggregate series, the rules for the in-focus devices, the calibration/
evaluation split - and, on request, the device meters and their ground-truth
episodes. Device meters are for scoring only; they never enter a model.

This is the only place a file becomes a series: models get arrays,
transformations get a series, and the notebook chains them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import pandas as pd

from wattwiser.experiments.data_loader import (
    gold_parquet_path,
    load_device_profiles,
    load_gt_cycles,
    load_power_series,
    load_split_us,
)
from wattwiser.experiments.segmentation import build_episodes

TimestampsUs = npt.NDArray[np.int64]
PowerW = npt.NDArray[np.float64]
# One device's intervals as two equal-length arrays: start times and end times.
IntervalArrays = tuple[TimestampsUs, TimestampsUs]

EPISODE_COLS: list[str] = ["t_on_us", "t_off_us", "dur_s", "energy_wh"]
DEFAULT_ENERGY_HOLD_S: float = 60.0


class PowerSeries(NamedTuple):
    """One power meter reading: times and watts, same length, sorted by time."""

    ts_us: TimestampsUs
    w: PowerW

    def window(self, t0_us: int, t1_us: int) -> "PowerSeries":
        """The readings with t0_us <= ts_us < t1_us."""
        inside = (self.ts_us >= t0_us) & (self.ts_us < t1_us)
        return PowerSeries(self.ts_us[inside], self.w[inside])

    def before(self, t_us: int) -> "PowerSeries":
        """The readings strictly before t_us (the calibration span)."""
        if self.ts_us.size == 0:
            return self
        return self.window(int(self.ts_us[0]), t_us)

    def since(self, t_us: int) -> "PowerSeries":
        """The readings at or after t_us (the evaluation span)."""
        if self.ts_us.size == 0:
            return self
        return self.window(t_us, int(self.ts_us[-1]) + 1)


@dataclass(frozen=True)
class DeviceSpec:
    """One in-focus device and the rules its profile pins down."""

    name: str
    kind: str
    on_threshold_w: float   # watts above the floor that count as ON
    min_on_s: float         # ON stretches shorter than this are dropped
    merge_gap_s: float      # ON stretches closer than this are joined


@dataclass(frozen=True)
class HouseTask:
    """One house's experiment view, loaded once from the curated tree.

    mains     the aggregate series (the only model input)
    devices   in-focus devices with their rules, in profile order
    split_us  calibration before this time, evaluation at or after it
    """

    dataset: str
    house: str
    mains: PowerSeries
    devices: tuple[DeviceSpec, ...]
    split_us: int
    energy_hold_s: float = DEFAULT_ENERGY_HOLD_S
    _submeter_cache: dict = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def load(cls, dataset: str, house: str) -> "HouseTask":
        """Build the task view of one house from the gold layer."""
        # aggregate parquet -> series; device profile -> in-focus rules;
        # split file -> split_us
        df = load_power_series(gold_parquet_path(dataset, house, "mains"))
        mains = PowerSeries(df["ts_us"].to_numpy(np.int64), df["w"].to_numpy(float))
        profiles = load_device_profiles(dataset, house)
        in_focus = profiles[profiles["in_focus"] == True]  # noqa: E712
        devices = tuple(
            DeviceSpec(name=row["device"], kind=row["class"],
                       on_threshold_w=float(row["thr_used_w"]),
                       min_on_s=float(row["dwell_s"]),
                       merge_gap_s=float(row["merge_s"]))
            for _, row in in_focus.iterrows()
        )
        return cls(dataset=dataset, house=house, mains=mains, devices=devices,
                   split_us=load_split_us(dataset, house))

    # --------------------------------------------------------------- devices

    def device(self, name: str) -> DeviceSpec:
        """The rules of one in-focus device (KeyError when it is not in focus)."""
        for spec in self.devices:
            if spec.name == name:
                return spec
        raise KeyError(f"{name!r} is not in focus for {self.dataset}/{self.house}")

    @property
    def device_names(self) -> tuple[str, ...]:
        """In-focus device names, in profile order."""
        return tuple(spec.name for spec in self.devices)

    # ---------------------------------------------------------------- series

    def mains_before_split(self) -> PowerSeries:
        """The aggregate before the split (the calibration span)."""
        return self.mains.before(self.split_us)

    def mains_after_split(self) -> PowerSeries:
        """The aggregate at or after the split (the evaluation span)."""
        return self.mains.since(self.split_us)

    def submeter(self, name: str) -> PowerSeries:
        """One device's own meter - for scoring only, never a model input."""
        if name not in self._submeter_cache:
            df = load_power_series(gold_parquet_path(self.dataset, self.house, name))
            self._submeter_cache[name] = PowerSeries(
                df["ts_us"].to_numpy(np.int64), df["w"].to_numpy(float))
        return self._submeter_cache[name]

    # ---------------------------------------------------------------- labels

    def gt_cycles(self, name: str) -> pd.DataFrame:
        """Hand-marked plus rule-derived cycle marks of one device, by start time."""
        gt = load_gt_cycles(self.dataset, self.house)
        return gt[gt["device"] == name].sort_values("t_on_us").reset_index(drop=True)

    def press_intervals(self, name: str, before_us: int | None = None) -> IntervalArrays:
        """Switch-on intervals to calibrate on: cycle marks, optionally
        restricted to those starting before before_us."""
        marks = self.gt_cycles(name)
        if before_us is not None:
            marks = marks[marks["t_on_us"] < before_us]
        return (marks["t_on_us"].to_numpy(np.int64),
                marks["t_off_us"].to_numpy(np.int64))

    def gt_episodes(self, name: str, t0_us: int | None = None,
                    t1_us: int | None = None) -> pd.DataFrame:
        """Ground-truth episodes of one device: its meter through its rules.

    The window [t0_us, t1_us) applies only when t0_us is given.
    """
        # device meter -> optional clip -> threshold + minimum length + merge
        series = self.submeter(name)
        if t0_us is not None:
            end = t1_us if t1_us is not None else int(series.ts_us[-1]) + 1
            series = series.window(t0_us, end)
        rule = self.device(name)
        return build_episodes(pd.DataFrame({"ts_us": series.ts_us, "w": series.w}),
                              rule.on_threshold_w, min_dwell_s=rule.min_on_s,
                              merge_gap_s=rule.merge_gap_s,
                              max_hold_s=self.energy_hold_s)
