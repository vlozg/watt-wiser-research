# Backbone capacity review: is the M1 seq2seq undertrained?

**Date:** 2026-09-29
**Subject:** the cross-home seq2seq behind the M1 baseline in `README.md`, i.e. the
`S2S` configuration in `transfer_lib.py` (identical to `05_method_compare`'s),
trained by `05_method_compare/01_run_compare.py train` on 2026-09-28.
**Sources:** `data/results/method_compare/run.log` (training curves, stage timings)
and `data/results/method_compare/metrics.csv` (scores).

## Verdict

Yes, it is undertrained, but the larger limit is capacity: the net cannot see a
whole washing-machine or dishwasher cycle. The M1 numbers (0.313 dev / 0.280 unseen,
mean cycle F1 over pairs) are a floor for this family, not its ceiling. Even so, the
net already wins the kettle and ties the fridge on unseen homes, with no button
presses at all.

## Evidence

### 1. Training stopped while the loss was still falling

Six epochs, fixed; no validation split, no early stopping. SmoothL1 loss per epoch:

| device | windows (homes) | epoch 1 | epoch 4 | epoch 5 | epoch 6 | last-epoch drop |
|---|---|---|---|---|---|---|
| kettle | 36,000 (12) | 0.1034 | 0.0724 | 0.0704 | 0.0690 | 2.0% |
| microwave | 33,000 (11) | 0.0813 | 0.0545 | 0.0541 | 0.0536 | 0.9% |
| fridge | 54,000 (18) | 0.0340 | 0.0200 | 0.0197 | 0.0195 | 1.0% |
| washing machine | 45,000 (15) | 0.1526 | 0.1182 | 0.1146 | 0.1123 | 2.0% |
| dishwasher | 30,000 (10) | 0.2018 | 0.1485 | 0.1470 | 0.1442 | 1.9% |

Each home contributes 1,500 windows centred on the device's ON samples plus 1,500
random ones, and each window is seen once per epoch. That is a small slice of
the labelled pre-split data available, and the 29-house pretraining pool the bench
defines (`ctx['pretrain']`) is not used at all.

### 2. The net is small and short-sighted

- **15,073 parameters** (24 channels; one input conv, five dilated residual blocks,
  a 1x1 head). Common NILM seq2point nets have millions.
- **Receptive field 257 samples = 25.7 min at 6 s** (9 + 4 x (2+4+8+16+32)). The
  input window is 512 samples, but no output sample sees more than 257 of them.
  Washing-machine and dishwasher programs run 1 to 2 h, so the net only ever sees
  fragments of them. Kettle runs (2-4 min) fit inside the field easily.

### 3. Seen homes barely beat unseen homes: high bias, not overfitting

On the 20 development homes the net was trained on their own earlier history, yet
it scores 0.313 there against 0.280 on unseen homes, a gap of 0.033. A net with
spare capacity would fit the homes it trained on much more closely. The per-device
pattern follows the receptive field:

| device | dev (seen) | unseen | reading |
|---|---|---|---|
| kettle | 0.622 | 0.733 | short event, fully visible: best of all methods |
| fridge | 0.233 | 0.299 | ties the rules model on unseen homes |
| washing machine | 0.331 | 0.129 | cycle longer than the field; collapses off-home |
| dishwasher | 0.337 | 0.187 | cycle longer than the field |
| microwave | 0.059 | 0.049 | confused with the kettle; few windows show both |

It is also uneven across homes: its median over unseen pairs is 0.15 against a mean of
0.28, so a few homes carry the mean.

## What to change, in order of expected gain

1. **Receptive field of about 2 h:** more dilation levels (64, 128, 256) or a
   down-sampling U-Net path, with 64-128 channels. This is the fix for the program
   devices and the prerequisite for everything else.
2. **Synthetic mixing:** paste submetered device traces from donor homes onto real
   aggregates. This is the standard NILM augmentation; it yields unlimited labelled
   windows and teaches overlap directly.
3. **Use all the data:** every ON window, hard negatives (look-alike devices running,
   e.g. kettle windows for the microwave net), and the 29-house pretraining pool.
4. **Train to convergence**, holding out whole homes for validation, with early
   stopping; report the leave-home-out curve (this is M2's transfer matrix).
5. **Adapt on the K=5 marks** (M3), designed around segment 0's fine-tuning failure
   modes listed in `README.md` (overfitting at 40 epochs, sigmoid saturation, dead
   heads).

## Compute: is a single L4 enough?

Yes, for everything in this experiment.

| workload | measured here (shared 8-core CPU) | on one L4 |
|---|---|---|
| seq2seq training, one epoch, 36k x 512 windows | about 40 s (4 threads, box shared with another job) | about 1-2 s |
| full `train` stage, 5 devices x 6 epochs | 1,764 s | minutes, even for a net 100x larger with 2 h context |
| seq2seq inference, 90 days of one home | under 1 s | negligible |
| `predict` stage, 27 homes x 3 seeds | 1,075 s, dominated by FHMM decoding | unchanged unless FHMM is ported |

- **Memory:** 24 GB holds a device's whole training set on the GPU, even at a million
  augmented windows (about 2 GB at 512 samples, float32), so batches can be sliced
  from device memory without a data loader. bf16 mixed precision roughly halves the
  time again.
- **What the GPU does not speed up:** FHMM decoding is a Python loop over timesteps
  (`01_fhmm/fhmm_lib.decode_batch`); since FHMM ranks last on every metric, drop it
  from the loop rather than port it. The rules model is CPU-only but about 3 s per
  home. Parquet loading and resampling are CPU work, cached after the first run.
- **What it unlocks:** leave-home-out cross-validation (5 folds x 5 devices) and the
  augmentation and adapt-on-marks experiments become minutes per iteration instead
  of hours.
