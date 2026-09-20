# NILM electricity basics, explained like you're five

A refresher on the electrical quantities that show up in every NILM dataset —
voltage, current, power, energy — using a plumbing analogy, since electricity
behaves a lot like water in pipes.

## The core four

### Voltage (V, volts) — the pressure

How hard electricity is being "pushed". In a US home the wall outlets push at
120 V; big appliances (dryer, oven, EV charger) get 240 V. In NILM data, mains
voltage is basically constant — it wobbles a little (117–125 V) but it is not
the interesting signal. And it is the one thing you don't control: the grid
supplies the pressure, and each appliance decides how much current to pull at
that pressure. Flip a switch and you change the flow, not the push — which is
exactly why NILM watches current and power while treating voltage as backdrop.
(A big motor starting can slightly drag the house voltage down for a moment —
a faint clue in itself — but "voltage is given, current is chosen" is the
right default model.)

### Current (I, amps) — the flow rate

How much electricity is actually moving. This is what changes when you turn
things on: a phone charger draws a trickle, an air conditioner gulps. In NILM,
current is where the action is — appliances "pull" different amounts.

### Power (W, watts) — how fast energy is being used *right now*

The combination of pressure and flow:

```
P = V × I
```

Water analogy: a fire hose (high pressure, high flow) does more work per second
than a leaky faucet (low pressure, low flow). A 1200 W kettle at 120 V pulls
10 A. Power is an *instantaneous rate* — like a speedometer.

### Energy (Wh, kWh) — the total amount used over time

What your utility actually bills:

```
energy = power × time
```

A 1000 W appliance running for 1 hour uses 1 kWh (costs roughly 15–30 cents).
Power is speed; energy is distance traveled. The Shelly EM and most NILM
datasets report both: watts for "right now", kWh accumulating for "the bill".

## Cheat sheet

| Quantity | Unit | Water analogy | NILM data role |
| --- | --- | --- | --- |
| Voltage | V (volt) | Pipe pressure | Near-constant mains context, rarely the signal |
| Current | A (amp) | Flow rate | Varies per appliance; part of the fingerprint |
| Power | W (watt) | Pressure × flow, right now | The main disaggregation signal |
| Energy | Wh / kWh | Total water used | What gets billed; cumulative counters |

## Two things high school may have skipped

### It's AC, not a steady flow

Mains electricity flips direction 60 times per second (60 Hz in the US). So V
and I are not constant numbers — they are sine waves. The "120 V" on the label
is a kind of average (root-mean-square, rms) of that wave. No math needed; just
know that "V rms" or "I rms" in the data means the effective value of the wave.

### Real power vs. "wasted" power (power factor)

This one actually matters for NILM:

- **Real power (W)** — what does actual work and shows up on the bill: the
  wave-by-wave product v × i, averaged over time.
- **Apparent power (VA)** — V rms × I rms: the two effective values multiplied,
  timing ignored. (Current is the quantity, amps its unit — so "volts × amps"
  just means volts × current.)
- **Power factor** — real ÷ apparent, between 0 and 1.

Both come from the same two ingredients, V and I — the difference is the
recipe. With AC flipping direction 60 times a second, the order of operations
matters: real power multiplies the two waves together at every instant and
*then* averages, so it respects their timing; apparent power averages V and I
separately and multiplies the two averages, throwing the timing away. When the
waves march in step (kettles, heaters, anything purely resistive) the two
agree: 1200 W is also 1200 VA. When a device's current lags behind the push,
part of the flow sloshes back and forth each cycle without doing net work, and
the device pulls more amps than its watts suggest. Example: a compressor
pulling 4 A at 120 V is 480 VA, but at a power factor of 0.6 only about
290 W is actually doing work.

Plain version, as three lines:

```
S (apparent, VA) = V rms × I rms              — two averages multiplied, timing-blind
P (real, W)      = average of v × i over time — multiply first, then average
PF               = P / S                      — 1.0 when the waves are in step
```

("rms" just means the effective, DC-equivalent value of the wave — the "120 V"
on an outlet label is already an rms number.) The utility must build wires that
carry every amp, so infrastructure is sized for S — but only P does work and
shows up on the bill. When the waves are in step the two coincide; the more a
device's current lags, the wider the gap between them.

Some devices (motors, fridges, anything with coils) cause current and voltage
to drift out of sync, so they pull more amps than the watts suggest. For NILM
this is a gift: *how* a device draws current (its timing, its shape) is part of
its fingerprint, not just how much.

## Why this maps onto NILM

The device signatures above can be read from two kinds of data, which gives
two methods of disaggregation.

### Method 1: total wattage from the mains

The setup: one combined watt curve from the mains; whose fingerprints are
these?

- A fridge cycles: short bursts of a few hundred watts, on and off, all day —
  an on/off signature.
- A dimmer or laptop charger draws a smooth, variable trickle — a level
  signature.
- Big resistive loads (kettle, dryer, water heater) are clean, stable blocks at
  nearly constant watts — easy to spot.

Just one number (watts), sampled slowly — once a second or once a minute — is
enough to try this. That is what cheap meters report, what the Shelly EM gives
us, and what most classic NILM methods consume.

### Method 2: the shape of the V and I waves themselves

In AC, V and I are not single numbers but 60 Hz waves, and every device bends
those waves in its own way — a laptop charger clips the current wave flat on
top, a motor pulls it lopsided. Even two devices drawing the same watts wiggle
differently, so the *shape* per device is a much richer fingerprint than the
watt level alone. The cost: this needs fast sampling (kilohertz) and extra
hardware. The V-I track (PLAID captures at 30 kHz, under `research-logs/vi/`)
works at this level.

> **Reminder:** the V and I a Shelly reports are rms values — one effective
> number per wave, like a multimeter reading. That is Method 1-style data, not
> the waveform Method 2 needs. Capturing the actual wave shape takes dedicated
> high-frequency hardware; a standard submeter's V/I reading cannot stand in
> for it.

## One-liner to keep

**Volts = push, amps = flow, watts = push × flow right now, kWh = what you pay
for.**

## Where to go next

`docs/knowledge/ELI5_COMMON_NILM_FEATURES.md` - the features NILM methods
compute from these quantities (delta power, duty cycles, V-I trajectories),
with real figures from this repo.
