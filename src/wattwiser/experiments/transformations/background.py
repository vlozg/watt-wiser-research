"""The always-on floor and the noise around it, estimated from the aggregate.

floor_w  the 10th percentile of the watts: the level a quiet house sits at
noise_w  how much a quiet reading wobbles, from the median absolute deviation
         of the watts above the floor (a median, not a plain spread, so a
         fridge that runs part of the time does not blow the number up)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from wattwiser.experiments.transformations.resample import bucket_mean
from wattwiser.experiments.transformations.types import PowerSeries

DEFAULT_SUBSAMPLE: int = 7
FLOOR_PERCENTILE: float = 10.0
MEDIAN_ABS_DEVIATION_TO_SD: float = 1.4826
MIN_NOISE_W: float = 1.0


@dataclass(frozen=True)
class Background:
    """The two numbers a decoder needs about a quiet house."""

    floor_w: float
    noise_w: float


def background_of(w: npt.NDArray[np.float64]) -> Background:
    """Floor and noise of a watts array, by the frozen percentile/MAD recipe."""
    # watts -> 10th percentile floor -> spread of the watts above it
    floor = float(np.percentile(w, FLOOR_PERCENTILE))
    resid = w - floor
    mad = float(np.median(np.abs(resid - np.median(resid))))
    return Background(floor_w=floor,
                      noise_w=float(max(MEDIAN_ABS_DEVIATION_TO_SD * mad, MIN_NOISE_W)))


def estimate_background(series: PowerSeries, t_end_us: int,
                        subsample: int = DEFAULT_SUBSAMPLE) -> Background:
    """Floor and noise over the readings before t_end_us.

    In practice t_end_us is the split time, so the estimate covers exactly the
    calibration span. subsample thins the readings to keep it fast."""
    # readings before t_end -> every subsample-th one -> frozen recipe
    return background_of(series.w[series.ts_us < t_end_us][::subsample])


def estimate_background_bucketed(series: PowerSeries, t_end_us: int,
                                 bucket_s: float = 60.0) -> Background:
    """The same recipe on a bucket-mean series.

    Averaging readings shrinks the noise, so the noise of a coarser series has
    to be measured on that coarser series, not carried over from the native one.
    """
    coarse = bucket_mean(series, bucket_s)
    return background_of(coarse.w[coarse.ts_us < t_end_us])
