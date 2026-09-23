# FHMM and event matching under session supervision — what the patent, the NIPS paper, and the registry imply

**Context:** Scoping the model-family decision for the post-anchor experiments (the registry's "family B" question): how the two classical families — Hart-lineage event matching and additive factorial HMMs — differ in what they assume, what training they need, and what our K guided sessions buy in each. Written after a direct source check, prompted by the questions "did Hart assume single state?", "is FHMM trained on submeters or mains?", and "can FHMM handle unknown loads?".

**Status:** Research note (AI work, not owner-reviewed). Verification provenance this session:
- **US 4,858,141** (Hart/Schweppe NILM patent) — full text fetched from Google Patents (`patents.google.com/patent/US4858141A/en`); claims below quote it.
- **Kolter & Jaakkola, NIPS 2012** ("Approximate Inference in Additive Factorial HMMs with Application to Energy Disaggregation") — abstract fetched from the official MIT DSpace deposit (`hdl.handle.net/1721.1/115326`).
- **Hart 1992 Proc. IEEE paper** — still unverified; no open-access copy located via OpenAlex. The multi-state-FSM framing remains memory-cited.
- **Signal Aggregate Constraints in Additive FHMMs (2014)** — open-access PDF exists (Lincoln eprints, eprint 30392); not yet mined (no local pdftotext). The sum-constraint row in `analog-problems.md` §3 predates this check.

**Read alongside:** `analog-problems.md` (§2.1 factorial HMMs, §2.7 spike sorting, §4 the borrowing stack), `research-brief.md` §3 (field landscape + the denoised-aggregate trap), `docs/PROBLEM_STATEMENTS.md` §2–§7 (inputs, supervision budget, evaluation contract), and registry files H01, H02, H04, H05, H08, H13.

---

## 0. Short answers

| Question | Answer |
|---|---|
| Did Hart's system use fixed appliance classes? | No — the signature library is open by construction; what is fixed is the behavioral taxonomy (single-state / multi-state / variable / always-on) and the representation template. |
| Is Hart's model a pattern learner + matcher? | Yes — verified in the patent text: cluster analysis of step changes in (real, reactive) power, then ON/OFF pairing logic. No trained model anywhere. |
| Does Hart assume single-state devices? | The event layer assumes each cluster is one switching of *a single appliance* (patent, explicit). The multi-state FSM is **not in the patent** — it comes from the 1992 paper's discussion and stays memory-cited. |
| Is FHMM trained on submeters or mains? | Canon (Kolter & Jaakkola 2012, verified): **mains only, unsupervised**. Submeter-trained per-device HMMs are common practice and an upper bound that violates deployment parity. Ours is a third setting: **session-supervised, mains-only**. |
| Can FHMM detect overlapped devices? | Yes, structurally — overlaps are states inside the joint hypothesis space, resolved by the sum constraint. Limits: sum collisions, identical devices, imputed energy inside overlap windows. |
| Can FHMM handle unknown loads? | Not natively (closed world). The canon itself ships a "robust" component for unmodeled observations (verified) — an absorber, not a reporter. Honest UNKNOWN accounting must be engineered on top; *device-level* discovery of unknowns is the loop's job, not FHMM's. |

---

## 1. What the patent verifies about Hart's machinery

From the US 4,858,141 text (Google Patents fetch, this session):

> "...a digital computer for detecting changes in certain parameters and calculating the net change between steady state signal periods. the computer applies 'cluster analysis' techniques to the change measurements to group them into those associated with the switching ON or OFF of a single appliance. a logic program within the computer analyzes the measured appliance energized (ON) and de-energized..."

Verified structure, in order:

1. **Steady-state detection** on the aggregate; 2. **net-change measurement** per switch (the ΔP/ΔQ edge); 3. **cluster analysis** in the (real power, reactive power) plane — FIG. 8 is described as exactly that plot; 4. a **logic program** pairing ON and OFF edges into appliance instances.

So the "learner" is unsupervised clustering building a signature library incrementally, and the "matcher" is nearest-cluster assignment plus ON/OFF pairing with plausibility logic. The library is open by construction — adopting a new appliance is a data step (observe edges, label the cluster), not an engineering change. The operator-labeling step in Hart's deployment is the ancestor of our §3 confirmation loop.

**What the patent does not contain:** zero hits for "multi-state"; the only "finite state machine" hits are among *later cited patents* (Eaton 2013+). The multi-state-FSM treatment attributed to Hart comes from the 1992 paper's discussion, which no one has verified (repo-wide flag: `research-brief.md` §3.1, `docs/experiments/baseline-ukdale-plan.md`). Until the paper is read, any FSM build "on Hart's authority" rests on memory — verify first.

**Implication for the anchor:** our M0 (threshold + hysteresis + dwell) is Hart-lineage but *dumber than Hart* — no clustering, no ON/OFF pairing, no duration-plausibility checks. "Port Hart properly" (signature library from calibration sessions + event matching with pairing and dwell plausibility) is the honest next rung of family A, and it is supervised where Hart was unsupervised — K sessions name the clusters by construction.

## 2. FHMM training regimes in the literature — three settings, ours is the third

| Setting | Who | Supervision | Deployment parity? |
|---|---|---|---|
| Mains-only, unsupervised | **Kolter & Jaakkola 2012 (verified)**: "separate many appliances almost perfectly **using just the total aggregate signal**"; emissions bootstrapped from the differenced signal; convex inference, no local optima | none | yes — but identity assignment (which chain is which device) is unsolved in-model (label switching) |
| Submeter-trained per-device HMMs | Common practice in HMM/NILMTK-style evaluations and effectively all neural SOTA (mains in, submeter targets; e.g. Neural NILM arXiv 1507.06594) | per-appliance submeters | **no** — runtime has no submeters; upper bound, the exact mistake the registry flagged in the quarantined campaign ("signatures from clean submeter channels") |
| **Session-supervised, mains-only (ours)** | K guided sessions per device; emissions/transition parameters estimated directly from aggregate intervals | K sessions (§3: "the only supervision the method ever gets") | yes by construction |

Key contrast worth pre-registering as an ablation: **unsupervised EM vs session-supervised estimation on the same aggregate.** Unsupervised FHMM can *separate* appliances but cannot *name* them; the sessions buy exactly the naming (and better-initialized emissions). If unsupervised EM matches session-supervised performance, the calibration ritual buys less than assumed — that comparison is H01 in FHMM form. The Parson-line transfer variant (submeter-trained priors refined on aggregate) is the literature's middle ground [memory-cited — verify before relying on specifics].

## 3. What "feature engineering" and "training" mean inside FHMM

Nothing is fed in as discriminative features. The engineering lives in three parameter groups:

1. **Emissions** — per-device state Gaussians (OFF → low mean; ON → μ_d, σ_d; program devices get 3+ states for phases). Emission parameters *are* the appliance profile (client §6: "form deliberately open").
2. **Transitions** — self-transition probability encodes dwell (E[dwell] ≈ 1/(1 − p_stay)); the duration prior from `analog-problems.md` §2.3, made structural.
3. **Observation preprocessing** — the only "features": always-on floor estimation/subtraction, optional TV-1D denoising, rung bucketing (H03).

Mapping the feature list once proposed for "improving detection": power change → emission means + baseline handling; power level → emission means; duration → transition priors; co-occurrence → **model structure, not a feature** (the point of joint inference); rise/fall shape → **not representable** (memoryless emissions) — a stated family limitation.

Training itself is small under supervision: with K sessions, no EM is needed — moment estimation of μ, σ, p_stay from valid sessions (H06 flag gate first; a contaminated session biases μ_d — H12 made concrete). H01's K-curve becomes "sessions until the emission estimates stabilize"; prediction: kettle converges by K ≈ 1–2, washer needs more (phase inventory + low, floor-overlapping levels).

## 4. Overlaps: what joint inference buys and where it stops

- **Mechanism:** the joint state space contains combinations ("A ON + B ON"); the sum constraint scores each joint state by how well its emissions sum to the observation. Overlaps are *in-hypothesis-space*, unlike Hart matching where one combined edge is a confounder. On the UK-DALE slice 2+ appliances are ON about a third of the time [quarantined plan stat], so this is runtime-normal, not an edge case. Transition priors pull apart near-simultaneous onsets with different dwell behavior.
- **Hard limits:**
  1. **Sum collisions** — if μ_A + μ_B ≈ μ_C alone, the posterior is ambiguous and no joint inference rescues it. H04's noise-masking in FHMM form; the mechanism check (per-device levels vs the house always-on floor, plus pairwise sums) predicts *before the build* which overlaps are recoverable.
  2. **Identical/swappable devices** — "two ON" is decodable, "which is which" is not.
  3. **Overlap energy is imputed** — inside a both-ON window, per-device power is the emission means, not measurement; attribution error there is exactly the H01 question about μ-estimate quality.
- **Free product hook:** decoding yields per-device posterior marginals P(device ON at t) and a per-timestep innovation — a principled confidence signal for the §4.1 UNKNOWN threshold, not a threshold hack.
- **Pre-register the claim as a stratum split:** solo vs co-occurring ground-truth episodes, FHMM vs anchor, native cadence and 60 s separately (bucketing blurs simultaneous onsets first — H03 interaction). If the anchor dies on the overlapped stratum and FHMM holds, that is the measured case for family B; if it does not hold, the family-B bet fails cheaply.

## 5. Unknown loads: closed world by default, three mechanisms to fix it

1. **The canon's own absorber — verified:** K&J inference includes "a 'robust' mixture component that can account for unmodeled observations." It keeps the model from hallucinating attribution, but it is an *absorber*, not a reporter — our contract (§7: UNKNOWN mandatory, residual printed first; H05 books-close) requires tracking that component's energy share per home as the residual line.
2. **Confidence-based rejection — free from the decoder:** low posteriors or large innovation demote a timestep to UNKNOWN instead of forcing attribution (§4.1 confidence → UNKNOWN threshold; same logic as the spike-sorting analog, `analog-problems.md` §2.7: residual → unknown cluster, alarm instead of assign).
3. **Device-level discovery is out of FHMM's scope and should stay out:** it can reject a timestep's unexplained power; it cannot notice "this recurring unknown has kettle-shaped episodes at 07:00 daily." Discovery is the library-growth loop — Hart's operator labeling, our §3 confirmations, H13 mark curation. Composition: recurring UNKNOWN mass → open question to the user → confirmed pattern → new enrollment → back to the class-adoption question (§2 above).

Reactive-power extensions of FHMM exist (AFAMAP 2017, Applied Energy — active+reactive emissions; existence verified via OpenAlex this session) — exactly the H08 bet: aux channels make the emission space 2-D and attack level-identity confusion that W-only FHMM cannot. Parked until live Shelly data, per the registry.

## 6. Consequences for Experiment 2 design

- **Family arms to pre-register** (same instrument, same §7 contract): (a) port-Hart event matching (library + pairing + dwell plausibility, supervised from sessions); (b) session-supervised FHMM (this note's §3); (c) ablation: unsupervised EM, zero sessions (H01 in FHMM form). Rules anchor = the floor.
- **Mechanism check first** (§4): emission levels vs always-on floor and pairwise sums — decides which overlaps are recoverable and whether more joint inference can help at all.
- **Overlap-stratified metrics** as a named sub-analysis (§4), not prose claims.
- **Verification follow-ups before any of this is cited as [reviewed]:** read Hart 1992 Proc. IEEE (no OA copy; IEEE access needed) for the actual multi-state/FSM discussion; mine the SAC-2014 PDF (Lincoln eprint 30392) for the sum-constraint formulation; verify the Parson transfer line.
