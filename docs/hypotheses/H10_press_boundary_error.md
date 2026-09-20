# H10 — Press-boundary error: cost curve and step-snapping

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §5, §9 Q11 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable, two parts)

(a) **Unmitigated**, detection performance degrades with press-boundary error ε roughly like ε/dwell, per device class: graceful for long-dwell devices, steep for short-dwell ones. The worst direction is a **late start press** — the device is already running when the local baseline is taken, so ΔPower collapses toward zero (a kettle press 1 minute late can lose the entire signal).

(b) **With step-snapping** (search ±W around each press for the largest coherent step in the aggregate; snap the boundary to it), errors ε < W cost near-nothing; only errors beyond W, or steps hidden by coincident other-device activity, remain costly.

## Why it matters

- The calibration window is the method's only supervision, and its boundary is produced by a human thumb. If press error were fatal, the whole calibration design would need rethinking; if it is nearly free (via snapping), the product can trust casual users.
- The client doc's baseline rule — "estimate the normal household power immediately before switch-on" [client §5] — is exactly what a late press corrupts.

## How to verify

- In the shared button-press instrument (H02): jitter ground-truth boundaries by ε ∈ {10 s, 30 s, 1, 2, 5, 15} min, both directions and mixed; rebuild profiles from the jittered intervals only.
- Score F1/recall vs ε, per appliance class and cadence, with snapping OFF and ON (search window W frozen before the run). Report the ε at which each class first falls to within the anchor's noise band — or below a frozen margin of the anchor.
- Predicted shape: kettle degrades steeply beyond ε ≈ 30-60 s unmitigated; washer tolerates 15 min; snapping flattens the curves up to W.

## Evidence so far

- [none] — raised in owner review of `docs/PROBLEM_STATEMENTS.md`, 2026-09-20.
- Related reviewed fact: dwell priors span two orders of magnitude across canonicals (kettle 100-200 s vs washer 1-2 h) [`00_overview.md` §6], which is what makes the cost curve class-dependent.

## Open questions

- Should the UI confirm the snapped step with the user ("we saw the kettle switch on at 14:02 — right?")? That turns a noisy human input into a verified label at near-zero cost.
- Interaction with the interference flag: a coincident other-device step inside the search window is ambiguous — the same ambiguity H06 must resolve.

## History

- 2026-09-20 — created from owner review notes on the problem statement.
