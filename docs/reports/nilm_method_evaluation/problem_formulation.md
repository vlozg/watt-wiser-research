# Wattwiser NILM Problem Formulation


Purpose: Define the NILM problem before selecting the next method or engineering features.

---

## 1. Problem Overview

Wattwiser aims to identify individual appliance activity from aggregate
household electricity measurements.

During normal operation, the system will receive the total electricity
signal from the household rather than a separate measurement from each
appliance.

The main requirement is to:

- identify which target appliance is operating;
- estimate how much power the appliance is consuming;
- identify when the appliance starts and stops operating; and
- estimate the energy consumed by the appliance over time.

The problem formulation should therefore support both appliance detection
and appliance power estimation.

---

## 2. Deployment Constraints

The NILM approach needs to be suitable for the intended Wattwiser
deployment environment.

The main constraints are:

- aggregate household electricity measurements;
- low-frequency measurements;
- no dedicated measurement from each appliance during normal operation;
- a limited number of appliances may be calibrated by the user; and
- multiple appliances may operate at the same time.

The selected approach should not depend on information that will not be
available during actual Wattwiser operation.

---

## 3. What the System Needs to Produce

The primary goal is to estimate the power consumption of individual target
appliances from the aggregate electricity signal.

From this output, Wattwiser should be able to determine:

### Appliance

Which appliance is likely operating.

### Operating state

Whether the appliance is currently operating or not.

### Operating period

When the appliance started and stopped operating.

### Power consumption

The estimated power being consumed by the appliance.

### Energy consumption

The estimated energy consumed by the appliance over a period of time.

This means that ON/OFF detection alone is not sufficient for the complete
Wattwiser requirement. Power estimation is a core part of the problem.

---

## 4. Candidate Problem Formulations

Several formulations are possible for NILM. Each formulation leads to
different model types, features, and evaluation methods.

### 4.1 Pattern Matching

The system compares the observed electricity pattern with a known
appliance profile.

This is closely related to the calibration concept in Wattwiser, where
the system can learn characteristics of a particular appliance.

Potential outputs include:

- appliance identity;
- confidence;
- operating period; and
- estimated power.

A key limitation is that appliance behaviour can change and multiple
appliances can produce overlapping patterns.

---

### 4.2 Event or Span Detection

The system focuses on detecting changes in the aggregate signal and
identifying appliance operating events.

For example:

    Appliance starts → appliance operates → appliance stops

This approach is useful when the main objective is to identify appliance
operating periods.

However, overlapping appliances and gradual or multi-state appliance
behaviour can make event detection more difficult.

---

### 4.3 Classification

The system predicts the state of an appliance, such as:

    ON
    OFF

Classification is useful for determining appliance activity and can be
evaluated using metrics such as precision, recall, and F1.

However, classification by itself does not provide the actual power
consumed by an appliance.

---

### 4.4 Regression

The system directly estimates appliance power from the aggregate
electricity signal.

For example:

    Aggregate signal → estimated kettle power

This formulation directly addresses Wattwiser's requirement to estimate
appliance power.

The appliance operating state and operating period can potentially be
derived from the estimated power signal.

---

### 4.5 Sequence-to-Point

The system uses a window of aggregate measurements to estimate appliance
power at a particular point.

This is a regression-based NILM approach.

Its main advantage is that it directly estimates appliance power rather
than only predicting an ON/OFF state.

---

### 4.6 Sequence-to-Sequence

The system uses a sequence of aggregate measurements to estimate a
corresponding sequence of appliance power measurements.

The output is therefore an estimated appliance power profile over time.

This could potentially provide the information required for:

- appliance detection;
- operating-state identification;
- operating-span detection; and
- energy estimation.

---

### 4.7 State-Based Models / FHMM

State-based approaches model appliances using different operating states
and estimate which combination of states best explains the aggregate
signal.

FHMM is an established NILM approach and has already been tested in the
Wattwiser research project.

The existing FHMM experiment provides an initial reference for evaluating
other approaches.

---

### 4.8 Mixed Pipeline

The problem could also be separated into several stages:

    Aggregate electricity
            ↓
    Event / activity detection
            ↓
    Appliance identification
            ↓
    Power estimation
            ↓
    Energy estimation

A mixed approach may be appropriate if a single model cannot reliably
provide all required outputs.

---

## 5. How the Formulations Will Be Compared

The candidate formulations should be evaluated against the actual
Wattwiser requirements.

The main criteria are:

1. Can it identify the appliance?
2. Can it estimate appliance power?
3. Can it identify the operating period?
4. Can it estimate energy consumption?
5. Can it handle multiple appliances operating at the same time?
6. Can it work with low-frequency aggregate measurements?
7. How much calibration or training data is required?
8. How difficult is it to implement and run?
9. Can it be used as a practical basis for the next experiment?

---

## 6. Research Questions

Before selecting the next algorithm, the following questions need to be
answered:

1. What should be the primary prediction target for Wattwiser NILM?

2. Should ON/OFF state be directly predicted, or should it be derived
   from estimated appliance power?

3. Should Wattwiser primarily be treated as a pattern-matching,
   event-detection, classification, regression, sequence-prediction,
   state-estimation, or mixed problem?

4. Which formulation best supports both appliance identification and
   appliance power estimation?

5. Which established NILM methods are suitable for the selected
   formulation and the project's low-frequency data?

6. Which method can be implemented and tested quickly using the existing
   Wattwiser research pipeline?

---

## 7. Initial Working Direction

The current working direction is to treat appliance-level power
estimation as a central part of the NILM problem rather than treating
ON/OFF classification as the complete objective.

This is consistent with the Wattwiser requirement to both identify which
device is operating and estimate the power consumed by that device.

However, the final problem formulation has not yet been frozen.

The candidate formulations and established methods will be reviewed before
selecting the next experiment.

---

## 8. Next Step

The next stage is to review established NILM methods that fit the
candidate formulations, with particular attentiqto:

- FHMM;
- Sequence-to-Sequence;
- Sequence-to-Point; and
- other established methods suitable for low-frequency data.

The objective is to identify a method that fits the Wattwiser problem and
can be implemented quickly as the next experiment.

The selected method will then be documented in a separate experiment plan
before implementation