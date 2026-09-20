# Experiment Data Strategy -- UK-DALE as substrate, EDA as gate, the loop as demo

**Date:** session of Request W. **Question set:** (1) can UK-DALE replace the synthesized data for experiments, given the brief and our problem/product phrasing; (2) are Figures 1-4 from the visual reading a good EDA skeleton, and can we have a rigorous EDA script ready for real data; (3) does the anomaly-detection-on-unknown-bucket framing require data collection, or can we demo without it; (4) what do we actually have from the existing repo.

**New artifacts (this document's siblings):**
- `eda_shelly.py` -- the EDA battery + domain-shift judge, syntax-checked and run end-to-end twice.
- `eda_reference_ukdale.json` -- the UK-DALE reference metrics it was calibrated on.
- Demo outputs: `eda_runs/ukdale_reference/`, `eda_runs/synthetic_vs_reference/` (report.md, metrics.json, 4 figures each).

---

## 0. Short answers

1. **Yes -- UK-DALE is the right experimental substrate, in three tiers.** The synthetic CSV survives only as a unit-test fixture. UK-DALE full + a Shelly-emulation degradation layer becomes the integration substrate; the live Shelly is the acceptance test. The local slice's aggregate is `custom_aggregate` (no real mains), but it carries a **14.5% unlabeled-energy bucket** (306.0 kWh aggregate vs 261.8 kWh across the 5 labeled channels) -- so even the slice exercises the UNKNOWN problem, and the full UK-DALE house-1 download adds the true mains residual.
2. **Figures 1-4 are the right skeleton, but EDA must be scripted, not eyeballed.** The four figures map to a metrics battery (sampling ladder; temporal staircase/week; event statistics). `eda_shelly.py` implements the battery, emits fig01-04 analogues from any input, and judges every metric against the stored UK-DALE reference with PASS/FLAG verdicts. Running it on the synthetic CSV flags **5 of 10 axes** -- that is the domain shift, quantified.
3. **The loop's mechanics are demoable without collecting anything; its claims are not.** Demo now: real residual (mains minus submeters), novelty detection on it, injected new-device events on real baselines, self-dogfooding with one Shelly on your own flat. Only retention, precision-at-scale, and question-acceptance claims need a field pilot. Synthesize events on real baselines, never humans.
4. **From the repo: the shell, not the science -- and that is now partly fixed.** The repo gives a persistence layer (Next.js + Supabase), a schema, four trivial ETL scripts, and one flawed fixture. It contains no disaggregation, no event detection, no evaluation, no EDA, no real data. What the *conversation* produced is the research program (see section 4). And as of today the first executable code exists: the EDA script.

---

## 1. Q1 -- UK-DALE instead of synthesized data: the three-tier strategy

### Tier A -- synthetic CSV: unit-test fixture (nothing more)

Our repo-review verdict stands: single simulated day replayed 30 times, derived-by-arithmetic columns, perfect labels, 1.71% simultaneity, no unknown loads, white-noise frequency. Its remaining value is exactly the one a unit test has: deterministic input to check that plumbing (ETL, storage, the EDA script itself) does not crash and produces columns in the right shape. **Any feasibility conclusion drawn from it is void** -- that verdict is unchanged.

### Tier B -- UK-DALE + Shelly-emulation layer: the integration substrate

UK-DALE (Kelly & Knowlton, 2015) supplies what the synthetic generator omitted, on real physics: unknown loads (14.5% of the slice aggregate already), 32.7% two-plus-simultaneous-ON, a 1.0 W quiet-regime noise floor, real weekday/weekend structure, and ground-truth submeters for five appliances.

To make it *Shelly-shaped*, degrade it through fixed rungs (each rung is a check-in-able transform):

| Rung | Transform | What it emulates |
|---|---|---|
| R0 | native 6 s | UK-DALE as released |
| R1 | resample 6 -> 60 s | ESPHome `ade7953` default 60 s |
| R2 | resample 60 -> 300 s | `EMData.GetData` minimum period (300 s) |
| R3 | 30 VA floor + +/-5% noise above ~230 W | ADE7953 front-end + calibration doc's minimum-power clause |
| R4 | quantize into the history buckets (300/900/1800/3600 s) | what the app can actually read back |

The experiment matrix is then: does each stage of the borrowing stack (analog-problems.md section 4: threshold -> hysteresis -> factorial HMM -> calibration ritual) survive each rung? The degradation layer is ~50 lines of pandas; it is the cheapest way to know the sampling-rate answer *before* the hardware ships.

**Caveats, stated plainly:**
- One UK home, 2012-2015, 230 V UK plug culture. Vietnamese 220 V homes differ (no UK-style storage heaters, different fridge duty). UK-DALE calibrates the *method*, not the *market*.
- The local slice is UK-DALE **house-5** data (four channels verbatim: fridge_freezer, dishwasher, kettle, i7_desktop) relabeled house_1-style; its channel 1 is a synthetic aggregate = the sum of channels 2-6 plus a flat injected base (about 27 W, std 7.4 W), **not** any house's mains. The 14.5% reconciliation gap below is that injected base, not unmonitored household load. The full UK-DALE house-1 download (mains.dat) supplies the true aggregate for residual work. Provenance forensics 2026-09-21; authoritative house-1 numbers: `docs/reports/dataset_eda/01_ukdale_eda_review.md`.
- Reconciliation check (run this session): aggregate 306.0 kWh vs channels 2-6 sum 261.8 kWh over 70.66 days -> ratio 1.169. Corrected 2026-09-21: the 14.5% gap is the synthetic aggregate's injected flat base (a constant about 27 W), not a household "unknown bucket" - do not quote it as residual-size evidence.

### Tier C -- live Shelly: acceptance test and dogfood rig

The rate experiment (nilm-visual-reading.md section 10) is still the cheapest, highest-value live action: one Shelly EM Gen3, one weekend, answers the 300-vs-60 s question on real hardware. It is also the beginning of dogfooding (section 3).

---

## 2. Q2 -- Figures 1-4 as the EDA skeleton, made rigorous

### The mapping

| Figure (nilm-visual-reading.md) | What it shows | EDA metric in the script |
|---|---|---|
| Fig 1 -- resolution ladder | what you can see depends on sampling | dt stats, gaps, native-vs-60s-vs-300s ladder figure |
| Fig 2 -- poster week | staircase, duty, weekly rhythm | span, duty, weekday/weekend, lag-1day autocorr, week figure |
| Fig 3 -- one day zoom | appliance cycles unrolled | hourly profile, peak/trough, overlap, day figure with appliance overlay |
| Fig 4 -- event view | step sizes, durations, overlaps | steps/day at 30/100/300 W, noise floor, per-appliance transition ECDF, ON-duration ECDF, events/day |

### What "rigorous" adds beyond the figures

Pictures cannot certify domain shift; stored numbers with verdict bands can. The script computes a fixed battery (sampling, power, steps, diurnal, per-appliance, simultaneity), and -- when given `--reference` -- compares each metric against the UK-DALE reference with explicit ratio bands, plus a Population Stability Index on the 24-hour profile (<0.1 none, 0.1-0.25 moderate, >0.25 major; the credit-scoring convention).

### The calibration run (already done, end-to-end)

Reference built on the UK-DALE slice; then the synthetic CSV was judged against it:

| metric | synthetic | UK-DALE ref | ratio | verdict |
|---|---|---|---|---|
| dt median (s) | 5.0 | 6.0 | 0.83 | FLAG |
| steps/day >30 W | 4290.5 | 715.0 | 6.0 | FLAG |
| steps/day >300 W | 22.0 | 22.9 | 0.96 | PASS |
| noise floor (W) | 14.6 | 1.0 | 14.6 | FLAG |
| 2+ appliances ON (%) | 1.7 | 32.7 | 0.05 | FLAG |
| diurnal profile PSI | 12.09 | 0.000 | -- | FLAG |
| mean power / always-on / lag-1day / span | -- | -- | 0.4-4.3 | PASS |

Read: the synthetic data fails exactly where our manual review said it would -- event texture (6x the step count, because the base random-walks ~15 W per step against a 1 W real noise floor), simultaneity (19x under-represented), and daily shape (PSI 12). It passes on gross energy and on large events -- which is why it *looks* fine in a plot and fails in a battery.

The reference also reproduces every number we had established by hand: monitor duty 82.1%, monitor median-ON 111 W, kettle median-ON 2890 W, fridge duty 36.5%, 715 steps/day above 30 W.

### What happens when the real Shelly CSV arrives

Three commands, nothing else:

```
# once, reference already built:
python3 eda_shelly.py ukdale --make-reference --out eda_runs/ukdale_reference
# when real data lands:
python3 eda_shelly.py shelly_export.csv --reference eda_reference_ukdale.json --out eda_runs/real_shelly
```

Expect on a 300 s Shelly feed: dt FLAG (by design -- that is the rate question answered in numbers), noise floor likely between the synthetic 14.6 W and UK-DALE's 1.0 W, and the simultaneity/PSI verdicts becoming the real household's fingerprint. The script is deliberately label-free (recomputes ON states from power), rate-agnostic, and needs only pandas + numpy + matplotlib.

Event detection in v1 is thresholds + run-length encoding; the production upgrade path is PELT via `ruptures` (analog-problems.md section 2.5) -- EDA does not need it, judging domain shift does not either.

---

## 3. Q3 -- does the anomaly-to-question loop need data collection?

**Split the loop into mechanics and claims.**

| Layer | What it asserts | What it needs | Demoable now? |
|---|---|---|---|
| M1 residual monitor | aggregate minus named = unknown bucket | full UK-DALE mains (download) or the slice's 14.5% bucket | yes |
| M2 novelty detection | event-visible steps (threshold/hysteresis); baseline shifts (integration-beats-noise) | same | yes |
| M3 classify-before-ask | new device vs fault vs seasonal vs behavioral | templates + dwell statistics (kettle 240 s vs heater 1800 s) | yes, on UK-DALE events |
| M4 the question loop | one open question, rate-limited, learned-from | a UI + one human (you) | yes, dogfooded |
| C1 precision of novelty flags | false-positive rate per household-month | weeks of real per-home data | no -- pilot |
| C2 retention/behavior change | insight-to-action decay (1.9-3.9% in 4 weeks) | months, many homes | no -- pilot |
| C3 question acceptance rate | users answer, do not churn | live users | no -- pilot |

**The demo design (no collection):** run M1-M3 on the UK-DALE residual with injected anomalies -- take the real 70.66-day baseline, inject N synthetic new-device events (a 10 W router appearing, a 2100 W heater with 1800 s dwell) into the *unlabeled bucket*, and measure detection latency, classification correctness, and question-trigger rate. This is the legitimate use of synthesis: **synthesize events on real baselines, never humans.**

**The ambient-nature concession is real and should be conceded, not fought:** the loop's value claims live on timescales of weeks and require the device to be installed and forgotten. That is exactly why the demo scope is mechanism-only, and why the pilot (1-3 homes, 4-8 weeks, your own home first) is the *second* milestone, not the first.

Dogfooding note: one Shelly on your own flat gives M4 (and C1 at n=1) almost immediately -- you are the least expensive user and the most forgiving.

---

## 4. Q4 -- honest inventory: what exists, what does not

### From the repo (`repo/WattWiser/`, 31 files, one commit)

| Asset | What it is worth |
|---|---|
| `data/raw/synthetic_shelly_data.csv` (49 MB, 518,400 rows, 5 s, 16 cols) | schema template + unit-test fixture; void as evidence |
| `pipeline/processing/` inspect/process/validate/check_relationships | arithmetic ETL (VA=V*I, PF, diffs); reusable skeleton, nothing scientific |
| `pipeline/features/create_features.py` | time-of-day, rolling stats; fine plumbing, no detector |
| `backend/` Next.js 16 + Supabase (4 API routes) | the persistence shell; genuinely reusable |
| absent | disaggregation, event detection, baseline estimation, evaluation, train/test split, EDA, real-data ingestion, feedback loop, unknown handling |

### From this conversation (the part that is not starting from zero)

| Asset | File |
|---|---|
| Feasibility verdict chain (detectability vs materiality, 30 VA floor, stage ladder) | feasibility-verdicts.md, use-case-reassessment.md |
| Dataset forensics (UK-DALE + synthetic, reproducible) | dataset-walkthrough.md, repo-review.md + repo-analysis scripts |
| The borrowing stack (9 analog fields, what transfers) | analog-problems.md |
| The loop-is-the-product reframe + KPI shift + energy tables | product-core-reframe.md |
| Figure semantics + what each view can and cannot show | nilm-visual-reading.md + figures/ |
| **Executable EDA + domain-shift battery, calibrated on the UK-DALE slice (house_5-derived - see caveat 1)** | **eda_shelly.py + eda_reference_ukdale.json (new today)** |

**Verdict:** if "from zero" means lines of algorithm code, yes -- the repo contributes none, and today's script is the first executable piece. If it means the research program, no: the problem is formalized, the data strategy is tiered, the evaluation metrics are named, the first executable artifact exists, and the next three code steps are specified (Shelly-emulator rungs; residual monitor; threshold+hysteresis detector). The gap is engineering hours, not direction.

---

## Appendix -- validation numbers from today's runs

- UK-DALE slice: 985,855 rows, 70.66 days, dt 6.0 s, steps/day >30 W = 715.0, 2+ ON = 32.7%; appliance table reproduces monitor duty 82.1% / median-ON 111 W, kettle 2890 W / step 2878 W, fridge duty 36.5% (slice is house_5-derived under house_1-style labels - see the caveat in section 1; "monitor" = h5 i7_desktop).
- Synthetic: 518,400 rows, 30.00 days, dt 5.0 s, steps/day >30 W = 4290.5, 2+ ON = 1.7%, noise floor 14.6 W.
- Reconciliation: aggregate 306.0 kWh vs submeters 261.8 kWh (ratio 1.169) over the common window; the 14.5% gap is the synthetic aggregate's injected flat base, not unlabeled household load.
- Figures emitted per run: eda_fig01_ladder.png (three-rate ladder), eda_fig02_week.png, eda_fig03_day.png (appliances overlaid), eda_fig04_events.png (steps / hourly profile / transition ECDF / duration ECDF).
