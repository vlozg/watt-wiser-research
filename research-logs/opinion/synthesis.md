# Community validation of the Watt-Wiser use-case reassessment

**Question put to the community:** are the five load-bearing claims in docs/product/use-case-reassessment.md
supported by practitioners who have actually lived with whole-home disaggregation?

**Method.** Reddit (old.reddit JSON through the logged-in browser) plus Hacker News (Algolia).
Exact-phrase discovery queries, full thread fetches, then mandatory per-account verification via
the Reddit about endpoint. Raw artifacts in this directory.

**Collected:** 2026-09. Threads span 2014-2026. 14 Reddit threads fetched in full, 1 HN thread,
15 accounts verified, 1 GitHub prior-art sweep.

**Verification summary.** Every account carrying a load-bearing claim is 6-15 years old with
substantial karma; five are subreddit moderators. The one prominent pro-NILM voice is a
three-month-old single-product account. Details below.

---

## Verdict table

| # | Claim under test | Verdict | Confidence |
|---|---|---|---|
| C1 | Disaggregation delivers little practical value | **Supported, strongly** | High |
| C2 | Anomaly detection on aggregate NILM is harder; practitioners use submetered data | **Supported, strongly** | High |
| C3 | Feedback/awareness savings are small | **Supported by absence** | Medium |
| C4 | The real value is benchmarking / payback (measure, compare, decide) | **Supported, strongly** | High |
| C5 | The community answer is per-circuit CT hardware, not inference | **Supported, strongly** | High |

---

## C1. Disaggregation delivers little practical value -- SUPPORTED

This is the best-evidenced claim in the set. Five independent verified voices, in four
subreddits, over nine years, saying the same thing in different words.

**u/twoaspensimages** (account since 2019-02, 105,026 comment karma, moderator) -- seven-year
Sense owner, r/Sense "Appliances that change over time", 2023-01:

> "When we gut renovated it's been a very different story. It doesn't find anything with a
> variable load. It's lost more than it ever found. ... Honestly all I use it for is an instant
> watt meter I can see as I'm walking around the house turning things on and off."

Replying, **u/MartinB3**:

> "This. It's really all Sense is. A digital meter."

**u/Shadow14l** (since 2009-07, 44,348 comment karma, moderator), r/Sense "Sense vs. Emporia Vue",
2022-01:

> "Sense is neat but I just think their solution isn't technically feasible to the extent
> expected by most consumers."

Same thread, u/twoaspensimages on measured coverage:

> "5 years. 54% 'Other'"

and **u/RyanBorck** (since 2017-04, 7,921 comment karma) in the same thread:

> "64% Agree 36% Other"

**u/hdfvbjyd** (since 2016-09, 2,972 comment karma), r/Sense "Review, 6 months in - very
disappointed", 2017-05:

> "With this little detected, it would have been far easier and cheaper to get individual z wave
> power meters. ... The vast majority of the time, I just see a big unkown blob."

The vendor's own account, **u/SenseEnergy**, replied in that thread and conceded the shape of the
problem rather than disputing it:

> "There are certain devices that we are great at identifying right now and others that we are
> still working to improve detection on."

**u/fawkesdotbe** (since 2012-01, 43,754 comment karma, moderator), r/homeassistant, 2025-02,
asking the question that matters more than the accuracy question:

> "I don't follow. If you manage to do this and get the precise and reliable information that
> your induction cooktop uses a lot of energy, what will you do? Stop cooking, change your diet?
> Or do you see this more like a cool project to learn new techniques?"

**u/DIY_CHRIS** (since 2018-11, 23,869 comment karma), same thread:

> "This seems like throwing software at a hardware problem. If you don't want to use smart plugs,
> use a CT-clamp style monitor like the Emporia Vue 3 and place CT's on every circuit."

The r/energy thread "Energy Disaggregation at the Home" (2023-05) drew the same objection as its
top comment:

> "for what *purpose*? what is the endgame? to use less/save money..? ... why the detailed
> analysis? every month, you pay for X units of energy. don't take as many to begin with."

### The counter-evidence, stated fairly

Disaggregation is not worthless -- it is narrow, and the community distinguishes the two columns.

**u/roland35**, HN "Ask HN: Home Energy Monitor Recommendations?" (2023-06):

> "Sense is much less upfront to install - it is able to detect most large loads just by looking
> at the overall current and voltage going into the house via disagregation. It works pretty
> well!"

Read that carefully: "most **large** loads". That is exactly the feasible column. And
u/twoaspensimages in the same r/Sense thread concedes the historical case:

> "We've had our Sense 7 years. It found most of the late 80s appliances and even guessed what
> they were correctly. I was pleasantly surprised."

The failure mode is not random -- it is modern appliances. Same user, after renovation:
variable-speed everything. So the honest summary is: **disaggregation worked on the 1980s
appliance stock and stopped working as loads became inverter-driven and multi-state.** The
client is deploying into the modern stock.

---

## C2. Anomaly detection is harder, and practitioners do it on submetered data -- SUPPORTED

The single most informative find. One community member has built almost exactly what the user
proposed, and the implementation reveals the constraint.

**u/tavenger5** (since 2012-04, 146,955 comment karma, moderator), r/homeassistant, 2026-06:
*"I built an add-on that can tell you if an appliance is on when it shouldn't be, or even about
to fail!"*

Asked point-blank whether it is LLM-powered, the author answers:

> "No, it does not use an LLM to do anything. The pattern matching is a rule-based time-series
> with robust baseline comparison using median, median absolute deviation, 10th percentile, 90th
> percentile, and a confidence value based on sample count. Deviation scoring compares the
> observed value against the baseline median using a spread based on MAD..."

And on hardware, asked how it determines power usage:

> "Yes, there has to be an existing power meter, like the CircuitSetup 6 channel meter, or
> Emporia Vue"

with the method described as:

> "Pattern matching and, for mains, NILM"

**This is the whole argument in one sentence.** The person doing appliance anomaly detection
uses NILM only for the mains line, runs median/MAD deviation scoring on **per-circuit** data,
and needs a six-channel meter to do it. Nobody in that thread questions the hardware
requirement -- it is treated as obvious.

The r/Sense drift thread (2023-01, 13 comments) shows the same pattern from the consumer side.
The one discovery that produced an actual decision came from per-circuit data. **u/RangerPretzel**
(since 2011-10, 24,282 comment karma, moderator):

> "I picked up the Emporia Vue2. ... the individual circuit monitoring is invaluable. As an
> example, I discovered right away that my one heat pump draws 25w when 'off' while the other
> only draws 5w when 'off'. So in the Spring and the early Fall, I shut off both heat pumps via
> circuit breaker. While that doesn't sound like a lot (0.72 kwh per day)..."

That is precisely the meter-level baseline-creep exception identified in the reassessment:
it needed no attribution, it was a comparison of two like circuits, and it produced a number and
an action. It also came from circuit monitoring rather than disaggregation.

On why aggregate NILM fails here, from the same thread:

> "Mitsubishi heat pump... Sense is never going to detect that. It's variable speed everything,
> with no clear on/off transitions."

And a practitioner stuck at exactly the predicted wall, **r/MLQuestions** "Anomaly detection in
power consumption + NILM" (2025-07):

> "I have no labeled data so it is a bit hard to determine the ideal parameter."
> "for assigning sensors to the anomalies, I tried to look at their rate of change around the
> timestep of the anomalies, but I am not confident in my results yet."

The thread's four replies are all generic unsupervised-ML advice (isolation forest tuning, matrix
profiling, autoencoders). Nobody has a working answer. Five comments total -- and this is the
only thread in the entire collection where someone is attempting NILM-based anomaly detection.

This aligns with the two papers already cited in the reassessment (Applied Energy 2019;
ICASSP 2019) which found NILM traces less robust for faulty-behaviour identification than
submetered data. **Community practice and the literature agree.**

---

## C3. Feedback savings are small -- SUPPORTED BY ABSENCE

Stated as a gap rather than a proof, because that is what the evidence is.

Across every thread fetched, **not one disaggregation user reported a measured saving.**
Frustration, coverage percentages, and "what's the point" -- but no before/after number.

Where savings are reported, they come from circuit-level measurement and a specific action:
u/RangerPretzel's 0.72 kWh/day from switching off idle heat pumps. And where the
"what will you do?" question is pressed (u/fawkesdotbe above), the answer given by the OP was
load-shifting for a Belgian capacity tariff -- peak management, which needs a clock and a
peak reading, not appliance identification.

The magnitude question is answered by the literature already in hand (Ecol. Econ. 2020
meta-analysis: 1.9-3.9% realistic savings across 713,002 households; Houde et al. 2013: 5.7%,
significant for up to four weeks). The community contributed no contradiction to that, and no
supporting anecdote either. Treat the number as literature-backed, not community-validated.

---

## C4. Benchmarking / payback is the real value -- SUPPORTED, and the strongest single find

The r/Appliances thread "Do energy-efficient appliances really save money in the long run?"
(2025-11, 85 comments) is the user's Request D insight arrived at independently by a room full
of strangers. It is worth reading as a whole because the shape is so familiar.

Top comment, **u/daLejaKingOriginal** (11 points):

> "Just calculate the cost/savings."

**u/thewags05** (since 2016-02, 35,840 comment karma):

> "It depends on what you're replacing. I just had to get a new refrigerator. Compared to the
> old one it'll pay for itself in about 3.5 years. Heat pump dryers can pay for themselves pretty
> quickly too."

**u/mikerall** (since 2012-06, 45,194 comment karma), doing informal peer benchmarking:

> "My fridge is like 15/month, my uncle's was about 22/month in today's prices. My friend's is
> 10/month. His just had a 700 repair after 5 years. That offset another 6 years of efficiency
> between his and mine."

And the comment that is the product brief, from a now-deleted account (6 points):

> "Buy a plug that measures electrical consumption. Use it to measure the daily consumption of
> your appliance and maybe ask a friend to do the same and you can compare numbers and get a
> proper fact-based financial breakdown of the potential benefits."

**That is the notification-free, calibration-free, disaggregation-free version of the product.**
Measure the device, compare to a reference, produce a payback number. It requires one meter and
one interaction -- not a training loop and not appliance inference.

### Two caveats the community raised against its own idea

**u/thrax_uk** (since 2016-04, 7,828 comment karma):

> "Reliability > Energy efficiency. Also, energy efficient modes usually have downsides... Older
> appliances are also more likely to be repairable vs newer appliances."

A deleted account (7 points) supplies the trigger condition:

> "replacing a working, 'old' appliance with a new one for efficiency's sake will almost never
> pay off."

So the decision point is **end-of-life replacement**, not curiosity -- which sharpens the product:
the buyer is someone whose fridge has just died and who is choosing what to replace it with.
That is a purchase-moment, point-of-sale intervention, and it is a different company from
continuous monitoring.

---

## C5. The community answer is per-circuit CT hardware -- SUPPORTED

Independent of the disaggregation debate, the collected threads converge on what people actually
buy and recommend.

HN "Ask HN: Home Energy Monitor Recommendations?" (2023-06) -- thirteen comments, and the whole
thread is circuit-level instrumentation: Iotawatt (recommended three times), SPAN panel,
GreenEye, Shelly EM on individual circuits. **The word "disaggregation" appears once**, in a
defence of Sense. **u/leon_sbt** states the preference plainly:

> "Doing switching at the panel level seems very clunky. In reality, switching should be done at
> the device level. Ie per fan, light etc. If they had a self contained server similar to
> IOTAWATT that just instruments the power draw of each circuit then I would be a fan."

r/homeassistant "Whole home power monitoring" (2026-05, **485 points, 236 comments**) -- the top
three answers are all Emporia Vue 3, with ESPHome flashing for full local operation. NILM is not
mentioned in the visible top answers at all.

r/Sense "Got my Flex kit today" (2020-10) -- **u/poppinfresh_original** (since 2016-04) bought
the extra CT clamps precisely to get what disaggregation was not giving him:

> "Yes I intend to go breaker by breaker to gather some data about usage for the mystery stuff.
> ... I plan on using it more like a fancy Kill-A-Watt where I collect some data on a circuit's
> use over a period of time and then move on to the next."

**And the economics have moved.** r/homeassistant, IKEA Inspelning energy-monitoring smart plug,
2024-09: **741 points, 266 comments**, at **USD 11.99** and Zigbee. When per-device truth costs
USD 12 per load, the case for inferring it from the mains is much weaker than it was in 2015.

---

## GitHub prior art: the field is twelve years old and well tooled

A sweep of GitHub for NILM returns **1,416 repositories**. The mature ones:

| Stars | Repo | Since |
|---|---|---|
| 953 | nilmtk/nilmtk | 2013 |
| 219 | ch-shin/awesome-nilm | 2019 |
| 162 | JackKelly/neuralnilm (author of UK-DALE) | 2015 |
| 146 | klemenjak/nilm-papers-with-code | 2019 |
| 144 | OdysseasKr/neural-disaggregator | 2017 |
| 143 | nilmtk/nilmtk-contrib | 2019 |
| 120 | MingjunZhong/seq2point-nilm | 2020 |
| 104 | goruck/nilm | 2022 |

There is no scarcity of method, code, or literature. Anything the client builds from
first principles has a thirteen-year head start against it. The bottleneck is the sensor and the
labelling, which is exactly what the reassessment said.

The one active product-side project, **HA-NILM** (the same author as the r/homeassistant posts),
is open source with a HACS/add-on install. Its own landing page states the limitation better
than any critic could:

> "NILM provides useful estimation, not direct appliance measurement."

and its requirements:

> "A mains power sensor already available in Home Assistant" ... "At least 4 GB of RAM"

So even the most enthusiastic community implementation assumes a mains CT already exists,
concedes it is estimation rather than measurement, and needs 4 GB of RAM. Its own author notes
the accuracy caveat: "it is still something worth testing on each setup because appliances can
have very different power signatures depending on the model and how they operate."

---

## Source credibility and astroturfing check

Verified through the Reddit about endpoint. The file verification.jsonl holds the raw records.

| Account | Since | Comment karma | Moderator | Used for |
|---|---|---|---|---|
| u/tavenger5 | 2012-04 | 146,955 | yes | anomaly add-on author |
| u/twoaspensimages | 2019-02 | 105,026 | yes | 7-yr Sense owner, "54% Other" |
| u/mikerall | 2012-06 | 45,194 | no | fridge peer benchmarking |
| u/Shadow14l | 2009-07 | 44,348 | yes | "not technically feasible" |
| u/fawkesdotbe | 2012-01 | 43,754 | yes | "what will you do?" |
| u/digitalmarley | 2017-10 | 37,024 | no | Emporia Vue 3 |
| u/thewags05 | 2016-02 | 35,840 | no | 3.5-year fridge payback |
| u/RangerPretzel | 2011-10 | 24,282 | yes | heat pump 25 W idle discovery |
| u/DIY_CHRIS | 2018-11 | 23,869 | no | "software at a hardware problem" |
| u/poppinfresh_original | 2016-04 | 8,774 | no | breaker-by-breaker CT plan |
| u/RyanBorck | 2017-04 | 7,921 | no | "64% / 36% Other" |
| u/thrax_uk | 2016-04 | 7,828 | no | "reliability > efficiency" |
| u/hdfvbjyd | 2016-09 | 2,972 | no | 6-month disappointed review |
| u/itsallgoode | 2014-10 | 332 | no | r/energy OP |
| **u/Foreign-War7559** | **2026-06-10** | **6** | no | **HA-NILM author** |

**Red flags found:**

1. **The strongest pro-NILM voice fails the credibility check.** u/Foreign-War7559 created the
   account on 2026-06-10, has 31 link karma and 6 comment karma, is not a moderator, and has
   posted essentially only HA-NILM release announcements. Every positive statement about
   disaggregation working in the collected evidence traces back to this account or to the
   author's own documentation. Per the skill's rule, treat all HA-NILM performance claims as
   **vendor-adjacent and unvalidated by third parties.** Notably, the second HA-NILM thread drew
   only 10 comments, and no independent user in either thread reported a validated result --
   the one user who tried (u/AI_Racer) hit an error: "Failed to prepare training data... No valid
   training windows remain after removing mains gaps."

2. **No "is this an ad?" pushback appeared** in either HA-NILM thread, but engagement is thin
   (29 and 22 points), which is weak organic signal rather than organic validation.

3. **The r/Sense vendor account is properly disclosed** (u/SenseEnergy), so the one vendor
   statement in the evidence is legitimate and usable.

4. **Two of the strongest payback quotes come from deleted accounts** in r/Appliances. The
   argument they make is corroborated by verified users in the same thread, but the quotes
   themselves cannot be attributed.

5. **u/Jane_the_analyst** (r/energy physics explanation) returned an invalid account record --
   account deleted or suspended. Quote is not load-bearing and is excluded.

---

## Zero-signal findings

These matter as much as the positive results.

- **Hacker News has essentially no organic NILM discussion.** Academic NILM submissions get
  0-2 points and 0 comments each: "NILMTK: An Open Source Toolkit" (2014, 1 point),
  "Non-Intrusive Appliances Load Monitoring System Using Neural Networks" (2019, 2 points, 0
  comments), "Non-Intrusive Load Monitoring Based on Multiscale Attention Mechanisms" (2024, 2
  points, 0 comments). Across ten years, the technical audience that would scrutinise this
  hardest has not engaged with it once. The only real thread is a hardware recommendation thread
  that routes around disaggregation entirely.
- **No community thread anywhere reports a measured saving percentage from disaggregation.**
- **Only one thread in the entire collection attempts NILM-based anomaly detection** (r/MLQuestions
  2025-07, 5 comments, unresolved).
- I found no relevant threads in r/electricians, r/HVAC, or r/energyaudit on the payback
  question. Treat those as **untested, not absent.**

---

## Bias and scope limits

- **Platform bias.** Reddit and HN over-represent DIY and home-automation users who already own
  circuit-level CT hardware and are comfortable with technical tradeoffs. They are the hardest
  possible audience for a convenience-oriented product, and they may undervalue a product aimed
  at non-technical homeowners. This cuts in favour of the client, and should be stated to them.
- **r/Sense support bias.** r/Sense is where people go when the product disappoints. The
  satisfaction signal there is structurally depressed. I have partly corrected for this by
  including the positive statements (u/roland35, u/twoaspensimages on 1980s appliances) but the
  negative skew remains.
- **Legacy product.** Sense exited direct-to-consumer hardware in Nov 2025. Its community is now
  a support archive. The complaints are genuine but the product no longer competes, so the
  evidence speaks to the technology's limits more than to a live market.
- **Deleted content.** Several high-scoring comments in the IKEA thread and two key r/Appliances
  comments were deleted or removed and could not be verified.
- **Language and search.** English-language search only. Reddit search is fuzzy even with exact
  phrases, so recall is imperfect; absence of a thread is weaker evidence than presence.
- **Recency.** Evidence spans 2014-2026. The oldest (r/Sense 2017) predates the modern
  inverter-dominated appliance stock; the newest (2026) is the most relevant.

---

## What this changes for the client conversation

The community evidence does not overturn the reassessment. It sharpens three things:

1. **Say the narrow claim out loud and own it.** The practitioners who defend disaggregation
   defend it for large loads, on old appliance stock. That is the defensible product, and it is
   the client's section 5 experiment, not their section 1 or 7 framing.

2. **Anomaly detection is not an escape route -- and there is now a worked example.** The one
   person who built appliance fault detection in this community did it with a six-channel
   circuit meter, median/MAD rules, and no LLM. If the client wants anomaly detection, the
   honest answer is that it requires per-circuit hardware, which changes the BOM and the pitch.

3. **The strongest idea in the room is the one the community already voted for.** "Measure your
   appliance, compare it to a reference, get a payback number" appeared unprompted in an
   r/Appliances thread and is what the top comments in every efficiency thread actually ask
   for. It needs one meter and no inference. If the client wants a product rather than a
   research project, that is where the demand is.

The question to put to them, drawn directly from the evidence:

> "Your section 5 experiment is the right one and your section 1 framing is not. Which one is the
> project? And separately -- the community that has lived with this for a decade has concluded
> that per-circuit measurement beats inference, and that the decisions people actually make are
> replacement decisions driven by payback maths. Have you considered that the product might be a
> measurement tool rather than a disaggregator?"
