"""A model that explains the aggregate meter as a sum of ON/OFF devices.

    model.py      FHMM: fit on calibration intervals, then predict watts/episodes
    decode.py     the search over the 2^D ON/OFF combinations
    calibrate.py  calibration intervals -> level, spread, ON length
    episodes.py   decoded window -> episodes, claimed watts, unexplained share
    config.py     the frozen numbers, in one place
    types.py      the plain types this model exchanges (declared here, not imported)

Read the whole model from model.py. It imports nothing from the dataset,
transformation or primitive modules; the caller wires those together.
"""

from wattwiser.experiments.models.fhmm.config import DEFAULT_CONFIG, FHMMConfig
from wattwiser.experiments.models.fhmm.model import FHMM
from wattwiser.experiments.models.fhmm.types import (
    Decoded,
    DeviceParams,
    DeviceRule,
    FHMMParams,
    IntervalArrays,
    PowerSeries,
    PowerW,
    TimestampsUs,
)

__all__ = [
    "DEFAULT_CONFIG",
    "FHMMConfig",
    "FHMM",
    "Decoded",
    "DeviceParams",
    "DeviceRule",
    "FHMMParams",
    "IntervalArrays",
    "PowerSeries",
    "PowerW",
    "TimestampsUs",
]
