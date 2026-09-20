# H07 — How much do power-label values contribute to prediction?

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §3, §9 Q3 · **Registry:** `docs/hypotheses/README.md`
Reframed in owner review, 2026-09-20: the original framing ("labels lie, never depend on them") pre-judged the answer. The hypothesis is now the measurable question — what does each use of the label value actually buy?

## Statement (falsifiable)

The power-label value collected at enrollment has a measurable marginal contribution to detection. The ablation ladder below quantifies it per use-site; where label inputs earn their place, they are used; where they do not, they are dropped. The one requirement that holds regardless of the numbers: **graceful degradation** — no rung may silently break when the field is empty (unreadable label, user skips) or wrong. That is a robustness requirement from product reality, not a trust judgment.

## The ablation ladder (each rung vs the one below)

- **L0 — measured-only.** Profiles built from calibration sessions alone (level, step, dwell). Baseline; no label input anywhere in the method.
- **L1 — sanity check only.** Label vs measured profile compared at enrollment; wild mismatch → warn ("a 'kettle' whose sessions show 30 W is probably a wrong selection"). No effect on detection. Measured: false-warning rate and caught-mistake rate (simulated enrollment mistakes).
- **L2 — detection-time tie-break.** When two enrolled devices have overlapping measured signatures — the client's own kettle-vs-heater case, both at ≈2,100 W [client §7] — label values vote as a prior. Measured: ΔF1 in confusable households vs L0.
- **L3 — low-K stabilizer.** With K ∈ {1, 2} sessions the measured level estimate is noisy; the label value acts as a prior/seed for the expected step. Measured: does the learning curve (H01) shift left (smaller K*), and at what cost when the label is wrong?
- **L4 — hard constraint.** Detection thresholds anchored to the nameplate. Included as the cautionary endpoint: expected to degrade when labels are absent or wrong. If L4 robustly beats L0-L3, the caution was wrong — the interesting result.

Report per class × cadence × K; margins frozen before the run.

## Background risks (motivation, not evidence — tags explicit)

- [reviewed] Device *annotations* in the wild have been caught lying: REFIT's channel tagged "kettle" idles at 113 W and never boils (fleet p50-ON 2,614 W); GREEND's four "kettle" channels match no kettle physics and its "microwave" is a noise storm [`00_overview.md` §6 finding 2]. These are dataset channel labels — motivation for starting unverified device information at zero trust, **not** direct evidence about the product's nameplate field.
- [owner inference, untested] A nameplate states a rated maximum, not expected draw (draw sits at or below it); human entry adds wrong-model/typo errors. Whether nameplates "frequently" disagree with draw is unknown — the ladder measures the consequence either way.

## How to verify

Run the ladder inside the H01/H02 instrument (same sessions, same frozen scoring rules; nothing else varies). Additional measures: L1 warning quality across the fleet priors; L2 gains expected to concentrate in same-wattage confusable pairs; L3 × K interaction with H01; L4 degradation under injected wrong labels (empty, ±20%, wrong-device).

## Evidence so far

- [reviewed] background only: the dataset-label lies listed above.
- [none] for every rung of the ladder.

## Open questions

- What exactly the UI collects (watts only? rated current? annual kWh?) — product decision that shapes L2/L3.
- Does a violated L1 sanity band block enrollment, warn, or just log?
- If L3 helps only at K ∈ {1, 2}, the label's role is *bootstrap-only* — a different product answer than "always useful".

## History

- 2026-09-20 — created from conversation (original framing: "usable, never ground truth").
- 2026-09-20 — reframed in owner review: the stance pre-judged the answer and conflated dataset channel labels with the product's nameplate field; rewritten as the L0-L4 ladder. Dataset-label evidence moved to background with explicit tags; graceful degradation kept as the standing product requirement.
