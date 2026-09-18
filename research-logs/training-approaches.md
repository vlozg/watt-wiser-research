---
title: "NILM training approaches — an ablation over the design space"
topic: watt-wiser / NILM literature
date: 2026-06-19
status: complete
---

# NILM training approaches — what has already been tried

Purpose: answer "has anyone done this before?" for the *training and adaptation* side of the
WattWiser calibration idea, not the NILM idea in general. The calibration-to-detection MVP is,
mechanically, **active learning plus fine-tuning on household-specific labels**. This note
decomposes that design space into the axes a pipeline can vary, and records what each choice has
been shown to buy.

Method: harvested 804 works matching NILM phrases from OpenAlex (published 2014-2026, ranked by
citations), bucketed them by method keyword, then pulled full text where an open copy existed
(Strathprints, Lincoln eprints, arXiv). Raw data in training-approaches-raw.json and
training-approaches-key.json alongside this file.

---

## 1. The short answer

**Every component of the calibration idea already exists in the literature, published, cited, and
benchmarked.** Household-specific adaptation, active selection of which events to label, few-shot
fine-tuning, unknown-appliance rejection, per-home personalisation at the edge — all of it is
done. There are at least 33 papers on transfer/domain adaptation for NILM, 7 on active learning,
4 on few-shot/meta-learning, and 20 on federated/privacy-preserving NILM.

**And the literature's verdict is more damaging than "not novel."** Two findings in particular:

1. **Fine-tuning is only needed when domains genuinely differ, and even then only the last layers.**
   The canonical transfer study concludes that if the training and test data are in a similar
   domain, the model can be applied *"without fine tuning"*, and in a different domain *"only the
   fully connected layers need fine tuning."* So the case for a per-household calibration ritual is
   narrower than it looks.

2. **The literature's answer to "complex appliances" is a better signal, not more labels.** The NILM
   work that specifically targets complex or unidentified appliances reaches for **high-frequency
   V-I trajectories**, wavelets, or siamese embedding spaces — never for a bigger labelling effort
   in the home. That is the opposite of the calibration hypothesis.

---

## 2. The design space, decomposed

An NILM training pipeline varies along six axes. The calibration idea fixes four of them and leaves
two open, which is why it looks more novel than it is.

| Axis | Options in the literature | What WattWiser fixes |
|---|---|---|
| **Label source** | source labels; target labels; active querying; self-supervised pretext; unsupervised adaptation; federated; none | active querying (the calibration ritual) |
| **Target-domain data volume** | none; a handful (few-shot); 5-15% of a pool; a short time diary; a full labelled house | a short diary, then ongoing queries |
| **What transfers** | all weights; only fully-connected layers; latent features; embedding space | unspecified |
| **Prediction target** | regression (power), classification (on/off), unknown rejection | per-appliance representation, UNKNOWN class |
| **Where it runs** | cloud, edge, on-meter | Python layer behind a website |
| **Signal** | 1 s - 1 min power; 15 min AMI; high-frequency V-I | 1 min power (stock) |

---

## 3. Ablation table — what each approach changed, and what it bought

### 3.1 Label source

**Transfer learning / fine-tuning.** The default modern answer.

| Work | What it changed | Reported outcome |
|---|---|---|
| Transfer Learning for NILM, IEEE TSG 2019, doi:10.1109/tsg.2019.2938068 (327 cites) | Two schemes: appliance transfer learning (ATL) and cross-domain transfer learning (CTL) on seq2point | Latent features learned by a **complex** appliance (washing machine) transfer to a **simple** one (kettle). Similar domains need no fine-tuning; different domains need fine-tuning of **only the fully connected layers** |
| Deep Domain Adaptation ... Knowledge Transfer Learning Network, TSG 2021, doi:10.1109/tsg.2021.3115910 | Temporal convolutional network plus a domain-adaptation loss | Learns an invariant cross-domain representation for appliance states; "superior transferability" |
| Unsupervised Domain Adaptation ... Adversarial and Joint Adaptation Network, TII 2021, doi:10.1109/tii.2021.3065934 | Adversarial plus joint adaptation on feature *and* label space | "Only very limited labeled data in the source domain and enough **unlabeled** data in the target domain"; significant MAE improvement over the no-adaptation baseline |
| Transferability of Neural Network Approaches for Low-rate Energy Disaggregation, ICASSP 2019, doi:10.1109/icassp.2019.8682486 | CNN and GRU, tested on houses **not seen** during training | Explicitly targets "disaggregation on houses which have not been 'seen' before" |
| Transfer learning for multi-objective NILM in smart building, Applied Energy 2022, doi:10.1016/j.apenergy.2022.120223 | Multi-objective transfer between buildings | — |
| NILM by Voltage-Current Trajectory Enabled Transfer Learning, TSG 2018, doi:10.1109/tsg.2018.2888581 (251 cites) | Transfer on **V-I trajectories** (high frequency) | — |

**Active learning.** The direct ancestor of the calibration ritual.

| Work | What it changed | Reported outcome |
|---|---|---|
| An active learning framework for the low-frequency NILM problem, Applied Energy 2023, doi:10.1016/j.apenergy.2023.121078 (67 cites) | BatchBALD and probability/distance query strategies, stream-based querying, fine-tuning vs full retrain, applied to on/off classification across REDD, REFIT and UK-DALE | **Optimal accuracy-labelling trade-off with only 5%-15% of the query pool labelled.** Initial training set just 2^13 samples (a "small time-diary"); fine-tuning cost independent of pre-training set size |
| A Load Identification Method Based on Active Deep Learning and DWT, IEEE Access 2020, doi:10.1109/access.2020.3003778 (53 cites) | Pool-based and stream-based active deep learning on wavelet features | **33% fewer samples than the prior state of the art at equal F1** |
| Real-time Disaggregation ... Enhanced with User Feedback, 2019, doi:10.1109/cccs.2019.8888140 | Selects the disaggregation model dynamically from **user feedback on correctness** | Low citations; the concept is the same as the "user confirmation" step in the WattWiser loop |

**Self-supervised and unsupervised.** Removes the need for target labels entirely.

| Work | What it changed | Reported outcome |
|---|---|---|
| NILM Based on Self-Supervised Learning, IEEE TIM 2023, doi:10.1109/tim.2023.3246504 (43 cites) | Pretext task on **unlabelled target aggregates**, then supervised fine-tuning with source labels | "Labeled appliance-level data from the target dataset or house are **not required**"; designed for "unseen sites" |
| An unsupervised training method for NIALM, Artificial Intelligence 2014, doi:10.1016/j.artint.2014.07.010 (171 cites) | Fully unsupervised training | — |
| Low-Complexity NILM Using Unsupervised Learning and Generalized Appliance Models, IEEE TCE 2019, doi:10.1109/tce.2019.2891160 (136 cites) | Unsupervised, generalized appliance models, on-device oriented | — |
| On a Training-Less Solution for NIALM Using Graph Signal Processing, IEEE Access 2016, doi:10.1109/access.2016.2557460 (215 cites) | **No training at all** — graph signal processing | The extreme end of the axis |
| Non-Intrusive Load Disaggregation Using Graph Signal Processing, TSG 2016, doi:10.1109/tsg.2016.2598872 (309 cites) | GSP formulation | — |
| Pre-Trained Models for Non-Intrusive Appliance Load Monitoring, IEEE TGCN 2021, doi:10.1109/tgcn.2021.3087702 (53 cites) | Meta-learning and ensemble pre-training, then few-shot fine-tune on an unknown dataset | "Superior transferability performance compared with traditional DL and transfer learning methods" |

**Federated.** Keeps labels in the home and personalises at the edge.

| Work | What it changed | Reported outcome |
|---|---|---|
| FedNILM, IEEE TGCN 2022, doi:10.1109/tgcn.2022.3167392 (85 cites) | Federated learning, cloud model compression via filter pruning and multi-task learning, **personalised edge model via unsupervised transfer learning** | Targets exactly "edge model personalization" and "edge training data scarcity"; state-of-the-art accuracy with privacy preserved |
| Neural Load Disaggregation: Meta-Analysis, Federated Learning and Beyond, Energies 2023, doi:10.3390/en16020991 (21 cites) | Meta-analysis of NILM reviews plus a federated survey | — |
| Energy Disaggregation with Federated and Transfer Learning, WF-IoT 2021, doi:10.1109/wf-iot51360.2021.9595167 | Combines both | — |

**Unknown-appliance rejection.** This is the literature's version of the UNKNOWN class and the
"codebook".

| Work | What it changed | Reported outcome |
|---|---|---|
| Detection of unidentified appliances in NILM using siamese neural networks, IJEPES 2018, doi:10.1016/j.ijepes.2018.07.026 (121 cites) | Siamese embedding for unidentified appliances | — |
| Non-Intrusive Adaptive Load Identification Based on Siamese Network, IEEE Access 2022, doi:10.1109/access.2022.3145982 (42 cites) | V-I trajectory plus active power; matching against a **feature library** | "Through **adding new features to the feature library dynamically**, the identification of unknown load can be realized"; few-shot trainable. This is a codebook, built incrementally, exactly as described |

### 3.2 Where it runs

| Work | What it changed |
|---|---|
| Exploiting HMM Sparsity to Perform Online Real-Time NILM, TSG 2015, doi:10.1109/tsg.2015.2494592 (381 cites) | Online, real-time, sparse HMM |
| A Cloud-Based On-Line Disaggregation Algorithm for Home Appliance Loads, TSG 2018, doi:10.1109/tsg.2018.2826844 (112 cites) | "Fast and on-line household appliance load detection" |
| Real-Time Energy Disaggregation of a Distribution Feeder's Demand Using Online Learning, TPWRS 2018, doi:10.1109/tpwrs.2018.2800535 (33 cites) | Dynamic Fixed Share online learning. **Feeder-level, not household** — the only genuinely "online learning" work found is feeder-scale |
| Separating Feeder Demand Into Components, TSG 2020, doi:10.1109/tsg.2020.2967220 (47 cites) | Feeder-level, substation plus smart meter |

**Finding.** True *online/incremental* learning for **household** NILM is thin. Both clear
"online learning" papers are **feeder-level**, where the target is a population of air conditioners,
not an appliance in one home. Household-side "online" work is real-time *inference*, not online
*learning*.

### 3.3 Architecture (mostly orthogonal to the calibration question)

BERT4NILM (2020, doi:10.1145/3427771.3429390, 132 cites), ELECTRIcity transformer
(Sensors 2022, doi:10.3390/s22082926, 85 cites), Energformer (TCE 2023,
doi:10.1109/tce.2023.3237862, 70 cites), attention-based DNN
(Sensors 2021, doi:10.3390/en14040847, 104 cites). These improve accuracy on a fixed dataset;
they do not address cross-household generalisation.

### 3.4 Baselines and reviews

- Neural NILM, Kelly and Knottenbelt 2015, arXiv:1507.06594 (890 cites) — the origin. Reports that
  the neural nets "generalise well to an unseen house", beating combinatorial optimisation and FHMM
  on F1, precision, proportion of energy correctly assigned and MAE.
- Review on DNN Applied to Low-Frequency NILM, Energies 2021, doi:10.3390/en14092390 (125 cites).
- NILM: A Review, TSG 2022, doi:10.1109/tsg.2022.3189598 (277 cites).
- Towards Trustworthy Energy Disaggregation, Sensors 2022, doi:10.3390/s22155872 (112 cites) —
  declares a "mature NILM period" where "complexity, transferability, reliability, practicality and
  trustworthiness are the main issues of interest".
- Performance evaluation in NILM, WIREs DMKD 2018, doi:10.1002/widm.1265 (194 cites) —
  "there is still no consensus regarding which performance metrics should be used".

---

## 4. What the evidence says about the calibration premise

The premise is: *a household-specific guided calibration step is what makes appliance identification
work, especially for complex appliances.*

**Point 1 — the mechanism is established, not novel.** Calibration is active learning plus
fine-tuning. Todic 2023 does the query-strategy half rigorously and reports 5-15% of a pool. Zhong
2019 does the fine-tuning half and reports the fully-connected-layers-only result. The WattWiser
document describes the combination qualitatively and cites neither.

**Point 2 — the case for per-home work is narrower than it appears.** Zhong 2019's conclusion is
conditional: **similar domain means no fine-tuning at all**. A per-household ritual is justified
only to the extent that homes are genuinely different domains. Nobody in the WattWiser material has
established that they are — and the honest way to settle it is the transfer experiment, not an
appeal to opinion.

**Point 3 — active learning is the strongest supporting evidence, and it caps the effort.**
5-15% of a query pool is a real reduction. But note what a "query pool" is: 65,536 on/off samples in
Todic's setup, with an initial training set of 8,192. Calibration saves *labeling*, not *collection*.
The data still has to exist.

**Point 4 — the literature answers "complex appliances" with signal, not labels.** Every NILM work
that specifically targets complex or unidentified appliances uses V-I trajectories (TSG 2018),
wavelets (Access 2020), or a siamese embedding space (2018, 2022). Not one of them concludes that
more per-home labels unlock complex multi-stage separation. The bottleneck they identify is
**information in the signal**, which is exactly the 30 VA floor and the 1-minute sample interval
documented in the post-meeting assessment.

**Point 5 — the one finding that actually helps the complex-appliance story.** Zhong 2019's ATL
result is the closest thing to support: latent features learned from a **washing machine** transfer
to a **kettle**. But read carefully — the transfer direction is *complex to simple*. The complex
appliance is a **feature donor**, not a target of identification. That is a different claim from
"we can identify complex appliances", and it is the only version the evidence supports.

**Point 6 — labelling is not one-off, which cuts both ways.** Todic 2023 is explicit that
*"labelling is not a one-off task due to the large diversity of devices used in different
houses/buildings, and dynamic nature of these devices"* — wear and tear changes signatures over
years, and new appliances appear. This supports the need for ongoing user interaction; it also
means the per-household cost never amortises away.

---

## 5. The gap — what nobody has done

Useful for framing a genuine contribution, if they want one:

1. **A controlled ablation of calibration data volume against accuracy, at a fixed low sample
   rate.** Todic 2023 gets a query fraction (5-15%) on on/off classification. Nobody has produced
   the curve of *"with N minutes of guided household calibration at a 1-minute sample interval, here
   is the precision/recall you get on appliance class X"*, for a consumer device.
2. **The resolution floor as a function of sample rate.** The literature assumes 1 s or better for
   DNN NILM ("below 10 s" is the standard finding). What is achievable at exactly 60 s on consumer
   CT hardware is not established anywhere I found.
3. **Cross-household transfer measured on consumer-grade hardware rather than reference datasets.**
   All the transfer work uses REDD, REFIT, UK-DALE, AMPds — research-grade submetered datasets. No
   one has published the transfer curve for a 70-dollar consumer clamp.
4. **Complex multi-stage appliance separation at low resolution with guided labels.** This is the
   actual hypothesis, and I found no prior work claiming it. It is open because it is probably
   false, not because nobody thought of it.

---

## 6. Sources

Open copies actually retrieved and read in full or in part:

- Todic et al., Applied Energy 341 (2023) 121078 — full PDF via Strathprints, University of
  Strathclyde.
- Kelly and Knottenbelt, Neural NILM, 2015 — full PDF via arXiv:1507.06594.
- Real-Time Energy Disaggregation of a Distribution Feeder's Demand Using Online Learning — full PDF
  via arXiv:1701.04389.
- Zhong et al., Transfer Learning for NILM, TSG 2019 — abstract via OpenAlex; repository PDF listed
  at Lincoln eprints was empty on fetch (link rot), so only the abstract and its listed conclusions
  are quoted.

Blocked on fetch (curl and/or managed browser): analog.com, mdpi.com PDFs, ieeexplore PDFs,
sciencedirect, arXiv API (HTTP 406), Semantic Scholar.

Metadata for 804 works harvested from OpenAlex; the 27 core papers are stored with abstracts in
training-approaches-key.json.
