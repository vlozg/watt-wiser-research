# WattWiser — Feasibility Verdicts

**Scope:** technical assessment of the calibration-to-detection plan as laid out in the calibration document and the 13-step user-journey diagram.
**Status at time of writing:** no data collected; device purchased; the plan of record was to **synthesise training data using generative AI** while the product is built.
**Read alongside:** research-brief.md
**Correction (later):** see section 8. The "1 Hz" figure used throughout this document is an inference across the Shelly product line, not a Shelly EM Gen3 specification.

---

## 1. The headline

**There is nothing to review yet.** The engagement is an independent technical review of the existing data work; at the time of writing no data had been collected and no analysis artifacts existed. A review requires artifacts. There are none.

**And the one concrete technical commitment stated — "I will synthesise the data with generative AI" — is not a viable approach.** It is either a misunderstanding of the problem or a way to produce impressive-looking output without doing the work. Either way it is the most actionable finding available.

**The good news:** the calibration document itself is well written, and the question it asks is genuinely answerable in about **one day of work**. The project is not doomed. It is just unstarted, and the stated plan for starting it is wrong.

---

## 2. The contradictions in the calibration design

These are factual, checkable, and you should raise them plainly.

**2.1 The document says one thing; the project status says another.**
The doc's own framing: *"We want to validate the methodology **before collecting substantial real-world data**."* That sentence implies some data exists or is imminent. **In fact none has been collected**, and the device was already bought. The document is written as if the project is further along than it is.

**2.2 The two diagrams disagree with each other on who owns the event boundary.**

| Figure 1 (internal flow, "Figure 1. Current proposed guided-calibration workflow") | Journey diagram (13-step UI flow) |
|---|---|
| "User turns the appliance ON • **System detects ON event**" | Step 7: user presses **"I've Started the Machine"** — a user declaration |
| "User turns appliance OFF and clicks 'I've turned it off' • **System detects OFF event** • Calibration session ends" | Step 8: a **countdown timer** (48:00) runs down and the session ends when it hits zero |

Two different designs:
- **Who marks the ON event — the sensor or the user?** Figure 1 says the system detects it. The UI flow says the user asserts it.
- **How does the session end — when the appliance actually stops, or when a guessed timer expires?** Figure 1 says when the user says it stopped. The UI says when the countdown reaches zero.

This matters concretely: the journey diagram has the user **type the cycle duration in advance** ("Cycle Duration (shown on machine): 48 minutes"), and the recording window is bounded by that guess. If the real cycle runs 60 minutes, **you lose the last 12 minutes — which is exactly where the drain and spin signature lives.** If it runs 40, you record 8 minutes of nothing. The internal flow's design (end on actual stop) is the correct one. The implemented flow appears to be the weaker one, or the two flows were never reconciled. Ask which is implemented.

**2.3 The design targets the hardest appliance first.**
The entire 13-step journey is built around the **washing machine**. But:
- The brief's own §5 says start with *"2–4 relatively simple appliances… (for example kettle, microwave, toaster/heater)"*.
- Their own document's §3 says complex appliances *"may require sequence/operating-pattern analysis rather than a single steady power level."*
- A washing machine is multi-state, load-dependent, temperature-dependent, program-dependent, and its signature at 1 Hz is a 48-minute **sequence**, not a step change.

The most elaborate calibration UX has been built for the appliance that is hardest to disaggregate, on a sensor that is least suited to it, **before validating the trivial case.** That is backwards, and it is the most important process finding in the document set.

**2.4 The calibration flow generates almost no training data.**
This is the flaw that most directly threatens their own success metric.

- One 48-minute washing session yields roughly **one ON transition and one OFF transition** — maybe a handful of internal state changes. Running the recommended *"at least 2–3 calibration sessions"* gives you somewhere in the region of **3–9 events** for that appliance.
- The brief's key commercial metric is the **calibration-effort curve: how accuracy changes with 1, 3, 5 examples.** With 48-minute sessions you cannot even populate that curve cheaply — each data point costs the user three quarters of an hour.
- A **kettle** gives you 10 clean, labelled ON/OFF pairs in **10 minutes**, with near-identical ΔP. It is the ideal calibration target: cheap for the user, high event count, low variance, and it directly tests the 1 Hz step-detection question.

**The washing-machine flow is the most expensive possible way to produce the least useful training data.** Start with the kettle.

**2.5 The 30–60 second baseline is too short and conceptually weak.**
Step 6 of the journey says *"Recording household baseline… Please wait (30–60 seconds)."*

- Household baseline is not stationary. A fridge compressor cycles on and off on roughly a 20–40 minute duty cycle. A 30–60 s window can easily land entirely inside a compressor run, or entirely outside it, giving a **biased baseline** for a 48-minute session.
- With the Shelly's **30 VA no-load threshold**, the baseline cannot even see the small loads that constitute most of the standing load. Subtracting it removes very little.
- Better: a **robust rolling baseline** (e.g. a low percentile of the preceding hours, or a median over a window much longer than the fridge duty cycle), computed continuously rather than captured once. And record the entire session's context, not a 60-second prologue.

**2.6 There is no data-quality gate, and no verification that anything happened.**
The doc's §5 step 2 says *"Clean and validate. Remove invalid or missing readings."* Nothing in the UI flow implements it, and "remove" silently is the wrong behaviour — gaps must be **quantified and the session rejected** if the gap rate exceeds a threshold.

More importantly, **the app has a sensor and does not use it to check the user's claim.** Two cheap checks are missing:

1. **Did the device actually stream during the window?** At 1 Hz over WiFi/MQTT, dropouts are not an edge case; they are expected. If the poller died, the session is worthless and the user must be told immediately.
2. **Did total power actually step up when the user pressed "I've Started the Machine"?** The system can verify this in real time rather than trusting the button. If no step is detected within a few seconds, that is a failed calibration — say so **while the user is standing there**, not after post-processing. This is the single cheapest quality improvement available and it converts the flow from "trust the user" to "verify the user".

**2.7 The "is the profile valid and reliable?" gate is undefined.**
Figure 1 contains a decision diamond: *"Is the profile valid and reliable?"* with a failure branch (*"Calibration unsuccessful • Data is incomplete or inconsistent"*). The doc admits *"the mathematical form of this representation is not yet fixed."* So the flow contains a gate with no criterion behind it. Everything downstream depends on it, so it needs a **concrete, per-appliance numeric acceptance rule** — e.g. at least N valid sessions, and coefficient of variation of ΔP below some percentage, and the session's measured energy within some tolerance of the appliance's expected energy. Without that, "mark as calibrated" is meaningless.

**2.8 The architecture has no data-ingestion layer.**
Figure 2: *Website → Next.js APIs → Supabase / DB → Python processing → (Calibration → Appliance Profile) | (Detection → Prediction) → Database → Website.*

**The Shelly does not appear anywhere in that diagram.** There is no ingestion service, no poller, no time-series store, and no indication of how 1 Hz samples get from the device into the pipeline. That is the most failure-prone component in the whole system, and it is the one thing that must exist before any of the ML matters.

Two related concerns:
- **Postgres/Supabase is the wrong home for the raw stream.** Two channels at 1 Hz is ~172,800 rows per day per household. Fine for a demo, wrong for a product. Raw samples belong in a time-series store (or flat files/Parquet); Supabase can hold the derived features and profiles.
- **The 1 Hz data is not recoverable if the poller stops.** The device only retains a **1-minute** onboard log for ~10 days. If continuous polling fails for an hour, that hour of detail is gone permanently. The architecture does not acknowledge this at all.

**2.9 Nobody is using the second CT channel.**
The Shelly EM Gen3 has **two channels**. Every document treats it as a single whole-home meter.

**This is the best constructive idea available to them.** The second CT clamp is free continuous ground truth. Options:
- Clamp CT1 on the whole supply and CT2 on the circuit you care about (kitchen ring, EV charger, hot water). Now you have a **permanently labelled reference channel**, and every real appliance event on that circuit becomes a labelled training example automatically — no button-pressing, no user compliance, no 48-minute sessions.
- During calibration, put CT2 on the appliance's own circuit so the system learns the whole-home signature and the isolated signature **simultaneously**. That is a far stronger training signal than a user-declared window, and it lets you measure how much the aggregate signal smears the appliance's own reading.

This also happens to be exactly what the practitioner community recommends instead of disaggregation — per-circuit CT monitoring. **The hardware for it is already owned and unused.**

**2.10 Smaller technical points**
- **ΔCurrent is nearly redundant with ΔPower** at fixed voltage; the doc's own §7 table lists 9.1 A vs 8.8 A for two appliances both at 2100 W, which implies different voltages or power factors for the same nominal load — inconsistent as written.
- **Power factor will be weakly measured** on this device and is unlikely to be a strong discriminator at 1 Hz. Worth testing, not worth designing around.
- **The kettle-vs-heater example exposes a design gap.** If the only discriminator is duration (240 s vs 1800 s), the system cannot answer until the heater has run for many minutes. There is **no notion of a provisional prediction that is revised as the event continues**. Yet the brief's stated goal is "transparent accuracy and confidence" — which for these two appliances means *"50% kettle / 50% heater; will resolve in ~10 minutes"*, not a single label. The design has no mechanism for that, and it is required to be honest.
- **"Keep other major appliances off if possible" is unverifiable user compliance.** The doc's §5 step 5 (*"flag sessions where another appliance causes a significant overlapping change"*) is the right instinct, but the UI relies on the user instead of detecting it. Do the detection, and store a per-session cleanliness confidence.

---

## 3. The "synthesise data with generative AI" claim

**State this plainly: a generative model cannot produce the data this project needs, and it does not need to, because real data is already free.**

**What legitimate synthetic load data is.** Simulating household electricity is a real research technique — but it is done with **physical and statistical models**: Markov chains / FHMM priors over appliance states, additive synthesis from measured appliance waveform libraries, or dedicated tools like Load Profile Generator. These encode the physics: duty cycles, transition dynamics, simultaneity, and the actual noise characteristics of a meter.

**What an LLM produces.** Ask a language model for a CSV of "household power over 48 minutes" and you get numbers that are *plausible-looking* — smooth, well-behaved, with no genuine sensor noise, no realistic transition smear at 1 Hz, no fridge compressor cycling underneath, no WiFi dropout pattern, no measurement quantisation. The aggregate has none of the properties that make disaggregation hard.

**Why this is worse than useless:**
1. **A detector validated on it proves nothing.** You would be testing whether your model can invert a generator you wrote — not whether it can find a 2 kW step inside a real noisy aggregate.
2. **It produces artifacts that look like progress.** This is the actual danger. Charts, a confusion matrix, an F1 score — all meaningless, all presentable. For a project whose status is "not yet started", fabricated data manufactures the appearance of progress.
3. **It is completely unnecessary.** Real, labelled, open data exists and can be put into the exact 1 Hz regime in an afternoon:
   - **UK-DALE** (Nature Sci Data 2015): whole-home **16 kHz** plus lower-rate mains. Downsample to 1 Hz → a real aggregate signal at Shelly's rate.
   - **REFIT** (Nature Sci Data 2017): 20 UK homes, whole-home + 9 appliances at **8 second** intervals. Close enough to downsample to 1 Hz or use directly.
   - **Kaggle "Household Energy Disaggregation (NILM) – 1 Minute"**: CC0, per-appliance ground truth.

   Any of these lets you build and test the entire pipeline against **real physics with real labels, today, for nothing.**

**The question to ask:** *"Which public dataset are you validating against — UK-DALE, REFIT, or something else?"* If the answer is "we're generating our own", that is the finding.

**One legitimate use of synthetic data:** generating *unit-test fixtures* for the pipeline's parsing and storage code. It must never appear in an accuracy claim.

---

## 4. What is genuinely good here

Be fair: the documents are more honest and better-structured than the project's execution so far.

- **The calibration document is honest and well-structured.** It states the hypothesis, separates "current MVP direction" from "still to validate", and explicitly says the modelling method is *"intentionally still open for review."* It does not overclaim.
- **Its nine open questions are the right questions.** Rule-based vs ML first, appliance representation, sample size, UNKNOWN threshold, separating calibration from test, complex appliances — these are exactly what a competent reviewer would want asked.
- **Figure 1's internal flow is sound in structure.** Baseline → on → in use → off → clean → extract → branch simple/complex → build profile → validate → mark calibrated → improve over time. Including an explicit *"calibration unsuccessful, retry"* branch is good design; most teams forget the failure path.
- **The architecture layers are sensible** (Next.js API → DB → Python processing → calibration/detection split). It is only missing the ingestion edge.
- **The feature list is reasonable** and matches the literature: active power, ΔPower, duration, rise/fall behaviour, variability, power factor.
- **Asking before building**, which is exactly the right instinct and the reason this project is salvageable.

The problem is not the plan. The problem is that **nothing has been executed, and the one execution plan stated so far is invalid.**

---

## 5. The one-day experiment that settles it

A review of existing artifacts cannot be performed yet — there are none. What can be done instead needs no ML, no new product code, and no new data: it answers the brief's §5 step 1 and the core hypothesis at the same time.

**Part A — measure the real sampling behaviour (about an hour)**
Poll the Shelly at the fastest rate it will give you (local HTTP RPC / MQTT / WebSocket), log **raw timestamps**, and run for a continuous hour.
- Inter-sample interval: mean, median, and the full distribution.
- Gap distribution: how often does it drop below 1 Hz, for how long, how often?
- Does it hold up over an hour, or degrade?

**This single histogram either confirms or destroys the project's premise**, and it is the first thing the brief asks for.

**Part B — the appliance step test (about an hour)**
With the device already installed:
1. Boil a kettle ~10 times, labelled on/off. (~2 kW step)
2. Run a microwave ~10 times. (~1 kW step)
3. Run a toaster or heater.
4. Run a **small load** (e.g. a 100 W lamp) to demonstrate the **30 VA floor** and the ±5% sub-1 A accuracy band empirically.
5. Deliberately let the fridge and other loads run during some events, to observe how badly overlapping loads corrupt ΔP.

Then compute, per appliance: the ΔP step distribution (mean, standard deviation), whether 1 Hz captures the step or smears it across adjacent intervals, and the pairwise separability (kettle vs microwave vs toaster).

**Deliverable:** a handful of plots (raw 1 Hz series per event, ΔP distributions, the timestamp-gap histogram) and a one-page verdict: **can 1 Hz aggregate power separate these appliances, yes or no, with what margin.**

If yes — the ML is worth building, and they have a real baseline. If no — they have saved months and should reconsider the hardware (a faster meter, or more CT channels, which is what the community and the market both converged on).

**Bonus, and the highest-value thing in this document:** run Part B with **CT2 clamped on the appliance's own circuit**, and compare the isolated signature against what the aggregate shows. That directly measures how much the whole-home signal costs you — and it is the experiment that would tell them whether the second channel is their real product.

---

## 6. Recommendations

1. **State plainly that there is nothing to review yet.** It is a fact, not a criticism.
2. **Generating data with an LLM will not work, and it is unnecessary — UK-DALE and REFIT are real, labelled, free, and can be downsampled to exactly the rate the Shelly produces.** This is the single most useful finding to deliver.
3. **Prove the sensor can do the job in one day before building anything else** — the timestamp histogram and the kettle test (section 5).
4. **Start with the kettle, not the washing machine.** Cheapest calibration, most events, lowest variance, directly tests the core question.
5. **Use the second CT channel** — continuous ground truth is available and unused.
6. **Reconcile the two flow diagrams: they disagree about who marks the event.** Confirm which one is implemented.
7. **Make the app verify the user instead of trusting them** — confirm the device streamed, and confirm power actually stepped, while the user is still there.

---

## 7. Appendix — key quotes from the calibration document

- *"We want to validate the methodology before collecting substantial real-world data."*
- *"The exact modelling method used after feature extraction is intentionally still open for review."*
- *"We have not yet chosen how the score should be calculated or how the UNKNOWN threshold should be defined."*
- *"The mathematical form of this representation is not yet fixed."*
- *"Should complex multi-stage appliances be included in the MVP, or should we first validate the method on simple ON/OFF appliances?"* — **good question; the answer is no, and they should apply it to their own UI.**
- From the journey diagram: *"Recommendation: Run at least 2–3 calibration sessions (with different loads or programs if possible) for best results."*
- From the journey diagram: *"Keep other major appliances off if possible."*

## 8. Correction — the "1 Hz" figure is not a Shelly EM Gen3 specification

**Recorded after this assessment was written.** This corrects a claim made verbally and relied on in sections 2.3, 2.6, 2.8 and 5. The substance of the assessment does not change, but the number does, and it should not be repeated as though it were a datasheet value.

**What was claimed.** That the Shelly EM Gen3 delivers measurements at roughly 1 Hz, and that the whole analysis can assume that rate.

**What the documentation actually contains.**

| Quantity | Value | Source |
|---|---|---|
| Stored measurement log | **1 minute**, at least 10 days | Shelly knowledge base, Shelly EM Gen3 |
| EMData energy-export period | **300 / 900 / 1800 / 3600 s** (5-minute floor) | Shelly API docs, EMData component |
| Live push (StatusChange) | fires "on a regular interval" — **interval not stated** | Shelly API docs, EM component |
| Sampling frequency | **not published anywhere** | — |

The knowledge base states verbatim: *"Measurement data storage: At least 10 days of 1 min data resolution."* The EMData.GetData period parameter accepts only *"300, 900, 1800, or 3600 seconds"*. The EM component's StatusChange is documented as firing *"on a regular interval and an error condition change"* with no value given — and the API's own Notifications page contains no occurrence of "interval", "second", "period" or "regular" at all (verified by direct fetch: 6,236 bytes, zero matches).

**Source of the error.** A Shelly community forum thread (topic 10428, July 2025) in which **Pro 3EM** users report that *"neither scripts nor Modbus gave more than one new value per second."* That is a different device in the same family. The 1 Hz figure was extrapolated across the product line rather than read from an EM Gen3 specification.

**A trap to flag.** The EM component exposes a field called a_freq, documented as *"Phase A network frequency measurement value"*, in Hz. That is **mains frequency (50 or 60 Hz)**, not a sample rate. If a Hertz value read from the RPC output is treated as the sampling frequency, the model will be built on a misreading of a power-quality field. Brief section 5 step 1 asks to *"confirm raw fields and sampling frequency"* — this is the specific confusion that step exists to prevent.

**Consequences.**

1. **1 Hz is now a hypothesis to be measured, not a premise.** Section 5 Part A (the timestamp-gap histogram) is the load-bearing experiment rather than a preliminary. It is the only thing that can establish the rate.
2. **The device cannot store 1 Hz data.** Anything faster than 1 minute requires an always-on external collector, and **gaps are unrecoverable** — the onboard 1-minute log cannot backfill them (see 2.8). This is a **stock-firmware limit, not a sensor limit — see section 10.**
3. **If they fall back to stored data, the case weakens materially.** One-minute averaging smears exactly the step edges that event detection depends on. A 90-second kettle boil lands across two samples at partial amplitude.
4. **Everything else stands.** If the measured rate is genuinely around 1 Hz, the rest of this document applies as written.

---

## 9. Section-by-section read of "Calibration-to-Detection MVP Approach"

**What the document is.** A well-organised statement of hypothesis with no evidence behind any
part of it. It asks for adjudication of decisions that only measurement can settle. The
structure is sound and its section 9 asks the *right* questions — but the document is not ready to
be reviewed as if the answers were in it.

**Headline finding.** The stated MVP scope is **simple ON/OFF appliances**, not complex ones.
This is widely misread, including by the client's own material.

| § | What it says | Assessment |
|---|---|---|
| 1 | Hypothesis: *"household-specific guided calibration can create enough labelled examples to identify a small number of appliances."* Asks whether to change methodology *"before collecting real data"* | **Circular.** A calibration-to-detection method cannot be validated without data. The only pre-data question is feasibility in principle, which the literature already answers |
| 2 | Calibration *"gives the system labelled examples of what a particular appliance looks like electrically in a specific household"* | **The rationale is label generation, not complexity handling.** Consequence: labels are not the bottleneck — *separability* is |
| 3 | Signals: W, VA, V, A, energy. Splits simple (kettle, heater) from complex (washing machine, dishwasher) | **No sample rate appears anywhere in the document.** Every later step depends on it |
| 4 | Figure 1, guided-calibration workflow | Diagram only. *"The exact modelling method... is intentionally still open"* |
| 5 | 7 steps: collect, clean, baseline, **detect ON/OFF transitions and ΔPower**, interference check, features, representation | **Step 4 is event detection.** At 1-minute stored resolution a 90 s kettle boil lands across two samples at partial amplitude. On the device's own log the step may be unimplementable |
| 6 | *"Appliance profile... a product-level concept, not a final modelling decision."* Illustrative profile is a **kettle** | Honestly framed as undecided |
| 7 | Kettle 2,100 W / 9.1 A / PF 0.99 / 240 s vs Heater 2,100 W / 8.8 A / PF 1.00 / 1,800 s | **The only feature that separates them is duration.** Power is identical; current and PF differ by under 5% |
| 8 | Evaluate on unseen events; precision, recall, F1; keep calibration and test sets separate | **Correct and well-designed.** The strongest part of the document |
Nine open questions:
| 10 | Fixed vs open | Complex appliances sit in the *"still to validate / decide"* column |

### Four structural problems

1. **Circular validation (§1).** *"We want to validate the methodology before collecting
   substantial real-world data."* You cannot. What *can* be settled pre-data is whether the
   sensor at this sample rate can separate these appliances at all — and that is answered by
   physics and the published literature, not by adjudication.

2. **The sample rate is never named.** The document lists the signals but not their resolution,
   then builds a pipeline whose step 4 is transition detection. The entire method rests on an
   unstated number. Per section 8 above, that number is not documented for the EM Gen3.

3. **Their own worked example discriminates on duration, not on electrical signature.** Kettle
   and heater are identical in power and within 5% on current and power factor. So the feature
   doing all the work is *how long it ran*. That has three consequences: you must observe the
   whole event before you can classify it; a heater that runs for three minutes on a mild day
   is misclassified as a kettle; and a rule of the form *"did it run for 30 minutes"* needs no
   learned profile at all.

4. **Calibration is justified as label generation, but labels are not the constraint.** Public
   datasets (UK-DALE, REFIT, AMPds, SynD) already supply labelled appliance data. What
   is missing is *separability*, and calibration does not create it. If two appliances
   are not distinguishable at the available resolution, more labelled examples of them do not
   help.

### On scope — the common misreading

The document is explicit, and it points the *opposite* way to what people remember:

> *"**Simple appliances:** Relatively stable ON/OFF behaviour, such as a **kettle or heater**. A
> compact profile based on steady-state and transition features may be sufficient."*
>
> *"**Complex appliances:** Power changes across a cycle, such as a washing machine or
> dishwasher. These may require sequence/operating-pattern analysis..."*
>
> §9: *"Should complex multi-stage appliances be included in the MVP, or should we **first
> validate the method on simple ON/OFF appliances**?"*

So complex appliances are a **question**, not a target. The confusion is understandable: the
original brief's user journey is built entirely on a **washing machine**, while this document
says to start with a kettle. **The two documents contradict each other**, so the first step is to establish
which one is current.

**Worth confirming.** If their real claim is *"calibration lets us handle the appliances a
general algorithm cannot,"* that is a differentiated and testable thesis — and they should say it
out loud, because it changes the risk profile completely. The follow-up is then empirical: the
UK-DALE analysis in this workspace found a washing machine's **median step change is 128 W**,
against a 30 VA device floor and a ±5% accuracy band from 0 to 1 A. The parts of a washing
machine that are visible are its **heater**. The parts that make it complex — motor, valve, small
control steps — sit near or below the noise floor. And a 2 kW element is exactly what §7 already
lists twice, as kettle and heater.

---

## 10. Hardware addendum — the Shelly EM Gen3 can be reflashed for high-rate capture

This section revises the practical conclusion of section 8. The 1-minute storage limit is a
**firmware** limit, not a sensor limit.

### What the device actually is

Verified from the ESPHome device database entry for the Shelly EM Gen3 (page published
2026-01-21), which documents the PCB and pinout:

| Component | Detail |
|---|---|
| SoC | **ESP-Shelly-C38F, ESP32-C3**, single core, 160 MHz, 8 MB flash |
| Metering IC | **ADE7953** at I2C address **0x38** |
| RTC | AiP8563 at 0x51 (not supported by ESPHome) |
| ADE7953 IRQ | **GPIO4** (active low) — exposed |
| ADE7953 RESET | GPIO5 |
| I2C | SCL **GPIO6**, SDA **GPIO7** |
| Other | GPIO0 relay, GPIO1 button, GPIO3 NTC ADC, GPIO9 status LED, GPIO20/21 UART |

The ADE7953 is a proper single-phase metering IC with two current channels, an internal DSP, and
32-bit gain registers. ESPHome supports it natively via the **ade7953_i2c** component, which is a
**PollingComponent** — its update interval is set in YAML. The Shelly example config uses
**update_interval: 20s** purely as a default choice; nothing in the hardware requires it.

**Therefore the achievable sample rate is set by the chip and the I2C bus, not by the stock
firmware.** The stock 1-minute log and roughly 1 Hz live reporting are software behaviour.

### Three options, cheapest first

**Tier 0 — no hardware change (do this today).** Leave the stock firmware alone and poll the
device continuously over local RPC, MQTT, or WebSocket from an always-on collector. The onboard
log stays at 1 minute, but you capture roughly 1 Hz live. That is already **60x finer than the
stored data** and costs nothing but a script and a machine that stays on.

**Tier 1 — reflash with ESPHome (a weekend).** Flash the EM Gen3 with ESPHome using the
documented pinout and set **update_interval** to something like 100 ms. Expect **tens of Hz**.
This also removes the stock 30 VA no-load threshold, which is a firmware gate rather than an
analog limit. Difficulty is rated 2 of 5 in the ESPHome database.

**Tier 2 — purpose-built capture (a real project).** If genuinely high-frequency data is needed,
the Shelly is the wrong starting point. The established route is a current transformer with a
burden resistor and bias network into an ESP32 ADC (roughly 2–8 kHz), or into a sound-card
line-in at 44.1 kHz — which is how UK-DALE's 16 kHz channels were recorded. Public examples
exist, including an ESP32 plus SCT-013 NILM build and the CalPlug ADE7953 breakout (which ships
both I2C and SPI variants), plus the open-source 16-channel EnergyMe-Home meter.

### Caveats — read these before promising anything

1. **You get computed values, not waveforms.** The ADE7953 outputs RMS, active, reactive and
   apparent power, power factor and frequency. Faster polling gives you **high-rate power**, not
   raw AC waveforms, so no V-I trajectories, no harmonics, no transient analysis. That is a real
   ceiling: it fixes the *temporal* resolution problem, not the *spectral* one.
2. **The maximum sustainable rate is empirical and unverified.** I could not confirm the chip's
   register update rate or the practical I2C ceiling from a primary source. **Measure it.** The
   recipe: reflash, set update_interval to 50 ms, log the ESPHome timestamp of each publish, and
   plot the inter-sample gap histogram. Duplicated values reveal the true chip rate; growing gaps
   reveal an I2C or Wi-Fi bottleneck.
3. **Reflashing means giving up the stock product.** No Shelly Cloud, no app, no onboard 10-day
   log, and no factory calibration unless you retrieve it first. The ESPHome page warns for the
   3EM that calibration gains must be read from the stock firmware *before* flashing; the EM Gen3
   page lists example gains for 120 V / 50 A CTs.
4. **The analog objections all survive.** The 30 VA floor, the ±5% accuracy band from 0 to 1 A,
   the 2% band from 2 to 50 A, and the absence of waveform data are unchanged by any of this.
   Faster sampling does not make a small load visible.

### What this changes

The temporal-resolution objection in section 8 largely dissolves at Tier 1, and the "gaps are
unrecoverable" problem is manageable rather than fatal. **The analog objections do not dissolve.**
So the feasible set widens — more room for step detection, better simultaneous-event separation,
and a real shot at the 2–4 large single-state appliances the brief already targets — while the
infeasible set stays infeasible.

### And what it means for the project's framing

This is a **scope change disguised as a hardware tweak**. Tier 1 turns a modelling project into
a firmware project; Tier 2 turns it into an electronics project. Both are legitimate, and Tier 2
in particular would put them back on well-trodden ground with published benchmarks — but it also
means competing directly with the mature NILM literature rather than sidestepping it.

The client said they can *"change or reframe"* the problem. If so, this is the reframe worth
putting to them:

> *"Before we discuss the model, let us settle what the sensor can actually deliver. The stock
> firmware gives you one stored sample a minute. The hardware underneath can almost certainly do
> better, and there are three known routes to it. Which one you choose determines whether this is
> a data problem, a firmware problem, or an electronics problem — and those are three different
> projects with three different scopes."*

---


