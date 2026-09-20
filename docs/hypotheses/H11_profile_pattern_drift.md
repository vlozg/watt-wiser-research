# H11 — Profiles as patterns: cross-session template learning, and drift-to-anomaly

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §5, §10 · **Registry:** `docs/hypotheses/README.md`
Raised in owner review, 2026-09-20.

## Statement (falsifiable, two forms)

(a) **Template form:** a profile learned as a *common pattern* across the K valid calibration sessions — an aligned template of the episode shape (switch-on transient, steady plateau, switch-off; for multi-phase devices, a phase sequence) — detects unseen episodes better than simple aggregate statistics (level + dwell). Measurable as an ablation inside the H01/H02 instrument.

(b) **Drift form:** a device whose episodes **gradually** deviate from its calibrated pattern — sustained over weeks, not a one-off — can be flagged as anomalous ("device may be degrading") with a false-alarm rate low enough to be useful, using drift statistics computed from the same matching machinery as detection.

## Why it matters

- (a) is the client's own open question about the profile's mathematical representation [client §6, §10] — "find the common pattern" is a candidate answer with a well-defined test.
- (b) is a candidate **second product feature** from the same calibration investment: the profile that defines detection also defines "normal", and deviation-from-normal is the standard route to device-health insight (a fridge whose compressor cycles creep longer and more frequent as a seal leaks or coils clog). Not MVP scope — the MVP remains identification + energy.

## Why it might fail (honest confounders)

- **Cadence caps shape.** At ~1 Hz a kettle episode has structure; at the 60 s class it is 2-4 samples — no shape to learn, only level + dwell (H03). Any template gain is cadence-dependent.
- **K is thin.** With guidance at 3 valid sessions, template averaging is statistically fragile; session-specific noise can masquerade as pattern.
- **Natural drift ≠ failure.** Fridge draw and duty legitimately vary with season (harder in summer); kettle dwell varies with how much water the user boils — likely swamping any limescale signal; voltage wobble moves levels; a misattributed episode pollutes the drift series.
- **No failure labels exist.** No public dataset marks "this fridge broke in March". So (b) is verifiable only down to "sustained statistical drift detected at controlled false-alarm rate"; the interpretation "device broken" is a product claim, validated — if at all — through the confirmation loop or a spot rig (FAQ Q13).

## How to verify

- (a) **Template-vs-stats ablation** in the H01/H02 instrument: same sessions, same frozen scoring rules; profile = simple statistics vs aligned template (plus a phase-sequence variant for washer-class). Native cadence first (shape exists there), 60 s as the deployment check.
- (b) **Two stages**, on the long substrate:
  1. *Natural-drift envelope* (no failure labels needed): UK-DALE house 1 spans 4 years [reviewed framing §8]. Fit the profile from months 1-3; match episodes across the following years; measure how level, dwell, and (fridge) cycle frequency wander over time and season → the natural envelope per class.
  2. *Drift detector:* flag only sustained exceedance (CUSUM/EWMA-style sequential drift over weeks, never point outliers — a one-off oddity is probably contamination or misattribution). Report false-alarm rate against the natural envelope, plus the earliest detectable injected drift (slow ramp on level or dwell in simulation).

## Evidence so far

- [none] — both forms are new with this review pass.
- [quarantined] the old campaign ran an anomaly rung (`deprecated/baseline_runs/R6_anomaly/`) on the R1 residual (aggregate − always-on − attributed); unreviewed, recorded here as prior-art claim only [registry rule 1; recorded 2026-09-20 during the contradiction trace].
- Related reviewed facts: per-class level/dwell/duty priors exist to build the drift statistics on [`00_overview.md` §6]; the 4-year UK-DALE house makes the natural-drift pre-study feasible.

## Open questions

- Is device-health in scope for the client at all (product decision), or does this stay research?
- Which drift statistic per class: level residual (all), dwell residual (kettle/washer), cycle frequency (fridge)?
- Does the template survive the 60 s reality at all, or is it native-cadence-only?

## History

- 2026-09-20 — created from the owner review hypothesis: "from multiple calibration segments, find the common pattern; use it to flag anomaly — gradual deviation may mean the device is broken."
