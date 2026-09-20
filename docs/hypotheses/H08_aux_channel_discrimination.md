# H08 — Auxiliary channels separate same-wattage devices

**Status:** AI drafted (no human review yet) — **parked until live Shelly data** · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §3 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

Adding auxiliary aggregate channels — ΔCurrent and power factor, which the Shelly exposes [client §3 signal table; reviewed `research-brief.md` §4] — separates same-wattage devices (the client's kettle-vs-heater case: both ≈2,100 W) better than active power alone, measured as improved episode discrimination on an identical event set.

## Why it matters

- The client's own worked example leans on it: kettle vs heater differ by ΔCurrent 9.1 vs 8.8 A and PF 0.99 vs 1.00 at identical ΔPower [client §7].
- It is the "collect more / use everything" principle applied to the hardware's full signal table — the cheapest possible feature upgrade if it works.

## How to verify — parked, tier 3

- **Blocked on data, not on ideas:** the six public datasets are nearly W-only; REDD records apparent power *instead of* real power [reviewed `00_overview.md` §6]. No local substrate can test current/PF discrimination.
- Design now, run when a real Shelly export exists (tier 3): extend the H02 event features with ΔI and PF; ablation W-only vs W+aux on the same events; report per-class discrimination gains.
- Expectation management up front: the client's own example gap is tiny (PF 0.99 vs 1.00) against a ±5% metering band below ~230 W [reviewed `research-brief.md` §4] — plausibly unusable for small loads even if real for large ones. Measure, do not assume.

## Evidence so far

- [none]. Motivation is [client §7] plus the hardware's documented channel list [client §3; reviewed `research-brief.md` §4].

## Open questions

- Which aux fields the actual deployment export carries, and at what cadence (aux channels may arrive at a different rate than W).
- Whether aux features enter the anchor rules (thresholds on ΔI) or stay a scoring-time tiebreaker.

## History

- 2026-09-20 — created from the conversation hypothesis list; parked by data availability, not by decision.
