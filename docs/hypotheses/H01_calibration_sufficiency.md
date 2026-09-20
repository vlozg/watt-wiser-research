# H01 — Calibration sufficiency: how many guided sessions make a profile

**Status:** AI drafted (no human review yet) · **Last updated:** 2026-09-20 · **Framing:** `docs/PROBLEM_STATEMENTS.md` §5 · **Registry:** `docs/hypotheses/README.md`

## Statement (falsifiable)

For each enrolled device there exists a session count K* such that detection performance (episode-level F1 on strictly held-out events) plateaus at K*. Product guidance says "calibrate at least 3 times" [owner]. The guidance is right **iff** the measured K* ≤ 3 for the device classes in scope; the learning curve — F1 vs K ∈ {1, 2, 3, 5, 10, 20} — is the measurement.

## Why it matters

- Calibration is user time; the product promise ("calibrate a few times, then it works") rests on this number.
- It is the client's own open question ("how many valid calibration sessions before the profile is reliable" [client §8C, §9 Q5]).

## How to verify

- Shared instrument — the button-press calibration simulation (spec in H02): ground-truth episode intervals stand in for user start/stop presses; profiles are derived **only** from the aggregate over those intervals.
- Draw K sessions per device, build the profile, score strictly-later held-out episodes; sweep K ∈ {1, 2, 3, 5, 10, 20}; report F1/recall vs K per appliance class (simple vs complex [client §3]) and per cadence (native, 60 s).
- Also measure **valid-session yield**: flagged (contaminated) sessions do not count toward K [client §5 "combine valid calibration sessions"]. Predicted consequence: "3 valid" costs more than 3 attempts for long-session devices — fridge cycles every 10-40 min [reviewed `00_overview.md` §6].
- Pass criterion: frozen before the run — e.g. "F1 within X of the K=all plateau at K=3", X fixed per class at freeze time.

## Evidence so far

- [quarantined] `baseline_runs/R3_learning_curve/` claims the curve is flat from N=1 for single-state loads (kettle 0.62 throughout; fridge 0.50→0.51) and non-monotonic for washing machine (stabilizes around N≥10). **Caveat:** those signatures came from clean submeter channels — cleaner calibration than the product will ever have. Upper bound, not evidence.
- [none] under the button-press protocol.

## Open questions

- Does K* differ between simple (kettle) and complex (washer) appliances? Expected yes [client §3 distinction].
- Does the curve change under contaminated calibration? Predicted: yes, for long-session devices.
- Does K* depend on **placement policy** (quiet-window guided vs whenever the user happens to run sessions)? Measure count × placement jointly (quiet-window indicator: `docs/PROBLEM_STATEMENTS.md` §5); expected: guided placement lowers both K* and retries.
- Profile representation: do cross-session **templates** beat simple statistics? H11 form (a) — same instrument, same sessions.

## History

- 2026-09-20 — created from the hypothesis list settled in conversation.
