# NILM datasets — what they contain and how to use them

Companion to `research-brief.md` and `feasibility-verdicts.md`.
Purpose: answer "what are UK-DALE / PLAID / WHITED, what shape is the data, and how do I use them to prove or kill the WattWiser premise?"

---

## 0. Bottom line

| Dataset | Sample rate | What it measures | The one job it does for you |
|---|---|---|---|
| **UK-DALE** | **16 kHz** (V + I), 1 s and 6 s (power) | Whole-home **plus** per-appliance, same house, same clock | **The only one of the three that can evaluate disaggregation.** Aggregate + ground truth. |
| **PLAID** | **30 kHz** (V + I) | Single appliances, **plus 575 controlled 2-4 appliance mixtures** | Appliance signature library, and a controlled simultaneity testbed |
| **WHITED** | **44.1 kHz** (V + I) | Single appliances, first 5 s of startup | Transient / inrush shape library |

Three sentences that matter more than the rest of this document:

1. **PLAID and WHITED are not aggregate datasets.** They are single-appliance recordings. You cannot run a disaggregation experiment on them directly. They give you *signatures*, not *mixtures* — with the one exception of PLAID's aggregated set.
2. **UK-DALE is the workhorse.** It is the only free dataset with a real whole-home aggregate, per-appliance labels, and a 16 kHz waveform, all synchronised.
3. **All three are free and downloadable today.** No hardware, no client, no permission needed. You can answer the brief's section 5 step 1 before anyone buys anything.

---

## 1. UK-DALE

**Full name:** UK Domestic Appliance-Level Electricity
**Paper:** Kelly & Knottenbelt, *Scientific Data* 2:150007 (2015), DOI 10.1038/sdata.2015.7
**Licence:** CC BY 4.0
**Homes:** 5, southern England (London), Nov 2012 - Apr 2017. House 1 has 4.3 years.
**Host:** UKERC Energy Data Centre (CEDA), DOIs 10.5286/UKERC.EDC.000001..000004

### What it actually contains — four parallel streams

| Stream | Homes | Rate | Format |
|---|---|---|---|
| Whole-home **voltage + current** | 1, 2, 5 | **16 kHz** | stereo FLAC, ~200 MB per file |
| Whole-home **active + apparent power** | 1, 2, 5 | **1 s** | CSV, col 1 = UNIX timestamp |
| Whole-home **power** | all 5 | **6 s** | CSV, col 1 = UNIX timestamp |
| Per-appliance **power** | all 5 | **6 s** | CSV, one file per appliance channel + `labels.dat` |

House 1 has around 53 appliance channels (fridge, kettle, washing machine, dishwasher, microwave, TV, lights, etc.).

### Input shape

**16 kHz stream.** Each FLAC file is stereo: **left/right = whole-house voltage and whole-house current**, sampled at 16,000 Hz, 24-bit. For an `n`-second file you have two arrays of length `16000 * n`. It is *not* power — you must compute it.

The dataset ships a `calibration.cfg` per house with `volts_per_adc_step` and `amps_per_adc_step`. Conversion:

```
volts = volts_per_adc_step * number_of_ADC_steps * wav_value
amps  = amps_per_adc_step  * number_of_ADC_steps * wav_value
# number_of_ADC_steps = 2**31 for houses 1 and 2, 2**15 for house 5
# then, instantaneous real power:
P(t) = volts(t) * amps(t)
# and to get what a meter would report, average over a window:
P_1Hz[k] = mean( P(t) for t in second k )
```

That last line is the whole trick — see section 6.

**1 s and 6 s streams.** Two columns, no header, whitespace/comma separated:

```
1404059030 256
1404059036 254
```

Shape `(N, 2)` as `timestamp, power`. The 1 s channel carries both active and apparent power (so three columns in places).

**Per-appliance channels.** `channel_1.dat`, `channel_2.dat`, ... plus `labels.dat` mapping channel number to appliance name:

```
1 custom_aggregate
2 fridge
3 dish_washer
4 kettle
5 washing_machine
6 monitor
```

**Scale warning.** The complete April 2017 16 kHz set is **7.6 TB**. One uncompressed day is 8.3 GB (about 4.8 GB as FLAC). Do not try to download it all. Take one house, one week.

### Why it is the workhorse

It is the only free dataset where the aggregate and the individual appliances are recorded **in the same house at the same time on the same clock**. Without that you cannot compute an accuracy score, because you have nothing to score against.

---

## 2. PLAID

**Full name:** Plug-Load Appliance Identification Dataset
**Papers:** Gao et al. (BuildSys 2014); Medico et al., *Scientific Data* (2020), PMC7015894
**Collected:** Pittsburgh, Pennsylvania, USA — houses plus the CMU lab. Summer 2013 and winter 2014, extended 2017-2019.
**Sample rate:** 30 kHz
**Version used below:** PLAID 2018, Figshare DOI 10.6084/m9.figshare.10084619

### What it contains

| Archive | Size | Records | Contents |
|---|---|---|---|
| `submetered.zip` | 708 MB | **1,876** | One appliance at a time. 16 types. Houses 1-9 + CMU lab. ~2 s each. |
| `aggregated.zip` | 1.86 GB | **575** | **2-4 appliances switched on in sequence, then off in sequence.** 13 types. CMU lab only. 10 s each. |
| `plaid_hdf5.zip` | 3.0 GB | — | NILMTK-ready HDF5 |
| `metadata_submetered.json` | 787 KB | — | Labels for the above |
| `metadata_aggregated.json` | 393 KB | — | Labels for the above |

PLAID 2014 (Figshare id 11605074) is a single 274 MB zip with 1,074 instances across 11 types and 230 appliances.

### Input shape — confirmed from the official parser

Each measurement is one CSV. Two columns, **no header, current first then voltage**:

```
# instance 137.csv, 10 s at 30 kHz
0.0141, 168.22
0.0143, 170.05
...            # 300,000 rows
```

Shape `(300000, 2)` float — `current, voltage`. (Submetered files are ~2 s, so `(60000, 2)`.)

The official loader is literally:

```
np.genfromtxt(path + str(instance_id) + '.csv', delimiter=',',
              names='current,voltage', dtype=(float, float))
```

### Metadata schema — confirmed by reading the shipped JSON

Submetered (one appliance):

```
"1": {
  "appliance": {
    "brand": "", "current": "", "voltage": "", "wattage": "",
    "manufacture_year": "", "model_number": "", "notes": "",
    "load": "NL",            # R = resistive, I = inductive, NL = non-linear
    "status": "off-on",      # the transition captured
    "type": "Compact Fluorescent Lamp"
  },
  "header": {"collection_time": "July, 2013", "sampling_frequency": "30000Hz", "notes": "..."},
  "instances": {"length": "2.00s"},
  "location": "house1"
}
```

Aggregated (multiple appliances) — note the `on` / `off` **sample indices**:

```
"1": {
  "appliances": [
    {"type": "Fan",    "load": "I", "on": "[37043]",  "off": "[204316]", "brand": "Lasko cyclone"},
    {"type": "Vacuum", "load": "I", "on": "[89785]",  "off": "[169374]", "brand": "Dirt Devil"}
  ],
  "header": {"sampling_frequency": "30000Hz", "collection_time": "August, 2017"},
  "instances": {"length": "10.00s", "status": "on-on-off-off"},
  "location": "CMU lab"
}
```

That `on` / `off` field is the most useful label in the whole set: it is a **ground-truth transition timestamp to the sample**, at 30 kHz. Sample 37043 at 30 kHz = 1.235 s into the recording.

The `load` field is also free value: **R / I / NL** is exactly the physical distinction that determines whether a switch-on produces a clean step (R gives a clean step; I and NL do not).

### The aggregated set is the interesting one

575 records where 2, 3 or 4 appliances run at once. The `status` field encodes the switching order: `on-on-off-off` (361 records), `on-on-on-off-off` (82), up to `on-on-on-on-on-off-off-off-off` (20).

**Important caveat:** the appliances are switched on **one at a time, staggered**, not truly simultaneously. They were staged that way *precisely so they could be labelled.* The onset gaps are what I measured in section 5 — and the fact that they had to be staggered is itself the finding.

---

## 3. WHITED

**Full name:** Worldwide Household and Industry Transient Energy Dataset
**Paper:** Kahl, Ul Haq, Kriechbaumer, Jacobsen (2017)
**Host:** TUM, cs.cit.tum.de/dis/resources/whited — password-protected zip
**Collected:** 2015-2016, multiple regions worldwide
**Sample rate:** 44.1 kHz
**Contents:** ~1,368 measurements, on the order of 100+ appliance and machine types, household and industrial

### Input shape

Each measurement is a folder containing the first **5 seconds** of an appliance's start-up. Inside: instantaneous **voltage** and **current** arrays (CSV / MAT / DAT depending on region), so `(220500, 2)` at 44.1 kHz for a 5 s record, plus metadata.

It is organised region -> measurement -> signal type.

### What it is for

**Transients only.** 44.1 kHz is high enough to see the inrush of a motor and the harmonic content of a switching supply. It is the best of the three for studying *shape*. It has no aggregate data at all and no long-duration data — 5 seconds does not even contain a full operating cycle for most appliances.

Use it if you want to prove the point that "the signature that distinguishes a motor from a heater lives in the first 200 milliseconds, and the Shelly's 1-second average destroys it."

---

## 4. Also worth having

| Dataset | Rate | Note |
|---|---|---|
| **REFIT** | 8 s | 20 UK houses, 2 years, whole-home + 9 appliances. Nature Sci Data 2016. Bigger and more modern than UK-DALE for low-rate work. |
| **AMPds** | 1 min | Canadian house, 2 years, 19 circuits. |
| **REDD** | 1 s / 3 s (15 kHz for some) | 6 US houses. |
| **Pecan Street** | 1 min / 1 s | Large US cohort; application required. |
| **Kaggle "NILM - 1 Minute"** | 1 min | CC0, 449 KB. **Caution: almost certainly synthetic.** See section 5.5. |

**Tooling:** NILMTK is the standard Python toolkit and has converters for UK-DALE, REFIT, REDD, AMPds, iAWE and more. It is ageing and can fight with modern numpy; for UK-DALE specifically the `.dat` format is trivial enough that a 20-line parser is often less trouble.

---

## 5. Measurements already made (so you do not have to take this on faith)

Everything in this section was computed from the real files, not recalled.

### 5.1 PLAID 2018 aggregated — how far apart are switch-ons?

Across the 575 multi-appliance records (728 consecutive onset gaps, 727 off gaps):

| | median | p10 | gaps under 1 s | gaps under 2 s |
|---|---|---|---|---|
| **Switch-ON gaps** | 2.22 s | 1.43 s | **5.5%** | 38.7% |
| **Switch-OFF gaps** | 1.65 s | 1.15 s | **5.0%** | **74.1%** |

Read that table twice.

- About **1 in 20 switch-ons** happens less than a second after the previous one. At 1 Hz those two events are one event. Not "hard to separate" — **one sample with one number in it.**
- **74% of switch-offs** occur within 2 seconds of another switch-off. The *end* of overlapping operation is much messier than the start.
- And these are **hand-staged lab recordings** where a human deliberately spaced the switching out so the experiment would be labelable. Real households have no such courtesy. This is a **best case for separability**, and it still collides routinely.

Bucketed onset gaps: under 1 s: 40, 1-3 s: 513, 3-5 s: 128, 5 s or more: 47.

### 5.2 A real UK-DALE house slice — how often are appliances on at once?

A 75-day slice of UK-DALE (29 Jun - 12 Sep 2014), 1,048,573 samples at 6 s, five monitored loads: fridge, dishwasher, kettle, washing machine, "monitor" (a device that is on 80% of the time). Provenance corrected 2026-09-21: the signals are house-5 channels (fridge_freezer, dishwasher, kettle, and i7_desktop for the "monitor"; the washing-machine channel matches nothing verbatim), relabeled house_1-style - see the section 8 caveat.

**Simultaneous operation:**

| How many of the monitored appliances are ON | Share of time |
|---|---|
| 0 | 12.30% |
| 1 | 55.74% |
| **2** | **30.80%** |
| 3 | 1.16% |
| 4 | 0.00% |

**32.0% of the time, two or more appliances are running simultaneously.**

**When the kettle runs, at least one other monitored appliance is also on 93.6% of the time.**

That last number is the direct answer to "can we detect multiple devices currently running". The kettle — the single easiest appliance in the house, the one the brief nominates as the starting point — is *almost never alone*.

**Transition collisions (ground truth):**

| Window | 1 appliance switching | 2 switching | 3 switching |
|---|---|---|---|
| Same 6 s sample | 99.8% | 0.2% | — |
| Within 12 s | 87.1% | **12.8%** | 0.1% |

Exact simultaneity is rare; **near**-simultaneity is not.

### 5.3 The step sizes — and what the Shelly can see

Per-transition magnitude, measured on each appliance's own channel:

| Appliance | p10 | median | p90 |
|---|---|---|---|
| **kettle** | 685 W | **2,887 W** | 2,952 W |
| **washing_machine** | 44 W | **128 W** | 224 W |
| **fridge** | 16 W | **107 W** | 135 W |
| **dish_washer** | 46 W | **57 W** | 103 W |
| monitor | 60 W | 71 W | 128 W |

Now overlay a Shelly-class meter: **30 VA no-load floor**, accuracy **+/-5% below 1 A** (about 230 W at 230 V), +/-2% above.

| Appliance | invisible (under 30 VA) | visible but +/-5% (30-230 W) | accurate (over 230 W) |
|---|---|---|---|
| kettle | 1.0% | 2.6% | **96.4%** |
| fridge | **27.6%** | 68.0% | 4.4% |
| dish_washer | 1.1% | 96.0% | 2.9% |
| washing_machine | 6.8% | 83.7% | 9.4% |

This is the feasibility verdict, measured rather than asserted:

- **The kettle is trivially separable.** A 2,900 W step nobody will confuse with anything.
- **Everything else lives in the band where the meter is only +/-5% accurate, or below its floor entirely.** The fridge, dishwasher and washing machine all produce steps of roughly 50-220 W — overlapping each other almost completely, and sitting exactly where measurement error is largest.

You cannot tell a fridge step from a washing-machine step from a dishwasher step by magnitude. They are the same size.

### 5.4 Fridge duty cycle — the baseline window is unsound

Fridge compressor ON-durations over the same 75 days (n = 2,366 cycles):

- median **1,191 s (about 20 minutes)**
- p10 = 6 s, p90 = 1,556 s (26 min), max = 9,883 s (2.7 hours)
- **74% of cycles are longer than 60 seconds**

Their UI records a **30-60 second baseline** before calibration. That window is shorter than three-quarters of the fridge cycles it is trying to average out, so whichever side of the cycle it lands on biases everything downstream. (Also: at 30 VA, the meter cannot see most of the standing load it is trying to characterise anyway.)

### 5.5 Provenance warning on the Kaggle 1-minute set

`adityarajeshwarkarn/household-energy-disaggregation-nilm-1min` — CC0, 449 KB, 40,320 rows.

- Timestamps start **2024-06-01**, but the household column names are fridge_w, ac_w, washer_w, tv_w, lights_w, base_w.
- `total_w` minus the sum of the component columns = mean 0.05 W, std 5.99 W — i.e. the "total" is the sum plus a small random perturbation.
- Only **253 distinct fridge values across 40,320 minutes** — heavily quantised.

**Verdict: it looks simulated, not measured.** It is the exact kind of file that gets reached for when a real one is hard to find, and the exact kind of file that must never appear in an accuracy claim. Use UK-DALE or REFIT instead.

---

## 6. The experiment: the downsampling ladder

This is the central move, and it needs no hardware and no client.

**Claim to test:** "a Shelly-class meter at roughly 1 Hz can learn and then recognise a small number of important household appliances."

**Method:**

1. Download UK-DALE **house 1**, the **16 kHz** stream, for one or two weeks. (Free, CC BY.)
2. Convert FLAC to volts and amps using that house's `calibration.cfg`.
3. Compute `P(t) = V(t) * I(t)` at 16 kHz. This is ground truth at the highest resolution available.
4. **Downsample the same signal down a ladder**: 16 kHz -> 1 Hz -> 6 s -> 1 min. The 1 Hz rung is, to first order, what the Shelly delivers.
5. Load the **6 s per-appliance** channels as labels.
6. Run **one fixed, deliberately simple event detector** on every rung. Same detector, same parameters — only the sample rate changes.
7. Score each rung against the labels: precision, recall, F1, and the error in the estimated step magnitude dP.

**Output: an accuracy-vs-sample-rate curve.**

That single curve answers brief section 5 step 1, and it does it before anyone buys anything, installs anything, or asks a household to cooperate. It also tells you the *ceiling*: if the detector already struggles with the 16 kHz rung, no amount of feature engineering at 1 Hz will recover it, and the project's premise is dead. If 1 Hz retains most of the 16 kHz performance, the premise survives and now has evidence behind it.

### Four tests, in order of cost

**(a) The ladder** — as above. This is the main event.

**(b) The collision test.** Using the 16 kHz aggregate plus the 6 s labels, find every window where 2+ appliances are on and measure how often their transitions fall within one sample of each other. My PLAID measurement says expect roughly **1 in 20 onsets to collide** and about **1 in 4 switch-offs to be within 2 s**.

**(c) The visibility test.** For each appliance compute the dP distribution and overlay the meter's real limits (30 VA floor, +/-5% below 1 A). Section 5.3 is a worked example; repeat it for the appliances the client actually cares about.

**(d) The ceiling test.** Train and evaluate on PLAID's clean single-appliance data at 30 kHz, with perfect labels, and find the best achievable F1 across its 11 types. That is the field's upper bound on the easy version of the problem. Whatever number comes out, 1 Hz with 150x less information cannot beat it.

### Optional fifth: the separability map

Using PLAID's aggregated set (exact ground-truth transition indices at 30 kHz), inject each mixture into a 1 Hz pipeline and measure whether the components are recoverable, as a function of two axes:

- **x-axis:** gap between onsets (0.2 s to 10 s)
- **y-axis:** ratio of the two step magnitudes

The result is a 2-D map of *where disaggregation works and where it does not*. That is a compelling artifact to put in front of a client — it turns "it's hard" into "here is the boundary, and here is which side your appliances are on."

---

## 7. What these datasets can and cannot prove

**They can prove:**

- whether the *method* works at a given sample rate
- the achievable ceiling, at 16-44 kHz with perfect labels
- which appliances are separable by magnitude and which are not
- how often real households present simultaneous loads
- roughly what accuracy to expect, with a defensible number attached

**They cannot prove:**

- that it works in **their** deployment. Different country (230 V / 50 Hz vs the US 120 V sets), different appliance mix, different wiring, different meter, and the Shelly specifically.

That residual gap is real but small, and a single day with the actual device closes it. The point is that **you arrive at that day already knowing what you expect to see**, instead of discovering it live.

**The line to give the client:**

> I can tell you today, for free, using real measured data from five UK homes, whether this sensor class can do what the brief asks. Then one day with your Shelly tells us whether your specific hardware agrees. That is a week of work, not a research programme.

---

## 8. Files and artifacts from this investigation

Under `research-logs/`:

| Path | What it is |
|---|---|
| `sakunrasilka_nilm-test2/` | UK-DALE **house-5** channels relabeled house_1-style: 6 channels, 75 days, 6 s resolution, plus `labels.dat` (provenance corrected 2026-09-21 - see the caveat below) |
| `plaid/metadata_aggregated.json` | PLAID 2018 labels for the 575 multi-appliance records |
| `plaid/metadata_submetered.json` | PLAID 2018 labels for the 1,876 single-appliance records |
| `plaid/analyze.py` | Type / load / status census of both metadata files |
| `plaid/gaps.py` | The onset and off-gap distribution from section 5.1 |
| `ukdale_demo.py` | Channel census, transition counts, simultaneity at 6 s and 12 s |
| `ukdale_demo3.py` | Simultaneous-ON analysis, visibility ladder, step overlap, fridge duty cycle |
| `kaggle_1min/` | The suspect synthetic 1-minute set, kept as a negative example |

### One caveat to record (provenance corrected 2026-09-21)

Signal forensics against the full download (`data/raw/ukdale-full/`) showed this slice is **not house 1**: `channel_2` = house-5 `fridge_freezer`, `channel_3` = house-5 `dishwasher`, `channel_4` = house-5 `kettle`, `channel_6` = house-5 `i7_desktop` (byte-exact copies of each channel's first 2^20 rows, rebased to a common start), relabeled house_1-style. `channel_5` ("washing_machine") matches no house_1-5 channel verbatim and is likely synthesized. `channel_1` ("custom_aggregate") is **the sum of the five channels plus a flat injected base** (residual mean about 27 W, standard deviation 7.4 W) - not any house's mains. A real whole-home meter would carry 40+ unmonitored loads on top of these five.

So the **appliance-level** findings above (step sizes, duty cycles, co-occurrence) are genuine UK-DALE measurements - of **house 5**, under wrong labels - and the aggregate channel is synthetic arithmetic, not a real aggregate. Every "house 1" attribution in this walkthrough inherits that mislabel; the authoritative UK-DALE house-1 numbers are in `docs/reports/dataset_eda/01_ukdale_eda_review.md`. For real aggregate work use the full download (house-1 mains) or the 16 kHz voltage/current stream.
