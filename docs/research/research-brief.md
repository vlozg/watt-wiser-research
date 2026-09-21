# WattWiser — Research Brief

**Prepared for:** the WattWiser technical assessment.
**Sources:** the project brief plus ~4 hours of desk research into the field, the hardware, and the prior SOTA
**Raw evidence:** `research-logs/`

---

## 1. Bottom line

1. **You are hired as an independent technical reviewer of the existing data work.**
2. **The problem space is NILM** (Non-Intrusive Load Monitoring / energy disaggregation) — a 40-year-old academic field with thousands of papers, a standing open-source toolkit, and several free open-source implementations that already do almost exactly what the brief describes.
3. **The brief's central hardware claim is wrong.** It says the Shelly EM Gen3 measures total household electricity "at high frequency". It does not. It is a **~1 Hz step-change sensor with a documented 1-minute onboard log and a 30 W blind spot**. This is the single most important technical fact in the engagement.
4. **Narrow version: feasible. Broad version: not.** Recognising 2–4 big resistive appliances (kettle, microwave, toaster, heater) in one house from household-specific calibration is realistic at 1 Hz. The commercial ambition in §1/§7 — whole-home, category-level, "unusual usage", standby — is not achievable on this hardware.
5. **The field's most-funded consumer product just quit.** Sense (USD 105M+ raised, 10+ years, kHz sampling) exited direct-to-consumer hardware on 31 Dec 2025, citing cost and installation friction. Their users' complaints were about disaggregation accuracy, not the meter.
6. **Recommendation:** start with a bounded "Stage 0 technical assessment" with a written deliverable before any broader work.

---

## 2. The correction that matters most

Sections 1-5 of the brief read like a **build specification**. §6 reads like a review engagement:

> "You are **not** being asked to join the project or take ownership of the model development. We would like your help as an **independent technical reviewer** to assess the current data science work…"

So the real ask is: **audit the existing ML work and give a verdict on whether it is technically sound.** That distinction matters for scope and expectations:

- The review is worthless without **access**: repo, notebooks, experiment logs, model outputs, raw data. Without access there is nothing to review, but an opinion may still be expected.
- "Independent technical reviewer" can drift into unbounded scope ("while you're in there, can you just fix it?"). **Clarify the review-vs-build boundary in writing before anything else.** It is the single biggest scope risk here.

---

## 3. Q1 — The problem space: what is going on, what do people talk about?

### 3.1 The field has a name

**NILM — Non-Intrusive Load Monitoring**, also called **energy disaggregation**. It was invented at MIT in the early 1980s (George Hart, Ed Kern, Fred Schweppe), funded by EPRI, patented as US 4,858,141, and canonised in Hart's 1992 Proc. IEEE paper (3,000+ citations). The founding insight is exactly WattWiser's: read the whole-home supply and infer individual appliances from the **step changes in real power (ΔP) and reactive power (ΔQ)** when they switch on/off. Multi-state appliances are modelled as finite-state machines.

It is not a new idea, and the team should not be allowed to present it as one.

### 3.2 The seven things the field actually argues about

1. **Sampling rate is the master variable.** kHz sampling gives you start-up transients, harmonics and waveform shape — highly discriminative. Sub-Hz sampling gives you only *step changes in a mean power value* — far less informative. Almost every strong published result uses kHz data or clean 1 s+ data with exact appliance ground truth.
2. **Generalisation across houses is the unsolved problem.** Models trained on house A collapse on house B. Even recent work states plainly that "the generalisation capability of these methods to different houses… [is a] major challenge" (arXiv 2103.12177).
   - **This is the one genuinely good strategic instinct in the brief.** The household-specific guided-calibration approach *sidesteps the field's hardest open problem.* That is a real, defensible reason to do it this way, and it should be the project's headline argument.
3. **"How good is good enough?"** The field's most useful reframing (Barker et al., arXiv 1510.08713): perfect appliance identification is unnecessary; even crude disaggregation measurably improves downstream inferences such as occupancy. **The right success metric is usefulness, not accuracy.**
4. **A reproducibility crisis, and an evaluation trap.** A large share of published NILM results cannot be reproduced. More importantly for your review, there is a documented **"performance gap between testing on real and denoised aggregates"** (arXiv 2008.10985): many papers evaluate on *artificial sums of individual appliance signals* rather than real recorded mains data, which **inflates accuracy.** Any evaluation the project presents must be checked for this.
5. **The load types that break everything:** multi-state appliances (fridges/freezers, washing machines with cycles), variable-speed/inverter loads (modern heat pumps, some chargers), simultaneous operation, and small/standby loads.
6. **Privacy.** NILM data reveals occupancy and lifestyle from a single meter — an established privacy concern and a real GDPR/consent question if they're collecting household data.
7. **Commercial disappointment.** For decades the field was noted for "a dearth of applications with demonstrated value". That has now been tested in the market — see §6.

### 3.3 What practitioners (not academics) talk about

From Home Assistant and r/Sense discussions, the recurring practitioner themes are strikingly consistent:

- The heuristic approach **works for big resistive loads** and only those: *"dryer, oven, stove, microwave, rice cooker, and EVSE"* (author of the HA community NILM blueprint).
- One-decimal, "update only on change" sensors destroy it.
- **Solar generation confounds it** unless separately subtracted.
- Small loads are invisible: *"a fridge and freezer change characteristic based on outside temperature… modern chargers change characteristic… These will obscure any wattmeter with a collective measurement."* (WallyR, HA forum)
- The recurring conclusion: *"It is impossible to map a house with only one wattmeter."*
- The pragmatic recommendation the community actually gives is **not disaggregation** — it is a **per-circuit panel CT monitor** (e.g. Emporia Vue, 16 channels): *"would have been far easier and cheaper to get individual z wave power meters."*

**Takeaway to hold in the meeting:** the community has already run this experiment informally and converged on the answer. WattWiser must either (a) stay inside the slice where the heuristic works, or (b) explain what it does that the community could not.

---

## 4. Q2 — The device: what a Shelly EM Gen3 actually collects

### 4.1 The brief's claim vs. reality

The brief asserts the Shelly EM Gen3 with a CT clamp *"measures total household electricity at high frequency."*

**That is false, and it is load-bearing for the whole project.**

| Claim | Reality |
|---|---|
| "high frequency" measurement | **No high-frequency mode exists.** The official datasheet lists **no 1-second measurement or logging interval at all.** |
| — | Onboard historical logging is **1-minute resolution, ~10 days of storage**. |
| — | Live telemetry via MQTT / WebSocket / HTTP RPC streams faster than the log, but the practical ceiling reported by users on the Shelly Pro 3EM family is **~1 new value per second** — *"neither scripts nor Modbus gave more than one new value per second"* (Shelly community forum, Jul 2025, acknowledged in-thread by a Shelly moderator; the thread is literally a feature request for >1 Hz, citing meters that offer 10 Hz). |
| Implied waveform data | **None.** Each value is an interval aggregate (mean/RMS), not a waveform. No transients, no harmonics. |
| — | **No-load threshold: 30 VA per channel** → anything below ~30 W is simply not seen. |
| — | Ammeter accuracy ±2% (2–50 A), ±2% (1–2 A), **±5% (0–1 A)**. At 230 V, 1 A ≈ 230 W, so below ~230 W the measurement degrades to ±5%. |
| — | Channel-to-channel calibration requires a **minimum 500 W load**. |
| — | 2 channels (2 CT clamps), 50 A CT included, single-phase, <1.2 W self-consumption, dry-contact relay. |

**Net: this is a ~1 Hz, 2-channel, aggregated real+apparent power meter with a 30 W dead zone.** It is a **step-change sensor**. It is not a research-grade NILM front end.

### 4.2 Why this matters so much

Sense's own software, per its CEO, *"takes millions of measurements per second."* The most successful disaggregation product ever shipped depends on **kHz+ sampling**. WattWiser proposes to do the same job on **1 sample per second**.

That is not automatically fatal — but it converts the project from "build a classifier" into **"prove that 1 Hz aggregate power is sufficient at all."** That is the actual research question, and it is a much better-defined one. The brief's §5 step 1 (*"Confirm the raw Shelly fields and sampling frequency actually available"*) shows the brief's author already suspects this, which is a point in the brief's favour — but §1's prose contradicts it.

**Be precise and fair about this in the meeting.** The hard 1 Hz evidence comes from the Pro 3EM family; the EM Gen3 datasheet simply documents a 1-minute log and claims nothing faster. The exact achievable rate on the EM Gen3 **must be measured**, not assumed. Ask for the raw data and compute the timestamp deltas yourself.

### 4.3 The fields you actually get (what to ask them to confirm)

Active power (W), apparent power (VA), power factor, voltage (V), current (A), active + apparent energy (kWh), fundamental active/reactive energy, internal temperature. Two channels. That is the complete feature set — power factor being "to be validated as a useful discriminator" in the brief is fair, since at 1 Hz and with this accuracy it is weak.

---

## 5. Q2b — Is there sample data online? Yes. Use it before spending a cent.

**There is no public labelled Shelly-EM-Gen3 household dataset.** But that is not a blocker, because there is a clean substitute.

### 5.1 Public datasets with per-appliance ground truth (open access)

| Dataset | Whole-home rate | Appliance rate | Size |
|---|---|---|---|
| **UK-DALE** (Nature Sci Data 2015) | **16 kHz** (and lower-rate mains) | 1/6 Hz | 5 UK homes; one for 655 days |
| **REFIT** (Nature Sci Data 2017) | ~8 s | 8 s | 20 UK homes, 2 years, ~1.19bn readings, 250k+ appliance uses |
| **REDD** | 1 s / 3 s (15 kHz some) | 1 s | 6 US homes |
| **PLAID / WHITED** | 30 kHz / 44.1 kHz | — | transient-level |
| **AMPds, HES, ECO, iAWE, EMBED, DRED, Pecan Street, MORED** | mixed | mixed | NILMTK has converters for ampds, combed, dataport, eco, greend, hes, iawe, redd, ukdale |

### 5.2 The useful trick

**Downsample the UK-DALE or REFIT whole-home channel to 1 Hz and you have a free, legitimate proxy for exactly what the Shelly produces — with ground truth attached.**

That means the entire methodology (event detection, feature design, baseline matcher, confidence thresholds, calibration-effort curve, confusion matrix) can be **built and validated offline, for free, before any hardware is installed in any home.** If a simple ΔP matcher cannot separate kettle/microwave/toaster on downsampled UK-DALE, it will not work on a Shelly either. This is the correct first move, it costs nothing, and it is a fair thing to expect before any hardware work begins.

Also available for a quick sanity check: Kaggle "Household Energy Disaggregation (NILM) – 1 Minute" (CC0, ~4 weeks of 1-minute household power with per-appliance ground truth).

---

## 6. Q3 — Has anyone done this before? Yes, repeatedly, including on this device

### 6.1 Open source already does this — for free

| Project | What it is |
|---|---|
| **lgarciamarrero92/ha-nilm** (51 stars, actively maintained) | *"Turn your whole-home power sensor into appliance activity and energy insight."* Learns appliance patterns in a **guided training phase**, then does **local inference**. Publishes per-appliance power/energy/on-off entities into Home Assistant. Ships an inference service + training server. Docker or HA add-on. Free. |
| **begleyt/shelly-3em-smart** | **NILM-style appliance detection from a Shelly Pro 3EM** — same device family, same concept, open source. Websocket event detection on power steps, tolerant matching (running mean + spread + duration + time-of-day), per-device kWh. |
| **bondesen/ha-el-detektiv** | Learns appliance power signatures. Notably smarter at calibration: a movable **smart plug is temporarily used as a "test meter"**, and its load is auto-subtracted from the whole-home "unexplained" figure — solving the labelling problem better than "ask the user to switch the appliance on". |
| **rsaikali/linkya** | NILM from a French Linky utility meter. |
| HA community **"NILM blueprint"** (tronikos) | **No ML at all** — matches sudden power increases with an almost-equal later decrease. Reported to work for *"dryer, oven, stove, microwave, rice cooker, and EVSE"*. |
| Others | robeertm/shelly-energy-analyzer, CircuitSetup Energy Analyzer, qcase-lab/AutoML-for-NILM, falkhaider/hems-nilm-homeassistant |

**The first act for any engineer is to read this list.** So a fair and revealing review question is: *did the project benchmark against ha-nilm and the HA NILM blueprint before building anything from scratch?* If not, that alone is a substantive finding.

### 6.2 The commercial cautionary tale — Sense

Sense was the best-funded, most technically credible pure-play in consumer NILM. It raised a USD 18M round led by Schneider Electric (2018) and a **USD 105M Series C (2022)**. Then:

- **3 Nov 2025 — Sense officially exited the direct-to-consumer hardware market** (Latitude Media, exclusive). It stopped selling the Sense Monitor on **31 Dec 2025** and pivoted to embedding its software inside utility smart meters.
- **The stated reason was not accuracy — it was cost and installation friction:** *"high up-front costs and complex installation requirements that limit adoption."*
- Its CEO's framing of the future: disaggregation only scales when the meter is already there and owned by a utility.

What Sense's own users report about disaggregation (r/Sense):

- *"6 months in — **very disappointed**… only recognised very basic appliances… The vast majority of the time, I just see a big unknown blob."*
- *"going on ~9 months now, only 16 devices 'recognized'…"*
- *"the mother ship downloaded a bunch of devices to my account **THAT NEVER TURNED ON**!!!"* (i.e. empty/auto-generated profiles presented as detected appliances)
- Reported coverage: **"5 years, 54% Other"**; another **"64% / 36% Other"**.
- *"not technically feasible to the extent expected by most consumers… feels like snake oil."*

**Why this matters to you:** the market has already run the experiment on "consumer disaggregation with a retrofit box", with far more money and far faster sampling than WattWiser has. It did not fail on the meter — **it failed on the disaggregation.** That is precisely the risk the brief underestimates.

Note the honest counter-argument, which you should put *to* them rather than assume: Sense was chasing *whole-home* disaggregation. WattWiser's brief deliberately narrows to a *small set of calibrated appliances*. That narrowing is the whole bet. Your job in the review is to test whether the team actually holds to that narrowing or drifts back toward the Sense promise — §1 and §7 of the brief already drift.

### 6.3 Academic prior art (for citation in the review)

- Hart, *Nonintrusive Appliance Load Monitoring*, Proc. IEEE 1992 (patent US 4,858,141).
- Zoha et al., *NILM Approaches for Disaggregated Energy Sensing: A Survey*, Sensors 2012 (~950 citations).
- Zeifman & Roth 2011; Kelly & Knottenbelt *Neural NILM* (arXiv 1507.06594).
- Barker et al., *How good is good enough? Re-evaluating the bar for energy disaggregation* (arXiv 1510.08713).
- *Investigating the Performance Gap between Testing on Real and Denoised Aggregates in NILM* (arXiv 2008.10985) — the evaluation trap.
- VAE for NILM (arXiv 2103.12177) — states cross-house generalisation is still unsolved.
- WaveNet for disaggregation + on/off detection, 20 households / 2 years on REFIT (arXiv 1908.00941). Directly on point: for the **on/off detection** task, a **direct binary classifier** gave the better F1. Worth noting, since WattWiser's real task is closer to on/off detection than to full disaggregation.

---

## 7. Q3b — Is it feasible? The honest verdict

**Split the question.**

**Feasible (credible, worth funding as a proof of concept):**
- Distinguishing **2–4 large, distinct, binary, resistive appliances** — kettle (~2–3 kW), microwave (~1 kW), toaster, heater, possibly an EV charger — where each switch-on is a **step change of several hundred watts**.
- **In a single household**, using household-specific guided calibration.
- With an explicit **UNKNOWN** class and honest confidence.
- Evaluated on genuinely unseen events, with precision/recall/F1 and a confusion matrix.

This slice is exactly what the HA community heuristic already achieves by hand. A 1 Hz ΔP sensor can see these steps. **This is a real, achievable MVP.**

**Not feasible on this hardware (say so plainly):**
- Whole-home or "category"-level consumption estimates.
- **"Always-on" / standby decomposition** — killed outright by the 30 VA no-load threshold.
- Anything under roughly **30 W**; anything below ~230 W is also only ±5% accurate.
- Multi-state appliances (washing machines, dishwashers beyond the heating element), variable/inverter loads, fridges on low duty.
- Reliable performance with PV/solar present unless generation is separately metered and subtracted.
- Simultaneous-load separation.

**The gap to name explicitly:** the product described in §1 and §7 is the *infeasible* column; the experiment in §5 is the *feasible* column. The brief's success criterion is well chosen ("a small number of important appliances… with transparent accuracy and confidence") — but its vision section is not. **The primary risk is that the project quietly reverts to the vision and then judges the technical work against an impossible target.** Making that boundary explicit is arguably the most valuable thing this review can deliver.

---

## 8. The technical question list

### A. Access and evidence (without these, a review is meaningless)
1. Is there **read access to the repo, notebooks, experiment logs, model outputs and documentation**, and can the code be run directly?
2. **Does any labelled data exist yet?** How many homes, how many days, at what polling interval, stored how — device 1-minute log or streamed live values?
3. Who owns that data, and what consents/privacy basis exist? (Whole-home load data reveals occupancy — genuine GDPR exposure.)

### B. The technical questions that separate a good answer from a bluff
4. **What is the measured sampling rate and the exact list of Shelly fields being ingested?** Ask for the raw log and compute the timestamp deltas yourself. The brief says "high frequency"; expect ~1 s or worse, with gaps.
5. Has the **30 VA no-load threshold** and the **±2–5% accuracy band** been accounted for? **What is the smallest appliance in scope?**
6. Is evaluation done on **real aggregate signals** or **synthetic sums of appliances**? (Synthetic sums inflate results — arXiv 2008.10985.)
7. Is the held-out test set **genuinely unseen events**, from unseen sessions/days? Or are calibration events leaking into evaluation?
8. Are they reporting **precision/recall/F1 and a confusion matrix including UNKNOWN**, or only accuracy?
9. **Have they benchmarked against existing open-source baselines** (ha-nilm, the HA NILM blueprint, a trivial ΔP threshold)? If not, why build from scratch?
10. **What is the baseline before ML?** A simple ΔP + duration matcher should already work for kettle/microwave at 1 Hz. If work jumped straight to a neural model, that is a red flag.
11. How is the **calibration-effort trade-off** quantified (1 vs 3 vs 5 examples)? Does the commercial case survive the answer?
12. Are **PV/solar, EV charging and three-phase** in scope? (PV breaks the heuristic approach unless separately metered.)
13. **What has been completed, and what is the evidence?** Ask for the last four weeks of concrete artifacts — not a status description.

### C. Two tests you can run yourself (cheap, and they establish credibility fast)
- **Ask for one week of raw Shelly data**, even unlabelled, and compute the timestamp deltas yourself. If they cannot produce a week of raw data, the project has not started.
- **Ask them to name the single hardest failure mode they have hit so far.** A real practitioner has one ready; a bluff does not.

### D. The question to ask them back
> "The most-funded company in this space just exited consumer hardware. What do you know that they didn't?"

---

## 9. Overall verdict

**Not necessarily — but not on the terms as described.**

### Green flags
- **The brief's §4 and §5 are genuinely good.** Narrow the scope first, confirm the raw data before modelling, visualise before choosing a model, build a simple baseline before ML, evaluate on unseen events with a confusion matrix, then sweep calibration effort, and **only then** consider a more sophisticated model. That is a well-sequenced, professional plan..
- The success criterion is honest and correctly scoped.
- Explicit UNKNOWN handling and a calibration-effort curve show real product thinking.
- It is a **bounded** piece of work: there is a defined deliverable (a technical assessment) and a defined question.

### Red flags
1. **The core hardware premise is factually wrong.** 1 Hz is not "high frequency". Either the documentation overstates the sensor, or the premise is aspirational. Technical risk is concentrated exactly where the brief thinks it has none.
2. **Scope is ambiguous** (§6 review vs §4–5 build). An ambiguity that invites unbounded scope.
3. **No evidence that any data exists.** If nothing has been collected, there is nothing to review — and the "review" silently becomes building it.
4. **The category leader just exited the consumer market** after USD 100M+ and kHz sampling. The commercial hypothesis in §1 is contradicted by the field's history.
5. **The differentiator is unclear.** Free open-source projects already do guided-calibration NILM for Home Assistant. Ask what is defensible here beyond the UI.

### Recommended first step: Stage 0 — Technical Assessment

A bounded **Stage 0: Technical Assessment** with a written deliverable:

> A technical assessment with a written deliverable covering: (i) an audit of what currently exists (code, notebooks, experiments, data); (ii) verification of the actual Shelly data quality and effective sampling rate on a real sample; (iii) a clear statement of what is and is not achievable on this hardware; (iv) a go / no-go recommendation with the three highest-value next steps.



---

## 10. Sources

**The brief**
- AI_Engineer_Project_Brief.docx (local copy; extracted under `docs/client/brief-extract/`)

**Device**
- Shelly KB — Shelly EM Gen3: https://kb.shelly.cloud/knowledge-base/shelly-em-gen3 (1-min log / 10 days, 30 VA threshold, accuracy bands, 500 W CT calibration minimum)
- Shelly community, "Higher measurement interval for Shelly 3EM (pro, any)": https://community.shelly.cloud/topic/10428-higher-measurement-interval-for-shelly-3em-pro-any/ (~1 Hz ceiling; >1 Hz feature request; 10 Hz comparative meters)
- Shelly EM Gen3 product/datasheet pages (no 1-second measurement or logging spec)

**Market**
- Latitude Media, *Is the era of direct-to-consumer energy hardware coming to a close?*, 3 Nov 2025: https://www.latitudemedia.com/news/is-the-era-of-direct-to-consumer-energy-hardware-coming-to-a-close/
- r/Sense: "Review, 6 months in - very disappointed"; "Sense Monitor no longer available as of December 31, 2025" (90+ comments); "Sense is going away" (DIY Solar Power Forum)

**Practitioner discussion**
- HA Community NILM blueprint (tronikos) and threads 619672, 557048, 306176, 402909

**Prior art (open source)**
- github.com/lgarciamarrero92/ha-nilm, github.com/begleyt/shelly-3em-smart, github.com/bondesen/ha-el-detektiv, github.com/rsaikali/linkya, github.com/robeertm/shelly-energy-analyzer, github.com/CircuitSetup/CircuitSetup-Energy-Analyzer

**Academic**
- Hart, Proc. IEEE 1992; US Patent 4,858,141
- Zoha et al., Sensors 2012; Zeifman & Roth 2011
- arXiv 1510.08713 (how good is good enough); arXiv 2008.10985 (real vs denoised aggregates); arXiv 2103.12177 (generalisation unsolved); arXiv 1908.00941 (WaveNet disaggregation + on/off detection on REFIT); arXiv 1507.06594 (Neural NILM)
- UK-DALE, Nature Scientific Data 2015; REFIT, Nature Scientific Data 2017; NILMTK dataset converters

Full raw captures: `research-logs/`
