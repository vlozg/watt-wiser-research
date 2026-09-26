# Transfer-route applicability audit — code, weights, and fit to our problem statement

**Created:** 2026-09-26. Companion to `transfer-learning-sota.md` (the SOTA review, 847 lines).
**Grounding:** `docs/PROBLEM_STATEMENTS.md` — if any verdict here disagrees with it, that doc wins.
**Method:** every artifact claim below was re-checked on 2026-09-26 against the Hugging Face Hub API
(model + dataset search and model cards), the GitHub REST API (repo metadata, config listings), and
the papers' own HTML for code links. Raw evidence: `research-logs/nilm-transfer-sota/artifacts_audit/`
(18 paper HTMLs + link scans, HF API captures, GitHub repo/search captures). Tags: `[hf]`
`[repo]` `[abs]` `[full]` `[reviewed]` `[quarantined]` `[owner]`.

---

## 0. Bottom line

| # | Route | Best artifact | Code | Weights | Fits our problem | Verdict |
|---|---|---|---|---|---|---|
| 1 | Benchmark + models | **nilmbench** + nilmtk-contrib + nilmtk `[repo]` | yes (16 PyTorch models, T1/T2/T3 TOML configs confirmed on disk) | **no** — trains per task | yes — 60 s/15 min protocols match the deployment assumption | **USE — E1/E2 harness** |
| 2 | Transformer backbone (T2 winner) | NILMFormer code `[repo]` | yes | **no** | yes (aggregate, low-frequency) | **USE — self-train** |
| 3 | Prompt/foundation NILM | FM4NILM `[abs]` | **no** | **no** | paradigm only | **MONITOR** |
| 4 | Pretrained energy FM | **EnergyFM** `[hf]` — `energy-ttm` (dl 163), `energy-tspulse` (dl 105) | partial | **yes** | **no** — hourly forecasting/analytics, not disaggregation | **REJECT as backbone; monitor** |
| 5 | LLM-adapter NILM | `virtsion/nilmformer_*` `[hf]` | no | yes (Llama-2-7b LoRA) | **no** — empty template cards, no provenance | **REJECT (unusable provenance)** |
| 6 | SSL low-frequency | Chen et al. 2022, arXiv 2210.04176 `[abs]` | **no** (0 GitHub hits; no link in paper) | no | **yes — closest match to option B** | **ADAPT — re-implement (E3)** |
| 7 | Source-free DA + SSL | IEEE TIM 2024 `[abs]` | unknown (paywalled) | no | stricter variant of 6 | MONITOR |
| 8 | Unsupervised (state/BSS/accounting) | methods only; no code links found `[abs]` | mostly no | no | selective — per class, not whole-home | **ADAPT selectively** |
| 9 | Few-shot / exemplar conditioning | no artifact (FM4NILM); our own enrollment design | no | no | **yes — this IS our product loop** | **BUILD (in-house)** |
| 10 | Active learning for calibration | `github.com/anonn23/anon` `[repo]` (anonymized) | yes | no | yes — picks which devices to calibrate | **ADAPT** |
| 11 | Continual learning (low-frequency) | Lan et al. 2025 x2 `[abs]` | not found | no | as specification; not as v1 dependency | **SPEC now, MONITOR methods** |
| 12 | Solar / PV injection | DualNILM toolkit + HF dataset `[hf]` `[repo]` | yes (MIT) | data | yes — BTM solar eval | **USE** |
| 13 | Grid/power FMs (PowerPM, PowerFM, GridFM, FETS) | weights exist for some | yes | some | **no** — grid forecasting, not appliance-level | REJECT for NILM |

Five load-bearing conclusions:

1. **There is still no public pretrained NILM/disaggregation checkpoint.** Every Hugging Face hit for
   "NILM" is either an unattributed Llama-2 LoRA adapter set (empty template cards) or junk. The only
   released *energy* weights (EnergyFM) are **hourly** meter analytics. So the backbone is **on us to
   train** — now verified against the artifact registries, not inferred from paper absence.
2. **The benchmark and 16 model implementations are runnable today** (nilmtk 952 stars, nilmtk-contrib
   144 stars, nilmbench with typed `tasks.toml`), but **weights are not shipped** — they are
   per-task training jobs. "Use a pretrained model" therefore means "run our own training", which is
   what E1/E2 already budget for.
3. **Our product is open-set and few-shot; most of the literature is closed-set and label-rich.**
   The problem statement requires, per event, *which enrolled device* is running **or UNKNOWN**
   `[reviewed]`. Almost no published NILM work has an UNKNOWN class. That single difference
   reshapes which research applies (§3.5): few-shot exemplar conditioning and open-set confidence are
   the core, full-home disaggregation is the wrong target.
4. **The 60 s-class deployment assumption makes NILMBench directly comparable** — better than stated
   in the SOTA review §11.1 caveat (a), which assumed a 1 s deployment. Live 1 Hz telemetry is the
   ceiling, not the product assumption. The 1 s edge-precision question stays open but is no longer a
   comparability blocker.
5. **The geography gate is our real data risk**, and it is a **data-collection** item, not a method
   item: public corpora are UK/EU 230 V; REDD is US but 2011-era and short; Pecan Street is paywalled.
   Our fleet is the only US-native 1-channel aggregate corpus we control (§5).

---

## 1. The gates — what "applicable" means here

Derived from `PROBLEM_STATEMENTS.md` (the grounding doc) and the reviewed hardware findings:

- **G1 signal gate.** Input is one aggregate series; the ADE7953 reports computed RMS/active/
  reactive/apparent/PF. **No waveform, V-I, harmonics or transient data at any poll rate** — a
  metering-IC fact, not a sampling fact. The entire high-frequency/V-I branch (Toirov 2025, SimCLR
  V-I 2026, PLAID V-I few-shot, event-transient methods) is **permanently out**, at any poll rate.
- **G2 cadence gate.** Deployment logging is a 60 s-class assumption `[quarantined]`; live
  telemetry approx 1 Hz `[reviewed]`; 1 s-class public corpora (REDD, ECO, GREEND; UK-DALE
  6 s) align with the telemetry ceiling. Higher Tier-1 rates buy **event-edge precision only** (G1
  caps features).
- **G3 label gate.** Per enrolled device: identity/type metadata plus at least 3 **guided button-press
  sessions** `[owner]`, then a user-confirmation feedback loop. That is a **support-set
  (few-shot)** design, not a supervised-training design. Source labels for transfer come from
  `data/gold_annot/` and the public corpora; the deployed fleet provides **unlabeled**
  aggregate.
- **G4 power gate.** 30 VA no-load blind spot; ±5% below approx 230 W `[reviewed]`. Weak
  multi-state classes are quantized away — and NILMBench2026 independently names the dishwasher the
  worst-generalizing load. Gate and field agree.
- **G5 geography gate.** Product is US (110-120 V split-phase). UK-DALE, REFIT, ECO, GREEND are UK/EU
  230 V. NILMBench2026's T3 documents that cross-country zero-shot **collapses bidirectionally**.
- **G6 open-set gate.** The output contract is per-event attribution **or UNKNOWN** `[reviewed]`.
  Closed-set disaggregation metrics (per-appliance F1 over a fixed label space) do not measure the
  product contract; the literature has almost nothing for G6.

A route is **applicable** only if it passes G1 and G6 as-is, or can be **tweaked** into them at
acceptable cost (§4), and only if its artifacts exist (§2).

---

## 2. Artifact audit — what can actually be run

### 2.1 Code that exists and is runnable today `[repo]`

| Artifact | Stars | Pushed | What it gives us | Weights? |
|---|---|---|---|---|
| `nilmtk/nilmtk` | 952 | 2026-07 | dataset access, meters, metrics — the data layer of E1 | n/a |
| `nilmtk/nilmtk-contrib` | 144 | 2026-08 | the 16 model implementations (PyTorch) behind NILMBench2026 | **no** |
| `nilmtk/nilmbench` | 2 | 2026-07 | T1/T2/T3 runner; `configs/{tasks,datasets,metrics,runtimes}.toml`; `results/published/` | **no** |
| `adrienpetrali/NILMFormer` (EDF-Lab mirror, 4 stars) | 4 | 2026-06 | the T2-winning architecture | **no** (none on HF) |
| `github.com/anonn23/anon` | - | - | **Benchmarking Active Learning for NILM** (arXiv 2411.15805) code — anonymized | no |
| `MathAdventurer/PV-Augmented-NILM-Datasets` + HF dataset `[hf]` | - | 2026 | PV-injection toolkit (NREL irradiance, temperature effects), MIT, NILMTK-compatible; REDD/UK-DALE variants | n/a (data) |
| In-house: `baseline_lib.py`, `fhmm_lib.py`, `data/gold_annot/` | - | - | our source-label + FHMM scaffold | our own |

Data staging: REDD/UK-DALE/REFIT HDF5 conversions are **not redistributed** by nilmbench; the runner
verifies user-staged files against recorded SHA-256 digests. A convenience `Pybunny/nilmbench-ukdale`
HF dataset exists (dl 84) `[hf]` — **verify its digests before any use**; provenance unverified.

### 2.2 Weights that exist `[hf]` — and what they are NOT

- **EnergyFM** (`EnergyFM/energy-ttm` dl 163; `EnergyFM/energy-tspulse` dl 105):
  IBM TTM/TSPulse backbones, pretrained on approx 1.26 billion **hourly** records; tasks are
  short-term load and day-ahead **forecasting**, anomaly detection, imputation, classification. **No
  disaggregation task, no appliance-level output.** At 1 h resolution every event our product cares
  about is gone.
- `virtsion/nilmformer_*` (12 repos): **Llama-2-7b PEFT/LoRA adapters** (`base_model:
  meta-llama/Llama-2-7b-chat-hf`), template-empty cards, no paper link. Highest downloads
  approx 11. Something LLM-prompt-NILM exists, but **provenance is unverifiable** — unusable as a
  foundation, recorded here so it is not re-discovered as promising.
- IBM `granite-timeseries-ttm-*`: generic TSFM weights (forecasting head), flexible
  frequency — a possible **encoder pre-initialisation** in principle, but adapting a forecasting TSFM
  into a disaggregator is a research project, not a plug-in. Deprioritised vs self-training on
  in-domain corpora.
- Grid FMs (PowerPM approx 250M, PowerFM collection, GridFM/GridSFM): real weights, **wrong task and
  wrong signal** (grid nodes, not household aggregate).

**Net: zero public weights for household-level disaggregation.** FM4NILM's "foundation model" remains
a paper, not an artifact. The SOTA review's claim survives the audit — now verified against the HF +
GitHub registries rather than inferred.

### 2.3 Papers with **no code link found** (paper HTML checked 2026-09-26) `[abs]`

Chen et al. 2022 SSL (2210.04176); RefQuery (2603.04998); FM4NILM (2609.23146, page did not render —
still no repo); prompting LLMs training-free (2505.06330); few labels are all you need (2506.05895);
aggregate recomposition (2609.18315); Egarter 2014 (1412.2877); UNILM (1907.06299); Khodayar 2018
(1809.03534); Zufferey 2021 (2104.03120); Kim 2022 ICA (2209.09165); Bayesian surprise (2009.07756);
Toirov 2025 (2506.06637); FedNILM (2106.07751); federated meta-learning (2204.06767); FETS
(2604.22328). GitHub search for "NILM self-supervised": **0 repositories**. The SSL group's only
public code is `MingjunZhong/NeuralNetNilm` (78 stars, seq2point era, 2020) — **not** the
SSL method.

---

## 3. Route-by-route critical assessment

### 3.1 SSL — verdict: ADAPT (re-implement; no artifact to reuse)

**Exists:** Chen, Zhao, Zhong, Luan 2022 (2210.04176) — pretext pre-training on **target aggregate
only**, supervised heads from **source** labels, no target labels required `[abs]`. No code
anywhere.

**Why it fits us:** input = aggregate only (G1 pass); pretext task is cadence-agnostic (G2 fine);
requires **no target labels** (G3 satisfied by design); eval protocol is T2-style cross-house (G5 is
our problem, not disqualifying). It is the only published method whose *problem shape* equals ours:
scarce target labels, aggregate-only.

**What breaks without tweaks:** (a) their pretext ("map aggregate sequences to derived
representatives") is under-specified without code — we must choose and justify a pretext; (b) their
downstream is closed-set supervised fine-tuning — no UNKNOWN head (G6); (c) their corpora are UK
230 V (G5); (d) nothing handles the 30 VA floor.

**Tweaks (concrete):**
- **T-SSL** pretext = masked-window reconstruction + contrastive (AMDA-style aggregate recomposition
  as augmentation); validate the pretext itself by linear-probe on `gold_annot` before any
  fine-tuning.
- **T-HEAD** heads per **enrolled device** + a shared UNKNOWN/confidence head (G6).
- **T-EXEMPLAR** per-home adaptation = freeze encoder, fit heads on the button-press support set
  (few-shot), with per-home normalization statistics (NILMBench's adaptive-denormalisation direction).
- **T-CORPUS** pre-training corpus = public UK/EU + REDD + **our fleet aggregate** (opt-in) — the
  fleet is what makes it US-native (G5 mitigation).

**Cost:** E3-scale (one pre-training run on approx 10^8-10^9 samples at 1-60 s cadence is feasible
with a TTM-class-size model). Highest-value build item in the plan.

### 3.2 Transfer learning proper (frozen backbone + per-home adaptation) — verdict: USE, with self-trained weights

- **Backbone:** train on public corpora via the nilmtk-contrib/nilmbench models; **NILMFormer's
  z-normalization + TokenStats/ProjStats** is the transfer mechanism the T2 evidence endorses
  (adaptive denormalisation is per-home and label-free). No weights exist — training is on us (§2.2).
- **RefQuery** (query-conditioned scaling) `[abs]`: no code; concept is cheap to prototype
  on a frozen backbone; unverified — prototype only after E2 shows exemplars help.
- **Few-shot exemplar conditioning (FM4NILM idea, no artifact):** our enrollment sessions **are** the
  support set. This is not a paper to import — it is the product loop restated as a modelling choice.
  Build it in-house on top of the SSL/frozen backbone.

### 3.3 Unsupervised — verdict: ADAPT selectively (per class, and as a discovery mechanism)

**Exists:** no code links for any of the eight method papers (§2.3). What remains transferable is
**design patterns**, implementable in-house (FHMM infra already exists):

- **Egarter-style online state learning** at 1 Hz for the always-on/periodic class (fridge): no
  labels, progressive model updates — fits the product's **device-discovery** moment ("we think you
  have a fridge — enroll it?") better than it fits attribution. **T-DISC:** use unsupervised state
  discovery as the *enrollment proposer*, so the user's calibration effort is spent only where it pays.
- **UNILM's probabilistic knapsack** as an **energy-accounting layer**: per-device energy estimates
  should sum to (aggregate − unattributed residual). This gives a label-free **sanity monitor** and
  the residual series that defines UNKNOWN `[abs]` — directly supports the G6 contract.
- **Zufferey (minute-range water heater), Kim (15-min ICA HVAC):** these target the **1-min onboard
  log / billing line**, not real-time feedback. Park them for the utility-scale product line; do not
  spend them on the 60 s real-time path.
- **In-house FHMM-EM (unsupervised variant):** no external code needed (`fhmm_lib` exists);
  respect the H14 lesson on washer/dishwasher mis-specification — constrain states to observed step
  counts from enrollment sessions.
- **Critical limit:** every successful unsupervised result is single-appliance or category-level
  (SOTA review §11.4). Whole-home unsupervised multi-class at 60 s remains an open wall — the
  dishwasher result (T3) and our H04 agree. **Do not promise label-free whole-home.**

### 3.4 Continual learning — verdict: SPEC now, method-level MONITOR

Map the three places "continual" could bite in our problem statement:

1. **Per-device profile updates** (user confirmations -> profile improvement, `[reviewed]`):
   head-level updating on a frozen encoder. With additive per-device heads there is **structurally no
   catastrophic forgetting** — old heads are untouched. No CL research needed for v1.
2. **New enrollments over time** (class-incremental heads): same story **if** the encoder stays
   frozen — the "freeze the backbone; add a head per appliance class" spec from SOTA review §11.3.
   Analytic-CL-style closed-form head updates (Lan 2025) would fit, but no code is found
   `[abs]`; the spec is adoptable without the method.
3. **Backbone-level continual pre-training** as the fleet corpus grows: this is where published CL
   would matter (Toirov-style `[abs]` — high-frequency, not portable; replay/rehearsal or
   parameter-isolated methods). Defer to an E5-class experiment **only after** E3 proves the SSL
   backbone is worth maintaining.

**Honest answer to "can we apply CL given our problem statement?"** Yes — but the *problem statement*
mostly dissolves the need: per-home instances with per-device heads on a frozen encoder are
class-incremental by construction. Adopt now the **constraint** (never re-train the encoder per home
or per device; log every confirmation as a first-class training example for later continual
pre-training). Method-level CL research stays on the monitor list.

### 3.5 Open-set / UNKNOWN — the gate the literature fails

Almost no reviewed work models UNKNOWN. What we can assemble from the audit:

- **Bayesian surprise as an overfitting/performance guard** (Jones & Klemenjak 2020
  `[abs]`) — a label-free confidence signal; repurpose as the UNKNOWN trigger.
- **Knapsack energy residual** (UNILM pattern) as the unattributed-energy estimate.
- **User confirmations** as the ground-truth stream that calibrates the UNKNOWN threshold per home
  (the product's own active-learning loop).
- Open-set recognition for NILM specifically is thin — flag as our **differentiator and
  responsibility**: extend the T1/T2/T3 metrics with an open-set protocol (per-enrolled-device F1 +
  UNKNOWN precision/recall) for our own eval; consider contributing it upstream.

### 3.6 Adjacent-but-not-applicable (recorded so nobody re-litigates)

EnergyFM (hourly analytics); TTM base (forecasting TSFM); PowerPM/PowerFM/GridFM/GridSFM/FETS (grid
forecasting); Toirov + SimCLR V-I + PLAID (G1 kill); DualNILM (applicable **toolkit**, §2.1, not a
backbone); virtsion adapters (provenance).

---

## 4. The tweak ledger — what each adoption actually costs

| Tweak | What we change | Effort | Unblocks |
|---|---|---|---|
| T-SSL | re-implement Chen 2022 pretext on aggregate-only; linear-probe validation first | E3-scale (weeks) | zero-label per-home adaptation |
| T-NORM | per-home z-normalization + learned de-normalization (TokenStats pattern) | small | cross-house drop mitigation, no labels |
| T-HEAD | per-device heads + UNKNOWN head on frozen encoder; heads added per enrollment | small | product contract (G6) + CL-as-spec |
| T-EXEMPLAR | button-press sessions as support set for head fitting / exemplar conditioning | small | E2 sweep; the calibration product loop |
| T-AL | active-learning selection of **which devices** to ask the user to calibrate | small | calibration UX; `anon` code exists |
| T-ACCT | UNILM-style energy accounting as residual/UNKNOWN monitor | small | G6 contract; drift detection |
| T-DISC | unsupervised state discovery -> guided enrollment proposals | medium | label-acquisition flywheel |
| T-PV | PV-injection toolkit on UK-DALE/REDD for BTM-solar eval | small | solar robustness evidence |
| T-60S | adopt nilmbench at 60 s; publish our 1 s extension as a contribution | medium | comparability + novelty |
| T-CONT | replay + parameter-isolated continual pre-training on fleet corpus | E5-class, later | long-horizon backbone maintenance |

---

## 5. Data-collection asks — feedback to the product team

What we could collect, what each item unlocks, and the burden. **A1 and A2 are the two that change
what is methodologically possible**; the rest are supporting.

| # | Ask | What it unlocks | Research route it feeds | Burden | Priority |
|---|---|---|---|---|---|
| A1 | **Retain unlabeled approx 1 Hz aggregate** per consenting home (rolling window, opt-in) | the only **US-native, in-domain** pre-training corpus that exists; also TTA and drift monitoring | SSL (E3), TTA, continual pre-training | zero user burden; approx 0.1-0.2 GB/home-year uncompressed, far less stored parquet | **P0** |
| A2 | **Guided button-press sessions** (already specified, >= 3/device) + which-device selection via AL | per-home support sets for few-shot heads; E2's N = 0/1/3/10/30 sweep | few-shot/exemplar, active learning | minutes per device | **P0** |
| A3 | **1-min onboard log retention** (longer windows) | benchmark-comparable T1/T2/T3 eval at 60 s; utility/billing line (Zufferey/Kim regime) | harness, unsupervised-low-freq | nil (device-native) | P1 |
| A4 | **User confirmations as labels** — store them as first-class training data | the continual/online loop; UNKNOWN calibration | CL-as-spec, open-set | nil (existing loop) | P1 |
| A5 | **CT2 stays evaluation-only** (already the position) | cross-check instrumentation, not a modelling input | eval only | nil | keep |
| A6 | **Tier-1 higher poll rate** (ESPHome, tens of Hz) | event-edge precision/latency only — **no new feature classes** (ADE7953 has no waveforms) | edge timing, not ML | reflash effort | P2 — deprioritised for NILM accuracy |
| A7 | **Optional: license a US labeled corpus** (Dataport/Pecan Street class) | an external US source-corpus for cross-country eval (our T3 direction) | transfer eval | money + legal | P2 — gate on E2 failing UK->US transfer |
| A8 | **Opt-in fleet corpus contribution** consent flow | scales A1; the flywheel that makes the backbone an asset over time | SSL, CL | UX copy + policy | P1 |

Sequencing note: A1 needs **no new product behaviour** — only retention policy and consent copy — so
it should be decided **before** the fleet grows; a backbone trained on retained data is only as good
as what was kept.

---

## 6. What this audit settles

- **No external checkpoint will rescue the backbone** — self-training on public + fleet data is the
  plan, and the plan already says so. E1/E2 unchanged in substance; E3 now has a named method to
  replicate (Chen 2022) with **no code dependency**.
- **Few-shot/exemplar conditioning is in-house work** (FM4NILM is a paper, not an artifact) — but the
  product's enrollment loop is exactly the support-set design it describes, so the concept is
  low-risk even with no external code.
- **Continual learning is a design constraint for v1** (frozen encoder + additive heads + retained
  confirmations), and a research item only for backbone maintenance later.
- **Unsupervised methods are scoped**: discovery proposals, energy accounting, and the 1-min billing
  line — not whole-home label-free disaggregation.
- **The geography gate is the one place where more data beats better methods** — A1/A8 are the
  product-team decisions that most directly change what is achievable.

**Caveats.** Artifact checks are point-in-time (2026-09-26) — this field released EnergyFM and
DualNILM artifacts within the review window, so **re-check quarterly**. Paywalled items (IEEE TIM
source-free DA; MDPI Lan 2025) were not code-audited. Most method assessments remain abstract-level
`[abs]`; the `[full]` tag applies to NILMBench2026 only. The virtsion HF family
is recorded as observed-but-unverified provenance, and nothing in this doc should be cited on its
basis.
