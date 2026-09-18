# The Loop Is the Product: Scope, Behavioral Priors, and the Unknown

**Context:** Three brainteaser follow-ups to `../research/analog-problems.md` and `use-case-reassessment.md`, asked while rethinking the product core: (1) must we record every consuming device, or only those above some wattage level? (2) can user feedback / behavioral data act as a feature that unblocks what the power channel cannot distinguish? (3) what if we monitor the unknown source, detect anomalous change, and ask the user whether they bought a new device?
**Status:** Strategy note with two newly computed evidence blocks (UK-DALE slice energy shares; synthetic-set residual share) and OpenAlex-verified citations where found. One real house plus one synthetic generator — indicative, not field proof.
**Read alongside:** `use-case-reassessment.md` (core thesis, same dir), `../research/analog-problems.md` §2.7 (the residual), `../research/nilm-visual-reading.md` §10 (the rate experiment), `../../research-logs/training-approaches.md` (active-learning papers).
**Short answer:** (1) No — and wattage is the wrong cut: the right cuts are *detectability* and *materiality*, and they disagree with each other. (2) Yes — ambiguity is conditional on the evidence available, and behavior is a conditioning variable you can buy with a 10-minute survey instead of better hardware. (3) Yes — and that is the product: the unknown bucket is not a failure mode, it is the engagement surface and the data flywheel. All three converge on one reframe: "which device consumed which" is weak; "a house that notices things and asks good questions" is strong.

---

## 0. The three questions are one question

The stated product core — show/estimate which device consumes which — has been judged weak in the feasibility work: disaggregation accuracy is bounded by the sensor, ambiguity is irreducible 32.6% of the time, and insight-driven savings decay within weeks. All three brainteasers quietly point at the same replacement: the value is not in the naming, it is in the **loop** — notice change, attribute what is attributable, declare what is not, ask the user exactly one good question when it matters, and get permanently better from the answer. Disaggregation becomes a component of that loop, not the product itself.

## 1. Q1 — Record above detectability, rank by materiality

"Only those above a wattage usage level" conflates two different thresholds:

- **Detectability**: step size versus the 30 VA sensor floor. Determines what you can *name*.
- **Materiality**: energy = power × duty cycle. Determines what *matters on the bill*.

They disagree, and the disagreement is the whole answer. Computed this session on the UK-DALE slice (one house, 70.66 days, 6 s cadence, 985,855 common samples):

| appliance | mean-ON power (W) | duty (%) | kWh/yr | share of named energy | median step (W) |
|---|---|---|---|---|---|
| monitor (desk setup) | 111 | 82.1 | 667 | 49.3% | 71 |
| fridge | 109 | 36.5 | 341 | 25.2% | 107 |
| dish_washer | 97 | 2.4 | 140 | 10.3% | 57 |
| kettle | 2,890 | 0.4 | 107 | 7.9% | 2,887 |
| washing_machine | 161 | 1.4 | 97 | 7.2% | 128 |

(Shares are of the five named loads' combined 261.8 kWh over the window; "monitor" is this house's desk setup — one house, do not over-generalize.)

Read the table against the question. The kettle has the loudest signature in the house — 2,887 W steps, the calibration document's worked example — and the *smallest* materiality among the five: 7.9% of named energy, 107 kWh/yr. The monitor draws 71 W steps, barely above the Shelly's 30 VA floor, and carries 49% of named energy simply by being on 82% of the time. And the reference point that makes it vivid: a 10 W always-on router costs 87.6 kWh/yr — within 20% of the kettle. The most visible appliance in the house and an invisible one cost about the same.

So "record everything above a wattage level" fails in both directions: it over-targets the kettle and under-targets the monitor; and it cannot represent the router at all, because a constant load has no step to record — it lives in the baseline, not the events.

The second evidence block is the product's own synthetic dataset (30 days, 5 s, 518,400 rows): the four named appliances are **28.8%** of total energy; the unnamed base load is **71.0%** (mean 264.9 W). By construction — the generator built a base load that dwarfs the named loads. In a real house that residual is dozens of small devices. You will never name it by instrumentation, and you do not need to: **identification and accounting are different goals.** Awareness needs accounting ("everything else cost you X this month, and it is trending up"); naming matters only where naming changes action.

Three classes fall out:

| class | examples | ground-truth policy |
|---|---|---|
| detectable + material | fridge, heater, washing machine | record (calibration session); name |
| detectable + immaterial | kettle, toaster, microwave | name anyway — they arrive free with the calibration |
| undetectable | router, standby, chargers, sub-floor lighting | never record; *declare* in a 10-minute inventory; account as residual |

The residual is not a failure. It is a reportable line item — total minus identified — and its trend is precisely what "electricity awareness" means for the small stuff.

## 2. Q2 — Behavioral data is the conditioning variable that breaks ties

Formally: "indistinguishable" is conditional, not absolute. The posterior P(states | power) is ambiguous exactly when the likelihood is flat between competing hypotheses — kettle versus heater at 2,100 W is that case. But P(states | power, schedule, inventory, feedback) is frequently sharp. Nothing changed in the physics; the posterior received more evidence. The power channel is one channel; behavior is the missing channel, and it is cheap.

The analogy from your own field is exact. ASR never resolved homophones with better acoustics — "recognize speech" and "wreck a nice beach" are acoustically near-identical and linguistically trivial — it resolved them with the language-model prior. The power channel is the acoustic channel; the behavioral prior is the language model. In speech you needed on the order of 100,000 hours to learn the prior; here the prior is one user's house, acquired in a 10-minute survey. It is the cheapest high-value feature in the product.

Four evidence channels, ranked by cost:

1. **Declared inventory** — a 10-minute survey, zero instrumentation. Resolves existence-level ambiguity: "there is no space heater in this house" kills kettle-versus-heater before any power data arrives. Also powers residual accounting (§1).
2. **Temporal and contextual priors** — time-of-day, occupancy, season, weather. Kettles spike at breakfast; heaters ramp with occupancy; nothing is a heater in July. Verified anchor: context-aware deep NILM ("Scale- and Context-Aware Convolutional Non-Intrusive Load Monitoring", IEEE Trans. Power Systems 2019, 146 cites) showed context features improve disaggregation. The classical version of the same idea is a prior table in the factorial HMM (`analog-problems.md` §2.1) — no deep net needed.
3. **Explicit feedback on shown detections** — confirm or correct. This is active learning, already catalogued in `training-approaches.md` (Applied Energy 2023; IEEE Access 2020; TIM 2023). Every correction is a permanent labeled template: the user is a free annotator for exactly the events they care about.
4. **Implicit feedback** — did the user act on the insight? Weights future questions and measures engagement.

Mechanism: the DBN/HMM absorbs all four as weighted evidence — noisy human labels are just low-confidence evidence, which the model handles natively. "Guided calibration" then stops being a one-week session and becomes the loop: detect, show the best guess *with its uncertainty*, let the user correct, tighten the prior, detect better.

Honest limits. Feedback cannot lower the 30 VA floor — no declaration makes an unmeasured load measurable (though declaration still fixes its *accounting*, per §1). Feedback is sparse, biased toward salient events, and sometimes wrong — confidence-weight it and never force a label; ask open questions. And the channel only opens if the UI surfaces uncertainty: users cannot correct what they were never shown.

## 3. Q3 — Monitoring the unknown: the residual becomes the product

This is `analog-problems.md` §2.7 (the spike-sorting residual) turned from failure mode into product surface. After modeling known appliances and baseline, the residual is itself a signal: a *persistent new pattern* — a new step level, a new periodic box, a new schedule — is a candidate novelty.

Two detection regimes:

- **Event-visible novelty**: a new 1.5 kW device produces steps far above the floor; the PELT/changepoint machinery (`analog-problems.md` §2.5) finds it.
- **Baseline-shift novelty**: a new 25 W always-on device is invisible per event but visible as a sustained shift of the baseline model — integration beats noise over time. This is the mechanism behind "always-on" estimates in commercial products; unverified for this stack, and one of the cheapest experiments available.

Then the move you proposed: ask. "We noticed something new drawing about 150 W each evening around 19:00 — anything new in the house?" Every answer is simultaneously a labeled template, an inventory update, and earned trust. The anomaly question converts the system's own uncertainty into the user's teaching moment.

But an anomaly is not necessarily a new device. Classify before asking:

| branch | example | follow-up | value |
|---|---|---|---|
| new device | aquarium heater bought last week | confirm, name, add template | data flywheel |
| fault | fridge compressor cycling oddly | advisory alert, careful wording | highest value — food-loss prevention |
| seasonal | heater returns in winter | prior update, not an alarm | keeps noise down |
| behavioral | guests for the weekend | nothing, or a soft note | avoids wrong labels |

The detection half is a recognized research line: "Unknown Appliances Detection for Non-Intrusive Load Monitoring Based on Conditional Generative Adversarial Networks", IEEE Trans. Smart Grid 2023 (43 cites); "Unknown appliances detection for non-intrusive load monitoring based on vision transformer with an additional detection head", Heliyon 2024 (17 cites); and the fault branch has its own review ("Fault Detection and Efficiency Assessment for HVAC Systems Using Non-Intrusive Load Monitoring: A Review", Energies 2022, 56 cites). All verified this session via OpenAlex.

Ask design — the difference between a feature and a nuisance: open questions, not leading ones ("did you buy a device?" forces a wrong label onto a behavioral anomaly); hysteresis and confidence thresholds so the system does not cry wolf; a rate limit, because questions are an engagement budget and spending them daily burns it.

This loop is also the answer to the core-thesis decay finding (insight-to-action 1.9–3.9%, fading within four weeks): dashboards decay because nothing new happens after week two; anomaly questions are re-engagement events by construction — the product notices something, the user gets to be right about it, the model gets better. The product that asks good questions retains longer than the product that draws charts.

Risks, honestly: false positives erode trust faster than anything else (two wrong "new device?" questions in a month and the user stops answering); fault claims carry liability — word them as observations, never diagnoses ("your fridge is cycling differently than usual", not "your fridge is failing"); and mind the creepiness line — notice things the user would want noticed.

## 4. What the reframe changes

- **KPI shift**: from per-appliance disaggregation error to {novelty detection precision, attribution coverage over time, question acceptance rate, residual honesty}. Naming the top loads still matters — as one component, not the product.
- **The hardware constraint hurts less**: noticing is not naming. The 30 VA floor bounds detection of small loads, not awareness-through-accounting; the unverified live sampling rate (`nilm-visual-reading.md` §10) still gates event-level features, but the loop works at whatever rate the Shelly sustains.
- **Smallest prototype**: a residual monitor plus one well-designed question. It tests the thesis without new hardware and without solving disaggregation completely.
- The feasibility chain is unchanged: the rate experiment remains the first thing to run.

## 5. One sentence

The weak version of the product asks the model to name every watt and fails on the 71% it cannot see; the strong version asks the model to notice change, attribute what it can, declare what it cannot, and ask the user exactly one good question when it matters — the loop is the product, and the loop is buildable on the hardware you already have.

---

## Appendix: computed numbers and verified sources

**UK-DALE slice (computed this session; one house, 70.66 days, 6 s cadence, 985,855 common samples; channels 2–6 per labels.dat; energy = sum of 6 s samples)**
See the table in §1. Named total: 261.8 kWh over the window. Kettle annualized 107 kWh/yr versus 87.6 kWh/yr for a hypothetical 10 W always-on router.

**Synthetic Shelly CSV (computed this session; 30 days, 5 s, 518,400 rows)**
whole_house 53.7 kWh/30d; shares of total energy: kettle 10.5%, washing_machine 8.9%, fridge 6.7%, microwave 2.7%; unnamed base load **71.0%** (mean 264.9 W, 5th percentile 185.2 W, 95th percentile 363.6 W). The base load magnitude is the generator's construction, not field evidence.

**Citations verified this session via OpenAlex**
- "Scale- and Context-Aware Convolutional Non-Intrusive Load Monitoring", IEEE Transactions on Power Systems, 2019 — doi:10.1109/tpwrs.2019.2953225 (146 cites) — Q2 context channel
- "Unknown Appliances Detection for Non-Intrusive Load Monitoring Based on Conditional Generative Adversarial Networks", IEEE Transactions on Smart Grid, 2023 — doi:10.1109/tsg.2023.3261271 (43 cites) — Q3
- "Unknown appliances detection for non-intrusive load monitoring based on vision transformer with an additional detection head", Heliyon, 2024 — doi:10.1016/j.heliyon.2024.e30666 (17 cites) — Q3
- "Fault Detection and Efficiency Assessment for HVAC Systems Using Non-Intrusive Load Monitoring: A Review", Energies, 2022 — doi:10.3390/en15010341 (56 cites) — Q3 fault branch
- "Real-time Disaggregation of Residential Energy Consumption Enhanced with User Feedback", CCCS 2019 — doi:10.1109/cccs.2019.8888140 (1 cite; weak but real) — Q2
- Active-learning NILM papers: already verified and catalogued in `training-approaches.md`
- The homophone/language-model analogy is common knowledge in speech; no citation attached
