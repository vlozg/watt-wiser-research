# WattWiser NILM baseline - TERMINAL-state dossier (autoresearch segments 0-3)

Status: CLOSED by the owner on 2026-09-28. Segment 3 (cross-home transfer
learning) closed with **zero logged runs**: it produced a measured
cross-method reference (experiment 05) instead of a bound-space iteration, so
nothing was logged against the segment-3 metric. No further rule-based
iteration is proposed; the rule bound space is exhausted (section 4). The DL
line's next step is a per-device hybrid (section 6), which is a new experiment,
not a continuation of this loop.

## 1. Deliverable and closing score

Artifact of record: `src/experiments/04_autoresearch/model.py` at commit
`b4298ca`, md5 `12971dac24b82600dd052a0eb4283a35`, unmodified since the last
keep. Re-measured fresh at hand-off (`bash .auto/measure.sh`, exit 0) and
bit-identical to `.auto/last_bench_v4.json`:

| metric | value |
|---|---|
| mean_device_f1 (primary) | 0.366174 |
| mean_device_f1_p10 | 0.345739 |
| device_balanced_mean | 0.368405 |
| house_1_v4_mean | 0.529428 |
| v4_n_pairs / v4_n_houses | 66 / 20 |
| median kettle_f1 | 0.561050 |
| median fridge_f1 | 0.387253 |
| median dishwasher_f1 | 0.384353 |
| median microwave_f1 | 0.267210 |
| median washing_machine_f1 | 0.246657 |

Per-seed means (2026, 1, 2, 3, 4): 0.373682, 0.344694, 0.366424, 0.366174,
0.347308. Primary is the median over seeds of the per-seed mean over the 66
(house, device) development pairs; one pair is 1/66 = 0.01515.

Product bars at close: house_1 v3 median >= 0.70 and transfer mean >= 0.50 were
NOT met (house_1_v4_mean 0.529). The worst-device bar (every device > 0.7) was
never approached: the pool's weakest devices are washing machine 0.247 and
microwave 0.267.

## 2. Frozen protocol (never tuned)

`bench_v4` pool: 20 development homes, 66 (house, device) pairs, median over
the frozen seeds [2026, 1, 2, 3, 4]; 7 holdout homes are readout-only. Frozen
constants: `v2.TAU_ONSET_S`, `v2.DURATION_BAND`, `v2.MERGE_S`,
`v2.K_CALIB`, `v2.DEVICE_CLASS`; `thr_on_W = 0.5 x p50_on_W`; a device is
visible only if `2*thr >= AMP_MIN_W` (50.0 W). Entry point is the frozen
`.auto/measure.sh`; no other path is a legal score.
Holdout homes: ukdale/house_2, ukdale/house_5, refit/house_5, refit/house_3,
refit/house_2, refit/house_9, refit/house_20.

## 3. Ledger (whole campaign)

110 ledger entries in `.auto/log.jsonl`: 4 segment configs and **106 logged
runs - 29 keep, 77 discard, 0 crash / checks_failed**.

Four segments, four metric framings (numbers are not comparable across them -
each is a different measurement population):

| segment | name | metric | closing value |
|---|---|---|---|
| 0 | seq2seq worst-device episode F1, UK-DALE house_1 | min_device_f1 | 0.029649 (superseded) |
| 1 | cycle protocol v2, house_1 only | mean_device_f1 | 0.589654 |
| 2 | bench v3 big bets, then bench v4 pool | mean_device_f1 | 0.366174 |
| 3 | cross-home transfer learning (experiment 06) | mean_device_f1 | no runs logged |

Segment-1's 0.5897 and the v4 pool's 0.366174 are different protocols
(house_1-only episode F1 vs median-over-seeds mean over 66 pairs across 20
homes), not a regression. The v4 re-baseline line: 0.306428 (df85d3c,
per-home re-calibrated pool) -> 0.321967 (703a591) -> 0.336828 (4deec78) ->
0.354623 (2f0ee0f) -> 0.366174 (b4298ca).

Keep chain (29 commits, chronological):

```
54cf23b 0           EXP-01: multi-house pretrain baseline collapses to zero
7e1d46c 0.007188    EXP-05: head-role separation revives all 5 device heads
0f3a023 0.010152    v15 vis-routed hybrid decode: min 0.0102 (+41%)
8f54897 0.017910    v16 liveness routing + 5-chain MAP: min 0.0179 (+76%)
67ce270 0.029649    v19 mw context-mix FT: min +66%
46f5599 0.029649    EXP-24 v23 per-device representation routing: bit-exact
ca6a00f 0.183727    EXP-29 rules v0 baseline under cycle protocol v2
62376fa 0.245925    i26 level-return event mining + ON-plateau emission
d56c8d7 0.254062    i28 mark-band program naming (density tiebreak, phase gates)
deb67e8 0.272528    i28 raw heat-share gate (extractor-independent)
597970b 0.315212    i28 raw-p90 chain amp + seeding (extractor-free)
9014d8f 0.389392    i29 fridge band from mined compressor population
a311614 0.399232    i30 mw event-span emission aligned to GT cycle
ddca985 0.509036    i31 dw sustained heater-run detector, mark-derived gates
8affcc7 0.533668    kettle sustained-run additive detector (net-new)
a0e009b 0.556434    i33 wm30 sustained-run detector: mark-fused runs
c68bad0 0.573951    i34 fridge run-basis detector: sub-amp-floor cycles
fa33e1a 0.574597    i35 fridge run-basis dur-lo extension to mark/3
71ad484 0.589654    i36 wm30 heater p90 floor gets REL_AMP lo margin
5857708 0.421473    re-baseline HEAD under bench v3 (10-seed median + transfer)
5318070 0.459345    B2 probe: extractor fall-run fix - biggest jump of campaign
025f41f 0.494189    m4 dw onset geometry: median per-mark pre/post-offset ext
b6c3fd3 0.505987    m6: wm30 window-skip + drop dw run-basis ownership on wm
5ad5980 0.505987    v4 prereq: model.py device-subset-robust (bit-identical)
df85d3c 0.306428    bench v4 re-baseline: per-home re-calibrated pool primary
703a591 0.321967    fridge-only 20 W step floor: +0.0155 primary
4deec78 0.336828    m18: floor a sub-threshold mark amp at the reader's median draw
2f0ee0f 0.354623    m20 reader-floor visibility: primary +0.0178
b4298ca 0.366174    kettle yields emitted program spans: clears bar 0.3646
```

## 4. Why the rule line is terminal

Keep rule in force at close: keep iff pool primary >= last kept floor + 0.01,
p10 must not drop, no device median may drop by more than 0.03. The last bar
was 0.376174 against a 0.366174 incumbent.

The segment-2 close-out (runs 103-118, all discards) partitioned the remaining
bound space three ways:

- **Harmful** - the dw merge (109), dw idle dial (110), dw span floor (113) and
  dw mean floor (114) all protect precision; removing any one loses more than it
  gains.
- **Inert / vacuous** - run 115 (wm heat-share ceiling) was bit-identical; run
  116 (wm prog_spans re-point) moved 1e-4; run 117 (dw prog_spans re-point) 7e-5;
  run 118 (marks-free kettle train suppression) produced zero firing. Audit
  gates before spending a pool run (m42).
- **Real but non-compounding** - run 108 (wm merge, 0.365828) and run 112
  (combined, 0.365631) each moved the primary by less than the 0.01 bar and did
  not stack.

Everything else in the backlog was closed as refuted. Full enumeration with
reasons, one entry per hypothesis, is in `.auto/ideas.md`: onset statistics,
admission width on burst devices, wm span ceilings, fridge band/duration/
isolation, high-side amp lift, crossed detectors, the dw all-or-nothing branch,
house-specific dw/wm placement knobs, mw `dur_ref`, H-shift/timebase,
fragmentation switching, cross-house physical envelopes, pre-span self-
calibration of burst bands, program-run-span suppression, synthetic-onset sign
gates, declared-device-spec gate bands, contract-merge alignment for the kettle,
±22 min extended program-span suppression, house-adaptive `AMP_MIN_W`, the
fridge short-cycle rescue, amp-vs-program-level yield, and the whole wm/dw
band-gate family.

## 5. The one measured loss left on the table (representation, not a gate)

The kettle block (12 pairs, mean F1 0.562) contains two dead pairs: house_12
0.060 (712 predictions against 127 GT cycles) and house_7 0.130 (455 vs 108).
Together they are worth about +0.015 - more than the +0.01 bar.

Mechanism: `ev_in_prog` (model.py L1346-1348) derives only from `prog_spans`,
which derives from the device profile. house_12 has no dishwasher in `cmap`,
so no dw program spans are emitted there and its duty-cycling heater blocks
surface as kettle boils. No amplitude or duration band separates a duty-cycling
heater from a boil - every candidate was measured dead (runs 103-118). This is
the documented justification for the transfer-learning line: the aggregate
alone does not carry the discriminator, a cross-home model might.

## 6. Cross-method reference (experiment 05, holdout readout)

Measured by `src/experiments/05_method_compare` on the 7 holdout homes, 6 of
which have scored devices (ukdale/house_2 fails bench eligibility), i.e. 26
pairs. Reduction: per-pair median over seeds, then mean over pairs.

| device | rules | rules+GT thr | FHMM | seq2seq |
|---|---|---|---|---|
| kettle | 0.582 | 0.580 | 0.444 | **0.733** |
| fridge | 0.304 | 0.390 | 0.165 | 0.299 |
| dishwasher | **0.351** | **0.351** | 0.093 | 0.187 |
| washing machine | **0.140** | **0.140** | 0.045 | 0.129 |
| microwave | **0.153** | **0.153** | 0.045 | 0.049 |
| all 26 pairs | 0.306 | 0.325 | 0.159 | 0.280 |

Energy (median over pairs; the all-zeros prediction scores 1.0): daily error
FHMM 1.306 / rules 0.723 / seq2seq 0.650; total 0.891 / 0.548 / 0.459; NDE
2.218 / 0.999 / 0.809. No method is product-ready on energy.

Reading: the DL net uses **zero button presses** and is competitive overall,
with a complementary error structure - unseen precision/recall is rules
0.407/0.271 against seq2seq 0.257/0.454. It wins decisively on the kettle
(0.733 against 0.582; rules spans 0.511-0.595 across seeds, and the
ground-truth-threshold variant also loses at 0.580, so the gap is
representational, not a threshold artifact) and on the washing machine in the
development pool. It loses worst on the microwave, whose failure is an
amplitude/sub-floor problem (several homes sit at 43-47 W, under the 50 W
visibility floor) and matches segment 0's finding that the microwave ON head is
blind.

Next measurable step: **per-device arbitration** - rules for microwave, fridge
and dishwasher, the cross-home net for kettle and washing machine. Per-device
best-of is 0.353 unseen against rules' 0.306, i.e. +0.047 with no training
(+0.054 under a mean-over-seeds reduction). Adaptation on the K=5 marks is the
follow-on, and it must be designed against segment 0's recorded failure: full
fine-tuning overfit (about 11x retention damage at 40 epochs) with saturated
heads from a reused `pos_weight` - freeze the trunk, fine-tune the head only,
recompute `pos_weight` on calibration data, and guard the OFF-sigmoid.

## 7. Integrity record

- The 7 holdout homes were read only for milestone readouts; no tuning touched
  them. Development pre-split spans only; the evaluation-span submeter was never
  an input. K=5 marks only; no extra labels.
- Declined, for the record: keeping a favourable calibration draw, post-hoc
  metric redefinition (F1-bitwise-identical on an identical baseline), and
  heater-filtered subsets (run 51 measured worse).
- Segment 3 registered a metric but landed nothing in `04_autoresearch`; the
  DL work lived entirely in experiments 05 and 06, so the scored artifact was
  never at risk.
- Experiment isolation: experiments must not import each other. 05 is
  self-contained. `06_transfer_dl` currently imports 05's `compare_lib` and
  needs either a standalone rewrite or removal.

## 8. Open items at close (owner-owned)

1. Per-device arbitration (section 6), then mark-based adaptation.
2. Fold the 52 literals in `model.py` into one fitted parameter dict.
3. Per-home reliability estimated from calibration-only signals.
4. History-length curve at 7 / 14 / 30 / 60 days.
5. `.auto/b1_encoder.py:171` cross-house retrieval defect (owner-named).
6. The unsatisfiable `DUTY_CV_MAX = 0.6` thermostat-interval test
   (`model.py` L97) - repair or retire.
7. `AGENTS.md` layout still lists only `00_baseline` and `01_fhmm`;
   experiments 02-06 are unlisted.

## 9. Reproduce

- Score: `bash .auto/measure.sh` (frozen; prints `METRIC mean_device_f1=...`).
- Restore the incumbent: `cp .scratch/s101_incumbent101.py
  src/experiments/04_autoresearch/model.py`, or `git checkout --
  src/experiments/04_autoresearch/model.py` plus `git apply
  .auto/runs/94_wm_median_ext.diff` and `git apply
  .auto/runs/101_fridge_shortcycle.diff`.
- Evidence: `.auto/log.jsonl` (every run), `.auto/ideas.md` (hypotheses with
  readings), `.auto/runs/*.log` (raw benchmark output), `.auto/prompt.md`
  (the frozen charter), `data/results/method_compare/` (experiment 05).
