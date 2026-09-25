from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pattern_matching_lib import (
    appliance_exists,
    build_appliance_profile,
    calculate_metrics,
    extract_sessions,
    load_appliance_data,
    match_profile,
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

RESULTS_DIR = (
    ROOT
    / "data"
    / "results"
    / "pattern_matching"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# EXPERIMENT CONFIGURATION
# ============================================================

HOUSES = [
    "house_1",
    "house_2",
    "house_5",
]

APPLIANCES = [
    "kettle",
    "microwave",
    "fridge",
    "washing_machine",
    "dishwasher",
]

K_VALUES = [
    1,
    3,
    5,
    10,
    20,
]

N_DRAWS = 10

# Same split used in the Seq2Seq experiment
SPLIT_US = 1380585600000000

# Fixed base seed for reproducibility
BASE_SEED = 20260924

HOUSE_SEEDS = {
    "house_1": 1,
    "house_2": 2,
    "house_5": 5,
}


# ============================================================
# RUN ONE EXPERIMENT
# ============================================================

def run_one(
    train,
    test,
    sessions,
    house,
    appliance,
    k,
    draw,
):

    # --------------------------------------------------------
    # Reproducible random seed
    # --------------------------------------------------------

    seed = (
        BASE_SEED
        + HOUSE_SEEDS[house] * 10000
        + k * 100
        + draw
    )

    rng = np.random.default_rng(
        seed
    )

    # --------------------------------------------------------
    # Select K calibration sessions
    # --------------------------------------------------------

    if len(sessions) < k:
        return None

    selected_indices = rng.choice(
        len(sessions),
        size=k,
        replace=False,
    )

    selected_sessions = [
        sessions[i]
        for i in selected_indices
    ]

    # --------------------------------------------------------
    # Build appliance profile
    # --------------------------------------------------------

    profile = build_appliance_profile(
        sessions=selected_sessions,
        appliance=appliance,
    )

    # --------------------------------------------------------
    # Match calibrated profile against test mains
    # --------------------------------------------------------

    result = match_profile(
        aggregate_power=test["mains_w"],
        profile=profile,
    )

    # --------------------------------------------------------
    # Ground truth
    # --------------------------------------------------------

    y_true = (
        test["appliance_w"]
        .to_numpy(
            dtype=float
        )
    )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    y_pred = (
        result["predicted_power_w"]
        .to_numpy(
            dtype=float
        )
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    metrics = calculate_metrics(
        y_true,
        y_pred,
    )

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "house": house,
        "appliance": appliance,
        "k": k,
        "draw": draw,

        "n_calibration_sessions": k,

        "profile_mean_power_w":
            profile.mean_power_w,

        "profile_std_power_w":
            profile.std_power_w,

        "profile_median_power_w":
            profile.median_power_w,

        "profile_mean_duration_s":
            profile.mean_duration_s,

        "profile_std_duration_s":
            profile.std_duration_s,

        "mae_w":
            metrics["mae_w"],

        "nmae":
            metrics["nmae"],

        "energy_error":
            metrics["energy_error"],

        "f1":
            metrics["f1"],
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "EXPERIMENT 2 — "
        "PATTERN / PROFILE MATCHING"
    )
    print("=" * 70)

    print()
    print(
        "Houses:",
        HOUSES,
    )

    print(
        "Appliances:",
        APPLIANCES,
    )

    print(
        "K values:",
        K_VALUES,
    )

    print(
        "Draws per K:",
        N_DRAWS,
    )

    print()

    all_results = []

    # ========================================================
    # HOUSE LOOP
    # ========================================================

    for house in HOUSES:

        print()
        print("=" * 70)
        print(
            f"HOUSE: {house}"
        )
        print("=" * 70)

        # ====================================================
        # APPLIANCE LOOP
        # ====================================================

        for appliance in APPLIANCES:

            # ------------------------------------------------
            # Check appliance exists
            # ------------------------------------------------

            if not appliance_exists(
                DATA_ROOT,
                house,
                appliance,
            ):

                print(
                    f"\nSKIP: {house} / "
                    f"{appliance} "
                    f"(data not found)"
                )

                continue

            print()
            print(
                f"Loading: "
                f"{house} / {appliance}"
            )

            # ------------------------------------------------
            # Load data
            # ------------------------------------------------

            train, test = load_appliance_data(
                data_root=DATA_ROOT,
                house=house,
                appliance=appliance,
                split_us=SPLIT_US,
            )

            print(
                f"Train rows: "
                f"{len(train):,}"
            )

            print(
                f"Test rows: "
                f"{len(test):,}"
            )

            # ------------------------------------------------
            # Extract calibration sessions
            # ------------------------------------------------

            sessions = extract_sessions(
                train
            )

            print(
                f"Calibration sessions: "
                f"{len(sessions):,}"
            )

            if len(sessions) == 0:

                print(
                    "SKIP: "
                    "no calibration sessions"
                )

                continue

            # =================================================
            # K LOOP
            # =================================================

            for k in K_VALUES:

                if len(sessions) < k:

                    print(
                        f"K={k}: SKIPPED "
                        f"(only "
                        f"{len(sessions)} "
                        f"sessions available)"
                    )

                    continue

                print()
                print(
                    f"Running "
                    f"{house} / "
                    f"{appliance} / "
                    f"K={k}"
                )

                # =============================================
                # DRAW LOOP
                # =============================================

                for draw in range(
                    N_DRAWS
                ):

                    result = run_one(
                        train=train,
                        test=test,
                        sessions=sessions,
                        house=house,
                        appliance=appliance,
                        k=k,
                        draw=draw,
                    )

                    if result is not None:

                        all_results.append(
                            result
                        )

                    print(
                        f"  Draw "
                        f"{draw + 1}/"
                        f"{N_DRAWS} complete"
                    )

    # ========================================================
    # CHECK RESULTS
    # ========================================================

    if not all_results:

        raise RuntimeError(
            "No experiment results were produced."
        )

    # ========================================================
    # RAW RESULTS
    # ========================================================

    results_df = pd.DataFrame(
        all_results
    )

    raw_path = (
        RESULTS_DIR
        / "pattern_matching_raw.csv"
    )

    results_df.to_csv(
        raw_path,
        index=False,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary_df = (
        results_df
        .groupby(
            [
                "house",
                "appliance",
                "k",
            ]
        )
        [
            [
                "mae_w",
                "nmae",
                "energy_error",
                "f1",
            ]
        ]
        .agg(
            [
                "mean",
                "std",
            ]
        )
        .reset_index()
    )

    summary_path = (
        RESULTS_DIR
        / "pattern_matching_summary.csv"
    )

    summary_df.to_csv(
        summary_path,
        index=False,
    )

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print()
    print("=" * 70)
    print(
        "EXPERIMENT 2 COMPLETE"
    )
    print("=" * 70)

    print()
    print(
        f"Total completed runs: "
        f"{len(results_df):,}"
    )

    print()
    print(
        "SUMMARY"
    )

    print("-" * 70)

    print(
        summary_df.to_string(
            index=False
        )
    )

    print()
    print(
        "Raw results:"
    )

    print(
        raw_path
    )

    print()
    print(
        "Summary results:"
    )

    print(
        summary_path
    )

    print()
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()