# Use-case reassessment — is "what is on right now" the right problem?

Triggered by the observation that disaggregation ("from a total-watts time series, say which appliance is running") is a toy problem, and that the real value is more likely in **anomaly detection** (a device degrades, its consumption drifts up) or in **benchmarking** (tell a buyer what a device actually consumes before they buy it).

This document tests those three ideas against the literature and against what this sensor can physically measure.

---

## 1. The instinct is correct, and the field agrees

"Reporting what we used each day does not mean much if all of it is essential and cannot be reduced" is not a lay objection. It is the central unresolved critique of the whole residential-feedback industry, and the evidence supports it strongly.

**What feedback actually saves** (much less than the folklore):

| Source | Estimate |
|---|---|
| Folklore / vendor claims | "up to 20%" |
| Older reviews | 6.4 - 7.4% |
| **2020 meta-analysis** — 52 studies, 128 observations, **713,002 households** | **1.9 - 3.9%** |
| Houde et al. 2013, field experiment | 5.7% average, significant only for **up to four weeks** |

The meta-analysis (Ecol. Econ. 2020, DOI 10.1016/j.ecolecon.2020.106635) is explicit about why the older numbers were inflated: *"an absence of a control group, of socio-demographic data, and the self-selection of participants into treatment leads to overestimation of effects."* It also finds that cost feedback and generic saving tips cause **relative increases** in consumption; only individual, real-time and personalised advice help.

So a product whose value proposition is "we will show you your consumption and you will save" is competing for roughly **2 to 4 percent**, and the effect decays within a month.

That is a serious problem for the brief. It is not a problem for the underlying idea of measuring — it is a problem for feedback **as the product**.

---

## 2. But anomaly detection is not an escape — it is strictly harder

This is the important correction. Two papers asked this exact question and both answered no.

**Paper 1** — "Can non-intrusive load monitoring be used for identifying an appliance's anomalous behaviour?", Applied Energy 2019, DOI 10.1016/j.apenergy.2019.01.061, ~106 citations.
They took an anomaly detector that **works well on submetered data**, then ran it on NILM-reconstructed traces instead, across six homes and four state-of-the-art NILM algorithms:

> "on average, NILM traces are not as robust to identification of faulty behaviour as compared to using submetered data"

**Paper 2** — "Evaluation of Non-intrusive Load Monitoring Algorithms for Appliance-level Anomaly Detection", ICASSP 2019, DOI 10.1109/icassp.2019.8683792. Used the two-year REFIT dataset, both aggregate and submetered:

> "We explain why anomaly detection performs worse with NILM data as compared to submetered data, highlighting the need for new, anomaly-aware NILM approaches."

### Why it must be harder — the structural argument

To conclude "this fridge is degrading" from an aggregate meter you must:

1. **Identify** the fridge within the aggregate — that is disaggregation, in full.
2. **Characterise** its normal consumption — which requires step 1 to keep working across months, across duty cycles (median compressor run in the real UK-DALE slice measured here was **1,191 s**, and 74% of cycles exceed one minute), across ambient temperature, and across every other load in the house changing underneath it.
3. **Detect drift** — and the drift you care about is usually small. The fridge's typical transition in that same slice was **107 W median**, inside the band where a Shelly-class meter is only +/-5% accurate. A degrading compressor drawing 15% more is a shift of about 15 W, near the noise floor of the instrument.

Anomaly detection does not replace disaggregation. It **consumes** disaggregation and then imposes a stricter success criterion on it. If "which appliance is on" is unsolved, "which appliance is quietly failing" is further away, not closer.

### The one genuine exception

**Meter-level anomalies that need no attribution.** The ICASSP paper states the tradeoff plainly: meter-level detection "does not identify the anomaly-causing appliance", but it is easy and it does catch things. Specifically:

- **Baseline / always-on creep.** Everything permanently drawing power, tracked as a single number over weeks. A stuck pump, a failing always-on device, a freezer running continuously. Genuinely useful, genuinely detectable, and it requires nothing more than a minimum over a window — no machine learning, no disaggregation, no appliance identity.
- **Whole-home shape anomalies**: a load that never turns off, a duty cycle that shortens, an overnight floor that rises.

This deserves serious weight because it is the **only** high-value analysis on this list that the sensor is unambiguously good at. But note what it delivers: it tells you **something is wrong**, not **what**.

---

## 3. The benchmarking idea is stronger — precisely because it needs less

"Collect actual consumption per device/brand and guide buyers toward real-world consumption" is the most promising of the three, for a reason that is easy to miss.

### The information problem is already solved, for free

Per-appliance consumption for a **new** appliance is published and authoritative: EU energy labels, US ENERGY STAR, manufacturer spec sheets, mandatory test standards. A database of "what a 2024 fridge uses" does not need to be crowdsourced. It is a lookup.

### What the sensor uniquely adds

**The actual consumption of your actual, existing, in-situ appliance, under real conditions.** That is the one number no label provides — labels tell you what the **replacement** would use, not what your fourteen-year-old unit is using now. And nameplate ratings on old appliances substantially understate real draw (aged compressors, dirty condenser coils, degraded insulation).

Put those together and you have a genuine, decision-shaped product:

> Your fridge actually consumes X kWh/year. A current replacement consumes Y. At your tariff, replacing it pays back in Z years.

That is a decision a person can act on, and it needs no continuous classification of anything.

### The reframe that matters

That product needs **one controlled measurement per appliance**, not continuous monitoring. Which means it needs no disaggregation, no 1 Hz streaming, and none of the always-on ML pipeline.

**It is what the client's calibration flow already does.** The 13-step journey — select appliance, enter details, baseline, turn it on, wait, confirm — is *mismatched* for a "passively know what is on" product and *well matched* for a "measure this one appliance's real consumption, once" product.

Their design is not badly built. It is aimed at the wrong goal. Moving the goal to match the design is far cheaper than rebuilding the design to chase disaggregation.

### The supply-chain problem with the crowdsourced version

If the per-device consumption database is populated by **their own sensors**, it inherits every accuracy problem in this document — a database built from unreliable measurements is worse than none, because it launders error into apparent authority. If it is populated from **published labels**, it is free and already exists. Either way, the sensor is not the data source.

---

## 4. The test to apply to every new idea

**"What does the user do differently after seeing this?"**

| Idea | What the user does | Verdict |
|---|---|---|
| Which appliance is on right now | Nothing | Fails |
| Your annual consumption, charted | Nothing (maybe 2-4% for a month) | Fails |
| Something in your home is misbehaving | Investigate | Partial — no ML, no attribution |
| Your fridge is failing, service it | Repair before food spoils | Passes — but needs appliance-level detection, the hardest item here |
| Your fridge costs X, replacement pays back in Z years | Replace it | Passes — and it is the **easiest** to build |
| Your always-on load is W watts, costing N per year | Unplug things | Passes — and it is a **minimum over a window** |

Notice the shape of that table. The ideas that pass split cleanly into **hardest** and **easiest**, and the one the brief is built around is neither. Disaggregation sits in the middle: hard to build, and the user does nothing with the answer.

---

## 5. Ranking the three options for this sensor and this team

**Best fit — "measure once, compare, decide".**
Inventory the appliances, take one controlled measurement of each, compare against published consumption for a modern replacement, output a payback number. Uses the existing calibration UX as designed. No disaggregation, no continuous classification, no streaming. Produces a decision. The technical content is real but modest, and the hard part is measurement hygiene rather than machine learning.

**Second — baseline and always-on analysis.**
Track the minimum load over each day, week and month; flag creep; price the waste. This is the highest-value-per-line-of-code item in the entire project, and it is a minimum over a window. It requires nothing else in their pipeline.

**Worst — continuous disaggregation, and appliance-level anomaly detection built on top of it.**
Hardest to build, and the literature says the second layer does not work well even where the first does.

---

## 6. The tension to be honest about

This is a pivot **away from the brief's technical premise**. The brief's section 1 claims high-frequency sampling, and section 7 describes a hardware-agnostic disaggregation layer validating "data frequency, continuity and measurement quality". That is the expensive, unsolved, research-grade part.

The valuable product needs **less** AI than the brief promises. For an engagement framed as an AI Engineer role, that is an awkward finding — the thing worth building is not the thing that justifies the job title.

That is not a reason to stay silent. It is a reason to put it in the Stage 0 written deliverable and let them decide, because a project that pivots toward a real product ships more than one that builds the impressive-sounding thing and stops. It should be framed as an opportunity: their calibration design already suits the stronger use case.

### The question to put to them

> If the system told a household "your fridge is costing you this much, and a replacement pays back in this many years" — backed by a real measurement — would that be a product you would ship? Because that is a much smaller build than a general disaggregation engine, and it is the one your calibration flow already appears to be designed for.

---

## 7. Where this leaves the earlier analysis

Nothing in the dataset walkthrough changes. The downsampling ladder, the visibility limits, the simultaneity measurements all still apply, and they apply to whichever use case is chosen. But note which parts stop mattering:

- If they pursue **"measure once, compare, decide"**, the simultaneity problem largely disappears (one appliance is measured at a time, on purpose), the 1 Hz question softens (a controlled measurement can take its time), and the difficulty collapses into accuracy alone.
- If they pursue **anomaly detection**, every constraint bites harder, because now the fridge must be identified **and** tracked for months.
- If they pursue **feedback**, the physics barely matters, because the ceiling on the outcome is 2-4% regardless of how good the sensor is.

That last line is the one worth sitting with. For a feedback product, **the sensor is not the bottleneck — the behavioural response is.** No improvement in disaggregation accuracy moves that number much.
