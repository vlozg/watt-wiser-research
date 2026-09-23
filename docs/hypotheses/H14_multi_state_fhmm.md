# H14 — Per-device multi-state emissions from the same calibration windows

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-23 · **Framing:** `docs/experiments/fhmm-session-supervised-plan.md` §6 (v1 froze 2 states per device), §12 (deferral) · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

The FHMM v1 froze every device at 2 hidden states (OFF / one ON level), because its levels come from the window mean of the aggregate inside calibration sessions and the §7 contract scores episodes. The claim: adding per-device states (S ∈ {2, 3}) whose extra levels are discovered by **unsupervised clustering of the aggregate P inside the same session windows S_k** — no new supervision, the user still presses start/stop only — improves program-device detection (washing machine, dishwasher) at native cadence, without degrading bursty devices (kettle) or the fridge profile. Expected: no improvement at the 60 s rung — the collapse mechanism (forward-backward mass spreading across composite states below the claim threshold) multiplies with the state count.

Two-sided: if within-session clustering does not separate stable levels, or program-device F1 does not clear the margin over the anchor baseline (registry rule 2), the hypothesis fails.

## Why it matters

- The v1 read-out (2026-09-23) localizes the remaining error to level mis-specification, not detectability: the washing machine is the worst device for every arm (house 2: anchor 0.034, FHMM 0.071, EM 0.061 pooled F1), yet the same device *improves* at the 60 s rung (0.067 → 0.21) — bucket-means accidentally phase-average the program profile, which is the signature of a single ON level failing to represent the phase sequence (fill, wash, heat, spin).
- Mode competition on house 5: the dishwasher's low mid-cycle phase sits between its OFF and ON levels and is absorbed by the washing machine's wide-sd state; a dishwasher eco/main state pair would absorb its own phase.
- The supervision contract is unchanged, so this is a model-structure question inside the same calibration protocol — a measurement, not a new data-collection ask.

## How to verify

- **B2 arm** on the frozen runner (`src/experiments/01_fhmm/02_run_kcurve.py`): S ∈ {2, 3} per device; within-session 1D clustering (GMM) on the aggregate w inside each S_k window; state level = cluster mean minus floor; per-state dwell from within-window run lengths; sd per state from cluster spread.
- **Guard:** keep an extra state only when the between-cluster margin clears `max(sigma_off, sd_state)` (same functional form as the state-aware gate); otherwise stay binary. Protects short single-phase sessions (kettle) from noise splits.
- Same frozen protocol: pre-split press pools, K grid, 20 draws, native + 60 s, frozen tau, scored against the same post-split eval GT on the three axes (episode F1 + strata, span, books-close).
- **Prediction table, stated before running** (from the 2026-09-23 v1 evidence): washer/dishwasher native F1 rises above the anchor margin; kettle unchanged (already 0.77-0.85 pooled F1 from K = 1, single level is the right model); 60 s rung unchanged or worse (composite-state spread grows with state count); house 5 unchanged (levels inside the ambient band are H04's domain).

## Evidence so far

- [none] — verification not yet run. The diagnosis rests on AI-run FHMM v1 outputs (`docs/reports/fhmm/`, 2026-09-23, owner review pending); the v1 deferral itself is pre-declared in the frozen plan §12.

## Open questions

- Identifiability: sessions must be long enough to contain >= 2 phases; kettle bursts will not cluster — the guard keeps them binary, which is correct.
- Does multi-state shift the cadence knee (H03 ladder)? More states should spread posterior mass faster at coarse cadences — run the ladder after or jointly, not independently.
- The claim-rule lever first (see H03 open questions): a union claim rule (Viterbi bit OR forward-backward marginal) may recover rung kettle F1 without touching the model — if it does, the multi-state arm should be evaluated on the corrected rule.

## History

- 2026-09-23 — created from the FHMM v1 read-out: the pre-declared §12 deferral plus measured washer/dishwasher level mis-specification (rung inversion, house-5 mode competition, worst-device F1 for every arm).
