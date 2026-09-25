from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_CADENCE_SECONDS = 6
ON_THRESHOLD_W = 50.0


# ============================================================
# DATA STRUCTURE
# ============================================================

@dataclass
class ApplianceProfile:
    appliance: str

    mean_power_w: float
    std_power_w: float
    median_power_w: float
    q10_power_w: float
    q90_power_w: float

    mean_duration_s: float
    std_duration_s: float

    mean_rise_w: float
    std_rise_w: float

    mean_fall_w: float
    std_fall_w: float

    n_sessions: int


# ============================================================
# DATA LOADING
# ============================================================

def load_appliance_data(
    data_root: str | Path,
    house: str = "house_1",
    appliance: str = "kettle",
    split_us: int = 1380585600000000,
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    data_root = Path(data_root)

    house_dir = data_root / house

    mains_path = house_dir / "mains.parquet"
    appliance_path = house_dir / f"{appliance}.parquet"

    if not mains_path.exists():
        raise FileNotFoundError(
            f"Mains file not found:\n{mains_path}"
        )

    if not appliance_path.exists():
        raise FileNotFoundError(
            f"Appliance file not found:\n{appliance_path}"
        )

    # ----------------------------
    # Load mains
    # ----------------------------

    mains = pd.read_parquet(
        mains_path
    )[["ts_us", "w"]]

    # ----------------------------
    # Load appliance
    # ----------------------------

    appliance_df = pd.read_parquet(
        appliance_path
    )[["ts_us", "w"]]

    # ----------------------------
    # Convert timestamps
    # ----------------------------

    mains["time"] = pd.to_datetime(
        mains["ts_us"],
        unit="us",
        utc=True,
    )

    appliance_df["time"] = pd.to_datetime(
        appliance_df["ts_us"],
        unit="us",
        utc=True,
    )

    # ----------------------------
    # Resample to 6 seconds
    # Same as Seq2Seq experiment
    # ----------------------------

    mains = (
        mains
        .set_index("time")["w"]
        .resample("6s")
        .mean()
        .rename("mains_w")
    )

    appliance_df = (
        appliance_df
        .set_index("time")["w"]
        .resample("6s")
        .mean()
        .rename("appliance_w")
    )

    # ----------------------------
    # Align
    # ----------------------------

    df = pd.concat(
        [
            mains,
            appliance_df,
        ],
        axis=1,
    )

    df = (
        df
        .dropna()
        .sort_index()
    )

    # ----------------------------
    # Train/test split
    # ----------------------------

    split_time = pd.to_datetime(
        split_us,
        unit="us",
        utc=True,
    )

    train = df[
        df.index < split_time
    ].copy()

    test = df[
        df.index >= split_time
    ].copy()

    return (
        train.reset_index(),
        test.reset_index(),
    )


def appliance_exists(
    data_root: str | Path,
    house: str,
    appliance: str,
) -> bool:

    data_root = Path(data_root)

    return (
        data_root
        / house
        / f"{appliance}.parquet"
    ).exists()


# ============================================================
# EVENT DETECTION
# ============================================================

def detect_appliance_events(
    appliance_power: pd.Series,
    threshold_w: float = ON_THRESHOLD_W,
    min_duration_samples: int = 2,
) -> List[Tuple[int, int]]:

    power = appliance_power.to_numpy(
        dtype=float
    )

    on = power >= threshold_w

    events = []

    start = None

    for i, state in enumerate(on):

        if state and start is None:
            start = i

        elif not state and start is not None:

            end = i - 1

            if (
                end - start + 1
                >= min_duration_samples
            ):
                events.append(
                    (start, end)
                )

            start = None

    # Event continues to end
    if start is not None:

        end = len(on) - 1

        if (
            end - start + 1
            >= min_duration_samples
        ):
            events.append(
                (start, end)
            )

    return events


# ============================================================
# SESSION EXTRACTION
# ============================================================

def extract_sessions(
    df: pd.DataFrame,
    threshold_w: float = ON_THRESHOLD_W,
) -> List[pd.DataFrame]:

    events = detect_appliance_events(
        df["appliance_w"],
        threshold_w=threshold_w,
    )

    sessions = []

    for start, end in events:

        session = df.iloc[
            start:end + 1
        ].copy()

        if len(session) > 0:
            sessions.append(session)

    return sessions


# ============================================================
# PROFILE CREATION
# ============================================================

def build_appliance_profile(
    sessions: List[pd.DataFrame],
    appliance: str,
    cadence_seconds: int = DEFAULT_CADENCE_SECONDS,
) -> ApplianceProfile:

    if not sessions:
        raise ValueError(
            f"No calibration sessions available "
            f"for {appliance}"
        )

    mean_powers = []
    durations = []
    rises = []
    falls = []

    for session in sessions:

        power = session[
            "appliance_w"
        ].to_numpy(
            dtype=float
        )

        mean_power = float(
            np.mean(power)
        )

        duration = (
            len(power)
            * cadence_seconds
        )

        rise = float(
            np.max(power)
            - power[0]
        )

        fall = float(
            power[-1]
            - np.min(power)
        )

        mean_powers.append(
            mean_power
        )

        durations.append(
            duration
        )

        rises.append(
            rise
        )

        falls.append(
            fall
        )

    mean_powers = np.asarray(
        mean_powers
    )

    durations = np.asarray(
        durations
    )

    rises = np.asarray(
        rises
    )

    falls = np.asarray(
        falls
    )

    return ApplianceProfile(

        appliance=appliance,

        mean_power_w=float(
            np.mean(mean_powers)
        ),

        std_power_w=float(
            np.std(mean_powers)
        ),

        median_power_w=float(
            np.median(mean_powers)
        ),

        q10_power_w=float(
            np.percentile(
                mean_powers,
                10,
            )
        ),

        q90_power_w=float(
            np.percentile(
                mean_powers,
                90,
            )
        ),

        mean_duration_s=float(
            np.mean(durations)
        ),

        std_duration_s=float(
            np.std(durations)
        ),

        mean_rise_w=float(
            np.mean(rises)
        ),

        std_rise_w=float(
            np.std(rises)
        ),

        mean_fall_w=float(
            np.mean(falls)
        ),

        std_fall_w=float(
            np.std(falls)
        ),

        n_sessions=len(sessions),
    )


# ============================================================
# PROFILE MATCHING
# ============================================================

def calculate_similarity(
    power_window: np.ndarray,
    profile: ApplianceProfile,
) -> float:

    if len(power_window) == 0:
        return float("inf")

    mean_power = float(
        np.mean(power_window)
    )

    duration_s = (
        len(power_window)
        * DEFAULT_CADENCE_SECONDS
    )

    power_error = (
        abs(
            mean_power
            - profile.mean_power_w
        )
        / max(
            profile.mean_power_w,
            1.0,
        )
    )

    duration_error = (
        abs(
            duration_s
            - profile.mean_duration_s
        )
        / max(
            profile.mean_duration_s,
            1.0,
        )
    )

    score = (
        0.7 * power_error
        + 0.3 * duration_error
    )

    return float(score)


def match_profile(
    aggregate_power: pd.Series,
    profile: ApplianceProfile,
    threshold: float = 0.50,
    min_window_samples: int = 2,
) -> pd.DataFrame:

    values = aggregate_power.to_numpy(
        dtype=np.float64
    )

    n = len(values)

    predictions = np.zeros(
        n,
        dtype=np.float64,
    )

    scores = np.full(
        n,
        np.inf,
        dtype=np.float64,
    )

    target_window = max(
        min_window_samples,
        int(
            round(
                profile.mean_duration_s
                / DEFAULT_CADENCE_SECONDS
            )
        ),
    )

    # Prevent extremely long windows.
    target_window = min(
        target_window,
        120,
    )

    if target_window >= n:
        return pd.DataFrame(
            {
                "predicted_power_w": predictions,
                "match_score": scores,
            },
            index=aggregate_power.index,
        )

    # --------------------------------------------------------
    # Rolling mean using cumulative sum
    # --------------------------------------------------------

    cumulative = np.concatenate(
        [
            np.array([0.0]),
            np.cumsum(values),
        ]
    )

    window_sums = (
        cumulative[target_window:]
        - cumulative[:-target_window]
    )

    window_means = (
        window_sums
        / target_window
    )

    # --------------------------------------------------------
    # Similarity
    # --------------------------------------------------------

    power_error = (
        np.abs(
            window_means
            - profile.mean_power_w
        )
        / max(
            profile.mean_power_w,
            1.0,
        )
    )

    duration_s = (
        target_window
        * DEFAULT_CADENCE_SECONDS
    )

    duration_error = (
        abs(
            duration_s
            - profile.mean_duration_s
        )
        / max(
            profile.mean_duration_s,
            1.0,
        )
    )

    scores_window = (
        0.7 * power_error
        + 0.3 * duration_error
    )

    matched = (
        scores_window
        <= threshold
    )

    # --------------------------------------------------------
    # Write predictions
    # --------------------------------------------------------

    matched_indices = np.where(
        matched
    )[0]

    for start in matched_indices:

        end = (
            start
            + target_window
        )

        score = (
            scores_window[start]
        )

        current = scores[
            start:end
        ]

        better = (
            score < current
        )

        if np.any(better):

            predictions[
                start:end
            ][better] = (
                profile.mean_power_w
            )

            scores[
                start:end
            ][better] = score

    return pd.DataFrame(
        {
            "predicted_power_w":
                predictions,

            "match_score":
                scores,
        },
        index=aggregate_power.index,
    )

# ============================================================
# METRICS
# ============================================================

def calculate_mae(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> float:

    y_true = np.asarray(
        y_true,
        dtype=float,
    )

    y_pred = np.asarray(
        y_pred,
        dtype=float,
    )

    return float(
        np.mean(
            np.abs(
                y_true
                - y_pred
            )
        )
    )


def calculate_nmae(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> float:

    y_true = np.asarray(
        y_true,
        dtype=float,
    )

    denominator = np.mean(
        np.abs(y_true)
    )

    if denominator <= 1e-9:
        return float("nan")

    return (
        calculate_mae(
            y_true,
            y_pred,
        )
        / denominator
    )


def calculate_energy_error(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    interval_seconds: int = DEFAULT_CADENCE_SECONDS,
) -> float:

    y_true = np.asarray(
        y_true,
        dtype=float,
    )

    y_pred = np.asarray(
        y_pred,
        dtype=float,
    )

    true_energy = (
        np.sum(
            np.maximum(
                y_true,
                0,
            )
        )
        * interval_seconds
        / 3600.0
    )

    predicted_energy = (
        np.sum(
            np.maximum(
                y_pred,
                0,
            )
        )
        * interval_seconds
        / 3600.0
    )

    if true_energy <= 1e-9:
        return float("nan")

    return float(
        abs(
            predicted_energy
            - true_energy
        )
        / true_energy
    )


def calculate_detection_f1(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold_w: float = ON_THRESHOLD_W,
) -> float:

    y_true = np.asarray(
        y_true,
        dtype=float,
    )

    y_pred = np.asarray(
        y_pred,
        dtype=float,
    )

    true_on = (
        y_true >= threshold_w
    )

    pred_on = (
        y_pred >= threshold_w
    )

    tp = np.sum(
        true_on & pred_on
    )

    fp = np.sum(
        ~true_on & pred_on
    )

    fn = np.sum(
        true_on & ~pred_on
    )

    precision = (
        tp / (tp + fp)
        if tp + fp > 0
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn > 0
        else 0.0
    )

    if precision + recall == 0:
        return 0.0

    return float(
        2
        * precision
        * recall
        / (
            precision
            + recall
        )
    )


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, float]:

    return {
        "mae_w": calculate_mae(
            y_true,
            y_pred,
        ),

        "nmae": calculate_nmae(
            y_true,
            y_pred,
        ),

        "energy_error": calculate_energy_error(
            y_true,
            y_pred,
        ),

        "f1": calculate_detection_f1(
            y_true,
            y_pred,
        ),
    }