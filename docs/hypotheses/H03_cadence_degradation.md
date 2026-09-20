# H03 — The 1-minute-class default cadence degrades detection

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §2 item 1 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

At the deployment logging cadence (60 s class [quarantined assumption; 1-minute onboard log is a reviewed hardware fact `research-brief.md` §4]), detection performance drops materially relative to native cadence, with the loss concentrated on low-power appliance classes; it degrades further toward unusable at 300 s. "Materially" = for at least one device class that clears the anchor at native cadence, the F1 drop at the degraded cadence exceeds a margin frozen in advance, or the class collapses to floor level.

## Why it matters

- It is the deployment risk, not a laboratory curiosity: the product's default logging interval is in this range, and the client can change it — but only if the cost is measured.
- Cadence is the first-order design constraint of this problem [reviewed `00_overview.md` §6 finding 1].

## How to verify

- Same detector and button-press calibration as H02; additionally bucket the aggregate to 60 s and 300 s (mean-bucket and max-bucket variants) and re-run.
- Per-appliance degradation table: native vs 60 s vs 300 s, real-mains substrates only for the deployment verdict (synthetic/slice aggregates flatter the result).
- Report which classes collapse toward the floor at which cadence — that table is the product-facing answer.

## Evidence so far

- [quarantined] `deprecated/baseline_runs/R2_rungs/`: on real mains, 60 s drops kettle 0.62→0.48, fridge 0.51→0.39, dishwasher→0.00. The calibration slice shows the *opposite* pattern (bucketing denoises it) — substrate choice flips the conclusion, which is exactly why the deployment verdict must come from real-mains substrates.
- [reviewed] AMPds2 is natively 60 s and its kettle/fridge episodes sit near the detection floor — a natural degraded-cadence proxy [`00_overview.md` §6].

## Open questions

- Mean-bucket vs max-bucket aggregation (does the runtime have access to within-minute maxima?) — matters for bursty loads.
- The exact achievable telemetry rate on the EM Gen3 must be measured on live hardware [reviewed `research-brief.md` §4].

## History

- 2026-09-20 — created from the conversation hypothesis list.
