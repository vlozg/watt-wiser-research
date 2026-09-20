# Review: `06_ampds2_eda.ipynb`

**Scope.** `docs/reports/dataset_eda/06_ampds2_eda.ipynb` only. The other notebooks in the
series (`01`-`05`, `07`) are out of scope except where this one cites them.

**Method.** Read the notebook cell by cell (43 cells: 28 markdown, 15 code). Re-derived every
headline number directly from `data/raw/AMPds2/` - the 21 per-circuit CSVs, the four wide matrices
`Electricity_{P,Q,S,I}.parquet`, the billing/monthly tables, both climate files - using independent
re-implementations, never the notebook's own output. Read the release's own record: the Harvard
Dataverse deposits for **AMPds R2013 (doi:10.7910/DVN/MXB7VO)** and **AMPds2
(doi:10.7910/DVN/FIE0S4)**, and the AMPds2 data descriptor (**Makonin, Ellert, Bajic & Popowich,
*Scientific Data* 3:160037, 2016, DOI 10.1038/sdata.2016.37**). Inspected the release's HDF5
(`AMPds2.h5`) directly, the extraction pipeline the notebook consumes
(`src/pipelines/01_extract_dataset/extract_ampds2.py`), the gold label map
(`data/gold/appliance_map_ampds2.json`), the series overview (`00_overview.md`), NILMTK's AMPds
converter for public-tooling comparison, and the client pipeline under `repo/WattWiser/pipeline/`
for the notebook's "can we collect this?" claims.

---

## 1. Verdict

Numerically this is the most trustworthy notebook in the series. **Every headline quantity
reproduces exactly** - the 23-channel energy table to the kWh, the register forensics to the
individual corrupt minute, the episode and duty statistics, the seasonality ratios, the weather
join, the split-phase peak-hour contrast. The register dissection (Q4) and the cadence anatomy (Q3)
are genuinely good work: they are correct, they are mechanised, and they each end in an operational
rule we can use.

Four things keep it from being the reference document for this dataset, and all four are about
*what the columns are*, not about the arithmetic:

1. **The notebook's central subject is not a meter.** Q6 calls `UNE` "the largest main-house
   circuit" and "the dataset's largest unlabelled circuit". `UNE` is not a circuit at all - it is
   the remainder the release computed after subtracting the 18 named channels, and the release's own
   files prove it: on the published `Electricity_P.csv`/`Electricity_S.csv`, `UNE` violates
   `S >= P` in **1,044,248 of 1,051,200 minutes (99.34%)**, median `P/S` = 41, and its
   apparent-energy integral (1,457 kWh) is **less than half** its active-energy integral
   (3,482 kWh). No measured channel can do that. The Dataverse record for the release states the
   inventory plainly: **21 power meters**. There are 21 per-circuit CSVs and 21 HDF5 meters; the
   wide matrices carry 23 columns. The two extras are computed.
2. **The coverage headline is an identity, and the notebook asserts both sides of it.** Q5 concludes
   "100.0%, every single minute ... when coverage is complete, the 'residual/unknown' class
   disappears". Q6 then finds 17.9% of all electricity sitting in an unattributed circuit. Both
   cannot be true, and the resolution is the arithmetic above: check 2 is `UNE = UNE`. The
   contrast the TL;DR draws against UK-DALE (86-97%) and REFIT (~36%) is therefore not
   like-for-like, and the honest version of the comparison is *more* useful to us, not less
   (see P0-1).
3. **Per-circuit power factor is written off in the one place the notebook is right to care about
   it.** Q8 identifies PF as the motor-versus-resistor discriminator; Q12 then lists "PF per
   circuit (we cannot collect it) - [insight only]", and Q8 states "Our Shelly EM reports only
   whole-service PF". Our own schema carries `power_factor`, `apparent_power_VA`,
   `voltage_V` and `current_A` per channel, computes PF from them
   (`repo/WattWiser/pipeline/processing/process_data.py:17-23`) and validates the result
   (`repo/WattWiser/pipeline/processing/check_electrical_relationships.py:9-26`). The capability
   claim is inverted, and the notebook's own voltage/current table is the test fixture that shows
   why our formula needs care.
4. **`V * I` is not apparent power on this panel - on the 240 V channels it is roughly twice it.**
   The notebook prints a voltage table and a PF table and never checks a single power identity.
   Verified across all 21 per-circuit channels on the rows where each is actually drawing power:
   the six circuits recorded at ~240 V show `V*I` between 1.8x and 2.1x `S` (median relative
   difference 0.80-1.09), while the fifteen recorded at ~120 V show `V*I` within 10% of `S`
   (0.010-0.103). The release's current column on a 240 V circuit is a two-leg quantity, so
   multiplying it by a line-to-line voltage double-counts. That is precisely the formula our pipeline uses to derive apparent power and PF.
   This dataset documents the trap; the notebook owns the data and does not state it.

Everything below expands these, then credits what the notebook gets right, then ranks what is
missing. Severity is about consequence for us, not about how hard the fix is.

---

## 2. Reproduction

Everything below was recomputed from the raw release (`data/raw/AMPds2/`) with independent code.
No notebook output was trusted.

| Notebook claim | Notebook | Independent recompute | Verdict |
|---|---|---|---|
| wide matrix shape | 1,051,200 x 23 | 1,051,200 x 23 | exact |
| timestep / nulls / span | 60.0 s, 0, 730.0 d | min ts gap 60 s, 0 nulls, 730.0 d | exact |
| file inventory | 38 files, 6 groups | 38 (21 per-circuit + 4 wide + 2 monthly/billing + 2 climate + 5 gas + 4 water) | exact |
| energy table, all 23 channels | WHE 19,488 ... OUE 0 | identical, every channel | **exact** |
| WHE p50 / max | 758 W / 12,260 W | 758 / 12,260 | exact |
| register span vs P-integral | 19,480 vs 19,488 kWh (0.04%) | identical | exact |
| corr(P, register diff) | 0.9609 | 0.9609 | exact |
| negative register diffs | 10; wipe at minute 48,153: 1,924,472 -> 0 -> 1,924,453 | identical | exact |
| meltdown | 12 diffs > 1 MWh, 2013-06-17 10:00 -> 10:39; 9 drops; sizes {1.84, 12.88} MWh | identical | exact |
| naive positive-diff sum | 60,032 kWh = 3.1x the true span | 60,032 / 19,480 = 3.08x | exact |
| tiling checks 1 / 2 / 3 | 1,053.0 W / 0.0 W / 0.0 W | identical | exact, tautological (R2) |
| all-zero minutes | 6 | 6, at 2012-05-04 10:34 + 5 inside the meltdown | exact, cause wrong (R5) |
| longest identical WHE run | 11 min; 678 runs > 5 min | 11; 678 | exact |
| episodes > 1 kW | 24,159 (33.1/day); p50 4, p90 39, max 537 min; <=3 min 47.5% of events / 3.6% of energy | identical | exact |
| FGE | duty 36.6%, 39.3 cycles/day, ON p50 10 min, 130 W, max 1,497 W | identical | exact |
| UNE | 3,482 kWh (17.9%), on 99.4% of minutes, 5,020 bursts (6.9/day), p50 4 min, p50 1,525 W, max 5,258 W, night 85 W / workday 170 W | identical | exact, subject mis-identified (R1) |
| HTE | p50 5 W, max 74 W, 128 kWh | identical | exact |
| seasonality | winter/summer 1.28x; HPE 3.0x; gas 3.9x; corr(WHE, temp) -0.65 | identical | exact |
| RSE | 22.5% of service, peak 18:00 (524 W) vs main 22:00 (1,246 W), corr 0.79, base 133 W | identical | exact |
| weather file | 17,520 hourly rows; 10.4 degC; timestamps in ms | identical, ms confirmed | exact |
| V / f | mean 240.3 V, p20-p99 spread 8.5 V; f mean 60.005 Hz | identical; f min 0.000 (unreported) | exact |
| co-firing enrichment | 2.2x (HTW), 2.3x (WHW), 2.0x (WHG) | raw ratios identical; hour-matched 1.39x / 1.49x / 1.41x | reproduces but uncontrolled (R6) |
| floor decomposition | p50 sum 341 W, "every watt attributed" | 341 W confirmed; attribution false (R1) | wrong |
| **`S >= P`** | not tested | **UNE: 99.34% of minutes violate it; median P/S 41** | missing (R1) |
| **`V*I` vs S** | not tested | **240 V channels: V*I is 1.8x-2.1x S; 120 V channels: V*I ~ S** | missing (R4) |
| per-day rate divisors | `/ 730.4` | span is 730.0 d | low (R10) |
| machine-readable summary | 3 hand-typed statistics | all 3 happen to reproduce, but they are literals | low (R10) |
| citation | Paliwal, Sadeghianpourhamami & Stuckey, 2019 | Makonin et al. 2016, *Sci Data* 3:160037; Dataverse doi:10.7910/DVN/FIE0S4 | wrong (R8) |

---

## 3. What the notebook gets right

- **The register dissection (Q4) is the best work in the notebook.** It finds all 10 negative
  diffs, localises the wipe to a single minute, characterises the 39-minute meltdown, states the
  correct mechanism (a counter wrap, not consumption), and then proves the conclusion rather than
  asserting it: the naive positive-diff sum is 3.08x the true span, while the endpoint-to-endpoint
  span agrees with the P-integral to 0.04%. The operational rule it lands on - derive energy from
  `P`, never from the register - is exactly right. I checked the arithmetic independently and it
  holds to the watt.
- **The cadence anatomy (Q3) is the reason this dataset earns its place in the suite.** The
  duration-versus-energy decomposition of the 24,159 episodes is the single most transferable
  measurement in the notebook: 47.5% of episodes last <= 3 minutes but carry 3.6% of energy. That
  is a quantitative statement of what a 60 s poll does and does not destroy, and it is the number
  to quote when the cadence question comes up.
- **Grid integrity is verified, not assumed.** 1,051,200 contiguous rows, one timestep, zero nulls,
  integer watts, identical `ts_us` across every minutely file (I checked the alignment the
  notebook assumes but never tests - it passes exactly). The weather file's millisecond timestamps
  are detected, diagnosed and corrected in the notebook rather than papered over.
- **The label audit instinct is right, and the HTE finding is real.** `HTE` is labelled "Instant
  Hot Water Unit" and draws a 5 W median with a 74 W maximum over two years - 128 kWh total. That
  mismatch between a label and its measured behaviour is exactly the kind of defect the gold layer
  must survive, and the notebook surfaces it with numbers. (It then half-retracts it in Q6 by
  offering the same label for `UNE`; see R1.)
- **The MHE provenance check is correct and well argued.** "MHE is not a meter ... WHE minus RSE
  minus GRE reproduces MHE exactly" is verified, and the reasoning behind it - a convenience column
  cannot be treated as a measurement - is the right frame. The notebook simply does not apply it to
  `UNE`, which has the same provenance.
- **The seasonality block joins the right things.** Comparing electricity, gas and temperature
  together, and reporting the correlation (-0.65) rather than a bare ratio, is the correct way to
  show that the winter/summer factor is heating rather than behaviour.
- **The RSE contrast is a real finding with a clean statistic.** The sub-panel peak at 18:00 (524 W)
  against the main house at 22:00 (1,246 W), with corr 0.79, is a compact demonstration that one
  service can carry two households. The "two households, one service" lesson is sound; the topology
  is three structures, not two (R11).

---

## 4. Errors, ranked

### R1 (high) - `UNE` is the release's residual, not a circuit, and the release's own file proves it

Q6's framing: "`UNE` carries 3,482 kWh - 17.9% of all electricity, **the largest main-house
circuit** - yet appears in *no* label source: no per-circuit CSV in the release, no meter in the
HDF5 file, no description in our extracted map."

The three absences are correct and I verified each: there is no `UNE.csv`; `AMPds2.h5` under
`/building1/elec` holds exactly 21 meters (`meter1`-`meter21`) and neither `UNE` nor
`MHE` is among them; the gold map has no entry. The Dataverse record for the release states
"There are a total of **21 power meters**". What the notebook does not do is follow its own MHE
logic one step further. Two independent proofs, both from the release's own bytes:

1. **The identity is exact by construction.** In `Electricity_P.csv`,
   `WHE - RSE - GRE - sum(18 named) - UNE == 0` for every row (max absolute residual 0 W), and
   `WHE - RSE - MHE == GRE` exactly. Both hold **exactly in Q and S as well**, and hold in `I`
   to float32 epsilon (max residual 2.8e-14). An identity that survives across four independently
   measured quantities, in every one of 1,051,200 rows, is a definition, not a coincidence. Q5's
   check 2 is therefore `UNE = UNE` - it cannot fail.
2. **`UNE` violates physics that the named channels do not.** Apparent power cannot be less than
   active power. In the published files:

   | channel | minutes with `S < P` | median `P/S` | P-integral | S-integral |
   |---|---|---|---|---|
   | `WHE` | 1,705 (0.16%) | 0.840 | 19,488 kWh | 22,261 kWh |
   | `MHE` | 273,558 (26.0%) | 0.922 | 15,072 kWh | - |
   | `RSE` | 8,223 (0.78%) | 0.816 | 4,389 kWh | - |
   | `GRE` | 1 (0.00%) | 0.030 | 27 kWh | - |
   | **`UNE`** | **1,044,248 (99.34%)** | **41.0** | **3,482 kWh** | **1,457 kWh** |

   In the strongest `UNE` bursts (>2 kW) the median `P/S` is 1.11 and the maximum 2.98. `MHE`'s
   26% is the same signature at lower amplitude - the notebook already calls `MHE` arithmetic - and
   `WHE`'s 0.16% is the corrupt-register minutes the notebook itself found. `UNE` is the only
   channel where the violation is the norm.

Consequences to fix, in order: (a) drop the phrase "the largest main-house circuit" - `UNE` is the
unaccounted remainder of the release's own accounting, which is a *more* interesting object; (b)
re-derive the coverage statement as "the release closes its books by construction, and the closure
is published as `UNE`", which is the honest version of "100.0%"; (c) restate the floor
decomposition: the p50 floor of 341 W includes ~108 W of residual, so "every watt of it is
attributed" is only true if arithmetic counts as attribution; (d) keep the behavioural finding -
it survives and is arguably the most useful result in the notebook, because *what lives in a
residual* is exactly the question our own deployment will face. The correct reading of Q6 is:
"in a fully submetered home, the unlabelled remainder is 17.9% of consumption and it looks like
water heating" - a residual-composition result, not a discovered sensor.

### R2 (high) - "Coverage 100%, the residual disappears" and "17.9% unattributed" are one fact, told twice and reconciled nowhere

The two sentences are in the same notebook, three sections apart:

- Q5: "Check 2 is the headline: the 20 labelled house circuits plus the suite tile WHE *exactly* -
  not 86-97% (UK-DALE), not ~36% (REFIT) - 100.0%, every single minute." ... "when coverage is
  complete, the 'residual/unknown' class disappears".
- Q6: "the dataset's largest unlabelled circuit".

The first is a property of the release's arithmetic; the second is a property of its documentation.
The reconciliation the notebook owes the reader is one sentence long: *the release defines the
remainder as a column, so a residual class cannot appear in a tiling check; the residual has not
disappeared, it has been named `UNE`.* Without it, the TL;DR's cross-dataset contrast is
misleading in the direction that flatters our method: UK-DALE's 86-97% and REFIT's ~36% are
submetered *shares of a measured aggregate*, ours here is a subtraction performed by the publisher.
For a client-facing benchmark suite, this is the kind of comparison that later gets quoted back at
us.

Note also that the notebook's own cell-17 caveat ("the open risks move into label quality and
attribution") is the right instinct; it needs the `UNE` conclusion attached to it.

### R3 (high) - Q12 writes off per-circuit power factor, which is the client pipeline's own feature

Q8: "the electrical forensics our Shelly EM cannot produce per circuit (**it reports V and
per-circuit P only**)". Q8 again: "Our Shelly EM reports only whole-service PF, so per-circuit PF
is a capability AMPds2 has that we will not - [insight only]". Q12, in the closing list: "PF per
circuit (we cannot collect it)".

The client repository contradicts all three. The pipeline's own electrical-relationship checker
exists *because* those columns exist:

- `repo/WattWiser/pipeline/processing/process_data.py:17-23` - computes
  `calculated_apparent_power_VA = voltage_V * current_A`, then
  `calculated_power_factor = active_power_W / apparent_power_VA`.
- `repo/WattWiser/pipeline/processing/check_electrical_relationships.py:9-26` - recomputes the
  same two quantities and reports the error against the measured `apparent_power_VA` and
  `power_factor` columns.
- `repo/WattWiser/pipeline/features/create_features.py:58` - carries `power_factor_change` as a
  model feature.

So the accurate statement is the opposite of the notebook's: per-circuit PF is *the* electrical
capability we do have, which is why Q8's motor-versus-resistor split transfers directly into our
gold-layer taxonomy - and why we should be validating the identity it rests on (R4) rather than
recording it as a capability gap.

### R4 (high) - The 240 V current column is a two-leg sum, so `V*I` is twice apparent power - and our pipeline uses `V*I`

The notebook prints a per-circuit voltage table (Q8) and a per-circuit PF table (Q8) and never cross-
checks them. The check is one line per channel and it does not pass cleanly:

Measured on the rows where the channel is drawing power (`S > 50 VA`), across all 21 per-circuit
files:

| voltage class | channels | median relative difference between `S` and `V*I` | reading |
|---|---|---|---|
| ~240 V (six) | `WHE`, `RSE`, `GRE`, `HPE`, `CDE`, `WOE` | 0.802 - 1.090 (median across channels 0.919) | `V*I` is 1.8x - 2.1x `S` |
| ~120 V (fifteen) | `B1E`, `B2E`, `BME`, `CWE`, `DNE`, `DWE`, `EBE`, `EQE`, `FGE`, `FRE`, `HTE`, `OFE`, `OUE`, `TVE`, `UTE` | 0.0102 - 0.1030 (median 0.054) | `V*I` agrees with `S` to ~5% |

The notebook prints the voltage table that establishes exactly this split - six channels at ~240 V,
fifteen at ~120 V - and never uses it to classify the channels or to test an identity. The
mechanism is consistent with the panel's split-phase topology: a 240 V appliance's current is
carried by both legs, and the release's `I` appears to record the sum. That the observed factor is
1.8x-2.1x rather than exactly 2.0 is itself the argument for recording the leg convention per
channel instead of inferring it (P1). The notebook observes the V-I coupling elsewhere (the dryer
start sag) without ever multiplying V by I.

Why this matters to us, not just to the notebook: our pipeline derives apparent power and PF from
`voltage_V * current_A` and validates it against the measured values. On a single-phase 120 V
channel that identity is correct. On a two-leg channel metered with one voltage reference it is
wrong by a factor of ~2, and the failure is silent - the derived PF comes out at up to half the
true value, which is exactly the quantity the notebook wants to use to separate motors from resistors.
Recommended: (a) add the three identities as a first-class EDA check, per circuit; (b) state the
leg convention (`I` is one leg or the sum) as a field in the gold layer rather than a discovery
each time; (c) audit `calculated_apparent_power_VA` and `calculated_power_factor` on a 240 V
circuit before the feature is trusted, and add a unit test built from this dataset.

### R5 (medium) - The six all-zero minutes are the two register incidents; Q4 and Q7 tell the same story twice with different explanations

Q7 attributes the six all-zero minutes to "logger reboots ... hidden gaps, not missing rows". I
located all six: **2012-05-04 10:34** and **2013-06-17 10:06, 10:34, 10:36, 10:37, 10:38**. The
first is the register-wipe minute (the `1,924,472 -> 0 -> 1,924,453` transition is at the same
timestamp); the other five are inside the 39-minute meltdown window that Q4 dissects. So five of
six zeros are in one incident, and the sixth is the second incident - both of which the notebook
has already found and explained in the previous section, with a different mechanism.

Neither section cross-references the other, and "reboot" is an unverified mechanism. The correct
statement is stronger than the original: *in this release the rows are never missing, but the logger
writes zeros when it is confused, and it was confused at exactly the two moments the cumulative
registers corrupted.* That is a reusable rule for our own ingest: zero rows adjacent to a register
discontinuity are suspect, not merely empty.

### R6 (medium) - The co-firing test has no control, and the "three independent sensors" are one schedule

Q6's enrichment statistics are quoted raw: hot-water flow is enriched 2.2x (0.20 vs 0.09) during
`UNE` bursts, whole-home water flow 2.3x, the gas water-heater counter 2.0x. The baseline is the
dataset-wide rate, so any quantity with a daily rhythm is "enriched" during a burst load that also
has a daily rhythm - and both do, because both are driven by occupant hot-water use.

I re-ran the test against an **hour-of-day-matched baseline**: for each burst minute, compare
against non-burst minutes in the same hour of day. The effect survives, and it shrinks:

| witness | raw | hour-matched expected | hour-matched | shrinkage |
|---|---|---|---|---|
| `HTW` (hot-water flow) | 2.2x (0.200 vs 0.090) | 0.144 | **1.39x** | ~60% of the headline |
| `WHW` (whole-home water) | 2.3x | - | **1.49x** | - |
| `WHG` (gas water heater) | 2.0x | - | **1.41x** | - |

A 200-draw hour-matched permutation null gives a mean of 0.144 with a 95% band of 0.140-0.149, so
the observed 0.200 is ~26 standard deviations out. **The conclusion is sound; the magnitude is
roughly 60% overstated.** Two further caveats: `HTW` is a subset of `WHW`, so the first two
"witnesses" are nested, not independent; and all three are proxies for the same household water
schedule, so "three independent sensors" is really "one schedule, observed three ways". The
cross-sensor *method* is still the right lesson for us (and the notebook's own closing advice -
"hunt cross-sensor evidence before inventing labels" - is correct); what it needs is the control.

### R7 (medium) - The gallery window is the highest-energy window in two years, presented as typical behaviour

`best_window()` sorts all 6-hour windows by total energy and takes the first of the top 300 whose
ON-fraction is <= 95%. That is a *maximum-demand* window with a duty filter, and the Q9 captions
read it as representative ("`FGE` shows the compressor sawtooth", "the heat pump runs as hour-plus
compressor blocks"). Two consequences: (a) every `FGE` panel is drawn from the two coldest days
available, which is why the duty cycles look so clean; (b) for a circuit that is rarely off, all
top-300 candidates may be >= 95% ON, and the function then falls back to `cand[0]` - the highest-
energy window, entirely ON - so an always-on circuit's "gallery" panel cannot show anything except
one unbroken plateau. One line in the caption ("window selected as the highest-energy 6 h span with
at least 5% OFF minutes") would fix the honesty problem; a median-day window alongside it would fix
the representativeness problem.

### R8 (medium) - The provenance section cites a work that does not resolve, and misses both citable sources

The Provenance section's sources line reads: "staged from the SFU release (P. Paliwal, N. Sadeghianpourhamami,
J. Stuckey, "AMPds2: A Public Dataset for Load Disaggregation and Sustainability Research",
2019)". A Crossref author/bibliographic query for those names returns no such work in this subject
area, and the AMPds2 dataset descriptor is a different paper: **Makonin, S., Ellert, B., Bajic,
I.V., Popowich, F., "Electricity, water, and natural gas consumption of a residential house in
Canada from 2012 to 2014", *Scientific Data* 3:160037, 2016, DOI 10.1038/sdata.2016.37**. The
release's own record is the Dataverse deposit **doi:10.7910/DVN/FIE0S4** (AMPds2); the original
one-year release is **doi:10.7910/DVN/MXB7VO** (AMPds R2013), which is what NILMTK's converter
targets.

This matters beyond tidiness: the Dataverse description is the document that states the 21-meter
inventory that decides R1, and the descriptor is where the release's own definitions live. A
provenance line that points at neither is why the accounting question was never asked. Fix the
citation, and cite the Dataverse record as the inventory source.

### R9 (medium) - "The only North American split-phase panel in our suite" contradicts the series overview

Cell 5 says the panel is "the exact structure our Shelly EM deployment will face in US homes, which
**no other dataset in our suite reproduces**"; Q12 repeats "the only dataset here with a split-phase
240 V panel". `00_overview.md` assigns that niche to REDD explicitly: "| `03_redd_eda.ipynb` |
REDD | 6 US houses, 1 s, 2011. Heritage US set; **split-phase mains**. |" and, in the topology
table, "REDD needs two meters summed (split-phase)"; the notebook's own provenance cell lists
`03_redd_eda.ipynb` as a sister notebook. The claim is checkable in the same directory and it is
wrong.

The defensible version is narrower and still useful: AMPds2 is the only release in the suite that
records *per-circuit voltage and current* on a split-phase panel, and the only one at 60 s. REDD has
the topology but at 1 s with a different channel convention. State it that way and the dataset's
role in the suite (the cadence-limit study, the bridge between the UK fleet and our deployment)
becomes clearer, not weaker.

### R10 (low) - Hand-typed statistics in the machine-readable summary, and the 730.4-day divisor

The notebook's own contract is "every number printed in prose is computed by the notebook (no
hand-typed statistics)". The human-readable output honours it; the machine-readable one - the
artifact a pipeline would actually consume - does not:

- `'corr_P_registerdiff_masked': 0.9609` is a literal. It happens to be right today.
- `'corr_monthly_whe_temp': -0.65` is a literal. It happens to be right today.
- `'timestep_s': 60.0` is a literal; the notebook prints `[60.]` from the data two cells earlier.

All three are checkable in one line each, and the risk is not that they are wrong now - it is that
they silently stay "right" when the data or the mask changes. Two of them are exactly the numbers a
future reader would use to validate a re-run.

Related: every per-day rate is computed as `x / 730.4`, while the notebook's own span printout is
**730.0 days** (1,051,200 minutes / 1440). The divisor is a magic constant, it appears in the FGE
cycle rate and the `UNE` burst rate, and it makes both ~0.05% low. Small, but it is the same
defect class: a number that is not derived from the data.

### R11 (low) - Smaller defects

| # | Where | Defect |
|---|---|---|
| a | Q6 "three structures" | "two households, one service" omits the third structure: `GRE` is labelled "Sub-Panel, Detached Building" and carries 27 kWh in two years (~37 Wh/day) - a real but nearly empty circuit. It is worth one clause, because it is the reason check 1 and check 3 have a non-zero residual at all |
| b | Q6 "seven exact 1.84 MWh steps" / "12.88 = 7 x 1.84" | "Exact" holds only at the printed 2 dp. The underlying steps are 1,839,357-1,839,358 Wh and the swing is 12,876,031 Wh = 7 x 1,839,357.5 + 528 Wh. Say "1.84 MWh to the printed precision", or print the watts |
| c | Q8 | `DPF` is printed but never discussed. It is a different quantity from the `APF` the prose uses: constant 1.000 on `WHE`/`RSE`/`GRE`/`HPE`/`CDE`/`WOE`/`B1E`, 0.89 on `FGE`, and exactly 0.00 on `EQE`/`UTE`/`OUE` (electronics with no displacement component). A column whose value is 0 or a hard 1.0 in most circuits is a derived or default-filled column, not a measurement, and it deserves the same provenance treatment as `MHE` |
| d | Q8 | `APF = P/S` by definition (median absolute difference 0.0013-0.0098 across channels), so "the power factors" are not independent evidence about the supply - `APF` cannot disagree with `P` and `S`. The only independently informative member of the family is `S` vs `sqrt(P^2+Q^2)`, which disagrees by up to 29% on `CWE`/`FRE` (0.293), `UTE` (0.288), `EQE` (0.222) - i.e. `Q` here is displacement-only and harmonic distortion is folded elsewhere. That is a real property of the release and it is invisible in the notebook |
| e | Q8 | `f` is reported only as mean 60.005 Hz; its minimum is **0.000 Hz**. A recorded 0 Hz is a sentinel or a dropout, and it should be counted and excluded before any frequency statistic |
| f | Q1 | Three water files are presented (`WHW`, `HTW`, `DWW`); the Dataverse record says two water meters "with additional appliance usage annotations". One of the three is likely an annotation table rather than a meter. Cheap to resolve from the release's readme |
| g | Q2 | `Pt` is described as "active energy total, in Wh" - correct, and I verified the implied unit from `corr(P, register diff)` and the span. Worth printing the unit check rather than asserting it, because it is the assumption the whole register section rests on |
| h | Q6 framing | The enrichment prose says "three independent sensors point the same way"; `HTW` is a strict subset of `WHW` (same household, finer point), so at most two of the three are independent observations of different things |
| i | Q3 | Dead variable `hi` in the episode cell (assigned, never used) |
| j | Provenance | The provenance cell points at the throwaway-artifact summary path for the machine-readable output. AGENTS.md forbids docs from referencing that directory: the summary belongs in a tracked location, or the reference should be dropped. This is currently the only `docs/` reference to it |

---

## 5. Missing analyses, ranked by value

### P0 - Close the release's accounting, and re-state what a residual means for us

The notebook's questions are one step short of the most valuable result in the dataset. It should
state, as a finding rather than a caveat: *the release publishes 21 measured meters, and closes its
books on a 23-column matrix; the two extra columns (`MHE`, `UNE`) are arithmetic.* Then it can do
the analysis that actually transfers: the residual is 17.9% of consumption, it is dominated by a
water-heating-shaped load, and it is what an incompletely-submetered panel gives you. For our own
deployment - Shelly CTs on a subset of circuits - the equivalent quantity is the live "unaccounted"
channel, and this dataset is the only one in the suite where the *true* answer is knowable. That is
a much better reason to keep AMPds2 than "the only fully submetered home". Concretely: a small
table of `WHE = RSE + GRE + named-18 + UNE` by energy (100% = 22.5% + 0.1% + 59.5% + 17.9%), and
a section on how to detect and bound the residual in our own data.

### P0 - Three power identities, per circuit, as a standard check

Covered in R4 and R11(d). Add, for every circuit: (1) `S` vs `V*I` with the leg convention stated;
(2) `APF` vs `P/S` (expect agreement - it is definitional); (3) `S` vs `sqrt(P^2 + Q^2)` with the
discrepancy reported as distortion power. One table, three columns, and it is the check that turns
"the panel looks clean" into an auditable statement - and the one that protects our own
`calculated_power_factor`.

### P0 - Register-versus-P audit on all 21 channels, not only WHE

The notebook audits the aggregate register thoroughly and then trusts the per-circuit registers
implicitly. They do not all agree with their own `P` integrals:

| channel | register span vs P-integral |
|---|---|
| `GRE` | +7.3 kWh, **26.6%** of its own span |
| `EQE` | +9.3 kWh, 1.33% |
| `HPE` | +26.9 kWh, 0.91% |
| `RSE` | +9.6 kWh, 0.22% |
| `WHE` | -7.5 kWh, 0.038% |

`GRE`'s 27 kWh total means a 7 kWh disagreement is a 27% error on that channel; the notebook's
conclusion "use `P`, never the register" is right, but the *magnitude* of the disagreement per
channel is the evidence that the rule is needed everywhere. It also closes the loop on the
`WHE`/others sign pattern: the disagreements do not cancel, so this is not a conserved
measurement error.

### P1 - An hour-matched control behind every cross-sensor claim

Covered in R6. The notebook already has the machinery for the seasonality comparison; the
enrichment test needs the same discipline. Minimum viable version: report raw and hour-of-day-
matched enrichment side by side, and give the permutation band. Given how central the Q6
attribution is to the notebook's story, this is the highest-value statistical change available.

### P1 - Reconcile with the release's record and fix the citation

Covered in R8. In addition to the citation, the notebook should compare its own inventory against
the Dataverse description line by line (21 power meters, 2 water + annotations, 2 gas, weather from
Environment Canada) and mark each of our 38 staged files against it. That is a half-hour of work
and it is precisely the kind of provenance table the other notebooks in the series already carry.

### P1 - Fix `ts_us` units in the extractor instead of guessing them in the notebook

The notebook detects that the weather file's timestamps are in milliseconds, corrects them, and
carries the caveat downstream. The defect is upstream:
`src/pipelines/01_extract_dataset/extract_ampds2.py:22` documents "`ts_us = unix_seconds * 1e6`"
and lines 38-46 apply that rule to *whatever the first column happens to be*. Two consequences are
already visible in the staged data: for `Climate_HourlyWeather` the first column is already in
milliseconds, so its `ts_us` is 1000x too large until the notebook patches it; for
`Climate_HistoricalNormals` the first column is the text `Item` field, which falls through to the
nullable-Int64 branch and yields an all-null `ts_us`. The notebook handles both correctly - it
should not have to. Recommended fix: a per-file (time column, unit) declaration table in the
extractor, and a manifest note per file; this removes the same class of ambiguity for
`NaturalGas_Monthly`, whose unit is currently inferred at runtime by a value test.

### P1 - Leg/phase topology as a first-class field

Covered in R4 and R9. Every circuit's record in the gold layer should carry its phase/leg
configuration (120 V single-leg, 240 V two-leg, aggregate), because it determines whether
`V*I` is apparent power. This is the most directly reusable artifact from this dataset for our
own deployment.

### P2 - A representative-window gallery

Covered in R7. Keep the maximum-energy window for signature reading, add a median-day window for
representativeness, and state the selection rule in the caption. Cheap and it removes a systematic
bias from every panel caption in Q9.

### P2 - Verify the alignment of the gas/water/climate tables rather than assuming it

The join in Q6 assumes the water and gas tables share the minutely grid and offset. I verified it:
the per-circuit and wide minutely files carry byte-identical `ts_us`, and the water tables align to
the same grid. The notebook never checks this, and it is one line. Worth adding explicitly, because
"the offset is the same" is exactly the assumption that fails in other datasets in the suite.

### P2 - The residual as the client's real UNKNOWN class

A short, forward-looking subsection: in our deployment the unaccounted power will not be a
published column, it will be a live estimate, and this dataset gives us the ground truth for what
such an estimate contains (a large, bursty, water-heating-dominated component plus a small
always-on base). It is the natural bridge from this notebook to the client-facing framing, and it
uses the `UNE` findings above rather than discarding them.

---

## 6. How this compares with public practice

- **The descriptor's inventory is the arbiter.** The AMPds2 Dataverse record states 21 power
  meters, and the descriptor paper organises the release the same way. Any notebook that treats a
  column outside that set as a measured channel is making a claim the release does not support.
- **Public tooling gives the two extra columns no meter identity.** NILMTK's AMPds converter builds
  one NILMTK meter per per-circuit CSV and ignores the wide matrices entirely; there is no
  converter-side object for `MHE` or `UNE`. Our conclusion agrees with the tooling - which is
  reassuring, but it also means the *derived* nature of those columns is not documented anywhere in
  the ecosystem. It should be documented in our gold layer.
- **Which release is being converted matters.** NILMTK targets AMPds R2013 (one year, DOI
  10.7910/DVN/MXB7VO), not the two-year AMPds2 deposit used here. NILMTK's converter timezone
  (`America/Vancouver`) validates the notebook's local-time choice, and its per-column mapping
  confirms the release's column set - but any comparison against "what NILMTK does with AMPds2"
  should state that the reference implementation is a year shorter.
- **The two quirks we found are undocumented in public sources we could reach**: the two-leg current
  convention behind the 240 V `V*I` factor of two, and the millisecond timestamps in the climate
  table. Both should be recorded as our own notes in the gold layer rather than looked up again.
- **On the citation**, the descriptor and the Dataverse deposits are the two citable objects; the
  notebook cites neither (R8).

---

## 7. Suggested order of work

1. **Correct the `UNE`/`MHE` framing** (R1, R2, P0-1). Reframe the coverage headline as a
   published closure, and reintroduce the residual as the transferable finding. This is a
   prose-and-one-table change; it is first because two other sections depend on it.
2. **Add the three power identities per circuit** (R4, R11d, P0-2), state the leg convention, and
   open a follow-up on `calculated_apparent_power_VA` / `calculated_power_factor` for 240 V
   circuits in the client pipeline.
3. **Fix the PF capability claim** (R3) in Q8 and Q12 - it is a factual correction about our own
   data contract, and it is what makes step 2 worth doing.
4. **Cross-link Q4 and Q7** and re-attribute the six zero minutes (R5).
5. **Add the hour-matched control** to the Q6 enrichment test (R6, P1), reporting raw and matched.
6. **Per-channel register-versus-P audit** (P0-3) - extend the existing `WHE` table to all 21
   channels.
7. **Fix the provenance: citation, Dataverse inventory table, and the throwaway-artifact
   reference** (R8, R11j).
8. **Extractor `ts_us` unit table** (P1), so the climate and monthly files stop needing runtime
   detection.
9. **Smaller items**: gallery caption rule (R7), summary-JSON literals and the 730.4 divisor (R10),
   the `DPF`/`APF`/`f` provenance notes and the 2 dp register language (R11), the REDD
   cross-reference (R9), the water-meter count (R11f).

---

## 8. Sources

- Notebook: `docs/reports/dataset_eda/06_ampds2_eda.ipynb` (43 cells).
- Release as staged: `data/raw/AMPds2/` (21 per-circuit CSVs, 4 wide matrices, `AMPds2.h5`,
  billing/monthly tables, `Climate_HourlyWeather`, `Climate_HistoricalNormals`, gas and water
  files, appliance manuals, `Electricity_Statements.pdf`).
- Extracted layer: `data/fnd/ampds2/` (38 parquet files) via
  `src/pipelines/01_extract_dataset/extract_ampds2.py`.
- Labels: `data/gold/appliance_map_ampds2.json`.
- Release record: Harvard Dataverse, AMPds2, doi:10.7910/DVN/FIE0S4; AMPds R2013,
  doi:10.7910/DVN/MXB7VO.
- Descriptor: Makonin, S., Ellert, B., Bajic, I.V., Popowich, F., *Scientific Data* 3:160037
  (2016), DOI 10.1038/sdata.2016.37.
- Series context: `docs/reports/dataset_eda/00_overview.md`;
  `docs/reports/dataset_eda/01_ukdale_eda_review.md`;
  `docs/reports/dataset_eda/02_refit_eda_review.md`.
- Client pipeline: `repo/WattWiser/pipeline/processing/process_data.py`,
  `repo/WattWiser/pipeline/processing/check_electrical_relationships.py`,
  `repo/WattWiser/pipeline/processing/validate_data.py`,
  `repo/WattWiser/pipeline/features/create_features.py`.
