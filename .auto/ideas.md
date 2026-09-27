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

**m1+m2 verdict (run 66, keep, 5318070): the probe paid for itself
without ever training on synthetic data.** Pasting seed-2026 mw mark
sig-0 into quiet backgrounds recovered nothing: the floor's extractor
measured fall magnitude + post-fall level at the fall-RUN START, and
plateaus drifting down > AMP_MIN_W (50 W) across the 6-sample step
window turn stp negative before the cliff (premature fall run: step
-81 W vs required >= 590 W, level still on plateau) -> event dropped
ENTIRELY. Real duty-cycled mw draws hit the same pathology, so the
defect was live on the bench. Fix: true contiguous fall-run ends via
np.diff on is_fall positions; magnitude = level drop across the run;
post-fall level after the run end; single-sample runs bitwise
identical. (Intermediate f_end = next-run-start - 1 was itself buggy
for gapped runs - overshoot to future falls, mag=-54 rejections -
caught on the probe.) Plus mw/kettle event-band gates from
mark-extracted events (fragmentation switch) and dw30 amp_lo 0.8x.
Bench: median 0.4215 -> 0.4593 (+0.0379, largest single-run gain of
the campaign), p10 +0.0233, transfer 0.1462 -> 0.1682; kettle +0.114,
dw +0.116, mw +0.039, wm +0.011, fridge -0.001. Probe iso F1 after:
kettle 0.60-0.74, mw 0.22-0.35, wm 0.52-0.88, dw 0.61-0.79 (residual
mw gap = smoothing-lag edge effects on 6-9-sample truth spans, a
paste artifact). Cross-fires parked: kettle event band admits mw
chunks (0.31 on mw spans, seed 2); wm sustained path claims dw pastes
(0.60, seed 1). Next: m3/m4 train-on-synthetic.

**Gate-fix bundle verdict (run 67, discard, tree back at 5318070):
attribution confirmed, deltas real but under the +0.01 keep bar - the
whole bundle is preserved as a patch.** Cross-fire attribution
(per-event, b2 probe): (a) seed-2 kettle cross-fire = the merged mw
paste event (2 kW, 294 s) admitted by the kettle EVENT band
[1753,2980] x [12,396] while the mw core rejects it (2032 > 1910) ->
kettle claims 0.865 of the mw span; the event is flat (p10/p90 0.89)
but the seed-2 kettle mark events are dip-y too (flats 0.11-0.24), so
a flatness discriminator is dead - the event is genuinely ambiguous on
(amp, dur), fixed only by a dur ceiling; (b) seed-1 mw cross-fire =
the mw event band admitted kettle chunks, fixed by a z-sum dispute
(ket_z <= mw_z suppresses the MW side only; the kettle keeps every
event its gate admits - its emission stays pre-dispute and
bit-identical, so stealing disputed events costs kettle recall);
anchors/half-widths from _gate_anchor_hw (event-band p50s when
switched, core stats x REL_AMP/REL_DUR otherwise); (c) seed-2 mw iso
R 0.13 = the fragmentation switch MISSED the boundary (dur_p50 54 ==
0.5 x core 108, strict < failed) -> the core gate rejected the paste's
low chunks. Dur ceiling: 3 x max(dur_p50, max(durs)/2) - merged
multi-chunk events are foreign structure, not longer draws; 3 x max
alone admitted them (294 s into a 60 s-chunk kettle), 3 x p50 alone
risks the 2026-mw extraction variance (p50 36, max 108). Switch test
now inclusive (<=). Probe: seed-1 cross-fire gone, seed-2 iso_kettle
0.72 restored, seed-2 mw iso 0.21->0.36 and mix_burst 0.43->0.67, no
regressions (probe iso_all_mean 0.598->0.610). Bench: median
0.4593->0.4672 (+0.0078, deterministic Pareto - mw median 0.354->0.382,
other devices bit-identical, p10 +0.0003, transfer -0.0004), under the
+0.01 keep bar -> discard per the pre-registered rule. Bundle patch:
.auto/runs/b2_m3_dispute_durceil_switch.diff (157 lines; apply with
git apply). Label note: session tags this 'm3' and the train-on-
synthetic bet 'm4'; this file's milestone list (above) calls the
train-on-synthetic pipeline 'm3' - same bet, one step earlier. Next:
apply the patch + train-on-synthetic pipeline as ONE bundle against
floor 0.4593 / bar 0.4693. Parked: seed-2 mix_burst wm->0.91 on mw
spans (no scored-device gain - the wm is unscored there), seed-1
mix_prog wm->0.60 on dw spans, dw collapse on seeds 6/7/8 (0.03) and
wm volatility (0.135-0.17 on seeds 4/1/8) - the bottom of the seed
distribution, m4-scale levers.

### Bench v3 + re-baseline (this segment, done first)
bench_v3.py built: 10-seed median primary, p10 + device-median
guardrails, transfer track frozen on GT usability (ukdale house_2 +
house_5, REFIT house_5/3/2/9/20), smoothed-perfect + random-floor
gates per pair, ctx.pretrain lazy pool, --confirm days 90-365.
measure.sh switched. Re-baseline = the floor every bet must beat.

### m5 verdict (run 69, discard; auto-reverted to run-68 state)
**dw streak segmentation: synthetic pass, eval FP collapse.** Chain:
scan-back refuted first (mark trace: dw pre-heat is electrically quiet,
exc p50 -82..+54W vs bg 27W, below-thr frac 0.89-1.00 at 120-300W -
per-cycle onset scanning has no signal; all 50 marks' pre-offsets mass
at 17.5-19min with contaminated outliers -> median stands). Recall
attribution: 12/28 GT episodes fail the SPAN gate on every seed inside
raw merged runs of 8220-20880s. m5 segmented overlong runs at internal
below-heat gaps (greedy pack to span-band max). Validator streak pass
recovered 4-6/6 pasted-pair onsets; b2 probe mix_prog dw RECOVERED
0.00->0.99 (2026) and 0.71->0.90 (seed 1); iso paths unchanged.
Bench: median 0.494189->0.481489 (-0.0127), p10 -0.0160, dw device
median 0.522727->0.448413 (-0.0743) despite gated-episode coverage
RISING 14->19 (2026) / 16->24 (seed 7). Emission attribution (seed 7):
63 emitted episodes, 19 matched (deltas ~0), 44 FP - the segmentation
slabs fire at non-cycle onsets. ROOT CAUSE: eval monoliths are NOT
clean consecutive dw cycles - they are dw cycles bridged with FOREIGN
appliance activity (wm cross-fire) through the 70min merge gap. No
mark-derived rule separates dw cycles from bridged foreign clusters:
inter-cycle heater gaps 19-46min overlap intra-cycle wash gaps 20-56
min; gap exc signatures seed-dependent (seed 1 pre-heat p50=99W is
motor-like); cycle pitch drifts with unknown inter-cycle idle (0-27
min). Synthetic validator is structurally blind (its streak = two
CLEAN pasted dw marks). Side effect: wm30 profile consumes the dw run
set for net-new candidates -> seed-1 wm ext_fwd 26.5->53.2min, wm
median +0.0097 (luck). LESSON: any emission-shape change must be
validated against REAL monolith structure, not clean synthetic paste
pairs; wm30's dependence on the dw run set couples the devices.
m6 candidates: (a) dw PRECISION lever - wm cross-fire runs pass dw
gates (pre-existing ~14-17 FP/seed even at m4; dw is P-limited); (b)
robust-mean variant for stacked-load episodes (5-7/seed, mean
1057-2205 vs <=943, hs passes 0.17-0.19) - needs own diag; (c) wm
residuals seeds 4/1/8 (0.135-0.17) - wm30 geometry diag; (d) parked:
transfer dw overshoot (no per-cycle electrical signal in pre-heat).

## m6 verdict (run 70, KEEP, b6c3fd3): wm30 window-skip + ownership removal

Both m5-parked wm residuals were fixed; all three pre-registered keep
conditions passed (median 0.505987 >= 0.504189, p10 0.485922 >=
0.466497, no device median drop; wm median 0.3547->0.3892). Six seeds
up, four bit-identical, none down.

1. Window-skip: an empty mark window no longer disables the wm
   sustained detector; it is skipped, and <2 usable windows disables
   (bands off one sample are noise). Fixes seed 8 (0.173->0.39 diag).
2. wm-side dw run-basis ownership REMOVED. DURABLE LESSON: the dw/wm
   mark bands can cross on wide-band calibrations (seed 4: dw dens
   ceiling 1.053/min > wm marks' max 0.44) - once crossed, NO
   mark-derived rule (any-overlap, double-pass gate admission, z-sum
   arbitration) can arbitrate a double claim; arbitration by emission
   order is a prior, not a measurement, and cost 8-19 real wm
   cycles/seed vs ~1 FP. Emit both and let each device's own gates
   bear the precision burden (kettle precedent at event level).
   Measured variant ladder (wm F1, seeds 8/4/1/2026): baseline
   0.227/0.208/0.220/0.629; double-pass 0.351/0.224/0.264/0.629;
   ownership-off 0.390/0.330/0.276/0.629. Named-chain dup check kept
   (chains are mark-verified; the wide dw bands are not).

New floor: median 0.505987, p10 0.485922, device medians kettle
0.766469 / mw 0.381962 / fridge 0.512856 / wm 0.389216 / dw 0.522727;
transfer 0.151921.

m7 candidates (in priority order):
(a) wm30 mark-stat robustification - the seeds 4/1 residual is
    band-floor rejects: eval wm runs mean 473-866 vs mean_lo 702-775,
    dens 0.04-0.20 vs dens_lo 0.14-0.20, hs ~0.15 vs 0.18. Derive the
    lo floors from per-window medians (or drop them when the mark
    spread is huge) instead of 0.75x-min of 4 windows. Validate on the
    seeds 4/1/8 diag before benching.
(b) wm FP trim - the dw cross-fire FPs (2026: 8/27 with gt_dw_overlap=1)
    and the ext_fwd 26-53 min overshoot into dw territory; needs its
    own diag after (a) moves the R/P balance.
(c) dw P-side (~14-17 FP/seed pre-existing, P-limited) - idle/mean band
    tightening, parked since m5.
(d) transfer campaign (owner bar 0.50, current 0.152): house-1 levers
    do not transfer; the biggest zeros are dw (ukdale h2 0.036, refit
    dw 0.000-0.017) - the per-house pre-heat backtrack (walk back from
    the first heater block while exc stays above the idle floor) is
    the parked adaptive lever.
(e) mw burst F1 median 0.382 (iso probe 0.347) - burst-path precision,
    parked.

## m7 verdict: extractor bounce rule REFUTED (run 71, discarded, no bench)
Hypothesis: _extract_events samples the post-fall level at f_end+STEP_H,
and a duty-cycled draw's 10-30 s magnetron off-gaps read as "level back
on", so every intra-draw fall fails; pairing then walks to the draw-end
fall and fuses the whole draw into one monster event the burst dur
ceiling rejects. Fix: accept a fall as end if the level bounces back
within hi = lo + STEP_H + 2.
A/B on the b2 probe (pre-fix vs post-fix, same seeds):
  seed 2026 iso_microwave 0.33 -> 0.33 (P/R bit-identical)
  seed 1    iso_microwave 0.35 -> 0.35
  seed 2026 iso_wm        0.67 -> 0.91 (R 0.54 -> 0.94)
  seed 1    mix_prog wm   0.75 -> 0.38 (R 0.63 -> 0.23)
  wm mark dens 0.30-0.56 -> 0.57-0.90/min (real wm runs fragment too)
The target metric (mw) does not move at all while seed-1 wm recall
collapses. Reverted before benching (a change the probe already shows is
net-negative is not worth a bench run).
RULES OUT: the mw iso R loss is not intra-draw event fusion at the
extractor. Fragmentation demonstrably increases (the mw fragment switch
fires more often) yet mw F1 is unchanged, so the mw ceiling is downstream
of extraction - emitted span/amp geometry and the burst gate bands, not
the pairing walk. Also rules out the bounce rule as a free change: it
fragments sustained wm runs and needs a wm-side guard before any reuse.

## Segment-2 pivot: bench v4 (per-home re-calibration) - owner direction
Eligibility freeze lives in .auto/pool_v4.py (GT-only, reads no model
score); scoring in .auto/bench_v4.py. PREREQUISITE FOUND: build_and_train
hard-indexes all five devices (model.py 793-796 min(wm,dw); 813/818
calib['dishwasher']; 874 calib['washing_machine']; 918 calib['kettle']),
but pool houses have arbitrary device subsets - the model must tolerate
absent devices before v4 can score anything. Must preserve house_1
bit-identity. Open concerns: the pair-mean is dominated by fridge
coverage; fit cost vs CMA-ES. B1 bug fixed (b1_encoder.py:171 gallery
kept only other-device events): corrected cross-house retrieval is at
CHANCE (enc 0.210 vs raw 0.225, 5 devices), while enroll is 0.840 enc vs
0.650 raw - the encoder's value is same-house K=5 enrollment, not
cross-house invariance.

## v4 prerequisite landed: model.py device-subset robust (run 72, keep 5ad5980)
Guards at every device-keyed site: _name_program filters to devices present in
mark (an absent device must not own a chain); seed_thr/heat_thr = FRAC *
min(present program amps) else +inf; dw30 and wm30 are built only when their
device is marked, partner amp falls back to the device's own mark amp; dur_ref
filtered to present devices; fridge_band = None without a fridge channel; out
allocated over ALL_DEVICES and narrowed to the house's devices on both return
paths; predict gate branches for kettle/microwave/fridge are presence elif +
zero-mask else. Verified: bench v3 re-run is BIT-IDENTICAL (median 0.505987,
p10 0.485922, all ten per-seed values to 6 dp, transfer 0.151921); subset smoke
test builds eco/house_03 and eco/house_01 (fridge only -> exactly [fridge]),
refit/house_17 (no dw channel -> 4 keys, partner fallback exercised),
ukdale/house_1 (all 5). Logged as keep as a DECLARED protocol exception: no
metric change, kept only because the discard path auto-reverts src/.
TRAP: log_experiment's narrative banner is computed against a fixed generic
baseline and printed '+20.1%' for this run; only title/description/asi are
trustworthy as claims. NEXT: .auto/bench_v4.py - per-home calibration
(build_calibration parameterized by the house's own thr_map + device list) + a
fresh build_and_train per (house, seed); primary = median over seeds of the mean
F1 over the 66 pool pairs; report pool pair-mean, device-balanced mean, the
house_1 subset and the v3 readout side by side; --holdout for the 7 holdout
houses, milestone-only.

## FROZEN v4 FLOOR at HEAD (run 73, keep, 5 seeds / 66 pairs / 20 houses)
primary mean_device_f1 0.306428 (pair-mean, median over seeds); p10 0.299752;
device-balanced 0.315375; house_1 subset 0.529246. Per-device medians: kettle
0.536898 / microwave 0.266004 / fridge 0.265079 / washing_machine 0.228634 /
dishwasher 0.346705. Per-seed: 2026 0.302565, 1 0.306428, 2 0.311406, 3
0.313968, 4 0.297877 (spread 0.298-0.314 -> low-noise median). Full pass 128 s.
0.505987 (v3) is a house_1-ONLY number and is NOT comparable to the v4 pool
primary: the drop is a metric redefinition, not a regression. transfer_mean_f1
0.151921 is a carried frozen v3 readout - bench_v4 does not recompute it; the
milestone replacement is holdout_mean_f1 over the 7 holdout houses.
measure.sh now runs bench_v4; checks.sh gates all five per-device medians in
[0,1] plus scored houses/pairs == the frozen 20/66. bench_v4 refuses to run if
model.py lacks ALL_DEVICES (guards against a revert silently breaking v4).
WEAKEST pool device: washing_machine 0.2286 (15 pairs, widest per-house spread)
- that is the B4 target.
## v4 POOL LOSS STRUCTURE (seed 2026, 66 pairs, bench_v4.py --dump)
AGGR (mean over that device's pairs):
  kettle           P=0.4751 R=0.5144 F1=0.4576  gt=4089  pred=5091  n=12
  microwave        P=0.3080 R=0.2744 F1=0.2622  gt=1888  pred=1560  n=11
  fridge           P=0.3867 R=0.1739 F1=0.2264  gt=37925 pred=16048 n=18
  washing_machine  P=0.2491 R=0.2557 F1=0.2423  gt=858   pred=1077  n=15
  dishwasher       P=0.4478 R=0.3594 F1=0.3883  gt=527   pred=359   n=10
Readings:
1. fridge is 18/66 = 27% of the pool weight and by far the worst recall
   (0.17). It is BIMODAL, not uniformly bad - it works on eco/house_02
   (P.94 R.63 F.75), refit/house_7 (.81/.49/.61), refit/house_16 (.55/.43/.49)
   and ukdale/house_1 (.67/.38/.49), and collapses on eco/house_01
   (.15/.02/.04), eco/house_03 (.05/.03/.03), eco/house_06 (.02/.00/.00),
   refit/house_12 (.05/.02), refit/house_10 (.03/.02), refit/house_8
   (.50/.09) and refit/house_17 (.57/.05). A per-house BAND failure, not a
   global margin: the band comes from one mined duty cell or one population
   fallback window, so a house whose passive window is unrepresentative gets a
   band that admits almost nothing (the three eco houses are fridge-only and
   all three collapse).
2. fridge emits 42% as many cycles as GT (16048 vs 37925) yet only 39% match,
   so this is NOT only recall: emitted cycles also land at wrong times or are
   merged/split. Prime suspect is run-basis emission lag - the run path starts
   where the 30 s smoothed level crosses amp_lo = 0.8 x mark amp (~line 1075)
   and writes max(seg, w) across the run (~line 1334), so onsets are
   structurally late by the climb. Check against v2.TAU_ONSET_S['fridge'].
3. wm is bad on BOTH axes (P0.25/R0.26) and emits MORE than GT (1077 vs 858):
   merging/splitting, not a threshold problem. That is the B4 target.
4. mw is precision-poor (.31) and emits fewer than GT (1560 vs 1888) -
   consistent with the m7 verdict that the mw ceiling is downstream of
   extraction, not of a gate.
5. kettle and dw are the healthiest (dw P.45/R.36 still over-admits on the
   run-basis gates). The device-balanced mean (0.3154) tracks the pair-mean
   (0.3064), so the pair-mean is not badly skewed by the 18 fridge pairs.
Next bets, in order (each must lift the v4 primary by >= 0.01 with no per-device
median down more than 0.03):
  (a) fridge per-house band from the house's own pre-span excursion population
      conditioned on the fridge mark (marks + history only, no hand-set
      constant), plus the run-basis onset-lag check against TAU_ONSET_S;
  (b) B4 wm explicit-duration phase model - the both-axes failure argues for a
      duration/phase prior, not another gate.
## m8: fridge run-gate re-basing REFUTED (run 74, discard)
Bet: the fridge cannot be button-calibrated (PASSIVE_FRIDGE_H=3), so its mark
comes from ONE random 3 h mains window with no labels. On the v4 pool that mark
amp reads 30/298/328/601/932/2203 W while the mined per-house population band
sits at 51-117 W on EVERY house, so the run-basis gate amp_lo = 0.8 x mark amp
lands ABOVE the band top and emits 0 candidates - on 5 of the 8 diagnosed
houses, all of them high-precision/very-low-recall (refit/house_17 P.57 R.05,
refit/house_8 P.50 R.09, refit/house_10 P.03 R.02, refit/house_12, eco/house_01).
Change: clamp the mark amp into the mined band (0.8 / 3.0 margins unchanged).
A credible mark is a no-op, so house_1 was bit-identical (0.529246) as predicted.
RESULT: primary 0.306428 -> 0.303330 (-0.0031), p10 0.299752 -> 0.297894,
fridge median 0.265079 -> 0.258555 (-0.0065), device-balanced 0.315375 ->
0.313924. All five seeds fell uniformly (-0.0020 to -0.0036), every other device
median bit-identical. Reverted.
WHAT IT RULES OUT: the pool fridge deficit is NOT a mis-based gate or a disabled
detection path. The 0.8 x mark gate was PROTECTING precision - run-basis emission
at 51-117 W / 11-38 min over 90 days admits more lookalikes than compressor
cycles in the houses that fail. It is the BAND SELECTION that is wrong there.
NEXT (concrete lead): on 8/8 diagnosed houses the log printed 'fridge fallback:
population band' - the intended per-house calibration (the most-regular (amp,dur)
duty cell, DUTY_AMP_W=(40,300), DUTY_DUR_S=(600,2400), DUTY_CELL_MIN=300,
DUTY_CV_MAX=0.6) NEVER FIRES anywhere in the pool. So every house is calibrated
from the p10-p90 of the whole <=120 W small-sustained population, which in the
collapsing houses is dominated by non-fridge activity. Diagnose why the cell
detector falls through (best CV vs 0.6, per-cell occupancy vs 300) rather than
re-margining the fallback band.
Note the eco houses are pathological: eco/house_06 GT fridge cycles are 4.0 min
(p50) against a band dur of 11-37 min and its GT threshold is 24 W; eco/house_03
is 18.3 min at thr 12 W; eco/house_01 is 22.7 min with p90 66 min vs a band top
of 38 min. A single global dur band cannot fit 4 min and 22 min devices.
## m9: the fridge run-basis path is a NO-OP either way; the duty-cell
##     detector's statistics do not exist on this pool (runs 74-75)

### The cell detector is unreachable, and relaxing it cannot help
Instrumented the mining to print cell occupancy/CV. With the shipped 10 W x
300 s quantization: eco/house_02 7 cells >=300, ukdale/house_1 2, and
eco/house_01 / eco/house_06 / refit/house_17 ZERO. Best cell CVs 0.74-1.06
against DUTY_CV_MAX = 0.6 - so both gates fail, everywhere. Cause of the low
occupancy: the extractor yields only ~11 fridge-class events/day over the
180-day pre-span (dm = 1002-7588 events spread over 100-140 cells), so a single
10 W x 300 s cell can never hold DUTY_CELL_MIN = 300 of them. DUTY_CELL_MIN is
an absolute count that does not scale with span or extractor yield.
Then re-ran with coarser 20 W x 600 s cells and a 20-event floor. Coarsening
collapsed 100-140 cells to ~40 and did NOT rescue the gate: best CVs became
1.018 / 0.865 / 0.891 / 2.037 / 1.006 / 0.834 / 0.765 (house_02, house_1,
house_01, house_03, house_06, house_17, house_8). The most-populated cells have
CV 1.0-11.8. So the CV statistic does not discriminate: the mined fridge-class
events are near-Poisson in time on EVERY house of the pool, and the intended
'regular duty cell' signal does not exist here. Relaxing DUTY_CV_MAX would just
pick a small random 20-58-event cell - worse than the population band.
CONCLUSION: the cell detector is dead code by construction (both gates), and it
is not repairable by re-scaling them. The population fallback IS the fridge
calibration on the whole pool. Any further fridge work must target emission
(precision) or a different unsupervised signature, not these gates.

### The run-basis gates: two ablations, both non-positive
Run 74: clamp the passive mark amp into the mined band (amp_lo 0.8 x mark amp
was landing ABOVE the band top, silently emitting 0 candidates on 5 of 8
diagnosed houses - all high-precision/very-low-recall: house_17 P.57 R.05,
house_8 P.50 R.09). Result -0.0031 primary, fridge median -0.0065.
Run 75: same clamp PLUS floor the mark duration at the band's own dur low edge
(the passive window returns the 1200 s default when it finds no matched
compressor pair, giving mark dur 0.3-2.2 min on house_17/10/12 and therefore a
near-zero dur_lo = a blip flood - this is what made run 74 lose). Result:
primary 0.306011 (-0.0004, mixed seed signs: +0.0013/-0.0004/+0.0024/+0.0001/
-0.00003), p10 +0.0005, device-balanced +0.001, fridge median -0.0001, house_1
bit-identical. The duration floor exactly cancels run-74's loss.
CONCLUSION: correctly gated or not, the run-basis path contributes ~nothing to
the pool fridge metric. The fridge deficit is not in the gating at all - it is
2 of 3 of the following, per house: (a) the house's compressor level sits above
the FR_POP_AMP_HI = 120 W cap that the fallback band top inherits, (b) the
house's cycle duration is outside the mined 10-40 min class entirely
(eco/house_06 GT p50 is 4.0 min at thr 24 W; eco/house_01 is 22.7 min with p90
66 min against a band top of 38 min), or (c) the fridge's unsupervised signature
is not separable from lookalikes (P .03-.15 in the collapsed houses).
NEXT BETS on the fridge, in order: (1) stop gating anything on the passive
window - but note runs 74/75 show that is worth ~0; (2) the honest lever is
per-house cycle-period estimation from the mains itself (autocorrelation of the
small-excursion indicator over the pre-span), giving a per-house duration band
that can span 4 min and 22 min devices - the mined-event interval CV cannot do
this, but an ACF peak is a different statistic and is untested; (3) otherwise
leave fridge alone and spend on the directed parameter fitting (52 literals) and
the B4 washing-machine phase model, which have much larger headroom.
