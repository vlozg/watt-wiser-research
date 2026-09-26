"""Every fixed number the FHMM uses, frozen 2026-09-22.

Levels and spreads are watts, durations are seconds. These values were
chosen once and then never changed, so a decode today repeats a decode from
the campaign. (The old campaign code calls some of them mu, sd, innov_c and
unknown_theta; the meanings are the same.)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FHMMConfig:
    """Settings shared by the fit, the decode and the episode extraction."""

    # campaign shape
    k_grid: tuple[int, ...] = (1, 2, 3, 5, 10, 20)  # how many presses per fit
    n_draws: int = 20                                # fits per K, different draws
    seed_base: int = 20260922
    knee_margin_f1: float = 0.05
    margin_over_anchor_f1: float = 0.05

    # device fit
    min_spread_w: float = 5.0             # a device spread never drops below this
    min_level_w: float = 5.0              # a device must rise this far above the floor
    dwell_clamp_s: tuple[float, float] = (30.0, 86400.0)  # allowed ON lengths
    off_gap_s: float = 7200.0            # typical OFF gap assumed for every device

    # decode
    warmup_s: float = 7200.0             # extra steps decoded on both sides of a chunk
    chunk_steps: int = 25600             # about 1.8 days at 6 s
    unexplained_c: float = 4.0           # steps off by more than c x noise are masked
    min_prob_on: float = 0.5             # posterior needed before a device may claim
    split_gap_s: float = 60.0            # masked stretch long enough to split an episode

    # scoring and calibration
    onset_tol_s: float = 12.0            # onset tolerance, twice the native step
    onset_tol_60s: float = 120.0
    duration_band: tuple[float, float] = (1.0 / 3.0, 3.0)
    overlap_cover: float = 0.20          # drop a training press overlapped beyond this
    residual_share_gate: float = 0.20
    anchor_off_factor: float = 0.9       # hysteresis: OFF below 0.9 x the ON threshold
    energy_hold_s: float = 60.0          # a reading holds for at most this long


DEFAULT_CONFIG = FHMMConfig()
