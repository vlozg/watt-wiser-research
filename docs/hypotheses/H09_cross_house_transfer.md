# H09 — Signatures transfer poorly across homes; per-home calibration is necessary

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §1, §7 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable — and deliberately two-sided)

The product's framing is **household-specific** guided calibration [client §1]. The testable claim behind it: signatures built in one home detect the same device class in another home **below the level that would justify skipping per-home calibration**. If the transfer matrix turns out strong, per-home calibration becomes optional (a major product simplification); if weak, the premise is confirmed and quantified. Either outcome is a result.

## Why it matters

- Per-home calibration is the strategic bet of the whole approach — it deserves a measurement, not an assumption.
- The client's evaluation plan already asks not to overfit "to one session or household" [client §8C], so this is inside their stated scope.

## How to verify

- **Transfer matrix:** build each signature from house A's calibration (button-press protocol, H02 instrument), score on house B's aggregate: within-dataset (UK-DALE h1 ↔ h2-h5) and cross-dataset wherever canonical types align (UK ↔ US ↔ Canada).
- Compare each off-diagonal cell against the diagonal (per-home calibration at the same K). The gap diagonal-vs-off-diagonal is the measured value of calibration.
- Report per appliance class: transfer may be class-dependent (a kettle's physics is more universal than a dishwasher's cycle).

## Evidence so far

- [quarantined] Mixed signals, both directions: kettle recall reportedly holds across all 5 UK-DALE houses (0.46-0.98) — partial transfer for one class; the weak class fails even *within* house, so it cannot transfer. Nothing verified.
- [reviewed] Cross-house variability is visible in the fleet priors: same canonical type spans wide ranges across datasets (kettle p50-ON 1,760-2,946 W) [`00_overview.md` §6] — consistent with either outcome.

## Open questions

- Which appliance classes have enough cross-house examples to make the matrix meaningful.
- Does transfer interact with H01 (fewer sessions per home might be acceptable if transfer fills gaps — or the reverse).

## History

- 2026-09-20 — created from the conversation hypothesis list.
