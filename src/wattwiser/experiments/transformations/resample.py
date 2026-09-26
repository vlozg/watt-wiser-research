"""Putting a series on a coarser grid.

The project uses one resampling rule: bucket mean. Every bucket gets the mean
of the readings inside it and is stamped with the bucket midpoint. The two
small helpers keep switching and noise correct when a decode moves to a
coarser grid: the ON chance per step changes with the step length, and a
spread loses only the part that comes from the averaging itself.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from wattwiser.experiments.transformations.types import PowerSeries


def bucket_mean(series: PowerSeries, bucket_s: float) -> PowerSeries:
    """Mean watts per bucket_s-second bucket, stamped at the bucket midpoint."""
    # native readings -> bucket ids -> mean per bucket -> midpoints + means
    bucket_us = int(bucket_s * 1e6)
    bucket_id = series.ts_us // bucket_us
    unique_buckets, first_index = np.unique(bucket_id, return_index=True)
    readings_per_bucket = np.diff(np.r_[first_index, len(bucket_id)]).astype(float)
    return PowerSeries(unique_buckets * bucket_us + bucket_us // 2,
                       np.add.reduceat(series.w, first_index) / readings_per_bucket)


def stay_on_prob_at(stay_on_prob: npt.NDArray, cadence_from: float,
                    cadence_to: float) -> npt.NDArray[np.float32]:
    """The same ON chance expressed per coarser step, keeping the average ON
    length in seconds unchanged."""
    off_chance = (1.0 - np.asarray(stay_on_prob, np.float64)) * (cadence_from / cadence_to)
    return (1.0 - off_chance).astype(np.float32)


def spread_at_cadence(spread_w: npt.NDArray, noise_from: float,
                      noise_to: float) -> npt.NDArray[np.float32]:
    """Device spreads at another grid: only the noise part averages away.

    A fitted spread mixes the device's own variation with the ambient noise.
    Averaging removes part of the noise, so strip the old noise and add the new
    one back. Levels do not change, because bucket means keep the mean."""
    device_part = np.maximum(np.asarray(spread_w, np.float64)**2 - noise_from**2, 0.0)
    return np.sqrt(device_part + noise_to**2).astype(np.float32)
