# Baseline experiment plan: UK-DALE as calibration substrate

**Status:** plan, not yet implemented. **Read alongside:** `experiment-data-strategy.md` (three-tier data plan),
`feasibility-verdicts.md` (verdict chain), `product-core-reframe.md` (the loop), `dataset-walkthrough.md`
(data caveats). This doc turns the calibration-mimicry idea into an executable experiment spec, and every
design choice below traces to a specific earlier finding (see the grounding table in 0.1).

> **Provenance correction 2026-09-21:** the "UK-DALE house-1 slice" this plan built on
> (`research-logs/sakunrasilka_nilm-test2/`) is house-5 data relabeled house_1-style
> (channels 2/3/4/6 = h5 fridge_freezer / dishwasher / kettle / i7_desktop, byte-exact;
> channel 1 = sum of channels + flat about-27 W base, synthetic; channel 5 unmatched).
> Every slice stat below (715 steps/day, 32.7% 2+ ON, noise floor 1.0 W, fridge 36.6%,
> kettle 2890 W, monitor 49.3% / 80-82% duty, ratio 1.167) describes house 5, not
> house 1. Authoritative UK-DALE numbers: `docs/reports/dataset_eda/01_ukdale_eda_review.md`.
> Body kept unmodified per the quarantine status; read every "house-1" mention with
> this correction.

## 0. Short answers

- **What we build:** the v1 NILM baseline on the UK-DALE house-1 slice - a rules-based episode detector
  (threshold + hysteresis + dwell) plus an evaluation harness, structured as a *calibration experiment*.
- **The one experiment that matters:** a calibration learning curve - calibrate each appliance from N episodes
  (N = 1, 2, 5, 10, 20, all) and plot episode precision/recall vs N. This answers, empirically, "how long must
  the client's real calibration session be?" - the question their calibration process exists to answer. It also
  stress-tests their calibration script's stated floor ("minimum power allowed ... 500 W"): fridge-class loads
  sit far below that line, so the curve tells us whether such a floor silently excludes whole device classes.
- **What baseline means here:** the floor every future model must beat. No neural nets in v1; deep models are
  documented as an upgrade path only.
- **Deliverable:** per-appliance episode precision/recall + onset/offset timing error + energy attribution,
  at three sampling rungs (6 / 60 / 300 s), plus the learning curve, a confusability matrix, and a rehearsed
  anomaly-loop demo on the real residual.
- **Explicitly out of scope (v1):** whole-home disaggregation (FHMM, seq2seq), always-on / standby loads,
  sub-30 W detection, multi-house generalization, V-I waveform methods (separate hardware track).

- **Literature position (9):** every component of this design exists in published NILM work; what the
  experiment claims is calibration economics + honest reporting + the loop demo, not method novelty.

### 0.1 Grounding: every choice traces to prior research

| Design choice in this doc | Grounded in |
|---|---|
| Feasible set only; no whole-home / standby / <30 W / multi-state promises | `feasibility-verdicts.md` verdict chain |
| Monitor as negative control + energy-share-weighted reporting | detectability-vs-materiality finding (`dataset-walkthrough.md`) |
| Rungs 6 / 60 / 300 s, 30 VA floor, +/-5% noise | tier-2 emulator (`experiment-data-strategy.md` 1) |
| Calibration learning curve | the calibration-mimicry discussion + client calibration doc floor (500 W) |
| UNKNOWN bucket, residual-honesty metric | `product-core-reframe.md` (loop is the product) |
| Anomaly-loop rehearsal run (R6) | demo-vs-claims split (`experiment-data-strategy.md` 3): mechanics demoable now, "synthesize events on real baselines, never humans" |
| Reuse of EDA loaders/primitives + domain-shift judge | `eda_shelly.py` + `eda_reference_ukdale.json` (no forking) |
| Why not the client's synthetic CSV | `repo-review.md` + `dataset-walkthrough.md`: 1 day replayed 30x, noise floor 14.6 W vs 1.0 W, 4,290 steps/day vs 715 - unusable as substrate |
| UK-DALE as tier-2 substrate; live Shelly stays tier-3 acceptance | `experiment-data-strategy.md` 1 |
| Learning curve = passive floor; active querying is the loop variant | `research-logs/training-approaches.md`: 7 active-learning papers; optimum accuracy-labeling trade-off at 5-15% of pool labeled (doi:10.1016/j.apenergy.2023.121078) |
| Rung expectations and the 60 s cliff | `research-logs/low-frequency-nilm.md`: four granularity regimes; winning results below 10 s; at 15-60 min "most NILM methods ineffective" |
| Dwell rules + dwell-ratio matching | `analog-problems.md` 2.3 (patch-clamp dwell-time kinetics as priors) + duration/switching priors, Kim et al. SDM 2011 |
| Monitor class: baseline subtraction, never event detection | IEEE ISGT 2019 mild-day method (doi:10.1109/isgt.2019.8791578) - attribute categories, not events, at coarse rates |
| Residual to UNKNOWN, alarm instead of assign | spike sorting / EMG decomposition (analog-problems.md 2.7) |
| Optional cycling-load scan (fridge period/duty) | BLS box-function search from exoplanet transits (analog-problems.md 2.6) |

## 1. Input

- **Data:** UK-DALE house-1 slice at `research-logs/sakunrasilka_nilm-test2/` -
  `channel_1.dat` = custom aggregate, `channel_2..6.dat` = appliance submeters, `labels.dat` maps them
  (1 custom_aggregate, 2 fridge, 3 dish_washer, 4 kettle, 5 washing_machine, 6 monitor).
  Text format: space-separated `epoch_seconds watts`, 6 s sampling; loader already exists in `eda_shelly.py`.
- **Slice stats (measured):** 985,855 rows / 70.66 days / 6.0 s; 715 steps/day > 30 W; 2+ appliances ON
  simultaneously 32.7% of the time; aggregate noise floor ~1.0 W.
- **Appliance set with materiality** (energy shares computed on this slice; submeters sum to 275.1 kWh,
  aggregate 321.1 kWh, ratio 1.167):

  | Ch | Appliance | Energy share | Episodes (>5 W, 12 s merge) | Windows (10-min merge) | Duty | Role |
  |---|---|---|---|---|---|---|
  | 2 | fridge | 25.6% (70.3 kWh) | 2,054 | 1,792 | 36.6% | cyclic, easy; the volume test case |
  | 4 | kettle | 7.5% (20.7 kWh) | 195 | 188 | 0.4% | binary, trivial at 6 s; median-ON 2,890 W, step 2,878 W, dwell ~240 s |
  | 5 | washing_machine | 7.4% (20.3 kWh) | 83 | 65 | 1.4% | multi-state, hard; program phases |
  | 3 | dish_washer | 10.2% (28.0 kWh) | 176 | 61 | 2.3% | multi-state, hard; lower power |
  | 6 | monitor | **49.3% (135.7 kWh)** | 31 | 31 | 80-82% | negative control; the materiality mirror |
  | 1 | aggregate | 321.1 kWh | - | - | - | deployment signal; ~14.3-14.5% unlabeled mass |

  The monitor row is the engagement's thesis in one line: the **largest** submeter load by energy is nearly
  undetectable by episode methods (no step, no clean episodes) - so the baseline must report per-appliance
  materiality next to accuracy, and the product answer for monitor-class load is the always-on/UNKNOWN bucket,
  not detection.
- **Temporal split:** calibration = first 40 days; test = final ~30.7 days. Never calibrate and test on the
  same episode; never shuffle across time. With the counts above, N = 20 calibration episodes is available for
  every target appliance even in the washer class (~1 window/day).
- **Citation:** UK-DALE (Kelly & Knottenbelt, Scientific Data 2015) and Neural NILM (arXiv 1507.06594) are
  already verified in `research-brief.md`. Hart 1992 (event-based NILM) remains flagged memory-cited.

## 2. Calibration mimicry (the framing being tested)

The client's calibration process: run each device alone at known settings, record, derive a signature, deploy.
In UK-DALE this maps to:

- appliance channel = a **perfect calibration recording** (what calibration would ideally produce);
- aggregate channel = the **deployment signal** (what the meter actually sees, co-occurrence and noise included);
- held-out test period = **post-calibration deployment**.

Three questions this framing answers that the client's docs currently only assert:

1. How many episodes does calibration need (learning curve) - converts "calibrate a bit" into a measured
   session length. Prediction to verify: fridge saturates almost immediately (abundant episodes), washer
   keeps improving longest (83 episodes / 70 days).
2. Does a calibration floor (their "minimum power allowed ... 500 W") hide fridge-class appliances? The fridge
   learning curve is computed from the full submeter trace; a 500 W-capped version is run as an ablation
   (R4) and the recall gap is the answer.
3. Do signatures survive the deployment sampling rate (60 s) and the 30 VA floor? Rung runs answer this
   before any Shelly is installed.

A fourth, from the literature: the N-curve above is the **passive** calibration curve (episodes taken as
they come). Active-learning results say active selection beats it - the Applied Energy 2023 study reaches
its optimum with only 5-15% of the query pool labeled, and the active deep learning work cuts samples 33%
at equal F1 (doi:10.1109/access.2020.3003778). The product loop's open-question mechanism is exactly the
active-query instantiation - so the measured gap between the passive curve (R3) and what an actively
chosen episode order would buy is the loop's quantified value.

## 3. Data processing & feature engineering

### 3.1 Loading and alignment

- Loader (exists): `np.loadtxt(path, ndmin=2)`; epoch seconds to index; all 6 channels on one 6 s grid;
  truncate to common time span. No resampling at R1.

### 3.2 Episode extraction (calibration side, from device channels)

- ON mask per appliance: power > `max(5.0, 0.02 * p95)` (the EDA floor rule); for cyclic loads additionally a
  relative threshold (e.g. 0.5 x median-ON) since compressor levels drift.
- Run-length encode into episodes `(start, end, mean, p90, min, dwell)`; merge gaps shorter than `gap_tol`
  (default 2 samples = 12 s; fridge compressors drop out briefly); drop episodes below `min_dwell` (default 12 s).
- **Activity windows** for multi-state loads: second gap-merge at 10 min (100 samples) collapses program phases;
  measured counts above (washer 83 episodes -> 65 windows).
- **Signature per appliance**: ON-power median + IQR; transition step (mean ON level minus 30 s pre-window
  baseline); dwell p10/p50/p90; rise time; OFF-state level. Example (measured): kettle 2,890 W median-ON,
  2,878 W step, ~240 s dwell - vs heater-class loads at ~1,800 s dwell, the key disambiguator (F2). Dwell
  enters as a *fitted prior* (p10/p50/p90), not a free parameter - the patch-clamp kinetics borrowing
  (analog-problems.md 2.3); duration and switching priors at low rate are literature-standard (Kim et al.,
  SDM 2011).

### 3.3 Aggregate conditioning (deployment side)

- Always-on floor = median of daily p10 (the EDA always-on metric); subtract before thresholding, or use as the
  hysteresis lower threshold.
- Optional rolling median (k samples) ahead of thresholding; keep raw for step features.
- The residual after subtracting all attributed detections is the **UNKNOWN stream** - the same object the
  product loop consumes. R6 rehearses the anomaly loop on it.

### 3.4 Degradation rungs (emulating the Shelly)

- Rung transforms on aggregate **and** submeters identically: mean-bucket resample via integer floor-divide on
  timestamps (6 -> 60 -> 300 s; no `resample()` - version-fragile, per the EDA fix), plus a max-bucket variant
  to mimic history-API bucketing; +/-5% multiplicative noise on levels above ~230 W; 30 VA measurement floor.
- Rationale: the client's ESPHome config samples at 60 s by default; rung results = what deployment will
  see. Literature frame: 6 s sits in the field's usable band (1-10 s, where event detection is strongest),
  60 s in the awkward middle the review finds weakest, 300 s approaching the utility band where "most NILM
  methods [are] ineffective" (doi:10.3390/en14092390; doi:10.1109/isgt.2019.8791578). The rungs therefore
  measure exactly where the cliff is - per appliance, which no review reports.

### 3.5 Features per candidate episode (detection side, aggregate)

`step` (level jump at onset), `mean_level`, `dwell`, `rise_time`, `post_offset_dwell`, `time_of_day` (optional,
for priors), `local_baseline`. Cheap, explainable, survive resampling - deliberately not learned embeddings;
the product needs an explainable detector.

## 4. Problem framings & models

| Framing | Question asked | Model | Verdict for v1 |
|---|---|---|---|
| F1: per-appliance binary episode detection | "Is appliance k ON in this window?" | M0: threshold + hysteresis + dwell rules from the signature | **v1 primary** |
| F2: event-then-classify | "Something turned on - which?" | M1: match (step, dwell, level) against all signatures; nearest-signature with margin | v1 secondary; yields the confusability matrix |
| F3: supervised onset classifier | per-candidate-step labeling | logistic / GBM on the 3.5 features | optional stretch; sklearn absent -> hand-rolled numpy logistic; likely unnecessary |
| F4: joint disaggregation | "split mains into all appliances" | FHMM (per-appliance 2-state HMM + Viterbi), seq2seq NN | **out of scope** - 70 d / 1 house / 5 labeled appliances cannot support it; documented upgrade path |

- M0 is deliberately dumb: the baseline the client can understand, reproduce, and defend. It is also the
  tier-2 substrate piece: the same detector code later runs on synthetic fixtures (tier 1 unit tests) and on
  live Shelly output (tier 3 acceptance).
- M1 conflict rule: overlapping detections on aggregate may coexist if predicted levels sum ~ observed;
  otherwise keep the higher-energy one and leave the remainder to the UNKNOWN bucket (the product's residual
  honesty, rehearsed early). The residual-to-UNKNOWN-then-alarm pattern is spike sorting's unknown-cluster
  handling (analog-problems.md 2.7); a BLS-style periodicity scan (2.6) remains available for the cycling
  side (fridge period/duty) if the episode framing misses it.
- Kettle-vs-heater style confusions are resolved by dwell, not level (240 s vs 1,800 s) - measured in R4.
- PELT / `ruptures` change-point detection stays an upgrade path (library not installed).

## 5. Metrics (the part that decides whether this means anything)

### 5.1 Unit of evaluation: the episode, never the sample

Point-wise accuracy is **rejected**: always-on loads make it a lie - a detector that predicts "monitor ON"
always scores ~80%+ on the monitor channel (duty ~82%) while detecting nothing. All headline metrics are
episode-level. Every per-appliance metric is reported next to its **energy share** (1), so the reader sees
what each number is worth: a perfect kettle detector is worth 7.5% of submeter energy; the monitor's 49.3%
share is intentionally NOT won by the baseline - it is handled by the always-on/UNKNOWN design, and saying so
outright is part of the deliverable.

### 5.2 Matching rule (fixed before any run)

Greedy one-to-one matching, sorted by onset: a predicted episode matches a GT episode iff
`|onset_pred - onset_gt| <= tol` and `0.5 <= dwell_pred / dwell_gt <= 2.0`, with `tol = max(2 x dt, rung interval)`
(12 s at 6 s; 120 s at 60 s; 600 s at 300 s). Each GT episode matches at most one prediction, and vice versa.

### 5.3 Headline metrics (per appliance, per rung)

| Metric | Definition | Why |
|---|---|---|
| Precision (ep) | matched predictions / all predictions | false-alarm control |
| Recall (ep) | matched GT / all GT episodes | detection coverage |
| F1 (ep) | harmonic mean; with support count n | headline table cell |
| Onset error | median abs(onset_pred - onset_gt), seconds | user-facing timing ("kettle started at 7:02") |
| Offset error | median abs(offset_pred - offset_gt), s | dwell accuracy |
| Energy attribution | matched detected energy / GT appliance energy in test period | the loop's attribution-coverage KPI |
| Confusability | per (predicted appliance, true appliance) cross-count | kettle-vs-heater class errors made visible |
| Residual honesty | aggregate test energy left unattributed (%) | mirrors the UNKNOWN bucket; sanity vs the ~14.3-14.5% unlabeled mass |
| Materiality | energy share column, always printed beside P/R | prevents optimizing trivia |

### 5.4 Negative control

The monitor channel is run through the same pipeline and must produce ~zero episode detections; any detector
logic that "finds" the monitor is fit to noise and is rejected before looking at anything else.

### 5.5 Calibration learning curve (the deliverable metric)

F1 and recall vs N calibration episodes (N = 1, 2, 5, 10, 20, all), per appliance, at 6 s and 60 s. The knee of
this curve = recommended length of the client's calibration session, in minutes of runtime per appliance.

### 5.6 Proposed pass gates (set on calibration-period data, then frozen for the test period)

| Appliance | Gate @ 6 s | Gate @ 60 s |
|---|---|---|
| kettle | P >= 0.95, R >= 0.90 | P >= 0.90, R >= 0.80 |
| fridge | P, R >= 0.85 | P, R >= 0.70 |
| washing_machine | R >= 0.70 (activity-window level) | R >= 0.60 |
| dish_washer | R >= 0.60 | no gate (report only) |
| monitor | ~0 detections (negative control) | same |

If the fridge fails its 60 s gate, the client's 60 s default becomes an explicit risk item, not an assumption.

## 6. Run matrix

| Run | What | Output |
|---|---|---|
| R1 | M0 @ 6 s, all appliances, full test period | baseline table (the anchor) |
| R2 | rungs 60 s, 300 s (+ max-bucket variant) | survival table per appliance |
| R3 | learning curve over N calibration episodes (+ 500 W-floor variant) | calibration-session-length answer; calibration-floor verdict |
| R4 | confusability matrix + dwell-rule ablation (with/without dwell filter) | which rules carry the accuracy |
| R5 (stretch) | +/-5% noise + 30 VA floor on top of 60 s | robustness under measurement error |
| R6 | anomaly-loop rehearsal: take the R1 residual/UNKNOWN stream, inject synthetic anomaly events (known shapes), run classify -> open-question mechanics | the demoable-now loop demo, no humans involved |

Artifacts: `baseline_ukdale.py` (CLI, mirroring the `eda_shelly.py` twin pattern) + `baseline_runs/` with
`report.md` + `metrics.json` per run. Reuse the EDA loaders and primitives; do not fork them. When the real
Shelly feed arrives, the existing domain-shift judge (`eda_shelly.py` vs `eda_reference_ukdale.json`) gates
whether baseline conclusions transfer - PASS/FLAG bands are already defined there.

## 7. Pitfalls & honesty

- `custom_aggregate` is not the exact sum of submeters (~14.3-14.5% unlabeled energy, ratio 1.167) - the
  aggregate always carries an UNKNOWN mass; detectors must be allowed to miss it, and the residual-honesty
  metric keeps this visible.
- Single house, UK 2012-15 market and appliance stock - signatures transfer imperfectly to the client's home;
  this is a substrate for method validation, not a ground truth for their deployment. The domain-shift judge
  is the formal gate.
- Washer / dishwasher are multi-state: evaluate at the **activity-window** level (union of phases), not per phase.
- Fridge defrost cycles create long low-power troughs - expect false OFFs; check against labels before tuning.
- Co-occurrence contamination: signatures come from clean submeters, but thresholds apply to contaminated
  aggregates (2+ ON 32.7% of the time) - the hysteresis band and local baseline exist to absorb exactly this.
- **What this baseline does NOT prove:** retention curves, precision at multi-home scale, question-acceptance
  rates - those are pilot-tier claims (1-3 homes, 4-8 weeks) per the demo-vs-claims split. The baseline proves
  mechanics and calibration economics only.
- V-I trajectory work stays on its own hardware track (`vi-trajectory-hardware.md`); no waveform features in v1.
- Never report point-wise accuracy (5.1); never tune on the test period; no random windows.
- Literature honesty: every component of this design is published (33 transfer, 7 active-learning, 4 few-shot,
  20 federated NILM papers harvested and verified - `research-logs/training-approaches.md`). The baseline
  claims calibration economics and mechanics, not novelty; the loop/product framing is where the novelty
  question lives (`product-core-reframe.md`, 9.3).

## 8. Environment

- Available (uv-tracked, `pyproject.toml` + `uv.lock`): numpy, pandas, scipy, matplotlib (Agg; `MPLCONFIGDIR=/tmp/mplcfg`). Run with `uv run python3`.
- Not installed (do not assume): sklearn, ruptures, statsmodels, hmmlearn, jupyter. M3 stays hand-rolled-only
  and deferred; PELT upgrade requires installing `ruptures` first.

## 9. Prior research this baseline stands on

### 9.1 NILM literature (verified in the research notes)

| Line | Work (verified) | What it reports | What this baseline does with it |
|---|---|---|---|
| Event-based NILM | Hart 1992 (canonical; flagged memory-cited) | changepoint + steady-state clustering; still the field baseline | M0 is this lineage, deliberately |
| Low-frequency regimes | Energies 2021 review, doi:10.3390/en14092390 (124 cites) | best results cluster below 10 s; the field is unsettled at 1 min | the rungs (6/60/300 s) measure the cliff per appliance |
| Very low-rate solutions | Applied Energy 2020, doi:10.1016/j.apenergy.2020.114949 | disaggregation methods targeted at very low-rate smart meter data | the 60/300 s rungs sit exactly in this regime - expectations must be lowered there (cited-on-title; read fully before relying on specifics) |
| Coarse-data honesty | IEEE ISGT 2019, doi:10.1109/isgt.2019.8791578 | at 15-60 min "most NILM methods ineffective"; substitutes category attribution via baseline subtraction | monitor-class load: baseline subtraction + UNKNOWN, never event detection |
| Transfer / calibration | IEEE TSG 2019, doi:10.1109/tsg.2019.2938068 (327 cites) | similar domains need no fine-tuning; different domains only FC layers | the calibration ritual is narrower than assumed - R3 quantifies what signatures alone buy |
| Active learning | Applied Energy 2023, doi:10.1016/j.apenergy.2023.121078 (67 cites) | optimum accuracy-labeling trade-off at 5-15% of pool labeled; 2^13-sample start ("small time-diary") | the learning curve is the passive version; the loop's open-question is the active version - the gap is loop value |
| Active (deep) selection | IEEE Access 2020, doi:10.1109/access.2020.3003778 (53 cites) | 33% fewer samples at equal F1 | upper bound for the active variant |
| User feedback | 2019, doi:10.1109/cccs.2019.8888140 | model selection driven by user confirmation of correctness | the loop's user-confirmation step, literature-endorsed |
| Unknown rejection | IEEE Access 2022, doi:10.1109/access.2022.3145982 (42 cites) | feature library grows dynamically; unknown loads identified by addition | the UNKNOWN bucket + codebook design |
| Training-less | IEEE Access 2016, doi:10.1109/access.2016.2557460 (215 cites) | graph signal processing, no training | the extreme "no calibration" end of the axis; noted, not adopted |
| Self-supervised | IEEE TIM 2023, doi:10.1109/tim.2023.3246504 (43 cites) | target-house labels not required | alternative to calibration; upgrade path if the learning curve disappoints |
| Online household learning | (finding, `training-approaches.md`) | genuinely online household NILM is thin; online work is feeder-scale | the loop runs on batch episodes, not online weight updates |

### 9.2 Adjacent fields (analog-problems.md): how separation is done elsewhere

| Field | Instance | Borrowed here |
|---|---|---|
| Patch-clamp ion channels | one noisy scalar, discrete hidden states - solved in the 1980s | dwell-time distributions as fitted priors (3.2, 5.2) |
| Changepoint statistics | mature detection discipline | PELT/BOCPD = the upgrade path for candidate events |
| Exoplanet transits | "find box functions in a noisy series" (BLS) | optional fridge/HVAC periodicity and duty-cycle scan |
| Spike sorting / EMG | additive superposition of repeated templates | residual -> UNKNOWN cluster; alarm instead of assign |
| Single-channel speech separation | same shape, harder instance; classical methods near-hopeless pre-2015, deep nets won on data + compute | the honest lesson: at this data scale stay classical; seq2point only if data grows |
| Factorial HMMs | NILM's own formalization (Kolter & Jaakkola 2012) | exact at K <= 4 (16 joint states) - F4 upgrade path |
| Water end-use disaggregation | the direct sibling domain | shared evaluation conventions, same co-occurrence traps |

Speech separation is the closest and the most instructive: it is the harder instance of the same input
shape, and its pre-2015 classical toolset failed the way this baseline would at low data scale - the
field moved when data and compute arrived, not when someone found a better rule. That is why M3/F4 are
upgrade paths tied to data scale, and why the v1 baseline does not apologize for being rules.

### 9.3 The one-sentence position

Everything in this doc is literature-known; the defensible claims are (a) measured calibration economics
for this deployment, (b) the negative-control + materiality reporting discipline, and (c) the loop demo
(R6) - novelty lives in the product framing, not in any single component.

## 10. Multi-household extension (what more data buys)

**Slice inventory correction (checked 2026-09-18):** the local UK-DALE is **not** the full dataset. It is
house 1 only, 6 of the house's 53 labeled channels, spanning 2014-06-30 23:59 UTC -> 2014-09-12, and every
channel is truncated at 2^20 = 1,048,576 rows (an upstream export cap; channel_4 shorter at 985,854). The
full 2017 release adds houses 2-5, the full house-1 span (2013-2017), and the 53-channel label set.
Consequences: more calibration episodes per appliance, longer test spans, and cross-house tests. When the
full download lands, rebuild `eda_reference_ukdale.json` and re-run R1-R5 - rung logic unchanged, expect
number shifts with the same shape.

### 10.1 Datasets that convert to the UK-DALE shape (aggregate + submeters)

| Dataset | Local copy | Homes | Rate | Conversion | Role |
|---|---|---|---|---|---|
| UK-DALE full (2017) | pending (user downloading) | 5 | 6 s | none - same .dat schema, more channels | primary substrate; rebuild reference |
| REDD @ 1 min | **already local** (`research-logs/xingyang990210_nilm-datasets/` building_1..6.csv) | 6 | 1 min | none: `total` column = aggregate, appliance columns = submeters | the immediate cross-house set, natively at the 60 s rung |
| REFIT | not reachable from here (pure.lboro.ac.uk blocked); user download or mirror | 20 | 9 s | wide CSV -> long table | the 20-home generalization tier |
| AMPds2 | host reachable (zenodo.org 200) | 1 | 1 min | convert | native 60 s = the Shelly rung exactly |
| ECO | dataverse.harvard.edu reachable | 6 | 1 s | convert | extra homes, Swiss market |
| DRED / GREEND | mixed hosts | 1 / 8 | 1 min / 1 s | convert | optional |
| tracebase | no | n/a | 1 s | no aggregate exists | extra calibration signatures only, never deployment simulation |
| PLAID | local (`research-logs/vi/`) | n/a | 30 kHz snapshots | **NOT convertible** - waveforms, no household timeline | V-I hardware track only |
| Client synthetic CSV | local | 1 | 1 s | artifact (1 d replayed 30x) | excluded per repo-review |

REDD-1-min caveats: resampled (fractional socket readings are minute-means), submeters do not sum to
`total` (same unlabeled-mass property as UK-DALE), ~1 month/home = thin calibration supply - fine for
transfer testing, not for learning curves.

### 10.2 What this changes in the experiment

- **R7 - cross-household transfer matrix:** signatures calibrated on house A applied to house B's aggregate
  (UK-DALE house 1 vs houses 2-5; UK-DALE vs REDD homes; REFIT vs both). This directly measures the TSG 2019
  no-fine-tuning claim (doi:10.1109/tsg.2019.2938068). Strong matrix -> the client can skip per-home
  calibration; weak matrix -> the calibration session becomes per-home mandatory. Either way, measured.
- The learning curve (R3) stays per-house; full UK-DALE gives each appliance ~10x more calibration episodes,
  sharpening the N = 20 knee.
- Loader stays schema-agnostic from day one: long table (epoch_s, channel_id, watts); every converted dataset
  drops in unchanged; matching rules and gates carry over, with gates re-derived per house on its calibration
  split (never tuned on test).
- Keep per-house materiality reporting: energy shares move across homes - monitor-class dominance is a house
  property, not a law.

## Appendix: session-established numbers used above

| Quantity | Value | Source |
|---|---|---|
| Rows / span / dt | 985,855 / 70.66 d / 6.0 s | EDA run, `eda_runs/ukdale_reference/` |
| Steps > 30 W per day | 715.0 | EDA |
| 2+ appliances ON | 32.7% of time | EDA |
| Monitor duty / median-ON | 80-82% / 111 W | EDA + episode count run (this doc) |
| Fridge duty | 36.5-36.6% | EDA + this doc |
| Kettle median-ON / step / dwell | 2,890 W / 2,878 W / ~240 s | EDA + q123_stats |
| Kettle vs heater dwell | ~240 s vs ~1,800 s | q123 analysis |
| Noise floor | ~1.0 W | EDA |
| Aggregate energy / submeter sum | 321.1 / 275.1 kWh, ratio 1.167 | this doc (materiality pass) |
| Unlabeled aggregate energy | ~14.3-14.5% | this doc + `dataset-walkthrough.md` reconciliation |
| Episode counts (70.66 d) | fridge 2,054; kettle 195; washer 83; dishwasher 176; monitor 31 | this doc |
| Client synthetic CSV (for contrast) | 1 day replayed 30x; noise floor 14.6 W; 4,290 steps/day | `repo-review.md` |
| Local slice exact span | house 1, 2014-06-30 -> 2014-09-12, channels capped at 2^20 rows (6/53 labels) | inventory check (this doc, 10) |
| REDD local set | 6 buildings, 1-min, `total` + appliance columns, ~1 month/home (2011) | `research-logs/xingyang990210_nilm-datasets/` |