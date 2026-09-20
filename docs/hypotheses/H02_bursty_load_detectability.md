# H02 — Large bursty appliances are detectable from the aggregate alone

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §2, §7 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

An enrolled, single-state, high-power, bursty device (kettle-class; candidate set per the canonical decision) is detected from the runtime aggregate at native public-dataset cadence at episode-level precision/recall clearly above the anchor baseline — and above the floor — by a margin frozen below, with honest energy attribution on matched events (estimated/ground-truth within a fixed band).

## Why it matters

- This is the product's reliable core and the client's MVP premise ("identify a small number of appliances from whole-house readings" [client §1]).
- It is the claim the hardware critique turns into a *research question* [reviewed `research-brief.md` §4: "prove that ~1 Hz aggregate power is sufficient at all"].

## How to verify — the shared button-press calibration simulation

1. **Substrate:** UK-DALE full (primary) + other datasets with site meters (§8 of the framing doc); aggregate series at native cadence.
2. **Simulated sessions:** for device d, sample K ground-truth episode intervals of d as the user's start/stop presses. From the **aggregate over those intervals only**: local baseline (level just before the start press), ΔPower at both presses, dwell = interval length; apply the interference flag (H06 rule, frozen); valid sessions only go into the profile.
3. **Detection:** rules-based anchor (threshold + hysteresis + dwell matching, plus a dwell-prior variant) watching the aggregate, never the submeters.
4. **Scoring:** strictly-later held-out episodes; greedy one-to-one matching; onset tolerance scaled to cadence; episode P/R/F1 + energy attribution; UNKNOWN always reported [reviewed `00_overview.md` §5].
5. **Pass criterion:** a margin over the anchor and floor (§6), frozen before the run — no pre-declared per-class bars [owner decision 2026-09-20]. For comparison only: the [quarantined] plan claimed kettle P ≥ 0.95, R ≥ 0.90 at ~6 s and P ≥ 0.90, R ≥ 0.80 at 60 s (`docs/experiments/baseline-ukdale-plan.md` §5.6) — reference points from unreviewed work, never pass marks.
6. **Ablation knobs (same instrument):** boundary-jitter sweep (H10); placement policy / quiet windows (H06).

## Evidence so far

- [quarantined] `baseline_runs/` R1: kettle episode F1 0.62 at 6 s (P 0.45 / R 0.98) on the calibration slice; recall 0.46-0.98 across all 5 houses; energy est/GT 0.94-0.99 on matched events. **Caveat:** signatures derived from clean submeter channels; upper bound.
- [reviewed] The separability is real in the data: kettle p50-ON 1,760-2,946 W, dwell p50 100-200 s across datasets — magnitude + duration separate it from everything else in the priors table (`00_overview.md` §6).

## Open questions

- Canonical target set: does microwave join kettle/fridge/washer/dishwasher as a full target (5 canonicals, per reviewed EDA) or stay 4 (per the quarantined campaign)?
- ~~Gate numbers themselves~~ — resolved [owner decision 2026-09-20]: absolute per-class bars are out; margins over anchor/floor are the criterion.

## History

- 2026-09-20 — created from the conversation hypothesis list.
- 2026-09-20 — owner decision during evaluation-contract review: no pre-declared per-class pass gates; the baseline ladder (§6) is the reference, and quarantined numbers are comparison points, not pass marks.
