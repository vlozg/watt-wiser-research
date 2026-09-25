# NILM jargon, in plain language

Reference for the words the experiment docs and reports use. Companion to the ELI5
primers (`ELI5_NILM.md`, `ELI5_COMMON_NILM_FEATURES.md`). Keep it open while
reading `docs/hypotheses/`, the experiment plans, and the reports.

## The signals

- **aggregate (mains)** — the whole-home meter's power reading; the only signal
  models may learn from.
- **submeter** — a meter on one appliance. Used to check answers, never to make
  them: the models are blind to it.
- **GT (ground truth)** — the hand-annotated record of when each device really
  ran, stored in `data/gold_annot/`.
- **gold layer** — the cleaned per-channel data store the pipeline reads
  (`data/gold/`).

## Calibration

- **press / press pool** — one annotated device cycle, read as a simulated
  start/stop button press; the pool is all of a device's cycles.
- **session** — the aggregate over one press interval: one calibration example.
- **K, K-curve** — how many sessions the product gives the model; the K-curve
  plots accuracy against that number, to find where more calibration stops helping.
- **profile** — a device's calibrated rule: ON threshold, minimum run time,
  merge gap.
- **parity rule** — calibration and scoring build device spans with the same
  code, driven by the same GT marks; only the aggregate ever feeds a model.
  Submeters are evaluation-only.

## The FHMM model

- **FHMM** — factorial hidden Markov model: one ON/OFF switch per device, all
  running in parallel; the meter reads the sum of what is on, plus background.
- **emission** — the model's prediction of the meter reading for a combination
  of device states: a Gaussian with a level and a width.
- **Viterbi** — the decode step: pick the most likely combination of device
  states at each timestep.
- **dwell** — how long a device stays on once it turns on.
- **floor, sigma_off (floor_w, sigma_off_w)** — the always-on base load
  (10th-percentile watts) and the noise width around it (1.4826 x MAD). The
  model's "everything is off" line and how fuzzy it is. Called
  `background_estimates` in older code.
- **margin / sub-noise** — margin: how far a device's ON level sits above the
  floor, measured in sigmas of the noise. Sub-noise: within about 2 sigma —
  indistinguishable from background (the fridge, in every house here).
- **innovation gate (refusal rule)** — when the meter reads something no
  combination of device states can explain within a few sigma, the decoder
  refuses to attribute those watts instead of forcing a wrong claim.
- **unknown share** — the fraction of energy the decoder refused that way.

## Scoring and reports

- **episode** — one ON span of a device; the unit everything is scored on.
- **cadence, 60 s bucket** — the meter's sampling rate; bucket-meanning to
  60 s simulates slower storage meters ("rung" in older docs and code).
- **energy balance (books-close)** — measured energy minus what devices claim
  minus the floor; a large leftover means the claims under-cover the meter.
- **arm** — one experiment variant run through the same scoring: the anchor
  (plain rules), B1 (session-supervised FHMM), B0 (EM without calibration).
- **ablation** — an arm that removes one ingredient, to measure what it
  contributes.
- **split** — the train/test timestamp: all calibration strictly before it,
  all scoring at or after it.
