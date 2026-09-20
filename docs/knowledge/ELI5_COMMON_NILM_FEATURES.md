# Common NILM features, explained like you're five

Companion to `docs/knowledge/ELI5_NILM.md` (electricity basics: V, I, W, kWh,
AC, power factor). That doc explained the physical quantities; this one covers
what people *compute* from them — the features NILM methods eat. Each feature
is illustrated with a figure from this repo, all generated from real
measurements (UK-DALE 6 s data: one UK home, 70.7 days; plus 16 real PLAID
waveform captures at 30 kHz).

The two data worlds, recapped from `ELI5_NILM.md`:

- **Method 1** — a slow watt curve from the mains: one number per second down
  to one per 5 minutes. What the Shelly EM gives.
- **Method 2** — the V and I waves themselves at kilohertz rates. Needs
  dedicated waveform hardware.

## Features from a slow power curve (Method 1)

### 1. Power level

The raw signal itself: watts over time. A house at rest sits at a baseline
(fridge + standby + always-on loads); appliances appear as activity stacked on
that baseline. Everything below is derived from this one curve.

### 2. Delta power (ΔP) — the step

Δ (delta) is math shorthand for "change in":

```
ΔP = P(now) − P(previous sample)
```

Appliances announce themselves as *steps*. The baseline can sit anywhere
between 300 W and 2500 W depending on what is already running, so absolute
levels are noisy to match — but the jump when something switches is stable:

```
12:00:00  mains =  350 W
12:00:01  mains =  690 W    ΔP = +340 W  ← about 340 W just turned on
12:02:01  mains =  348 W    ΔP = -342 W  ← the same something turned off
```

A matched pair like +340 / −342 is the classic fridge-cycle signature. ΔP is
a derived feature: computed from the same curve, no new hardware, and it
removes the unknown baseline — the step survives whatever else the house is
doing. Event-based NILM is built on this: flag every |ΔP| above a threshold
as an "edge", then attribute edges to appliances.

![Figure 4 — the event view](../../figures/fig04_event_view.png)

Panel (a): an event is a step shared by the aggregate and the appliance trace.
Panel (b): every step the meter took over 70 days — structure appears at the
fridge (about 107 W) and kettle (about 2.9 kW) sizes. Panel (c) is the sobering
one: per-appliance step-size distributions overlap heavily on a log axis, so
step size alone cannot identify a device. Panel (d): appliances overlap in
time about a third of the day.

### 3. Duration, duty cycle, and cycling

How long does a device stay on, and how often? In the reference data the
fridge is on 32% of the day, the kettle 0.6% — a model can score 99% accurate
by predicting "everything is off", so duty cycles matter more than peak power.
The fridge's regular pulsing (about 50 times a day) is the closest thing in a
house to a clock; periodicity is itself a feature.

![Figure 3 — one day unrolled](../../figures/fig03_one_day_zoom.png)

### 4. Ramp and multi-stage shape

Not everything is a step. A washing machine runs a long multi-stage cycle:
ramp, plateau, slow decay. A method (or a synthetic data generator) that
thinks in single rectangles cannot represent it.

![Figure 9 — real vs synthetic](../../figures/fig09_real_vs_synthetic.png)

Real appliances ramp and wander; perfect rectangles are the tell of generated
data (more in `docs/research/nilm-visual-reading.md`, section 8).

### 5. Power factor from scalar readings

If the meter reports both real power (W) and apparent power (VA) — as the
Shelly does — the ratio (power factor) is available even in Method 1 data:
heater-class loads sit near 1, motor-class loads well below. One extra
discriminator at zero extra hardware cost.

### 6. Time-of-day context

Kettles cluster at breakfast, dishwashers after dinner. Usage-time priors are
a standard feature in classic NILM models — cheap, and surprisingly effective.

### 7. The sampling rate decides the whole menu

The same evening of the same house, aggregated more and more coarsely:

![Figure 1 — the resolution ladder](../../figures/fig01_resolution_ladder.png)

At 6 s every appliance switch is a clean edge; at 60 s brief events blur; at
900 s only the envelope of activity survives; at 3600 s disaggregation is not
even defined. Before picking features, ask what rate the data actually has —
the feature menu shrinks with the sample rate.

## Features from waveforms (Method 2)

### 8. V-I trajectory (loop shape)

Plot voltage on x, current on y, one loop per mains cycle: every device draws
its own closed 2D curve. Four archetypes cover most of what you will see:

| Trajectory shape | Physics | Typical devices |
| --- | --- | --- |
| Straight line through the origin | Purely resistive: current tracks voltage instantly | Kettle, coffee maker, heater |
| Open ellipse / loop | Inductive: current lags voltage; loop area is reactive power | Fridge, fan, vacuum |
| Burst near the voltage peak | Switch-mode supply charging its capacitor | Laptop, CFL |
| Lopsided / asymmetric | Half-wave rectification | Microwave, hairdryer |

The shapes are scale-invariant — the property step sizes lack — which is why
high-frequency methods rasterise trajectories and feed them to CNNs.

![Figure 5 — the V-I gallery](../../figures/fig05_vi_gallery.png)

### 9. Harmonics and THD

FFT one full mains cycle of current: a resistive kettle puts essentially all
energy in the fundamental (2% THD — a spike any resistor would produce, so it
carries almost no identity); a laptop's switch-mode supply spreads energy
across harmonics (148% THD — distinctive). Harmonics help classify an
already-isolated capture, but the FFT is linear, so it does not by itself
separate a mixture: the house current is kettle + laptop + fridge, so its
spectrum is those three spectra added bin by bin — every device's 3rd
harmonic lands in the same 180 Hz slot and simply adds, leaving nothing in
the plot that says which device owns which bar. To use harmonics you must
first isolate a window where one device is on (an event step, a submeter
capture); only then does the spectrum become that device's fingerprint.

Used or mostly ignored? Both, depending on hardware. With waveform-capable
meters they are a standard classification feature — the founding 1992 NILM
paper already used harmonic vectors. Mainstream low-rate NILM ignores them
for a plain reason: at 1 Hz sampling there is no waveform, hence no harmonics
to compute. Most submeters — the Shelly included — are in that camp, so for
this project harmonics are background knowledge, not a planned feature.

![Figure 7 — harmonic spectra](../../figures/fig07_harmonics.png)

### 10. Phase, transients, and inrush

At waveform level the V-I timing is directly visible: a motor's current peak
arrives fractionally after the voltage peak (the lag that scalar power factor
summarises). Fast captures also show **inrush** — a vacuum spikes to about
1.8 kW on switch-on and decays to a 550 W plateau within half a second,
behaviour invisible at slow sampling rates.

![Figure 8 — waveform to number](../../figures/fig08_waveform_to_power.png)

## Which features does the Shelly actually support?

| Feature | Data needed | Shelly EM Gen3 |
| --- | --- | --- |
| Power level, duty cycles, time-of-day | slow curve | yes (stored history at 300 s; live polling faster) |
| ΔP / event detection | roughly 1–10 s | the experiment to run — what rate it sustains is unverified |
| S and power factor | scalar readings | yes |
| Loads below about 30 VA | sensitivity | no — the no-load blind spot per channel |
| V-I trajectory, harmonics, inrush | raw waveform, kHz | no — rms values only, no waveform register |

## Where to go next

- `docs/knowledge/ELI5_NILM.md` — the electricity basics behind every feature
  above.
- `docs/research/nilm-visual-reading.md` — the full figure-by-figure
  masterclass these images come from: how to audit a new dataset in ten
  minutes, why NILM stays hard even with perfect data, and what the Shelly's
  limits mean for the project.
