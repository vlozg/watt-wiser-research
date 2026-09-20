# H04 — Dishwasher / washing-machine class is unreachable by threshold+duration rules

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §2, §6 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

Within the frozen rules family (ON-threshold + hysteresis + dwell matching, including the dwell-prior variant) on the W-only aggregate at deployment cadence, dishwasher/washing-machine-class enrolled devices cannot reach useful episode attribution on real-mains substrates. The binding failure is **noise-masking** — the signature's step sits at or below the household's always-on noise floor — not threshold placement.

Scope discipline: "unreachable" is claimed **only** for this frozen variant family on the W channel. Any detector outside the family (state machines, ML) resets the question.

## Why it matters

- This is the negative result that defines the product boundary: which device classes the MVP can honestly serve, and which need a different data path (higher-rate sampling or per-circuit sensing) — a hardware decision, not a tuning one.
- The client's simple-vs-complex distinction [client §3] makes washer/dishwasher the declared hard case.

## How to verify

- Re-run the quarantined variant sweep under button-press calibration (does *worse* calibration change the verdict? predicted: it gets worse, since long calibration sessions are near-certainly contaminated [reviewed fridge-cycle priors]).
- Report per-variant deltas on real-mains substrates; accept the negative result only when the documented family is exhausted and the failure mode matches the noise-masking prediction (signatures at/below the always-on floor, over-fire on noise, ground-truth fragmentation).
- The mechanism check that makes the claim mechanistic, not just empirical: compare each device's p50-ON level against the house's measured always-on floor and noise band.

## Evidence so far

- [quarantined] `baseline_runs/experiments/` E00-E19: 14 detector variants; best weak-class gain +0.006-0.012 F1 — negligible; documented failure modes are noise-floor over-fire (5-17x) and fragmented ground truth.
- [reviewed] The separation problem is real in the data: washer/dishwasher p50-ON 120-380 W vs fridge base 30-130 W and per-house always-on floors — the classes overlap in the priors table [`00_overview.md` §6].

## Open questions

- Does the frozen family include a minimal state machine (multi-phase washer cycles)? Decide at freeze time; it bounds the claim's scope.
- Interaction with H03: at 60 s the weak class may be *doubly* unreachable (smaller steps after bucketing).

## History

- 2026-09-20 — created from the conversation hypothesis list.
