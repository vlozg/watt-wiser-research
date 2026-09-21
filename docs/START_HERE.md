# Start here — catch-up map

**This map:** the shortest path through the work that followed, and what it concluded.

## The one-paragraph version

Phase 1 reviewed the brief, the problem, the hardware, and the delivered repo, then
tested the core approach on real public data. Result in one line: a narrow version of
the product is feasible (a few large appliances per home, calibrated per house), while
whole-home disaggregation on the Shelly EM Gen3 is not — the constraint is the meter's
sampling, not the algorithm. The next decision is a go/no-go that splits in two halves:
capture real data from the device, and run the approach on public data at full rate.

## Where to read, in order

| # | Doc | What it answers |
|---|-----|-----------------|
| 0 | `docs/knowledge/ELI5_NILM.md`, then `docs/knowledge/ELI5_COMMON_NILM_FEATURES.md` | New to NILM? Electricity basics (V, I, W, kWh, AC, power factor), then the features NILM methods compute. Skip if you know the basics. |
| 1 | `docs/PROBLEM_STATEMENTS.md` | What problem are we actually solving — inputs, outputs, the calibration protocol, the evaluation contract. Every claim trust-tagged. |
| 2 | `docs/research/research-brief.md` | What the field knows, what the hardware can do (section 4), and why the best-funded consumer product in this space quit. |
| 3 | `docs/product/feasibility-verdicts.md` | Which versions of the product are feasible, which are not, and why. |
| 4 | `docs/reports/dataset_eda/00_overview.md` | The six public datasets: scale, cadence, label reality, and each dataset's documented trap — then focus on the real UK-DALE set (01) first. |
| 5 | `docs/reports/gt_cycle/` | What hand-annotated device cycles reveal: devices are identifiable, but multi-phase appliances (washing machine) break the single-profile representation — a limit beyond hardware. Start with `01_ukdale_gt_cycle_eda.ipynb`. |
| 6 | `docs/hypotheses/README.md` | The hypothesis registry (H01–H13): statuses, and how each would be verified next. |

## Go deeper, as needed

- Experiment specs and renders: `docs/experiments/baseline-ukdale-plan.md`,
  `docs/reports/baseline/`
- Curated, hand-annotated calibration episodes: `data/gold_annot/` (tracked)

## State of play

- **Hardware.** The Shelly EM Gen3 spec documents 1-minute storage; whether around
  1 live value/second is streamable must be measured on the actual device — the two
  available sources disagree.
- **Public data.** Six datasets staged at raw fidelity — 46 households, 2.2B+ rows —
  cover experimentation scale; hand-annotated episodes are the calibration input.
- **Quick experiment.** Kettle/fridge-class detection works with minutes of
  calibration. Dishwasher/washing-machine class does not separate from baseline noise
  at this sampling rate — a hardware/representation limit, not a tuning problem.
- **Field context.** Cross-house generalisation remains the field's unsolved problem,
  and the best-funded consumer disaggregation product exited the market.
- **Next.** The two go/no-go halves above, then a scope decision with the answer in hand.

Repo layout, conventions, and reproduction: `README.md`.
