# 06 - transfer learning for cross-home NILM

**Status:** segment 3 (owner-directed pivot: transfer learning / DL), pre-registered
in `.auto/ideas.md` as **B6-pre**. Charter: `.auto/prompt.md` sections 3-6.

## Purpose

The rule stack in `04_autoresearch/model.py` plateaued: runs 103-118 were 16
consecutive discards that measured out the whole bound space. The residue with
bar-clearing magnitude is a **representation failure** - unlabelled or rejected
program cycles leak heater blocks into the kettle (`house_12`: 712 predicted
kettle episodes against 127 GT; worth roughly +0.015 on the pool primary) - and it
is unreachable by construction for any band or span rule:

* `ev_in_prog` derives only from emitted program spans, and a home with no marks
  for a device has **no profile at all** (`house_12` has no dishwasher channel in
  `cmap`, so no `dw30` exists);
* no amplitude or duration band separates a duty-cycling program heater from a
  kettle boil (established in memos m35/m36).

A learned representation is the natural instrument for exactly this discrimination.
This experiment builds it, under the product's deployment parity: aggregate only,
K=5 marks per device, no per-device meter ever.

## Composition

Standalone: experiments never import across `src/experiments/` directories
(AGENTS.md), so `transfer_lib.py` carries its own copies of what it needs.

| piece | comes from |
|---|---|
| frozen protocol, pool, homes, calibration, scoring | `.auto/bench_v4.py`, `pool_v4.py`, imported directly |
| home loading + pre/eval split plumbing | `transfer_lib.py` (a copy of `05_method_compare`'s loader) |
| the dilated-CNN seq2seq net + windowing + training loop | `transfer_lib.py`, same architecture as 05's so checkpoints load in both |
| scored entry point in prod parity | `04_autoresearch/model.py` (bench_v4 hard-codes it) |

`05_method_compare` remains the comparison + explorer/visualization harness. This
directory owns the new *method*: pretraining, adapt-on-marks, transfer evaluation.
Span caches and results land in `data/results/transfer_dl/`.

## Data discipline (see prompt.md section 5)

* Pretraining uses the **20 development homes' pre-split spans only**.
* The **7 holdout houses are a milestone-only readout** - never trained on, never
  used for hyperparameter selection, never run per iteration.
* A scored home's **eval-span submeter channels are never an input**.
* No method may require more than K=5 marks plus the pre-span aggregate.

## Milestones

1. **M1 - DL baseline (zero-shot).** Evaluate the pretrained backbone on the pool
   (dev vs unseen) against the rules baseline, measured here. No claims before this
   number. `05_method_compare/01_run_compare.py` can still emit side-by-side
   `rules | rules_gt_thr | fhmm | seq2seq` preds for the explorer/visualization, but
   the measured M1 readout belongs to this directory.
2. **M2 - transfer matrix.** Leave-one-home-out on the dev pool: H09's diagonal
   (per-home) vs off-diagonal (transfer) cells.
3. **M3 - adapt-on-marks.** Condition or fine-tune the pretrained backbone using
   only the target home's K=5 marks; score against the frozen pool primary.
4. **M4 - land it.** Make `04_autoresearch/model.py` an adapter over the winner +
   committed weights and run the full bench (that run is the keep).

**Kill criterion.** If by M3 the adapted backbone cannot beat the rule incumbent on
the pool primary with p10 not falling - judged over at least 3 pre-registered runs,
not one - abandon the backbone and report the transfer matrix as the result. H09 is
deliberately two-sided: a measured weak transfer is a result, not a failure.

## M1 baseline (measured 2026-09-28, current architecture)

From `05_method_compare`'s comparison (`data/results/method_compare/{run.log,metrics.csv}`),
mean episode F1 over device-home pairs, all methods on identical homes/pairs:

| method | dev (66 pairs) | unseen (26 pairs) |
|---|---|---|
| rules_gt_thr | 0.365 | 0.325 |
| rules (incumbent family) | 0.354 | 0.306 |
| **seq2seq** | **0.313** | **0.280** |
| fhmm | 0.222 | 0.159 |

Per device, seq2seq vs rules (dev / unseen):

| device | seq2seq | rules | verdict |
|---|---|---|---|
| kettle | 0.622 / 0.733 | 0.563 / 0.582 | **DL wins, +0.059 / +0.151** |
| washing_machine | 0.331 / 0.129 | 0.244 / 0.140 | DL wins on dev, ties on unseen |
| dishwasher | 0.337 / 0.187 | 0.388 / 0.351 | rules win |
| fridge | 0.233 / 0.299 | 0.347 / 0.304 | rules win on dev, parity on unseen |
| microwave | 0.059 / 0.049 | 0.257 / 0.153 | **rules win by a lot** |

**Reading.** DL loses overall but its error structure is *complementary*, not inferior:
recall 0.532 dev / 0.454 unseen against rules' 0.347 / 0.271, with the reverse ordering
in precision. It wins on exactly the devices where rule gating is structurally weakest
(the kettle, whose mark-free program-cycle leak runs 103-118 proved unreachable - the
H09 prediction) and on the washing machine, and it loses worst on the microwave, whose
failure is an amplitude problem (sub-floor houses at 43-47 W) matching segment 0's
"microwave ON head is blind" finding. Also: dev-to-unseen degradation is *smaller* for
seq2seq (-0.033) than for rules (-0.048), so its transfer is if anything more stable.

This makes the promising target a mechanism-grounded per-device hybrid (DL for
kettle/wm, rules for mw/fridge/dw) rather than a wholesale replacement: the per-device
best-of gives ~0.397 dev / ~0.353 unseen, i.e. +0.03 over the rule family.

Backbone provenance: `data/results/method_compare/seq2seq/<device>.pt`, 24 ch +
BatchNorm, 44 state-dict keys, produced by `05_method_compare/01_run_compare.py train`.
`transfer_lib.load_net` prefers 06's own `pretrain/` and falls back to those files
(read as data; same architecture). The v0 32-ch Softplus checkpoints (which
collapsed to a constant output) are archived under `data/results/transfer_dl/archive/`.

**Capacity review:** `backbone_capacity_review.md` - this backbone is undertrained
(loss still falling at epoch 6) and short-sighted (15k parameters, a 25.7 min
receptive field against 1-2 h program cycles; seen-home F1 only 0.033 above unseen),
so M1 is a floor for the family. It lists the fixes in order and sizes the compute:
one L4 GPU is enough for M2-M3.

## Prior art from segment 0 (already paid for - recycle, do not re-walk)

The first DL attempt (`.auto/log.jsonl`, segment 0, runs 1-7) used a *multi-output*
CNN under a different protocol (`min_device_f1` on house_1 alone), but its
mechanism-level findings transfer:

* `clamp(min=0)` on the power head is a dead-ReLU trap: a channel whose
  pre-activation goes negative gets zero gradient and dies permanently. **Softplus**
  revived all five heads (microwave, fridge and washing machine were outputting
  exactly 0 W).
* Full-span MSE starves small-amplitude devices (fridge ON is ~4% of the normalized
  range). Mask the amplitude loss to device-ON positions and let a separate ON head
  carry detection.
* Weight-space fine-tuning on the K=5 calib sessions **overfits**: 11x retention
  damage at 40 epochs, and sigmoid saturation when the pretrain `pos_weight` (up to
  50) was reused on ON-heavy calib positions. An adapter must recompute class weights
  on the calib positions and guard saturation explicitly.
* Multiplicative output-scale calibration is inert for a head that outputs 0 W - it
  rescales live-but-miscalibrated heads only.
* A guard that trips on the calib OFF-sigmoid distribution caught saturation the loss
  curve never showed.

Segment 0's ceiling under that protocol was ~0.083 `min_device_f1`; the rule stack
scores 0.366174 `mean_device_f1` over 66 pairs, so the target here is the latter.

## Running

```bash
# pretrain the shared backbone (one net per device, dev homes' pre-split spans)
uv run python3 src/experiments/06_transfer_dl/01_pretrain.py            # all devices
uv run python3 src/experiments/06_transfer_dl/01_pretrain.py --devices kettle --homes eco/house_01,refit/house_1 --epochs 1

# M1 baseline readout (comparison harness + explorer/visualization)
uv run python3 src/experiments/05_method_compare/01_run_compare.py train predict summary
```

Weights land in `data/results/transfer_dl/pretrain/<device>.pt`.
