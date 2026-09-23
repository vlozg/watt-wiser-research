# FHMM session-supervised experiment plan (Experiment 2 — family B)

**Status:** Frozen 2026-09-22 (AI work). Owner approved starting the experiment with the recommended defaults; the §8 checklist records the frozen values. Any later change is a protocol break and gets logged as one.
**Serves:** H01 (K-curve, in FHMM form), H02 (the shared instrument), H04 (weak-class reachability), H05 (books-close), H06 (valid-session yield), H09 (per-home estimation).
**Method background:** `docs/research/fhmm-notes.md` (patent + K&J verification, training regimes, overlap mechanics, unknown handling).
**Contract:** `docs/PROBLEM_STATEMENTS.md` §2–§7.

---

## 0. The question, one line

Does a session-supervised additive FHMM beat the rules anchor on the §7 episode contract — classification, span localization, and energy attribution alike — at the session budget the product prescribes (K = 3 valid sessions), and where exactly does it fail (overlaps, weak classes, unknown loads)?

## 1. Arms — one instrument, one contract

| Arm | What it is | Purpose |
|---|---|---|
| **A0 — anchor** | Existing rules baseline (threshold + hysteresis + dwell), already implemented in `src/experiments/00_baseline/` | The floor every arm must clear (§6 ladder) |
| **B1 — session-supervised FHMM** (treatment) | Additive FHMM, 2 states per device + baseline/UNKNOWN component; emissions and transitions estimated from K valid sessions (aggregate-only over GT press intervals); exact joint Viterbi; posterior marginals + innovation → confidence → UNKNOWN | The family-B bet |
| **B0 — unsupervised EM ablation** | Same FHMM, zero sessions: differencing init + EM on pre-split aggregate (K&J-style); chains named post hoc by best match to profile stats (analysis-only step, labeled as such) | H01 in its cleanest form: how much of performance is *separation* vs *naming*? If B0 ≈ B1, the calibration ritual buys less than assumed |
| Deferred — port-Hart event matcher (family A) | Signature library + ON/OFF pairing + dwell plausibility | Separate pre-registration if approved; keeps v1 arms minimal |

## 2. Data — what we actually have (verified this session)

- **Substrate:** UK-DALE houses 1, 2, 5 — the houses with curated marks and reserved test spans (`data/gold_annot/ukdale/*/splits.csv`; house_1 boundary 2013-10-01). Houses 3/4 exist in the gold layer but have no mark curation — transfer check (H09) later, out of v1.
- **Button-press pools** (mark counts from `manual_cycles.csv` / `rule_cycles.csv`, this session): see Appendix A. Consequences:
  1. Program devices (washer, dishwasher) have exactly 20 marks per house → **K = 20 is the full pool** (K=all ≡ K=20); CIs at high K come from bootstrap resampling and will be wide. State this in every report.
  2. Microwave has GT only in houses 1–2; dishwasher only in houses 2 and 5. Score per device only where GT exists; print the coverage table.
  3. Fridge has **no press marks anywhere** (duty class — nothing to press). Needs the §6 decision.
- **Parity rule (H02 step 2, binding):** episodes built from the device submeter channels via `baseline_lib.build_episodes` with the profile thresholds (thr/dwell/merge from `device_profile.csv`), restricted to the scoring window. Submeters are used for evaluation only — never by any model. **Press pools** remain the gold_annot marks (manual for program devices, rule for burst devices), pre-split only. Verified this session: post-split GT is rich for house_1 kettle (5,759) and microwave (4,272), moderate for house_2 (kettle 235, microwave 114), and house_5's rule marks stop before its split (kettle last 2014-09-07) — the coverage table is printed in every report. house_1 = first 12 months post-split (2013-10-01 → 2014-09-30); house_2 = full post-split span (2013-08-12 → 2013-10-10); house_5 = full post-split span (2014-10-10 → 2014-11-13). Rationale: house_1's post-split record is 43 months and the window bounds compute; house_5's post-split GT coverage is thin and is reported as a coverage limitation, never patched after scores exist. every session reads the **aggregate over the GT interval only** — never the device submeter. GT selects the windows (that is what a press is); the aggregate supplies the numbers. `device_profile.csv` stats are submeter-derived and are used for inventory and the mechanism check only, never as model parameters.
- **Cadence:** native 6 s primary; 60 s rung secondary (bucket-mean; H03).

## 3. Model spec (v1, deliberately small)

- **Device set:** the 5 canonical targets enrolled; everything else is unmodeled.
- **States:** 2 per device (OFF/ON). Washer and dishwasher are modeled as 2-state activity windows in v1 (the §7 contract evaluates episodes, not phases); multi-state phase chains are a v2 extension, pre-registered separately.
- **Emissions:** OFF ~ N(0, σ_off²), σ_off = pre-split ambient noise sd per house; ON ~ N(μ_d, σ_d²), estimated from valid sessions (in-session aggregate minus the local pre-press baseline level). Variance floors frozen (§8) to avoid degenerate posteriors.
- **Transitions:** per-device 2×2; p_stay from session dwells (E[dwell] ≈ 1/(1 − p_stay)); class-prior fallback where sessions are thin (program 600/600, burst 30/60 rule parameters from the profile pipeline). Dwell-prior floors frozen.
- **Baseline / UNKNOWN component:** house always-on floor estimated pre-split from the aggregate (never the submeters); per-timestep innovation test demotes unexplained timesteps to UNKNOWN (constant c, frozen); marginal-based rejection demotes low-confidence device claims (θ, frozen). Both mechanisms report; the residual line prints first (H05).
- **Decoding:** exact factorial Viterbi over the 2^5 = 32 joint device states per timestep. Trivial compute; no approximations needed at K = 5.
- **By-products:** per-device posterior marginals P(device ON at t) and per-timestep innovation — the §4.1 confidence signal, not a threshold hack.
- **Energy attribution:** integrate emission means over claimed ON spans; inside overlaps energy is imputed by emission means (a stated limitation, printed in the report); books-close line first: attributed + residual vs aggregate (H05).

## 4. Protocol (inherits H02 steps verbatim where applicable)

1. **Session sampling:** per device, R = 20 seeded bootstrap draws of K GT intervals from the pre-split pool; K ∈ {1, 2, 3, 5, 10, 20} (H01 grid); per-device independent draws; all five devices parametrized at the same K for a joint decode.
2. **Valid-session gating (H06):** interference-flag rule frozen before the run; flagged sessions do not count toward K; attempts-vs-valid yield recorded per device class (predicted > 1 for program devices).
3. **Training:** moment estimation from valid sessions (no EM in B1). Contaminated-session bias is the H12 concern — the flag gate plus the P3 placement sensitivity address it.
4. **Decoding:** over the full post-split test span per house, native and 60 s.
5. **Scoring:** greedy one-to-one episode matching (reuse `baseline_lib.match_onsets` / `prf`); onset tolerance τ = 12 s native / 120 s at the 60 s rung (2× cadence, the baseline convention); dwell-ratio band frozen with the constants; UNKNOWN always reported; residual printed first. Scoring uses the frozen evaluation-GT source and windows (§2).
6. **Strata:** solo vs co-occurring GT episodes (the 2+ ON fraction of each test span is measured and reported). FHMM vs anchor per stratum is the falsifiable family-B claim — if the anchor dies on the overlapped stratum and FHMM holds, that is the measured case; if FHMM does not hold there, the bet fails cheaply.
7. **Grouping:** per-device results reported; class-level grouping (simple vs complex) reported; **no per-class pass bars** (owner decision 2026-09-20).

## 5. Metric surface — three axes, one surface for every arm

Every arm (A0, B1, B0) reports the same surface, computed from the same decode + matching output — no extra runs.

**Axis 1 — classification (episode detection).**

- **Primary:** pooled episode F1 across in-focus test episodes per house (pooled-vs-macro aggregation TO FREEZE). Per-device F1 reported, never gated.
- **K-curve:** F1 vs K per arm with bootstrap CIs; K* = smallest K within X of the K = 20 plateau (X TO FREEZE, candidate 0.05).
- **Margins over the ladder (§6):** B1 vs A0 at K = 3 and K = 20, overall and on the overlapped stratum (margin m TO FREEZE).

**Axis 2 — span localization (matched episodes only, same one-to-one matching).** Episode F1 collapses each event to a binary match at tolerance τ; these say how good the span actually is:

- onset **signed** error (t_pred − t_gt), median + p90, per device — the sign matters: hysteresis + dwell rules make the anchor systematically late at onset;
- offset signed error, median + p90;
- duration ratio (pred/gt), median + spread — separates "dwell prior/merge rule wrong" from "emission level wrong";
- span IoU, mean per device — tolerance-free, no new matching decisions.

**Axis 3 — regression (attribution).**

- per-matched-episode mean-power ratio (decoded level vs GT mean power) — the direct read on μ_d quality vs K (H01);
- span-level per-device normalized MAE (MAE / mean aggregate power over the span), stratified solo vs co-occurring — the regression analog of the F1 strata;
- whole-span per-device energy estimated vs GT — not matched-only, because matched-only ratios hide false-positive energy; plus the books-close residual share and UNKNOWN coverage (H05, already contractual).

**Gating across axes (frozen):** F1 margins stay the primary pass criterion: m = 0.05 F1 over A0 at K = 3 and K = 20, overall and on the overlapped stratum. Axes 2–3 carry the frozen **no-regression gate**: B1 ≤ A0 (equal or better) on onset median error and span-level nMAE, per house. Everything else on axes 2–3 is report-only. The metric list is closed at freeze; adding metrics after the first decode is a protocol break.

**Yield and deliverables.**

- **Yield:** attempts vs valid sessions per class (H01's "3 valid costs more than 3 attempts" prediction).
- **Deliverables:** `metrics.json` per run; report render under `docs/reports/fhmm/` (marimo notebook, make export target, pattern of `export-baseline`); evidence lines appended to H01/H02/H04/H05/H06 (status changes stay owner-gated).

## 6. Device-specific decisions

- **Fridge (duty class, no press semantics; FROZEN):** one fixed passive profile, estimated aggregate-only over pre-split GT duty intervals (parity-clean: GT selects the windows, the aggregate supplies the numbers). The profile is K-independent — fridge joins the decode as the 5th device but is **not** in the K-curve. P3 sensitivity: placement/robustness of the passive estimate.
- **Microwave (houses 1–2), dishwasher (houses 2, 5):** score only where GT exists; house-coverage table in the report.
- **Non-focus devices** (toaster, hair dryer, boiler, lighting, ...): unmodeled in v1 — their load lands in the baseline/UNKNOWN component. Decision gate: if the books-close residual share exceeds a frozen threshold, a pre-registered extension adds fixed nuisance components with pre-split aggregate-estimated levels. TO FREEZE.

## 7. Mechanism check — Phase 0, cheap, must precede any FHMM run

Per house and device: session-derived ON level vs the always-on floor + noise band; pairwise emission sums vs observed joint levels. Output: the **recoverable-overlap map** and a written prediction of which devices and which overlaps FHMM can and cannot separate (the H04 transfer prediction). Frozen before the runs, so the experiment cannot be tuned around its own predictions. If washer/dishwasher ON levels sit at or below floor + noise, H04 is predicted to transfer to FHMM — document that before seeing any score.

## 8. Freeze checklist — owner sign-off before any run

- [x] Primary aggregation: **pooled episode F1 per house** (episodes pooled across scored devices); per-device F1 reported, never gated. X (K* knee) = **0.05 F1** vs the K = 20 plateau. m (margin over anchor) = **0.05 F1** at K = 3 and K = 20, overall + overlapped stratum
- [x] Fridge treatment: fixed passive profile (aggregate-only over pre-split GT duty intervals), in decode, out of the K-curve (§6)
- [x] B0 EM ablation in v1 scope: **yes** (P3) — it is H01's cleanest form
- [x] Port-Hart arm deferred to its own pre-registration
- [x] H06 interference-flag rule: a session is invalid if other in-focus devices' GT episodes cover **> 20%** of its interval (frozen)
- [x] Constants: variance floor σ_d ≥ 5 W; E[dwell] clamped to [30 s, 24 h]; innovation constant c = 4 (ambient-sd units); UNKNOWN marginal threshold θ = 0.5; τ = 12 s native / 120 s at 60 s; residual-share extension gate = 20% of span energy
- [x] Axis 2–3 gates: no-regression = **B1 ≤ A0** (equal or better) on onset median error and nMAE, per house; remaining span/regression metrics report-only
- [x] Seeds (base 20260922), R = 20 draws, K grid {1, 2, 3, 5, 10, 20}; house set 1/2/5 (3/4 out of v1); scoring windows per §2
- [x] **Unit-test gate:** synthetic decode-recovery test passes before any real run (construct an aggregate as the sum of known per-device series + noise; assert episode recovery and honest UNKNOWN on an unmodeled injection) — passed 2026-09-22 (3 devices, F1 = 1.0 all, onsets exact, gate 100% on injection / 0% in quiet margin, mu-hat within 30 W)

## 9. Implementation

- **New code:** `src/experiments/01_fhmm/` — `fhmm_lib.py` (session estimation; exact joint Viterbi; marginals/innovation; UNKNOWN demotion) and `01_fhmm_session_supervised.py` (marimo notebook source; render to `docs/reports/fhmm/`). Reuse `baseline_lib` (`gold_file`, `gt_cycles`, `load_series`, `build_episodes`, `match_onsets`, `prf`, `md_table`) and `thresholds.json`. Axis 2–3 metrics (§5) extend the same matching output: a `span_metrics()` helper on matched pairs plus nMAE / whole-span energy from the existing `step_energy_cumsum_wh` / `window_energy_wh` helpers — no additional decode runs.
- **Deps:** numpy/pandas/matplotlib only — no hmmlearn; the 32-state DP is hand-rolled and exact. Read `.agents/skills/marimo-notebook/SKILL.md` before authoring; headless matplotlib (`MPLCONFIGDIR`, Agg).
- **Runtime:** 32 states × ~1M timesteps per house-span decode → seconds to minutes in numpy; the full sweep (3 houses × 6 K × 20 draws × 2 cadences × 2 arms) is hours, not days.

## 10. Phasing

| Phase | Content | Estimate |
|---|---|---|
| P0 | Freeze checklist signed; mechanism check; synthetic unit test | 0.5–1 d |
| P1 | `fhmm_lib` + notebook plumbing; single-house, single-K smoke vs anchor | 1–2 d |
| P2 | K-curve, all houses, native cadence; yield accounting | 0.5–1 d |
| P3 | EM ablation arm; 60 s rung; fridge sensitivity; placement knob | 1 d |
| P4 | Report render, `metrics.json`, registry evidence lines | 0.5 d |

Total: about 4–5 focused days of implementation + runs.

## 11. Risks and mitigations

- **Session contamination (H12):** flag gate + yield reporting + placement-policy sensitivity (P3).
- **Thin program-device pools (20/house):** wide CIs at high K; K = 20 ≡ K = all; stated in every report.
- **B0 label switching:** multiple EM restarts + name-matching by best emission match to profile stats; the naming step uses GT knowledge and is labeled analysis-only, not a runtime capability; separation-only purity reported alongside.
- **Sum collisions** (fhmm-notes §4): predicted by the mechanism check; never re-interpreted post hoc.
- **60 s bucketing blurs simultaneous onsets (H03):** strata split kept per cadence.

## 12. Out of scope for v1

Multi-state phase models; aux channels (H08); neural/transfer arms (H09 cross-dataset); houses 3/4; cross-house profile transfer; port-Hart matcher (own pre-registration if approved).

---

## Appendix A — button-press mark pools (counted this session)

| device | class | house_1 | house_2 | house_5 | source |
|---|---|---|---|---|---|
| kettle | burst | 6,897 | 757 | 186 | rule_cycles |
| microwave | burst | 5,047 | 375 | — | rule_cycles |
| washing_machine | program | 20 | 20 | 20 | manual_cycles |
| dishwasher | program | — | 20 | 20 | manual_cycles |
| fridge | duty | 0 | 0 | 0 | no press semantics |

Other curated marks exist (toaster 20 per house; house-specific: hair_dryer, hoover, straighteners in house_1; rice_cooker, running_machine in house_2; electric_hob, nespresso_pixie, oven, treadmill in house_5) — all unmodeled in v1 (§6).

## History

- 2026-09-22 — drafted from `docs/research/fhmm-notes.md` and the staged-data inventory; no runs performed; nothing frozen.
- 2026-09-22 — metric surface widened from classification-only to three axes (classification / span localization / regression) after the owner flagged that the anchor's surface measured matches only; one no-regression gate added, the rest report-only.
- 2026-09-22 — **FROZEN**: owner approved the run with the recommended defaults; §8 items checked with values; evaluation-GT source (submeter-derived episodes, evaluation-only) and per-house scoring windows fixed after inspecting the post-split mark coverage. Runs may start.
- 2026-09-22 — protocol break (logged, pre-run): the §3 innovation gate scale is the decoded joint state's own emission sd, floored at the ambient σ_off — `|resid| > c · max(σ_off, sd_state)`, c = 4 unchanged. The frozen `c · σ_off` form self-gates legitimate ON steps of any device whose within-session sd exceeds 4·σ_off (true for every enrolled high-draw device on real data; caught by the synthetic S1 unit test). Quiet-region sensitivity (the UNKNOWN mechanism) is unchanged: for all-OFF states sd_state reduces to σ_off.
- 2026-09-22 — protocol break (logged, pre-run, before any scored run): joint emission variance formula corrected to `var_j = σ_off² + Σ_ON (sd_d² − σ_off²)` — the ambient floor is one shared noise source counted once, ON members add their session-sd excess. The drafted `D·σ_off²` form made the all-OFF state width √D·σ_off (292 W vs the true 130 W on house_5) and turned the quiet-region gate into `c·√D·σ_off`, contradicting the gate-break entry above (quiet must reduce exactly to `c·σ_off`). The corrected form is exact for all-OFF, single-ON and pairwise states under independence; synthetic unit test re-passed after the change.
- 2026-09-22 — clarification (logged, pre-scoring): the rung (60 s) decode uses the same frozen background estimator (p10 floor, 1.4826·MAD) applied to the bucket-mean series itself, not the native-cadence values carried over; measured effect is small (house_2 93.4 → 95.6 W) because the ambient structure is slow. Device session-sd excess over ambient is preserved across the rescale (sd_rung = sqrt(sd² − σ_off,native² + σ_off,rung²)); levels and dwell priors are unchanged.
- 2026-09-23 — implemented and executed end to end: `src/experiments/01_fhmm/` (`fhmm_lib.py` shared library with a development-time synthetic unit test whose tracked reproduction is notebook section 9; `00_mechanism_check.py`; frozen runner `02_run_kcurve.py`; analysis notebook `01_fhmm_session_supervised.py` rendered by `make export-fhmm` to `docs/reports/fhmm/01_fhmm_session_supervised.ipynb`). All frozen values used as frozen; both logged protocol breaks applied. Runs: houses 1/2/5, K ∈ {1, 2, 3, 5, 10, 20} × 20 seeded draws per arm, native + 60 s rung, EM ablation. Headline (native pooled F1, B1 vs anchor): house_1 0.345 vs 0.167, house_2 0.458 vs 0.198, house_5 0.039 vs 0.000; EM ablation 0.143/0.084/0.000; rung 60 s B1 collapses to 0.098/0.057/0.020 while the anchor transfers unchanged (0.165/0.205/0.000). Reading: the K-curve is nearly flat from K=1 (bursty devices pin their level with one clean session); the rung hostility is forward-backward spread across composite states plus bucketing that erases short bursts (kettle native 0.77-0.85 -> 0.12-0.14) while smoothing helps program devices (washing_machine native 0.06-0.07 -> 0.21 at 60 s); house_5 collapses honestly at floor 428 W - the anchor saturates at 0.0 and session levels sit inside the ambient band; per-device span IoU stays high where claims survive (0.94-0.98 med). Metrics: `docs/reports/fhmm/metrics_kcurve_house_{1,2,5}.json`.

