# Data collection for experimentation

**Status:** live checklist. **Related:** `experiment-data-strategy.md` (the tier plan),
`baseline-ukdale-plan.md` (the runs), 10 of that doc (multi-house extension). This doc is the practical
acquisition guide: what to download, from where, how to land it, and what NOT to download. All
`research-logs/...` paths below are relative to the repo root (this project's `research-logs/`) -
not any workspace-root `research_logs/`, which holds other-topic research only.

## 1. Short answers

- The set currently being downloaded (UK-DALE 2017 disaggregated appliance/whole-house power) is
  **sufficient for every planned run** - R1-R5 baseline runs and R6/R7 (loop rehearsal, transfer matrix).
- The 16 kHz waveform release (~3 TB) is **not needed** for anything in the plan. It belongs to the separate
  V-I hardware track, where PLAID 30 kHz captures (already local) do the job. Do not stream-process 3 TB
  for this project; see the decision record in 6.
- Already local and already UK-DALE-shaped: REDD @ 1 min (6 homes) and a Kaggle 1-min household
  (provenance unverified). Nothing blocks the experiment work.

## 2. What is already local (inventory, checked 2026-09-18)

| Set | Path | Shape | Caveats |
|---|---|---|---|
| UK-DALE slice | `research-logs/sakunrasilka_nilm-test2/` | house 5 channels relabeled house_1-style, 6 channels, 6 s, 2014-06-30 -> 09-12 | NOT house 1 (provenance forensics 2026-09-21: ch2/3/4/6 are verbatim house-5 fridge_freezer/dishwasher/kettle/i7_desktop; ch1 aggregate is synthetic = sum + flat base); every channel capped at 2^20 rows; superseded by the full download |
| REDD @ 1 min | `research-logs/xingyang990210_nilm-datasets/building_1..6.csv` | `total` + appliance columns, 6 homes, ~1 month each (2011) | resampled minute-means; thin calibration supply; fine for R7 transfer |
| REDD @ 3 s (Kaggle) | `data/redd-kaggle/` -> `research-logs/redd-kaggle/` | 35 chunk CSVs, 6 homes, ~12 d/home, 6-9 appliance cols + `main`, no timestamps | forensics below; timestamp-stripped derivative - align chunks before use |
| Kaggle 1-min | `research-logs/kaggle_1min/household_power_1min.csv` | 1 home, 28 d (2024-06), `total` + fridge/ac/washer/tv/lights/base, 40,321 rows | provenance unverified - run replay checks before any use |
| PLAID samples | `research-logs/vi/plaid_samples/` | 16 device captures @ 30 kHz | V-I track only |
| Client synthetic | `repo/WattWiser/data/raw/synthetic_shelly_data.csv` | 5 s | diurnal template + per-day noise, re-drawn appliance schedules; excluded (repo-review) |

## 3. Download list, priority order

### 3.1 Tier 1 - required for the baseline runs

**UK-DALE 2017, disaggregated appliance + whole-house power** - IN PROGRESS (user download).

**Status 2026-09-19:** landed in `data/` (project folder, transient staging) via CEDA -
`dap.ceda.ac.uk/edc/d1/7d78f943-.../` (the working host; the wget/aria2 script is tracked at `research-logs/download_uk_dale_2017.sh`, a copy also sits beside the staged data).
**Layout note 2026-09-19:** all raw dataset directories were reorganized under `data/raw/`
(`data/raw/ukdale-full/`, `data/raw/REFIT/`, `data/raw/redd/`, `data/raw/AMPds2/`,
`data/raw/GREEND_0-2_300615/`, `data/raw/ECO/`); paths below and in the extraction
pipelines point there. Extraction into `data/fnd/` is unchanged. Reproducible staging:
the user uploaded one zip per dataset to public Google Drive -
`src/pipelines/00_download_dataset/download.py` downloads, extracts and verifies them
(size-verified against `raw_manifest.json`); if a download fails, see the original-host list in section 3.
Two zips mid-download (aria2): `ukdale.zip` = plain-text channels (the set our loader parses),
`ukdale.h5.zip` = HDF5/NILMTK (needs pytables - absent; keep as archive). Plus readmes, per-building
yamls, metadata. An armed watcher moves each zip to `data/raw/ukdale-full/` the moment its
`.aria2` control file disappears, then the readmes/script; the staged copy under `data/` is
retained (user-managed, gitignored).

- Host: `data.ukedc.rl.ac.uk` (probed 302 alive 2026-09-18).
- Contents: houses 1-5, per-house `channel_*.dat` + `labels.dat` - the same schema the loader already
  parses. House 1 has 53 labeled channels; houses 1-3 reportedly include 1-s aggregate mains (verify on
  arrival - that would cover the sub-10-s band question without any waveform data).
- Size: tens of GB for the low-frequency part. The ~3 TB part is the 16 kHz waveform release - **skip it**.
- Land at: `data/raw/ukdale-full/house_<n>/` (keep upstream structure).
- On arrival: add to `.gitignore` (raw data, re-downloadable), rebuild `eda_reference_ukdale.json`,
  re-run R1-R5, unlock R7 across houses 2-5. See the checklist in 8.

### 3.2 Tier 2 - the transfer / multi-house set

- **REFIT (cleaned)** - aggregate + appliance watts, ~9 s sampling per the record text (the staged
  20-house release measures **3-4 s median, irregular** - house 1: 6.96 M rows / 639 d), ~1.5 yr/house (2014-15). **Decision (verified 2026-09-19): download the Zenodo record,
  doi:10.5281/zenodo.5063428** - reachable here, CC-BY-4.0, 6 files, ~2.2 GB total:
  `CLEAN_House1/2/3/4/5/11.csv` (~400 MB each). Caveat: that record carries **6 houses, not 20** -
  which still matches the REDD-1-min set (6 homes) for a real cross-house test. The full 20-home
  cleaned set is the Strathclyde portal entry (doi:10.15129/9ab14b0e-...) - refitsmarthomes.org probed
  000, Strathclyde data hosts unreachable; fetch user-side only if >6 homes becomes necessary. The
  2015 Strathclyde entry is the RAW uncleaned version (known timestamp drift) - skip it.
  Files: `https://zenodo.org/api/records/5063428/files/CLEAN_HouseN.csv/content`. Land at
  `research-logs/refit/`; conversion = wide CSV -> long table.
  **Staged 2026-09-19: `data/raw/REFIT/` = `CLEAN_REFIT_081116.7z` (the FULL 20-house Strathclyde cleaned
  release - supersedes the 6-house Zenodo plan; numbering skips house 14, spans 392-648 d/house) +
  `Processed_Data_CSV.7z` + `MetaData_Tables.xlsx`. Extract per use (6.7 GB extracted in scratch).**
  User-supplied REFIT routes: `pureportal.strath.ac.uk/.../refit-electrical-load-measurements-cleaned/`
  (note: pureportal.strath.ac.uk is NOT the pure.lboro host - probe it) and a Kaggle mirror
  `kaggle.com/datasets/kyleahmurphy/uk-electrical-load`. User-supplied extras: AMPds2 also at
  `dataverse.harvard.edu doi:10.7910/DVN/FIE0S4`; DRED at `st.ewi.tudelft.nl/~akshay/dred/`;
  ECO at `vs.inf.ethz.ch/res/show.html?what=eco-data`; GREEND via sourceforge.
  Checked 2026-09-19, not needed: Zenodo 15362256 (resLoadSIM, NZ/DE load profiles) is **synthetic,
  city-aggregated** 1-min demand curves for electrification scenarios - no house level, no appliance
  channels, no ground truth; scenario-study material, useless for NILM. Same story likely for any
  "load profile" releases from grid simulators (resLoadSIM, LoadProfileGenerator): profiles, not data.
- **REDD original (1 s)** - primary host `redd.csail.mit.edu` is dead/blocked (000).
  **Route found 2026-09-19: Zenodo record 13917372** ("Processed NILM Datasets for Research: IAWE, REDD,
  and UKDALE", doi:10.5281/zenodo.13917372, Oct 2024) ships `redd.h5` (401 MB) = NILMTK-format HDF5 of
  the original REDD, plus `iawe.h5` and `ukdale.h5` (we have the full UK-DALE already) and paper-
  specific tensorized `.npy` files (skip). h5py (3.16.0) is available to read it.
  User is downloading `redd.h5` themselves (agent fetch attempt aborted); on arrival verify channel
  inventory + timestamps, land at `research-logs/redd-original/`. Provenance chain = original REDD ->
  NILMTK conversion -> third-party paper upload.
  **Staged 2026-09-19: `data/raw/redd/redd.h5` (383 MB). Read path verified: `tables` compound nodes
  work; `pandas.HDFStore` fails on this legacy store under pandas 3. b1: 20 meters, mains
  2011-04-18 to 05-24 @1 s; 11-26 meters per building.**
  Checked third-party route 2026-09-19: `inesylla/energy-disaggregation-DL` builds on the Seoul National
  University "Subtask Gated Networks" preprocessed REDD (AAAI 2019, doi:10.1609/aaai.v33i01.33011150) -
  but that set is circulated by its authors on request, no public link in the repo: dead end for data.
  Two things still borrowed from that repo: corroboration that a **cross-house split** (their train
  houses 2-6 / test house 1) is a defensible default, and their **error-vs-aggregate-demand
  correlation** diagnostic (error against how crowded the aggregate is) - cheap and worth adding to
  the EDA battery / R6 rehearsal analysis.

  **Kaggle REDD, forensics 2026-09-19** (`data/redd-kaggle/`, 35 chunk CSVs, 64 MB, 6 houses):
  NOT the original 1-s REDD - it is a **preprocessed ~3-s derivative** with **timestamps stripped**
  (bare integer index), float32 values, appliance subset = the SGN/attention selection (dish washer,
  fridge, washer dryer, microwave, stove, heater, CE), chunks split at gaps with backward-fill imputation
  (matches the SGN preprocessing recipe quoted in the inesylla README). Verified real by alignment:
  `redd_house5_0.csv` locks onto local `building_5` at 20 rows/min across 4 channels independently
  (furnace 0.69, microwave 0.74, washer dryer 0.73, heater 0.57, all one window: 2011-05-30 23:31 ->
  05-31 19:40) - so rate = 3 s, house numbering = REDD numbering, and chunk offsets are recoverable by
  the same correlation trick (+-1 min). Coverage is only ~12 d/house (house 5: 20 h) vs ~36-44 d in the
  local 1-min set. **Verdict: keep as a supplementary high-rate cross-check (3 s is native for REDD
  appliance channels); the 1-min local conversion stays the primary REDD set.** Kaggle source URL still
  needed for the provenance log; provenance chain = REDD -> third-party preprocess -> Kaggle upload.
  **Provenance supplied (user note): `kaggle.com/datasets/joragasy/redd-dataset`.**

### 3.3 Tier 3 - optional extras

- **AMPds2** - zenodo.org (probed 200), doi:10.5281/zenodo.591331 (verify the record page). 1 house,
  ~2 yr, native 1-min = exactly the Shelly 60 s rung.
  **Staged 2026-09-19: `data/raw/AMPds2/` (2.2 GB) - `Electricity_P.csv`: 730 d from 2012-04-01, 60 s,
  zero measured gaps, WHE aggregate + 20 appliance cols, mean 1,112 W.**
- **ECO** - dataverse.harvard.edu reachable; ETH host untested. 6 homes, 1 s, Swiss market.
- **DRED / GREEND** - DRED optional (hosts likely blocked; browser route). GREEND staged:
  **`data/raw/GREEND_0-2_300615/` (16 GB), 8 buildings, 134-500 daily files each, 1 s, plug-level MACs
  only (no aggregate column); buildings 4-5 contain mis-dated `dataset_2000-01-01.csv` files.**
  Naming trap checked 2026-09-19: Kaggle `lucabasa/dutch-energy` (Energy consumption of the
  Netherlands) is **not DRED** - it is the annual per-zipcode consumption tables published by the
  Dutch grid operators (Enexis, Liander, Stedin and peers), >=10 connections per row, no time series,
  no appliances. Useless for NILM; easy to hit while searching Dutch energy data.
- **tracebase** - appliance-only recordings (no aggregate): calibration signatures only; low priority.

### 3.4 Explicitly not collected

- UK-DALE 16 kHz waveforms (~3 TB) - see 6.
- Pecan Street Dataport - login-walled; only if a later experiment needs utility-granularity US data.
- UK HES - restricted access.

Full EDA over all staged datasets: `docs/reports/dataset_eda/` (00 overview + one executed
notebook + PDF export per dataset; marimo sources in `src/pipelines/02_fnd_eda_notebooks/`).

## 4. Where to look for data (routes + status)

Probed from this environment 2026-09-18:

| Route | Status | Use |
|---|---|---|
| data.ukedc.rl.ac.uk | 302 alive | UK-DALE |
| zenodo.org | 200 | AMPds2, DRED, many mirrors |
| dataverse.harvard.edu | 202 | REFIT / ECO mirrors |
| raw.githubusercontent.com | alive | GitHub-hosted datasets + conversion scripts |
| pure.lboro.ac.uk | blocked (000) | REFIT primary - use mirror / user download |
| redd.csail.mit.edu | dead/blocked (000) | - |

Established session fetch routes: OpenAlex API (429 -> 12 s backoff), arxiv.org/pdf, PMC.
Blocked: DDG, IEEE Xplore, ScienceDirect, mdpi, nature.com pages.

Discovery tips that work from here:

- OpenAlex full-text search for dataset names finds new mirrors via papers' data-availability sections.
- The nilmtk wiki "Data Sets" page (github.com/nilmtk/nilmtk) catalogs ~20 datasets with links -
  wiki pages need the browser route.
- The Neural NILM author's GitHub (JackKelly) holds REFIT -> UK-DALE-style conversion code, fetchable
  via raw.githubusercontent.

## 5. Intake procedure (every new dataset)

1. Land under `research-logs/<name>/`, keeping upstream structure and any README.
2. If > 50 MB: add to `.gitignore` immediately - raw data stays untracked and re-downloadable.
3. Convert to the common long table: `epoch_s, channel_id, watts` (+ `dataset_id, house_id`).
   The baseline loader reads only this shape; every dataset drops in unchanged.
4. Run the EDA battery; build the set's own reference; cross-compare vs `eda_reference_ukdale.json`
   (the domain-shift judge, PASS/FLAG bands).
5. For non-academic sources (Kaggle etc.): run the replay checks (`deprecated/analysis/repo-forensics/analyze_synthetic.py`
   logic) before trusting it.
6. Record row counts, span, rate, unlabeled ratio in the 2 inventory.
7. Wire into the baseline runs with a `dataset_id`; gates are re-derived per house/dataset on its
   calibration split only (never tuned on test).

### 5.1 The cleaning pass for real Shelly data (REFIT-derived, Shelly-adapted)

The REFIT cleaned release (Murray et al.) is worth copying in **shape**: an explicit issue taxonomy,
flag-not-delete processing, and a per-dataset issues log shipped with the data. The checks, mapped to
the Shelly setup:

| REFIT raw-data issue | Shelly equivalent | Check |
|---|---|---|
| sensor-network clock drift / unsynchronized meters | server-side timestamps (NTP), but ESPHome restarts resync mid-stream | interval histogram: gaps, duplicate timestamps, resync jumps |
| zero-filling during dropouts | WiFi dropouts; some integrations write 0 W on poll failure | runs of exact zeros vs device status; OFF vs NO-DATA distinction |
| wrong-timestamp blocks (hours/days off) | DST/timezone handling, HA time-source changes | duplicate/missing hour around DST transitions |
| mislabeled appliances | the calibration notes are the label source of truth | cross-check channel labels vs calibration session log |
| aggregate-submeter disagreement | live polling (fast) vs history API (300 s buckets) mixing | detect source switches: quantization changes between 1-s and bucketed levels |
| (REFIT-specific) | 30 VA measurement-floor quantization | step-size histogram vs the ~1.0 W reference noise floor |
| (REFIT-specific) | replay artifacts (the old pipeline bug class) | the `deprecated/analysis/repo-forensics/analyze_synthetic.py` check battery |

Process per capture session: run checks -> **flag, do not delete** (flagged intervals keep a status
column) -> ship the cleaned long table + `issues.md` per session (what was found, fixed, left as-is) ->
validate against ground truth. The validation is where we beat the REFIT setup: their cleaning was
validated with in-person surveys; **our calibration sessions make appliance state known-truth by
construction** - the cleaner is required to preserve those windows exactly, which validates the whole
cleaning pass for free on every house. Output also feeds the loop: flagged NO-DATA intervals become
explicit gaps in the UNKNOWN stream, never silent zeros.

## 6. The 16 kHz question (decision record)

**Decision: skip.** Reasons, in order of force:

1. The baseline plan is power-only (Shelly EM Gen3: 1-min stored, faster live polling). Waveforms add
   nothing to calibration economics, the 6/60/300 s rungs, or the transfer matrix.
2. V-I is a separate track (`vi-trajectory-hardware.md`): it needs a client-side kHz rig. The waveform-
   shape analysis that research does need is already served by the local PLAID 30 kHz captures.
3. 3 TB exceeds any storage plan here; streaming-while-downloading resampling is the right instinct if it
   were needed - the cheap variant would be a server-side filter keeping 1-s RMS aggregate + ~1 min
   waveform snippets per event (GB, not TB). But that answers a different experiment than the one the
   client needs first.
4. Even in the literature, high-frequency data helps complex/multi-state appliances - and the honest cheap
   route there is PLAID-style captures on the client's own devices (a few hours), not a UK download.

## 7. Storage budget

Low-frequency UK-DALE 2017: tens of GB (fine; raw data is .gitignore-ed, tracked tree stays ~11 MB).
16 kHz release ~3 TB (skip). REFIT cleaned ~2-4 GB. REDD original ~2 GB (skip - local 1-min conversion
suffices).

## 8. Arrival checklist for the current download

- [x] houses 1-5 present, each with `labels.dat` (checked 2026-09-19; extracted to
  `data/raw/ukdale-full/house_N/` - house_1 14 GB/53 ch, house_2 913 MB/19 ch, house_3 34 MB/5 ch,
  house_4 171 MB/6 ch, house_5 809 MB/25 ch)
- [x] aggregate rate check: **all five houses are 6-s aggregates in this release - no 1-s aggregate**
  (1-s mains exists only in the separate 2015 mains zips). Native rung = 6 s; 60/300 via floor-divide.
- [x] aggregate gap map (rows vs span at 6 s):

  | house | rows | span | coverage | >10-min gaps | W range |
  |---|---|---|---|---|---|
  | 1 | 21,837,636 | 1628.8 d | 93.1% | 67 | 46-8,788 |
  | 2 | 2,780,373 | 234.5 d | 82.3% | 12 | 109-16,529 |
  | 3 | 512,327 | 39.4 d | 90.4% | 19 | 4-4,090 |
  | 4 | 2,186,446 | 205.6 d | 73.8% | 2 | 119-8,765 |
  | 5 | 1,763,101 | 137.1 d | 89.3% | 5 | 347-9,644 |

  Gaps -> NO-DATA, never zeros. R7-class label mapping across houses: fridge-class = house_1 `fridge`,
  house_2 `fridge`, house_4 `freezer`, house_5 `fridge_freezer` (5/5 houses); kettle = 5/5
  (house_4 composite `kettle_radio`); washer = house_1/house_2 `washing_machine`, house_5
  `washer_dryer`, house_4 composite; dish washer = houses 1/2/5; microwave = houses 1/2/5. No
  same-house fridge+freezer pair exists anywhere, so no intra-house merge is needed.
- [x] heavy dirs already gitignored (`data/` covers everything: `raw/`, `fnd/`, `gold/`)
- [ ] rebuild `eda_reference_ukdale.json`; re-run R1-R5
- [ ] R7 transfer matrix: house 1 -> houses 2-5 (+ REDD homes)