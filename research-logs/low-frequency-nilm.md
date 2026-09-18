# Low-frequency NILM: what the field says about 1-minute data

**Question:** the Shelly EM Gen3's finest *stored* resolution is 1 minute. Is that usable for
this project, and what does the research and commercial community do with data at that
granularity?

**Collected:** 2026-09. Sources: OpenAlex literature sweep (5 queries, ~34k works scanned,
top-ranked extracted), Shelly product/API documentation, and a browser sweep of the commercial
landscape.

---

## 1. Headline

**One-minute data is a recognised, well-studied regime — and it is the regime where NILM is
weakest.** The literature is explicit that the *best* low-frequency results come from intervals
**below 10 seconds**, and that at utility granularity (15 to 60 minutes) *"most NILM methods
[are] ineffective."*

One minute sits in an awkward middle: too coarse for the event detection the client wants, not
coarse enough to be the utility's problem. The research that does succeed at this granularity
abandons event detection and answers a different, easier question.

---

## 2. The four granularity regimes

The field implicitly agrees on these bands. What is achievable changes at each boundary.

| Regime | Rate | What it can do | Who uses it |
|---|---|---|---|
| **High frequency** | kHz+ | V-I trajectories, harmonics, transients; near-unique signatures | research, power quality, Bidgely's on-meter edge |
| **Low frequency** | 1 s to 10 s | event detection of large single-state loads; the usable NILM band | UK-DALE, REFIT, Sense-era hardware |
| **Very low frequency** | 1 min to 15 min | category-level attribution, load profiling, HVAC vs base | smart meters, utility analytics |
| **Billing** | 30 min to 1 month | totals, forecasting, tariff selection | utilities, retailers |

**The client's device, at its documented stored resolution, sits in the third row.** At its
(undocumented, to-be-measured) live rate it may reach the second.

---

## 3. What the literature actually says

### 3.1 The best low-frequency results need intervals below 10 seconds

**Review on Deep Neural Networks Applied to Low-Frequency NILM** — Energies 2021, 124 citations,
doi:10.3390/en14092390. This is the canonical review of the subfield; it defines low-frequency
NILM as *"data with sampling rates lower than the AC base frequency"* (i.e. below 50/60 Hz).

Its performance comparison across reported MAE and F1-scores finds the best-performing
approaches share:

> *"data sampling intervals below 10 s, a large field of view, the usage of generative
> adversarial network (GAN) losses, multi-task learning, and post-processing."*

**That is the single most important finding for this project.** The review surveyed the whole
subfield and the winners cluster under 10 seconds. One minute is six times coarser than the
weakest winning interval. The brief's own §5 experiment (kettle, microwave, toaster, heater)
targets the second row, where the field is strongest — which is another reason §5 is the right
experiment and the 1-minute fallback is not.

The review also flags that the field *"highlight[s] the need for comparative studies"* and notes
missing elements — i.e. the literature itself is not settled.

### 3.2 At utility granularity, standard methods stop working

**HVAC load Disaggregation using Low-resolution Smart Meter Data** — IEEE ISGT 2019,
doi:10.1109/isgt.2019.8791578. States the constraint without hedging:

> *"Traditional non-intrusive load monitoring (NILM) methods are effective for load
> disaggregation using high resolution smart meter data collected by power quality meters.
> However, smart meter data collected and stored by utilities are normally 15-, 30- or
> 60-minute in granularity, **making most NILM methods ineffective**."*

**What they do instead is instructive.** Their sequential energy disaggregation algorithm does
*not* detect appliance events. It works in three steps: remove large infrequently-used loads,
estimate a **base energy consumption curve** using a *"mild-day method"* (mild weather days are
assumed to have no HVAC), then subtract. It answers **"how much heating and cooling"**, not
**"which appliance turned on."**

This is the template for what coarse data can honestly deliver: **attribute energy to a category
using physics and baselines, and do not attempt identification.**

### 3.3 Spectral signatures are the main attempt to rescue low-rate NILM

**Residential Appliance Identification Based on Spectral Information of Low Frequency Smart
Meter Measurements** — IEEE Trans. Smart Grid 2015, 105 citations, doi:10.1109/tsg.2015.2484258.

Uses Karhunen-Loève expansion to decompose the active power signal into "subspace components"
as a signature, explicitly contrasting itself with *"existing NILM techniques that rely on
multiple measurements at high sampling rates"*. Validated on tracebase and REDD.

So there is a genuine research line claiming low-rate identification. Note the caveats: it
assumes a known appliance inventory, reduces candidates via "SC level power conditions", then
applies maximum a posteriori estimation over a combination space. It is a **combinatorial
matching method over a closed set of appliances**, which is exactly the shape the client's
guided calibration is groping toward — and it needs the appliance library to be right.

### 3.4 Lumping unknown loads into one bucket is standard practice

**An optimisation-based energy disaggregation algorithm for low frequency smart meter data** —
Energy Informatics 2019, doi:10.1186/s42162-019-0089-8. The algorithm:

> *"assumes that a fraction of the loads present in the household is known (e.g. washing machine,
> dishwasher, etc.), but it also considers unknown loads, **treating them as a single load**."*

Benchmarked against Combinatorial Optimization and FHMM from NILMTK. **The client's "UNKNOWN"
class is not a workaround or a hedge — it is the published state of the art at this granularity.**
That is worth telling them; they may be treating it as an admission of failure.

### 3.5 Evaluation in this field is unsettled

**Performance evaluation in NILM: Datasets, metrics, and tools — A review** — WIREs Data Mining
and Knowledge Discovery 2018, 194 citations, doi:10.1002/widm.1265:

> *"there is still no consensus regarding, which performance metrics should be used to measure
> and report the performance of NILM systems and their underlying algorithms."*

**Consequence for the client:** any accuracy number they report needs an explicitly named metric
and an explicitly named dataset. An F1 score with no metric definition is not a result.

### 3.6 The synthetic-data question, answered by the field

**A synthetic energy dataset for NILM in households (SynD)** — Nature Scientific Data 2020,
124 citations, doi:10.1038/s41597-020-0434-6.

This is what legitimate synthetic NILM data looks like, and it is published in a Nature journal.
It is *"the result of a custom simulation process that relies on power traces of real household
appliances"*, delivering 180 days of aggregate and per-appliance power, with case studies
demonstrating similarity to four real-world datasets.

**The contrast with the client's plan is the whole point.** Legitimate synthesis is
*recombination of measured appliance traces under a physics model*. Asking a language model for
a CSV of household power is neither. The existence of SynD also reinforces the earlier finding:
the data problem is already solved, for free, by UK-DALE, REFIT, AMPds and SynD.

### 3.7 The adjacent questions that DO work at coarse granularity

Low-frequency smart meter data supports a large, healthy research field — it is just not
appliance identification:

- **Activity and occupancy inference.** *Non-Intrusive Load Monitoring and Classification of
  Activities of Daily Living Using Residential Smart Meter Data* — IEEE Trans. Consumer
  Electronics 2019, 154 citations, doi:10.1109/tce.2019.2918922.
- **Category attribution** (HVAC vs base vs always-on) — see 3.2.
- **Load forecasting, tariff optimisation, demand response, baseline estimation** — the bulk of
  the utility analytics literature.
- **Anomaly detection on the meter-level baseline**, which needs no attribution at all. See the
  Applied Energy 2019 result already cited in docs/product/use-case-reassessment.md
  (doi:10.1016/j.apenergy.2019.01.061).

---

## 4. Commercial landscape

**The pattern: consumer-facing NILM has largely failed and utility-facing disaggregation
survives — but the survivor's advantage is a data position a small team cannot copy.**

### Bidgely — the commercial leader, and the most instructive data point

Utility-scale, the main company still selling disaggregation. Their architecture has **two
distinct tiers**. Getting this right matters, because the first version of this section got it
wrong — see the correction at the end of this section.

**Tier 1 — AMI disaggregation (the main product).** From their solution brief:

> *"12 distinct appliance loads detected per home"* ... *"15-minute interval granularity from AMI
> data"* ... *"Trained on ground truth from tens of thousands of homes"* ... *"Built on early
> experience with 5-second high-frequency data"*

and:

> *"We can tell whether an electric heater was running during each 15-minute interval of the day,
> and how much energy it consumed in that interval."*

> *"Bidgely uses meter data to detect the presence and use of 12 different appliance loads in
> homes — at the sample level, not the bill level."*

**Tier 2 — real-time, on-meter (compatible AMI 2.0 meters only).**

> *"For real-time use cases, Bidgely adds on-meter intelligence on compatible AMI 2.0 meters,
> using high-frequency signals available on the meter itself to detect fast events such as EV
> charging within minutes."*

> *"A miniaturized version of our disaggregation application runs directly on the meter —
> analyzing high-frequency signals available only on the meter itself to produce on-off detection
> events. Unlike AMI disaggregation, these real-time events can have a proactive impact on load
> shifting, DR, and EV programs."*

Note Bidgely's own phrase: *"Unlike AMI disaggregation."* They are explicitly describing two
different products.

### What this actually establishes

**It is the strongest existing evidence that NILM works commercially.** Bidgely sells
appliance-level disaggregation — twelve loads, not merely broad categories — from 15-minute
utility meter data. Anyone claiming NILM is only ever a research toy has to answer for Bidgely.

**It also shows what winning requires.** Their two decisive advantages are precisely what the
client does not have:

1. **Ground truth from tens of thousands of homes**, plus 16+ patents. That is the training set
   and the moat. The client has no data and is proposing to synthesise it.
2. **AMI data already sitting in the utility's systems.** No hardware, no installation, no user
   compliance, no calibration ritual. The client needs someone to open a breaker panel and then
   spend 48 minutes labelling one washing-machine cycle.

**The trajectory is instructive too.** Bidgely reports being *"built on early experience with
5-second high-frequency data"* and now sells 15-minute results. They moved from fine to coarse,
because coarse data was already deployed everywhere and they had the labels to compensate. The
client is attempting the reverse: fine-grained ambition, no labels, and a hardware install.

### 4.1 Correction (added after first publication)

The first version of this section claimed Bidgely does *"category attribution at 1-minute
granularity"* and called it *"the ISGT method, commercialised"*. **All three parts of that were
wrong.**

| Claim made | What Bidgely's own material says |
|---|---|
| 1-minute granularity | **15-minute** granularity from AMI data |
| category attribution | **"12 distinct appliance loads"** — appliance-level identification |
| the ISGT method (3.2) | trained ML on AMI data, labelled from tens of thousands of homes. ISGT is baseline subtraction with no training data at all |

The 1-minute figure was invented by analogy to this project's hoped-for rate. The "ISGT method"
label mistook a similarity of output shape for a similarity of method. Neither appears in
Bidgely's material or in the ISGT paper.

**One further precision:** the high-frequency, on-meter processing is **Tier 2**, a separate
product for real-time fast events. It is *not* how the 15-minute appliance identification is
produced. Bidgely's own words — *"Unlike AMI disaggregation"* — separate the two.

### 4.2 What Bidgely's customers actually buy

**The customer is a utility** — the electricity company itself, the entity that owns the
meters and sends the bills — **not a homeowner.** That is the whole answer to why this business
survives where consumer NILM died. From their own material, the intelligence layer is sold into
utility workflows:

- **Customer experience and call centre.** *"A CSR sees which appliances drove a customer's bill
  increase before the customer finishes explaining the problem."* *"A high-bill alert identifies
  whether HVAC, EV charging, water heating, or another major load caused the spike."* This is
  call deflection and self-service.
- **Programs, rates and engagement.** *"A program manager identifies which customers are most
  likely to benefit from efficiency, electrification, TOU, DR, or affordability programs."*
  *"A marketing team targets customers based on actual behavior, not demographic proxies."*
- **Grid planning and operations.** *"A planner identifies where EVs, heat pumps, HVAC, solar,
  storage, and other DERs are already affecting the grid."* *"An operations team sees what load
  is stressing a transformer, feeder, or substation."*
- **Revenue protection.** They also sell *theft detection* — *"flag tampering, bypass, and tariff
  misuse."*

Headline claims: **"Zero Sensors"**, **"100% Built-in"**, **"16+ Patents"**, and **"15%
Reduction in Residential Energy Consumption"**.

**Why the error tolerance is completely different from a consumer product.** A utility does not
need to know which specific appliance you own. It needs a *population-level segmentation* good
enough to target a program. An EV classifier that is right 70% of the time is still enormously
better than "mail everyone." The decision it feeds is *"send this household a heat-pump rebate
offer"* — not *"replace this appliance."* Errors are absorbed by the aggregate.

That is the structural difference. **Consumer NILM needed per-appliance precision that had to
survive one person's scrutiny; utility NILM needs statistical lift over a population.** Same
algorithm class, incomparable error budgets. The 15% consumption reduction is a *population*
outcome produced by targeted programs, not a homeowner reading a disaggregated chart.

### 4.3 Input resolution vs output resolution, and the "5-second" ambiguity

The 15-minute figure and the per-interval appliance breakdown are **not alternatives**. They
describe different ends of the same pipeline:

- **Input:** AMI meter data at 15-minute resolution — one whole-home energy total per interval.
- **Output:** for each 15-minute interval, an attributed breakdown across the 12 loads.

So Bidgely produces **one dictionary per 15-minute interval**, computed from 15-minute-resolution
input. Input fidelity and output resolution are both 15 minutes.

**On *"Built on early experience with 5-second high-frequency data":* the phrase is ambiguous and
cannot be resolved from the marketing copy.** Two readings:

1. **A 5-second sampling interval** — one reading every 5 seconds. Coarse in the NILM
   literature, but 180x finer than the 15-minute data they now use.
2. **5-second windows of a genuinely high-frequency waveform** — e.g. 5 s at 16 kHz.

The first reading is more likely: it sits in a list of *data-scale credentials* alongside "tens
of thousands of homes" and "15 countries," and a continuous 5-second-resolution recording is the
kind of thing a data company would describe as early experience with. Reading 2 would imply
hardware captures the company does not own.

**Either way it does not change the conclusion.** Note also that Bidgely uses *"high frequency"*
loosely — for 5-second data here, and for on-meter signals in Tier 2. The same looseness appears
in the project brief's own §1 "high frequency" claim. **Treat any vendor's frequency adjective as
marketing until a spec sheet gives you a number.**

**One apparent contradiction, resolved.** Section 3.2 reports that at 15–60 minute granularity
*"most NILM methods [are] ineffective."* Bidgely sells 15-minute disaggregation. Both are true,
because they are claims about different methods:

- Traditional community methods (FHMM, combinatorial optimisation) do fail at 15 minutes.
- Bidgely succeeds at 15 minutes by **giving up two things**: fine-grained output (12 coarse
  classes, not appliances or events) and data efficiency (they buy their way out with ground
  truth from tens of thousands of homes and 16+ patents).

Read the 3.2 claim correctly: 15-minute disaggregation is ineffective *with standard methods and
no labelled training data*. Bidgely is the exception that proves it — and it pays for the
exception with the one resource the client does not have.

### The rest of the field

| Company | Approach | Status / note |
|---|---|---|
| **Bidgely** | utility-scale disaggregation from meter data + on-meter edge | active; the reference case |
| **Sense** | on-device edge NILM on a consumer CT | exited direct-to-consumer hardware Nov 2025; pivoted to embedding in meters |
| **Verv** (UK) | high-frequency NILM | listed as **deadpooled**; site now targets commercial BMS energy monitoring |
| **Kimbal** | NILM with a plug-in device + app | active; appliance-level claims |
| **Smappee, Emporia, Curb, Neurio (Generac), IoTaWatt** | **per-circuit CT hardware**, not inference | the mainstream consumer answer |
| **Hilo (Hydro-Québec), Utilidata, Onzo/Navetas** | utility analytics and demand-side programmes | adjacent, mostly not appliance-level NILM |

**The consistent story across a decade and three continents:** companies that tried to sell
consumers *inferred* appliance data have exited, pivoted, or been deadpooled. Companies that sell
measured data (CT hardware) or utility-scale analytics continue.

---

## 5. What this means for WattWiser

1. **1-minute data is not a fallback — it is a different product.** At 1 minute, event-based
   appliance identification is out of the question, and the honest deliverable becomes category
   attribution and baseline profiling. If the client's live rate turns out to be ~1 Hz, they are
   in the good band; if they end up on stored data, they are in the weak one. Measuring the rate
   (assessment section 6 Part A) decides which company they are.

2. **The field's own winners use sub-10-second intervals.** This is a direct, citable answer to
   "is 1 Hz enough?" — 1 Hz (1 s) is comfortably inside the winning band; 1 minute is not.

3. **The "UNKNOWN" bucket is state of the art, not a compromise.** Published low-frequency
   disaggregation explicitly lumps unknown loads as a single load. They should stop treating it
   as a hedge.

4. **The commercial leader sells interval-level category presence and on-meter event detection.**
   That is the shape of a business that works. A consumer clamp with cloud inference is not on
   that list.

5. **Category attribution remains the available fallback — but not because Bidgely does it.**
   "How much of your bill is heating, how much is always-on, how much is the rest" is answerable
   at coarse granularity with baseline methods (the ISGT approach in 3.2), needs no calibration
   ritual, and needs no appliance inference. That is a more honest project at 1-minute resolution
   than appliance identification. **Bidgely does not validate this route** — they do
   appliance-level identification at 15 minutes with utility data (see 4.1). The fallback rests
   on the physics in 3.2, not on the commercial leader's example.

---

## 6. Sources

**Literature** (all verified via OpenAlex, titles and abstracts read directly):

- Energies 2021, doi:10.3390/en14092390 — *Review on Deep Neural Networks Applied to Low-Frequency NILM* (124 cites)
- IEEE ISGT 2019, doi:10.1109/isgt.2019.8791578 — *HVAC load Disaggregation using Low-resolution Smart Meter Data*
- Applied Energy 2020, doi:10.1016/j.apenergy.2020.114949 — *Non-intrusive load disaggregation solutions for very low-rate smart meter data*
- WIREs DMKD 2018, doi:10.1002/widm.1265 — *Performance evaluation in NILM: Datasets, metrics, and tools* (194 cites)
- IEEE TSG 2015, doi:10.1109/tsg.2015.2484258 — *Residential Appliance Identification Based on Spectral Information of Low Frequency Smart Meter Measurements* (105 cites)
- Energy Informatics 2019, doi:10.1186/s42162-019-0089-8 — *An optimisation-based energy disaggregation algorithm for low frequency smart meter data*
- Sci Data 2020, doi:10.1038/s41597-020-0434-6 — *A synthetic energy dataset for NILM in households (SynD)* (124 cites)
- IEEE TCE 2019, doi:10.1109/tce.2019.2918922 — *NILM and Classification of Activities of Daily Living Using Residential Smart Meter Data* (154 cites)
- Applied Energy 2019, doi:10.1016/j.apenergy.2019.01.061 — anomaly detection on NILM vs submetered data

**Documentation:** Shelly knowledge base (Shelly EM Gen3 spec, storage, accuracy, 30 VA no-load
threshold); Shelly API docs (EM and EMData components, Notifications page).

**Commercial:** bidgely.com/disaggregation; Sense; Verv (Tracxn deadpool listing); Kimbal.

**Limits:** commercial status verified via search snippets and company sites, not audited
financials. Two literature items (Applied Energy 2020, Applied Energy 2019) returned no abstract
from OpenAlex and are cited on title and prior reading only. Search was English-language.
