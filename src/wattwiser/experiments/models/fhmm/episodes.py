"""Turning a decoded window into episodes and claimed watts.

An episode is a stretch where the decoder says a device is ON, it is sure
enough (probability at least min_prob_on), and the readings are explained
rather than masked. Short episodes are dropped, and nearby ones are joined
unless a long unexplained stretch sits between them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from wattwiser.experiments.models.fhmm.config import DEFAULT_CONFIG, FHMMConfig
from wattwiser.experiments.models.fhmm.types import Decoded, DeviceRule
from wattwiser.experiments.models.segments import merge_runs, runs

EPISODE_COLS: list[str] = ["device", "t_on_us", "t_off_us", "level_w"]


def device_episodes(decoded: Decoded, device: str, level_w: float, rule: DeviceRule,
                    cadence_s: float, params_row: int = 0,
                    config: FHMMConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """The episodes of one device in one row of a fit."""
    # ON readings -> stretches -> join nearby ones -> drop the short ones
    column = decoded.devices.index(device)
    is_on = ((decoded.on[:, params_row, column] == 1)
             & (decoded.prob_on[:, params_row, column] >= config.min_prob_on)
             & (decoded.unexplained[:, params_row] == 0))
    starts, ends = runs(decoded.ts_us, is_on)
    if len(starts) == 0:
        return pd.DataFrame(columns=EPISODE_COLS)
    split_steps = max(int(config.split_gap_s / cadence_s), 1)
    masked_total = np.concatenate(([0], np.cumsum(decoded.unexplained[:, params_row])))
    t_on, t_off, _ = merge_runs(decoded.ts_us, starts, ends,
                                int(rule.merge_gap_s * 1e6), masked_total, split_steps)
    long_enough = (t_off - t_on) / 1e6 >= rule.min_on_s
    return pd.DataFrame({"device": device, "t_on_us": t_on[long_enough],
                         "t_off_us": t_off[long_enough], "level_w": level_w})


def claimed_power(decoded: Decoded, device: str, level_w: float,
                  params_row: int = 0,
                  config: FHMMConfig = DEFAULT_CONFIG) -> np.ndarray:
    """Watts over the window: level_w while the device is claimed ON, else 0."""
    column = decoded.devices.index(device)
    claimed = ((decoded.on[:, params_row, column] == 1)
               & (decoded.prob_on[:, params_row, column] >= config.min_prob_on)
               & (decoded.unexplained[:, params_row] == 0))
    return np.where(claimed, level_w, 0.0)


def unexplained_share(decoded: Decoded, grid_w: np.ndarray, params_row: int = 0,
                      config: FHMMConfig = DEFAULT_CONFIG) -> float:
    """Share (0..1) of the window's energy that sits on unexplained readings -
    the part of the aggregate the decoder is not accounting for."""
    hold_us = np.minimum(np.diff(decoded.ts_us, append=decoded.ts_us[-1]),
                         config.energy_hold_s * 1_000_000)
    energy = grid_w * hold_us
    total = energy.sum()
    return float(energy[decoded.unexplained[:, params_row] == 1].sum() / total) if total else 0.0
