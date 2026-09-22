# FHMM session-supervised experiment plan (Experiment 2 — family B)

**Status:** Drafted 2026-09-22 (AI work; not pre-registered). Every gate, margin, and constant is marked **TO FREEZE** — nothing here runs before the freeze checklist (§8) is signed off, per the registry discipline (criteria frozen before runs, never tuned on test).
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
- **Parity rule (H02 step 2, binding):** every session reads the **aggregate over the GT interval only** — never the device submeter. GT selects the windows (that is what a press is); the aggregate supplies the numbers. `device_profile.csv` stats are submeter-derived and are used for inventory and the mechanism check only, never as model parameters.
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
5. **Scoring:** greedy one-to-one episode matching (reuse `baseline_lib.match_onsets` / `prf`), onset tolerance scaled to cadence plus dwell-ratio band (frozen); UNKNOWN always reported; residual printed first.
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

**Gating across axes:** F1 margins stay the primary pass criterion. Axes 2–3 carry one frozen **no-regression gate** vs A0 (B1's onset median error and nMAE must not exceed A0's by more than a frozen margin — candidate: no worse than A0 at all, decided at freeze); everything else on axes 2–3 is report-only. The metric list is closed at freeze; adding metrics after the first decode is a protocol break.

**Yield and deliverables.**

- **Yield:** attempts vs valid sessions per class (H01's "3 valid costs more than 3 attempts" prediction).
- **Deliverables:** `metrics.json` per run; report render under `docs/reports/fhmm/` (marimo notebook, make export target, pattern of `export-baseline`); evidence lines appended to H01/H02/H04/H05/H06 (status changes stay owner-gated).

## 6. Device-specific decisions

- **Fridge (duty class, no press semantics):** (i) exclude from the v1 K-curve, include in decode with frozen priors, or (ii) passive-mode arm — "sessions" = GT duty intervals read aggregate-only (parity-clean), K-curve over dwell-plausible window counts. **Recommendation:** (i) in v1, (ii) as a P3 pre-registered sensitivity. TO FREEZE.
- **Microwave (houses 1–2), dishwasher (houses 2, 5):** score only where GT exists; house-coverage table in the report.
- **Non-focus devices** (toaster, hair dryer, boiler, lighting, ...): unmodeled in v1 — their load lands in the baseline/UNKNOWN component. Decision gate: if the books-close residual share exceeds a frozen threshold, a pre-registered extension adds fixed nuisance components with pre-split aggregate-estimated levels. TO FREEZE.

## 7. Mechanism check — Phase 0, cheap, must precede any FHMM run

Per house and device: session-derived ON level vs the always-on floor + noise band; pairwise emission sums vs observed joint levels. Output: the **recoverable-overlap map** and a written prediction of which devices and which overlaps FHMM can and cannot separate (the H04 transfer prediction). Frozen before the runs, so the experiment cannot be tuned around its own predictions. If washer/dishwasher ON levels sit at or below floor + noise, H04 is predicted to transfer to FHMM — document that before seeing any score.

## 8. Freeze checklist — owner sign-off before any run

- [ ] Primary aggregation (pooled vs macro), X (K* knee margin), m (margin over anchor at K = 3 and K = 20, overall + overlapped stratum)
- [ ] Fridge treatment (§6, option i vs ii)
- [ ] B0 EM ablation in v1 scope (recommended: yes — it is H01's cleanest form)
- [ ] Port-Hart arm deferred (recommended)
- [ ] H06 interference-flag rule (algorithm + threshold)
- [ ] Constants: variance floors, dwell-prior floors, innovation constant c, UNKNOWN threshold θ, matching tolerances + dwell band, residual-share extension gate
- [ ] Axis 2–3 gates: no-regression margin vs A0 for onset median error and nMAE; confirm the report-only list for the remaining span/regression metrics
- [ ] Seeds, R, K grid; house set (1/2/5 primary; 3/4 out of v1)
- [ ] **Unit-test gate:** synthetic decode-recovery test passes before any real run (construct an aggregate as the sum of known per-device series + noise; assert episode recovery and honest UNKNOWN on an unmodeled injection)

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
- 2026-09-22 — metric surface widened from classification-only to three axes (classification / span localization / regression) after the owner flagged that the anchor's surface measured matches only; one no-regression gate added, the rest report-only. Nothing frozen yet.
