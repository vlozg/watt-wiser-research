from pathlib import Path

import numpy as np

from pattern_matching_lib import (
    load_appliance_data,
    extract_sessions,
    build_appliance_profile,
    match_profile,
    calculate_metrics,
)


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[3]

DATA_ROOT = (
    ROOT
    / "data"
    / "gold"
    / "ukdale"
)


# ============================================================
# CONFIGURATION
# ============================================================

HOUSE = "house_1"
APPLIANCE = "kettle"

# Same split used in the Seq2Seq experiment
SPLIT_US = 1380585600000000

K = 5


# ============================================================
# LOAD
# ============================================================

print("=" * 60)
print("PATTERN / PROFILE MATCHING")
print("=" * 60)

print(f"House: {HOUSE}")
print(f"Appliance: {APPLIANCE}")
print()

train, test = load_appliance_data(
    data_root=DATA_ROOT,
    house=HOUSE,
    appliance=APPLIANCE,
    split_us=SPLIT_US,
)

print(
    f"Training rows: {len(train):,}"
)

print(
    f"Test rows: {len(test):,}"
)


# ============================================================
# CALIBRATION SESSIONS
# ============================================================

sessions = extract_sessions(
    train
)

print(
    f"Available calibration sessions: "
    f"{len(sessions):,}"
)

if len(sessions) < K:

    raise RuntimeError(
        f"Only {len(sessions)} calibration "
        f"sessions available, but K={K}."
    )


# ============================================================
# SELECT K SESSIONS
# ============================================================

rng = np.random.default_rng(42)

selected_indices = rng.choice(
    len(sessions),
    size=K,
    replace=False,
)

selected_sessions = [
    sessions[i]
    for i in selected_indices
]


# ============================================================
# BUILD PROFILE
# ============================================================

profile = build_appliance_profile(
    sessions=selected_sessions,
    appliance=APPLIANCE,
)

print()
print("CALIBRATION PROFILE")
print("-" * 60)

print(
    f"Mean power: "
    f"{profile.mean_power_w:.2f} W"
)

print(
    f"Median power: "
    f"{profile.median_power_w:.2f} W"
)

print(
    f"Power std: "
    f"{profile.std_power_w:.2f} W"
)

print(
    f"Mean duration: "
    f"{profile.mean_duration_s:.2f} s"
)

print(
    f"Calibration sessions: "
    f"{profile.n_sessions}"
)


# ============================================================
# MATCH AGAINST TEST DATA
# ============================================================

print()
print("Running profile matching...")

result = match_profile(
    aggregate_power=test["mains_w"],
    profile=profile,
)


# ============================================================
# EVALUATE
# ============================================================

true_power = (
    test["appliance_w"]
    .to_numpy(
        dtype=float
    )
)

predicted_power = (
    result["predicted_power_w"]
    .to_numpy(
        dtype=float
    )
)

metrics = calculate_metrics(
    true_power,
    predicted_power,
)


# ============================================================
# RESULTS
# ============================================================

print()
print("RESULTS")
print("-" * 60)

for name, value in metrics.items():

    print(
        f"{name}: {value:.6f}"
    )

print()
print("=" * 60)
print("DONE")
print("=" * 60)