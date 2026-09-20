# H12 — Calibration contamination reality check (FAQ Q2, made measurable)

**Status:** AI drafted (no human review yet) — **the cheapest hypothesis to settle: pure descriptive analysis on the six datasets, no new hardware, no simulation** · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §5, §9 Q2 · **Registry:** `docs/hypotheses/README.md`
Raised in owner review, 2026-09-20.

## The assumption under test

The working assumption so far (§5, FAQ Q2, H06's motivation): other devices contaminate calibration sessions, and long sessions (washer/dishwasher, 1-2 h) are "near-certainly contaminated" because fridges cycle every 10-40 min [reviewed priors]. Owner challenge: this is *measurable* — the datasets contain both each target's true episodes and every other device's activity, so we can count what real calibration windows would have looked like, on all six datasets. The assumption is then confirmed, weakened, or rejected by measurement instead of fridge arithmetic.

## Statement (falsifiable)

For press-bounded calibration windows placed on real target-device episodes:

- **(a) Two distinct rates**, per canonical class × window length × dataset:
  - *raw contamination* — ≥1 other-device event anywhere inside the window. Predicted mostly harmless for level+dwell profiles: a fridge cycling mid-washer-session does not move the washer's step or dwell.
  - *harmful (boundary) contamination* — ≥1 other-device event within ±B of the target's switch-on/switch-off transitions (B frozen, e.g. 5 min — the baseline + snap region). This is the kind that corrupts the baseline, shrinks ΔPower, or hijacks the step search.
- **(b) The "near-certainly contaminated" claim** survives only if P(boundary-harmful) for 1-2 h windows is at or above a frozen threshold (e.g. 0.9); materially below → the claim is **rejected** in its harmful form, and clean long sessions are plentiful.
- **(c) Quiet-window availability:** the fraction of clock time where a clean window of length L exists, by hour of day — the measured basis for the app's quiet-window guidance (§5), per dataset.

## Why it matters

- Upstream of the whole calibration chain: H01 (session count), H06 (flagging yield), H11 (drift statistics need clean episodes). If boundary contamination is rare, the calibration story simplifies; if common, H06 is the hardest UX problem in the product.
- First hypothesis that can leave *drafted* on evidence reviewable in one sitting: one EDA pass, owner reviews, status moves.

## How to verify (pure EDA on existing data)

1. For every ground-truth episode of each canonical device (plus small press-slop padding), define the candidate calibration window.
2. From the *other* devices' channels, mark every ON/step event inside; classify raw-only vs boundary-harmful (±B).
3. Report per dataset × class × window length: raw rate, harmful rate, clean-window availability by hour of day.

Caveats to print with the results: plug-only datasets (GREEND; ECO's plugs) see only instrumented devices → their measured contamination is a **lower bound**; REDD's mains is apparent power (event *timing* remains valid); AMPds2 at 60 s blurs brief contaminator events (undercounts kettle-length interference).

## Evidence so far

- [none] — analysis not yet run.
- [reviewed] The one number that hints the *harmful* rate is not small: about half of kettle/washer/dishwasher onsets begin while another canonical target is already running [`00_overview.md` §6]. Owner's opposing intuition: mid-session contamination (the raw rate) is largely harmless, so the scary-sounding claim may collapse once raw and harmful are separated. The measurement decides.

## Open questions

- The boundary half-width B (frozen before the run) and whether the press-slop margin (H10) widens it.
- Do contaminator *levels* matter (a 20 W base load vs a 2 kW kettle), or only event counts? Suggest recording both.

## History

- 2026-09-20 — created from owner review: "FAQ 2 is worth a hypothesis; we can already answer and reject that assumption with analysis on all 6 datasets."
