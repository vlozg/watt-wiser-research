"""The simple baseline: switch a device on when the meter goes above a limit.

A reading above the ON threshold turns the device on; it turns off only once
that reading falls below a slightly lower limit, so a wobbling signal does not
flicker. Short episodes are dropped and nearby ones joined. This is the bar
the learned model has to beat, and it claims a level equal to its threshold.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from wattwiser.experiments.models.fhmm.config import DEFAULT_CONFIG, FHMMConfig
from wattwiser.experiments.models.fhmm.types import PowerSeries
from wattwiser.experiments.models.segments import merge_runs, runs

EPISODE_COLS: list[str] = ["device", "t_on_us", "t_off_us", "level_w"]


def anchor_episodes(series: PowerSeries, t0_us: int, t1_us: int, on_threshold_w: float,
                    min_on_s: float, merge_gap_s: float,
                    config: FHMMConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Episodes of the aggregate above on_threshold_w, in [t0_us, t1_us)."""
    # readings above the limit -> ON; below the lower limit -> OFF; in between
    # -> keep whatever the last clear reading said
    g0 = int(np.searchsorted(series.ts_us, t0_us, side="left"))
    g1 = int(np.searchsorted(series.ts_us, t1_us, side="right"))
    seg_ts = series.ts_us[g0:g1]
    seg_w = series.w[g0:g1]
    off_threshold_w = on_threshold_w * config.anchor_off_factor
    mark = np.where(seg_w > on_threshold_w, 1,
                    np.where(seg_w < off_threshold_w, 0, -1))
    decided = mark != -1
    last_decided = np.maximum.accumulate(np.where(decided, np.arange(len(mark)), -1))
    state = np.where(last_decided >= 0, mark[np.maximum(last_decided, 0)], 0)
    starts, ends = runs(seg_ts, state == 1)
    if len(starts) == 0:
        return pd.DataFrame(columns=EPISODE_COLS)
    t_on, t_off, _ = merge_runs(seg_ts, starts, ends, int(merge_gap_s * 1e6))
    long_enough = (t_off - t_on) / 1e6 >= min_on_s
    return pd.DataFrame({"device": "", "t_on_us": t_on[long_enough],
                         "t_off_us": t_off[long_enough], "level_w": on_threshold_w})
