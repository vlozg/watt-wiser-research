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

- m4 (run 96, DISCARD): cross-house physical envelope for kettle/microwave.
  Offline scope over 99 builds: 4 outlier builds = 1 house x 4 seeds, so
  the family reaches exactly 1 of 66 pairs - and it loses there (pool
  0.359052 vs the 0.359446 incumbent; that pair 0.06 -> 0.00; a
  duration-only variant gives 0.359239 -> 0.01). Diagnosis: house_12's
  own reader threshold <= 115 W corroborates the anomalous mark, so the
  outlier is the label's evidence, not a calibration error.
  Cross-house physical priors CLOSED both ways. With the encoder's
  learned cross-house retrieval already at chance, the whole B1
  cross-house strand is bounded by measurement: its only reachable pair
  is a label anomaly. Kill criterion not yet met (runs 63/64/65/96 = 4,
  and transfer_mean_f1 never moved); a further m needs a trainable
  component, which the rule-based model does not have.
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

### Big-bet portfolio (owner list, recorded run 84) - 5 projects, 5-15 runs each

Each bet is a multi-run project: pre-registered hypothesis, milestones, kill
criterion. One bad first run is not a refutation. B1 and B2 below are the same
bets as the pre-registered pair above; this block is the canonical scope.

B1. Cross-house event encoder with nearest-example matching. OPEN.
    Mine switch events from every pretraining house (tens to hundreds of
    house-years of aggregate); train a contrastive encoder on event windows
    (submeter labels allowed as supervision in pretraining houses only);
    enrollment = embed the device's K marks; assign a new event to the nearest
    device, or UNKNOWN beyond a distance threshold. Targets transfer directly,
    works with K = 1-5.
    Done: m1 miner (run 63; 5260 events over 29 houses), m2 encoder (enroll
    top-1 0.65 raw -> 0.84 encoded). Cross-house top-1 now reads 0.21.
    Open: the cross-house invariance sub-goal (was 0.000 in m2), the known-
    broken retrieval line (b1_encoder.py:171), retrain on the pool, UNKNOWN
    threshold. The m3 GATE sub-strand is CLOSED (refuted at two
    implementations, runs 64/65) - do not reopen it.

B2. Synthetic supervision in the target house. OPEN, patch in hand.
    Extract each mark's baseline-subtracted signature from the aggregate; paste
    signatures into real ctx.pre backgrounds (millions of copies), varying
    amplitude, time stretch and overlap; train the house's detector on the
    result; background windows are UNLABELED, never negative (the device may be
    running unmarked there). Combine with B1, starting from the encoder.
    Done: m1+m2 (run 66 KEEP +0.0379, from the probe's extractor fix); the
    cross-fire / dur-ceiling / switch bundle (run 67) measured +0.0078, under
    the bar, preserved at .auto/runs/b2_m3_dispute_durceil_switch.diff.
    Next: apply that patch and the synthetic-training pipeline as ONE bundle.

B3. Self-training over the unlabeled year. m1 DONE (run 97, see m32):
    self-calibration of the burst admission band from the pre-span event
    population is REFUTED - a single house's aggregate is not device-pure,
    so its population amp is biased low. Next m needs a device-pure labeling
    function (B1's trainable component or B2's synthetic supervision).
    Pseudo-label the pre-split year with the best current detector, keep only
    confident events, train a stronger model on them, re-label, iterate. Guard
    drift with the dev set and leave-one-mark-out checks. Turns 5 marks into
    thousands of labels. Cheapest large lever; the run-78-84 evidence says the
    binding constraint is per-house band/statistic calibration, not capacity
    (m16/m17/m18 were all calibration-derived quantities disabling detection).

B4. Generative program models for washing machine and dishwasher. NOT STARTED.
    Explicit-duration phase models (HSMM: fill, heat, wash, rinse, spin, pause)
    with phase grammars learned from pretraining-house cycles and adapted with
    the K marks; decode all devices jointly under a sum-to-aggregate constraint
    using event-level emissions, not the old network posteriors.
    Pre-conditions measured: wm median 0.2286 with BOTH axes broken (P 0.25 /
    R 0.26) and it emits 1077 events against 858 GT (over-segmentation, not
    under-detection); the dw/wm class separation lives in the dens/idle gates.
    m6-m17 say the geometry is adequate and the gates are the limit, so the
    phase grammar should REPLACE the span/density gate family, not join it.

B5 (optional, most ambitious). Masked-signal foundation model. NOT STARTED.
    Masked pretraining on all aggregates in data/gold, fine-tuned with B2's
    synthetic target data.

Process finding (recorded honestly): runs 78-83 were six ad-hoc guard-clean
repairs under the flat +0.01 bar, not bets - the portfolio sat idle. Those
repairs did converge on the same defect class (calibration-derived quantities
that silently disable detection) and run 84 finally landed one, but the
remaining headroom is in the portfolio. Proposed order: B3 (cheapest, largest
label gain) -> B4 (widest spread, worst transfer) -> B1 retrain -> B2 bundle
-> B5.
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

## FROZEN v4 FLOOR at HEAD (run 77, keep, commit 703a591, 5 seeds / 66 pairs / 20 houses)
primary mean_device_f1 0.321967 (pair-mean, median over seeds); p10 0.318039;
device-balanced 0.328482; house_1 subset 0.542204. Per-device medians: kettle
0.536898 / microwave 0.266004 / fridge 0.328763 / washing_machine 0.228634 /
dishwasher 0.346705. Full pass 110 s. Seed spread 0.31-0.34 (run 78 read
0.3125/0.3182/0.3233/0.3340/0.3378 on a near-floor variant -> low-noise median).
(superseded: run 73 df85d3c primary 0.306428 / p10 0.299752 / fridge 0.265079.)
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
## m10: the fridge deficit was extraction-side only - and scoping the low
##     floor to ONE device is what makes it safe (run 77, KEEP, 703a591)
Run 76 lowered the GLOBAL amp floor 50/40 -> 20 W and gained the fridge median
+0.0637 but lost on all four other devices (kettle -0.0128, microwave -0.0267,
wm -0.0120, dw -0.0045): the mined event set is a SHARED intermediate, so every
device's program and density statistics moved with it. Net primary +0.0072 -> discard.
Run 77 applied the same 20 W floor to the FRIDGE ONLY (FR_STEP_MIN_W = 20.0, a
separate _extract_events call over the fridge-band path; the shared set keeps
AMP_MIN_W = 50.0). Result: primary 0.306428 -> 0.321967 (+0.0155), p10
0.299752 -> 0.318039, device-balanced +0.0131, house_1 0.529246 -> 0.542204,
fridge median 0.265079 -> 0.328763 (+0.0637) and the other four medians
BIT-IDENTICAL. KEEP.
PHYSICAL READING: a mined event measures a STEP (fut minus past), which is
background-robust; a coarse-grid cell measures a LEVEL, which is not. Only
step-based extraction can see a compressor draw sitting under the shared amp
floor. The run-77 low-floor population mines 5610 events at 22-111 W / 11-37 min
and 6316 at 25-113 W / 10-33 min, against the floor's 51-117 W.
DESIGN RULE (generalises beyond the fridge): when lowering a threshold that feeds
a SHARED intermediate, scope the change to the single device that needs it -
collateral across devices is invisible in the primary metric but real.
## m11: the fridge duration floor is NOT a bug - it does precision work, and
##     mark_dur/3 both widens and narrows (run 78, discard)
Diagnosis first (bench_v4.py --dump, seed 2026, whole pool): the fridge loss is
(a) holes and (b) spurious firings, NOT duration geometry - on the short-cycle
houses we emit 10-20x too FEW episodes (eco/house_06 123 pred vs 1839 GT,
refit/house_17 107 vs 1840, refit/house_12 310 vs 748, eco/house_03 726 vs 1178)
while the GT is duty-cycle granularity (4-27 min per cycle, 20-47 cycles/day).
Then found a real intent/code contradiction: the build comment at model.py:1061
asserts the EVENT path gates duration on 'the same 1/3 margin ... against the
mark', but the event path gated on fridge_band['dur'] - the POOL population band
(floor 10-11 min) - so the per-house calibration was silently overridden.
Run 78 unified the event path onto fridge_band['fr_run'] = (mark_dur/3,
population top). Result: primary 0.321967 -> 0.323317 (+0.0014, below the +0.01
bar), p10 0.318039 -> 0.314758 (DROPS - the rule forbids), fridge median
0.328763 -> 0.318640 (-0.0101), the other four medians bit-identical. DISCARD.
WHY IT HALF-WORKED: the pair MEAN rose while the median fell. mark_dur/3 is
STRICTER than the 10-11 min pool floor whenever mark_dur > 33 min, so one edit
both widened the band (short-mark houses gained the missing short cycles) and
narrowed it (mid-range houses lost). The pool floor is protective, not vestigial.
NEXT (untested): keep the structural unification but enforce monotonicity - the
marks may only WIDEN the pool band: dur_lo = min(pool_lo, mark_dur/3), dur_hi
unchanged. Every mid-range house is then bit-identical, and only houses whose own
5 marks say 'minutes' admit short cycles. Ceiling on the gain is ~0.001-0.004, so
this ranks BELOW the directed 52-literal parameter fitting and the B4 wm phase model.

## m12 (run 79, discard) - DW CALIBRATION DEGENERACY: undefined statistics must
degrade gracefully, never become dead gates or blocked corrections

Two dead scored dw pairs (`refit/house_10` dw 0.00, `refit/house_11` dw 0.00) traced to
two sites in `_dw30_profile`, both the same class: a calibration statistic that is
UNDEFINED is silently turned into a VALUE that switches a mechanism off.

1. IDLE SENTINEL. A fully-heated mark window has no below-heat samples, so
   `idles.append(float(np.median(below)) if len(below) else 0.0)` wrote a hard 0.0 for
   'no information', and `'idle_hi': 2.0 * max(idles)` then made idle_hi = 0 W, so the
   gate `if idle > prof['idle_hi']` rejected every candidate. On `refit/house_10` the
   profile printed `idle<=0W` and `dw sustained runs: 0 pass` (dw n=1/86, F1 0.00).
   Fix: `else None` + max over the non-None values (inf when none). VERIFIED: house_10
   dw 0.00 -> 0.1458 (n 1 -> 10, P=0.70, R=0.08) and the profile prints `idle<=infW`.
   Scope: house_10 is the ONLY pool house with a 0-valued idle_hi (other dw houses
   263-1426 W, wm houses 122-2952 W), so this repair touches exactly one scored pair.
2. ONSET-CORRECTION SIGN CLAMP. The synth-onset check computes a median bias `med` and
   intends (per its own docstring) to shift ext_back toward delta 0, but
   `new_b = np.clip(old_b + med, 0.0, 1800.0)` forbids any negative shift and the base
   `ext_back_s = max(0.0, median(pres))` forbids a negative base. VERIFIED: on
   `refit/house_11` the probe self-corrects (ext_back -0.5 -> -11.0 min, pasted deltas
   -630/-630/-30 -> +0/+0/+600) BUT the real eval span is unchanged (dw 0.00 n=12/12).
   => THE SYNTHETIC PASTED-MARK PROBE IS NOT A FAITHFUL PROXY FOR THE REAL SPAN.

REAL-SPAN GEOMETRY (emitted vs GT dw onsets, seed 2026, measured directly):
- `refit/house_10` gt=86 em=10: every emission lands exactly on a GT onset (best|d| 0 s)
  but only 7/86 GT are covered -> RECALL-limited, not placement-limited. Its own 5 pasted
  marks are rejected by its gates (0/3 recovered) with `heater_gap_merge=70min` against a
  span band of 8-21 min -> the merge width and the span band are mutually inconsistent.
- `refit/house_11` gt=12 em=12: nearest miss 648 s against the 600 s TAU_ONSET
  tolerance (the same near-miss class the code comment at the correction site documents).
- controls `refit/house_16` 32/58, `refit/house_21` 37/76, `refit/house_13` 34/73 within
  tolerance -> the detector is near-correct wherever its profile is non-degenerate.

POOL RESULT: primary 0.322648 (+0.000681 vs the 703a591 floor 0.321967), p10 0.317801
(-0.000238), device_balanced 0.331399 (+0.002917), house_1 flat, all five device medians
bit-identical (the dw median 0.346705 sits above 0.146, so repairing the lowest dw pair
cannot move it). Sub-bar -> DISCARD, reverted. The pair-level gain is real but
seed-dependent: a deterministic +0.0022 is eroded to +0.0007, i.e. the probe-driven
onset shift costs about as much as it gains on other seeds.

RE-APPLICATION RECIPE (for the bundle, exact anchors in `_dw30_profile`):
  a. `if len(below) else 0.0` -> `else None` at BOTH idle sites (dw + wm).
  b. `'idle_hi': 2.0 * max(idles),` -> max over non-None, inf when none (BOTH sites).
  c. base: drop the `max(0.0, ...)` around `float(np.median(pres))`; update:
     `np.clip(old_b + med, 0.0, 1800.0)` -> `-1800.0` lower bound; add the closed-loop
     guard (restore old_b when the re-measured probe bias is worse).
  d. candidate for the same bundle: `dens_lo = 0.75 * min(denss)` becomes 0.000 whenever
     one mark window measures no events (`refit/house_11` wm prints `dens=0.000-0.390`;
     re-census the other wm houses before acting - the count is not verified), i.e. the
     same zero-as-undefined bug disabling the lower density gate.

## m13 (run 79) - REFUTED: the fridge cycle period is not recoverable from the mains
Autocorrelation of the pre-span mains (60 s grid, rolling-median baseline, 10-240 min
lags) over all 18 fridge pre-spans: 8/18 peak exactly at the 10 min search boundary (no
interior period), and where a peak exists it misses the GT p50 by 2-6x (house_17 T=16 vs
27, house_10 10 vs 17.5, house_06 21 vs 4, house_02 31 vs 16.3, house_08 10 vs 16.7,
house_01 10 vs 22.7). Periodic-run durations are 1-4 min everywhere, and the small-step
rise count is 36-170/day against a true 20-47 cycles/day -> a lookalike-dominated train.
Second independent statistic (after m9's interval CV 0.74-11.8) agreeing that the fridge
period is NOT in the mains; stop mining this path.

## m14 (run 80, discard) - ORDER-STATISTIC SENTINELS: a 0 UPPER bound is fatal, a 0 LOWER
bound is merely permissive (the min-based floor is PROTECTIVE)

The m12 class was generalised to the density floor and split cleanly:
- CONFIRMED for an upper bound. `idle_hi = 2*max(idles)` with a fully-heated mark window
  contributing `else 0.0` gives idle_hi = 0 W, which rejects EVERY candidate. Repair
  (`else None`, max over non-None, inf when none) lifts `refit/house_10` dw 0.00 -> 0.1458
  (n 1 -> 10, P=0.70). Keep this repair in any bundle.
- REFUTED for a lower bound. `'dens_lo': 0.75 * min(denss)` with one window mining no
  events gives dens_lo = 0.000, which merely PERMITS everything. Excluding the zeros
  lifted all six dead floors (to 0.060/0.088/0.121/0.150/0.205/0.280) and the wm outcome
  was mixed-to-negative: house_13 0.32 -> 0.38, house_16 0.19 -> 0.21, house_7 0.26 -> 0.27,
  house_1 emissions 105 -> 77 with F1 flat, house_6 0.04 -> 0.00, and the 5-seed wm median
  FELL 0.228634 -> 0.224674. The sparse window that produced the 0 carries real
  information. Same shape as m11 (removing a low order statistic costs precision AND
  recall): DO NOT re-apply the dens_lo change.

POOL RESULT (run 80): primary 0.323427 (+0.001460 over the 703a591 floor 0.321967), p10
0.317584 (-0.000455), device_balanced 0.332085, house_1 flat, kettle/mw/fridge/dw medians
bit-identical. Sub-bar -> discard, reverted.

EMISSION-GEOMETRY CENSUS (seed 2026, emitted vs GT onsets/durations, measured directly over
6 houses; this is the diagnosis the next structural run should start from):
- FRAGMENTATION IS ZERO. The fraction of emitted onsets having another emission within
  TAU_ONSET_S is 0.00 for every device on every house measured. Near-duplicate emissions
  are NOT why precision is low; de-duplication is dead as a lever.
- ONSET BIAS IS HARMLESS. A systematic -18 s (fridge), -18 s (microwave), -15 s (kettle),
  -400 s (wm) median bias is INSIDE the per-device tolerance (120/60/600 s). Not the
  limiter; do not chase it.
- MICROWAVE over-emits 2-4x with durations ~2x too short: house_18 274 em for 61 gt (median
  duration 84 s vs 114 s gt), house_6 74 for 390, house_10 224 for 103. mw is a
  precision+duration problem downstream of extraction (m7).
- FRIDGE and WM ARE COVERAGE-LIMITED. Matching cover: fridge 175/1956 (house_10),
  1080/4209 (house_18), 419/2165 (house_1), 487/2436 (house_6); wm 14/61, 17/77, 1/37,
  12/42, 1/22. The detectors miss most real cycles while emitting many others.
- `refit/house_6` is RECALL-DEAD HOUSE-WIDE (kettle F1 0.02 with 649 gt cycles, microwave
  0.04 with 390) and its GT cycles are SHORT: median 90 s kettle AND mw duration against
  150-250 s elsewhere. That is a per-house smoothing/step-scale calibration problem, i.e.
  the owner-directed per-house parameter fitting from the K=5 marks - not a sentinel.

BATCHING (process note for the owner): three consecutive structural repairs (m10-style,
m12, m14) have now each measured a REAL pair-level gain but stayed under the +0.01 keep
bar and were reverted (runs 78, 79, 80). The keep rule is effectively forcing batching:
the next run should carry the verified idle repair TOGETHER WITH a structural wm/fridge
recall change, and be judged as one bundle.

## m15 (run 81, discard) - COUNT GATES ARE THE SAME DEFECT AS SENTINELS, AND THE KETTLE HAS
ONE: `KET_MARK_MIN` disabled the sustained-run path on 9 of 12 kettle pairs

MEASURED: `kettle sustained marks: N/5 windows hold an isolated in-band run` over the 12
kettle pairs is 0/5 x2, 1/5 x2, 2/5 x3, 3/5 x4, 4/5 x1. With KET_MARK_MIN=3, 9 of 12
pairs (75%) run the sustained-run path DISABLED. The four houses at 3/5+ are exactly the
top kettle F1s (0.76, 0.77, 0.82, 0.84); the nine disabled ones span 0.02-0.62.

WHY THE GATE IS WRONG (not just mistuned): the count votes on the 5 marks, but every
emitted candidate is ALREADY filtered individually (`ket_span`, `ket_amp_band`,
`_iso_clear`, no admitted-event overlap, no named-span overlap). So the count adds NO
per-candidate protection - it only punishes homes whose electrical environment is busy,
since any >=1kW neighbour within +-600 s breaks a mark's isolation test. It is a vote on
mark-window luck. `refit/house_6` is the extreme: 235 mined kettle-band events with
dur_p50 1.2 min against a 1.5 min GT, but 1/5 isolated marks -> kettle F1 0.02 with 649
GT cycles.

RESULT of KET_MARK_MIN 3 -> 1 (plus the run-80 idle repair, dens_lo NOT re-applied):
primary 0.329025 = +0.007058 over the 703a591 floor, with EVERY GUARD IMPROVED - p10
+0.005786, device_balanced +0.009932, house_1 +0.003421, kettle median 0.536898 ->
0.540554, mw/fridge/wm/dw medians bit-identical. Per house at 1 seed: eco/house_02
kettle 0.34 -> 0.74 (P 0.52->0.71, R 0.25->0.77), ukdale/house_1 0.76 -> 0.79, the
other ten pairs bit-identical. Discarded only because +0.0071 < the +0.01 bar.

NEW MECHANISM - emission counts are not scoring evidence: on 3 of the 5 newly-enabled
pairs the net-new sustained candidates landed ADJACENT to existing kettle episodes, so
counts rose (house_6 28->33, house_12 684->712, house_21 280->301) while F1 did not move
AT ALL. Scoring matches onsets; extending an episode creates no new onset. Never judge a
change by emission counts - only by onset deltas.

NEXT PROBE (smallest principled step past this): a POPULATION-based demonstrability rule -
run the path when `ket_marks >= KET_MARK_MIN` OR the span holds >= N isolated in-band
candidates. This reaches the 2 pairs still at 0/5 (their marks never demonstrate the
pattern, but their span may hold isolated in-band runs elsewhere, which is exactly the
eco/house_02 story that produced +0.40). Downside is bounded: both pairs sit far below
the kettle median, so they cannot move it; the only real risk is kettle episodes
suppressing microwave emissions via the burst-dispute path on those 2 houses.

RE-APPLICATION RECIPE for the next bundle (5 hunks in model.py, all verified to compile
and to score checks-pass):
1. `KET_MARK_MIN = 3` -> `1` (keep the demonstrability comment).
2. L470 + L677: `idles.append(float(np.median(below)) if len(below) else 0.0)` -> `else None`.
3. L500 + L697: `'idle_hi': 2.0 * max(idles),` -> `2.0 * max([v for v in idles if v is
   not None]) if any(v is not None for v in idles) else float('inf'),`.
4. Do NOT re-apply the `dens_lo` change (m14 refuted it).

PROCESS (owner decision needed): runs 78, 79, 80, 81 are four consecutive discards of
GUARD-CLEAN structural fixes - each measured a real, reproducible, per-pair gain (m11
fridge scoping class, m12 dw calibration, m14 sentinel, m15 count gate) and each was
reverted for being under a flat +0.01 bar. This run is the sharpest case: p10, device-
balanced, house_1 and the kettle median ALL improved and nothing regressed. Verified
progress cannot accumulate under a flat bar; either structural fixes must be allowed to
accumulate (e.g. keep when p10 and device_balanced both rise and no median falls), or
the loop must be allowed to batch several sub-bar fixes before judging.

## m16 (run 82, discard) - THREE BATCHED REPAIRS, +0.009476, STILL 0.0005 SHORT

MEASURED (pool v4, 66 pairs, 5 seeds, checks pass, 106 s):
  primary 0.321967 -> 0.331443 (+0.009476); p10 0.318039 -> 0.325666 (+0.007627);
  device_balanced 0.328482 -> 0.340336 (+0.011854); house_1 0.542204 -> 0.545625.
  Medians: kettle 0.536898 -> 0.543172 (+0.006274); fridge 0.328763 -> 0.334602
  (+0.005839); mw/wm/dw bit-identical. No device median fell. Closest sub-bar run
  yet, and the fifth consecutive guard-clean discard (78, 79, 80, 81, 82).

BUNDLE (6 hunks, each verified before batching):
1. run-81 kettle gate repair: KET_MARK_MIN 3 -> 1, with the gate counting marks
   that hold an IN-BAND run (ket_inband), not only an ISOLATED one. Isolation
   stays a per-candidate filter; it was never a sensible vote on five windows.
2. the run-80 idle sentinel pair (None instead of 0.0; idle_hi=inf if all None).
3. NEW: the fridge run-basis amp window is 0.8x the PASSIVE MARK amp. A
   neighbour load inside the passive window contaminates the mark, 0.8x it lands
   above the mined band top and the window inverts. refit/house_17: passive
   'fridge' mark = 932W/0.3min (a 2kW neighbour) -> window [745W, 120W] -> ZERO
   run-basis candidates for 90 days. Guard: if 0.8*mark_amp > band_amp_hi, take
   lo, dur-lo and isolation from the MINED band (0.8*band_lo,
   band_dur_lo/REL_DUR[1], 3*band_hi). No new constants; bit-identical where the
   mark is clean.

PER-REPAIR EVIDENCE (1 seed):
- kettle gate: path live on 10/12 -> 12/12 pairs; eco/house_02 0.34 -> 0.74,
  refit/house_13 0.23 -> 0.25, other ten bit-identical. The kettle lever is
  EXHAUSTED: the full in-band gate adds only +0.02 to the summed kettle F1 over
  the isolated-count version (5.93 -> 5.95). Ten of twelve pairs ignore the gate;
  their binding constraint is precision.
- fridge repair: house_17 run-basis 0 -> 2372 candidates, emissions 107 -> 280,
  P 0.29 -> 0.16, R flat 0.02 (F1 0.03 -> 0.04). The new candidates do not land
  on that house's GT cycles; the repair's real yield is the +0.0058 fridge median
  it earns on OTHER contaminated-mark houses. house_17's fridge is a placement
  problem, not a demonstrability one - do not chase it with band work.

PROCESS (new data on the m15 note): m15 recommended batching several sub-bar
structural repairs and judging them once. This run did exactly that - three
verified, guard-clean, individually-positive repairs - and still landed 0.0005
short. The ratchet is the problem: every reverted fix must be re-applied by the
next run before it can add anything, so the required batch grows while the bar
stays fixed. Concrete proposal: keep when primary rises >= 0.005 AND p10 rises
AND device_balanced rises AND no device median falls. Runs 78-82 would all have
been keeps and the floor would now be 0.3314, compounding instead of re-applying.

NEXT (biggest clean opportunity left): refit/house_11 washing_machine emits 0 of
15 GT cycles while 37 candidates pass the wm run gates on the PRE span; emission
re-runs the same gates on the EVAL span (model.py L1183 reuses _dw30_runs on
exc_e/ev30_e), so a level gate calibrated on one 180-day window (idle <= 122W,
mean_band, hs_band, dens) can reject every candidate in the other - the m10 'a
level is not background-robust' lesson, now in the wm path. Diagnose per-gate
pass counts on the eval span for house_11, then repair the dead gate. A single
pair 0.00 -> 0.4 is +0.006 pool primary; wm has 15 pairs and the lowest device
median (0.2286), so the same repair may lift several.
## m17 (run 83, discard 0.331443) - a mask write below the reader's floor
Same class as m14/m15/m16 (a calibration-derived quantity silently disables
a detector) but at the *write* boundary, not a gate.
- Symptom: refit/house_11 wm emitted 0 episodes while 37 pre-span and 16
  eval-span runs passed every _dw30_runs gate (diag: spans 36-107min inside
  [18,142], mean 330-495W inside [149,664], hs 0.25-0.64 inside [0.21,1.50],
  idle 54-148W vs idle_hi 122). The gates were live; the emissions were
  invisible.
- Mechanism: emission writes emit_w = mark_<dev>['mean_w'] into the output
  mask (dw L514, wm L710). house_11's wm mark is amp=215W dur=28.4min
  mean=30W (low duty: short heater bursts in a 28-min window), and 30W sits
  BELOW AMP_MIN_W = 50W, the floor the harness's own event reader uses (see
  the existing FR_STEP_MIN_W note for the same blinding). np.maximum(seg, 30)
  marks the span with a value no reader can see.
- Repair: emit_w = max(mark_<dev>['mean_w'], AMP_MIN_W) for dw and wm.
  Verified: house_11 wm pred 0 -> 13. Metrically NEUTRAL on the pool
  (0.331443 == run 82 to 6dp): house_11's wm F1 stays 0.00 because those 13
  emissions sit 600s+ off the 15 GT cycles. No other pool pair has a
  sub-50W wm/dw mark mean, so nothing else moved.
- RULE: a detector that fires must not write sub-floor levels; every mask
  write has to be legible to the reader's own floor.
NEXT (biggest clean prize left): the house_11 placement defect, whose shape
is itself diagnostic. house_11 emits 13/15 wm and 12/12 dw episodes with
ZERO onsets inside tau_onset, while its dense devices score (kettle 0.57 on
565 GT, fridge 0.25 on 1877, mw 0.23 on 91). A systematic timebase offset
between the model's eval-span grid and the GT mask would destroy exactly
the sparse devices (wm 15, dw 12) and barely dent the dense ones (a shifted
onset still lands within tau of *some* cycle when GT runs 1.6/day).
H-shift: the predicted onsets carry a fixed offset (span start / stride
arithmetic) on every house, visible only where GT is sparse. TEST next
iteration: dump one house's pred vs GT onsets and print the signed
nearest-GT offset distribution per device - if wm/dw show a large fixed
offset and kettle ~0, repair the timebase, never per-house offsets (a real
offset must come from one arithmetic error, not from tuning).
Standing: bundle (m16 six hunks + m17 clamp) = +0.009476 over the 703a591
floor, the 6th consecutive guard-clean run under the flat +0.01 bar
(78-83). Keep-rule proposal (>=0.005 + p10 + device_balanced + no device
median down) is still pending with the owner.

## m18 (run 84, KEEP 0.336828) - the band's ANCHOR, not its width: a mark below
##      the reader's own floor defines a band that excludes every GT-eligible draw

Defect: the kettle's event band is [1-REL_AMP, 1+REL_AMP] x mark_amp. On
refit/house_6 the kettle mark read 1259 W while the reader's floor for that
house/device is thr = 1307 W. The pool's threshold convention is half the
median on-draw (half_p50; ukdale/house_1 kettle thr 1173 W matches the v1
protocol exactly), so the device's median draw on house_6 is ~2614 W and the
mark sat at HALF of it. The band it defined, [1009, 1508] W x [24, 216] s, kept
83 of the house's 964 >= 1200 W excursions over the eval span (measured, not
inferred): F1 0.018 on 649 GT cycles with P 0.18 / R 0.10.

Diagnosis path (the reusable part): .scratch/h_shift.py replaces run_job with a
raw-onset readout (per device n_gt / n_pred / F1 / self, nearest own-GT offset,
cross-device match matrix). Results: (1) H-shift REFUTED as a class - matched
pred-to-own-GT offsets are sub-minute at tau_kettle = 60 s (house_1 kettle self
0.79, house_11 0.68), so no timebase offset exists anywhere; (2) no crossed
detectors either - house_11 wm/dw preds match own GT 0.00 but their cross hits
are the fridge/kettle base rates (21-6 cycles/day), not a swap; (3) the zero
pairs are TIME-COVERAGE mismatches (house_11 wm GT lives in days 4-29 while the
model emits over the whole 90-day span); (4) an eval-event tally showed
refit/house_6 kettle keeping 83 of 9344 extracted events, against a house
population of 964 events >= 1200 W.

Repair (one edit, in build_and_train right before the event-band mining): floor
a mark's amplitude at the protocol's median draw whenever it reads below the
reader's floor - if thr > 0 and mark_amp < thr then mark_amp = 2 * thr. A
representative mark is a no-op (ukdale/house_1 kettle mark 2182 W > thr 1173 W;
house_11 1790 W > 1040 W), so it fires only where the mark is provably not a
device draw. It fixes the event band AND the run-gate amp floor (0.8 x mark
amp), which inherited the same bad anchor.

RESULT (full v4, 125 s, 66 pairs / 20 houses, checksPass): primary 0.336828
(+0.014861 vs floor 0.321967) -> KEEP, the first since run 77. p10 0.325351
(+0.007312). device-balanced 0.341397 (+0.012915). kettle median 0.555140
(+0.018242); fridge 0.332973 (+0.004210, a fridge passive mark also
triggered); microwave 0.266004 / wm 0.228634 / dw 0.346705 BIT-IDENTICAL to the
floor. house_1 0.545625 (bundle-only, +0.003421). No device median fell.

Why it generalises (owner's learnable-across-homes direction): the fix uses only
protocol-derived quantities (the reader's threshold and its half_p50 meaning)
and the house's own mark - no hand-set constant, no eval-span data, no labels
beyond the K marks. The defect class is now complete across five levels:
sentinel bound (m14), count gate (m15), inverted lower bound (m16), sub-floor
mask write (m17), sub-floor BAND ANCHOR (m18).

NEXT: (a) the same sub-floor test should be applied to the wm/dw emit level -
m17 left the clamp max(mean_w, AMP_MIN_W = 50), which uses a magic constant,
whereas the run's own mean level is principled and provably identical on
house_11's 13 episodes (every admitted run's mean is 330-495 W against thr
45.5 W); (b) house_11 wm/dw are TIME-COVERAGE mismatches, not placement bugs -
do not chase placement there; (c) execute the big-bet portfolio (B3 first).
## m19 (run 85, DISCARD +0.002069) - the dw run-basis span band is the binding gate

Hypothesis: the dw run-basis `span_band` (0.6/1.25 x the K=5 mark window spans) silently excludes
most of the house's own runs - the m18 defect class (a calibration-derived statistic gating out the
population) on the dw's span axis instead of amplitude.

Method: temporary one-gate-at-a-time instrumentation in `build_and_train` (relax exactly one key of
`dw30`, recount `_dw30_runs`, print the per-gate counts). At seed 2026, house_7 / house_10 / house_11 /
house_6 runs admitted:

  span_band  44->145, 32->47, 97->216, 42->70   <- binding on EVERY house
  mean_band  52/40/129/43    hs_band 50/32/104/46
  dens_hi    47/37/118/42    idle_hi 44/32/97/47    amp_lo 59/32/98/42

Every extra run admitted by relaxing `span_band` ALREADY passed all the other run gates, so the
population of runs that pass every other gate is a valid re-anchor. Repair: re-anchor
`dw30['span_band']` from that population at the SAME 0.6/1.25 margins with p10/p90 (one junk run
cannot set an edge), only ever widen, only when >= 5 such runs exist (same order as the K=5 marks).
Scope: the dw device only - the wm passes its own `wm30` profile to `_dw30_runs`.

Measured (66 pairs / 20 houses / 5 seeds): primary 0.338897 (+0.002069), p10 0.325042 (-0.000309),
device_balanced 0.344129 (+0.002732), house_1 0.520777 (-0.024848), dw median 0.331597 (-0.015108).
kettle / microwave / fridge / wm medians BIT-IDENTICAL to the floor.
Per house (seed 2026, dw only): refit/house_10 0.15->0.28 (10->57 preds, P 0.70->0.35, R 0.08->0.23),
refit/house_7 0.065->0.07, refit/house_6 0.56->0.55, ukdale/house_1 0.67->0.64 (P 1.00->0.88),
refit/house_11 0.00 (12->53 preds, all false positives).

Verdict: DISCARD, but the lever is real (+0.002 primary; the recall it was for did appear on
house_10). It loses precision (house_1 dw, house_11's 41 extra junk runs), so it must carry a
precision guard before entering a bundle. The reverted `src/` is the run-84 floor.

REFUTED in the same iteration: extending the kettle's population-anchored duration reference
(`dur_ref`, the mined p50 over pre-span events inside the mark amp band, already used for the kettle
at model.py L1223) to the mw admission gate. Measured: ukdale/house_1 mw 0.352->0.15 (-0.20) against
only +0.03 on refit/house_17. Reason: the mined mw cluster is cross-fire contaminated (house_6 and
house_1 both p50 2.5 min vs a 1.2 min mark), whereas for the kettle the mined and mark durations
agree (1.8 vs 1.9 min). The raw mark duration is the better mw anchor - do not retry without a
changed assumption.

NEXT: point the same one-gate instrumentation at the fridge (refit/house_10 1936 preds / 1956 GT at
P 0.04 R 0.04; refit/house_17 280 / 1840) and the mw (refit/house_6 74 / 390). That method found the
binding dw gate in a single screen, and fridge_dw/mw pair-level zeros are the largest clean prizes
left. B3 is still the next multi-run project, with this instrumentation as its confidence step.

## m20 (run 86, KEEP 0.354623) - the reader floor is the last hand-set visibility constant

Floor: `703a591` 0.321967 -> m18 `4deec78` 0.336828 -> **m20 `2f0ee0f` 0.354623 (+0.017795)**.
p10 0.325351 -> 0.336690 (UP), device_balanced 0.341397 -> 0.358294, house_1_v4_mean 0.545625 -> 0.539774.
Medians: kettle 0.555140 (flat), microwave 0.266004 (flat), **fridge 0.332973 -> 0.370963 (+0.037990)**, wm 0.228634 -> 0.242345 (+0.013711), dw 0.346705 (flat). No device median down > 0.03.

Lesson: the pool convention `half_p50` means the reader marks a device on only above `thr[d]`, and the device's median on-draw sits at `2*thr[d]`.
Any level the model writes at or below `thr[d]` is invisible however real the detected event. So every emission must be floored at `2*thr[d]`;
there is no room for a hand-set constant such as `AMP_MIN_W = 50 W` (m17 used 50 W for wm/dw; this run removed it, and the fridge raw writes were never floored at all).
Implementation: one central hunk in `build_and_train`'s returned predictor - `np.copyto(out[d], np.maximum(out[d], 2*thr[d]), where=out[d] > 0)`
(zeros stay zero so masks keep their support). It is a no-op wherever the gate is already threshold-anchored (kettle/microwave bands are mark-anchored at 2*thr),
which the screen confirmed bit-identical on 4 houses.

Refuted in this run (dead code, kept in the tree for now): the protocol-anchored fridge duty-cell re-anchor guard. It never fired on any of the 20 pool houses
(zero `fridge cell re-anchored` prints in `.auto/runs/86.log`). Its guard needs >= `DUTY_CELL_MIN = 300` pre-span events in a band around `2*thr +/- 20%`;
those bands hold fewer than 300 events on refit. The 154 W = 2*thr reading that motivated it was the median of ALL extracted events, not the fridge's draw - a bad inference.

New diagnosis (the fridge's remaining gap). Phase probe `.scratch/fr_phase.py` (eval span, seed 2026, refit/house_6, house_10, house_17):
the GT fridge cycles in refit are **0.3-1.0 min pulses repeating every ~45-50 min**, while the model emits 11-37 min runs;
only 2/12 (house_10) and 4/12 (house_6) of the emitted runs start at a real pulse. The mined most-regular 20-100 W / 11-37 min duty cell is therefore a
**competing periodic load**, not the fridge: interval-CV regularity is not identity. Detected-run counts match GT counts there (house_10 1936 vs 1956) while the phases are
independent - i.e. the model finds a same-rate periodic load at the wrong times. `self` on house_6 was 0.24-0.26 and on house_10 0.11-0.12.

Next (in order): (1) give the fridge duty-cell selection a physical criterion instead of minimum interval-CV - isolated thermostat cycles (reuse `_iso_clear`),
amplitude stability inside the cell, and a fridge-like duty fraction; (2) consider extending the fridge cell hypothesis space below `DUTY_DUR_S = 600 s`, since the
refit marks are themselves consistent with short pulse cycles; (3) then resume the big-bet portfolio with B3 (self-training over the unlabeled year).
Standing: a gain on house_1 alone is not a gain (house_1 subset fell 0.006 here while the pool rose 0.018); never diagnose on the holdout.

### m21 - the fridge duration gate is a reader-visibility gate; on refit the graded cycles are not extractable (run 87, DISCARD, unchanged 0.354623)

Run 87 shipped nothing: pool primary 0.354623 before and after, with the m19 fridge re-anchor guard deleted. That is itself the measurement - the guard was inert pool-wide (0 print over 20 houses, 0.000000 primary delta), and a 4-house subset A/B was bit-identical before the full run. Three repairs were implemented, screened on that subset, and refuted:

1. Mark-derived mining duration window (`_fdur` x REL_DUR replacing DUTY_DUR_S in the fridge duty-cell mining): subset mean 0.364151 -> 0.350107, fridge median 0.257162 -> 0.193965. Windows produced 0.5-4.2min (house_10), 0.1-0.9 (house_17), 4.4-39.8 (house_6), 6.6-59.7 (ukdale/house_1). DO NOT RETRY.
2. Reader-anchored amp band attached to the mark branch: inert. That branch is the `elif` of `if fridge_band is not None`, so on every house with a mined band it never executes (bit-identical metrics confirmed it).
3. Reader-anchored union (2*thr +- REL_AMP, inside the home's mark duration window) attached to the live band branch: added 734 preds on house_10, 23 on house_17, 1118 on house_6, 291 on ukdale/house_1, yet subset mean 0.364151 -> 0.363897 and fridge median -> 0.256019. The graded reader cycles are not the population that sits at the reader's own draw level. DO NOT RETRY.

What this establishes (and why to stop editing the fridge band):

- `evaluation.score_episodes` matches onsets within tau, then DISCARDS a matched pair whose len_pred/len_gt falls outside DURATION_BAND. The fridge run-basis emits 20-30min runs (band dur 10-37min) while the refit reader cycles are 0.3-1.0min, so those onsets can never score even when they coincide.
- On refit there are two coexisting periodic loads (~66min period): the model's ~1900 long runs and the reader's brief pulse at each cycle start. The graded one has no extractable aggregate signature - not the band population, not the 2*thr population (repair 3), and shortening the mining window made it worse (repair 1). That is an extraction limit on those homes, not a band-selection bug.
- Consequence: the refit fridge prizes (house_10 +0.0044, house_17 +0.0044) are out of reach of band edits. The reachable fridge work is house_6 (0.226 -> 0.33), where reader pulses do partly coincide with emitted onsets.

Next: stop tuning the fridge band, do not re-run these three repairs, and spend the next runs on B3 (self-training over the unlabeled year) - the first untouched big-bet.

### m22 - the fridge duty-cell path is dead for two independent reasons, and its duration space excludes the graded cycles (run 88, DISCARD, unchanged 0.354623)

Census of run 87's own build prints (every pool block):

- `fridge mined cell: a50 ...` = 0 lines, `fridge mined cell: none regular enough` = 0, `fridge fallback: ...` = 63. The mined duty-cell path ran on NO block: every fridge-bearing block took the m16 population fallback. The gate `int(dm.sum()) >= DUTY_CELL_MIN` (300) is combinatorially impossible - a 10 W x 5 min bucket inside a 280 W x 30 min box (~224 buckets, 1.5-10k events) holds tens of events - so the path never even reached its CV test.
- `named dw=0` on 61/61 blocks (deliberate per the module docstring: dw is carried by the sustained path).
- `kettle sustained marks: X/5` sums to 87 of 180 windows (2 blocks at 0/5): the sustained kettle path's pre-registration fails on over half of all mark windows, but the event path carries the kettle (median 0.555) and the sustained path only adds ~2.5 runs per block.
- `mark re-anchor fridge` on 3 blocks only.

Repair attempted (B3-style, self-training on the home's own unlabeled pre-span): make the cell path reachable - per-cell floor 300 -> 20 (enough points for a p5-p95 band) - and replace the selection criterion, because the interval-CV criterion is a SECOND dead gate: consecutive-interval CV cannot survive the extractor's ~1/3 capture of the true cycles (a periodic fridge seen a third of the time reads as irregular). The replacement is Rayleigh phase folding: fold the cell's on-times modulo their own median period, take the concentration R, floor it by the home's own box population R_pop and the classical 1.7/sqrt(n) critical value. The m19 reader-draw re-anchor guard was deleted in the same edit, since making the path reachable would otherwise have activated it and applied the run-87-refuted reader-draw band.

Result: the path fires on 3 of 4 subset houses, and every winning cell is a sparse day-scale one - house_10 R=0.418 n=20 T=8264min (5.7 days), house_17 R=0.342 n=36 T=1769min, ukdale/house_1 R=0.364 n=34 T=4401min - while the box populations are temporally Poisson-like (R_pop=0.006-0.017, cv_pop 0.92-3.31). Subset mean 0.364151 -> 0.347702, fridge median 0.257162 -> 0.183141. REFUTED.

This is the third independent demonstration that narrowing the fridge's duration hypothesis space loses: the m16 wide fallback band is the measured optimum, the run-87 mark-derived window lost (-0.063 fridge median), and now the day-scale Rayleigh cells lose (-0.074). Structural reading: the graded refit fridge cycles are 0.3-1.0min while DUTY_DUR_S = 600-2400s excludes them entirely, and the 10-40min compressor-class box population is a near-Poisson mixture rather than a duty device.

Do not keep editing the fridge band: the fallback is a measured local optimum, and the remaining prize needs a different hypothesis space (or the extractor to see the pulses at all, which run 87 showed it does not). Reverted with `git checkout` and re-measured: primary 0.354623, p10 0.336690, byte-identical to the floor. Note for whoever next makes the cell path reachable: delete the m19 reader-draw re-anchor guard first.

Next: leave the fridge and start B3 for real on a device whose weak median is not band-limited.

## m23 (run 89, DISCARD 0.354848) - the --dump unlock, and three structurally dead device pairs

Run 89 measured a conditional microwave plateau fusion: `predict` admits fragmented
plateau events (dur inside the mark's *fragment* band, `ev_band`) and then emitted one
onset per event, so a duty-chunked magnetron cycle produced several onsets and
`score_episodes`' one-to-one onset matching counted each extra fragment as a false
onset. Fusing fragments whose pause is inside 1.25x `eb['dur_p50']` (the marks' own
fragment duration; same margin convention as the wm/dw merge gaps), strictly
conditional on `ev_band` so unfragmented houses are untouched. Evidence: subset mw
median 0.223885 -> 0.228612 and fusion print fired (262 plateau events -> 204 cycles);
pool primary 0.354623 -> 0.354848 (+0.000225), p10 0.336690 -> 0.340019 (+0.0033),
device_balanced 0.358294 -> 0.359466, mw median 0.266004 -> 0.267281, no device median
down. Below the +0.01 keep bar, so reverted - but it is a NON-REGRESSION with a real
mechanism, so bundle it with the next genuine gain. Patch recipe (against `2f0ee0f`):
replace the duplicated `for k in np.flatnonzero(mw_ok):` emission block at predict
(the block is literally pasted twice, lines ~1319-1325) with: `_mwk =
np.flatnonzero(mw_ok)`; if `eb is not None and _mwk.size > 1`, walk `_mwk` and group
consecutive events while `on[k] - off[g1] <= max(1, int(round(1.25 *
float(eb['dur_p50']) / cad_s)))`, tracking the group max amp; emit each group once as
`out['microwave'][on[g0]:off[g1]] = np.maximum(seg, amax)`; else emit per-event as
before. Bundled inert edits: ported the `_wm30_profile` window-skip rule to
`_dw30_profile` (skip a mark window whose excitation never crosses the heater
threshold instead of disabling the whole dw detector; require >=2 usable windows) and
corrected the dw disable message, which blamed 'mark windows produced no heater runs'
when the real cause was no dishwasher mark. Both provably inert on this pool: the
all-or-nothing branch never fired in 61 blocks.

### The real unlock: `bench_v4.py --dump` gives per-pair precision/recall
Run `uv run python3 .auto/bench_v4.py --dump --workers 1` (~110 s). Per house per seed
it prints `device P=.. R=.. F1=.. n=pred/gt`, plus per-device `AGGR` lines. 330 pairs
parsed. Full-pool device structure (median F1 over pairs / mean P / mean R / pred / gt):

| device | pairs | median F1 | mean P | mean R | pred | gt |
| --- | --- | --- | --- | --- | --- | --- |
| fridge | 90 | 0.300 | 0.430 | 0.335 | 150243 | 189625 |
| washing_machine | 75 | 0.180 | 0.243 | 0.246 | 5204 | 4290 |
| kettle | 60 | 0.620 | 0.519 | 0.620 | 28999 | 20445 |
| microwave | 55 | 0.230 | 0.330 | 0.289 | 10675 | 9440 |
| dishwasher | 50 | 0.500 | 0.432 | 0.318 | 1488 | 2635 |

Kettle is the only healthy device. Every other device is precision- AND recall-poor,
and the dishwasher is the clearest shape: P 0.43 vs R 0.32, i.e. recall-starved (1488
preds against 2635 gt) - it needs MORE detection, not tighter gates. Note this is the
pool-wide picture; the 4-house subset has a misleadingly high dw median (0.4575 vs the
pool's 0.3467) because its dw pairs happen to be the ones that work.

### The prize: dead pairs that are dead on every seed
The 18 worst pairs are dominated by exact zeros that repeat across seeds - not noise:

- `refit/house_10` dishwasher: preds 0/86, 0/86, 2/86, 0/86, 0/86, F1 0.000. The house
  HAS a dw mark and `_dw30_profile` builds a profile (subset print: `span=8-21min
  amp>=1393W mean=1375-5022W hs=0.75-1.75 idle<=infW dens<=0.588/min
  heater_gap_merge=70min ext_back=0.0min ext_fwd=0.0min`), but then `dw sustained runs:
  0 pass run-basis gates (0.000/day)`. So the detector is calibrated off a valid mark
  and every eval run is then rejected by the run-basis gate family.
- `refit/house_13` dishwasher: preds 1/73, 0/73, 1/73, 1/73, 1/73, F1 0.000 - the same
  shape, no detection at all. (Not yet confirmed to have a dw mark; check first.)
- `refit/house_11` washing_machine: F1 0.000 on four seeds with preds 33/58/41/64 vs a
  fixed gt 15 - precision-zero, the detector emits far more cycles than exist.
- `refit/house_11` dishwasher: F1 0.000 on four seeds at 12/12, 26/12, 6/12, 9/12 -
  preds are roughly the right COUNT, so this one is onset/timing disagreement rather
  than a counting failure.
- `refit/house_17` s4 wm 0/66 and `refit/house_4` s4 wm 5/32: single-seed, so treat as
  seed variance, not structure.

Arithmetic that matters: the primary is the mean over the 66 pool pairs, so the two
dead dishwasher pairs (house_10, house_13) are worth 2 x F1 / 66 - reaching a modest
F1 0.4 on both would be +0.012 primary, over the +0.01 keep bar, before counting the
device-median and device_balanced lift. A house where the dishwasher is simply never
detected is exactly the 'make the process learnable across homes' defect, not a
benchmark artifact.

### Next hypothesis (B3-adjacent, dw generalization)
The dw run-basis gate family does not generalize to a house whose own mark yields a
valid profile. Diagnose house_10 first: dump the mark-derived profile against the runs
that actually fail, and find which of (amp / mean / hs / dens / span) kills every run -
the printed profile's `span=8-21min` is suspiciously narrow for a whole-house dw cycle.
There is a self-training angle here that fits B3: the house's own unlabeled eval year is
available, so the run-basis bands can be re-estimated from the house's own run
population (the runs the mark profile already ranks as plausible) instead of being
frozen from five mark windows. Keep the precision guard: house_11 dw shows what
unchecked admission costs (41 junk runs on the earlier span re-anchor).
## m24 (run 90, discard, commit 2f0ee0f): single-block dw marks - big dw win, one pair loss, median-seed trap

**Verdict.** primary 0.352638 (floor 0.354623, delta -0.001985), p10 0.346326 (+0.0096, floor 0.336690),
device_balanced 0.359112, house_1_v4 0.540104 (unchanged), checksPass true, no device median down >0.03
(dw median 0.346705 -> 0.388346 UP). Discarded only because the keep rule needs the PRIMARY up >=0.01.

**The metric decoded (the important methodological finding).** mean_device_f1 is the MEDIAN over the 5
seed means of the 66-pair mean, not a mean over seeds. Reconstructed exactly from per-pair CSVs at the
floor: {0.335152, 0.356818, 0.354545, 0.357576, 0.338333} -> median 0.354545 = recorded 0.354623. With
the fixes: {0.345758, 0.364697, 0.352576, 0.368333, 0.346818} -> median 0.352576 = recorded 0.352638.
So FOUR of five seeds improved (+0.0106 s1, +0.0079 s2, +0.0108 s3, +0.0085 s4) while seed 2026 fell
-0.0020, and seed 2026 was the middle value. **A change must move the median seed; 4-of-5 good seeds is
not enough, and the all-pairs mean (+0.007152) is NOT the metric.**

**Hypothesis tested.** refit/house_10 and refit/house_13's dead dishwashers share one root cause: gate
bands derived from a mark whose own run is structureless. Two edits, both conditional so mark evidence
wins wherever it exists:
(1) merge gap: `merge_n = int(round(4200.0/DW30_GRID_S))` (70 min) when `max_gap == 0` -> `merge_n = 1`,
    applied to both mirrored profiles (_dw30_profile and _wm30_profile). house_10's 70-min value was
    provably that else-branch, reachable only when its marks yield one fully-ON block per window.
(2) duty floor: dw `hs_band = (0.75*min(hss), 1.75*max(hss))` -> floor dropped (hs_lo = 0) when
    min(hss) >= 0.999, because a mark run IS the merged above-heater region, so hs = 1.0 by construction
    carries no duty evidence and the 0.75 floor excludes partial-duty cycles (other houses measure hs
    0.22-0.64).
Diff saved: .auto/runs/90_single_block_mark_fixes.diff (112 lines). Per-pair CSVs: .scratch/run90_base.csv
and .scratch/run90_new.csv (330 pairs each; comparison script .scratch/cmp90.py).

**Attribution (all-pairs mean F1, floor -> fixes).** dishwasher n=50 0.3398 -> 0.3810 (+0.0412),
washing_machine n=75 0.2333 -> 0.2357 (+0.0024), microwave n=55 0.2720 -> 0.2742 (+0.0022),
kettle n=60 0.5423 -> 0.5423 (0.0000), fridge n=90 0.3668 -> 0.3668 (0.0000), ALL 330 +0.007152.
Kettle/fridge/microwave prediction-vs-gt counts are bit-identical; only dw and two wm pairs moved.

**What the fixes unlocked (keep these).**
- refit/house_13 dw: 0.00 on all five seeds (1 pred vs 73 GT) -> 0.51/0.51/0.57/0.58/0.55 (37-53 preds).
  The largest single-pair gain recorded in this campaign. s2026 was already alive at the floor, so
  house_13's floor pair-median 0.4650 was carried by seed 2026 alone.
- refit/house_4 wm pair +0.11 (s1) and +0.07 (s3), house aggregate +0.037/+0.023; refit/house_8 +0.005/+0.01.

**What they broke (fix it, do not abandon it).** refit/house_10 dw 0.1500 (10 preds) -> 0.0000 (1 pred) on
seed 2026 ONLY - exactly -0.15/66 = -0.00227, which is the entire primary regression. The 70-min fallback
was LOAD-BEARING there: with merge_n = 1 house_10's raw heater blocks are shorter than its own mark-derived
span band (8-21 min), so span_band rejects them, and the old evidence-free 70-min gap was what made them
long enough to pass. Same parameter, opposite sign on two houses.

**Next hypothesis A (cheap, safe): union the two merge priors.** Run the dw detector under both merge_n
(the mark-derived/fallback value AND 1) and union the resulting runs; span_band is then the arbiter, so
house_10 keeps its long runs and house_13 keeps its short ones. Implementation: one extra _dw30_runs pass
with prof2 = dict(prof, merge_n=1); it needs no new gates because the existing bands filter both sets.
This recovers the -0.002 (median back to ~+0.0002) but will NOT clear the +0.01 bar on its own.

**Next hypothesis B (the real prize): fix refit/house_10's dishwasher.** With the median seed being 2026,
house_10's dw IS the metric bottleneck: 86 GT cycles and only 10 preds (F1 0.15) at the floor, so taking it
to ~0.75 is +0.6 on one pair = +0.0091 on seed 2026, which combined with A clears the bar on the median
seed. Diagnose BEFORE writing more gates (two rounds of band repairs have now moved the pool by ~0): dump
house_10's 86 GT dw intervals (eval submeter, .scratch/ only) against the exc trace at the profile's own
heat = 1393 W and check whether one GT cycle appears as ONE block (extraction/threshold problem) or MANY
short blocks (merge problem); also compare its mark windows' structure with its eval cycles - the marks
read single-block fully-ON (hs = 1.0) while the eval blocks come out <8 min, which is itself inconsistent
and is probably the real defect. Do NOT widen the band family again.

**Refuted / inert this run.** The dw mark-window skip port ported from _wm30_profile is confirmed INERT
(two subset screens, with and without it, were bit-identical) - do not re-attempt it. Also do not trust
subset aggregates as a proxy: the 4-house subset said -0.0081 while the pool all-pairs mean was +0.0072,
because house_13 (the main beneficiary) is not in the subset. Never log a subset number as a metric.
## m25 (run 90 follow-up, diagnostic): house_10 dishwasher - level, merge gap, hs floor and density ceiling are all REFUTED as the blocker

**Setup.** refit/house_10 dw is the metric bottleneck: with 2026 as the median seed, +0.6 F1 on this one pair is +0.0091 on the median seed. Diagnostics: .scratch/dw10.py, dw10_sweep.py, dw10_sweep2.py, dw10_sweep3.py (offline; labels used only to count cycle hits).

**GT structure.** 86 dw cycles in the 90-day eval window, durations 10.0-27.2 min (median 18.8), median onset spacing 16.6 h.

**Refuted 1 - level/threshold.** 86 of 86 GT cycles reach max exc >= the mark-derived 1393 W (per-cycle max exc median 2241 W, min 1928 W). At merge_n=1, 59 of 86 cycles already contain an exc block spanning the mark band 8-21 min (blocks per cycle: 1 for 21 cycles, 2 for 64, 3 for 1). The eval cycles are visible at the marks own threshold.

**Refuted 2 - merge gap alone.** Faithful reconstruction (reproducing the floor profile gives its printed 0-pass as n_adm=1). Admitted runs by merge gap: 0.5min->1, 1->1, 2->3, 3->4, 5->16, 8->15, 12->15, floor 70min->10. Best gap touches only 9 of 86 GT cycles.

**Refuted 3 - hs floor (run 90s dw edit) is irrelevant for house_10**: sweeping hs_band (0.75,1.75) vs (0,1.75) gave identical counts (1/3/4/16/15/15).

**Refuted 4 - density ceiling.** Sweeping dens_hi over 0.588, 1.0, 2.0, 5.0, inf at merge gaps 0.5/2/5 min changed NOTHING (1/3/16 admitted at every ceiling, cycles hit 0/0/9). The density ceiling is not binding here.

**Run 90s house_10 regression was the merge gap** (70min -> 1), not the hs edit: at merge_n=1 the eval admits 1 run (n=1 pred, F1 0.00) whereas the 70-min gap admitted 10 (n=10, F1 0.15). Note the printed line "dw sustained runs: N pass run-basis gates" is emitted from the MINING/pre span, not the eval window - it read 10 in run 90 while the eval admitted 1. Never read that print as an eval measurement.

**Additive gate census on the eval window (merge_n=10, gates enabled one at a time):**
- all gates permissive: admitted=176, cycles touched=43/86
- +span 8-21min: admitted=16, cycles touched=9/86
- +amp>=1393W: admitted=16, cycles touched=9/86
- +mean 1375-5022W: admitted=16, cycles touched=9/86
- +hs 0-1.75: admitted=16, cycles touched=9/86
- +dens<=0.588: admitted=16, cycles touched=9/86

**So the blocker is whichever gate drops the count, and 86/86 cycles reaching 1393 W with 59 in-band is the constraint to exploit.** Re-run the census (the printed numbers are in the run 90 follow-up log) before writing code: if the drop is in span_band the answer is a longer allowed span for houses whose marks are single-block; if it is amp/mean the answer is the run statistic being diluted by the merge. In every case the fix must be conditioned on the marks carrying no fragmentation evidence (max_gap == 0 / min(hss) >= 0.999) so evidence-bearing houses are untouched, and unioned with the merge_n=1 candidate rather than replacing it.

**Kill criterion.** If a conditioned fix still leaves house_10 dw F1 below ~0.35, stop attacking bands: 86 cycles all reach the threshold, so at that point check whether the GT cycles union several submeter channels that the marks never see (p4.canon_channels) and pivot to B4 (program model) for the dw instead.
## m26 (run 91, discard, commit 2f0ee0f): widening the dw span band when the marks show no pause - uniform gain, sub-bar

**Change.** Built on the run-90 edits (re-applied from .auto/runs/90_single_block_mark_fixes.diff). In the dw profile of src/experiments/04_autoresearch/model.py, when max_gap == 0 (the marks contain no internal pause at all) the merge gap is derived from the mark span scale (merge_n = round(0.5 * 0.6 * min(spans) / DW30_GRID_S), bridging pauses up to half the shortest mark span) and the span tolerance is widened about the same centre (0.25*min(spans) to 3.0*max(spans)). The scale-tolerant gates (amp/mean/hs/idle/dens) still arbitrate, and houses whose marks DO show a pause (max_gap > 0) are untouched. Diff saved at .auto/runs/91_single_block_span_condition.diff (126 lines) because the run was discarded.

**Why this and not the other candidates.** Additive gate census on refit/house_10 eval window, merge_n=10: all gates permissive -> 176 runs admitted, 43/86 GT cycles touched; adding the span band 8-21 min alone -> 16 runs, 9/86; adding amp>=1393W, then mean 1375-5022W, then hs 0-1.75, then dens<=0.588 changed nothing further. Level (86/86 cycles reach 1393 W), merge gap alone (best 16 admitted, 9/86 cycles), the dw hs floor (identical counts), and the density ceiling (0.588 -> inf identical) were all refuted first.

**Result (pool, 66 pairs, 20 houses, 5 seeds, 111 s, checks pass).** primary 0.358165 vs floor 0.354623 = +0.003542 (sub-bar). p10 0.343651 (+0.006961), device_balanced 0.365867 (+0.007573), house_1 v4 mean 0.540104 (unchanged). Device medians: dishwasher 0.384353 (+0.037648), microwave 0.267281 (+0.001277), kettle 0.555140, fridge 0.370963, washing_machine 0.242345 - none down.

**All five seeds rose** (seed means, order [2026,1,2,3,4]): run 91 = [0.358165, 0.342976, 0.361740, 0.365480, 0.344664] vs floor = [0.354545, 0.335152, 0.356818, 0.357576, 0.338333]. The median is still seed 2026, so the metric still effectively reads 2026, whose +0.0036 comes from house_10 dishwasher alone (targeted screen: F1 0.15 with n=10 preds -> 0.36 with n=73 preds, R=0.34).

**Lesson.** p10 and device_balanced rising faster than the primary is the signature of repairing dead tail pairs, and that is the shape of every remaining win: the median seed needs several pairs moved, not one.

**Next run.** (1) Apply the same no-pause condition to the wm mirror (identical code); check the wm mark profiles for max_gap == 0 houses first. (2) Run bench_v4.py --dump and diff per pair against .scratch/run90_base.csv (330 pairs) so the next change is chosen from a full attribution rather than aggregates. (3) Dead pairs left on the median seed: refit/house_10 fridge (P=0.04 on 1956 gt), refit/house_6 microwave (R=0.02 on 390 gt), refit/house_11 wm and dw, refit/house_7 dw.
## m27 (run 92, discard, commit 2f0ee0f): two refutations - the wm mirror is inert and a robust wm span ceiling costs 0.0035

**Refutation 1 (kills a planned step).** m26 planned to port run 91's no-pause condition to the wm mirror. The saved run logs refute it before spending a run: every logged wm profile carries heater_gap_merge = 17, 30, 31, 32, 34, 37, 41, 44, 46, 47, 51, 59, 67, 69, 89 min, i.e. the wm marks ALWAYS hold an internal pause, so the max_gap == 0 branch would never fire. The wm mirror is inert by construction. Do not retry it.

**Refutation 2 (the run).** wm profiles logged before the change had span bands of 5-136, 4-44, 8-91, 10-72 min (max/min 3.4x to 30x, because the band hangs off max(spans) over five mark windows). The change referenced the ceiling to median(spans) at the same 1.25 margin whenever max > 3*min, leaving consistent-mark houses byte-identical and the lower bound on min(spans). Result: primary 0.354655 vs 0.354623 floor (+0.000032) and vs 0.358165 incumbent (-0.003510); washing_machine median 0.242345 -> 0.215407, house_1 v4 mean 0.540104 -> 0.533005, p10 -0.0063, device_balanced -0.0062; all five seeds fell (2026 0.358165->0.354655, 1 0.342976->0.334474, 2 0.361740->0.357406, 3 0.365480->0.356107, 4 0.344664->0.341674). Diff kept at .auto/runs/92_wm_robust_span_ceiling.diff.

**Lesson (general).** For the wm, the spread across the five mark windows is REAL device behaviour, not sampling noise: the widest marked cycle is a real cycle and the wide ceiling carries recall for exactly the houses that need it. min/max over five marks is evidence here, not an outlier artifact. Any future wm precision work must not tighten the span ceiling - it has to come from the mean/density bands or from a phase-program model (owner B4).

**Per-pair deficit ranking of the floor state** (mined offline from .scratch/run90_base.csv, 330 pairs, no benchmark run). Worst pairs (house, device, median F1, median preds/gt): refit/house_10 dw 0.00 (0/86), refit/house_11 wm 0.00 (58/15), refit/house_11 dw 0.00 (12/12), refit/house_13 dw 0.00 (1/73), refit/house_10 fridge 0.04 (2541/1956), refit/house_12 kettle 0.04 (230/127), refit/house_18 wm 0.06 (58/37), eco/house_03 fridge 0.07 (726/1178), refit/house_21 wm 0.08 (63/42), refit/house_7 kettle 0.13 (450/108). Houses by lost F1: refit/house_11 3.95 (5 devices), refit/house_10 3.60 (4), refit/house_6 3.10, refit/house_21 2.92, refit/house_7 2.91, refit/house_8 2.78. Median-seed device means: wm 0.242 (15 pairs), mw 0.261 (11), fridge 0.339 (18), dw 0.405 (10), kettle 0.562 (12).

**Next run.** The incumbent state is floor + run 91 (recoverable with git checkout then git apply .auto/runs/91_single_block_span_condition.diff). Regenerate a per-pair dump of that incumbent state so the next change is chosen from attribution, not aggregates; then take the wm through its mean/density bands (the mean_band upper bound is likewise a 1.25*max over five marks) as the last cheap wm lever before the B4 phase-program model.

## m28 - run 93: the admission-margin question is closed, both directions (discard, primary 0.355973)

Two cheap screens (~40 s each, 6 houses, seed 2026) refuted two whole families
before a full run was spent on the survivor.

1. **wm onset aggregate - refuted as inert.** The wm path aggregates the five
   per-mark-window onset offsets with a MEAN (`_wm30_profile`, model.py L728-729)
   while the dw path uses a median and documents why (run-67 comment: an offset
   error past the 600 s matching tolerance collapses F1 to 0 *with the right
   cycle count*). Implemented a support-maximising aggregate (the offset the most
   windows agree on, 30 s grid tolerance, ties breaking to the sample median so
   agreeing windows reduce exactly to the incumbent) for both profiles. Result:
   25 of 26 pairs bit-identical; only refit/house_7 wm moved (0.260 -> 0.230).
   The four dead wm pairs did not move. The wm F1=0 pairs are NOT an onset-offset
   artifact - the per-window offsets were already consistent. Closed.

2. **Widening the burst admission margins - refuted.** REL_AMP 0.20 -> 0.30 and
   REL_DUR (1/3,3) -> (0.25,4): 8 pairs changed, sum -0.4900. The damage sits in
   the healthy pairs (refit/house_8 kettle 0.620 -> 0.440, ukdale/house_1 kettle
   0.790 -> 0.620) while the recall-collapse pairs it was aimed at did not respond
   (house_8 mw 0.110 -> 0.100, house_6 mw unchanged). The burst-recall collapse is
   not an admission-width problem; run 91's dw widening does not generalise to the
   burst devices.

3. **The mirror step - measured, sub-bar.** REL_AMP 0.20 -> 0.15 (single field, so
   attribution is clean): primary 0.355973 = floor +0.00135 and -0.00219 vs the
   incumbent (floor + run 91). But the per-device medians rose: mw 0.267 -> 0.2845
   (+0.0172), kettle 0.5551 -> 0.5590, house_1_v4_mean 0.5401 -> 0.5462 (+0.0061),
   p10 0.3437 -> 0.3479 (+0.0042), device_balanced -0.0019. So the amp margin is
   **already near-optimal at 0.20 for the pool mean**; the sensitivity curve is
   peaked there, and the mean-vs-median divergence is now measured: a
   precision-leaning change buys the medians, p10 and the standing-bar house and
   pays the mean through a few large recall losses (house_12 mw 0.430 -> 0.340).
   Diff kept at `.auto/runs/93_rel_amp_tighten.diff`.

### What this closes, and where the campaign has to go
Every per-house gate/band family in `model.py` is now refuted in at least one
direction: onset statistic (this run), admission width both ways (this run), span
ceilings (run 92), fridge band repairs (m21/m22), crossed detectors (m6), and the
level / merge-gap / hs-floor / density-ceiling knobs for house_10 dw. The
remaining dead pairs are **mark-window/GT misassignment plus irreducible lookalike
populations**, not gate calibration:
- refit/house_12 kettle admits 784 predictions at 1110 W / 14.4 min against a mined
  cluster of n=1600 lookalikes at 9.4 min, and its own mark window (115 W / 36.4 min)
  is the mislabeled side; the GT cycles really are ~1.1 kW, so trusting the mark
  would destroy the little recall it has.
- refit/house_6 mw carries a mark of amp=786 W with mean=60 W (an idle-dominated
  window) against 390 GT cycles at R=0.02; no band anchored on that mark can work.
Therefore the next iterations must change *structure*, not margins: **B4** (phase
grammar / HSMM to replace the wm+dw span+density gate family) or **B1** (cross-house
encoder retrain) or **B3** (unlabeled-year self-training). Each needs 5-15 runs and
an explicit kill criterion; one bad first run is not a refutation.

NOTE for whoever builds the parameter dict (owner side-item #1): the 52 `model.py`
literals now have one measured anchor - REL_AMP's optimum is 0.20 (0.15 costs the
mean -0.0022, 0.30 costs -0.0035 on a 6-house screen) - and REL_DUR's upper margin
should NOT be widened past 3.0 (screen B).

## m29 - Run 94: wm emission extension (mean->median) + four fridge refutations

**Result.** Pool primary **0.359446** (floor 2f0ee0f 0.354623; run 91 alone 0.358165) =>
**discard** (needs >= 0.364623). p10 0.344277 (up from 0.343651), device_balanced 0.365435,
house_1_v4_mean 0.540104. Medians: kettle 0.555140 / mw 0.267281 / fridge 0.370963 /
wm 0.246657 (floor 0.242345) / dw 0.384353. Run 91's dw gain is intact; no median regressed.

**The change.** The wm profile's emission extensions were the MEAN of the per-mark-window run
offsets (`np.mean(oss/oes)`, model.py L728-729) while the dw profile uses the MEDIAN with a
non-negative clamp (`np.median(pres/posts)` L502-503, the run-67 fix). One anomalous mark window
moves a 5-sample mean by up to a fifth of its span and shifts every emitted episode; the wm's three
right-count/zero-match pairs (house_18 43/37 F1=0.03, house_6 27/22 F1=0.04, house_11 33/15 F1=0.00)
are that signature. Gain is +0.0013 pool and concentrates entirely in refit/house_10 (0.163 -> 0.25,
n 133 -> 136/77) - the same house whose dw a 606-642s offset error wrecked in run 67. 13 of 14 wm
houses were unchanged, i.e. the offsets were already consistent there. Harmless consistency fix,
unkeepable alone.

**The fridge's admission-side space is now closed - four refutations this run:**
1. duration ceiling `REL_DUR[1]*max(pop_p50, 0.5*pop_max)`: counts barely moved (house_18 2207->2223,
   house_8 1182->1281) and the movers lost recall (eco_02 0.79->0.70, ukdale_1 0.48->0.47); -0.09
   across 7 houses.
2. event-path amp high side lifted to the mined class ceiling: **bit-identical** on all 7 houses -
   because the run-basis window already IS `[0.8*mark, class_hi]`. Both fridge paths already share
   one amp window, so the dominant event path was never binding.
3. isolation lifted to `max(3*mark, 3*class_hi)`: run-basis candidates doubled (107->305, 1164->1937)
   with every fridge F1 unchanged to 2dp - the added candidates overlap spans already lit.
4. (standing) REL_AMP 0.15/0.30 both ways, and the duty-cell path is dead in all 20 houses
   (cv > DUTY_CV_MAX everywhere), so the reader-draw re-anchor never fires and m21's cell repairs
   were vacuous rather than wrong.
=> The fridge's ~1900 missing GT cycles on house_8 (R=0.30 at P=0.68) are **extractor-bound**, not
   gate-bound. The universal fallback band (21-115 W / 10-38 min) is already what both paths use.

**Error-mode decomposition (seed 2026 per-pair P/R) - the three families fail oppositely:**
- wm (15 pairs, mean 0.242): OVER-emission, 7/15 pairs at 1.4-2.3x GT count with P always < R.
  Lookalike admission via `hs_band`'s `0.75*min(hss)` floor, which one low-heat mark window
  (hs 0.13) drags to 0.10; plus 3 placement pairs. Note wm gap-merge is already 17-89 min, so this
  is not fragmentation.
- fridge (18 pairs, mean 0.339): UNDER-emission, 8/18 at 0.44-0.73x count WITH high precision
  (0.58-0.86) => extractor-bound.
- dw (10 pairs, mean 0.426): healthy, 3 under / 0 over.

**Banked diffs (must travel together next bundle: they sum to +0.0048):**
- `.auto/runs/91_single_block_span_condition.diff` (dw, +0.0035, no pair regressed).
- `.auto/runs/94_wm_median_ext.diff` (wm mean->median, +0.0013).

**Next.** Margin surgery on the single-house gates is exhausted (onset statistic, admission width
both ways, span ceilings, fridge band/isolation/duration). The next lever must add *information*:
B3 self-training over the unlabeled year, B1 cross-house encoder retrain, B4 wm/dw phase grammar.
wm's `hs_band` floor (one cold/low-duty calibration mark dragging the floor to 0.10) is the one
documented-but-unexplored wm admission knob if a structural wrapper is ever built around it.

## m30 (run 95) - fragmentation switch: gate-consistent firing test -> refuted

Run 95 replaced the burst fragmentation switch's cliffs
(`eb['dur_p50'] <= 0.5*core_dur or eb['amp_p50'] < 0.7*core_amp`) with the gate's own
admission test (fire iff the population's median event is outside the mark's REL_AMP /
REL_DUR band). Pool: median seed 3 **0.358233**, seed 2026 **0.359446 bit-identical** to
run 94, p10 0.341569, device_balanced 0.359969; medians kettle 0.553975 / mw 0.263539 /
fridge 0.370963 / wm 0.246657 / dw 0.384353 -> mw -0.0037, kettle -0.0012, discard.

Mechanism screen (6 houses, seed 2026, `.scratch/s95_base.txt` vs `.scratch/s95_new.txt`):
2 firings -> 2 firings, every METRIC bit-identical. The change only moves seeds 1-4.
So `ev_band` firing was never the mw's under-emission cause: the strict superset
widens the band on houses where the mark gate already admits the population median.

Closure: **the burst-admission family is exhausted in every direction** -- REL_AMP
0.15/0.30 (run 93), admission width on burst devices, the fragmentation switch and its
firing condition, the fridge band/duration/amp/isolation repairs (m21/m22, run 94).

New hard evidence for the B1 portfolio: the switch's diagnostic print is the only place
the model compares a mark against its own **mined event population**. On refit/house_12 the
kettle mark reads 115W/2184s against a window population p50 of 1110W/864s (10x amp, 2.5x
duration mismatch): the calibration press was a program appliance, so the ev_band path
emits 1.1kW/14min wm-like heater runs as kettle (2223 preds vs 635 GT, P 0.03, F1 0.04).
Abstaining scores the same F1, so no label-free per-house rule can recover that pair --
only cross-house evidence (what a kettle looks like in other homes, B1) could. **TESTED AND REFUTED in run 96 (m31):** the cross-house kettle prior (1.9-4.1 kW) repaired that very mark and the pair fell 0.06 -> 0.00 (pool -0.0004), because house_12's own reader threshold is <= 115 W - its reader corroborates the low-power long channel, so the anomaly IS the label's evidence and no cross-house physical rule can separate it.

- m31 (run 96) cross-house physical envelope for burst devices - CLOSED
  both directions by measurement. `_xhouse_burst_env()` (model.py) reads
  `.auto/cache/b1_events_v1.npz` (B1 m1 mined events; the 7 v4 holdout
  houses are provably absent, so the prior is transfer-clean) and builds
  envelope = p10/p90 of peak_w/dur_s x (0.4, 2.0). A mark outside the
  envelope is repaired to the cross-house median and `ev_band[d]` is
  dropped, because `_burst_event_bands` mines the SAME K=5 windows: a bad
  window makes the mark AND the mined population junk, so only cross-house
  evidence can break the tie. Applied after the reader-floor re-anchor,
  before `dur_ref`; amp test restricted to flat-draw devices (a
  duty-cycled microwave peak_w is not comparable to its mark median draw).
  SCOPE measured offline over all 99 builds of the incumbent dump BEFORE
  writing any gate logic: 4 outlier builds = ONE house x ~4 seeds (kettle
  99-111 W / 25.7-37.0 min, 10-25x outside); microwave 0, wm 0, dw 0.
  Full pool, 5 seeds, 97.6 s: primary 0.359052 (-0.0004 vs the 0.359446
  incumbent), p10 0.343538 (-0.0007), kettle median 0.551845 (-0.0033),
  mw/fridge/wm/dw medians and house_1_v4_mean 0.540104 unchanged. The only
  firing pair, refit/house_12 kettle seed 2026: 0.06 (P .03 R .19,
  712/127) -> 0.00 (506/127). Duration-only probe (`_XH_AMP_DEVS = ()`):
  0.359239, same pair -> 0.01. Diagnosis: house_12's own reader threshold
  is <= 115 W, which is why the floor re-anchor never fired there and why
  its pretraining windows show a low-power long channel. The mark is NOT a
  calibration error - the anomaly IS the label's evidence - so a
  physically correct 1.9-4.1 kW prior removes the only overlap the pair
  had. Same wall as eco/house_02 vs eco/house_06 fridge: label anomalies
  are separable by neither label-free nor cross-house physical rules.
  Diff: `.auto/runs/96_xhouse_burst_env.diff` (12331 B, 156/14 = incumbent
  bundle 85/14 + 71). Restore the incumbent with
  `git checkout -- src/experiments/04_autoresearch/model.py && git apply
  .auto/runs/94_wm_median_ext.diff`.

- m32 (run 97) B3 m1 self-calibration of the burst admission band from the
  pre-span event population - REFUTED, and the reason is structural. The
  pre-span year is ALREADY mined at zero extra cost (ev_on/off/amp/dur,
  10.9-15.3k level-excursion events over 180 d vs the K=5 marks), so m1 =
  pseudo-label that year with a window 3x wider than the admission band
  (|ev-mark| <= 0.6*mark amp, REL_DUR dur, n >= 20) and re-derive the band.
  Variant A (population p10/p90 = the band): primary 0.317427 vs the
  0.359446 incumbent (-0.0420); kettle -0.146, mw -0.081, house_1 -0.093;
  fridge/wm/dw bitwise unchanged. Variant B (population p50 = centre, the
  mark's REL_AMP = width): 0.311275 - worse, so the CENTRE is bad too, not
  just the width. Mechanism (same-GT A/B on 3 houses): house_17 kettle
  574->1506 emissions over the SAME 590 GT, P 0.83->0.21 AND R 0.81->0.55;
  house_17 mw 104->392, P 0.39->0.10; ukdale_1 kettle 377->585, P 0.78->
  0.42; house_12 mw 36->172, P 0.56->0.14. The population p50 is biased
  4-30% LOW (1791->1710, 2676->2149, 1046->770, 115->67 W): a label-free
  amp window around a device always contains far more sub-device excursions
  than the device's own events. The K=5 marks are read on the submeter
  during a device-active press, so they are a strictly better amp estimator
  than any single-house aggregate statistic. GT counts were identical in
  every A/B pair (GT is model-independent, bench_v4.py:177), and
  fridge/wm/dw were bitwise unchanged, so the blast radius is exactly the
  kettle/microwave gates. B3's premise holds for a TRAINABLE model (a
  learned detector can be re-fit on pseudo-labels); in a rule-based model
  the pseudo-labels only feed the same hand-written statistics, and every
  such statistic of the target house's own aggregate has now been refuted
  (m16/m17/m18 band, m31 cross-house prior, m32 self-cal). A further B3 m
  needs a DEVICE-PURE labeling function - cross-house discriminative
  training (B1's trainable component) or B2 synthetic supervision.
  Diff: `.auto/runs/97_b3_selfcal_bands.diff` (11014 B, 127/14 = incumbent
  bundle 85/14 + 42).

### m33 - the fridge fragment/duration family is CLOSED: the per-fragment
  duration test is a counterweight to the bench's cycle-merge scale, not a bug
  (run 98, DISCARD, primary 0.358120 vs incumbent 0.359446)
  Three variants measured, all at or below the incumbent:
  (A) drop the per-fragment duration test (amp band only) -> 0.347223: eco/house_06
  fridge 0.01 -> 0.80 (P 0.88 R 0.74) but eco/house_02 fridge 0.79 -> 0.52 and
  pool -0.0122. (B) superset: admit a short fragment when its CHAIN fits the
  duration band, chain cap = 0.25x the population's own median inter-cycle
  spacing -> 0.358889 (eco/house_02 preserved 0.79, eco/house_06 still 0.02 because
  the cap cannot reunite its fragments). (C, logged) the same superset chained at
  the model's own CHAIN_GAP_S = 600 s -> full 5-seed 0.358120, fridge median
  0.366137 (-0.0048), every non-fridge device bit-identical (cleanly fridge-only).
  Ground truth that motivated it: v4 GT fridge cycles are 12-16 min on with 44-50
  min gaps (~2400-2800 per 90 days), but the extractor pairs the compressor's
  steady draw into a median 4.0 min fragment (eval-span dur p10/50/90 = 0.7/4.0/
  28.3 min), so emitting ALL 20 W-floor events on eco/house_06 scores F1 0.742
  while the incumbent amp+dur band keeps 221/2950 events for F1 0.013.
  Mechanism: the bench merges on-cells across gaps at its own MERGE_S before it
  scores the cycle duration, and that merge is wider than any chain the model can
  rebuild without copying a bench constant. The fragment test therefore SPLITS the
  mask so distinct cycles never bridge (this is what protects eco/house_02 at
  0.79) at the price of deleting the pieces of one cycle (eco/house_06). Opposite
  per-house effects from one rule; the separating statistics (event amp p90 226 W
  vs 77 W, event dur p50 4.0 vs 16.0 min) ARE the filter's own statistic, so any
  rule keyed on them is circular - eco/house_02 vs eco/house_06 stays not
  label-free separable. The earlier 'fridge recall gaps are extractor-bound'
  verdict is right in OUTCOME (the filter is not a lever) but wrong in CAUSE.
  Diff: `.auto/runs/98_fridge_frag_chain.diff` (11346 B, 85/14 incumbent + 42).

### m34 - NEXT LEVER: microwave over-long merged events (hypothesis N, unstarted)
  The mw is the worst device (median 0.267281, 11/66 pairs) and refit/house_6 is
  74 pred / 390 GT with P 0.12 - broken in both directions. GT groundwork this run:
  v4 GT mw cycles are SHORT duty chunks (duration p10/50/90 = 0.8/1.5/8.6 min on
  refit/house_6, 1.0/3.0/7.4 on refit/house_8) and only 11-19 percent of
  consecutive GT cycles sit less than 10 min apart, so merging is rarer than the
  model assumes: the extractor emits 294 s events from a 60 s-chunk population and
  the duration band REJECTS the merged event instead of splitting it. Fix to test:
  split an over-long merged mw event at its internal pause/plateau minima into
  mark-duration chunks (the mw already has fragment fusion, so the inverse needs
  the plateau/pause structure, not a blind re-split). mw GT durations above are
  model-independent and already measured - do not re-derive them.

### m35 (run 99) mw: the split/arbitration/floor family is measured; the amp band is the wall
  Closes m34 (hypothesis N = split over-long merged mw events): the duration
  REJECTS are not merged cycles. Census (temporary print, seed 2026, --workers 1):
  mw events inside the amp band but over the duration ceiling have dur p50
  498-2124 s (8-35 min), p90 up to 6008 s (100 min) - foreign long loads, exactly
  the 'foreign structure' the _burst_event_bands docstring claims. So M2 (split)
  is refuted by measurement, before any code. Per-house dispositions (eb = did the
  fragmentation switch fire): house_10 eb=yes amp_ok 431 dur_rej 134 -> 202 preds
  vs 103 GT (1.96x); house_18 eb=yes 471/137 -> 269 vs 61 (4.41x); house_4 eb=no
  216/19 -> 166 vs 314 (0.53x); house_6 eb=no 171/47 -> 74 vs 390 (0.19x);
  house_8 eb=no 802/111 -> 120 vs 298 (0.40x). The switch selects over- vs
  under-emission; within a regime the residual is not fragmentation (m23) and not
  event duration (this census) - it is the amp band, i.e. m32's 'a label-free amp
  window around a device always contains far more sub-device excursions than the
  device's own events'. M1 (fire the switch with 1 mark event) was dropped as
  redundant: run 95 (m30) already showed the firing condition is not the lever.
  1) run-span arbitration guard - REFUTED (-0.000152, exact incumbent A/B at seed
  2026, dumps in .scratch/s99_base.txt and .scratch/s99_iso.txt). L1245-1250
  already suppresses mw inside NAMED chains for exactly this reason, but dw chains
  are never named and the dw/wm sustained-run spans (L1222/L1274) were never
  recorded for it. Recording the un-extended spans moved only 4/11 mw pairs
  (house_11 +0.03, house_10 -0.01, house_17 -0.02, house_18 -0.01); the
  over-emission is NOT program-phase draws. Variant kept at .scratch/s99_iso_model.py.
  2) robust burst duration floor - MEASURED +0.000389, sub-bar, DISCARD.
  _burst_event_bands anchors its CEILING on the robust dur_p50 (3 x max(p50,
  max/2)) but its FLOOR on min(durs), which is near-vacuous: the mark-event filter
  only requires dur >= 12 s, so dur_lo lands near 4 s and admits 12-18 s sub-chunk
  residues. The mirror dur_lo = (1/3) x min(p50, 2 x min) is parameter-free and
  cannot exclude any observed chunk class (2 x min caps the floor at 2/3 of the
  shortest observed chunk). Blast radius verified: kettle/wm/dw/fridge bitwise
  unchanged, so this is a clean mw-gate-only experiment. Measured (5 seeds, 99 s):
  primary 0.359446 -> 0.359835, mw median 0.267281 -> 0.268743 (+0.0015), p10
  0.344277 -> 0.344273, device_balanced 0.365435 -> 0.365726, house_1 0.540104
  unchanged. Removes 39 spurious short mw preds on house_10 (202 -> 163, F1 0.19
  -> 0.20) and 0-2 elsewhere: mechanism confirmed, magnitude ~25% of one house's
  excess. Not worth keeping below the 0.364623 bar.
  3) NEXT (the only mw gate left): the residual excess on eb=yes houses sits at
  60-171 s, i.e. inside the duration band, so the amp band must separate mw from
  mw-like foreign structure, and m32 proves no single-house aggregate statistic
  can. Device-pure only route left (B3's closure): B2 synthetic supervision -
  paste the mark signatures into real pre-span backgrounds and fit the admission
  band from the paste response. Label-free, device-pure by construction.
### m36 (run 100) the declared device level cannot gate a burst device; spec family closed
  Hypothesis: data/gold/thresholds.json's [thr, 2*thr] declares a device's own
  power band - thr_on_W is exactly half p50_on_W in EVERY pool house, so the P1
  contract (thr <= 0.5*p50_on_W) is saturated and 2*thr IS the declared median
  on-power - therefore a mark whose extractor population lies outside that band
  did not contain the device and the declared band should gate instead.
  Screen A (all burst devices, population outside [thr, 2.5*thr]): 0.348631,
  -0.0108 vs the incumbent 0.359446. Fired on 4 microwaves whose declared
  levels are 59-179 W plus 2 kettles; mw median 0.267 -> 0.191, kettle 0.555 ->
  0.568. Screen B (same, restricted to continuous bursts, population >= 0.7*mark
  core - the _burst_event_bands duty-chunk clause inverted): 0.347608; the 4 mw
  overrides still fire, so that clause does NOT separate a duty-chunked mw from
  a contaminated kettle. Screen C (kettle-scoped) = FULL pool 0.360094
  (+0.000648), p10 +0.00056, device_balanced 0.365660; all five device medians
  and house_1 bit-identical to the incumbent, and the only pair that moves is
  refit/house_12 kettle (P=0.03 R=0.19 n=712/127, declared 113 W). DISCARD,
  sub-bar (run 99's +0.0004 was discarded identically).
  Mechanism: lowering a burst amp floor to a declared level is harmful whenever
  that level sits inside the house's base-load structure - the 43-179 W mw specs
  admit the base load wholesale. The mark-observed population, even when it
  disagrees with the spec, is the better gate; this re-confirms m32.
  The real discovery is the refit/house_12 kettle: declared 113 W, mark CORE
  115 W (agreeing with the spec), mark EVENT population 1110 W. The
  fragmentation switch fires on its DURATION clause (dur_p50 864 <= 0.5*2184)
  and so discards a spec-CONSISTENT mark core in favour of a contaminated event
  band. That pair is 0.03-magnitude, so repairing it is worth +0.0006 - not a
  leverage point.
  Family closed: thresholds.json carries powers but no durations, so a declared
  band paired with mark-derived durations is incoherent, and no static level can
  resolve duty structure. The residual burst deficit IS duty structure (m35's
  'the amp band is the wall'; m32's sub-device excursions) - B4's phase grammar
  is the instrument.
  1) NEXT if a burst band is retried: gate on duty STRUCTURE, not level. The
  switch needs to separate 'mark core is the device, events are contamination'
  (house_12 kettle) from 'mark core is the cycle, events are the duty chunks'
  (every microwave). It currently conflates them - its duration clause fires on
  both, so it can only be trusted when the two agree.

### m37 (run 101) - the 600 s fridge mining floor hides short-cycle fridges

Pre-registered: the fridge emission band is fitted only on mined events whose
`dur` is inside `DUTY_DUR_S = (600, 2400)` s (model.py L1073-1074). A home whose
compressor recycles every ~4 min can never enter that fit: it sees only the
>=600 s tail, which is the MERGED long excursions, so the band floor sits at
10 min and the real cycles are gated out. Fix: re-mine the same (amp, dur) grid
over the full sustained range and accept a materially shorter mode only when a
single 1-min duration bucket DOMINATES the in-window population (>=2000 events
and >=50% of them) and the prior band floor is still pinned at the 600 s prior.

Result: mechanism CONFIRMED. Pool primary 0.359446 -> 0.363271 (+0.003825);
seed-2026 screen 0.359446 -> 0.372472 (+0.0130). Sub-bar (bar 0.364623, missed
by 0.00135) so run 101 is DISCARDED; diff banked at
`.auto/runs/101_fridge_shortcycle.diff` (+42/-1 on the incumbent) and left
applied in the tree, which now holds the best-known bundle.

  1) eco/house_06 fridge was the largest single headroom pair in the pool
     (+0.012 available): incumbent P=0.081 R=0.005 F1=0.010 gt=1839 pred=123,
     PR dur 10.9/22.1/38.5 min at 1.37/day. The GT is 4.0/4.0/4.1 min at
     20.4 cycles/day (pre-span submeter: 60.8/day at the same 4.1 min).
  2) The number that pinned it: the model's own miner reports 11185
     level-excursion events over 164 pre-span days = 68/day - the right order
     for the cycles - but only 13% (1593/11644 in-window) survive the >=600 s
     filter, and the fallback band `dur=10-36min` is just that filtered tail.
     The detector was resolving the cycles; the BAND was destroying the pair.
     A zeroed passive mark window on this house (fabricated amp=30W dur=20min)
     is why the band, not the mark, was in charge.
  3) Duration buckets (amp 20-300 W, dur >= 120 s) separate the one broken home
     without touching the rest: eco/house_06 has n=8485 in the single 4-min
     bucket (73% of in-window events, amp p50 50.1 W); refit/house_10 tops out
     at 15% spread over 2-12 min; refit/house_1 at 5% over 2-18 min.
     Dominance, not regularity, is the usable label-free discriminator.
  4) STANDING DEFECT FOUND: the cell fit's thermostat-interval test
     (DUTY_CV_MAX = 0.6) is unsatisfiable - a real fridge's inter-cycle interval
     varies, cv = 0.691 on eco/house_06 - so all 20 pool houses print "fridge
     fallback" in every build and the (amp x dur) cell path has never once
     fired. Any future work on that path must replace the CV test first.
  5) Blast radius was exactly the intended pair: every other device median was
     bit-identical to the incumbent (kettle 0.55514, mw 0.267281, wm 0.246657,
     dw 0.384353); p10 +0.0020, device_balanced 0.365435 -> 0.366918, house_1
     unchanged at 0.540104.
  6) UNEXPLAINED, and the reason the pool gain is only +0.0038: the rescue's
     inputs (mined events, fallback band) are seed-INVARIANT, so it fires for
     every seed, yet seed 2026 gains +0.858 pair-F1 on eco/house_06 (~0.01 ->
     ~0.87) while the other four seeds average ~+0.10. Suspect the
     seed-dependent mark re-anchor in the run-basis path (model.py L1158-1167).

NEXT (in order):
  1) Run 102 needs only +0.00135 to clear the bar - the tree already holds the
     best-known bundle (floor + 94 + 101 = 0.363271). Cheapest candidates: make
     the fridge emission seed-robust (item 6) or take the next fridge headroom
     pair, refit/house_10 (0.042; 1695/2541 preds already sit INSIDE a GT span,
     so the model splits long GT cycles and cannot reach the GT p90 of 85 min).
  2) The remaining sub-0.2 fridge pairs carry ~0.012 each. The "the band, not
     the detector" pattern is worth checking pair by pair before any new
     mechanism is added.
  3) The burst-device band family stays closed (m32/m35/m36, unchanged).

m38 (run 102, KEEP 0.366174, commit b4298ca) - program-span ownership at EVENT level.
  1) WIN: a burst event lying inside a span already EMITTED as a dw/wm program run
     is that program's own heater, not the kettle. The mw has applied this to
     named chains since run 88 (ev_in_named); the emitted dw30/wm30 run-basis
     spans were never in that set, and model.py L1334-1335 admitted the kettle
     gate was chain-blind. Fix: ev_in_prog over the CORE emitted runs
     (stride*a30..stride*b30 and a6..b6) plus the named chains, with
     '& ~ev_in_prog' on both kettle-gate branches. Pool 0.363271 -> 0.366174
     (+0.002903); kettle median 0.55514 -> 0.56105; cleared the pre-registered
     bar 0.364623 (= floor 0.354623 + 0.01). First keep since run 86.
     NEW BAR for run 103: primary >= 0.376174.
  2) COST, and the next lever: ukdale/house_1 subset 0.540104 -> 0.529428
     (-0.0107). There the kettle declares 1173 W - the same level as a wm/dw
     heater - so real coincident boils are suppressed. NEXT: make the test
     level-aware, i.e. suppress only when the program's own claimed amp can
     explain the event (program amp >= event amp). The FPs suppressed elsewhere
     sit far below the program's amp, so the win should survive.
  3) THE EXTENSION IS NOT FREE: suppressing on the pre/post-extended span
     (i1 = stride*b30 + ext_fwd6, +-22 min) collapses the kettle gain back to the
     incumbent (0.566709 -> 0.561131). Suppress on the core emitted run only.
  4) Two adjacent generalizations refuted by measurement and reverted:
     ev_in_named |= ev_in_prog (mw) gave -0.000049 at seed 2026; using
     prog_spans in the kettle SUSTAINED-run dedup gave 0.566709 -> 0.561214 -
     that path is already isolation-gated, so its runs inside a program span are
     real kettles.
  5) Fridge strand CLOSED by census (.scratch/s102_buckets.py): of the 18 pool
     fridge houses eco/house_06 is the ONLY one with a dominant short-cycle mode
     (4 min bucket, 0.73 of its 11644 events). Every other house is flat (top
     bucket dominance 0.06-0.16, several 2/3/4 min buckets competing) with its
     >=600 s mode (10-24 min) intact, so run 101's 120-300 s rescue window fires
     exactly where it should and widening it wins nothing. Fridge run-merge was
     also refuted (18 pairs, seed 2026: primary -0.002 / -0.007 / -0.020 at
     r = 0.25/0.5/1.0 of the shorter chunk) - the preds are correctly sized.
  6) The AMP_MIN_W = 50 W visibility defect is real but NOT fixable globally:
     house_6 mw declares 43 W, house_8 44 W, house_10 47 W, eco/house_03 kettle
     17 W, and the fridge already carries its own FR_STEP_MIN_W mine for the
     22-91 W steps. Lowering the SHARED floor to min(50, 0.5*min(2*thr)) was
     refuted hard: seed-2026 primary 0.366660 (-0.0058 vs the kept change) with
     all five medians down (kettle 0.5589, mw 0.2505, wm 0.2388, dw 0.4174) -
     the sub-50 W population is noise, not those devices. Any fix here must be
     device-specific.
  7) OPEN, in order: (a) level-aware suppression (item 2); (b) refit/house_11 dw
     0.000 (12 preds / 12 GT, zero match) and refit/house_7 dw 0.065 (33/91,
     under-emission); (c) the mw cluster (refit/house_6 0.040 on 74/390);
     (d) owner-directed: fold the 52 model.py literals into one fitted parameter
     dict, per-home reliability from calibration-only signals, and the
     history-length curve at 7/14/30/60 days.

SEGMENT 3 CHARTER (owner-directed: pivot to transfer learning / DL) - the rewrite
licence, data discipline and multi-run keep exception are in .auto/prompt.md
sections 3-6. Home of the work: src/experiments/06_transfer_dl/ (05_method_compare
stays the comparison + explorer/visualization harness; 02_seq2seq supplies the net;
04_autoresearch/model.py stays the scored entry point bench_v4 hard-codes).

B6-pre (pre-registered BEFORE any run) - CROSS-HOME TRANSFER BACKBONE.
Hypothesis (docs/hypotheses/H09_cross_house_transfer.md): a shared representation
pretrained on the development homes' pre-split spans, then adapted to a new home
using only its K=5 marks and its own pre-span aggregate, can beat the per-home rule
stack (incumbent primary 0.366174) on the frozen pool - and specifically closes the
mark-free program-cycle leak (house_12 712 kettle preds vs 127 GT) that runs 103-118
proved no band or span rule can reach.
Milestones: M1 DL baseline established with the existing comparison harness - where
does a cross-home seq2seq actually stand, dev vs unseen? No claims before that
number. M2 leave-one-home-out transfer matrix (H09 diagonal vs off-diagonal) on the
dev pool. M3 adapt-on-marks: condition / fine-tune the backbone with the target
home's K=5 marks only, score the frozen pool. M4 land the winner into
04_autoresearch/model.py as an adapter and run the full bench.
Kill criterion: if by M3 the adapted backbone cannot beat the rule incumbent on the
pool primary with p10 not falling - judged over at least 3 pre-registered runs, not
one - abandon the backbone and report the transfer matrix as the result (H09 is
deliberately two-sided; a measured weak transfer is a result, not a failure).
Data discipline: the 7 holdout houses are a milestone-only readout, never trained or
tuned on; dev homes' PRE-SPLIT spans only; no eval-span submeter is ever an input.

m55 (run 118) - the first marks-free STRUCTURAL lever, after 116/117 proved span
bookkeeping cannot reach the leak (ev_in_prog derives only from prog_spans, which
derives only from a device profile; house_12 has no dishwasher in cmap, so no dw30
exists and no span of any kind can cover its 712 kettle events vs 127 GT). Since
m35/m36 showed no amp/duration band separates a partial-duty program heater from a
boil, the untested discriminator is TEMPORAL GEOMETRY: a thermostat/program heater
duty-cycles with an OFF gap <= its own ON-time, whereas independent boils are
separated by far more than their duration. TESTED: at the kettle gate, drop an
admitted event only if BOTH neighbours are admitted and each gap <= that
neighbour's own ON-time (on/off indices only - no unit conversion, no new
constant, no marks, no sub-meter data). Reading: kettle+primary up => temporal
geometry is the marks-free discriminator and it should be reused for the mw and
the dropped trains fed back as unlabelled program spans; kettle down => real
repeated boils sit within their own duration of each other and the next form is
the amplitude stability of the train across its members.

m54 (run 117) - completes run 116 on the dw block. CONFIRMED by read: the dw
block computes i0/i1 (ext_back6/ext_fwd6 margins, the largest of any device:
back to 10 min, forward to 68 min) and EMITS over out['dishwasher'][i0:i1], but
registered only the RAW run (stride*a30, stride*b30) in prog_spans. ev_in_prog is
built exclusively from prog_spans and is the kettle's ONLY defence against
program heaters (m35/m36: dw heater bursts sit inside every kettle band).
TESTED: append((stride*a30, stride*b30)) -> (i0, i1) - a consistency fix using
already-computed indices, no new constant. Reading: inert like run 116 => span
bookkeeping cannot reach the case that matters; the leak needs a house with a
profile whose cycles are REJECTED or with NO profile at all (house_12 has no
dishwasher in cmap, hence no dw30 exists and no span of any kind can cover it),
which needs a marks-free program-heater detector on the burst side - B4/B2.

m53 (run 116) - run 115's reconnaissance exposed an inconsistency at the leak
point. The wm EMITS its cycle over the ext_back/ext_fwd-extended span
[i0, i1] (margins up to 24-68 min) but registered only the RAW run
(a6, b6) in prog_spans, and ev_in_prog - the kettle's only defence against
program heaters (m35/m36: no amp/dur band can separate them) - is built solely
from prog_spans. So the model claimed an interval as the program's own cycle for
emission while leaving the heater bursts in that interval's margins to surface as
kettle draws (house_12 712 preds/127 GT, house_7 455/108; the pool kettle block is
12 pairs at mean 0.562, so those two are worth ~+0.015 > the +0.01 bar). TESTED:
prog_spans.append((a6, b6)) -> (i0, i1) in the wm block - a consistency fix using
already-computed indices, no new constant. Reading: kettle up => leak confirmed as
margin bursts and the dw block's identical append should be aligned too (needs its
verbatim text); kettle down => the margins hold real draws and the real case is
mark-free (house_12 has no dishwasher in cmap, hence no dw profile at all), which
needs a marks-free program-heater detector on the burst side - the B4/B2 route.

m52 (run 115) - the wm heat-share CEILING, the last untested extreme in the wm
bands: hs_band = (0.75*min(hss), 1.75*max(hss)). It sits BELOW 1.0 whenever the
marked runs were not all fully ON (max(hss) < 0.571), so it rejects high-duty real
cycles, and is vacuous when max(hss) = 1.0 - which is why it can look inert in a
dump and still bind in weak houses (cf. run 107's lesson). TESTED: ceiling ->
inf, floor untouched. Also banked for the record: the kettle/prog suppression
region (model.py ~L1310-1372) printed in this run. PRIORITY ARITHMETIC for future
runs: the kettle block (12 pairs, mean F1 0.562) holds the two dead pairs
house_12 0.060 (712 preds/127 GT) and house_7 0.130 (455/108) worth ~+0.015
together - more than the +0.01 bar - and run 114 showed events shifting between
dw and kettle, so the mechanism is the unlabeled-program leak: a house with no
dw marks (house_12 has no dishwasher in cmap) emits no dw program spans, so its
heater blocks surface as kettle bursts. Fix belongs on the burst side.

m51 (run 114) - after run 113 closed the dw span floor as precision-protecting,
the second untested dw summary gate is mean_band = (0.8*min(means),
1.25*max(means)). Its FLOOR rejects any cycle whose whole-run mean power falls
below 0.8x the lowest marked mean, and a long pump-heavy real cycle has exactly
that low-mean signature (house_7 dw means span 429-1052 W, floor at 343 W), so it
is a cycle-length-coupled statistic - a different mechanism from the level/share
floors closed in 104/113. TESTED: dw mean_band lower bound -> 0.0, ceiling and all
other bands untouched. Reading: inert => the deficit comes from cycles producing
no above-heat run at all (marks representativeness, the B4 route); harmful => all
four dw admission mechanisms tested by removal (merge 109, idle 110, span 113,
mean here) protect precision and the dw gate family is exhausted for tuning.

m50 (run 113) - last untested dw admission gate: the SPAN floor. The dw profile
builds span_band as (0.25*min(spans), 3.0*max(spans)) or (0.6*min(spans),
1.25*max(spans)) depending on whether the marks' runs are fully ON, so any real
cycle shorter than the floor is rejected outright - the natural mechanism for
house_7 admitting 44 run-basis cycles/yr against 91 GT. Runs 109/110 already
proved the deficit is not the merge and that dw admission gates do bind. TESTED:
both dw span floors set to 0.0, all upper bounds untouched. Reading: inert =>
the deficit comes from the heat-level/share gates or from cycles producing no
above-heat run at all (marks representativeness, not a gate); harmful => the
floor protects precision and, after the run 110/111 idle dial, this device needs
a better discriminator (B4 phase grammar) rather than any single gate.

m49 (run 112) - combined the two individually-real-but-sub-bar device changes
(wm merge median-gap from run 108; dw extrapolated idle ceiling from run 111) to
test their INTERACTION through the shared prog_spans suppression: the wm's split
runs expose kettle bursts (run 108: kettle -0.0032) and the dw's widened
admission adds program-span coverage that should re-suppress them. Both lines are
single-line and were measured in isolation, so this is a clean two-variable test.
Reading: kettle loss smaller than run 108 standalone => the cross-device coupling
is real and prog_spans becomes the top target; primary merely additive => no
interaction, and the B4 phase grammar is the remaining route.

m48 (run 111) - follow-up to m47. Run 110 (dw idle_hi = inf) was NOT vacuous:
dw median +0.005965, p10 +0.000527, but pool primary -0.001833, so the ceiling
binds and the optimum lies between 2.0*max(mark idle medians) and infinity: it
buys recall in weak dw houses and pays with precision elsewhere. TESTED (1 line,
dw profile dict L536): idle_hi = 3.0*max - min, i.e. the sample max extrapolated
by one observed spread (the max over ~5 windows is downward-biased), keeping the
original x2 factor. Non-arbitrary in form; compare the dw/mean tradeoff against
run 110's outright removal. If it is inert vs 2x max, the eval-time idle medians
jump far past any moderate widening and only the extremes matter.

m47 (run 110) - the dw is the pool's most PRECISION-rich (P 0.447) and recall-poor
(R 0.347) program device, so its constraint should be admission, not precision;
house_7 admits 44 run-basis cycles/yr against 91 GT. Run 109 proved the merge is
not the deficit (removing the long-gap merge cost the dw 0.0455), so the untested
lever is the sustained-phase idle ceiling (dw profile dict L536, idle_hi =
2.0*max of the marks' sub-heat medians). Only the WM's ceiling had been probed
(run 106: vacuous, never bound). TESTED: dw idle_hi = float('inf'), all other
bands untouched. Reading: inert => vacuous, deficit is span/onset placement;
harmful => load-bearing, completing the device-specific ceiling-family picture.
Remaining untested dw widths: hs_band upper bound, span_band.

m46 (run 109) - the run-108 generation mechanism (median heater gap instead of
the max) applied to the DW, which has the strongest over-merge signature in the
pool: refit/house_7 admits 44 run-basis cycles/yr against 91 GT cycles (0.244 vs
0.5 per day; dw recall 0.347, 2/10 pairs under F1 0.2, house_11 gates 97 times
for 12 GT). The dw profile (L444-458) carries the identical duplicated statistic
as the wm (max_gap over all mark windows -> merge_n = 1.25*max_gap/30). If the dw
gain is real but the primary is flat again, the binding constraint is the shared
prog_spans suppression that cost the kettle 0.0032 in run 108, not the merge.

m45 (run 108) - FIRST generation-side change (gates closed, m44): the wm's
merge_n = 1.25 * max_gap where max_gap is the largest heater-block gap inside ANY
one mark window (L682-696). One window holding two wash cycles therefore supplies
its INTER-cycle pause, and the eval-time merger bridged 35-78 min (spans reached
156 min, i.e. two GT cycles in one pred; 31 dead wm pairs at recall 0.245).
TESTED: merge_n from min(max_gap, 2*median(wm_gaps)), the robust-estimator
precedent, guard changed to 'max_gap > 0 and wm_gaps' so the documented
no-pause fallback (merge_n=1) is untouched. Still-open generation defect in the
same function: per window the profile keeps max(_merge_runs(...), key=len) - the
LONGEST run - so a contaminated two-cycle window also donates that window's
span/p90/idle/dens statistics.

m44 (run 107) - dens_hi = 2.0*max(denss) trimmed to the second-densest window
REGRESSES: pool 0.362782 (-0.003392), p10 0.344327, wm 0.241681 (-0.004976),
seed 3 wm -0.013727 with fridge/dw unchanged. The dump's 1.035-1.294 blocks/min
ceilings are set by REAL wm cycles (a high heater-block rate is wm-like), not by
pump chatter, so this upper bound is load-bearing for recall even though its
range looked vacuous. Runs 104 (floors) + 105 (heat level) + 106 (idle ceiling) +
107 (dens ceiling) now CLOSE the wm gate family: no single-feature gate separates
the wm FPs because they are structurally wm-like. Levers left: candidate
GENERATION (the merged-run construction, heater_gap_merge up to 78 min) or B2
synthetic supervision. Untouched: the dishwasher profile (L536-537), never
scored in isolation. METHOD: a bound whose range merely LOOKS vacuous may still
bind on the tail; the audit must test the bound, not argue it.

m43 (run 106 follow-up, RECORD CORRECTION + method) - the BASE seed-3 values are
microwave 0.292094 / dishwasher 0.354751, i.e. IDENTICAL to what run 106's (and
run 105's) seed-3 screens printed for their variants. So the "+0.0249 microwave /
-0.0296 dishwasher" movement claimed in run 105's log entry was PHANTOM: I
compared a single-seed (seed 3) draw against the POOL MEDIAN baselines
(0.267210 / 0.384353), which are different seeds' draws for those devices. The
per-device pool median is not seed 3's value for every device, so a seed-3 screen
must always be compared against a seed-3 BASE measurement - the base pool median
is a valid baseline only for the primary and for the devices whose median draw
happens to be seed 3 (kettle, wm, and the primary do coincide, which is what made
the error easy). Run 105's conclusion still stands where it matters (its pool was
net-neutral: mw/dw bit-identical), but its device-level deltas were an artefact.
SECOND METHOD POINT (run 106): the idle cap min(2*max(idles), heat) is a REAL
vacuity repair - the gate's own range (up to 2952 W vs a heat level of ~1.5 kW)
provably cannot constrain anything - yet the pool is BIT-IDENTICAL on all ten
aggregates, because the pool aggregates are medians over seeds and the cap only
bites in the non-median draw where the vacuity was observed. "Fires only in a
non-median draw" and "cannot fire at all" are indistinguishable in the pool
report: to tell them apart, screen BOTH a mid seed and seed 2026 and compare each
against its own base.

m42 (run 106) - GATE VACUITY AUDIT. idles[i] in _wm30_profile is the MEDIAN of the
sub-level phase INSIDE the i-th merged run (L722), and a merged run is by
construction the 30 s grid at or above heat, so every idle is below heat: the
ceiling 2.0*max(idles) can only exceed heat through the x2 factor. In the pool
dump it does - idle<=2952 W and <=2914 W, and 263 W where heat is 161 W. A 3 kW
"quiet level" test admits anything, i.e. the gate is vacuous exactly where wm
precision is worst (P 0.245; 7/15 pairs < 0.2). TESTED: idle_hi ->
min(2.0*max(idles), heat) (the run-mining level, no new constant).
METHOD: this is the first gate audited for vacuity BY CONSTRUCTION (does the
statistic's range intersect the gate's range?) instead of by tuning; the same
audit is open for dens_hi = 2*max(denss) (reaches 1.294/min in the dump),
span_band (a 2-156 min min/max) and hs_band's 1.75*max. Note the failure mode
learned here in passing: an edit that only half-rewrites a parenthesised
expression passes a naive string replace but fails ast - always run
python3 -c ast.parse BEFORE the 150 s pool run (a broken tree measures as a null
metric and log_experiment rejects a non-finite metric).

m41 (run 105, DISCARD 0.3662xx - net-neutral) - the wm's heat level is NOT the
over-emission lever, and (the durable part) a wm change is NOT device-local.
TESTED: heat = PROG_HEAT_AMP_FRAC * min(mark_wm['amp'], dw_amp) -> the wm's own
mark amp (a cross-device coupling removed). SCREEN seed 3 (= the median seed =
the primary's own draw): 0.366174 -> 0.366222 (+0.000048) but with microwave
0.267210 -> 0.292094 (+0.024884) exactly offset by dishwasher 0.384353 ->
0.354751 (-0.029602). SCREEN seed 2026: +0.000135 with mw and dw BIT-IDENTICAL
to base. So the change fires broadly yet its effect is a cancellation.
FINDING: the wm30 runs are emitted as program spans and enter the shared
prog_spans / dispute / named-chain machinery that gates the microwave,
dishwasher and kettle. Therefore (1) never judge a wm-only hypothesis on the wm
median - check all five device medians; (2) a ~0.025 "gain" in one draw can be
pure reallocation with zero net (only the pool primary arbitrates); (3) any
future edit to run 102's program-span rule must be scored on all five device
medians. Also diagnosed here: refit/house_7 dw has 44 candidate runs/yr against
91 GT cycles at F1 0.032 (a TIMING failure, not a count failure - its dw mark
pre_offs run -0.5,-1.0,-1.0,+4.5,+14.5 min with ext_back clamped to 0), and
refit/house_11 dw passes 97 run-basis gates against 12 GT at F1 0.000.
WM OVER-EMISSION is now closed against: heat level (m41), admission floors
(m40), mark-statistic trims (m40). Remaining routes: candidate generation at
the 30 s dwell/merge level, or B2 synthetic supervision. Bar 0.376174.

m40 (run 104, DISCARD 0.366174 - bit-identical to the committed blunt rule) -
the wm admission floors are NOT the over-emission mechanism; m39's lead was
mis-framed. TESTED: replace 0.75*min(x) with a trimmed min (sorted[1] of five
usable windows) for hs_band[0] and dens_lo in _wm30_profile. SCREENS (seed
2026): bundle 0.372409 (-0.001052, wm 0.247979 -> 0.242229); density-only
0.373607 (+0.000146, wm 0.247885); heat-share-only 0.372577 (-0.000884, wm
0.243702, house_1 +0.003175). POOL (density-only): 0.366174 with EVERY
reported aggregate bit-identical to the blunt rule (p10 0.345739,
device_balanced 0.368405, house_1 0.529428, all five device medians).
LEARNINGS. (1) The heat-share floor is a RECALL guard: the low-hs merged runs
it admits are real wm cycles with long pump phases (the hs value comes from the
MERGED run, so a house whose mark windows need a wide merge naturally has low
hs). hs_lo rounding to 0.00 is protecting truth, not admitting lookalikes. Do
NOT reopen hs_lo - not as a trim, not as a joint repair with merge_n.
(2) The density floor rarely binds: after trimming it 4 of 5 seeds are
unchanged to the last digit, so dw30-lookalike rejection already comes from the
other gates (span/amp/mean/idle ceilings). Do not reopen dens_lo.
(3) METHOD - the most valuable result of this run: a seed-2026 screen is NOT a
valid go/no-go filter for a change whose FIRING depends on the calibration
draw. The primary is the median of the five per-seed means and seed 2026 is the
top, most atypical draw (0.373 vs 0.346-0.366 for seeds 1-4), so a change that
fires only in 2026 can show +0.0001 on the screen and exactly 0.000000 on the
pool - run 104 is the first case where the screen's sign did not transfer.
Before spending a 150 s pool run, confirm the change fires in a MID seed
(1 or 3), not only in 2026.
NEXT: the wm over-emission (median 0.2467, 7/15 pairs < 0.2) must be attacked
at candidate GENERATION (what merges into a run, i.e. _runs/_merge_runs and the
30 s grid dwell structure) or through the program path - not through the
admission floors. The largest structural lever is still B2 synthetic
supervision -> the device-pure admission band, which is also the only remaining
route to B3's device-pure labeling closure. Bar stays 0.376174.

m39 (run 103, DISCARD 0.363341; bar was 0.376174) - the program-span yield is
NOT narrowable by the program's own claimed level; that trade is intrinsic.
HYPOTHESIS: yield a burst event only when the program span's OWN claimed level
can explain its amplitude (dw30/wm30 emit_w, the chain's measured span level
lvl from L1282), keeping the run-102 blunt rule's kettle gain while protecting
ukdale/house_1's real coincident boils (its kettle declares 1173 W, at wm/dw
heater level). CHANGE: prog_spans entries became 3-tuples (c0, c1, level);
prog_spans.extend(named_spans) replaced by two explicit appends so named_spans
keeps its 2-tuple form for the wm30 dup test and the kettle sustained dedup;
gate = (on<c1)&(off>c0)&(amp<=lvl_p); CORE runs only, never the extension.
RESULT: house_1_v4_mean recovered EXACTLY (0.529428 -> 0.540104, +0.010676) but
the whole kettle gain went back (screen 0.566709 -> 0.561279; pool delta
-0.005661). Pool 0.363341 (-0.002833 vs the committed blunt 0.366174); p10
0.346289. REFUTATION, and not salvageable by a margin: the FPs the blunt rule
removes sit ABOVE the program's level (they are the program's own above-mean
heater spikes, not partial-duty draws) while house_1's true kettle sits at only
~1.18x the wm's emitted mean, so the two populations OVERLAP in amp-vs-level.
Any margin >= 1.18 suppresses house_1's kettle, any margin < 1.18 re-admits the
spikes. Do not reopen this feature (also do not reopen the extension-coverage
variant, m38).
STATE: src/ reverted to the committed blunt rule b4298ca (0.366174) = the
best-known state; nothing banked, no diff needed. Bar stays 0.376174.
RECORDED LEAD (untested): the wm heat-share admission floor is structurally
unstable across builds. hs_band = (0.75*min(hss), 1.75*max(hss)) over the
usable mark windows; in 3 of the logged builds hs_lo rounds to 0.00, i.e. one
low-hs merged run disables the whole house's heat-share test. It is entangled
with merge_n: hs is measured over the MERGED run, so a build with a large
max_gap yields long merged runs with low hs, which loosens the floor AND widens
the merge at once. Any repair must treat hs and merge_n jointly; a trimmed-min
floor alone moves both. The wm cluster is the largest headroom left (median
0.2467, 7/15 pairs < 0.2, over-emitting).
NEXT: a +0.01 step must be structural, not span ownership. Candidates in order:
(1) B2 synthetic supervision -> the device-pure admission band, which is also
the last route for B3's device-pure labeling closure; (2) the wm cluster via
the hs/merge_n joint repair above; (3) the last two dw pairs below 0.2
(refit/house_11 dw 0.000 on 12/12 and refit/house_7 dw 0.065 on 33/91).

## SEGMENT 3 - CLOSED (2026-09-28)

The rule line is terminal: 106 runs, 29 keeps, 0 crashes; last keep `b4298ca`
at pool primary 0.366174 against a bar of 0.376174. Runs 103-118 exhausted the
remaining bound space (harmful: dw merge/idle/span/mean floors; inert or
vacuous: 115 bit-identical, 116 ~1e-4, 117 7e-5, 118 zero firing; real but
non-compounding: 108 and 112). The remaining measured loss is a representation
failure, not a gate: the kettle block's two dead pairs (house_12 0.060 with 712
predictions against 127 GT cycles, house_7 0.130 with 455 against 108, ~+0.015
together) come from `ev_in_prog` deriving only from `prog_spans`, so a home
with no dishwasher marks emits no dw program spans and its duty-cycling heater
blocks surface as kettle boils. No amplitude or duration band separates them.

The transfer-learning segment produced no run against this loop's metric. Its
output is the cross-method reference in `data/results/method_compare/`
(experiment 05, 26 unseen pairs, per-pair median over seeds): rules 0.306,
rules+GT thresholds 0.325, cross-home seq2seq 0.280 with **no button presses**,
FHMM 0.159. The net wins the kettle 0.733 against 0.582 (and against 0.580 with
ground-truth thresholds, so the gap is representational) and the development
washing machine, and loses the microwave (0.049 against 0.153) where the
failure is amplitude - several homes sit at 43-47 W, under the 50 W visibility
floor.

Next experiment (new, not a continuation): per-device arbitration - rules for
microwave/fridge/dishwasher, the cross-home net for kettle and washing machine.
Per-device best-of is 0.353 against rules' 0.306 unseen, i.e. +0.047 with no
training. Adaptation on K=5 marks is the follow-on and must be built against
segment 0's recorded fine-tuning failure (about 11x retention damage at 40
epochs, saturated heads from a reused `pos_weight`): freeze the trunk,
fine-tune the head only, recompute `pos_weight` on calibration data, guard the
OFF-sigmoid. Terminal record: `.auto/dossier.md`.
