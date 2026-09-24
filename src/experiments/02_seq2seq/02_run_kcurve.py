from __future__ import annotations

import copy
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ROOT / "data" / "gold" / "ukdale"
REPORT_ROOT = ROOT / "data" / "results" / "seq2seq"

HOUSE = "house_1"
APPLIANCES = [
    "kettle",
    "microwave",
    "fridge",
    "washing_machine",
]

SPLIT_US = 1380585600000000

CADENCE_SECONDS = 6

K_GRID = [1, 3, 5, 10]
N_DRAWS = 10

WINDOW_SIZE = 128
BATCH_SIZE = 64

EPOCHS = 5
LEARNING_RATE = 1e-3

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SEED_BASE = 2026


# ============================================================
# REPRODUCIBILITY
# ============================================================

def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ============================================================
# DATA LOADING
# ============================================================

def load_series(house: str, appliance: str):

    house_dir = DATA_ROOT / house

    mains = pd.read_parquet(
        house_dir / "mains.parquet"
    )[["ts_us", "w"]]

    appliance_df = pd.read_parquet(
        house_dir / f"{appliance}.parquet"
    )[["ts_us", "w"]]

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

    df = pd.concat(
        [mains, appliance_df],
        axis=1,
    )

    df = df.dropna()
    df = df.sort_index()

    train = df[
        df.index
        < pd.to_datetime(
            SPLIT_US,
            unit="us",
            utc=True,
        )
    ]

    test = df[
        df.index
        >= pd.to_datetime(
            SPLIT_US,
            unit="us",
            utc=True,
        )
    ]

    return train.reset_index(), test.reset_index()


# ============================================================
# CALIBRATION SESSIONS
# ============================================================

def detect_sessions(
    train_df: pd.DataFrame,
    threshold_w: float = 50.0,
    min_duration_s: float = 12.0,
):
    """
    Detect candidate appliance ON sessions from the
    labelled appliance channel.

    These are used ONLY to construct labelled training
    examples.

    The test period remains completely unseen.
    """

    power = train_df["appliance_w"].to_numpy()

    on = power > threshold_w

    sessions = []

    start = None

    for i, state in enumerate(on):

        if state and start is None:
            start = i

        elif not state and start is not None:

            end = i

            duration = (
                (end - start)
                * CADENCE_SECONDS
            )

            if duration >= min_duration_s:
                sessions.append(
                    (start, end)
                )

            start = None

    if start is not None:

        end = len(on)

        duration = (
            (end - start)
            * CADENCE_SECONDS
        )

        if duration >= min_duration_s:
            sessions.append(
                (start, end)
            )

    return sessions


# ============================================================
# SESSION VALIDATION
# ============================================================

def valid_sessions(
    sessions,
    train_df,
    max_sessions=None,
):
    """
    Keep sessions with usable surrounding context.

    We need enough data before/after the event to
    construct the Seq2Seq window.
    """

    valid = []

    half = WINDOW_SIZE // 2

    for start, end in sessions:

        if start < half:
            continue

        if end + half >= len(train_df):
            continue

        valid.append(
            (start, end)
        )

    if max_sessions is not None:
        valid = valid[:max_sessions]

    return valid


# ============================================================
# POWER SCALING
# ============================================================

class PowerScaler:

    def __init__(self):
        self.minimum = 0.0
        self.maximum = 1.0

    def fit(self, values):

        values = np.asarray(values)

        self.minimum = float(
            np.min(values)
        )

        self.maximum = float(
            np.max(values)
        )

        if self.maximum <= self.minimum:
            self.maximum = (
                self.minimum + 1.0
            )

    def transform(self, values):

        return (
            np.asarray(values)
            - self.minimum
        ) / (
            self.maximum
            - self.minimum
        )

    def inverse_transform(self, values):

        return (
            np.asarray(values)
            * (
                self.maximum
                - self.minimum
            )
            + self.minimum
        )


# ============================================================
# DATASET
# ============================================================

class SessionDataset(Dataset):

    def __init__(
        self,
        df,
        sessions,
        mains_scaler,
        appliance_scaler,
    ):

        self.samples = []

        mains = (
            mains_scaler.transform(
                df["mains_w"].to_numpy()
            )
        )

        appliance = (
            appliance_scaler.transform(
                df["appliance_w"].to_numpy()
            )
        )

        half = WINDOW_SIZE // 2

        for start, end in sessions:

            center = (
                start + end
            ) // 2

            left = center - half
            right = left + WINDOW_SIZE

            if left < 0:
                continue

            if right > len(df):
                continue

            x = mains[left:right]

            y = appliance[left:right]

            self.samples.append(
                (
                    x.astype(np.float32),
                    y.astype(np.float32),
                )
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):

        x, y = self.samples[index]

        x = torch.tensor(
            x,
            dtype=torch.float32,
        ).unsqueeze(-1)

        y = torch.tensor(
            y,
            dtype=torch.float32,
        ).unsqueeze(-1)

        return x, y


# ============================================================
# MODEL
# ============================================================

class Seq2SeqCNN(nn.Module):

    def __init__(
        self,
        channels=64,
    ):

        super().__init__()

        self.network = nn.Sequential(

            nn.Conv1d(
                1,
                channels,
                7,
                padding=3,
            ),

            nn.ReLU(),

            nn.Conv1d(
                channels,
                channels,
                7,
                padding=3,
            ),

            nn.ReLU(),

            nn.Conv1d(
                channels,
                1,
                7,
                padding=3,
            ),
        )

    def forward(self, x):

        x = x.transpose(1, 2)

        x = self.network(x)

        x = x.transpose(1, 2)

        return x


# ============================================================
# TRAINING
# ============================================================

def train_model(
    model,
    loader,
    epochs,
):

    model = model.to(DEVICE)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    loss_fn = nn.MSELoss()

    history = []

    for epoch in range(epochs):

        model.train()

        total_loss = 0.0
        batches = 0

        for x, y in loader:

            x = x.to(DEVICE)
            y = y.to(DEVICE)

            optimizer.zero_grad()

            prediction = model(x)

            loss = loss_fn(
                prediction,
                y,
            )

            loss.backward()

            optimizer.step()

            total_loss += float(
                loss.item()
            )

            batches += 1

        mean_loss = (
            total_loss
            / max(batches, 1)
        )

        history.append(
            mean_loss
        )

        print(
            f"      epoch "
            f"{epoch + 1}/{epochs} "
            f"loss={mean_loss:.6f}"
        )

    return model, history


# ============================================================
# TEST PREDICTION
# ============================================================

@torch.no_grad()

def predict_test(
    model,
    test_df,
    mains_scaler,
    appliance_scaler,
):
    model.eval()

    mains = mains_scaler.transform(
        test_df["mains_w"].to_numpy()
    )

    n = len(mains)

    predictions = np.zeros(n)
    counts = np.zeros(n)

    step = WINDOW_SIZE

    starts = np.arange(
        0,
        n - WINDOW_SIZE + 1,
        step,
    )

    TEST_BATCH_SIZE = 1024

    for batch_start in range(
        0,
        len(starts),
        TEST_BATCH_SIZE,
    ):

        batch_starts = starts[
            batch_start:
            batch_start + TEST_BATCH_SIZE
        ]

        batch = np.stack([
            mains[start:start + WINDOW_SIZE]
            for start in batch_starts
        ])

        x = torch.from_numpy(
            batch.astype(np.float32)
        ).unsqueeze(-1)

        x = x.to(DEVICE)

        pred = model(x)

        pred = (
            pred
            .cpu()
            .numpy()
            .reshape(len(batch_starts), -1)
        )

        for i, start in enumerate(batch_starts):
            end = start + WINDOW_SIZE

            predictions[start:end] += pred[i]
            counts[start:end] += 1

    valid = counts > 0

    predictions[valid] /= counts[valid]

    predictions = np.clip(
        predictions,
        0.0,
        1.0,
    )

    predictions = (
        appliance_scaler.inverse_transform(
            predictions
        )
    )

    return predictions


# ============================================================
# METRICS
# ============================================================

def regression_metrics(
    y_true,
    y_pred,
):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    mae = float(
        np.mean(
            np.abs(
                y_true - y_pred
            )
        )
    )

    denominator = float(
        np.mean(
            np.abs(y_true)
        )
    )

    nmae = (
        mae / denominator
        if denominator > 0
        else np.nan
    )

    true_energy = float(
        np.sum(y_true)
        * CADENCE_SECONDS
        / 3600.0
    )

    pred_energy = float(
        np.sum(y_pred)
        * CADENCE_SECONDS
        / 3600.0
    )

    energy_error = (
        abs(
            pred_energy
            - true_energy
        )
        / true_energy
        if true_energy > 0
        else np.nan
    )

    return {
        "mae_w": mae,
        "nmae": nmae,
        "true_energy_wh": true_energy,
        "pred_energy_wh": pred_energy,
        "energy_error": energy_error,
    }


def detection_metrics(
    y_true,
    y_pred,
    threshold_w=50.0,
):

    true_on = (
        np.asarray(y_true)
        > threshold_w
    )

    pred_on = (
        np.asarray(y_pred)
        > threshold_w
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

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    return {
        "precision": float(
            precision
        ),
        "recall": float(
            recall
        ),
        "f1": float(f1),
    }


# ============================================================
# ONE EXPERIMENT
# ============================================================

def run_one(
    train_df,
    test_df,
    sessions,
    k,
    draw,
):

    seed = (
        SEED_BASE
        + k * 100
        + draw
    )

    set_seed(seed)

    rng = np.random.default_rng(
        seed
    )

    selected = list(
        rng.choice(
            len(sessions),
            size=min(
                k,
                len(sessions),
            ),
            replace=False,
        )
    )

    selected_sessions = [
        sessions[i]
        for i in selected
    ]

    mains_scaler = PowerScaler()
    appliance_scaler = PowerScaler()

    # IMPORTANT:
    # scaler is fitted using training data only.

    mains_scaler.fit(
        train_df["mains_w"]
    )

    appliance_scaler.fit(
        train_df["appliance_w"]
    )

    dataset = SessionDataset(
        train_df,
        selected_sessions,
        mains_scaler,
        appliance_scaler,
    )

    if len(dataset) == 0:

        return {
            "k": k,
            "draw": draw,
            "sessions": 0,
        }

    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
    )

    model = Seq2SeqCNN(
        channels=64
    )

    print(
        f"    K={k}, draw={draw}: "
        f"{len(dataset)} training windows"
    )

    model, history = train_model(
        model,
        loader,
        EPOCHS,
    )

    prediction = predict_test(
        model,
        test_df,
        mains_scaler,
        appliance_scaler,
    )

    true_power = (
        test_df["appliance_w"]
        .to_numpy()
    )

    metrics = regression_metrics(
        true_power,
        prediction,
    )

    metrics.update(
        detection_metrics(
            true_power,
            prediction,
        )
    )

    metrics.update(
        {
            "k": k,
            "draw": draw,
            "sessions": len(
                selected_sessions
            ),
            "final_train_loss": history[-1],
        }
    )

    return metrics


# ============================================================
# MAIN
# ============================================================

def main():

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("SEQ2SEQ MULTI-APPLIANCE K-CURVE EXPERIMENT")
    print("=" * 60)

    print(f"House: {HOUSE}")
    print(f"Appliances: {APPLIANCES}")
    print(f"K values: {K_GRID}")
    print(f"Draws: {N_DRAWS}")
    print(f"Device: {DEVICE}")
    print()

    all_results = []

    for appliance in APPLIANCES:

        print()
        print("#" * 60)
        print(f"APPLIANCE: {appliance}")
        print("#" * 60)

        train_df, test_df = load_series(
            HOUSE,
            appliance,
        )

        print(
            "Training rows:",
            len(train_df),
        )

        print(
            "Testing rows:",
            len(test_df),
        )

        print(
            "Detecting calibration sessions..."
        )

        sessions = detect_sessions(
            train_df
        )

        sessions = valid_sessions(
            sessions,
            train_df,
        )

        print(
            "Valid sessions:",
            len(sessions),
        )

        if len(sessions) == 0:
            print(
                f"Skipping {appliance}: "
                "no valid sessions."
            )
            continue

        for k in K_GRID:

            print()
            print(
                f"========== "
                f"{appliance} | K={k} "
                f"=========="
            )

            if len(sessions) < k:
                continue

            for draw in range(N_DRAWS):

                print(
                    f"{appliance} | "
                    f"K={k} | "
                    f"draw={draw}"
                )

                result = run_one(
                    train_df,
                    test_df,
                    sessions,
                    k,
                    draw,
                )

                result["appliance"] = appliance
                result["house"] = HOUSE

                all_results.append(result)

    results_df = pd.DataFrame(
        all_results
    )

    output_csv = (
        REPORT_ROOT
        / "seq2seq_multi_appliance_raw.csv"
    )

    results_df.to_csv(
        output_csv,
        index=False,
    )

    print()
    print("Saved:", output_csv)

    metric_columns = [
        "mae_w",
        "nmae",
        "energy_error",
        "f1",
    ]

    summary = (
        results_df
        .groupby(
            ["appliance", "k"]
        )[metric_columns]
        .agg(["mean", "std"])
        .reset_index()
    )

    summary_output = (
        REPORT_ROOT
        / "seq2seq_multi_appliance_summary.csv"
    )

    summary.to_csv(
        summary_output,
        index=False,
    )

    print(
        "Saved:",
        summary_output,
    )

    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    print(
        summary.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    metric_columns = [
        "mae_w",
        "nmae",
        "energy_error",
        "f1",
    ]

    summary = (
        results_df
        .groupby(["appliance", "k"])[
            metric_columns
        ]
        .agg(
            ["mean", "std"]
        )
        .reset_index()
    )

    summary_output = (
        REPORT_ROOT
        / "seq2seq_kcurve_summary.csv"
    )

    summary.to_csv(
        summary_output,
        index=False,
    )

    print(
        "Saved:",
        summary_output,
    )

    print()
    print(
        "========== SUMMARY =========="
    )

    print(
        summary.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()