# Hypotheses registry

One file per hypothesis: `H<nn>_<slug>.md`. Problem framing and vocabulary: `docs/PROBLEM_STATEMENTS.md`.

## Status vocabulary

| Status | Meaning |
|---|---|
| **AI drafted (no human review yet)** | Stated by the agent; no human review yet; verification not yet run — or run only by quarantined (unreviewed) code |
| **proved** | Verification executed and its evidence reviewed and approved by the project owner |
| **rejected** | Falsified by verification the owner reviewed |

Rules:

1. A status change requires evidence the **owner has reviewed**. Numbers from quarantined artifacts (`deprecated/baseline_runs/`, `deprecated/analysis/`) never promote a hypothesis past *AI drafted*; they live in each file's "Evidence so far" as tagged claims.
2. Pass/fail criteria — margins over the baseline ladder (§6 of the problem statement), never pre-declared per-class bars [owner decision 2026-09-20] — are written into the hypothesis file **before** the verification run and are never tuned on test data.
3. Evidence tags match `docs/PROBLEM_STATEMENTS.md` §0: **[reviewed]**, **[client]**, **[quarantined]**, **[none]**.

## Symbols

One-line glosses; the full story of each symbol lives in its home file.

| Symbol | Plain meaning | Home |
|---|---|---|
| **K** | How many calibration sessions a device gets | H01 |
| **K\*** | The session count where quality stops improving — the "enough sessions" point H01 hunts for | H01 |
| **ΔPower** | The power jump at switch-on/switch-off: the device's draw minus the household level just before it | H02 |
| **ε** | How far a human's button press lands from the device's true start/stop, in seconds | H10 |
| **W** | The step-snapping search window: how far from the press the detector may look for the real power jump to snap the boundary onto | H10 |
| **B** | The contamination exclusion half-width: how close another device's event may sit to a calibration boundary before it counts as harmful | H12 |
| **τ** | Matching tolerance: how many seconds early or late an onset/offset may land and still count as detected | `docs/PROBLEM_STATEMENTS.md` §7.1 |
| **P / R / F1** | Precision / recall / F1, with layman definitions and formulas | `docs/PROBLEM_STATEMENTS.md` §7.2 |

## Index

| ID | Hypothesis (one line) | Status | Evidence today |
|---|---|---|---|
| [H01](H01_calibration_sufficiency.md) | A small number of guided sessions (guidance: 3 valid) yields a usable profile — the session-count learning curve | AI drafted | [quarantined] flat-from-1 claimed, with cleaner calibration than reality |
| [H02](H02_bursty_load_detectability.md) | Large bursty enrolled devices (kettle-class) are detectable from the aggregate alone at deployment-parity | AI drafted | [quarantined] kettle F1 0.62 at 6 s claimed |
| [H03](H03_cadence_degradation.md) | The 1-minute-class default cadence materially degrades detection, worst for small loads | AI drafted | [quarantined] real-mains degradation claimed |
| [H04](H04_weak_class_unreachable.md) | Dishwasher/washing-machine-class loads are unreachable by threshold+duration rules on this hardware | AI drafted | [quarantined] 14-variant sweep, no material gain |
| [H05](H05_energy_books_close.md) | Attribution + explicit always-on/UNKNOWN closes the energy books per home | AI drafted | [quarantined] residual claims; [reviewed] dataset-side coverage facts |
| [H06](H06_interference_flagging.md) | Interference-flagged calibration sessions still leave enough valid ones to build profiles | AI drafted | [none] — the client doc's own untested assumption |
| [H07](H07_nameplate_sanity.md) | How much do power-label values contribute to prediction? Ablation ladder: measured-only → sanity check → tie-break → low-K seed → hard constraint | AI drafted | [reviewed] background only (dataset-label lies); ladder untested |
| [H08](H08_aux_channel_discrimination.md) | Auxiliary channels (ΔCurrent, power factor) separate same-wattage devices better than watts alone | AI drafted (parked until live Shelly data) | [none] — public data lacks the channels |
| [H09](H09_cross_house_transfer.md) | Signatures transfer poorly across homes; per-home calibration is necessary | AI drafted | [quarantined] mixed: kettle partially transfers across 5 houses |
| [H10](H10_press_boundary_error.md) | Human press-boundary error is cheap up to the snap window; beyond it cost scales like error/dwell | AI drafted | [none] — raised in owner review 2026-09-20 |
| [H11](H11_profile_pattern_drift.md) | Cross-session pattern templates improve detection; sustained drift from the profile flags device degradation | AI drafted | [none] — raised in owner review 2026-09-20 |
| [H12](H12_calibration_contamination.md) | FAQ Q2 made measurable: real calibration-window contamination (raw vs boundary-harmful) across all six datasets | AI drafted | [reviewed] simultaneity hint only — analysis not yet run |
| [H13](H13_user_mark_curation.md) | User-mark annotation: marks identify the device (measured 0.79); disaggregation from marks not demonstrated — and the mark corpus itself does not exist yet (20-mark WM seed only); annotating public datasets is the real data-collection task | AI drafted | [none — instrument exists, not owner-reviewed] GT-cycle EDA |

## The shared instrument

One experiment settles H01, H02, H03, H04 and H06 at once: the **button-press calibration simulation** — ground-truth episode intervals stand in for user start/stop presses; profiles are derived *only* from the aggregate over those intervals (local baseline, ΔPower, interference flag), exactly as the product will; scoring is strictly held-out, episode-level. Its spec lives in H02 "How to verify"; every hypothesis file that uses it links there.

A second instrument covers H13: the **GT-cycle EDA** (render `docs/reports/gt_cycle/`, source `src/pipelines/04_eda_annot_gt_cycle/`) — cycle-level marks curated on review sheets into `data/gold_annot/`, mark-derived profiles scored against submeter cycle GT, plus a recall-ceiling diagnostic. It validated device identification from marks; disaggregation is not demonstrated, and the mark corpus is the missing data (H13).

## Housekeeping

- Rename a file only by editing its H-number link here and in `docs/PROBLEM_STATEMENTS.md` pointers.
- A hypothesis may be retired (merged/descoped) — record the decision in History, never by silent deletion.
