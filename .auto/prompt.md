> **STATUS: TERMINAL (closed by the owner 2026-09-28).** This loop is closed and
> must not be resumed as a rule-tuning loop. The rule bound space is exhausted:
> 106 runs, 29 keeps, last keep `b4298ca` at primary 0.366174 against a bar of
> 0.376174. The terminal record is `.auto/dossier.md`; the full hypothesis
> record is `.auto/ideas.md`. The open direction is the per-device hybrid
> (rules for microwave/fridge/dishwasher, a cross-home net for kettle and
> washing machine) measured in `data/results/method_compare/` - a new
> experiment, not a continuation. Sections 0-9 below remain the frozen charter
> for any future segment.

# Autoresearch task: WattWiser NILM - episode detection + attribution (transfer-learning segment)

## 0. What this loop is for
Improve the product's ability to answer, from the aggregate alone, *which enrolled
device is running, when, and how much energy it used - or UNKNOWN*. Grounding
authority: `docs/PROBLEM_STATEMENTS.md` (it wins over every other doc). Deployment
parity is absolute: the method never sees a per-device meter, at any time, end to
end (that doc's sections 3 and 7). The only supervision is K guided calibration
sessions per home, plus whatever the aggregate itself offers.

## 1. Primary metric (frozen, measured by .auto/measure.sh)
METRIC mean_device_f1 - median over the frozen 5 seeds of the mean episode F1 over
the frozen 66 (house, device) pairs; every pool house is re-calibrated with its own
K=5 marks, its own pre-split history and a fresh build_and_train - the deployment
path. Higher is better. Tracked on every run: mean_device_f1_p10,
device_balanced_mean, house_1_v4_mean, the five per-device medians, transfer_mean_f1.

## 2. Frozen - never edit, never tune
`.auto/measure.sh`, `.auto/bench.py`, `bench_v2.py`, `bench_v3.py`,
`bench_v4.py`, `checks.sh`, `pool_v4.py`, `pool_v4.json`; the evaluation
contract (`wattwiser.experiments.evaluation`); the threshold / tau / duration-band
/ cadence constants; pool eligibility, eval spans and seeds. If a protocol constant
looks wrong, STOP and say why instead of silently editing it.

## 3. What may change now (segment-3 rewrite licence)
This loop is no longer restricted to small threshold tweaks. Explicitly authorised:
1. **Architecture rewrites.** Replace the rule-based detector with a learned model
   or a hybrid; change representations; add learned components; delete rule families.
2. **New tracked artifacts.** Training scripts, library modules and small committed
   checkpoints are legitimate - e.g. `src/experiments/06_transfer_dl/`, weights under
   `data/results/transfer_dl/`. The scored entry point stays
   `src/experiments/04_autoresearch/model.py` (bench_v4 hard-codes it), so a new
   architecture lands there as a thin adapter over the new module + weights.
3. **Multi-run bets.** Pre-register hypothesis, milestones and kill criterion in
   `.auto/ideas.md` before starting. One bad first run is not a refutation; judge a
   bet over its milestone, not over one measurement.
4. **Problem reframing inside the product boundary** - different output
   parameterisation, different UNKNOWN semantics, a retrieval / transfer
   formulation instead of per-home rules.

## 4. Landing rule (how a big rewrite survives the auto-revert)
The plugin auto-commits on `keep` and auto-reverts on `discard`, so an
intermediate behaviour-neutral rewrite cannot survive a run on its own. Therefore:
- Develop a rewritten architecture in its own module (`06_transfer_dl/`), where
  iterations do not touch the scored path.
- Land it by making `04_autoresearch/model.py` an adapter and running the bench:
  that run is the `keep` that persists the work.
- Park intermediate diffs as `.auto/runs/<n>_<slug>.diff` so a revert cannot lose them.
- A pure refactor that cannot move the primary metric ships as a diff artifact,
  never as a run.

## 5. Data discipline (cheating = wasted run)
1. Never use a scored home's eval-span submeter channels as model input, and no
   model choice may depend on the eval span.
2. Training on other homes' labels is legitimate: the 20 dev homes' **pre-split**
   spans may be used for pretraining. The 7 holdout houses are a **milestone-only
   readout** - never train on them, never select hyperparameters on them, and never
   run `--holdout` per iteration.
3. The calibration interface is K=5 marks per device plus the pre-span aggregate. A
   method may not require extra labels: solve it with better methods, not more labels.
4. Report honestly: p10 and per-device medians beside every primary. A change that
   helps the mean and hurts the tail is not a win.
5. Every run is logged - keep / discard / crash - with its evidence.

## 6. Keep rule, and its multi-run exception
Default: keep iff primary >= last kept primary + 0.01 AND p10 does not fall AND no
device median falls more than 0.03.
Exception, for a pre-registered big bet: an *intermediate* milestone may declare its
own bar in advance - e.g. "primary no worse than -0.005, p10 not down, and the
target device or group measurably improved" - and that declared bar then makes the
run a legitimate keep. The bar is declared in `.auto/ideas.md` BEFORE the run, never
chosen after seeing the number.

## 7. Standing product bars (not the loop metric)
house_1 v3 median >= 0.70 and transfer mean >= 0.50 are product bars. K=5 marks is a
product constraint, not a tunable.

## 8. Iteration mechanics
- Benchmark: `bash .auto/measure.sh` (full pool, ~95-165 s). Screens:
  `--seeds N` single seed (~19 s) or `--houses` (~4 s); compare a screen against
  THAT seed's own base.
- Audit gate vacuity / behaviour BEFORE the pool; `ast.parse` model.py before any
  pool run.
- The discard auto-revert is not guaranteed: verify `git status --porcelain src/`
  and restore with `git checkout -- src/experiments/04_autoresearch/model.py` if dirty.
- Backlog: `.auto/ideas.md`; diagnostics in the asi field (hypothesis /
  rollback_reason / next_action_hint).

## 9. Where the campaign stands (segment 2, kept honest)
Incumbent `b4298ca`: primary 0.366174, p10 0.345739. Runs 103-118 were 16 consecutive
discards that measured out the rule-bound space: every relaxation of a gate protects
precision (dw merge / span / mean floors), some bounds are provably vacuous (the wm
heat-share ceiling), and the residue with bar-clearing magnitude - unlabelled or
rejected program cycles leaking heater blocks into the kettle (worth ~+0.015) - is
unreachable by construction: `ev_in_prog` derives only from emitted program spans, a
home with no marks for that device has no profile at all, and no amp or duration band
can separate a duty-cycling heater from a boil. That is a representation failure,
which is why segment 3 is a learned / transfer formulation (experiment 06, H09).
