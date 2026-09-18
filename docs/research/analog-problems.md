# Analog Problems: Fields That Attack the Same Input Shape as a Power Time Series

**Context:** Follow-on to `nilm-visual-reading.md`. The Shelly emits a scalar power series and nothing else — no waveform, no V-I trajectory, no spectrum. That closes two of the four visual primitives and raises the real question: is a low-rate scalar series with this structure a known, solvable object anywhere else, and what can be imported?
**Status:** Research note. Every load-bearing citation was verified via OpenAlex this session (DOIs in the Appendix); Hart 1992 and Page 1954 are cited from memory and flagged.
**Read alongside:** `nilm-visual-reading.md` (the four visual primitives), `training-approaches.md` (training approaches of the 26 ablation papers — the complementary, method-side view), `repo-review.md` §11 (what the hardware actually emits).
**Short answer:** Yes — the shape is a named object in at least six other fields. Two of them (changepoint statistics, factorial HMMs) have machinery importable in an afternoon, and one of them — single-channel speech separation — is your own home field, and it is the *harder* instance of the same class. What no import can do is resurrect information the sensor never captured.

---

## 0. The shape, written down

The series the Shelly produces is:

```
y_t  =  s_1,t + s_2,t + ... + s_K,t  +  eps_t
```

with K of order 2–4 appliances of interest plus a nuisance term. Each `s_k,t` has four properties, and these properties — not the fact that it is electricity — are what make the problem what it is:

1. **piecewise-constant** — appliances hold a level for minutes to hours (kettle about 3 min ON; fridge compressor median ON 1,191 s in our UK-DALE slice), so the signal is a staircase, not a wave;
2. **discrete states** — most appliances are ON/OFF; multi-state ones (washing machine) are short ordered chains of levels;
3. **sparse transitions** — about 111 genuine transitions/day in the UK-DALE slice, versus 715.7 aggregate steps above the 30 W threshold: 6.4 times more edges than events, so most edges are noise or overlap artifacts;
4. **exact additive mixing** — the sum constraint holds to the watt at every instant (verified on the synthetic set: max VA arithmetic error 0.0217), and the mixing operator is the identity. There is no reverberation, no filter, no unknown channel.

That is the formal object: **an additive factorial state-space model observed through a single scalar channel.** "Factorial" because the hidden state is a tuple — state of appliance 1 through state of appliance K; "additive" because the observation is the sum of the per-chain emissions.

This framing is encouraging rather than deflating, and the reason is your own field. Single-channel speech separation — one microphone, several speakers — is the same class with a *worse* instantiation: continuous dense sources, unknown count, no structure. It went from "hopeless" (the pre-2015 consensus) to "solved well enough to ship" not by sharpening separation mathematics but by learning strong source priors. Power has the easier instance of the class: sources are few, known from calibration, discrete, and mostly constant.

## 1. What remains open and what is closed

With a scalar power series, exactly three information channels are available:

| Channel | What it contains | Where it appears in the visual guide |
|---|---|---|
| **Temporal structure** | step times, dwell durations, cycle periods, duty cycles | Figs 1–4 |
| **Magnitude structure** | level heights, step sizes, their distributions | Fig 4 (b)(c) |
| **Combination structure** | which subsets of known appliances best explain the observed sum | Fig 4 (d) |

Closed: waveform shape (Figs 5–6) and spectrum (Fig 7) — the ADE7953 exposes no waveform register, so no transform can synthesize them.

Every method borrowed below lives entirely inside the three open channels. Worth stating plainly before any borrowing: **the imports change what you do with the data, not what the data is.**

## 2. Nine fields, ranked by closeness

### 2.1 Additive factorial HMMs — the exact formalization (NILM's own)

**What it is.** Ghahramani and Jordan defined factorial HMMs in 1997 ("Factorial Hidden Markov Models", *Machine Learning*; 1,186 citations): K independent hidden chains observed through one emitted combination. Kolter and Jaakkola imported the machinery into NILM ("Approximate Inference in Additive Factorial HMMs with Application to Energy Disaggregation", NIPS 2012; 462 citations), adding a sparsity prior and mean-field inference. A 2014 follow-up adds *signal aggregate constraints* — the requirement that inferred signals sum to the observation, which is exactly the physics.

**The shared object.** Identical. This is not an analogy; it is the formalization of the problem.

**What to borrow.** The generative model itself: per-appliance transition matrices, emission distributions on power, duration priors; an observation model that is the *sum* plus noise; then exact inference. At K = 2–4 the joint state space is 2^K, i.e. 4 to 16 states — small enough for **exact** Viterbi, no approximations needed. Kim et al. 2011 ("Unsupervised Disaggregation of Low Frequency Power Measurements", SIAM SDM; 639 citations) supplies the low-frequency, duration-aware variant, which is precisely the Shelly's regime. The online HMM-sparsity line (IEEE TSG 2015, already catalogued in `training-approaches.md`) is the real-time version.

**What does not transfer.** Nothing structural. The practical limits sit elsewhere: priors come from the calibration session, so model quality is bounded by calibration quality, and the 30 VA floor is below every model's reach.

### 2.2 Single-channel speech separation — your home field, and the *harder* instance

**What it is.** One microphone, several speakers. The pre-2015 consensus was that this is underdetermined and near-hopeless classically. Two papers changed it: permutation invariant training (Yu et al., ICASSP 2017; 884 citations) removed the label-permutation failure, and Conv-TasNet (Luo and Mesgarani, IEEE/ACM TASLP 2019; 2,098 citations) showed that a fully learned time-domain encoder-mask-decoder beats classical masking. The lesson: **the separation operator is not where the information lives; the learned source prior is.**

**The shared object.** One additive mixture of per-source signals. The mixing operator is the identity in *both* fields — speech waveforms add in the air exactly the way powers add at the meter.

**What to borrow — and why power is easier.**

| | Speech, single mic | Power, Shelly |
|---|---|---|
| Sources | many, unknown count | 2–4, known from calibration |
| Source structure | continuous, dense | discrete states, long dwell |
| Mixing | identity (additive) | identity (additive) |
| Priors available | ~100,000 hours of speech | hours of calibration |
| Overlap | effectively always 2+ talking | 2+ ON only 32.6% of time |

Two thirds of the time in the UK-DALE slice, zero or one appliance is ON. In a two-speaker cocktail party it is effectively always. That is the whole difference in one number.

**What does not transfer.** The deep-net route at your data scale. Seq2point — the direct speech/NMT import into NILM ("Sequence-to-Point Learning with Neural Networks for Non-Intrusive Load Monitoring", AAAI 2018; 546 citations) — was trained on UK-DALE and REDD, not on three calibration hours. At your scale, priors-first beats nets-first; the transfer-learning route for small data is covered in `training-approaches.md`.

### 2.3 Patch-clamp ion-channel recordings — biophysics solved "one noisy scalar, discrete hidden states" in the 1980s

**What it is.** A patch clamp records the current through one membrane patch: a noisy scalar that flips among a handful of discrete conductance levels as channels open and close. The field's answer was HMM idealization — fit a hidden Markov model to the scalar current, infer the state sequence, then extract *kinetics*: open-time and closed-time distributions. Verified anchor: "Applying Hidden Markov Models to the Analysis of Single Ion Channel Activity", *Biophysical Journal*, 2002.

**The shared object.** Exactly yours: a scalar sum of discrete-state chains plus noise. The differences are timescale (milliseconds versus minutes) and state count.

**What to borrow.** Two things, both cheap. First, **dwell-time distributions as priors** — an appliance's ON/OFF durations are not free parameters to infer per event; they are physics. A fridge compressor's ON time is set by thermostat hysteresis and thermal mass; treating 1,191 s as a prior rather than re-inferring it is the patch-clamp move. Second, **kinetic schemes for multi-state appliances** — a washing machine program is a chain of states with *allowed transitions*, not an arbitrary level sequence; biophysics formalizes this as a state diagram with transition rates. This is also the principled answer to the calibration document's duration-only discrimination problem: kettle and heater both draw about 2,100 W and separate not on power but on dwell (240 s versus 1,800 s) — a duration prior makes that separation principled rather than hand-tuned.

**What does not transfer.** Their inference machinery for *dense* events — transitions milliseconds apart, dead-time corrections. Your transitions are minutes apart, so the hardest part of their method is irrelevant to you; the import is the priors, not the code.

### 2.4 DNA copy-number segmentation — the same statistical object with the axis relabelled

**What it is.** Array-CGH measures DNA copy number along a chromosome: a noisy scalar, piecewise-constant along a 1-D coordinate, with steps at segment boundaries. Replace "chromosome coordinate" with "time" and it is your power series. The field's two workhorses: circular binary segmentation (Olshen et al., *Biostatistics* 2004; 2,444 citations) and the fused lasso (Tibshirani et al., JRSS-B 2005; 2,818 citations) — penalized least squares with a total-variation penalty, i.e. "fit piecewise-constant curves with few steps".

**The shared object.** Piecewise-constant scalar plus noise plus few breakpoints. Identical mathematics; different axis label.

**What to borrow.** The **total-variation (fused-lasso) denoiser** as the zero-effort first step on any Shelly series: it suppresses noise-floor wiggle while provably preserving step edges — the exact opposite of a moving average on a staircase. One pass of TV-1D before any detection step attacks the 715.7-steps/day figure directly, because most of those edges are noise. Also available: CBS-style exact breakpoint lists.

**What does not transfer.** Genomics solves *segmentation*, never *assignment*: it has thousands of segments and no need to name a source. The borrow is the denoiser and the breakpoint finder, not the pipeline.

### 2.5 Changepoint detection — the detection half as a mature engineering discipline

**What it is.** Step detection in noisy series is its own field with its own canon: CUSUM (Page, *Biometrika* 1954; cited from memory), PELT (Killick, Fearnhead and Eckley, JASA 2012; 2,619 citations — *exact* optimal detection at linear cost), Bayesian online changepoint detection (Adams and MacKay, arXiv:0710.3742 — online, produces a run-length posterior instead of hard breakpoints), and Bai-Perron structural breaks in econometrics. Verified entry points: the `ruptures` survey (Truong, Oudre and Vayatis, *Signal Processing* 2019; 1,347 citations) and a benchmark evaluation ("An Evaluation of Change Point Detection Algorithms", 2020).

**The shared object.** Steps in a noisy scalar — the detection half of your problem, solved and packaged.

**What to borrow.** Everything here is directly implementable: `ruptures` (Python) exposes PELT, binary segmentation, dynamic programming and kernel methods behind one API; PELT is O(n) so it runs comfortably on a 30-day Shelly history; BOCPD is the online variant if you later want live detection rather than batch analysis. This is the layer to build **first**: it needs no calibration, and it turns the raw series into a candidate-event list that every later stage consumes.

**What does not transfer.** A changepoint detector finds steps; it cannot name them (that is §2.1's job), and it fires on overlap artifacts — the 6.4 times edge inflation is precisely what it must not be left to interpret alone.

### 2.6 Exoplanet transits — "find box functions in a noisy series", named BLS

**What it is.** Kepler and TESS photometry: a star's brightness dips by a fixed depth for a fixed duration, repeatedly. The box least squares algorithm (Kovács, Zucker and Mazeh, *A&A* 2002; 989 citations) searches over (period, duration, depth) box functions fitted to the series — literally "find the best box-shaped event".

**The shared object.** An appliance ON-event *is* a box function: level P for duration T. A kettle is a box of about 2,900 W for about 3 min; a fridge is a periodic box.

**What to borrow.** Box-shaped event templates as a detection prior — search over (depth, duration) rather than thresholding instantaneous power — and **periodicity search for cycling loads**: fridge and water-heater cases are genuinely periodic, and a BLS-style scan recovers compressor periods and duty cycles cheaply and robustly.

**What does not transfer.** Most appliance events are stochastic, not periodic — BLS's power comes from repeated transits. Use it where periodicity exists; use plain box templates elsewhere.

### 2.7 Spike sorting and EMG decomposition — additive superposition of repeated templates

**What it is.** An extracellular electrode in the brain records the *sum* of action potentials from many neurons — additive superposition of repeated, stereotyped waveforms. The field sorts spikes by template matching and greedily subtracts matched templates to reveal what remains (the logic of matching pursuit). Surface EMG decomposition is the same problem for muscle.

**The shared object.** Additive mixture of repeated source events, one channel.

**What to borrow.** The inference pattern rather than the algorithm: build a template library from calibration, match-and-subtract events from the series, and treat the **residual as a signal** — a large unexplained residual after subtracting known appliances *is* the UNKNOWN class, detected rather than force-assigned. This gives the brief's "explicit UNKNOWN state" a mechanism instead of a label.

**What does not transfer.** The waveform templates themselves. Turn-on transients in power are only observable at roughly 1 Hz or faster; at 60–300 s sampling the transient is at most two samples wide. The library-and-subtract pattern applies to *steps* (from §2.5), not shapes — the closed primitives of `nilm-visual-reading.md` §5–7.

### 2.8 Music transcription — the piano roll is the answer key you are trying to reconstruct

**What it is.** Polyphonic transcription: one audio mixture, superimposed notes, output is a piano roll — a binary matrix over (note x time). That matrix is *exactly* the appliance x time state matrix NILM wants to infer, with the same underdetermination.

**The shared object.** Event-structured additive mixture with a discrete-state output representation.

**What to borrow.** The language-model move: sequences of states have grammar. A washing machine program is a phoneme sequence — short ordered chains with allowed transitions. Constrained Viterbi (a transition matrix encoding program structure) is a standard ASR technique that maps across directly, and it is how you stop a factorial HMM from inventing impossible state sequences.

**What does not transfer.** Music's grammar is strong (scales, chords, metre); appliance grammars are weak. The constrained-transition trick transfers; learned language models do not, at your data scale.

### 2.9 The applied cousins — water end-use disaggregation and CO2 occupancy estimation

**What they are.** Two fields in the same domain family with the same shape. Water end-use disaggregation: a smart water meter's flow series is the superposition of fixture events, solved with HMMs and event clustering; verified anchor: "Implications of data sampling resolution on water use simulation, end-use disaggregation...", *Environmental Modelling & Software* 2018 — note that this field also had to confront sampling resolution head-on. CO2-based occupancy estimation: one ppm series, the sum of discrete occupants' metabolisms, with Markov-switching models on top ("A Markov-Switching model for building occupant activity estimation", *Energy and Buildings* 2018).

**What to borrow.** Their evaluation practice — they disaggregate with far less data than NILM's canonical sets and are explicit about resolution limits — and their small-data HMM recipes. Also their framing discipline: both state which load sizes sit below their sensor floor, the same honesty the 30 VA wall demands of this project.

**What does not transfer.** Water events are shorter and hydraulically shaped; CO2 mixing is diffusive rather than instantaneous. The recipes transfer; the signals differ.

## 3. What NILM has already imported (do not reinvent)

| Borrowed method | NILM paper | Status |
|---|---|---|
| Changepoint + steady-state clustering | Hart 1992 (canonical) | The original method; still the baseline |
| Factorial HMM | Ghahramani & Jordan 1997, via Kolter & Jaakkola NIPS 2012 | Mature; exact at K of 4 or fewer |
| Duration and switching priors at low rate | Kim et al., SDM 2011 | Directly your regime |
| Sum constraint (signal aggregate) | Additive FHMM follow-up, 2014 | The physics, made explicit |
| HMM sparsity for online use | IEEE TSG 2015 (in `training-approaches.md`) | Real-time variant |
| Seq2seq from NMT; then seq2point | Neural NILM 2015; AAAI 2018 | Deep-learning import; needs data scale |
| Learned source priors, speech-style | implicit in the deep-NILM line | Mostly unimported at low data scale |

The two import channels that remain genuinely cheap and underused in low-rate NILM are **modern changepoint tooling** (§2.5) and **kinetics-style duration priors** (§2.3).

## 4. A concrete borrowing stack for 2–4 appliances on Shelly data

| # | Step | Borrowed from | Effort | Output |
|---|---|---|---|---|
| 0 | Establish the actual sampling rate (live polling vs 300 s history) | — | the free experiment | which methods are even admissible |
| 1 | TV-1D / fused-lasso denoise | genomics (§2.4) | minutes | clean staircase, step edges preserved |
| 2 | PELT changepoints via `ruptures` | statistics (§2.5) | hours | candidate event list: times and delta-P |
| 3 | Event features: magnitude, duration, time-of-day | Hart + patch-clamp (§2.3) | hours | clustered events; duration prior fitted |
| 4 | Factorial Viterbi over 2^K joint states with dwell priors | factorial HMM (§2.1) | 1–2 days | per-appliance state sequence, exact at K of 4 or fewer |
| 5 | Residual to UNKNOWN bucket; alarm instead of assign | spike sorting (§2.7) | hours | principled unknown handling |
| 6 | BLS-style periodicity scan for cycling loads | astronomy (§2.6) | hours | fridge / HVAC periods and duty cycles |
| 7 | Only if data grows: seq2point CNN | speech / NMT (§2.2) | days | marginal gains at your data scale — try last |

Two notes on the non-obvious choices. Step 4 is *exact*, not approximate, because 2 to the power of 4 is 16 joint states — the "2–4 appliances" constraint from the feasibility work quietly converts an intractable inference problem into a finite-state Viterbi that runs in real time on a laptop. Step 5 is where the brief's "explicit UNKNOWN state" requirement gets its mechanism: in the template-subtraction view, UNKNOWN is not a class a classifier can fail into; it is what remains when the known library fails to explain the observation.

## 5. What no import can fix

1. **The 30 VA floor.** Sub-floor loads are invisible at the sensor; a better model of an unmeasured signal is still a guess. The HMM noise term can absorb them, never recover them.
2. **Step-size degeneracy.** Fig 4(c): fridge, washing machine and kettle step distributions overlap on a log axis; kettle and heater share 2,100 W exactly. Duration priors mitigate but never eliminate this — two *simultaneous* same-size loads are unresolvable, and 2+ appliances are simultaneously ON 32.6% of the time in the UK-DALE slice.
3. **The rate question.** Every §2.5 and §2.7 method degrades as sampling coarsens, and the Shelly's sustained real rate is unverified (stock history API: 300 s finest; ESPHome default 60 s). Still the cheapest, most valuable experiment in the project — `nilm-visual-reading.md` §10.

## 6. One sentence

Your sensor delivers the least informative of the four visual primitives — but the object it produces, a scalar sum of a few discrete, sparse, long-dwell sources, is one that statistics, biophysics, genomics, astronomy and your own field of speech have all attacked with published, importable machinery; the binding constraint is not methodological but physical, and nothing imported can resurrect information the sensor never captured.

---

## Appendix: sources verified this session

All DOIs below were confirmed via the OpenAlex API during this session (titles quoted from API records). Two classics cited without verification are flagged.

**NILM's own formalization**
- Ghahramani & Jordan, "Factorial Hidden Markov Models", *Machine Learning*, 1997 — doi:10.1023/a:1007425814087 (1,186 cites)
- Kolter & Jaakkola, "Approximate Inference in Additive Factorial HMMs with Application to Energy Disaggregation", NIPS 2012 — MIT DSpace doi:10.1184/r1/6603563 (462 cites)
- "Signal Aggregate Constraints in Additive Factorial HMMs, with Application to Energy Disaggregation", 2014 (75 cites; repository record)
- Kim et al., "Unsupervised Disaggregation of Low Frequency Power Measurements", SIAM SDM 2011 — doi:10.1137/1.9781611972818.64 (639 cites)
- Zhang et al., "Sequence-to-Point Learning with Neural Networks for Non-Intrusive Load Monitoring", AAAI 2018 — doi:10.1609/aaai.v32i1.11873 (546 cites)

**Changepoint statistics**
- Killick, Fearnhead & Eckley, "Optimal Detection of Changepoints with a Linear Computational Cost" (PELT), JASA 2012 — doi:10.1080/01621459.2012.737745 (2,619 cites)
- Truong, Oudre & Vayatis, "Selective review of offline change point detection methods" (the `ruptures` survey), *Signal Processing* 2019 — doi:10.1016/j.sigpro.2019.107299 (1,347 cites)
- "An Evaluation of Change Point Detection Algorithms", 2020 — doi:10.48550/arxiv.2003.06222 (89 cites)
- `changepoint` R package, JSS 2014 — doi:10.18637/jss.v058.i03 (1,294 cites); `ocp` BOCPD package, CRAN 2018 — doi:10.32614/cran.package.ocp (34 cites)
- Adams & MacKay, "Bayesian Online Changepoint Detection", arXiv:0710.3742 (2007) — *arXiv preprint, not separately verified*
- Page, "Continuous inspection schemes" (CUSUM), *Biometrika* 1954 — *cited from memory*

**Genomics**
- Olshen et al., "Circular binary segmentation for the analysis of array-based DNA copy number data", *Biostatistics* 2004 — doi:10.1093/biostatistics/kxh008 (2,444 cites)
- Venkatraman & Olshen, "A faster circular binary segmentation algorithm for the analysis of array CGH data", *Bioinformatics* 2007 — doi:10.1093/bioinformatics/btl646 (982 cites)
- Tibshirani et al., "Sparsity and Smoothness Via the Fused Lasso", JRSS-B 2005 — doi:10.1111/j.1467-9868.2005.00490.x (2,818 cites)

**Biophysics**
- "Applying Hidden Markov Models to the Analysis of Single Ion Channel Activity", *Biophysical Journal* 2002 — doi:10.1016/s0006-3495(02)75542-2 (108 cites)

**Astronomy**
- Kovács, Zucker & Mazeh, "A box-fitting algorithm in the search for periodic transits" (BLS), *A&A* 2002 — doi:10.1051/0004-6361:20020802 (989 cites)

**Speech — your home field**
- Yu et al., "Permutation invariant training of deep models for speaker-independent multi-talker speech separation" (PIT), ICASSP 2017 — doi:10.1109/icassp.2017.7952154 (884 cites)
- Luo & Mesgarani, "Conv-TasNet: Surpassing Ideal Time-Frequency Magnitude Masking for Speech Separation", IEEE/ACM TASLP 2019 — doi:10.1109/taslp.2019.2915167 (2,098 cites)

**Applied cousins**
- "Implications of data sampling resolution on water use simulation, end-use disaggregation...", *Environmental Modelling & Software* 2018 — doi:10.1016/j.envsoft.2017.11.022 (88 cites)
- "A Markov-Switching model for building occupant activity estimation", *Energy and Buildings* 2018 — doi:10.1016/j.enbuild.2018.11.041 (40 cites)
- "Building occupancy estimation and detection: A review", *Energy and Buildings* 2018 — doi:10.1016/j.enbuild.2018.03.084 (283 cites)
