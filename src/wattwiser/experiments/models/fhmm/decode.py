"""Finding the most likely ON/OFF combination at every reading.

With D devices there are 2^D possible combinations. For each combination and
each reading we score how well the aggregate watts match it, then follow the
best path through time (Viterbi) and, separately, compute how sure we are
that each device is ON (forward-backward). Long spans are cut into chunks
with a little overlap, so memory stays bounded and the answer is continuous.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from wattwiser.experiments.models.fhmm.config import DEFAULT_CONFIG, FHMMConfig
from wattwiser.experiments.models.fhmm.types import Decoded, FHMMParams, PowerSeries


def joint_states(n_dev: int) -> tuple[npt.NDArray[np.int8], npt.NDArray[np.float32]]:
    """The 2^D device combinations, as bit tables.

    Combination j (0..2^D-1) means device d is ON when bit d of j is set.
    Returns device_bits (D, 2^D) and on_of_state (2^D, D).
    """
    j = np.arange(1 << n_dev, dtype=np.int64)
    device_bits = ((j[None, :] >> np.arange(n_dev)[:, None]) & 1).astype(np.int8)
    return device_bits, device_bits.T.astype(np.float32)


def gaussian_loglik(obs: np.ndarray, mean: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """Log-likelihood of obs under a Gaussian with the given mean and sd."""
    return -0.5 * ((obs - mean) ** 2 / sd**2 + np.log(2.0 * np.pi * sd**2))


def decode(series: PowerSeries, params: FHMMParams, t0_us: int, t1_us: int,
           devices: tuple[str, ...], cadence_s: float,
           config: FHMMConfig = DEFAULT_CONFIG) -> Decoded:
    """Decode the readings in [t0_us, t1_us) for every row of params.

    The rows share one pass, so fitting a hundred parameter sets costs little
    more than fitting one.
    """
    # per reading: score every device combination, keep the best path and the
    # per-device ON probability; chunks are decoded with overlap and clipped
    ts, w = series.ts_us, series.w
    level = params.level_w.astype(np.float32)
    spread = params.spread_w.astype(np.float32)
    stay_on = params.stay_on_prob.astype(np.float32)
    noise = params.noise_w.astype(np.float32)
    n_rows, n_dev = level.shape
    if n_dev != len(devices):
        raise ValueError(f"params has {n_dev} device columns, got {len(devices)} device names")
    n_states = 1 << n_dev
    device_bits, on_of_state = joint_states(n_dev)

    # watts the aggregate should show in each combination
    state_level_w = level @ on_of_state.T                      # (rows, states)
    # how often a device flips, from its typical OFF gap and ON stay
    off_steps = max(config.off_gap_s / cadence_s, 1.0)
    p_off_stay = np.float32(1.0 - 1.0 / off_steps)
    log_trans = np.zeros((n_rows, n_states, n_states), np.float32)
    for d in range(n_dev):
        device_chain = np.log(np.stack([
            np.stack([np.full(n_rows, p_off_stay, np.float32),
                      np.full(n_rows, 1.0 - p_off_stay, np.float32)], axis=-1),
            np.stack([(1.0 - stay_on[:, d]).astype(np.float32), stay_on[:, d]], axis=-1),
        ], axis=1))                                           # (rows, 2, 2): rows = from
        log_trans += device_chain[:, device_bits[d], :][:, :, device_bits[d]]
        # devices switch independently, so their log-probabilities add up
    start = np.ones((n_rows, n_states), np.float32)
    for d in range(n_dev):
        share_on = (1.0 - p_off_stay) / ((1.0 - p_off_stay) + (1.0 - stay_on[:, d]))
        start *= np.where(device_bits[d][None, :] > 0, share_on[:, None], 1.0 - share_on[:, None])
    trans_prob = np.exp(log_trans)

    g0 = int(np.searchsorted(ts, t0_us, side="left"))
    g1 = int(np.searchsorted(ts, t1_us, side="right"))
    n_total = g1 - g0
    if n_total <= 0:
        raise ValueError("empty decode window")
    warmup = int(config.warmup_s / cadence_s)
    chunk = int(config.chunk_steps)
    on_out = np.zeros((n_total, n_rows, n_dev), np.int8)
    prob_out = np.zeros((n_total, n_rows, n_dev), np.float32)
    unexplained_out = np.zeros((n_total, n_rows), np.int8)
    loglik = np.zeros(n_rows, np.float64)
    pos = 0
    while pos < n_total:
        core0, core1 = pos, min(pos + chunk, n_total)
        w0 = max(0, core0 - warmup)
        w1 = min(n_total, core1 + warmup)
        obs = (w[g0 + w0 : g0 + w1] - params.floor_w).astype(np.float32)
        n_seg = w1 - w0
        # each combination has its own expected level and its own spread.
        # The floor is ONE noise source, so it is counted once, and every ON
        # device adds only the part of its spread above that floor.
        state_var = noise[:, None]**2 + \
            (np.maximum(spread**2 - noise[:, None]**2, 0.0) @ on_of_state.T)
        state_scale_w = np.sqrt(np.maximum(state_var, 1e-12))
        state_loglik = gaussian_loglik(obs[None, None, :], state_level_w[:, :, None],
                                       state_scale_w[:, :, None]).astype(np.float32)
        # (rows, states, n_seg)

        # Viterbi: best score per state so far, plus which state we came from
        back_pointer = np.zeros((n_seg, n_rows, n_states), np.int8)
        best = start + state_loglik[:, :, 0]
        best -= best.max(axis=1, keepdims=True)
        for t in range(1, n_seg):
            candidates = best[:, :, None] + log_trans
            back_pointer[t] = candidates.argmax(axis=1).astype(np.int8)
            best = candidates.max(axis=1) + state_loglik[:, :, t]
            best -= best.max(axis=1, keepdims=True)
        states = np.zeros((n_seg, n_rows), np.int8)
        states[n_seg - 1] = best.argmax(axis=1).astype(np.int8)
        rows = np.arange(n_rows)
        for t in range(n_seg - 1, 0, -1):
            states[t - 1] = back_pointer[t][rows, states[t]]

        # forward-backward: how likely each combination is at each reading
        seg_peak = state_loglik.max(axis=1)                       # (rows, n_seg)
        scaled = state_loglik - seg_peak[:, None, :]
        forward = np.zeros((n_seg, n_rows, n_states), np.float32)
        first = start * np.exp(scaled[:, :, 0])
        norm = np.maximum(first.sum(axis=1), 1e-38)
        forward[0] = first / norm[:, None]
        loglik += seg_peak[:, 0] + np.log(norm)
        for t in range(1, n_seg):
            step = np.einsum("bi,bij->bj", forward[t - 1], trans_prob) * np.exp(scaled[:, :, t])
            norm = np.maximum(step.sum(axis=1), 1e-38)
            forward[t] = step / norm[:, None]
            loglik += seg_peak[:, t] + np.log(norm)
        backward = np.ones((n_seg, n_rows, n_states), np.float32)
        for t in range(n_seg - 2, -1, -1):
            step = np.einsum("bij,bj->bi", trans_prob, backward[t + 1] * np.exp(scaled[:, :, t + 1]))
            backward[t] = step / np.maximum(step.sum(axis=1, keepdims=True), 1e-38)
        posterior = forward * backward
        posterior /= np.maximum(posterior.sum(axis=2, keepdims=True), 1e-38)
        prob_on = posterior @ on_of_state                          # (n_seg, rows, D)

        # a reading that is off by more than c x the expected noise marks the
        # step as unexplained: the decoder is not claiming anything there
        level_here = state_level_w[rows[None, :], states]          # (n_seg, rows)
        scale_here = state_scale_w[rows[None, :], states]
        residual_w = obs[:, None] - level_here
        gate_w = np.maximum(scale_here, noise[None, :])
        unexplained = (np.abs(residual_w) > config.unexplained_c * gate_w).astype(np.int8)

        keep0, keep1 = core0 - w0, core1 - w0
        on_out[core0:core1] = (states[keep0:keep1][:, :, None] >> np.arange(n_dev)[None, None, :]) & 1
        prob_out[core0:core1] = prob_on[keep0:keep1]
        unexplained_out[core0:core1] = unexplained[keep0:keep1]
        pos = core1
    return Decoded(ts_us=ts[g0:g1], devices=devices, on=on_out, prob_on=prob_out,
                   unexplained=unexplained_out, loglik=loglik)
