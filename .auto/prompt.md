# Autoresearch task: WattWiser NILM detection + regression model

## Goal
Build and iteratively improve a NILM model that fits the WattWiser problem
statement (docs/PROBLEM_STATEMENTS.md): aggregate-only input, low frequency,
calibration-supported, episode-level evaluation. Bar set by the user:
episode F1 > 0.7 for EVERY target device, with a tracked regression score
(per-device power MAE / nMAE) reported on every run.

## Primary metric (frozen)
METRIC min_device_f1 - the worst target device's episode-level F1 on the
frozen benchmark (higher is better; target > 0.7).

## Regression score (tracked on every run)
- METRIC mean_mae_w: macro mean of per-device MAE (W), lower is better
- METRIC worst_mae_w: the worst per-device MAE (W)
- METRIC mean_nmae: macro mean of per-device nMAE (MAE / mean aggregate W)
Per-device MAE/nMAE are printed in the benchmark table and saved to
.auto/last_bench.json.

## Frozen benchmark protocol (.auto/bench.py - do not tune)
- Data: UK-DALE gold layer (data/gold/ukdale), 6 s mean resample.
- Eval house: house_1; eval span: first 30 days after split_us
  1380585600000000 (house_1 splits.csv contract, 2013-10-01).
- Expanded eval (user request): the 30-day slice is the frozen loop metric;
  when an improvement looks big enough to keep, confirm it on a larger span
  before declaring it final: BENCH_EVAL=full bash .auto/measure.sh re-scores
  the SAME trained model over the full post-split house_1 span
  (2013-10-01 to end of data, ~3.5 y; 90d/365d also available). The run logs
  the 30-day min_device_f1 as its decision metric and carries the full_
  METRIC lines (full-span F1/MAE) in its metrics + description.
- Devices (5): kettle, microwave, fridge, washing_machine, dishwasher.
- GT episodes: gold submeter channel > per-device threshold
  (data/gold/thresholds.json, half_p50: kettle 1173 W, microwave 762 W,
  fridge 44.5 W, washing_machine 90 W, dishwasher 60.5 W); min episode
  2 samples (12 s). Same thresholds applied to predictions (deployment parity).
- Matching: wattwiser.experiments.evaluation.score_episodes with onset
  tolerance tau = 12 s (2x cadence, the fhmm FROZEN tau_native_s convention)
  and duration band (1/3, 3.0). Frozen; never tuned on test.
- Calibration: K = 5 ON-sessions per device drawn with seed 2026 from
  house_1 PRE-split span - the only target-house data a model may train on.
- Pretraining data (allowed): house_2 + house_5 labelled channels (last 20%
  of each house = validation). NOTHING from house_1 post-split span may
  influence training, model selection, or hyperparameters.
- Model input: aggregate mains only (gap-filled: ffill limit 10 samples). Cadence note: the client meter samples natively at 1 Hz; the 6 s benchmark cadence is the frozen UK-DALE gold contract and stays fixed.
- Model output: per-device watts on the eval grid (stride-32
  overlapping-window inference is the reference implementation).

## Rules (cheating = wasted run)
1. Only src/experiments/04_autoresearch/model.py may change between
   iterations. bench.py, measure.sh, checks.sh and the protocol constants
   are frozen; if a protocol constant must change, stop and say why instead
   of silently editing it.
2. Never train on house_1 channels beyond the provided calibration sessions
   (ctx['calib']); the eval span must not influence any model choice.
3. Do not tune thresholds, tau, duration band, eval span, or metric code.
4. Never use eval-house submeter channels as model input.
5. Every run gets logged: keep/discard/crash all carry evidence.

## Iteration mechanics
- Benchmark: bash .auto/measure.sh (METRIC lines; primary printed first and last).
- Checks: bash .auto/checks.sh (gate: all 5 devices scored, finite metrics).
- Backlog: .auto/ideas.md - work top-down unless evidence says otherwise;
  persist hypothesis / rollback_reason / next_action_hint in the asi field.

## Known prior baseline (EXP-02: pointwise F1 at 50 W, K-only training, house 1)
fridge 0.487, kettle 0.037, microwave 0.058, washing machine 0.100 - not
comparable to this benchmark's episode F1 (different metric), but it shows
K-only training underfits. First lever: multi-house pretraining.