# NILM transfer learning — SOTA review and direction

**Scope:** the transfer / adaptation side of NILM, reviewed against the WattWiser constraint set
(Shelly EM Gen3, single aggregate channel, **approx. 1 s live capture** via an always-on collector
with the 60 s onboard log as the fallback, 30 VA floor, per-home calibration sessions, product
direction = transferable across households).
**Cadence note (2026-09-26, owner):** the deployment target is **approx. 1 s**, not 60 s — the
onboard-log figure was the *storage* rate, and continuous live polling is what the project is built
on. Per `docs/product/feasibility-verdicts.md` §8 this rate is a **measured hypothesis, not a
datasheet value**: promote it only after the timestamp-gap histogram (that doc's §5 Part A) confirms
it on the actual device. Everything below is now written for the 1 s case, with 60 s treated as the
degraded fallback.
**Date:** 2026-09-26 · **Status:** AI drafted, owner review pending.
**Read alongside:** `docs/research/research-brief.md` (§3.2 generalisation), `docs/hypotheses/H09_cross_house_transfer.md`,
`research-logs/training-approaches.md` (the 2026-06 predecessor note), `docs/PROBLEM_STATEMENTS.md`.
**Raw evidence:** `research-logs/nilm-transfer-sota/` (arXiv + OpenAlex harvests, abstracts, this file's sources).

**Evidence markers used in this doc:** `[abs]` = read at abstract/metadata level;
`[full]` = full text or repository read; `[repo]` = code/artifact inspected.

---

## 0. Bottom line

1. **The reframing.** "Transfer learning for NILM" is the field's name for its oldest open problem
   (generalisation across houses). It is not a new method family to adopt — it is a **mature design
   space with four generations of methods**, a mapped set of trade-offs, and published numbers for
   each. The decision is not *whether* to do transfer learning; it is *which adaptation route* fits a
   1 s single-channel meter and a product that must work in a house it has never seen.

2. **The 2025–2026 SOTA direction is exactly the product direction.** The frontier has moved from
   "fine-tune a model per house" to **"pretrain one backbone on many houses → freeze it → condition
   or lightly adapt it per home."** Two 2026 papers state the paradigm explicitly:
   `RefQuery` (frozen network + a per-appliance embedding, arXiv 2603.04998, 2026-03) `[abs]` and
   `FM4NILM` (one frozen text-prompted model serving twelve appliance-corpus requests across seven
   corpora, arXiv 2609.23146, 2026-09) `[abs]`. This is the architecture to build, not to invent.

3. **The "no labelled data" problem is real but smaller than it looks — and it is not the binding
   constraint.** The scarce labels are *target-home* labels. The literature's answer is
   few-shot adaptation (single-digit exemplars per appliance), active selection (5–15% of a query
   pool), weak supervision, or **no target labels at all** via self-supervised / unsupervised
   domain adaptation on the home's unlabelled aggregate stream. Public corpora supply the *source*
   labels; the project already has 46 houses staged.

4. **At 1 s the binding constraint is no longer cadence — it is signal bandwidth and the analog
   floor, and transfer learning moves neither.** 1 s puts the project at the **native cadence of the
   benchmark corpora** (UK-DALE 1 s, REDD 1 s, ECO 1 s, GREEND 1 s), so the low-frequency branch of
   SOTA — which *is* the whole foundation-model line — is directly available and directly
   comparable to published numbers. What stays closed is the **kHz V-I branch** (a large, strong
   slice of the transfer literature) and the **30 VA floor / sub-1 A accuracy band**. Domain
   adaptation moves cross-domain generalisation by small deltas (e.g. +3% `[abs]`, +0.14 F1
   `[abs]`); it does not add information. Transfer learning fixes *deployment cost and coverage
   extensibility*, not the *information ceiling*. See §3.1.1 for the availability split.

5. **No pretrained NILM foundation-model checkpoint is publicly available yet** — re-verified against the Hugging Face + GitHub registries in `transfer-applicability-audit.md` (2026-09-26). `NILMFormer`
   (KDD 2025) ships code only `[repo]`; `FM4NILM` (2026-09) has no repository `[repo]`. Pretraining
   is therefore on us — but the corpus is already staged, so this is a compute/engineering task, not
   a data-acquisition blocker.

**One-line direction.** Build the **pretrain-once, condition-per-home** pipeline; make the
button-press sessions the *adaptation* signal (exemplars, not training runs); and keep the product
scope at the appliances a 1 s single channel can actually separate, rather than expecting transfer
learning to rescue whole-home disaggregation.

---

## 1. What the question actually is

Four different things are called "transfer" in this literature, and they fail for different reasons:

| Axis | Question | WattWiser relevance |
|---|---|---|
| **Cross-house** | Same appliance, same country, different home | Core product question; H09 |
| **Cross-dataset / cross-country** | UK-DALE → REFIT → REDD / North America | The US-home requirement; different wiring, voltage, appliance stock |
| **Cross-appliance** | Knowledge learned for one appliance type helping another | Whether one backbone can carry many appliance heads |
| **Cross-cadence** | Train on 1 s data, deploy at 6 s / 60 s (onboard-log fallback) | Now a **robustness** requirement, not a forced constraint: deployment is 1 s |

Two distinct gaps get conflated under "we have no labelled data":

- **(a) Target-home labels — the adaptation gap.** How many labelled examples does the target home
  need? The literature's answer is *very few*, and it has several label-free routes.
- **(b) Source diversity — the generalisation gap.** Does a model trained on the available houses
  cover the appliance/usage space of an unseen home? This is fixed by **more pretraining houses and
  conditioning**, not by target labels.

The important asymmetry: **unlabelled target data is not scarce.** It is the meter stream itself.
A large part of the transfer literature exists precisely because the target aggregate is free and
only the target *labels* are expensive, and it exploits the free part. Framing the problem as
"no data" understates the available signal.

This also reframes the project's existing finding. The 2026-06 note
(`research-logs/training-approaches.md`) concluded the calibration-to-detection MVP is
"mechanically active learning plus fine-tuning on household-specific labels", and that every
component already exists. That is still true and this review confirms it. What has changed since
that note is the frontier: **the calibration ritual is no longer the state of the art for
adaptation.** Conditioning a frozen pretrained backbone on a handful of exemplars now does the job
that a per-home fine-tuning campaign was doing in 2023.

---

## 2. The SOTA landscape — four generations

Ordered by mechanism, not strictly by date; later generations do not replace earlier ones, they
absorb them as baselines.

### Generation 1 — fine-tune a per-appliance regressor (2019–2020)

| Work | Mechanism | Target data needed | Reported outcome |
|---|---|---|---|
| *Transfer Learning for NILM*, IEEE TSG 2019, doi:10.1109/tsg.2019.2938068, 328 cites `[abs]` | seq2point; appliance transfer (ATL) and cross-domain transfer (CTL) | a little target data, and only for CTL | Latent features of a **complex** appliance transfer to a **simple** one. Similar domains: no fine-tuning needed. Different domains: **only the fully connected layers** need fine-tuning. Code: `github.com/MingjunZhong/transferNILM` |
| *GANs and Transfer Learning for NILM*, SmartGridComm 2020, doi:10.1109/smartgridcomm47815.2020.9302933, 36 cites `[abs]` | GAN + parameter sharing / shared compact representation | some target data | Quantifies transfer value **as a function of source–target similarity** — useful framing: transfer payoff is predictable from domain distance |

**Reading for us.** The canonical result is more deflationary than it sounds: if domains are
similar, skip fine-tuning; if different, the head is enough. It argues against a heavy per-home
training ritual and *for* a strong shared backbone.

### Generation 2 — representation alignment / unsupervised domain adaptation (2021–2023)

| Work | Mechanism | Target labels | Reported outcome |
|---|---|---|---|
| *Deep Domain Adaptation … Knowledge Transfer Learning Network*, IEEE TSG 2021, doi:10.1109/tsg.2021.3115910, 89 cites `[abs]` | TCN + domain-adaptation loss on representations | **none** (unsupervised alignment) | Learns a domain-invariant representation; targets the "data shortage" scenario |
| *Semi-Supervised Domain Adaptation for Multi-Label Classification on NILM*, Sensors 2022, doi:10.3390/s22155838, 23 cites `[abs]` | domain adaptation for multi-label appliance presence | a little labelled + unlabelled | Frames appliance detection as multi-label to avoid per-appliance models |
| *Taming the Domain Shift in Multi-source Learning*, KDD 2023, doi:10.1145/3580305.3599910, 6 cites `[abs]` | hybrid multi-source domain-adversarial network (HLD-MDAN); new target-domain generalisation bound | **none** | Uses *many* public datasets as sources; outperforms single- and multi-source baselines |
| *A Semi-Supervised Approach for Improving Generalization in NILM*, Sensors 2023, doi:10.3390/s23031444, 20 cites `[abs]` | DANN with labelled + unlabelled data | **none** | **+3%** generalisation on highly uncorrelated data (REDD ↔ UK-DALE) |
| *Transferable Tree-Based Ensemble Model for NILM*, IEEE TSUSC 2022, doi:10.1109/tsusc.2022.3175941, 17 cites `[abs]` | LightGBM + feature-importance transfer | some | Cheap, privacy-preserving cross-domain transfer; a reminder that non-neural transfer is viable at low cadence |
| *Knowledge Distillation for Scalable NILM*, IEEE TII 2023, doi:10.1109/tii.2023.3328436, 25 cites `[abs]` | distillation from a large model + weak supervision | weak labels | **+0.14 F1 over a benchmark 78x more complex** on unseen target domains |
| *Investigating Domain Bias in NILM*, 2024, doi:10.1145/3671127.3699532, 3 cites `[abs]` | diagnostic study | — | Names the failure mode: deployment is hard because models are trained on domain-specific data |

**Reading for us.** This generation is the *label-free* option, and its honest ceiling is a few
points of F1, not a transformation. It is worth one experiment (E3 below) because it consumes the
free unlabelled aggregate stream, but nobody should plan a product on a +3% delta.

### Generation 3 — meta-learned / pretrained backbones for few-shot (2021–2024)

| Work | Mechanism | Target data needed | Reported outcome |
|---|---|---|---|
| *Pre-Trained Models for Non-Intrusive Appliance Load Monitoring*, IEEE TGCN 2021, doi:10.1109/tgcn.2021.3087702, 53 cites `[abs]` | meta-learning + ensemble pretraining of a base model, few-shot fine-tune on an unknown dataset | a handful | Beats traditional DL and plain transfer learning on transferability |
| *Load Recognition With Few-Shot Transfer Learning Based on Meta-Learning and Relational Network*, IEEE TSG 2024, doi:10.1109/tsg.2024.3390441, 19 cites `[abs]` | episodic meta-learning + relational network for appliance recognition | a few examples per class | Generalises across **four transfer scenes**; outperforms most prior NILM transfer methods |
| *A Few-Shot Learning Method for NILM With V–I Trajectory Features*, IEEE Sensors J 2024, 17 cites `[abs]` | few-shot on V–I (high-frequency) features | a few | Strong, but **requires high-frequency signal** — not available on our hardware |
| *An active learning framework for the low-frequency NILM problem*, Applied Energy 2023, doi:10.1016/j.apenergy.2023.121078, 67 cites `[abs]` | active selection of which samples to label, then update | 5–15% of a pool | Optimal accuracy/labelling trade-off at **5–15% labelled**; REFIT |
| *Benchmarking Active Learning for NILM*, arXiv 2411.15805, 2024-11 `[abs]` | uncertainty-aware nets; choose **which houses** to instrument | sensor installs, not labels | Beats random on Pecan Street; matches full-dataset training — **sensor placement is itself a transfer decision** |
| *FedNILM*, arXiv 2106.07751, 2021 `[abs]` | federated learning + pruning + unsupervised transfer for personalisation | none shared | On-device personalisation without centralising user data |
| *Learning Task-Aware Energy Disaggregation: a Federated Approach*, arXiv 2204.06767, 2022 `[abs]` | nested meta-learning inside federated learning | local only | Task-specific models across heterogeneous homes |

**Reading for us.** This is where the button-press protocol belongs. Active learning says **5–15%
of a query pool is enough**; few-shot meta-learning says single-digit examples per class. So the
project's open question is not "do we have enough labels" but "**what is the cheapest query
protocol that reaches the plateau, and how few presses is that**" — which is H01's K*, restated in
exemplars rather than sessions.

### Generation 4 — foundation models, prompt/conditioning, non-stationarity (2025–2026)

| Work | Mechanism | Target data needed | Reported outcome |
|---|---|---|---|
| *NILMFormer*, KDD 2025, arXiv 2506.05880 `[full-abs]` | sequence-to-sequence transformer **aware of non-stationarity**; EDF-Lab released code | target training data | Production-track: code published by **EDF-Lab** (`github.com/adrienpetralia/NILMFormer`, 55 stars, active into 2026) `[repo]`. A utility-scale deployment precedent |
| *Ask for Any Appliance: A Prompt-Programmable Foundation Model for NILM* (FM4NILM), arXiv 2609.23146, 2026-09 `[abs]` | cadence-aware transformer, **masked-reconstruction pretraining on 645k sequences from seven public corpora spanning 1–60 s**, aligned to natural-language appliance requests; Bernoulli-lognormal decoder splits detection from power | natural-language request + optional activation exemplars; **no parameter updates** | One frozen model serves **12 appliance-corpus requests**: 0.556 event F1, 0.625 AUPRC, best active-window MAE (251.8 W) among seven appliance-specific baselines. **+10 activation exemplars raise microwave AUPRC 0.132 → 0.214** with no weight updates |
| *RefQuery: Lightweight and Scalable Transfer Learning Framework for Load Disaggregation*, arXiv 2603.04998, 2026-03 `[abs]` | keeps a pretrained network **fully frozen**; learns only a per-appliance embedding via lightweight backprop | a short target run | Multi-appliance, multi-task, no fixed output set; strong accuracy/efficiency trade-off vs transformer baselines; aimed at real-time/edge |
| *Prompting Large Language Models for Training-Free NILM*, arXiv 2505.06330, 2025-05 `[abs]` | in-context LLM prompting with appliance features + time-series exemplars | a few exemplars in the prompt | Prompt-only LLMs give **only basic NILM capability and lag DL in complex scenarios**, but generalise strongly **across houses and regions by swapping injected appliance features**, with human-readable explanations |
| *Multi-Appliance NILM via Label-Preserving Aggregate Recomposition*, arXiv 2609.18315, 2026-09 `[abs]` | recompose aggregate windows by swapping only the residual background, preserving target labels; add prediction-consistency loss | source data only | Directly attacks the **residual-background shortcut** that makes source-house models fail in unseen houses |
| *Scaled and Inter-token Relation Enhanced Transformer for Sample-restricted NILM*, arXiv 2410.12861, 2024-10 `[abs]` | transformer architecture tuned for **small datasets** (inter-token relation, dynamic temperature) | small | +10–15% F1 over prior SOTA on REDD |
| *Towards a Deeper Understanding of Transformer for Residential NILM*, arXiv 2410.03758, 2024-10 `[abs]` | hyper-parameter study; BERT-style masking ratio | — | Practical recipe for transformer NILM; masking ratio matters |
| *Non-intrusive NILM based on Self-supervised Learning*, arXiv 2210.04176, 2022-10 `[abs]` | self-supervised **pretext task on the target's aggregate only**, then per-appliance fine-tune | **no target appliance labels for pretraining** | The cleanest statement of the label-free route |

**Reading for us.** This generation is the one that matches the product thesis, because it makes
**coverage extensible and per-home cost near-zero**: you condition on a request (text, embedding,
exemplar set) instead of retraining. The two decisive numbers are FM4NILM's zero-shot 0.556 event F1
on held-out households and RefQuery's demonstration that only a tiny per-appliance embedding needs
training. Both are 2026 results, so the field is at the beginning of this curve — the architecture
is proven in prototype, not yet productised by anyone except EDF.

### 2.1 What the field has *not* solved

- **Hard, multi-state appliances at coarse cadence.** Every strong result uses high-frequency
  signal, 1 s data, or clean 1 s+ ground truth. The published transfer gains are on simple/high-power
  loads. No transfer method manufactures separability.
- **Zero-shot with *no* anchors for a new appliance *category*.** FM4NILM's category-held-out result
  is weak-until-exemplars (microwave AUPRC 0.132 → 0.214). Ten exemplars is the price of entry.
- **Released pretrained checkpoints.** None found (see §3.6).
- **Cross-country, low-cadence foundation models.** FM4NILM spans cadences but is trained on
  standard corpora; the very-low-rate regime is studied separately (see §3.1). This intersection is
  the genuine niche.

---

## 3. Cross-cutting evidence that binds the direction to this hardware

### 3.1 Cadence — 1 s is the benchmark cadence, so this constraint largely dissolves

At **approx. 1 s**, the project sits at the *native* cadence of the standard corpora: UK-DALE
(1 s and 6 s power), REDD (1 s / 3 s), ECO (1 s), GREEND (1 s) — four of the six staged datasets —
with REFIT at 8 s and AMPds2 at 1 min. That is the single most useful consequence of the rate
clarification: **the transfer results in the literature are reported at our rate**, so they can be
reproduced as-is rather than treated as an upper bound on a finer signal.

For completeness, the low-rate literature is now only relevant as the *degraded fallback* case
(onboard-log-only operation): *NILM with very low-frequency data from smart meters in Switzerland*,
Energy & Buildings 2025, doi:10.1016/j.enbuild.2025.116002 `[abs]` (15-minute meters); *…very
low-rate smart meter data*, Applied Energy 2020, doi:10.1016/j.apenergy.2020.114949 `[abs]`.
FM4NILM pretrains across **1–60 s** corpora in one model `[abs]`, so cadence heterogeneity is a
pretraining design choice; at 1 s we sit inside its span rather than at its edge.

**Implication.** Build the corpus at 1 s (with 6 s / 8 s / 60 s augmentations for robustness).
Cadence-matched pretraining is cheap and directly testable (E1).

### 3.1.1 What the 1 s rate unlocks, and what it cannot

1 s is a **temporal** improvement, not a **spectral** one. The Shelly's ADE7953 metering IC reports
*computed* values (RMS, active/reactive/apparent power, power factor), not AC waveforms — so faster
polling gives high-rate **power**, never V-I trajectories, harmonics, or sub-cycle transients
(`docs/product/feasibility-verdicts.md` §10, caveat 1). The SOTA split follows exactly:

| SOTA branch | Available at 1 s? | Why |
|---|---|---|
| Low-frequency neural disaggregation (seq2point, RNN/CNN, transformers) | **Yes** | These are the methods evaluated on UK-DALE/REDD at 1 s |
| Foundation-model / prompt-conditioned transfer (FM4NILM, RefQuery, NILMFormer) | **Yes** | FM4NILM spans 1–60 s; NILMFormer is low-frequency by construction |
| Unsupervised domain adaptation, meta-learning, few-shot, federated | **Yes** | Operate on the low-frequency aggregate stream |
| Self-supervised pretraining on unlabelled aggregates | **Yes** | Same stream the meter produces |
| Event detection on ΔP steps | **Yes, improved** | 1 s resolves step edges the 60 s log smears |
| **V-I trajectory / high-frequency methods** (siamese V-I, PLAID-based, harmonics, transient analysis) | **No** | Needs waveforms; the ADE7953 does not expose them at any poll rate |
| **Low-power / standby appliances** (< 30 VA, and < ~230 W at ±5%) | **No** | 30 VA firmware gate plus the analog accuracy band — cadence-independent |

**Two cadence-adjacent limits that survive.** (a) About **1 in 20 switch-ons happens less than a
second after the previous one**, so at 1 Hz those merge into one event
(`docs/datasets/dataset-walkthrough.md`); transfer learning does not separate them, and only
Tier 1+ hardware does. (b) The H04 result (dishwasher/washer-class non-separation) must be
re-examined at 1 s before it is retired — the 60 s conclusion may have been partly a cadence
artefact, and this is now an open, cheap re-test rather than a settled fact.

### 3.1.2 The 30 VA floor — scope around it, do not dismiss it

**Where it genuinely does not matter.** Every appliance in the declared MVP set is 10–100x above the
floor: kettle (approx. 2 kW), microwave (approx. 1 kW), toaster, space heater, water heater, dryer,
AC compressor, EV charger. For that set the floor is a scoping detail, and the project's own EDA
already shows kettle-class detection works with minutes of calibration. If the product promise is
"the big loads that move your bill", the floor is not on the critical path.

**Where it still bites** — three places, and they are not about the target appliances:

1. **Standing / always-on load.** The floor makes the base load largely invisible, and the base is
   typically a large share of a home's kWh (`docs/product/feasibility-verdicts.md` §2 already notes
   the baseline "cannot even see the small loads that constitute most of the standing load"). A
   product that says "see what is using your energy" has a hole exactly where the constant spend is.
2. **ΔP resolution, not just coverage.** The issue is not only that a 25 W appliance vanishes; it is
   that every *step* is measured in 30 VA quanta. A 100 W lamp is approx. 3 quanta; a 40 W step is
   approx. 1 quantum and is indistinguishable from quantisation noise. The ±5% band below 1 A
   (approx. 230 W) adds up to 5% relative error on top, so small-load *attribution* is fuzzy even
   when the step is seen.
3. **It corrupts training, not just coverage.** In seq2point / FHMM the appliance estimates must sum
   to the aggregate; loads the meter cannot see land in the unexplained residual and bias the model
   toward whatever is visible. For the transfer line specifically: if a target home's small appliance
   never appears in its aggregate, **no prompt or embedding recovers it** — conditioning has nothing
   to condition on.

**Two facts that cut in the floor's favour being a blocker.** (a) REFIT carries a comparable
**30 VA measurement-floor quantisation** (`docs/datasets/data-collection.md` row "30 VA
measurement-floor quantization"), so the low-frequency SOTA numbers we compare against were produced
under a similar floor — the benchmark is not floor-free. (b) If `feasibility-verdicts.md` §10 Tier 1
is right that the threshold is a **firmware gate** removed by reflashing ESPHome, the floor becomes
deletable and only the ±5% 0–1 A *analog* band remains. But that section's caveat 4 says the 30 VA
floor is "unchanged by any of this" — **the two statements contradict each other and only one is
right.**

**How to settle it (one hour, no new hardware).** The 100 W lamp test already specified in
`feasibility-verdicts.md` §5 Part B step 4: step a small load and read the raw series. If the step
appears with usable amplitude, the floor is a firmware artifact and the user-facing scoping position
can be generous; if it does not, the floor is analog and the coverage claim must be stated as a
threshold. **This is an empirical question, not a documented one — do not assume either answer.**

**Position to hold.** Scoping around the floor is legitimate; asserting the floor is not real is
not. Note also that the floor is not the meter's interesting limit — the step-change power sensor
with no waveforms is, and no firmware change fixes that.

### 3.2 The ceiling — transfer does not beat the signal

The project's reviewed results already fix this: kettle/fridge-class detection works with minutes
of calibration; dishwasher/washing-machine class does not separate from baseline noise at this
sampling rate (hardware/representation limit, not tuning). H04 ("weak class unreachable") states the
same. The transfer literature is consistent: **domain adaptation moves the cross-domain gap by a few
points; it does not change the within-domain separability of a class.**

**Implication.** Do not present transfer learning as a path to whole-home coverage. Present it as a
path to *doing the feasible coverage without a per-home training campaign*.

### 3.3 What transfers best — the class hierarchy

- The ATL result (IEEE TSG 2019) is directional: **complex → simple transfers; simple → complex does
  not** `[abs]`.
- FM4NILM's best behaviour is on appliances with distinctive, high-power, physics-universal
  signatures `[abs]`.
- H09's own framing anticipates this ("a kettle's physics is more universal than a dishwasher's
  cycle").

**Implication.** A class-ordered transfer policy is defensible and matches both theory and the
project's data: transfer-first for resistive/high-power loads (kettle, microwave, toaster, heater,
water heater, AC compressor, EV charger); per-home-adaptation-required for multi-phase motor loads
(washer, dishwasher); do not claim the rest.

### 3.4 Solar and behind-the-meter injection

*DualNILM: Energy Injection Identification enabled Disaggregation*, arXiv 2508.14600, 2025-08
`[abs]` — behind-the-meter solar/battery injection obscures appliance signatures and **must be
identified as an explicit task**; DualNILM does state recognition and injection identification
jointly. The project's own phases/solar primer raises the same issue.

**Implication.** Any pretrained backbone for the US market needs an injection/export head, or it
will attribute exported energy to appliances. Cheap to add at architecture time, expensive to
retrofit.

### 3.5 Deployment and edge

- *An Embedded Deep Learning NILM System: A Year-Long Field Study in Real Houses*, IEEE TIM 2023,
  doi:10.1109/tim.2023.3328085, 32 cites `[abs]` — seq2point CNN on an Arm Cortex-M7, 12 months in
  two real Italian houses. The closest thing to a field-reality report in this literature.
- *Towards Real-world Deployment of NILM Systems: Challenges and Practices*, arXiv 2409.14821,
  2024-09 `[abs]` — three-tier edge/cloud architecture; the paper's contribution is explicitly the
  engineering gap between algorithms and deployment.
- Knowledge distillation (IEEE TII 2023) `[abs]` and FedNILM `[abs]` — model size and privacy are
  solved-enough to plan on.

**Implication.** A frozen backbone with a tiny adapter is *also* the cheapest thing to serve, which
aligns the accuracy story with the cost story. Good news for the architecture bet.

### 3.6 There is no downloadable pretrained NILM foundation model

Checked 2026-09-26 `[repo]`:

- `adrienpetralia/NILMFormer` (and `EDF-Lab/NILMFormer`): README documents source code +
  experiment reproduction; **no released weights**.
- `FM4NILM`: no public repository found via GitHub search; preprint dated 2026-09-19.
- GitHub searches for "NILM pretrained checkpoint" and "NILM foundation model": no relevant repo.

**Implication.** "Download and fine-tune a NILM FM" is not an available shortcut today. Pretraining
is on us. The staged corpora (46 houses, 2.2B rows) make this feasible; it is a compute/engineering
task, not a data-acquisition one. Re-check quarterly — this is the single fact most likely to change
the plan.

### 3.7 Pretraining-corpus scale, and the label-free options for filling it

- FM4NILM: 645k sequences from **seven** public corpora `[abs]`. Scale, not one dataset, is what
  makes the frozen-backbone result work.
- *Benchmarking Active Learning for NILM* uses **Pecan Street Dataport** `[abs]` — the
  thousand-home US corpus, the obvious scale-up if the US-home requirement binds.
- Synthetic pretraining is a real (if second-best) option: *Synthetic-to-Real Dataset Transfer
  Learning for NILM*, AMPS 2023, doi:10.1109/amps59207.2023.10297255 `[abs]` (seq2point transfers
  synthetic → real, performance depends on how close the probability mass functions are);
  *HiFAKES*, arXiv 2409.00062, 2024-08 `[abs]` (synthetic high-frequency data for generalisation
  diagnostics); *Cluster Aggregated GAN*, arXiv 2512.22287, 2025-12 `[abs]` (appliance-pattern
  generation, branching on intermittent vs continuous loads); industrial digital-twin data,
  arXiv 2506.20525, 2025-06 `[abs]`.
- Weak supervision: *Few Labels are all you need*, ICDE 2025, arXiv 2506.05895 `[abs]` — appliance
  localisation from weak labels; exactly the "cheap, imprecise annotation" regime a button-press
  protocol produces.
- Continual learning for new loads: arXiv 2506.06637, 2025-06 `[abs]` (self-supervised pretraining +
  continual online learning to absorb new appliances without forgetting).

**Implication.** The corpus strategy is: (i) the staged public corpora for supervised source labels;
(ii) synthetic/weak supervision to widen coverage toward the US appliance stock; (iii) the target
home's own unlabelled stream for self-supervised adaptation. Item (iii) is free and is the one most
worth exploiting.

---

## 4. Direction

### 4.1 The architectural bet

**Pretrain once on many houses at the deployment cadence; freeze; adapt per home by conditioning.**

    [multi-house, cadence-augmented corpora]  ->  pretrain cadence-aware backbone (SSL + supervised)
                                                        |
                                                        v
                                   FROZEN backbone  +  per-home adapter
                                                        |
                        +-------------------------------+-------------------------------+
                        |                               |                               |
              (a) request/embedding            (b) few-shot exemplar head       (c) test-time SSL
              conditioned output               (button-press sessions)          on unlabelled aggregate
              (RefQuery / FM4NILM)             (meta-learning / active)         (UDA, DANN, SSL fine-tune)

Keep the appliance inventory **open** (conditioning) rather than a fixed output vector — that is
what makes coverage extensible without retraining, and it is the specific thing Gen-4 papers fix
about Gen-1..3.

### 4.2 Options considered

| Option | Mechanism | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. Pretrain + freeze + condition** (RefQuery / FM4NILM paradigm) | one backbone; per-home adapter is an embedding/prompt learnt from few labels | matches product direction; cheapest per-home cost; extensible coverage; best published cross-house numbers | needs a pretraining run; no off-the-shelf checkpoint; more engineering than per-home fine-tuning | **Recommended** |
| **B. Pretrain + self-supervised adaptation, no target labels** | SSL pretext on the home's aggregate; adapt with zero labels | zero user effort; no calibration ritual at all | weaker than exemplar-conditioned (FM4NILM's exemplars still helped); no ground truth to validate against locally | **Fallback / complement** — use where a home refuses calibration |
| **C. Per-home few-shot fine-tune with active selection** (current calibration idea, upgraded) | freeze most weights; fine-tune head + select queries by uncertainty | smallest step from current work; published recipe (5–15% labels) | per-home training cost; does not scale to many homes cheaply; no coverage extensibility | **Subsumed by A** — keep as the adapter-training procedure, not as the architecture |
| **D. Prompt-only LLM, training-free** | in-context prompting of a general LLM | zero training; strong qualitative cross-region generalisation; explanations | lags DL on complex appliances (authors' own conclusion); cost/latency per query; unvalidated for metering | **Monitor, do not build on** |
| **E. Stay per-home from scratch** (status quo) | train per house | no new machinery | the thing the product direction rejects | Reject |

### 4.3 The calibration protocol becomes the adaptation protocol

This is the cleanest way to reuse existing project assets. Under option A:

- The button-press session is **not** a training run. It is a small set of **activation exemplars**
  for the requested appliance (plus the `DeltaPower` anchor already specified in H02).
- H01's K* question becomes: **how many exemplars per appliance reach the F1 plateau?** The
  literature's prior is single-digit per appliance for the easy classes; the project should measure
  it rather than assume sessions.
- Active selection (Applied Energy 2023 `[abs]`) says **5–15% of a candidate pool** suffices — so
  the protocol can be *adaptive*: press for the appliances the model is least certain about, not a
  fixed list.

### 4.4 What to stop doing

- **Stop training per-home models from scratch.** The 2019 result already said the head is enough;
  the 2026 results say even the head can be an embedding.
- **Do not chase whole-home coverage through transfer learning.** It does not add signal (3.2).
- **Do not grow the labelling ritual.** More annotation is the field's *rejected* answer for complex
  appliances; better signal, conditioning, or scope is the accepted one.
- **Do not adopt V–I / high-frequency few-shot methods.** Strong results, wrong hardware.

---

## 5. What this changes, and what it does not

| Changes | Does **not** change |
|---|---|
| Per-home cost: from a training campaign to an adapter fit / prompt conditioning | The signal-bandwidth ceiling: **no V-I / waveform branch** at any poll rate on this sensor (§3.1.1) |
| Coverage extensibility: a new appliance becomes a new request/embedding, not a new model | The 30 VA floor and the ±5% accuracy band below ~230 W |
| Cold start: a new home can be served by a frozen backbone before any calibration | Multi-phase motor-load separability (washer/dishwasher) — H04 stands |
| Where the moat is: **the pretraining corpus + adapter protocol**, not the per-home model | The need for a per-home anchor for hard classes |
| Product story: "adaptable to your home", measurable as exemplar count to plateau | The fact that public corpora, not proprietary data, supply the supervised labels |

The honest strategic statement: **transfer learning makes the feasible product deployable at scale;
it does not make the infeasible product feasible.** That is still a real and valuable change — it is
the difference between a per-house consulting engagement and a product — but it should be stated
with the ceiling attached.

---

## 6. Decision-relevant experiments (cheap, ordered)

Reuse `src/experiments/00_baseline/baseline_lib.py` and `src/experiments/01_fhmm/fhmm_lib.py`;
do not create a new stack.

**E1 — Cadence-matched corpus and transfer matrix (days).**
Build the corpus at **1 s** (native for UK-DALE/REDD/ECO/GREEND; resample REFIT 8 s and AMPds2
60 s), with 6 s / 8 s / 60 s augmentations as the robustness arm; build the H09 transfer matrix
(UK-DALE h1 ↔ h2–h5; then cross-dataset where classes align). Re-run the H04 weak-class check at
1 s on the same matrix — a negative result at 1 s would be cadence-independent, a positive one
reopens the washer/dishwasher scope. Report per-class off-diagonal vs diagonal.
*Falsifier:* if off-diagonal is at/near diagonal for the target classes, per-home training is
already unnecessary and the whole programme simplifies to a single model.

**E2 — Frozen-backbone linear/embedding probe (the decisive one, ~1 week).**
Pretrain a small cadence-aware seq2point/transformer on the multi-house corpus; freeze; fit only a
per-appliance head and a per-home embedding on N exemplars, sweeping N = 0, 1, 3, 10, 30.
Plot F1 vs N per class against the per-home-trained baseline.
*Falsifier:* if the frozen backbone never reaches the per-home baseline at any sane N, the
foundation-model paradigm does not hold at this cadence, and option C is the ceiling.

**E3 — Self-supervised adaptation with zero target labels (parallel to E2).**
Pretext-pretrain on the held-out house's aggregate only, then probe. This is the label-free arm and
the fallback for uncalibrated homes.
*Falsifier:* no better than no adaptation — then drop option B.

**E4 — Scale-up decision (only after E2).**
If E2's curve is promising, decide the corpus scale-up (Pecan Street Dataport for US homes, synthetic
augmentation for coverage) and the conditioning interface (text request vs embedding).
*Gate:* E4 is a compute/spend decision and should not start before E2 reports.

Each experiment's pass/fail must be written into the hypothesis file **before** the run, per the
registry rules. H09 is the natural home; H01 (K*, restated in exemplars) and H03 (cadence knee)
should be updated to reference the same runs rather than launching parallel ones.

### 6.1 Suggested new hypothesis

**H15 — Conditioning beats retraining at the 1 s deployment cadence.** *Falsifiable:* on the
staged corpora at 1 s, a frozen multi-house backbone with an N-exemplar per-home adapter
reaches the per-home-trained baseline's F1 for target classes at N ≤ some pre-declared small number,
and beats a per-home model trained on the same N examples. Failure mode to pre-declare: the hard
multi-phase classes never close the gap (expected, and consistent with H04).

---

## 7. Where the field is heading (2–3 year read)

1. **Foundation-model NILM is at the prototype stage and moving fast.** FM4NILM (2026-09) is the
   first prompt-programmable NILM foundation model; RefQuery (2026-03) is the first frozen-backbone
   adapter framework. Expect a released checkpoint within a year or two; re-check before committing
   to a large pretraining run.
2. **Conditioning replaces fixed inventories.** "Ask for any appliance" is a better product story
   than a fixed set of trained classes, and it is the direction both 2026 papers take.
3. **Utility-scale production precedent exists.** EDF publishes NILMFormer and maintains the
   repository `[repo]`. The field is no longer purely academic — but the shipped precedent is
   still per-deployment, not a public foundation model.
4. **The unclaimed niche is the intersection of (a) low cadence, (b) single channel, (c) cross-
   country, and (d) a few user-provided exemplars.** Published work covers subsets; none covers all
   four with a foundation-model recipe. If the project wants a defensible technical position, this
   intersection — and the US-home corpora to support it — is the place to hold it.
5. **Solar/islanding, open-set ("UNKNOWN"), and continual learning are becoming first-class.**
   Design them in now (injection head, open inventory, continual update), because they are cheap at
   architecture time and expensive to retrofit.

---

## 8. Sources

Grouped; **bold** = load-bearing for the recommendation. All items were retrieved and read at the
level marked in §2; raw JSON in `research-logs/nilm-transfer-sota/`.

**Canonical transfer**
- **Transfer Learning for NILM**, IEEE TSG 2019, doi:10.1109/tsg.2019.2938068 `[abs]` — ATL/CTL, FC-only fine-tuning.
- GANs and Transfer Learning for NILM, SmartGridComm 2020, doi:10.1109/smartgridcomm47815.2020.9302933 `[abs]`
- Transfer learning for multi-objective NILM in smart building, Applied Energy 2022, doi:10.1016/j.apenergy.2022.120223 `[abs]`
- On Metrics to Assess the Transferability of ML Models in NILM, arXiv 1912.06200 `[abs]`

**Domain adaptation / label-free**
- **Deep Domain Adaptation … Knowledge Transfer Learning Network**, IEEE TSG 2021, doi:10.1109/tsg.2021.3115910 `[abs]`
- Semi-Supervised Domain Adaptation for Multi-Label Classification on NILM, Sensors 2022, doi:10.3390/s22155838 `[abs]`
- **Taming the Domain Shift in Multi-source Learning**, KDD 2023, doi:10.1145/3580305.3599910 `[abs]`
- A Semi-Supervised Approach for Improving Generalization in NILM (DANN, +3%), Sensors 2023, doi:10.3390/s23031444 `[abs]`
- Transferable Tree-Based Ensemble Model for NILM, IEEE TSUSC 2022, doi:10.1109/tsusc.2022.3175941 `[abs]`
- **Non-intrusive NILM based on Self-supervised Learning**, arXiv 2210.04176 `[abs]`
- Investigating Domain Bias in NILM, 2024, doi:10.1145/3671127.3699532 `[abs]`
- Knowledge Distillation for Scalable NILM (unseen domains, +0.14 F1), IEEE TII 2023, doi:10.1109/tii.2023.3328436 `[abs]`

**Few-shot, meta-learning, active learning**
- **Pre-Trained Models for Non-Intrusive Appliance Load Monitoring**, IEEE TGCN 2021, doi:10.1109/tgcn.2021.3087702 `[abs]`
- **Load Recognition With Few-Shot Transfer Learning Based on Meta-Learning and Relational Network**, IEEE TSG 2024, doi:10.1109/tsg.2024.3390441 `[abs]`
- A Few-Shot Learning Method for Nonintrusive Load Monitoring With V–I Trajectory Features, IEEE Sensors J 2024, doi:10.1109/jsen.2024.3365132 `[abs]`
- **An active learning framework for the low-frequency NILM problem** (5–15% labelled), Applied Energy 2023, doi:10.1016/j.apenergy.2023.121078 `[abs]`
- **Benchmarking Active Learning for NILM** (Pecan Street), arXiv 2411.15805 `[abs]`
- Few Labels are all you need (weak supervision), ICDE 2025, arXiv 2506.05895 `[abs]`
- FedNILM, arXiv 2106.07751 `[abs]`; Learning Task-Aware Energy Disaggregation (federated meta-learning), arXiv 2204.06767 `[abs]`

**Foundation models, conditioning, architectures (2025–2026)**
- **Ask for Any Appliance: A Prompt-Programmable Foundation Model for NILM** (FM4NILM), arXiv 2609.23146 `[abs]`
- **RefQuery: Lightweight and Scalable Transfer Learning Framework for Load Disaggregation**, arXiv 2603.04998 `[abs]`
- **NILMFormer**, KDD 2025, arXiv 2506.05880; code `github.com/adrienpetralia/NILMFormer` and `EDF-Lab/NILMFormer` `[repo]`
- Multi-Appliance NILM via Label-Preserving Aggregate Recomposition, arXiv 2609.18315 `[abs]`
- Prompting Large Language Models for Training-Free NILM, arXiv 2505.06330 `[abs]`
- Scaled and Inter-token Relation Enhanced Transformer, arXiv 2410.12861 `[abs]`
- Towards a Deeper Understanding of Transformer for Residential NILM, arXiv 2410.03758 `[abs]`
- NILM Based on Image Load Signatures and Continual Learning, arXiv 2506.06637 `[abs]`
- Dimensionality Expansion of Load Monitoring Time Series and Transfer Learning for EMS, arXiv 2204.02802 `[abs]`

**Cadence, deployment, solar, synthetic**
- **Non-intrusive load disaggregation solutions for very low-rate smart meter data**, Applied Energy 2020, doi:10.1016/j.apenergy.2020.114949 `[abs]`
- **NILM with very low-frequency data from smart meters in Switzerland**, Energy & Buildings 2025, doi:10.1016/j.enbuild.2025.116002 `[abs]`
- **An Embedded Deep Learning NILM System: A Year-Long Field Study in Real Houses**, IEEE TIM 2023, doi:10.1109/tim.2023.3328085 `[abs]`
- Towards Real-world Deployment of NILM Systems, arXiv 2409.14821 `[abs]`
- **DualNILM: Energy Injection Identification enabled Disaggregation** (BTM solar), arXiv 2508.14600 `[abs]`
- Synthetic-to-Real Dataset Transfer Learning for NILM, AMPS 2023, doi:10.1109/amps59207.2023.10297255 `[abs]`
- HiFAKES, arXiv 2409.00062 `[abs]`; Cluster Aggregated GAN, arXiv 2512.22287 `[abs]`; industrial digital twin, arXiv 2506.20525 `[abs]`
- Neural Fourier Energy Disaggregation, Sensors 2022, doi:10.3390/s22020473 `[abs]`

**Surveys (for orientation)**
- **Non-Intrusive Load Monitoring: A Systematic Review of Methods, Scenario-Specific Challenges, and Pathways to Practical Deployment**, Energies 2026, doi:10.3390/en19081883 `[abs]` — lists algorithm transferability as a cross-cutting unsolved challenge.
- A Survey of Traditional and Emerging Deep Learning Techniques for NILM, AI 2025, doi:10.3390/ai6090213 `[abs]`
- Towards Trustworthy Energy Disaggregation, Sensors 2022 `[abs]`
- Emergent Mind NILM topic page (orientation only; does not cover transfer in depth), `research-logs/nilm-transfer-sota/raw/emergentmind-nilm.txt`

**Corpus provenance for the raw harvest**
- arXiv Atom API (13 queries) and OpenAlex works API (13 queries), 2026-09-26, saved under
  `research-logs/nilm-transfer-sota/arxiv/` and `/openalex/`.

---

## 9. Caveats — how to read this

- Most items are **abstract-level** `[abs]`. Specific numbers (F1, AUPRC, percentages) are quoted
  as the authors report them and are **not comparable across papers**: datasets, splits, metrics
  (event F1 vs energy F1 vs AUPRC), and appliance definitions all differ. Treat cross-paper numbers
  as indicative of direction and magnitude, not as a leaderboard.
- The two 2026 foundation-model papers are preprints; FM4NILM is dated 2026-09-19 and has had no
  time for scrutiny `[abs]`. Their paradigm is the trend; their specific numbers are not yet
  independently replicated.
- "No released **disaggregation** checkpoint" and "no code for FM4NILM" were checked on 2026-09-26
  via GitHub search and README inspection `[repo]`; this is the fact most likely to expire — and it
  has already partly expired at the margins (see §10.2, EnergyFM).
- This review does not re-derive any project-internal measurement; it relies on the reviewed
  findings already recorded in `docs/reports/gt_cycle/` and the hypothesis registry.

---

## 10. Addendum — second harvest and two corrections (2026-09-26, after owner review)

The owner challenged the coverage of the Emergent Mind page's citations. A second pass (Google/SERP
plus OpenAlex follow-ups, raw artifacts in `research-logs/nilm-transfer-sota/google_search/`) found
material the keyword-driven first pass missed, and **narrows two claims made in §0 and §3.6**.

### 10.1 Correction — a cross-building benchmark now exists

§0 and §3.6 implied that cross-house generalisation has no standard evaluation. It does now:

- **NILMBENCH2026: A Benchmark for Energy Disaggregation**, BuildSys '26 (Best Paper Candidate),
  doi:10.1145/3744256.3812587; reference implementation + runner at `github.com/nilmtk/nilmbench`
  `[repo]` — 16 models scored on regression accuracy, event-detection F1, parameters, FLOPs and
  runtime, with three explicit tasks: **T1 intra-building**, **T2 cross-building** (UK-DALE B1+B2 →
  B4), **T3 cross-dataset** (US → UK, different voltage standard).
- **NILMbench: A Novel Benchmark for High-Frequency NILM Models**, TechRxiv 2025,
  doi:10.36227/techrxiv.173834807.74888368 `[abs]` — the high-frequency sibling.

**Consequence.** T2 and T3 are exactly the H09 transfer question, already implemented, from the
canonical NILMTK group. **E1/E2 should adopt `nilmbench` as the harness rather than build an
evaluation scaffold** — that removes most of the estimated build cost from E1. Note T3 (US → UK) is
directly the cross-country case a US product needs.

### 10.2 Correction — a downloadable pretrained energy model exists (but not for disaggregation)

- **EnergyFM: Pretrained Models for Energy Meter Data Analytics**, e-Energy 2026,
  doi:10.1145/3744255.3798119 (Arjunan, Srivastava, Kumar, Jati) `[abs]` — IBM Tiny Time Mixers
  (TTM) and TSPulse backbones, pretrained on approx. **1.26 billion hourly** consumption records
  across tens of thousands of buildings; **weights published** on Hugging Face
  (`huggingface.co/EnergyFM/energy-ttm`) `[repo]`. Claims zero/few-shot transfer across
  heterogeneous buildings, regions and sectors; sub-5M parameters, CPU-runnable.

**The claim therefore sharpens rather than falls:** there is still **no public pretrained
*disaggregation* checkpoint**, but there is now a public pretrained *energy-meter* foundation model.
Two things follow. (a) It is **proof that the pretrain-once / adapt-per-building paradigm ships** in
this domain, which strengthens the §4.1 architecture bet. (b) It is a **candidate initialisation or
baseline for an aggregate encoder** — but at **hourly** cadence and trained for forecasting,
anomaly detection, imputation and classification, **not appliance separation**, so it cannot be
dropped in as a NILM backbone. Test it as an encoder initialisation, not as a solution.

Adjacent power-domain foundation models, for orientation only — none does appliance-level
disaggregation: PowerPM (NeurIPS 2024), PowerFM (`github.com/Power-Agent/PowerFM`), GridFM /
OpenGridFM, GridSFM (Microsoft), and the FETS forecasting benchmark (arXiv 2604.22328, 54 datasets
across 9 categories, **forecasting not disaggregation**).

### 10.3 Sources the first pass missed (all transfer-relevant)

- **Source-Free Domain Adaptation With Self-Supervised Learning for Nonintrusive Load Monitoring**,
  IEEE TIM 2024, doi:10.1109/tim.2024.3480230 `[abs]` — the closest published match to option B
  (§4.2): adapts with **no source data and no target labels**. Read before designing E3.
- **NILM Domain Adaptation: When Does It Work?**, 2024, doi:10.1109/icscc62041.2024.10690585
  `[abs]` — concludes domain adaptation is feasible but **warns explicitly about overfitting**.
  This is the cautionary counterweight to the optimistic half of §2, and worth citing honestly.
- **Semi-Supervised Domain Adaptation for Multi-Label Classification on NILM**, Sensors 2022,
  doi:10.3390/s22155838 `[abs]`
- **A Label-Free and Transferable NILM Framework for Smart Buildings**, IEEE 2026 (Hao et al.)
  `[abs]` — domain-generalisation framing (source-only training), label-free.
- **SimCLR-based NILM with colourised V–I trajectories**, Sensors 2026, doi:10.3390/s26041230
  `[abs]` — self-supervised contrastive pretraining; note the V–I front end is **high-frequency**,
  so the SSL result is informative but the input representation is not ours.
- Synthetic-to-Real Domain Adaptation for NILM via Reconstruction-Based Transfer Learning `[abs]`
- Second-pass orientation surveys: Saleem et al. 2025, doi:10.1007/s10489-025-06921-4 (21 cites);
  Xiang et al. 2026, doi:10.3390/en19081883; a 2026 NILM systematic review of observability regimes
  `[abs]`.

### 10.4 Assessment of the four citations raised in review

The Emergent Mind page is a usable **map** but its attributions and numbers are **not quotable
without going to the primary source**. Specifically:

- **UNILM** — Rodriguez-Silva & Makonin, 2019, doi:10.1109/appeec45492.2019.8994618, arXiv
  1907.06299, 14 cites `[abs]`. The "over 93%" is **93.7% of total aggregate energy accounted
  for** — an energy-attribution figure dominated by the largest loads, **not** per-appliance
  accuracy. It is real support for *unsupervised* operation (no submetered training) and a useful
  precedent; it is **not** evidence that appliances can be separated. Do not quote it as a
  disaggregation accuracy.
- **Azizi et al. 2020** — *A Novel Event-based NILM Algorithm*, arXiv 2009.02656 `[abs]`.
  Validated on **REDD at low frequency** — genuinely in-regime and worth reading in full. Its own
  framing names "close consumption values by different appliances" as a problem to solve, i.e. it
  targets our H04 difficulty rather than dissolving it.
- **Faustine et al. 2017 is a survey** (arXiv 1703.00785, *A Survey on Non-Intrusive Load Monitoring
  Methodies and Techniques*). The page cites it as an example of an *event-based approach* — **a
  misattribution.** The ">94% recall and nearly zero false positive rates" sentence is the page's
  synthesis; it is **not** a result I could source to Lu et al. 2019 or Azizi et al. 2020.
- **Liu et al. 2024** could not be resolved to a specific work; the page cites it for both
  steady-state modelling and combinatorial optimisation, which reads as a generic pointer.
- **Toirov et al. 2025** — arXiv 2506.06637, *NILM Based on Image Load Signatures and Continual
  Learning* `[abs]`. Continual learning + self-supervised pretraining is the right *idea*, but the
  method converts **current, voltage and power factor** into image signatures and evaluates on
  **high-sampling-rate datasets** — the **HF/V–I branch we cannot use**. The concept transfers; this
  implementation does not.

### 10.5 Net effect

No change to the §4 direction or the §4.1 architecture. Two claims are narrowed (§10.1, §10.2), the
evaluation plan gets cheaper (adopt `nilmbench`), and the label-free route gains a concrete prior
work to build on (§10.3). The methodological lesson is recorded as a caveat: **the first pass was
keyword-anchored on transfer terminology and under-sampled event-detection, unsupervised and
benchmark literature; a second pass on the citations of any secondary source is required before
quoting it.**

---

## 11. Third harvest — full texts, and the routes the owner probed (2026-09-26)

The owner asked specifically about the **continual-learning + SSL** route and the **unsupervised**
route at low frequency, and directed that full texts be read rather than abstracts. This section
records what the full texts actually say. Raw artifacts:
`research-logs/nilm-transfer-sota/nilmbench/` (paper PDF, `paper.txt`, `pdf.txt`, `leaderboard.csv`,
`leaderboard.json`) and `/arxiv2/`, `/google_search/`.

### 11.1 NILMBench2026, read in full — this is the harness, and it re-frames the problem

**NILMBench2026: A Benchmark for Energy Disaggregation**, Kuloor, Singh, Dhru, Batra (IIT
Gandhinagar), BuildSys '26, Best Paper Candidate, doi:10.1145/3744256.3812587 `[full]`. Full text
read (11 pp.); reference runner at `github.com/nilmtk/nilmbench` `[repo]`.

**What it is.** 16 models, 3 datasets (UK-DALE, REDD, REFIT), **2 resolutions (1 min and 15 min)**,
576 configurations x 3 runs, with Docker + uv provenance, FLOPs/runtime accounting, and a
leaderboard. It supersedes NILMTK '14 and nilmtk-contrib '19 by adding efficiency, multi-resolution
support, and — the part that matters here — **cross-building and cross-dataset generalisation as
first-class tasks**.

**The three tasks (verbatim protocol).**
- **T1 intra-building** — train 30 days on B1, test a held-out 1 week on B1 (temporal generalisation).
- **T2 cross-building** — UK-DALE: train B1+B2, test **B4**; REDD: train B1+B2+B3, test **B6**;
  REFIT: train B2+B3, test **B4**.
- **T3 cross-dataset zero-shot** — REDD (USA, 110 V) to REFIT (UK, 230 V), and the **reverse
  direction REFIT to REDD** as an explicit control.

**The findings, which are the field's current consensus.** (1) *No single model wins* — the best
architecture is appliance-dependent; CNNs excel on sparse high-power events, Transformers on
multi-state loads, so real deployment implies an ensemble or multi-expert system. (2) **Generalisation
is the main hurdle** — "performance falls off a cliff as the domain shifts", degradation appears in
*both* transfer directions, and the authors verify bidirectionally that the gap is **fundamental, not
a directional artifact**. (3) **MAE is misleading** — predicting "off" always scores a low MAE while
missing every activation; **event F1 is essential**. (4) *Efficiency is not accuracy* — the trade-off
is non-monotonic, and a **69K-parameter TCN rivals heavyweight NILMFormer on cross-dataset tasks**.

**Two results that land directly on this project.**
- **The dishwasher is the worst-generalising load.** In T3, "the dishwasher proves to be the most
  challenging load for generalisation, with nearly all models struggling to produce a meaningful
  prediction"; BERT is simultaneously the best model on the washing machine and the worst on the
  dishwasher. This independently reproduces our H04/H14 finding that the multi-state weak class does
  not separate — and shows it is a **field-wide** wall at 1 min, not a defect in our baseline.
- **MAE-only evaluation is not admissible.** Their appliance classes are Fridge (always-on),
  Microwave and Kettle (bursty), Washing Machine and Dish Washer (multi-state), Television
  (dynamic) — matching our class split. Any of our comparisons that rest on MAE alone must be
  re-stated in event F1 before being used to choose between designs.

**Their named research directions are our plan.** The closing section lists six: (1) domain
adaptation, (2) **self-supervised pre-training — "evaluate masked modeling on unlabeled
aggregate-power data before supervised fine-tuning"**, (3) multi-task state classification,
(4) adaptive denormalisation (local statistics, time-of-day, occupancy), (5) generative augmentation,
(6) maintained leaderboards. Directions 1, 2 and 4 are the §4 recommendation, arrived at
independently by the canonical benchmark group.

**Three caveats before adopting it.** (a) Their finest resolution is **60 s**, coarser than our 1 s
reach — our numbers will not be leaderboard-comparable unless we either re-run at 60 s or publish a
finer-resolution extension. (b) The in-repo `leaderboard.json` currently holds only `corrected-t1-redd`
**smoke** runs (52 entries); the real T2/T3 tables live in the paper PDF, so the numbers must be
transcribed from the paper, not scraped. (c) REDD/UK-DALE/REFIT HDF5 conversions are **not
redistributed** — the runner verifies user-supplied files against recorded SHA-256 digests, so there
is a real data-staging step before any run.

### 11.2 The SSL route at low frequency — yes, and it is the closest thing to our option B

The owner's read was right that Toirov et al. used the high-frequency V-I branch. The low-frequency
SSL work does exist, and the direct hit is:

- **Non-intrusive Load Monitoring based on Self-supervised Learning** — Shuyi Chen, Bochao Zhao,
  Mingjun Zhong, Wenpeng Luan, arXiv **2210.04176** (2022-10-09) `[abs]`. **"Labeled appliance-level
  data from the target data set or house is not required."** Only the **target aggregate power
  readings** are used, to pre-train a general network on a self-supervised pretext task mapping
  aggregate sequences to derived representatives; supervised downstream heads are then fine-tuned per
  appliance from **source** labels and applied to the target. The motivation is stated as exactly our
  problem: models "tend to require a large amount of labeled data" and are "difficult to generalise to
  unseen sites due to different load characteristics". This is option B (§4.2) already published, by
  the Nottingham group (Mingjun Zhong, Wenpeng Luan), at low frequency. **Read this in full before
  designing E3.**
- **Source-Free Domain Adaptation With Self-Supervised Learning for Nonintrusive Load Monitoring** —
  Zhong, Shan, Si, Liu, IEEE TIM 2024, doi:10.1109/tim.2024.3480230 `[abs]` — adapts with **no source
  data and no target labels**, i.e. the stricter variant where even the source corpus is unavailable
  at adaptation time.
- Adjacent: SimCLR-based NILM with colourised V-I trajectories, Sensors 2026, doi:10.3390/s26041230
  `[abs]` — SSL machinery, but a **high-frequency** front end.
- Survey-level: continual learning for energy management systems, Sayed, Himeur, Varlamis, Applied
  Energy 2025, doi:10.1016/j.apenergy.2025.125458, 24 cites `[abs]`.

### 11.3 The continual-learning route at low frequency — real but thin

- **Analytic Continual Learning-Based Non-Intrusive Load Monitoring**, Lan et al., Applied Sciences
  2025, 15(12):6571, doi:10.3390/app15126571 `[abs]` — low-frequency, explicitly framed around
  catastrophic forgetting and static label spaces as appliances are added.
- **Confidence-Based, Collaborative, Distributed Continual Learning Framework for NILM**, Lan, Luo,
  Yu, Sensors 2025, doi:10.3390/s25123667 `[abs]`.
- **Appliance-Incremental Learning for Non-Intrusive Load Monitoring** (2023) `[abs]` — incremental
  label space, new appliances added without retraining from scratch.
- The review (Sayed et al. 2025) is the entry point; **Toirov et al. 2025 remains the only
  continual-learning + SSL paper in the recent arXiv harvest, and it is high-frequency.**

**Assessment.** Continual learning at low frequency is **not** a mature line we can lift from — a
handful of 2023–2025 papers, no shared benchmark, no released code comparable to NILMTK. It is
nonetheless the *correct framing* for a product that adds appliance classes over time, and it is
cheap to adopt as a **specification** (freeze the backbone; add a head per appliance class; never
re-train the encoder per class) without adopting anyone's method wholesale.

### 11.4 The unsupervised route at low frequency — a real, older, still-active branch

This is more substantial than the first pass implied, and it deserves to be treated as a distinct
option rather than a footnote:

- **Autonomous Load Disaggregation Approach based on Active Power Measurements** — Egarter,
  Elmenreich, arXiv 1412.2877 (2014) `[abs]` — unsupervised, "without a priori knowledge about
  appliances", learns appliance models **in operation and updates them progressively**, on **1 s**
  active-power data.
- **Unsupervised algorithm for disaggregating low-sampling-rate electricity consumption of
  households** — Holweger et al., Sustainable Energy, Grids and Networks 2019,
  doi:10.1016/j.segan.2019.100244, 60 cites `[abs]`.
- **UNILM** — Rodriguez-Silva & Makonin 2019, arXiv 1907.06299 `[abs]` — filter pipelines +
  probabilistic knapsack; unsupervised; the 93.7% is aggregate **energy accounting** (see §10.4).
- **Unsupervised Disaggregation of Water Heater Load from Smart Meter Data** — Zufferey, Valverde,
  Hug, arXiv 2104.03120 `[abs]` — **minute-range** resolution, and it argues explicitly that
  existing NILM methods "require data streams at a time resolution in the range of one second or
  higher, which is not realistic for standard SMs".
- **An ICA-Based HVAC Load Disaggregation Method Using Smart Meter Data** — Kim, Ye, Lee, Hu, arXiv
  2209.09165 `[abs]` — blind-source-separation route at **15-minute** resolution on Pecan Street,
  with temperature-derived bounds to suppress unrealistic spikes.
- **A Bayesian Approach to Unsupervised, Non-Intrusive Load Disaggregation** — Massidda et al.,
  Sensors 2022, doi:10.3390/s22154481, 32 cites `[abs]`.
- **Energy Disaggregation via Deep Temporal Dictionary Learning** — Khodayar, Wang, Wang, arXiv
  1809.03534 `[abs]` — sparse dictionary learning, unsupervised, with a deep model supplying
  nonlinear temporal features.
- **NILM based on Unsupervised Learning** — Liu et al., Frontiers in Energy Research 2021,
  doi:10.3389/fenrg.2021.718916 `[abs]` — unsupervised identification of **newly added** appliances
  combined with a supervised back-propagation network.
- Plus the statistical classics: HMM / factorial-HMM inference by EM without labels, and
  **Bayesian surprise** as an overfitting guard (Jones & Klemenjak, arXiv 2009.07756 `[abs]`).

**The structural insight, and why this branch still has not solved our problem.** Almost every
successful unsupervised result targets a **single appliance or a coarse category** — water heaters,
HVAC, base load, "always-on" — or accepts category-level rather than appliance-level output. That is
precisely how it avoids labels. Where the target is the full multi-class appliance set at low
frequency, the branch converges on the same wall NILMBench2026 documents for the dishwasher and our
H04 recorded for washer/dishwasher.

**Therefore the realistic product shape is hybrid, not purely unsupervised:** use the unsupervised
route for the classes it actually wins on (high-power, thermally inert or strongly periodic loads
whose signatures survive at our cadence), and reserve cheap per-home calibration for the multi-state
weak class. That is a refinement of the §4 direction, not a replacement for it.

### 11.5 What §11 changes

- **E1/E2 get a published protocol and harness** (`nilmbench`, T1/T2/T3, Docker + uv, SHA-verified
  data) instead of a bespoke scaffold — the single largest cost reduction in the plan. Budget for the
  data-staging step, and plan a 60 s re-run (or a declared finer-resolution extension) for
  comparability.
- **Evaluation must be event-F1-first.** MAE-only comparisons are demonstrably misleading for the
  bursty and multi-state classes; this is now a stated result in the field's reference benchmark, not
  a preference.
- **E3 has direct prior art to build on** (§11.2) and should be written as a replication-plus-extension
  of Chen et al. 2022 rather than a from-scratch design.
- **The multi-state wall is externally confirmed.** Our H04/H14 result is now corroborated at 1 min by
  an independent benchmark on three datasets; the 1 s re-test is a genuine open question, not a
  re-litigation.
- **Continual learning is adopted as a specification, not a method** (§11.3).
- **Unsupervised is scoped per class, not adopted wholesale** (§11.4).
