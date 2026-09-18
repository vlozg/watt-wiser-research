# Recording V-I Trajectories: Hardware Reality Check

**Context:** Follow-on to `nilm-visual-reading.md` and the hardware work in `repo-review.md`. The question: if V-I trajectories are the field's best signature, can we record them, with what device, and is it as easy as clipping on a CT clamp?
**Status:** Research note. Vendor sites (analog.com, digikey, mouser product pages) are heavily bot-blocked from this environment, so component specs are verified from primary sources where possible and flagged as estimates where not.
**Read alongside:** `nilm-visual-reading.md` §5–6 (what the trajectory primitive is), `repo-review.md` §11 (the Shelly's actual capabilities).
**Short answer:** Feasible, yes. As easy as a clamp, no. A CT clamp measures **current only**, and the V-I trajectory is by definition the joint locus of voltage *and* current sampled **at the same instant** by **one** converter, through a clamp that passes **kilohertz harmonics**. That is three instruments, not one.

---

## 1. Why a clamp alone cannot do it

There are four independent reasons, and any one of them is fatal.

**1. No voltage.** A CT clamp is a current sensor. The trajectory has voltage on the x-axis. You therefore need a second, independent voltage channel, and that channel must be a **galvanically isolated differential measurement** of mains — a scope probe cannot simply be clipped to line and neutral. This reintroduces exactly the mains-contact hazard that made the Shelly's panel installation a concern in the first place.

**2. The samples must be simultaneous, not multiplexed.** A V-I trajectory is a scatter of `(v, i)` pairs, one pair per instant. A cheap energy monitor uses a single ADC multiplexed across its channels: it samples voltage, then current, then voltage again. For computing average real power that is harmless, because the timing error averages out. For a trajectory it is **not** harmless: the pairing is wrong by one conversion interval, and the plotted loop is distorted by an amount that depends on the sampling rate. This is precisely why PLAID specifies a *simultaneously sampled* DAQ card. Note the ADE7953 inside the Shelly EM Gen3 does use separate simultaneous ADCs — the hardware could do this; the firmware simply never exposes the samples.

**3. The clamp must have kilohertz bandwidth.** This is the trap, and the PLAID paper names it explicitly:

> "it is necessary to have a clamp with a high cut-off frequency. Some of the existing datasets with high sampling frequency did not account for this (e.g., BLUED used a current transformer with a cut-off frequency of ~300 Hz)."

An ordinary CT is engineered to pass the 50/60 Hz fundamental and to *reject* everything above it. But the entire discriminative content of a V-I trajectory lives in the harmonics — the flat top of a switch-mode supply's current, the lopsided loop of a half-wave rectifier. A 300 Hz-limited clamp renders every load as a near-perfect sinusoid and **flattens every trajectory into the same ellipse**. You would spend the money and get a signature set with no information in it.

**4. The clamp has a current-dependent phase shift.** The single most discriminative trajectory feature is the **phase relationship** between voltage and current. A CT's phase error varies with both current magnitude and frequency, and it is worst at low current. OpenEnergyMonitor discusses this openly for their own CTs ("the phase error is significantly less at 4 mA than at 2 mA"). In speech you throw phase away; here phase *is* the label. So the rig needs phase calibration, ideally against a resistive reference load.

---

## 2. Sampling rate: how fast is fast enough

From the canonical V-I trajectory paper (Lam et al., *IEEE TSG* 2013; free preprint at arXiv:1305.0596):

> "acquisition of instantaneous voltage and current waveforms is set up, typically at a rate of more than **100 samples per cycle**."

At 50 Hz (Vietnam's grid), one cycle is 20 ms, so 100 samples/cycle is **5 kHz minimum**. Practical datasets sit well above it:

| Dataset / rig | Rate | Samples per 50 Hz cycle | Bandwidth implied |
|---|---|---|---|
| Lam et al. minimum | 5 kHz | 100 | to the 50th harmonic |
| BLUED (flawed clamp) | 12 kHz | 240 | claimed, but clamp cut off at 300 Hz |
| PLAID | 30 kHz | 600 | to the 300th harmonic |
| COOLL | 100 kHz | 2,000 | laboratory grade |

The Nyquist relation is the thing to hold onto: **to see the Nth harmonic you must sample above 2N times the fundamental.** 10 kHz sampling resolves harmonics to the 100th — comfortably enough for the shapes in Figures 5 and 6 — and is the practical target.

---

## 3. The reference design that actually exists

This is not speculative. PLAID — the dataset behind the 16 trajectories in `figures/fig05_vi_gallery.png` — documents its rig completely, and it is worth reading as a shopping list.

From the PLAID paper (*Scientific Data* 7:42, 2020, open access, PMC7015894):

| Role | Instrument | Key spec |
|---|---|---|
| Digitizer | **NI-9215** DAQ card, USB | "four **simultaneously sampled** analog input channels", 16-bit ADC |
| Current | **Fluke i200** AC current clamp | 0.5–200 A, usable frequency **40 Hz – 10 kHz**, output 1 mA/A, CAT III 600 V |
| Voltage | **Pico TA041** differential oscilloscope probe | high-voltage differential, isolated |
| Software | MATLAB and LabVIEW | — |

Effective resolution was about **0.03 A and 0.03 V** after calibration. Collection was crowd-sourced across **65 locations** in Pittsburgh, yielding 1,876 records over 17 appliance types and 330 make/model combinations, at 30 kHz — and the paper still warns that "some instances are not well calibrated", which is a useful calibration of expectations for anyone attempting this alone.

Two design lessons fall straight out of that table. First, **the current sensor is a specialised instrument, not a commodity clamp** — a Fluke i200 is a metrology-grade tool in the same family as the probes in the next column. Second, **the voltage side needs a differential probe**, which is a safety device as much as a measurement device.

---

## 4. Device options and rough cost

Costs below are indicative only — every major distributor is bot-blocked from this environment, so treat the figures as order-of-magnitude, verify before quoting a client, and treat used-market prices as the realistic entry point.

| Route | What you buy | Indicative cost | Effort | Safety burden |
|---|---|---|---|---|
| **A. Power quality analyser** | Fluke 1770 series, Hioki PQ3198, Yokogawa WT series, Dranetz | 3,000–15,000 new; 2,000–5,000 used | Low — it is the product | None; CAT-rated |
| **B. Bench oscilloscope + probes** | Any digital scope with simultaneous channels, plus a high-bandwidth AC clamp and a differential voltage probe | 600–1,500 | Medium | Mains-rated probes required |
| **C. DAQ, PLAID's route** | NI-9215 (or equivalent simultaneous-sampling DAQ) + Fluke i200 + Pico TA041 | 1,000–2,000 | Medium | Mains-rated probes required |
| **D. DIY modern** | ADS131M08 (24-bit, 32 kSPS, **8-channel simultaneous sampling**) + ESP32/STM32 + high-bandwidth CT + burden resistor + isolated voltage divider | 100–300 in parts | High — weeks of engineering | You own the isolation design |
| **E. Metering IC with a waveform buffer** | **ADE9000** eval board — the driver exposes a `WFB_CFG` (waveform buffer) register, so on-chip waveform capture is supported | 50–150 for the board | High | You own the isolation design |

Route E deserves emphasis because it names the exact difference from what the team already owns. The **ADE7953** in the Shelly EM Gen3 and the **ADE9000** are relatives from the same metering family. The ADE9000 adds a waveform buffer; the ADE7953 has none, and the Shelly's firmware reads scalar registers only. So the hardware gap between "what we have" and "what a trajectory needs" is, at the silicon level, a known and purchasable part — the difficulty is the analog front end, the isolation, and the mains safety around it, not the IC.

---

## 5. The structural catch: plug-level, not panel-level

This is the part that decides whether the idea helps the project at all.

A V-I trajectory rig measures **one appliance at a time, at that appliance's own plug**. PLAID did exactly this, and it is why PLAID contains 1,876 individually-metered appliance records and **no whole-home aggregate signal**. It is a signature library, not a disaggregation test set.

The Shelly measures at the **panel**, where all appliances are superimposed. Those are opposite ends of the wire, and neither device substitutes for the other.

| | Plug-level V-I rig | Panel-level Shelly EM |
|---|---|---|
| Measures | One appliance, in isolation | Whole house, superimposed |
| Gives you | Appliance signatures (a library) | The aggregate signal (the actual problem) |
| Can validate a disaggregator? | **No** — no aggregate to disaggregate | Yes, in principle |
| Mains contact | At a socket; still needs an isolated voltage tap | Inside the distribution panel |
| Typical class | Bench test instrument | Consumer energy monitor |

So for WattWiser's stated goal — disaggregate the whole home — a V-I rig is a **research and calibration instrument, not a product sensor**. It is the right tool for building the ground-truth signature library that a household-specific calibration would draw on, and it is the wrong tool for the always-on deployment the product brief describes.

There is one place it genuinely connects to their existing plan. The calibration document centres on "guided calibration", and calibration is inherently a plug-level, one-appliance-at-a-time procedure. A V-I rig is a *better* calibration instrument than the Shelly, because it measures the appliance cleanly without needing to separate it from a noisy aggregate. But it only works if someone physically moves the plug — which is not something a shipped product can ask of a customer.

---

## 6. What I would tell them

**If the goal is to know whether V-I trajectories are worth anything for these appliances:** do not buy the rig. The answer is already public. PLAID is 1,876 real records at 30 kHz, it is free, and Figures 5 and 6 are drawn from it. That question costs nothing to answer.

**If the goal is to build a signature library for a specific home:** a route A or B instrument is a legitimate one-off capital purchase of roughly 1,000–2,000 used, and it is the only way to get real trajectories. Budget the calibration effort, not just the instrument.

**If the goal is a product sensor:** no device in this note is the answer. Every route either requires mains-contact installation at the plug, or costs more than the appliance it is monitoring. The Shelly's scalar-only telemetry is a consequence of being a 70-dollar consumer device, and the trajectory primitive lives one tier above it.

**The experiment worth running before buying anything** remains the same one flagged in `nilm-visual-reading.md` §10: determine what sampling rate a Shelly actually sustains in live polling, and what the ADE7953's integration time does to a step edge. That costs nothing, it settles the only question the current hardware has not yet answered, and it determines whether the low-frequency half of the visual vocabulary is even available.

---

## 7. Method note

Figures and claims in this note trace to primary sources: PLAID's acquisition rig and its criticism of BLUED's clamp are quoted from the open-access dataset paper (PMC7015894); the 100-samples-per-cycle requirement is from the arXiv preprint of Lam et al. (arXiv:1305.0596); the Fluke i200 bandwidth figure (40 Hz – 10 kHz) is from Fluke's own product page; the ADE9000 waveform buffer is confirmed by the `WFB_CFG` register write in Analog Devices' no-OS driver. Sampling-rate arithmetic is my own. Cost ranges are estimates, not quotes.
