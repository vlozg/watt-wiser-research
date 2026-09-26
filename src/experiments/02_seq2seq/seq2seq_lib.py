from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset


ROOT = Path(__file__).resolve().parents[3]

DATA_ROOT = ROOT / "data" / "gold" / "ukdale"


# ---------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------

def load_appliance_data(
    house: str = "house_1",
    appliance: str = "kettle",
    split_us: int = 1380585600000000,
) -> tuple[pd.DataFrame, pd.DataFrame]:

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

    split_time = pd.to_datetime(
        split_us,
        unit="us",
        utc=True,
    )

    train = df[df.index < split_time]
    test = df[df.index >= split_time]

    return (
        train.reset_index(),
        test.reset_index(),
    )


def appliance_exists(
    house: str,
    appliance: str,
) -> bool:

    path = DATA_ROOT / house / f"{appliance}.parquet"

    return path.exists()


# ---------------------------------------------------------
# SCALING
# ---------------------------------------------------------

class PowerScaler:

    def __init__(self):
        self.minimum = 0.0
        self.maximum = 1.0

    def fit(self, values):

        values = np.asarray(values)

        self.minimum = float(np.min(values))
        self.maximum = float(np.max(values))

        if self.maximum == self.minimum:
            self.maximum = self.minimum + 1.0

        return self

    def transform(self, values):

        values = np.asarray(values)

        return (
            (values - self.minimum)
            / (self.maximum - self.minimum)
        )

    def inverse_transform(self, values):

        values = np.asarray(values)

        return (
            values
            * (self.maximum - self.minimum)
            + self.minimum
        )


# ---------------------------------------------------------
# DATASET
# ---------------------------------------------------------

class Seq2SeqDataset(Dataset):

    def __init__(
        self,
        mains,
        appliance,
        window_size=128,
    ):

        self.mains = np.asarray(
            mains,
            dtype=np.float32,
        )

        self.appliance = np.asarray(
            appliance,
            dtype=np.float32,
        )

        self.window_size = window_size

    def __len__(self):

        return max(
            0,
            len(self.mains) - self.window_size + 1,
        )

    def __getitem__(self, index):

        end = index + self.window_size

        x = torch.tensor(
            self.mains[index:end],
            dtype=torch.float32,
        ).unsqueeze(-1)

        y = torch.tensor(
            self.appliance[index:end],
            dtype=torch.float32,
        ).unsqueeze(-1)

        return x, y


# ---------------------------------------------------------
# MODEL
# ---------------------------------------------------------

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
                kernel_size=7,
                padding=3,
            ),

            nn.ReLU(),

            nn.Conv1d(
                channels,
                channels,
                kernel_size=7,
                padding=3,
            ),

            nn.ReLU(),

            nn.Conv1d(
                channels,
                1,
                kernel_size=7,
                padding=3,
            ),
        )

    def forward(self, x):

        x = x.transpose(1, 2)

        x = self.network(x)

        return x.transpose(1, 2)


# ---------------------------------------------------------
# TRAINING
# ---------------------------------------------------------

def train_model(
    model,
    loader,
    epochs=5,
    learning_rate=1e-3,
    device="cpu",
):

    model = model.to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
    )

    loss_fn = nn.MSELoss()

    history = []

    for epoch in range(epochs):

        model.train()

        total_loss = 0.0
        count = 0

        for x, y in loader:

            x = x.to(device)
            y = y.to(device)

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

            count += 1

        mean_loss = (
            total_loss / max(count, 1)
        )

        history.append(mean_loss)

        print(
            f"Epoch {epoch + 1}/{epochs} "
            f"- loss: {mean_loss:.6f}"
        )

    return history


# ---------------------------------------------------------
# OVERLAPPING WINDOW PREDICTION
# ---------------------------------------------------------

@torch.no_grad()
def predict_overlapping(
    model,
    loader,
    dataset_length,
    window_size,
    device="cpu",
):

    model = model.to(device)
    model.eval()

    prediction_sum = np.zeros(
        dataset_length,
        dtype=np.float64,
    )

    prediction_count = np.zeros(
        dataset_length,
        dtype=np.float64,
    )

    start_index = 0

    for x, _ in loader:

        batch_size = x.shape[0]

        x = x.to(device)

        prediction = model(x)

        prediction = (
            prediction
            .cpu()
            .numpy()
            .squeeze(-1)
        )

        for batch_index in range(batch_size):

            start = start_index + batch_index

            end = start + window_size

            if end > dataset_length:
                break

            prediction_sum[
                start:end
            ] += prediction[
                batch_index
            ]

            prediction_count[
                start:end
            ] += 1

        start_index += batch_size

    valid = prediction_count > 0

    reconstructed = np.zeros(
        dataset_length,
        dtype=np.float32,
    )

    reconstructed[valid] = (
        prediction_sum[valid]
        / prediction_count[valid]
    )

    return reconstructed


# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------

def mae(
    y_true,
    y_pred,
):

    return float(
        np.mean(
            np.abs(
                np.asarray(y_true)
                - np.asarray(y_pred)
            )
        )
    )


def nmae(
    y_true,
    y_pred,
):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    denominator = float(
        np.mean(
            np.abs(y_true)
        )
    )

    if denominator == 0:
        return float("nan")

    return mae(
        y_true,
        y_pred,
    ) / denominator


def detection_metrics(
    y_true,
    y_pred,
    threshold_w=50.0,
):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    true_on = y_true > threshold_w
    pred_on = y_pred > threshold_w

    tp = int(
        np.sum(
            true_on & pred_on
        )
    )

    fp = int(
        np.sum(
            ~true_on & pred_on
        )
    )

    fn = int(
        np.sum(
            true_on & ~pred_on
        )
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0.0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def energy_error(
    y_true,
    y_pred,
    interval_seconds=6,
):

    true_energy = (
        np.sum(y_true)
        * interval_seconds
        / 3600.0
    )

    predicted_energy = (
        np.sum(y_pred)
        * interval_seconds
        / 3600.0
    )

    if true_energy == 0:
        return float("nan")

    return (
        abs(predicted_energy - true_energy)
        / true_energy
    )