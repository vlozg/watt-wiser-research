# H03 — The 1-minute-class default cadence degrades detection

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-23 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §2 item 1 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

At the deployment logging cadence (60 s class [quarantined assumption; 1-minute onboard log is a reviewed hardware fact `research-brief.md` §4]), detection performance drops materially relative to native cadence, with the loss concentrated on low-power appliance classes; it degrades further toward unusable at 300 s. "Materially" = for at least one device class that clears the anchor at native cadence, the F1 drop at the degraded cadence exceeds a margin frozen in advance, or the class collapses to floor level.

## Why it matters

- It is the deployment risk, not a laboratory curiosity: the product's default logging interval is in this range, and the client can change it — but only if the cost is measured.
- Cadence is the first-order design constraint of this problem [reviewed `00_overview.md` §6 finding 1].

## How to verify

- Same detector and button-press calibration as H02; additionally bucket the aggregate to 60 s and 300 s (mean-bucket and max-bucket variants) and re-run.
- Per-appliance degradation table: native vs 60 s vs 300 s, real-mains substrates only for the deployment verdict (synthetic/slice aggregates flatter the result).
- Report which classes collapse toward the floor at which cadence — that table is the product-facing answer.
- **Ladder refinement (2026-09-23, AI drafted; protocol fixed same day after owner clarification):** the question is **full retrain at each cadence** c ∈ {6, 10, 15, 30, 60, 300, 900} s — the same frozen session windows S_k and seeded draws, but levels, sd, dwell priors, background and the EM ablation all re-estimated on the c-cadence bucket-mean aggregate (bucket once per cadence; a session window must contain at least 2 buckets, else the profile falls back to never-claims; matching tolerance tau(c) = c). Train-at-6-s plus transform is kept as the secondary comparison per cadence: the retrain-vs-transfer gap isolates how much the learning channel itself degrades, separate from the detection channel. The 60 s transfer point is already measured (AI-run v1 outputs, docs/reports/fhmm/, owner review pending): B1 pooled F1 0.098/0.057/0.020 vs anchor 0.165/0.205/0.000 on houses 1/2/5. Deliverable: the measured knee c* per arm and device class under full retrain — the coarsest cadence where calibration at c still yields a usable profile — not a pre-declared bar.

## Evidence so far

- [quarantined] `deprecated/baseline_runs/R2_rungs/`: on real mains, 60 s drops kettle 0.62→0.48, fridge 0.51→0.39, dishwasher→0.00. The calibration slice shows the *opposite* pattern (bucketing denoises it) — substrate choice flips the conclusion, which is exactly why the deployment verdict must come from real-mains substrates.
- [reviewed] AMPds2 is natively 60 s and its kettle/fridge episodes sit near the detection floor — a natural degraded-cadence proxy [`00_overview.md` §6].

## Open questions

- Mean-bucket vs max-bucket aggregation (does the runtime have access to within-minute maxima?) — matters for bursty loads.
- The exact achievable telemetry rate on the EM Gen3 must be measured on live hardware [reviewed `research-brief.md` §4].
- Claim-rule lever (2026-09-23): the house-2 kettle rung diagnosis (Viterbi-bit recall 0.0 vs forward-backward marginal 0.77) suggests testing a union claim rule before concluding the model itself fails at coarse cadences — it is cheaper than any model change.

## History

- 2026-09-20 — created from the conversation hypothesis list.
- 2026-09-23 — ladder refinement added (7-point cadence sweep replaces the two-rung design); protocol fixed same day after owner clarification: **full retrain per cadence** — levels, sd, dwell priors, background and EM re-estimated on the c-cadence aggregate from the same frozen session windows, with the transfer-only variant kept as the secondary comparison. First measured point (transfer variant): the 60 s rung from the AI-run FHMM v1 campaign, owner review pending.
