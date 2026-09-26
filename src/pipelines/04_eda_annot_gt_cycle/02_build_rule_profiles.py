import os

import numpy as np
import pandas as pd

from wattwiser.experiments.data_loader import load_power_series
from wattwiser.experiments.segmentation import build_episodes
from wattwiser.paths import ROOT

DATASET = "ukdale"
HOUSES = ("house_1", "house_2", "house_3", "house_4", "house_5")
PROGRAM = ("washing_machine", "dishwasher")
BURST = ("kettle", "microwave")
DUTY = ("fridge",)
CYCLE_RULE = dict(dwell=600.0, merge=600.0)  # program class (settled in 01)
BURST_RULE = dict(dwell=30.0, merge=60.0)  # burst class: raw episodes
DUTY_RULE = dict(dwell=30.0, merge=12.0)  # duty class: compressor runs
CYCLE_LIKE_S = 600.0
CYCLE_LIKE_WH = 100.0
SPLIT_FRAC = 0.75
SOURCE_RULE = "rule_v1"

# Threshold decisions per (house, device). thr_used_w is what cycle GT uses;
# thr_source says where it came from; notes carry the measured justification.
THR = {
    ("house_1", "washing_machine"): dict(thr=90.0, source="gold"),
    ("house_1", "dishwasher"): dict(thr=60.5, source="gold"),
    ("house_1", "kettle"): dict(thr=1173.0, source="gold"),
    ("house_1", "microwave"): dict(thr=762.0, source="gold"),
    ("house_1", "fridge"): dict(thr=44.5, source="gold"),
    ("house_2", "washing_machine"): dict(thr=81.0, source="gold"),
    ("house_2", "dishwasher"): dict(
        thr=90.0, source="override",
        note="gold thr 984 W is heater-only (on-power p50 2001 W); 90 W keeps pump/fill phases",
    ),
    ("house_2", "kettle"): dict(thr=1477.0, source="gold"),
    ("house_2", "microwave"): dict(
        thr=500.0, source="override",
        note="gold thr 13 W sits in standby noise (on-power p50 26 W); 8,320 samples > 1 kW confirm real use",
    ),
    ("house_2", "fridge"): dict(
        thr=40.0, source="override",
        note="gold thr 5.5 W inside standby noise (on-power p50 11 W); 40 W is the compressor floor",
    ),
    ("house_3", "kettle"): dict(thr=1475.0, source="gold"),
    ("house_4", "kettle"): dict(thr=1083.0, source="gold"),
    ("house_4", "microwave"): dict(
        thr=90.5, source="excluded",
        note="mixed channel (washing_machine_microwave_breadmaker): contaminated by WM and breadmaker activations; not usable as microwave GT",
    ),
    ("house_4", "fridge"): dict(thr=45.5, source="gold"),
    ("house_5", "washing_machine"): dict(
        thr=50.0, source="override",
        note="gold thr 7.5 W is standby noise (9 day-scale mega-episodes); washer_dryer label - some cycles include a drying phase",
    ),
    ("house_5", "dishwasher"): dict(thr=48.5, source="gold"),
    ("house_5", "kettle"): dict(thr=1445.0, source="gold"),
    ("house_5", "microwave"): dict(
        thr=25.0, source="excluded",
        note="channel reads a constant ~50 W (p99 51 W) - no microwave signal; excluded",
    ),
    ("house_5", "fridge"): dict(thr=54.0, source="gold"),
}

# Devices present per house (canonical names, from the gold appliance map).
PRESENT = {
    "house_1": ("washing_machine", "dishwasher", "kettle", "microwave", "fridge"),
    "house_2": ("washing_machine", "dishwasher", "kettle", "microwave", "fridge"),
    "house_3": ("kettle",),
    "house_4": ("kettle", "microwave", "fridge"),
    "house_5": ("washing_machine", "dishwasher", "kettle", "microwave", "fridge"),
}

# House_1 keeps the established contract split from 01_ukdale_gt_cycle_eda;
# the other houses reserve the tail (1 - SPLIT_FRAC) of their span as test.
SPLIT_FIXED_US = {
    "house_1": int(pd.Timestamp("2013-10-01", tz="UTC").value / 1000),
}

# All-device metadata (extended profile): every gold channel gets a row with
# an in_focus flag and a suggested class. Class is a name-based prior; the
# 04_ukdale_all_device_eda notebook verifies it against measured stats and
# the figures before anything downstream relies on it.
GENERIC_THR_W = 20.0  # generic on-threshold for non-focus metadata rows
GENERIC_RULE = dict(dwell=30.0, merge=60.0)  # same shape as the burst rule

NAME_CLASS = {
    # automatic multi-phase programs
    "washing_machine": "program", "dishwasher": "program",
    "breadmaker": "program", "rice_cooker": "program",
    "coffee_machine": "program",
    # short stereotyped manual bursts
    "kettle": "burst", "microwave": "burst", "toaster": "burst",
    "hair_dryer": "burst", "hairdryer": "burst", "straighteners": "burst",
    "nespresso_pixie": "burst",
    # thermostatic / periodic
    "fridge": "duty", "solar_thermal_pump": "duty",
    # long user-controlled sessions
    "gas_oven": "manual", "oven": "manual", "electric_hob": "manual",
    "cooker": "manual", "iron": "manual", "steam_iron": "manual",
    "soldering_iron": "manual", "hoover": "manual", "vacuum_cleaner": "manual",
    "running_machine": "manual", "treadmill": "manual",
    # thermostatic heating
    "boiler": "heating", "gas_boiler": "heating", "electric_heater": "heating",
    # network / standby draw
    "adsl_router": "always_on", "modem": "always_on", "router": "always_on",
    "server": "always_on", "server_hdd": "always_on", "core2_server": "always_on",
    "network_attached_storage": "always_on", "gige_usbhub": "always_on",
    "data_logger_pc": "always_on",
    # entertainment / computing, user-driven variable draw
    "tv": "electronics", "primary_tv": "electronics", "24_inch_lcd": "electronics",
    "24_inch_lcd_bedroom": "electronics", "monitor": "electronics",
    "laptop": "electronics", "laptop2": "electronics", "atom_pc": "electronics",
    "i7_desktop": "electronics", "office_pc": "electronics", "htpc": "electronics",
    "ps4": "electronics", "playstation": "electronics", "sky_hd_box": "electronics",
    "amp_livingroom": "electronics", "hifi_office": "electronics",
    "home_theatre_amp": "electronics", "speakers": "electronics",
    "stereo_speakers_bedroom": "electronics", "subwoofer_livingroom": "electronics",
    "dab_radio_livingroom": "electronics", "kitchen_radio": "electronics",
    "kitchen_phone_stereo": "electronics", "projector": "electronics",
    "led_printer": "electronics", "lcd_office": "electronics",
    "ipad_charger": "electronics", "samsung_charger": "electronics",
    "battery_charger": "electronics", "bedroom_chargers": "electronics",
    "office_fan": "electronics", "baby_monitor_tx": "electronics",
    "tv_dvd_digibox_lamp": "electronics",
    # lighting
    "bedroom_d_lamp": "lighting", "bedroom_ds_lamp": "lighting",
    "childs_ds_lamp": "lighting", "childs_table_lamp": "lighting",
    "kitchen_dt_lamp": "lighting", "kitchen_lamp2": "lighting",
    "kitchen_lights": "lighting", "lighting_circuit": "lighting",
    "livingroom_lamp_tv": "lighting", "livingroom_s_lamp": "lighting",
    "livingroom_s_lamp2": "lighting", "office_lamp1": "lighting",
    "office_lamp2": "lighting", "office_lamp3": "lighting",
    "utilityrm_lamp": "lighting",
}


def suggest_class(dev):
    """Name-based class prior for the all-device metadata rows."""
    return NAME_CLASS.get(dev, "misc")



def modal_dt_s(ts_us):
    d = np.diff(ts_us) / 1e6
    d = d[(d > 0) & (d < 60)]
    if d.size == 0:
        return float("nan")
    vals, counts = np.unique(np.round(d, 1), return_counts=True)
    return float(vals[np.argmax(counts)])


def split_for_house(mains_ts, house):
    if house in SPLIT_FIXED_US:
        return SPLIT_FIXED_US[house]
    t0, t1 = int(mains_ts[0]), int(mains_ts[-1])
    cut = t0 + int(SPLIT_FRAC * (t1 - t0))
    day_us = 86_400_000_000
    return (cut // day_us) * day_us  # floor to UTC midnight


def cycle_like(ep):
    return ep[(ep["dur_s"] >= CYCLE_LIKE_S) & (ep["energy_wh"] >= CYCLE_LIKE_WH)]


def rule_for(dev):
    if dev in PROGRAM:
        return CYCLE_RULE
    if dev in BURST:
        return BURST_RULE
    return DUTY_RULE


def class_of(dev):
    if dev in PROGRAM:
        return "program"
    if dev in BURST:
        return "burst"
    return "duty"


def profile_row(house, dev, split_us):
    spec = THR.get((house, dev), dict(thr=float("nan"), source="absent"))
    row = dict(
        house=house,
        device=dev,
        in_focus=True,
        **{"class": class_of(dev)},
        thr_source=spec["source"],
        thr_used_w=spec["thr"],
        dwell_s=rule_for(dev)["dwell"],
        merge_s=rule_for(dev)["merge"],
        n_cycles=0,
        n_cycles_cal=0,
        dur_p50_min=float("nan"),
        energy_p50_wh=float("nan"),
        power_mean_w=float("nan"),
        power_peak_p50_w=float("nan"),
        power_peak_p95_w=float("nan"),
        on_power_p50_w=float("nan"),
        on_power_p99_w=float("nan"),
        notes=spec.get("note", ""),
    )
    if spec["source"] == "excluded" or spec["thr"] != spec["thr"]:
        return row, None
    df = load_power_series(gold_parquet_path(DATASET, house, dev))
    ts = df["ts_us"].to_numpy(np.int64)
    w = df["w"].to_numpy(float)
    on = w > spec["thr"]
    if on.any():
        row["on_power_p50_w"] = float(np.percentile(w[on], 50))
        row["on_power_p99_w"] = float(np.percentile(w[on], 99))
    if dev in PROGRAM:
        ep = build_episodes(df, spec["thr"], CYCLE_RULE["dwell"], CYCLE_RULE["merge"], 60.0)
        sel = cycle_like(ep)
        rule_cycles = None  # program cycles live in cycles.csv (manual marks)
    elif dev in BURST:
        ep = build_episodes(df, spec["thr"], BURST_RULE["dwell"], BURST_RULE["merge"], 60.0)
        sel = ep
        rule_cycles = ep
    else:  # duty: compressor runs, reported for reference only
        ep = build_episodes(df, spec["thr"], DUTY_RULE["dwell"], DUTY_RULE["merge"], 60.0)
        sel = ep
        rule_cycles = None  # duty is never written to rule_cycles
    row["n_cycles"] = int(len(sel))
    row["n_cycles_cal"] = int((sel["t_on_us"] < split_us).sum()) if len(sel) else 0
    if len(sel):
        row["dur_p50_min"] = float(sel["dur_s"].median() / 60.0)
        row["energy_p50_wh"] = float(sel["energy_wh"].median())
        pmean = sel["energy_wh"] / (sel["dur_s"] / 3600.0).replace(0.0, np.nan)
        row["power_mean_w"] = float(pmean.median())
        peaks = np.array([
            float(w[np.searchsorted(ts, int(r.t_on_us)):np.searchsorted(ts, int(r.t_off_us), side="right")].max())
            for r in sel.itertuples()
        ])
        row["power_peak_p50_w"] = float(np.percentile(peaks, 50))
        row["power_peak_p95_w"] = float(np.percentile(peaks, 95))
    cycles_out = None
    if dev in BURST and rule_cycles is not None and len(rule_cycles):
        cycles_out = rule_cycles.copy()
        cycles_out["source"] = SOURCE_RULE
    return row, cycles_out


def meta_row(house, dev, split_us):
    '''Generic-stats row for a non-focus channel (metadata, not cycle GT).

    Episodes use the generic 20 W threshold with the burst rule shape; the
    04_ukdale_all_device_eda notebook verifies the suggested class before
    anything downstream relies on these rows.
    '''
    df = load_power_series(gold_parquet_path(DATASET, house, dev))
    w = df["w"].to_numpy(float)
    on = w > GENERIC_THR_W
    row = dict(
        house=house,
        device=dev,
        in_focus=False,
        **{"class": suggest_class(dev)},
        thr_source="generic",
        thr_used_w=GENERIC_THR_W,
        dwell_s=GENERIC_RULE["dwell"],
        merge_s=GENERIC_RULE["merge"],
        n_cycles=0,
        n_cycles_cal=0,
        dur_p50_min=float("nan"),
        energy_p50_wh=float("nan"),
        power_mean_w=float("nan"),
        power_peak_p50_w=float("nan"),
        power_peak_p95_w=float("nan"),
        on_power_p50_w=float("nan"),
        on_power_p99_w=float("nan"),
        notes="all-device metadata row: generic 20 W threshold, burst-shaped episodes",
    )
    if on.any():
        row["on_power_p50_w"] = float(np.percentile(w[on], 50))
        row["on_power_p99_w"] = float(np.percentile(w[on], 99))
    ep = build_episodes(df, GENERIC_THR_W, GENERIC_RULE["dwell"], GENERIC_RULE["merge"], 60.0)
    row["n_cycles"] = int(len(ep))
    row["n_cycles_cal"] = int((ep["t_on_us"] < split_us).sum()) if len(ep) else 0
    if len(ep):
        row["dur_p50_min"] = float(ep["dur_s"].median() / 60.0)
        row["energy_p50_wh"] = float(ep["energy_wh"].median())
        pmean = ep["energy_wh"] / (ep["dur_s"] / 3600.0).replace(0.0, np.nan)
        row["power_mean_w"] = float(pmean.median())
    return row


def main():
    for house in HOUSES:
        out_dir = os.path.join(ROOT, "data", "gold_annot", DATASET, house)
        os.makedirs(out_dir, exist_ok=True)
        mains_df = load_power_series(gold_parquet_path(DATASET, house, "mains"))
        m_ts = mains_df["ts_us"].to_numpy(np.int64)
        split_us = split_for_house(m_ts, house)
        pd.DataFrame([dict(
            house=house,
            split_us=split_us,
            split_date_utc=str(pd.to_datetime(split_us, unit="us").date()),
            basis=("established 2013-10-01 contract (01_ukdale_gt_cycle_eda)"
                   if house in SPLIT_FIXED_US else
                   "floor to UTC midnight of t0 + 75% of mains span"),
        )]).to_csv(os.path.join(out_dir, "splits.csv"), index=False)
        rows, burst_frames = [], []
        gold_dir = os.path.join(ROOT, "data", "gold", DATASET, house)
        all_devs = sorted(
            f[: -len(".parquet")]
            for f in os.listdir(gold_dir)
            if f.endswith(".parquet") and f != "mains.parquet"
        )
        ordered = list(PRESENT[house]) + [d for d in all_devs if d not in PRESENT[house]]
        for dev in ordered:
            if dev in PRESENT[house]:
                row, cycles_out = profile_row(house, dev, split_us)
                rows.append(row)
                if cycles_out is not None:
                    cycles_out.insert(0, "device", dev)
                    burst_frames.append(cycles_out[["device", "t_on_us", "t_off_us", "dur_s", "energy_wh", "source"]])
            else:
                rows.append(meta_row(house, dev, split_us))
        pd.DataFrame(rows).to_csv(os.path.join(out_dir, "device_profile.csv"), index=False)
        if burst_frames:
            pd.concat(burst_frames, ignore_index=True).to_csv(
                os.path.join(out_dir, "rule_cycles.csv"), index=False
            )
        else:
            with open(os.path.join(out_dir, "rule_cycles.csv"), "w"):
                pass
        n_rc = sum(len(f) for f in burst_frames)
        cls_counts = pd.Series([r["class"] for r in rows]).value_counts().to_dict()
        print(f"{house}: split {pd.to_datetime(split_us, unit='us'):%Y-%m-%d}, "
              f"devices {len(rows)} (focus {sum(1 for r in rows if r['in_focus'])}), "
              f"rule_cycles {n_rc}, classes {cls_counts}")


if __name__ == "__main__":
    main()

