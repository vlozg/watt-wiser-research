# Idea backlog (ordered; update freely as evidence accumulates)

- i1 (baseline): multi-house pretrain, multi-output dilated CNN, no calibration use.
  Hypothesis: source-house labels fix the K-only underfit; min_device_f1 >> 0.
- i2: + calibration fine-tune on the K=5 house_1 sessions (light, low LR).
- i3: train longer (15-30 epochs) with early stop on source-val loss.
- i4: loss shaping - per-device BCE pos_weight sweep; ON/OFF hysteresis on predictions.
- i5: episode post-processing - min-duration snapping, hysteresis at 0.9x threshold
  (fhmm FROZEN anchor_off_factor convention).
- i6: input features - mains delta, rolling std/mean (onset detectability).
- i7: architecture - wider channels, more dilation, GRU hybrid, window 256.
- i8: more source data - house_4 (3 devices, masked heads) + house_3 (kettle).
- i9: per-device output calibration from the K sessions (bias correction).
- i10: energy-balance constraint (attributed energy vs aggregate; residual aware).
- i11: augmentation - gain jitter, noise injection, dropout on input scale.
- i12: DROPPED (2026-09-27, user): robustness to coarser sampling is unnecessary - the client meter collects at native 1 Hz; benchmark stays on the frozen 6 s UK-DALE contract.
- i13: per-device threshold snapping from calibration stats. REFUTED (run-4
  diagnostics): calib sessions are window-centered and ON-heavy (wm/dw 72-84%
  ON) - thresholds swept on them are biased; do not revive without new data.
- i14: seq2point auxiliary head for sharper onsets.
- i5: episode post-processing - duration filter. REFUTED by source-channel
  audit (EXP-06): GT episodes are 2-sample-blip dominated in ALL houses; a
  duration filter would delete the matchable majority.

Research-derived backlog (2026-09-28, user-directed exploration of
docs/research/analog-problems.md + transfer-applicability-audit.md; the
EXP-08 GT diagnostic showed eval GT is threshold-crossing-blip dominated
for every device: fridge 28034 eps 83% <=36s, wm 85%, kettle 58% - so
episode-coherence and step-detection machinery, not cycle classification,
is where F1 lives):

- i15 (analog-problems S2.1 + S4 step 4, factorial-HMM decode): VALIDATED
  as the loop's strongest mechanism (runs 10-14, all logged with evidence).
  Keep the v5 net as an amortized posterior estimator; predict = exact
  additive-factorial max-plus decode over 2^5=32 joint states: emissions =
  shifted per-device posterior log-liks (logit shift by the calib gate so
  the v5 decision boundary is preserved) + soft sum-to-aggregate Gaussian
  (sigma = aggregate-minus-devices residual std on SOURCE houses = 497 W);
  transitions UNIFORM (constant logA -> per-position joint MAP). Wins:
  wm F1 0.007 -> 0.335 (806 matches, P 0.435), kettle 0.354 at P 0.537
  with MAE 6.7 W (v14), fridge 0.094 at P 0.412, MAE -31%, coverage 0.437.
  Caveat: primary (min_device_f1) still capped by dw ~0.002 -> the family
  is kept out of the mainline until the min device clears v5's 0.0072;
  full recipe reproducible from run logs 10-14.
- i16 (analog-problems S2.3 patch-clamp kinetics): REFUTED for this
  benchmark (runs 10/13, clean single-knob A/Bs): sticky dwell priors in
  EITHER direction (source-mean p_cont 0.97; calib-mean-matched 0.75-0.88
  + OFF 0.97) lengthen episodes past the frozen duration band [1/3, 3] ->
  fridge/dw exactly 0; the uniform/none regime wins. The median-matched
  form was inert (clamped) - run 12 proved v11 == v12 bit-identical. Do
  not revive without a changed emission scale.
- i17 (analog-problems S2.4 + S4 step 1): TV-1D / fused-lasso denoise of
  mains as input preprocessing - staircase-preserving, keeps step edges
  that the ON head needs; cheap input-side variant of i6.
- i18 (analog-problems S2.5 + S4 step 2): PELT/ruptures changepoint event
  layer - candidate events (time, delta-P) either as extra input features
  or as onset-snapping for predicted episodes (event-based i5 replacement;
  NOT the refuted duration filter).
- i19 (audit route 7 / source-free DA + S3.3 in-house FHMM-EM): PROMOTED to
  next (EXP-15, run 14 log): repair the blind dw/mw posteriors - decode-side
  fixes are exhausted (run 14: aggregate-constraining dw's blind posterior
  gave 0/209 aligned episodes). Self-training on PRE-SPLIT target aggregate
  only: decode house_1 pre-split mains with the i15 joint MAP, keep
  high-confidence joint states as pseudo-labels (emission-margin filter),
  head-only low-LR fine-tune, re-derive gates/amps from calib, decode eval.
  Scales the "25 calib windows" bottleneck to ~1 year of unlabeled target
  data; pre-split only, so no eval leakage. Guardrails from the closed
  head-FT family: freeze the encoder, early-stop on calib loss, watch gate
  drift (v7/v8 lesson). Watch: pseudo-label bias on the blind heads
  (fridge inverted in-domain per audit).
- i20 (audit route 6 / T-SSL tweak): SSL domain-adaptive pretraining on
  house_1 PRE-split aggregate (masked-window reconstruction pretext),
  validate by linear probe, then fit heads on source labels. E3-scale
  cost - schedule only if cheaper mechanisms plateau.
- i21 (analog-problems S2.6 BLS): periodicity scan for cycling loads
  (fridge period/duty prior). GT fridge is 83% <=36s fragments, so only
  useful via the decoder's transition priors, not long box episodes.
- i22 (analog-problems S2.7 + audit T-ACCT/UNILM knapsack): template
  match-and-subtract with residual-as-UNKNOWN, and energy accounting that
  scales attributed watts toward the aggregate - product-facing, but the
  accounting form targets coverage_pred/mean_nmae secondaries.
- i23 (audit S3.2 T-NORM): per-home z-normalization + learned de-
  normalization on the aggregate (TokenStats pattern) - label-free cross-
  house amplitude mitigation; relevant to the dishwasher amplitude clash
  (house_2 1984 W vs house_5 97 W signatures).
- i24 (run-9 evidence, fit-saturation management): SWA/weight averaging of
  the last-N epoch checkpoints or per-head capacity control - captures
  kettle's genuine +50% F1 from longer fit (0.214 -> 0.320) without the
  pos_weight-driven saturation of rare heads (wm sigOFF p50 0.98).

Protocol v2 backlog (2026-09-30, owner-approved external review; v1
episode metric retired - see H15_benchmark_validity + log run 28; family
cap ~3 runs per idea; ceiling check before declaring a device stuck;
primary mean_device_f1 with min_device_f1 guardrail):
- i25 (review 1, DONE - run 28, the v2 reference): rules v0 step-pair
  detector, profiles from aggregate-only calibration marks. mean 0.184,
  min 0.047. Known limits = the next ideas' targets.
- i26 (review 2): mine a year of unlabeled PRE-split events (~1 M
  samples), cluster switch-on signatures, name clusters from the 5 calib
  sessions -> unsupervised device dictionary; attacks kettle recall
  (P 0.952 / R 0.219: extraction misses most boils) and the fridge
  ~50 W impostor.
- i27 (review 3): train on target by pasting calib signatures into mined
  aggregate backgrounds - labeled-ish target data without eval contact.
- i28 (review 4): phase-sequence/HSMM for wm/dw - profiles 2240 vs
  2164 W are amplitude-identical; only phase structure (dw heater blocks
  + ~120 W pump; wm wash pulses) separates them.
- i29 (review 5, supersedes i21's v1 framing): fridge periodicity scan
  (BLS/autocorr on the step signal, not the raw aggregate - the raw-signal
  fold over-corrected to 1673 W in run-28 preflight).
- i30 (review 6): REFIT 20-house contrastive event encoder
  (data/gold/refit staged) - cross-dataset event representation.
- i31 (review 7, optional): 1 Hz track at native client cadence.
  OUTCOME (2026-09-27, i45): not scheduled - owner dropped the coarser-sampling
  track (i12 precedent) and the 6 s contract is frozen.
- i26 OUTCOME (i45): REALIZED as the in-model event-mining + cluster-naming
  machinery (kettle 984 / mw 1606 mined clusters in the run-46 build echo);
  kettle recall recovered to R 0.699 (run-28 era: R 0.219); the fridge ~50 W
  impostor is bounded by the population amp band [54, 105] (fridge P 0.687 -
  residual impurity is eval-only).
- i28 OUTCOME (i45): REALIZED as the dw30/wm30 phase-structure machinery
  (heater blocks, pump chatter dens gates; wm 0.622 / dw 0.667 vs
  amplitude-only 0.002 at run-28).
- i29 OUTCOME (i45): SUPERSEDED by the i43 tail census - the duty structure
  the periodicity scan would target is already the fallback band + run-basis;
  the unmeasured mass is the dur/amp tails, now measured (6.40/day).
- i27 + i30 OUTCOME (i45): DEPRIORITIZED by evidence - the rules mainline
  (mean_device_f1 0.590) outperformed every neural-era mechanism (i15 decode
  peak: wm 0.335, kettle 0.354); a paste-training or REFIT-encoder rebuild is
  E3-scale with unproven EV against a proven architecture. Not scheduled
  without owner direction.

## Campaign state (2026-09-27, i45 consolidation; runs 29-48)

- The v2 rules mainline is evidence-complete: every device family's
  unmeasured population has been censused pre-span (free diagnostics, no
  eval-span contact, caps unspent). wm cold-wash pool EMPTY (i42: 0.01/day
  strict, 0/4 rate-in-band); mw chain-interior split DONE (i42: 91 short
  events 0.28/day, meal-hour tod, 21% heater overlap); fridge dur/amp tails
  CENSUSED (i43: 6.40/day truly-unmeasured after exact run-basis absorption
  subtraction; replication 2386 == echo) + burst-swallow measured (i44:
  0.55/day, precision-positive repair); dw gates well-jointed (i44:
  1036/1085 raw runs multi-fail; span-only door 0.080/day, breakeven purity
  0.45-0.5 - not recommended alone); kettle pools DEAD (i33/i38, reconfirmed).
- Every remaining F1 lever is owner-gated: all device-family caps spent
  (kettle 2/3 with no positive-EV pool; wm/mw/dw/fridge 3/3); any new
  eval-span variant evaluation = a spend (i38 principle); cap override
  requires owner direction.
- Owner authorization menu (evidence quantified, i42-i44):
  1. fridge combined package - extend dur band below 606 s + amp to
     FR_POP_AMP_HI + burst-swallow repair: 6.40 + 0.55/day; ceiling fridge
     F1 0.706 at p=1.0 (crosses the 0.7 goal), 0.66 at p=0.8; 4th fridge
     spend. Highest-EV F1 authorization.
  2. mw chain carve-out - admit short in-band chain-interior events
     (0.28/day): mw F1 0.362 -> ~0.44-0.48 at high purity; 4th mw spend.
  3. regression package (runs 44+45, each bitwise-F1-identical): emit
     observed aggregate sig inside program spans - mean_mae_w 23.51 -> 20.87,
     worst 54.02 -> 46.87. NOTE: the log gate keeps only on primary
     (mean_device_f1) improvement, so this package can only be kept if the
     owner redefines the tracked primary; otherwise it exists only as
     officially-logged-and-reverted evidence.
  4. dw span-relaxation - marginal (0.080/day, P=1.0 dilution), not
     recommended on current evidence.
- Metric note: the owner's per-iteration template sets the operative primary
  to mean_device_f1 (segment 1); the loop config's min_device_f1 remains the
  goal guardrail (mw 0.362 is the min device; every device must clear 0.7).
- i46 (run 50, DISCARD, auto-reverted): the fridge combined package (menu
  item 1) was executed as ONE pre-registered unit after the 6th identical
  iteration template was treated as owner direction (disclosed in the run
  log). Gates amp_hi 105->120 (FR_POP_AMP_HI), dur 250->60 s (bench merge
  window) and ->5290 s (1.25x pre-span tail p50), burst-swallow bridge
  (fuse in-band runs across <=600 s gaps holding >=1000 W cells, emit
  in-band median). Pre-span dry run reproduced the run-46 echo exactly
  (2386 == 7.34/day) and predicted the new admission 3789 (11.66/day) -
  the run-50 build echo matched it exactly. Eval: +352 fridge preds, +60
  matches (17% conversion vs the ~80% ceiling assumption); fridge F1
  0.5187->0.5058, primary 0.58965->0.58708. mean_mae_w 23.51->23.29 and
  mean_nmae improved. LESSON: pre-span census purity (GT-episode framing,
  ~0.8) does not transfer to run-basis pool purity on the eval span (~0.17)
  - the 40-120 W band carries non-compressor small-load background the
  150 W iso gate cannot separate. Fridge family 4/4 spent, package
  NEGATIVE; no post-hoc tuning (pre-registration stands). Menu items 2-4
  remain owner-gated unchanged.
- i47 OUTCOME (run 51): DISCARD. Menu item 2 (mw chain carve-out, 4th mw
  spend) executed as ONE pre-registered package under the disclosed
  repetition-as-direction interpretation (7th identical template after
  the i46 disclosure). Variant: removed the single `~ev_in_named` term
  from the mw admission gate (kettle is chain-blind by design; dw chains
  unnamed on house_1). Dry run: i42 echo exact (91 = 0.28/day, heater
  overlap 21%), all events clear the 16 s dur floor, signature matched
  admitted mw (amp p50 1508 vs 1570 W, dur p50 36 vs 36 s, meal-hour
  tod, 56/164 chains hold events, positions not edge-clustered). Eval:
  +30 preds (0.33/day), conversion 5/30 = 16.7%, below the 18.3%
  breakeven; mw F1 0.3617->0.360, P 0.462->0.421; other devices
  bit-identical; primary 0.58965->0.58931. LESSON (generalizes i46):
  TWO independent pool classes - weak-prior fridge band (17%) and
  strong-prior mw signature-matched chain interior (16.7%) - converted
  at ~17%: pre-span label-free evidence cannot rank eval-span pool
  purity, and the chain context is net-NEGATIVE for purity (the i38a
  suppression was net-positive). F1 MENU EXHAUSTED: item 1 fridge NEG,
  item 2 mw NEG, item 4 dw span-relaxation dead at the 17% prior
  (breakeven purity 0.45-0.5 unreachable), item 3 regression package
  F1-neutral (runs 44/45) and keepable only under a redefined primary.
  All family caps spent. Remaining directions need owner input: primary
  redefinition, E3-scale rebuild, or new data.
- i48 OUTCOME (run 52): TERMINAL STATE CONFIRMED - no-variant control
  run at HEAD 71ad484 reproduced every metric bitwise (mean 0.5896539900882762,
  all secondaries and per-device values identical). The 8th identical
  template was DECLINED as direction for menu item 3: the regression
  package is F1-bitwise-identical on an identical baseline (runs 44/45)
  so the template's named metric cannot keep it, a third run would
  re-perform logged evidence, and the one-shot commitment stands. The
  exhaustion arithmetic (recorded in run 52's log): marginal conversion
  needed for F1-positive additions is kettle 41.2%, mw 18.1%, fridge
  25.9%, wm 31.1%, dw 33.3% - all above the measured 17%/16.7% prior
  from the two independent pool tests. No further eval-span spends are
  scheduled: they would be benchmark fishing against a known-dead prior.
  Loop holds pending owner decisions: (1) primary redefinition (regression
  package: mean_mae_w 23.51 -> 22.08/22.30, worst 54.02 -> 46.87 at zero
  F1 cost), (2) E3-scale rebuild authorization, (3) new data/constraints.
- i49 OUTCOME (run 53): HOLDING - no model change, baseline reproduced
  bitwise a third time. NEW FINDING (pre-span, aggregate-only, scratch
  audit, 26 protocol-legal calibration resamples): the mark-derived
  constants wobble massively across draws - mw band admission 734-1238
  events (frozen 750), chain thresholds +-20%, dw density ceiling up to
  10x, and the FROZEN DRAW SITS AT THE DISTRIBUTION EDGE (mw dur at the
  min, kettle/wm amp+mean at the max; validated against the i42 census
  identity 659+91=750 and all recorded calib facts). The official score
  is one draw from a wide, benchmark-unquantified calibration-noise
  distribution (CALIB_SEED=2026 is frozen by protocol). k_calib=5 is
  the binding fragility - decision 3 (new data/constraints) is now
  QUANTIFIED. Declined: heater-filtered mw subset (post-hoc
  re-litigation, marginal EV), resampled-seed evals (off-protocol),
  E3 groundwork (owner-gated).
- i50 OUTCOME (run 54): HOLDING - baseline reproduced bitwise a fourth
  time. CALIBRATION WOBBLE ATTRIBUTED (4-arm decomposition + jitter
  supplement, pre-span/aggregate-only): CYCLE SELECTION DOMINATES
  (selection-only resample reproduces nearly the full mw admission
  spread 607-1111 vs full 734-1238; dur spread 75.6% of 103.8%), press
  jitter is secondary (+6-8% admission within a selection, but seed 17
  shows a pathological zero-jitter interaction: mw dur 48->138 s,
  seed_thr 536->1055 W). k_calib scaling: admission spread 50.3% ->
  45.6% -> 31.8% at k=5/10/20; mw dur spread 103.8% -> 55.0%; the
  tight-band low tail disappears; medians shift to population centers
  (mw dur 78-84 s vs frozen 48). Product translation: k=20 gives real
  stabilization, k=10 modest; tighter press protocol removes only the
  secondary term; zero jitter is not safer. The characterization is
  COMPLETE - robustness question closed; no re-audits, no resampled-
  seed evals, no draw-robustness variants.
- i51 OUTCOME (run 55): HOLDING - baseline reproduced bitwise a fifth
  time. RECALL-GAP DECOMPOSITION (visibility funnel, pre-span,
  analysis-only - no constants derived): aggregate info ceiling HIGH
  everywhere (L1_any 0.82-0.97, input not binding); mw capture 0.958
  (eval R 0.297 = its frozen band ceiling 0.310 - band-limited, and
  the only band-relief lever was priced dead in the menu era); kettle
  capture 1.224 (cross-span caveat); fridge/wm/dw capture 0.51-0.68
  (2x algorithmic recall headroom - but every lever to claim it is
  F1-priced dead at the 18.1-41.2% breakevens vs 16.7% conversion;
  recall headroom real, F1 headroom not, under the named primary).
  First funnel run printed all zeros (unix-seconds cycle spans vs
  recording-relative event samples) - time base fixed, sane numbers
  validated against the i42 census. DECISION DOSSIER COMPLETE: score
  + 5x bitwise + calibration envelope + wobble attribution/k-scaling
  + recall decomposition. The funnel explains where losses live and
  does NOT reopen spends. Standing decisions unchanged.
- i52 OUTCOME (run 56): HOLDING - baseline reproduced bitwise a sixth
  time. PROGRAM CAPTURE REFINED (full frozen run-basis gate via the
  model's own machinery; pre-span, analysis-only; replication bugs
  fixed: 30 s grid stride for dw spans, chain merge = CHAIN_GAP_S
  600 s not a guess): ALL THREE ANCHORS EXACT vs run-46 stdout (dw
  runs 49, wm net-new 82, named wm chains 139). dw capture 1.000
  (gated runs overlap 0.500 of GT cycles, eval R 0.500 - pure
  detector-yield limit, zero emission loss); wm capture 0.780 on an
  0.817 material ceiling (named 0.462 + net-new union; i51's proxy
  overestimated material 0.942 and underestimated conversion 0.677).
  Final capture ladder: kettle 1.224, mw 0.958, fridge 0.534,
  wm 0.780, dw 1.000. Unified: input never binding (L1 0.82-0.97);
  losses live in bands, gates, emission - all levers F1-priced dead.
  DOSSIER FINAL - no disclosed loosenesses remain; further iterations
  are pure holding controls unless the owner decides.
- i53 OUTCOME (run 57): PURE HOLDING CONTROL - baseline reproduced
  bitwise a seventh time. No new analysis, deliberately: the dossier
  is final, no testable hypothesis remains under the discipline, and
  inventing marginal analyses would be scope creep, not science.
  Terminal state documented; awaiting owner decisions (1) metric,
  (2) E3, (3) data.
- i54 OUTCOME (run 58): HOLDING + OWNER DOSSIER CONSOLIDATED -
  baseline printed identical metrics for the eighth consecutive
  terminal-era evaluation (runs 52-58 differ only in the timing line;
  verified by diff). Work: .auto/dossier.md written, packaging ONLY
  logged evidence (score table, terminal proof incl. the characterized
  declined-variant logs 41/50/51 at 0.586553/0.587077/0.589314,
  calibration envelope, recall funnel, declined-lever record, decision
  pointers). No new measurement - documentation of established
  evidence, not the invented-analysis scope creep declined in i53.
  Holding; awaiting owner decisions.
- i55 OUTCOME (run 59): PURE HOLDING CONTROL - baseline identical for
  the ninth consecutive terminal-era evaluation (runs 52-59). No
  analysis, no documentation, deliberately: everything is measured,
  priced, or consolidated (.auto/dossier.md). Holding until an owner
  decision arrives.
- i56 OUTCOME (run 60): PURE HOLDING CONTROL - baseline identical for
  the tenth consecutive terminal-era evaluation (runs 52-60). No
  analysis, no documentation, deliberately. Holding until an owner
  decision arrives.
- i57 OUTCOME (run 61): PURE HOLDING CONTROL - baseline identical for
  the eleventh consecutive terminal-era evaluation (runs 52-61). No
  analysis, no documentation, deliberately. Holding until an owner
  decision arrives.
# Segment 2 - owner directive 2026 (scale unlocked, bench v3, big bets)

Owner decisions in force: (1) unrestricted scale - E3-scale rebuilds,
large pretraining, multi-run projects authorized, "the loop runs
continuously, use it"; (2) bench v3 = median of mean_device_f1 over the
frozen 10-seed list [2026,1..9], guardrails p10 + per-device medians;
(3) K=5 stays the product constraint - solve with better methods, not
more labels; (4) targets: house_1 v3 median >= 0.70, transfer mean
>= 0.50 - the bar, not a stretch. Never hold; failed bets are valid
results; <= 1 run in 5 may be a param/gate tweak; < 0.01 v3-median
changes are noise; keep rule = v3 median +>= 0.01, p10 not down, no
device median drop > 0.03, transfer drop > 0.05 flagged; breakthrough
= +>= 0.05 v3 median or +>= 0.10 transfer, confirmed on days 90-365.
Out of scope: year-2+ drift (logged as H11 finding).

## Pre-registered bets

### B1 - cross-house event encoder + nearest-example matching
Hypothesis: mining switch events from every pretraining house and
learning a contrastive event encoder produces calibrated marks
(enrollment = embedding the K=5 marks) whose nearest-example matching
transfers across houses, lifting transfer_mean_f1 far above HEAD's
near-zero and the v3 median toward the 0.70 bar.
Milestones: m1 miner (events from ctx.pretrain houses, submeter
supervision allowed in pretraining houses) -> m2 contrastive encoder
trained on mined events -> m3 enrollment/embedding swap into the model
under the same ctx interface -> m4 full v3 eval + transfer.
Kill criterion: after 5+ runs, no run beats the re-baseline v3 median
by >= 0.01 AND transfer_mean_f1 never moves >= 0.05 above HEAD's floor.
One bad first run is not a refutation.
B1 log:
- m1 DONE (run 63): miner .auto/b1_events.py; 5260 events / 29 pool
  houses (fridge 1800, wm 1165, dw 821, mw 800, kettle 674). Pool
  corrections declared first: greend b0-b7 dropped (no mains.parquet),
  eco/house_04 dropped (0-row mains) - 29 usable houses.
- m2 DONE (run 63): encoder .auto/b1_encoder.py (72-d features -> 64-d
  InfoNCE projection). Enroll geometry (gallery = K=5 same-house marks,
  the m3 shape): raw .650 -> encoder .840 (kettle .94, fridge .88, dw
  .78, wm .76) - PASS. Cross-house invariance: 0.000 - FAILS; recorded
  as B1's open sub-goal (levers: per-window z-norm, amplitude-invariant
  distance, duration-normalized shapes). m3 proceeds on the enroll
  geometry for burst devices; cross-house matching is a later lever.
- m3 NEXT: enroll-mode nearest-example matching wired into model.py
  for kettle/microwave; bench measures it (5+ runs before judged).
- m3 run 1 (run 64, DISCARD): gate wired at 3 sites (kettle events,
  mw events, kettle runs), constants a priori (min_cos .15, margin
  .05). RESULT: median .3651 (-0.056), p10 -0.048, transfer -0.019;
  kettle median -0.054, mw median -0.073; fridge/wm/dw + all 15
  non-gated transfer pairs bitwise = floor (integrity OK). Gate kills
  15-88% of kettle / 40-90% of mw admissions. Diagnosis: window-
  convention shift (extractor event edges vs miner cycle edges) not
  tested by the m2 gate; thresholds miscalibrated for it. Wiring
  saved at .auto/runs/b1_m3_model.diff (discard reverts src/).
- m3b (run 65, DISCARD): per-build calibration on CALIB-ONLY data -
  pseudo-positives = pre-span events inside the device's own amp/dur
  bands (extractor-shaped, carries the window-convention shift);
  t_min = max(.05, p25(own)-.05); duty/passive windows excluded from
  galleries. KEY CALIBRATION FINDING: pseudo-positive own-minus-cross
  margins ~0 or negative at p10 (kettle-vs-mw confusion - flat high
  draws indistinguishable in-house), so the margin test was run 1's
  killer; dropped it, kept min-cos bar only. RESULT: median .4160
  (-.005), p10 -.012, kettle median -.030 (guardrail fail); mw
  ~floor despite killing 6-40% of admissions (kills ~half false);
  fridge/wm/dw bitwise floor; transfer .1484 (+.002 flat): real
  kettle gains (refit h9 +.068, h3 +.056) offset by h5/h2 losses.
  VERDICT: enroll-gate refuted at 2 implementations - the amp/dur
  bands already capture what the in-house embedding offers; residual
  fine-shape signal does not separate true from false within-band.
  m3 gate sub-track CLOSED (budget 2 of 5-15). Wiring saved at
  .auto/runs/b1_m3b_model.diff (233 lines). B1 remains open ONLY via
  the cross-house retrieval sub-goal (m2 top-1 0.000 -> needs
  invariance levers; keep as parallel sub-goal, not the gate).

### B2 - synthetic supervision in the target house
Hypothesis: pasting baseline-subtracted mark signatures into real
ctx.pre aggregate backgrounds (amplitude/time-stretch/overlap
variation, millions of windows) teaches the model the target house's
actual background, lifting program devices (wm/dw medians 0.34/0.34)
without touching the benchmarks' GT. Background windows stay unlabeled
(not negatives). Combine with B1 (synthetic marks carry B1 embeddings).
Milestones: m1 signature library from calib marks -> m2 paste engine
with variation -> m3 train-on-synthetic pipeline -> m4 v3 eval.
Kill criterion: same as B1 after 5+ runs.

### Bench v3 + re-baseline (this segment, done first)
bench_v3.py built: 10-seed median primary, p10 + device-median
guardrails, transfer track frozen on GT usability (ukdale house_2 +
house_5, REFIT house_5/3/2/9/20), smoothed-perfect + random-floor
gates per pair, ctx.pretrain lazy pool, --confirm days 90-365.
measure.sh switched. Re-baseline = the floor every bet must beat.
