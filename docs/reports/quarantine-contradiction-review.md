# Quarantined docs vs the problem statement — contradiction trace

**Date:** 2026-09-20 · **Trigger:** owner finished reviewing `docs/PROBLEM_STATEMENTS.md`; every owner decision taken during that review is now traced back against §0's quarantined set.
**Scope (prose artifacts only, per §0):** `docs/experiments/baseline-ukdale-plan.md`, `docs/datasets/` (5 files), `docs/product/` (3 files), `deprecated/baseline_runs/` top-level summaries (3), `docs/reports/phase1-report-draft.md`. `deprecated/analysis/` code and `data/gold/` are covered indirectly via the docs that specify them.
**Verdicts:** **contradicts** (asserts what the statement now forbids or has decided otherwise) · **superseded** (a decision under the old framing, voided by the 2026-09-20 owner decisions) · **tension** (challenges a framing choice; unresolved) · **gap** (quarantined claim not yet recorded where it belongs) · **consistent** (audited, no conflict).

---

## 1. Direct contradictions

### 1.1 The second CT channel as product input — `docs/product/feasibility-verdicts.md`
- §2.9 ("Nobody is using the second CT channel", L84-91): *"Clamp CT2 on the circuit you care about... a permanently labelled reference channel... no button-pressing, no user compliance"*; *"During calibration, put CT2 on the appliance's own circuit... a far stronger training signal than a user-declared window"*; *"exactly what the practitioner community recommends instead of disaggregation"*.
- Recommendation 5 (L176): *"Use the second CT channel — continuous ground truth is available and unused."* Part B (L166) goes further: it is *"the experiment that would tell them whether the second channel is their real product."*

**Contradicts:** §2 (*"The product does not install meters on appliances"*, aggregate-side signals only per [client §3]); §5 (calibration = guided button-press sessions on the single aggregate, end to end [owner]); the entire calibration-protocol hypothesis set (H01/H02/H06/H10/H12) is built on the single-signal decision.
**Nuance:** as a one-off *evaluation experiment* — clamping CT2 on an appliance circuit to measure how much the aggregate smears a known signal — this is the same species as FAQ Q13's smart-plug spot rig and is not forbidden. The contradiction is its use as **product input / calibration substitute**, which is exactly what Recommendation 5 proposes.

### 1.2 PASS/FAIL verdicts against pre-declared per-class gates — `deprecated/baseline_runs/summary.md` + `docs/experiments/baseline-ukdale-plan.md` §5.6
- Plan §5.6 (L253-263) declares per-class pass gates (kettle P≥0.95/R≥0.90 at 6 s; fridge P,R≥0.85; washer R≥0.70; dishwasher R≥0.60; monitor ≈0 detections as negative control).
- `deprecated/baseline_runs/summary.md` L47-49 then reads results as verdicts: *"60 s gates (plan 5.6): fridge PASS (P .82/R .71), kettle R PASS / P FAIL (.64 vs .90), washing_machine R FAIL (.45 vs .60)"*.

**Superseded:** owner decision 2026-09-20 (§7 principle 5) — no pre-declared per-class bars; pass = margin over the anchor/floor frozen in advance. The PASS/FAIL language is void; the numbers demote to quarantined comparison points (H02 now says exactly this).

---

## 2. Tensions (challenge framing choices; unresolved)

### 2.1 Per-appliance acceptance rule anchored to *expected* energy — feasibility §2.7 (L72-73)
Demands a *"concrete, per-appliance numeric acceptance rule"*: N valid sessions, CV of ΔP, and *"the session's measured energy within some tolerance of the appliance's expected energy."*
**Tension:** the flag rule is exactly what H06 must *measure* before freezing, and nameplate-anchored "expected energy" as an enrollment gate is H07's territory — L1 (warn-only) in the ladder; hard constraint only as the L4 cautionary endpoint. The "N valid sessions" and CV-of-ΔP parts are compatible candidates for H06's flag design; the nameplate-gate part contradicts the ladder framing.

### 2.2 Strategic reframe: "disaggregation is a component, not the product" — `docs/product/product-core-reframe.md` (L12)
*"The value is not in the naming... Disaggregation becomes a component of that loop, not the product itself."*
**Tension:** the statement's §1 core *is* the naming ("which device consumed which"). The reframe's concrete proposals — a declared 10-minute inventory survey, behavioral/schedule priors, ask-on-anomaly — are **extensions** the owner principle permits ("anything we collect, we may use") but they are absent from §3's input universe. Note: the inventory proposal would resolve kettle-vs-heater (H07 ladder L2 / H08) without any sensor.

### 2.3 Baseline estimator: local 30-60 s pre-press window vs robust rolling baseline — feasibility §2.5 (L57-62)
§5's protocol step takes a local baseline just before switch-on [client §5]; feasibility §2.5 argues a 30-60 s window lands inside fridge compressor runs and biases the baseline, recommending a low-percentile rolling baseline over hours.
**Tension:** a method critique, not a trust conflict — but the statement adopts the client's mechanism without marking the robustness question open. The H02 instrument's freeze should carry the rolling-baseline variant as an ablation.

### 2.4 No provisional/deferred verdict mode in the output contract — feasibility §2.10 (L93-97)
Kettle-vs-heater (same watts, dwell 240 s vs 1,800 s) cannot be resolved at onset; honesty demands *"50% kettle / 50% heater; will resolve in ~10 minutes"* — a provisional prediction revised as the event continues. §4's output contract has per-event answers and UNKNOWN, but **no provisional mode**.
**Tension:** a real design gap surfaced by quarantined analysis; interacts with H07's L2 tie-break and H08 (aux channels). Needs a §4 decision or an explicit open item.

### 2.5 "1 Hz" stated as established hardware fact — `docs/reports/phase1-report-draft.md` §1, feasibility §2.3/§5
Phase1 draft: *"a ~1 Hz aggregate step-change sensor"*. Reviewed framing (`research-brief.md` §4, statement §3 item 1): ~1 Hz is a practical ceiling *measured on the Pro 3EM family*; the EM Gen3's own rate **must be measured on live data**. (Feasibility §8 already corrects its own earlier 1 Hz claim — the phase1 draft was written against the uncorrected number.)

---

## 3. Gaps (quarantined claims not yet recorded where they belong)

### 3.1 H11 omits the quarantined anomaly rung — *patched 2026-09-20*
`deprecated/baseline_runs/summary.md` L88: an anomaly rung **was executed** (`R6_anomaly/`, on the R1 residual: aggregate − always-on − attributed). H11's evidence section said "[none]". Now recorded there as [quarantined] prior-art claim per registry rule 1.

### 3.2 Plan §5.3 diagnostics absent from §7.2 — candidate additions
Onset error (median |Δonset|), offset error (dwell accuracy), and the **confusability matrix** (per predicted-×-true appliance cross-counts) are useful, user-facing diagnostics the current metric glossary lacks. Confusability matters doubly: it is the kettle-vs-heater visibility that H07-L2/H08 need.
Related: the plan's matching rule (onset tolerance **+ dwell-ratio band 0.5-2.0**) is a *third* matching family — §7.1's menu currently lists only both-edges-τ or IoU. It must be on the menu at freeze time.

---

## 4. Consistent (audited, no contradiction)

- **Plan §5.1-5.3**: episode-first, pointwise accuracy explicitly rejected, energy share beside every number — the current §7 mirrors this. The contract stands on its own legs now (the plan is quarantined), but there is no conflict.
- **Deployment parity** throughout the plan and the campaign harness language (*"the detector sees only the aggregate; submeters are GT only"* — campaign.md L4, summary.md L5).
- **`docs/datasets/data-collection.md` §5.1**: calibration sessions as known-truth windows, flag-not-delete cleaning, NO-DATA → explicit UNKNOWN gaps — aligned with §5, H05, and the UNKNOWN discipline.
- **`docs/datasets/gold-layer.md`**: the aggregate is an independent measurement and submetering is partial — aligned with H05 (books do not close by submeter sum).
- **`docs/product/use-case-reassessment.md`**: the cited anomaly-detection papers (worse on NILM-reconstructed traces than on submetered data) are *supporting* evidence for H11's caution; its "measure once, compare, decide" alternative aligns with FAQ Q13's spot-rig discussion.
- **phase1 draft**: per-household calibration sidesteps cross-house model collapse — consistent with H09's two-sided claim; the synthetic-data verdict (unusable substrate) matches the statement's input discipline.

## 5. Recommended actions

1. ~~Record R6_anomaly in H11~~ (done, 2026-09-20).
2. Decide §4: add a **provisional-verdict mode** or file it as an open item (client-facing).
3. Add the plan's three diagnostics (onset error, offset error, confusability) and the dwell-ratio matching family to §7's menu at the next contract touch — marked [quarantined] in origin.
4. Put the rolling-baseline variant on H02's instrument freeze list as an ablation.
5. When the client report is written, feasibility Recommendation 5 needs an explicit one-line answer (accepted-as-evaluation-rig / rejected-as-product-input), not silence. — *Answered 2026-09-20: corrections section 9 added to `docs/product/feasibility-verdicts.md`.*
6. `deprecated/baseline_runs/` deprecated as a whole (banners on the three top-level summaries and the plan doc; AGENTS.md/README updated; tree moved under `deprecated/`): **kept on disk, not deleted** — the registry's recorded claims cite these paths, and the idealized numbers remain the upper-bound sanity check on the redo (a real-protocol result far above the idealized bound indicts the instrument). The redo is the H02 button-press simulation — a different calibration side on the same substrate — not a re-run of R2-R6.
