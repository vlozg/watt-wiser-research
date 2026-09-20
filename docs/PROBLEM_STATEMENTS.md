# Problem statements — WattWiser NILM

**Status:** the grounding doc for what the problem *is* — inputs, outputs, calibration protocol, evaluation contract — plus the FAQ that settles the misunderstandings surfaced so far. Maintained by hand; cited by `docs/hypotheses/`. If any other doc disagrees with this one, this one wins until revised here.
**Created:** 2026-09-20, from the owner-settled conversation on the calibration method.

---

## 0. Trust tags

Every factual claim in this doc carries exactly one tag:

| Tag | Meaning |
|---|---|
| **[reviewed]** | Appears in owner-reviewed, approved material: `docs/knowledge/`, `docs/research/`, `docs/reports/dataset_eda/`, `src/pipelines/00_download_dataset/`, `src/pipelines/01_extract_dataset/`, `src/pipelines/02_fnd_eda_notebooks/` |
| **[client]** | From the client-provided original `docs/client/docx/Calibration_Refined_for_Professor_Review (1).docx` (gitignored; client input, not agent-generated). "§n" refers to that document's sections |
| **[quarantined]** | Exists in the repo but has **not** been owner-reviewed (`deprecated/baseline_runs/`, `docs/experiments/`, `docs/reports/phase1-report-draft.md`, `docs/datasets/`, `docs/product/`, `deprecated/analysis/`, `data/gold/`). Recorded as a *claim*, never as fact |
| **[owner]** | Stated by the project owner in conversation (2026-09-20); re-confirm with the client where it changes product behaviour |

[quarantined] claims are exactly what the hypothesis registry (`docs/hypotheses/README.md`) exists to verify or discard. Numbers from quarantined artifacts can never promote a hypothesis to *proved* by themselves.

---

## 1. The problem in plain language

A home has one electricity meter at the point of connection — the **aggregate**. One number (watts), sampled at a fixed cadence, with everything the household does superimposed into it [reviewed: `00_overview.md` §2]. The product does **not** install meters on appliances. Instead:

1. The user enrolls a few devices: enters identity/type plus whatever the device's power label states, then runs one or more **guided calibration sessions** — press start on the device, press stop, end the session — while the whole-house signal is recorded [owner; client §4-5].
2. From those sessions the system builds an **appliance profile** (typical power, ΔPower at switch-on, typical duration, variability). Its mathematical form is deliberately open [client §6].
3. From then on the system watches the aggregate and answers, per event: **which enrolled device is running, when, and how much energy it used — or UNKNOWN** [client §7]. User confirmations feed back into profiles [client §1].

The learning loop: *calibration → feature extraction → profile → unseen event → prediction → user confirmation → profile improvement* [client §1].

---

## 2. Formal statement

**Given:**

1. one aggregate power series P = {p_t}, t = 1..T, at fixed cadence Δt. Hardware context [reviewed: `research-brief.md` §4]: ~1 Hz practical telemetry ceiling (measured on the Pro 3EM family; the EM Gen3's exact rate **must be measured on live data**), 1-minute onboard log, 30 VA no-load blind spot (below ~30 W nothing is seen), ±5% accuracy below ~230 W, 500 W CT calibration minimum. The deployment logging cadence (60 s class) is the current assumption [quarantined] and is treated as an experiment variable throughout;
2. for each enrolled device d ∈ D: metadata (identity, type, user-entered power-label values) and an enrollment record of K_d ≥ 1 **guided sessions** — product guidance: at least 3 **valid** sessions [owner] — each a single continuous interval I_{d,i} = [s, e] **of the same series**, bounded by the user's start/stop presses, carrying an interference flag [client §5];
3. nothing else. There is **no per-device submeter at any time**, end to end [owner; consistent with client §3's signal table, which lists only aggregate-side quantities].

**Estimate**, for t after enrollment: the per-device decomposition

> p_t = Σ_d p̂^(d)_t + û_t

where û_t is the unattributed residual (always-on + UNKNOWN). Per event: device-or-UNKNOWN with onset/offset and a score [client §7]. Per device: attributed energy, always reported next to its **energy share** so materiality is visible [reviewed: `00_overview.md` §5]. The books must close: attributed + always-on + UNKNOWN ≈ mains energy, with the residual's size reported per home, never assumed [reviewed: `00_overview.md` §2, §6 finding 4].

**Scope** [client §1, §10]: a *small number* of enrolled appliances; "we are not trying to perfectly identify every appliance in the home at this stage"; UNKNOWN is allowed instead of forcing a prediction; evaluation happens on unseen events.

---

## 3. Input universe — "anything we collect, we may use"

Owner principle (2026-09-20): the collection design defines what exists; the method is free to use **all** of it — and we can collect more where possible. The one hard boundary is set by the product: **no per-device metering, ever**.

| Input | Available | Role | Notes |
|---|---|---|---|
| Aggregate active power (W) | runtime, continuous | primary detection signal | [client §3] |
| Aggregate aux channels: voltage, current, apparent power, cumulative energy | runtime, where the hardware exposes them | candidate features (→ H08) | Public datasets are nearly W-only (REDD records apparent power *instead of* W) [reviewed: `00_overview.md` §6] → designable now, testable only on live Shelly data |
| Device metadata from the UI prompt: name, type, power-label values | enrollment | usable like any input; contribution measured per use-site by ablation (→ H07 ladder); the method must degrade gracefully when the field is empty or wrong | dataset channel labels demonstrably lie [reviewed: `00_overview.md` §6 finding 2]; nameplates are rated maxima, not measurements [owner inference, untested] |
| Guided sessions: press-bounded intervals + local baseline + ΔPower + interference flag | enrollment | **the only supervision the method ever gets** | [client §5]; other appliances may run freely during a session |
| User confirmations of predictions | post-deployment loop | profile improvement [client §1] | collected lazily, for free |
| Per-device submeters / waveforms | **never** | — | deployment parity boundary; submeters exist only inside public datasets, and only for *scoring* |

---

## 4. Output

1. **Per event:** enrolled device or UNKNOWN; onset/offset times; a score/confidence feeding the UNKNOWN threshold [client §7].
2. **Per device:** attributed energy over any window, beside its energy share [reviewed: `00_overview.md` §5].
3. **The books:** per-home residual honesty line (how much energy went to UNKNOWN) [reviewed: `00_overview.md` §5 item 4].
4. **Loop artifacts:** confirmations and open questions to the user [client §1].

---

## 5. Calibration protocol (as settled 2026-09-20)

1. **Collect metadata.** UI asks for device identity/type + whatever the power label states (nameplate watts, rated current) [owner]. Optional inputs; see H07 for how much they may be trusted.
2. **Run a guided session.** User presses device start, device stop, then ends the session. The aggregate is recorded throughout; a session = an interval of the same series [owner; client §5 step 1].
3. **Condition each session.** Estimate the normal household power immediately before switch-on (local baseline); compute ΔPower at the transitions; **flag sessions where another appliance causes a significant overlapping change** [client §5 steps 3-5]. The flag rule's precise threshold is ours to operationalize and must be frozen before any experiment (→ H06).
4. **Repeat freely.** As many sessions as the user wants; guidance "at least 3 valid sessions" [owner]. The client doc implies multiple sessions per profile ("combine valid calibration sessions" [client §5 step 7]).
5. **Build the profile** from valid sessions only. Form deliberately open [client §6].
6. **Detect.** Unseen event → compare against profiles → highest score → threshold → device prediction or UNKNOWN [client §7].

Physical reality of a session: only the calibrated device is under user control; everything else in the house runs as it pleases [owner]. Consequence: short sessions (kettle, 2-4 min) are usually clean; long ones (washer, 1-2 h) are near-certainly contaminated (assumption under test — H12) — fridges cycle every 10-40 min [reviewed: `00_overview.md` §6 priors]. Contamination therefore hurts the already-hard device classes worst.

**Placement and press accuracy (raised in owner review, 2026-09-20).** Three product-relevant consequences:
- **Presses are priors, not truth.** The press-bounded interval is snapped to the actual step in the aggregate within a search window, so small human timing errors cost nearly nothing; the cost beyond the window is quantified by H10.
- **The app can pick the moment.** A quiet-window indicator computed from the live signal (low recent variance, no recent steps) tells the user a good time to calibrate without them needing to know anything (yield effect measured under H06).
- **Not every device has a button.** A fridge cannot be started and stopped on demand, so a **passive calibration mode** (record a 2-3 h window; segment its natural cycles) is a likely requirement — open item, §10.

---

## 6. What "baseline" means here

Three distinct objects, often conflated:

1. **The harness** — evaluation protocol + metrics + splits, frozen before any run (§7).
2. **The anchor** — a deliberately simple, rules-based detector ("the dumbest honest thing that works"), explainable to the client, run under the harness. The client doc leaves rule-vs-ML open [client §9 Q3]; our stance: rules first.
3. **The floor** — the measured numbers any future model must beat.

The existing campaign artifacts (`deprecated/baseline_runs/`, spec `docs/experiments/baseline-ukdale-plan.md`) claim all three but are [quarantined] — and, critically, their calibration side was **idealized**: signatures were derived from clean per-device submeter traces, which the real product will never have. Their numbers are upper bounds recorded per hypothesis, not evidence. The button-press calibration simulation (H02) is the instrument that re-derives them under the real protocol.

---

## 7. Evaluation contract

- **Headline metrics are episode-level precision / recall / F1.** Pointwise accuracy is rejected: duty cycles span 0.5% (kettle) to 40%+ (fridge), so a detector that always answers "fridge ON" scores well while detecting nothing [reviewed: `00_overview.md` §5].
- **Energy share / energy attribution** is the co-metric on every table [reviewed: `00_overview.md` §5].
- **UNKNOWN is mandatory** in every evaluation; coverage/residual honesty is printed *before* any accuracy number [reviewed: `00_overview.md` §5 item 4].
- **Calibration events are strictly separate from test events** — and the split must not overfit "to one session or household" [client §8]. Session-level and household-level separation are both required.
- Matching rules and tolerances are **frozen in the hypothesis file before the run**; never tuned on test. There are **no pre-declared per-class pass bars** [owner decision 2026-09-20]: the baseline ladder (§6) is the reference — the **floor** (trivial detection) is the absolute reference, the **anchor** (calibration-based detector) the practical one. A verification passes by beating the anchor — or the floor, as its statement specifies — by a margin frozen in advance.
- Deployment parity: at runtime the method sees only the §3 runtime inputs. Public-dataset submeters exist for the scorer only.

### 7.1 How to score (the recipe — exact numbers frozen per experiment)

- **Episode:** one contiguous ON span of a device (ground truth), one contiguous detected span (prediction). Both are scored at the **runtime cadence being scored** — ground truth is resampled to the same view the detector had (deployment parity).
- **Matching:** greedy one-to-one, best score first. A match requires onset and offset each within a tolerance τ — how many seconds early or late an edge may land and still count as detected (frozen per experiment, scaled to cadence) — or an overlap rule (IoU: how much of the two time-spans covers the same stretch, "do the two shadows mostly coincide"). Pick **one** rule, freeze it, never tune on test.
- **Reporting discipline:** coverage line first; per house × appliance × cadence tables; no aggregate-only numbers; no accuracy without its UNKNOWN row.

### 7.2 The metrics, one by one (plain words, then the formula)

Notation: `est(t)` = the system's power estimate for a device at time step t; `true(t)` = the submeter's ground truth at the same step, resampled to the runtime view (§7.1); N = number of steps in the window; Σ = sum over the window. Two families: **episode-level** metrics judge *events* (did we catch it, was it the right device); **pointwise** metrics judge the raw power trace at every instant.

**Headline — episode level (uses the §7.1 matching):**

- **Precision (P)** — of all the times the system said "this device is running", how often was it right? Low precision = false alarms: the system blames the wrong device.
  `P = matched predicted episodes / all predicted episodes`
- **Recall (R)** — of all the times the device really ran, how many did the system catch? Low recall = missed events: silently wrong bills.
  `R = matched ground-truth episodes / all ground-truth episodes`
- **F1** — the one-number balance of the two; the harmonic mean punishes lopsidedness (all precision and no recall scores near zero, as it should).
  `F1 = 2 · P · R / (P + R)`
- **Energy attribution error** — over a window, how far the attributed energy is from the true energy, relative to the truth: "did the bill add up?" (The NILM literature calls this SAE, signal aggregate error.) Reported both per matched episode and over whole windows — the two fail differently. Trap: energy can look right while every event is missed (a stopped clock is right twice a day), so it is always paired with P/R/F1 on the same matched set.
  `error = | Σ est(t) − Σ true(t) | / Σ true(t)`
- **Energy share** — how much of the whole-home energy this device is even worth; the materiality line printed beside every accuracy number.
  `share = Σ true_device(t) / Σ mains(t)`
- **Residual rate** — the slice of the bill nobody could explain; this is UNKNOWN's row, printed before any accuracy number.
  `residual = ( Σ mains(t) − Σ attributed(t) − Σ always-on(t) ) / Σ mains(t)`

**Secondary — pointwise, computed on the raw power series (never the headline):**

- **Mean Squared Error (MSE)** — at every time step, take the gap between the estimate and the truth; square it, so a big miss hurts far more than a small one; average over the window. Reads as "how badly wrong, on average, with misses weighted by their size". Units: watts squared.
  `MSE = (1/N) · Σ [ est(t) − true(t) ]²`
- **Mean Absolute Error (MAE)** — the same gaps without squaring: simply the average size of a miss. Every step weighs the same; one terrible minute counts no more than its own size. Units: watts. More forgiving of outliers than MSE.
  `MAE = (1/N) · Σ | est(t) − true(t) |`
- **Why secondary — the duty-cycle trap:** high-duty-cycle appliances (a fridge is ON 40%+ of the time) dominate the pointwise average, so an always-on guess scores respectable MSE/MAE while detecting nothing. The episode metrics above are immune to that; MSE/MAE are reported for comparability with the NILM literature.

---

## 8. Role of the six public datasets

All [reviewed: `00_overview.md`]. In order of importance: (1) **the only ground truth available** — a real deployment has no per-device metering, so every quality number in this project (episode F1, energy attribution error, classic pointwise metrics such as MSE/MAE) is computable only here: the aggregate series stands in for the runtime signal, the submeters score it; (2) **priors** — the per-appliance fleet table (§6) that sanity-checks profiles and calibrations; (3) **textbook** — what the aggregate is made of. Deployment parity (§7) still binds: the submeters are the scorer's input, never the method's.

| Dataset | One-line role |
|---|---|
| UK-DALE | Primary reference; 1 s mains, ~6 s submeters; 4-year flagship house |
| REFIT | 20-home fleet scale; label-trust audit (labels can be wrong in both directions) |
| REDD | The US set; apparent-power caveat (magnitudes run high; ratios within panel unaffected) |
| ECO | 1 s plugs + occupancy labels |
| GREEND | Plug-level only, no site meter; label-trust testing |
| AMPds2 | Native 60 s — the degraded-cadence deployment proxy |
| (synthetic CSV) | Plumbing fixture only; not a substrate |

Standing findings that constrain any baseline [reviewed: `00_overview.md` §6]: cadence is the first-order design constraint; labels are incomplete and sometimes wrong (deduplicate canonicals; a vendor label alone earns no prior); residual mass is real and large and its composition is a per-house finding; simultaneity is low per bucket but high at events (~half of kettle/washer/dishwasher onsets begin while another target runs).

---

## 9. FAQ — the misunderstandings, settled

**Q1: Doesn't calibration give us a clean recording of the device (a submeter trace)?**
No. End to end there is a single signal. A calibration session is an interval of the *mixed* aggregate bounded by button presses; ΔPower is recovered by subtracting the local baseline just before switch-on [client §5]. Submeters exist only inside public datasets, and only for scoring.

**Q2: Can we ensure no other device runs during calibration?**
No [owner]. The client doc plans for exactly this: local baseline before switch-on + interference flagging of overlapping changes [client §5]. What we cannot yet claim is that flagging leaves enough valid sessions — that is H06 and nobody has measured it. And the upstream question — how contaminated would real calibration windows actually be? — is now measurable without any new hardware: H12 counts raw vs boundary-harmful contamination directly on all six datasets, replacing fridge arithmetic with fleet numbers.

**Q3: Is the power-label number used by the algorithm, or just UI metadata?**
It is collected, so it is an input like any other (owner principle) — and how much it *should* be used is a measurement, not a stance: H07 runs an ablation ladder (no labels → sanity check → tie-break prior among same-wattage devices → stabilizer for the first 1-2 sessions → hard constraint) and reports what each rung buys. Background risks, tagged honestly: dataset *channel labels* have been caught lying [reviewed: `00_overview.md` §6 finding 2]; nameplates are rated maxima rather than measurements and may be absent or mis-entered [owner inference, untested]. One requirement holds regardless of what the ladder shows: the method must degrade gracefully when the field is empty or wrong.

**Q4: How many calibration sessions does a device need?**
Product guidance: at least 3 valid ones [owner]. The real answer is a measured learning curve (H01), which is also the client's own open question [client §9 Q5]. Flagged sessions do not count toward the minimum.

**Q5: Is the first baseline machine learning?**
Open per the client [client §9 Q3]. Our stance: v1 is rules-based — threshold + duration matching — because it is explainable, reproducible, and the honest floor. If rules match the anchor's measured numbers (§6), ML is unjustified at this data scale; if they fall short of it, the case for ML must be argued from *this* evidence base as data grows.

**Q6: What is UNKNOWN and why does it exist?**
The explicit bucket for events/energy the method cannot confidently attribute. Mandatory: even the best-labelled dataset leaves a large residual [reviewed], the hardware is blind below ~30 W [reviewed `research-brief.md` §4], and pretending every watt is explained is the classic NILM overclaim.

**Q7: Do we promise whole-home disaggregation?**
No. A small set of *enrolled* devices + UNKNOWN [client §1, §10]. Always-on/standby loads are accounted, not detected — and are largely invisible to the hardware anyway [reviewed].

**Q8: Why not plain accuracy as the score?**
Duty cycles differ by two orders of magnitude across appliances; pointwise accuracy rewards always-on guessing. Episode-level P/R/F1 + energy share is the honest pair [reviewed `00_overview.md` §5].

**Q9: What are the six public datasets for?**
They are the project's **only ground truth** — the only place where disaggregation quality can be measured at all. A real home has no per-device metering (FAQ Q13), so outside these datasets no quality number is computable: not episode F1, not energy attribution error, not classic pointwise metrics such as MSE/MAE. Three roles, in order of importance: (1) **evaluation instrument** — the aggregate stands in for the runtime signal, the submeters score it; every verification in the registry (H01-H12) rides on this; (2) **priors** — the per-appliance fleet distributions that sanity-check profiles and calibrations; (3) **textbook** — what the aggregate is actually made of. What they are *not*: deployment data or a runtime input — the method never sees their submeters (deployment parity, §7).

**Q10: So what did the existing baseline campaign in the repo establish?**
Nothing officially — it is [quarantined]. Its claims are recorded per hypothesis as upper bounds earned with cleaner calibration than the product will have (§6). Verification under the real button-press protocol (H01/H02/H06) decides what survives.

**Q11: The calibration window is a human button press. How much does a sloppy press cost?**
The press is a prior; the signal is the truth. The system snaps the interval to the actual step in the aggregate within a search window, so errors smaller than that window cost nearly nothing. Beyond it, cost scales roughly like press-error / device-dwell: a 1-minute slip on a 2-minute kettle event is severe; the same slip on a 90-minute washer cycle is noise. The worst direction is a **late start press** — the device is already running when the baseline is taken, so ΔPower shrinks toward zero. H10 measures the full cost curve.

**Q12: Does it matter when the user calibrates? Clean sessions or busy ones?**
For estimating the device's signature, contamination never helps — a busy period only adds bias and flagged retries. So: prefer quiet periods, and let the app pick them automatically via the quiet-window indicator (§5). Time-of-day matters only *indirectly*, through how much else is running (evening peaks); the canonical devices' own signatures are effectively time-invariant. "Many busy sessions" is not better data — unless clean sub-intervals can be salvaged from flagged sessions, an open variant of H06. Caveat: the fridge cannot be button-calibrated at all (§5), and for it the placement question has a concrete answer: an overnight passive window.

**Q13: Can we validate on real homes?**
Not with ground truth — a deployed home has no per-device metering; that is the problem's boundary, not a flaw. What we can do: user confirmations (a product health metric, not science), physical consistency checks (the books, H05), and — if we choose to buy hardware — a **single smart plug on one device** during its normal life, giving per-device truth for that device only. A validation rig may use anything; it must simply never become a product input (deployment parity). The six public datasets remain the only full-truth laboratory.

---

## 10. Deliberately open (not settled here)

From the client's own list [client §10]: which features matter; the profile's mathematical representation; rule-vs-ML for v1; session count; confidence/UNKNOWN threshold definition; handling complex/overlapping appliances.
Ours, additional: the canonical target set (4 appliance classes used by the quarantined campaign vs the 5 canonicals of the reviewed EDA — microwave in or out); the exact interference-flag rule (H06); press-boundary robustness and the step-snapping search window (H10); placement policy — quiet-window guidance vs free choice, and salvage of contaminated sessions (H06); a passive calibration mode for non-button devices such as the fridge (product decision); whether to buy a smart-plug spot-validation rig (FAQ Q13); a device-health / anomaly use of profiles — pattern templates and drift-to-degradation signals (H11) — a candidate second feature, not MVP scope; the calibration-contamination reality check on all six datasets (H12) — the fastest hypothesis to settle.

---

## 11. Pointers

- Hypothesis registry: `docs/hypotheses/README.md` (status: drafted / proved / rejected).
- Client calibration document (original): `docs/client/docx/Calibration_Refined_for_Professor_Review (1).docx` (gitignored).
- Reviewed EDA entry point: `docs/reports/dataset_eda/00_overview.md`.
- Reviewed hardware facts: `docs/research/research-brief.md` §4.
