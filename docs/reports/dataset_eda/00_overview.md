# 00 — FND Dataset EDA: Overview, Terminology and Metrics

*Companion to the per-dataset notebooks in this directory. Data in `data/fnd/` is raw fidelity — original cadence, original values, nothing resampled or cleaned.*

---

## 1. What this report set is

An exploratory analysis of every dataset available to the project, one notebook each:

| File | Dataset | One-line summary |
|---|---|---|
| `01_ukdale_eda.ipynb` | UK-DALE | 5 UK houses, 1 s mains + ~6 s submeters, 2012-2017. Primary reference; 4.1-year flagship house. |
| `02_refit_eda.ipynb` | REFIT | 20 UK homes, one wide table each, ~7 s channels, 2013-2015. Fleet-scale label audit, stuck meters, frozen-plateau handling. |
| `02b_refit_eda_localtime.ipynb` | REFIT (local time) | The 02 walk re-run on true UK local time — one clock for all 20 homes; local-day rhythm where 02's UTC framing splits it. |
| `03_redd_eda.ipynb` | REDD | 6 US houses, 1 s split-phase panel + 3-4 s circuits (spec 3 s; b1/b4/b5 record 4 s), 2011. Heritage US set; 8-50% panel coverage with multi-day outages. |
| `04_eco_eda.ipynb` | ECO | 6 Zurich flats, 1 s site meter + plugs + occupancy labels. |
| `05_greend_eda.ipynb` | GREEND | 8 homes (Italy/Austria), 1 Hz wireless plugs in wide MAC-column format, no site meter. The label-trust set; longest spans (290-499 d); labels are positional (meter k = kth MAC column) and physics-checked in Q6. |
| `06_ampds2_eda.ipynb` | AMPds2 | 1 Canadian house, 2 years at 60 s, 20 circuit meters. Low-rate long horizon. |
| `07_synthetic_shelly_eda.ipynb` | Synthetic Shelly | 1 synthesized CSV, 30 days at 5 s. Unit-test fixture only. |

Each notebook is self-contained and designed to be **read top-to-bottom without executing anything**: a question is posed in markdown, code computes the answer, charts are rendered, a reading explains what the chart shows, and every notebook ends with a machine-readable summary of its key numbers.

**How the notebooks differ.** Each dataset can answer different questions, so each notebook asks its own: UK-DALE gets four-year stability and seasonality; REFIT gets 20-home scale (02b re-runs the same walk on true local time); REDD gets the split-phase and 110 V traps; ECO gets occupancy; GREEND gets what happens with no site meter; AMPds2 gets what 60 s cadence destroys; the synthetic fixture only proves the plumbing works. Read this overview first, then 01 as the template; the rest in any order.

---

## 2. The problem in one page

A home has one electricity meter at the point of connection — the **aggregate** (or *mains*). One number in watts, sampled every few seconds, with everything the house does superimposed into it: fridge compressor cycles, kettle boils, washing programs, standby electronics.

**Non-intrusive load monitoring (NILM)** — energy disaggregation — is the task of recovering *which appliances are running, when, and using how much* from that aggregate alone. Why it matters: a watt at the mains is anonymous. The same 500 W average could be an old freezer, a gaming PC, or a failing heater. Appliance-level breakdown turns a bill into a diagnosis — which devices consume (attribution), which are drifting toward failure (a fridge duty cycle creeping from 30% to 50%), what is actionable feedback, and where flexibility (a dishwasher mid-cycle) exists.

**Why these datasets matter to this project.** The target deployment records the aggregate with modern submeter hardware. Public datasets record far more — per-appliance meters, button logs, occupancy — and most of that *cannot be collected in deployment*. They are the textbook for what the aggregate is made of and what a model is being asked to infer. Every exhibit in the notebooks therefore carries a tag:

- **[insight only]** — for understanding the problem; not collectable in the target deployment, not usable for MVP experiments.
- **[collectable]** — the same quantity (or a close equivalent) can be recorded by the planned aggregate submeters.

The gap between "sum of known submeters" and "the mains" is the **residual**. Even the deepest labelling leaves a visible floor — UK-DALE's labelled channels track its site meter at r = 0.975 yet cover only 86-97% of mains energy across sampled 30-day windows — so any attribution model carries an explicit **UNKNOWN** class. One caveat worth internalising: UK-DALE's residual is a flat ≈60 W floor, uncorrelated with demand — mostly the 52 battery-powered plug meters' own draw — whereas a Shelly deployment's residual will be genuinely unmonitored appliances. Same accounting, different physics: the books must always be closed, but the residual's *composition* must never be assumed. Pretending everything is explained is the most common way NILM evaluations overstate their quality.

---

## 3. How the data was collected (the feeling of it)

Two instrument classes appear across the sets, in different mixes:

- a meter on the **incoming supply** — the aggregate, typically every 1 s (UK-DALE, REDD, ECO) or 60 s (AMPds2);
- small meters on **individual appliances or circuits** — a fridge here, the kettle there — typically every 3-7 s (REDD circuits 3-4 s, UK-DALE ~6 s, REFIT ~7 s), or plug meters in ECO/GREEND.

What "raw fidelity" means here: one file (or column) per meter, a single `ts_us` timestamp column (int64 microseconds, UTC; a fixed per-dataset offset encodes local time), original cadence preserved, missing-value sentinels as received (ECO `-1`, REFIT quality flags, GREEND mis-dated rows, REDD cache derivatives). Nothing is resampled or cleaned — the EDA measures the recording *as collected*, because cadence, gaps and sentinel handling are themselves findings.

---

## 4. Terminology

| Term | Meaning |
|---|---|
| **mains / aggregate** | Whole-home power at the point of connection. GREEND has none (plug sum only); REDD needs two meters summed (split-phase). |
| **channel / submeter / plug** | A per-appliance or per-circuit meter. UK-DALE numbers channels; REFIT has `Appliance1..9`; AMPds2 one file per circuit code. |
| **sampling cadence** | Interval between samples. Bounds visibility: a 2-minute kettle boil at 60 s sampling is 2 samples. |
| **ON threshold** | Power above which a channel counts as ON. Project convention: `thr_on_W = max(5.0, 0.5 * p50_on_W)`, where `p50_on_W` is the median power of samples above a 5 W noise floor. |
| **duty cycle** | Fraction of time ON. Fridge 20-55%, kettle <1%, always-on devices ~100% (and useless as NILM targets). |
| **episode / dwell** | A maximal contiguous ON run; its length is the dwell time (kettle ~2 min, washer ~1-2 h). Event-based methods detect onsets; dwell statistics size the detection window. |
| **signature** | The characteristic power shape of an appliance — edges, level, noise. Rich at 1 s, smeared at 60 s. |
| **residual / UNKNOWN** | Mains energy not explained by known submeters; must be an explicit class. |
| **simultaneity** | How often 2+ target appliances run at once — bounds how ambiguous the aggregate is. |
| **recording fraction** | Share of the analysis window a channel actually records. Use-only meters (UK-DALE's iron: ~0%) report energy for recorded periods only; OFF is indistinguishable from "logger parked". |
| **step size (dP)** | Power jump the aggregate sees at an appliance switch-on. A property of the appliance, not the meter — UK-DALE's kettle has a median step of ≈225 W despite drawing 2.3 kW when ON (thermostat cycling). |

---

## 5. Metrics — what we adopt and why

Pointwise accuracy misleads here: duty cycles span 0.5% (microwave) to 42% (fridge), so a single accuracy number averages over regimes differing by two orders of magnitude in event rarity. Therefore:

1. **Episode-level precision / recall / F1** is the headline metric — score *events* (a predicted ON-run overlapping a true episode within tolerance), not seconds. Tolerance scales with cadence (±60 s at 1 s data; the minimum at 60 s).
2. **Energy share and share error** is the co-metric — end users consume kWh, not events.
3. **Pointwise accuracy is reported only as a sanity number**, never the objective.
4. **The UNKNOWN class is mandatory** — attribution must close the books against the mains; the notebooks' coverage charts show the residual explicitly.

---

## 6. What the EDA found (cross-dataset digest)

### Signal level

| Dataset | Mains rows | Span (d) | dt (s) | Mean W | p50 W | p95 W | Energy (kWh) |
|---|---|---|---|---|---|---|---|
| UK-DALE h1 | 128,238,700 | 1,500.9 | 1.0 | 342.5 | 223.3 | 693.3 | 12,268 |
| REFIT h1 | 6,960,008 | 639.0 | 7.0 | 481.1 | 242.0 | 1,372.0 | 7,986.5 |
| REDD b1 (m1+m2) | 1,561,660 | 36.3 | 1.0 | 384.0 | 176.3 | 1,263.9 | 341.3 |
| ECO h01 | 21,168,000 | 245.0 | 1.0 | 283.0 | 128.5 | 1,200.0 | 1,658.2 |
| GREEND b0 (plug sum) | 19,886,555 | 310.5 | 1.02 | 161.7 | 90.3 | 314.3 | 1,204.7 |
| AMPds2 (WHE) | 1,051,200 | 730.0 | 60.0 | 1,112.3 | 758.0 | 2,988.0 | 19,488 |
| Synthetic | 518,400 | 30.0 | 5.0 | 372.9 | 286.5 | 777.0 | 268.5 |

(GREEND's "mains" is a plug sum — a lower bound, not a site meter. REDD's 341.3 kWh bridges multi-day outages by carrying values forward; capped at one 10 s sample per interval it is 167.7 kWh — 173.6 kWh of the bridged total is phantom. Per its release documentation REDD's meters record **apparent power**, so its W and kWh magnitudes run high relative to active power; ratios *within* the panel are unaffected.)

### Appliance priors

| Appliance | Typical p50_on W | Duty % (range) | Episodes/day | Dwell p50 |
|---|---|---|---|---|
| fridge | 30-130 | 20-55 | 10-30 | 10-40 min |
| washing_machine | 140-380 | 1-6 | 0.3-1.5 | 30-90 min |
| dishwasher | 120-2,545 | 0.5-1.8 | 0.3-1 | 60-120 min |
| kettle | 1,760-2,946 | 0.3-0.7 | 2-8 | 100-200 s |
| microwave | 930-1,520 | 0.5-1.1 | 1-4 | 60-180 s |

Ranges are the fleet-voted distributions from 01/02; the physics verdicts in 03-05 flag further channels that must not feed priors — REDD's degenerate low-power channels (03 Q4), GREEND's label-wrong channels (05 Q6: not one of its four "kettle" channels matches kettle physics, and its only "microwave" channel is a noise-storm). A vendor label alone earns no prior.

Reading: the **fridge is the always-there anchor** (highest canonical energy share in every house that has one); **kettle/microwave are high-power, rare, trivially detectable at 1 s**; **washing machine and dishwasher are the hard, valuable middle** — long multi-stage dwell, moderate power, high overlap risk with the fridge base.

### Structural findings

1. **Cadence is the first-order design constraint.** 1 s data shows crisp edges; 60 s flattens them. Detectors must be re-parameterised per cadence; AMPds2 is the in-house proxy for degraded-cadence deployment.
2. **Labels are incomplete everywhere that matters** — duplicate fridge columns, plugs covering only selected appliances, positional MAC-column names, combo channels merging several appliances, and label names that differ across houses (`dish_washer` vs `dishwasher`, `fridge_freezer`). Deduplicate canonicals before any cross-dataset statistic. REFIT's audit sharpens the point: its own labels can be wrong in both directions — a "kettle" that idles at 100 W and never boils, a second "microwave" that is actually a compressor-like trace — and the fleet-wide appliance priors only survive because 20 homes vote each type's distribution down (kettle p50-ON median 2,614 W; the mislabeled channel sits at 113 W — the fleet's minimum, and its trace (idle draw, no boil) looks nothing like a kettle).
3. **Threshold rules have failure modes.** A channel whose median ON power sits below the 5 W noise floor (REDD meter 5) looks ON 99.4% of the time under the convention; UK-DALE house 2's fridge, idling at ~10 W, reads 100% duty until a floor-aware threshold fixes it. And a single fleet-wide threshold per appliance type misfires too: applying REFIT's 90 W microwave rule across its 17 microwave channels flips 6 of them. Every per-channel threshold needs a duty-cycle sanity check against the sensor's idle floor.
4. **Residual mass is real and large — and its composition is a finding, not a given.** Coverage in deeply-labelled UK-DALE h1 runs 86-97% across sampled 30-day windows (the paper publishes 80% for the full deployment); mid-teens to ~53% across the 20 REFIT homes (median ~36%, residual 170-548 W, mains-vs-submeter-sum correlation 0.32-0.95); near-100% only in the synthetic fixture. UK-DALE's leftover is a flat ≈60 W floor made mostly of the meters' own draw; an always-on appliance floor still exists beneath it (a flat ~50 W device rode the UK-DALE lighting circuit for 7.8 days straight).
5. **Simultaneity is low once deduplicated — but not at events.** ~0.7-3.9% of 60 s buckets have 2+ canonical ON (REFIT's 20-home fleet sits at 3.9%); yet in UK-DALE roughly half of kettle, washer and dishwasher onsets begin while another canonical appliance is already running. Bucket-level stats flatter a model; event-level co-occurrence is the honest bound.
6. **Every dataset ships a documented trap** — REFIT's frozen meters: aggregate plateaus up to 35.6 days that still record phantom energy (5.4% of the fleet's total), fleet-synchronous freezes (14-15 houses pin to one constant value on 2014-08-01 and 2014-08-30), no home offers a contiguous 30-day gap-free stretch, and its `Issues` flag decodes cleanly to "submeter sum exceeds mains" — treat it as a quality marker, not an outage log. Elsewhere: ECO's plug `-1` W dropout sentinels, GREEND's year-2000 clock runs (and its NaN-valued dead columns, invisible to Parquet statistics), REDD's cache files and float32, AMPds2's cumulative registers with resets (plus billing anchors that are invoice dates in milliseconds - one duplicated pair - a weather timestamp column that is the CSV's local wall clock stamped as UTC, and a water-billing anchor reduced to `ts_us = 2`), the synthetic fixture's unlabeled 265 W base load. Meters also lie about magnitude: 25 UK-DALE channels carry sporadic ~4 kW RF artefacts (a table lamp "drawing" 3,993 W), REFIT's mains spikes reach ~68 kW (single-phase ceiling is ~14 kW), and UK-DALE's 6 s "aggregate" channel reads ≈13.7% high against the site meter. Reading raw files defensively is the default.
7. **Ground truth beyond meters is usable.** ECO occupancy labels show it directly: in house 1's summer label window, occupied hours average 261 W vs 127 W away — and that away-floor is the cleanest single illustration of the residual problem.

---

## 7. Reproduce

- Shared library: `src/pipelines/02_fnd_eda_notebooks/eda_fnd_lib.py` — streaming readers, `channel_stats`, simultaneity, resampling, figure helpers and the markdown formatters (`md_table` / `md_scan_stats` / `md_summary`) the notebooks render through.
- Notebooks: the eight `.ipynb` files in this directory are **generated artifacts**, exported fully executed from the marimo sources in `src/pipelines/02_fnd_eda_notebooks/`. Edit the `.py` source, then re-export:

  ```bash
  uv run marimo export ipynb --include-outputs -f src/pipelines/02_fnd_eda_notebooks/01_ukdale_eda.py \
    -o docs/reports/dataset_eda/01_ukdale_eda.ipynb
  ```

  (Exporting runs the notebook headless against `data/fnd/` and embeds the outputs; data paths resolve from the repo layout, so the export works from any working directory. The exported `.ipynb` files are never edited by hand.)

- Data: `data/fnd/<dataset>/` (raw fidelity) and `data/gold/` (label maps, thresholds) — read-only.
- Colour convention: the five canonical appliances keep one colour across every chart in every notebook; everything else renders in neutral greys.

*Each notebook ends with its own quirks list and a machine-readable summary block; the notebooks are the per-claim source of every number above.*
