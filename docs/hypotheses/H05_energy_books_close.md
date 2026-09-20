# H05 — Attribution + explicit UNKNOWN closes the energy books

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §2, §7 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

For every substrate and house, the accounting identity holds and is reported:

> mains energy ≈ Σ_d attributed(d) + always-on + UNKNOWN

with the residual (UNKNOWN) size printed **per house before any accuracy number**, and no attribution reported for a house whose coverage is not shown beside it. "Closes the books" = the identity is explicit and the residual is quantified — not that the residual is small.

## Why it matters

- The residual is a *product feature* (an honest UNKNOWN), not an error term [reviewed `00_overview.md` §5 item 4].
- Residual composition is a **per-house finding**: UK-DALE houses leave 3-14% of mains unexplained by the 5 canonical targets, while REFIT's 20-home median leaves roughly 64% — in many real homes, UNKNOWN dominates everything else [reviewed `00_overview.md` §6 finding 4].

## How to verify

- Harness computes, per substrate/house/window: mains energy, per-device attribution, always-on estimate, UNKNOWN = remainder; printed as a table before scores.
- Sensitivity: how the always-on estimate is derived must be frozen (its definition changes the residual).
- Deployment-parity check: at runtime only the aggregate is available, so always-on/UNKNOWN must be estimable from the aggregate alone (e.g. occupancy-free floor estimation) — verify the identity does not silently lean on submeter information.

## Evidence so far

- [reviewed] Dataset-side coverage: UK-DALE 86-97% of custom-aggregate energy covered by labeled channels; REFIT median ≈36% (range up to ~53%); GREEND has no site meter at all [`00_overview.md` §6].
- [quarantined] Campaign claims 96.8-100% of above-always-on residual "covered" by detections on its substrates — treat as unverified; note the metric ("above always-on") differs from the reviewed dataset-side coverage definitions.

## Open questions

- How to present REFIT-class homes (UNKNOWN-dominated) without letting attribution scores hide the emptiness of the picture.
- Whether "energy books" should close at event level, window level, or both.

## History

- 2026-09-20 — created from the conversation hypothesis list.
