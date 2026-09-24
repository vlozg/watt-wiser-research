import marimo

app = marimo.App()


# =========================================================
# IMPORTS
# =========================================================

@app.cell
def _():

    import numpy as np
    import pandas as pd
    import torch

    from torch.utils.data import DataLoader

    from seq2seq_lib import (
        load_appliance_data,
        appliance_exists,
        PowerScaler,
        Seq2SeqDataset,
        Seq2SeqCNN,
        train_model,
        predict_overlapping,
        mae,
        nmae,
        detection_metrics,
        energy_error,
    )

    return (
        DataLoader,
        PowerScaler,
        Seq2SeqCNN,
        Seq2SeqDataset,
        appliance_exists,
        detection_metrics,
        energy_error,
        load_appliance_data,
        mae,
        nmae,
        np,
        pd,
        predict_overlapping,
        torch,
        train_model,
    )


# =========================================================
# CONFIGURATION
# =========================================================

@app.cell
def _():

    house_name = "house_1"

    appliances = [
        "kettle",
        "fridge",
        "microwave",
        "washing_machine",
        "dishwasher",
    ]

    window_size_config = 128

    max_training_windows_config = 50_000

    max_test_windows_config = 10_000

    batch_size_config = 64

    epochs_config = 5

    learning_rate_config = 1e-3

    detection_threshold_w_config = 50.0

    print("House:", house_name)
    print("Appliances:", appliances)
    print("Window size:", window_size_config)
    print("Training windows:", max_training_windows_config)
    print("Test windows:", max_test_windows_config)

    return (
        appliances,
        batch_size_config,
        detection_threshold_w_config,
        epochs_config,
        house_name,
        learning_rate_config,
        max_test_windows_config,
        max_training_windows_config,
        window_size_config,
    )


# =========================================================
# DEVICE
# =========================================================

@app.cell
def _(torch):

    device_config = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("Device:", device_config)

    return device_config,


# =========================================================
# CHECK AVAILABLE APPLIANCES
# =========================================================

@app.cell
def _(
    appliances,
    appliance_exists,
    house_name,
):

    available_appliances = [
        appliance
        for appliance in appliances
        if appliance_exists(
            house_name,
            appliance,
        )
    ]

    unavailable_appliances = [
        appliance
        for appliance in appliances
        if appliance not in available_appliances
    ]

    print(
        "Available appliances:"
    )

    print(
        available_appliances
    )

    if unavailable_appliances:

        print(
            "\nNot available:"
        )

        print(
            unavailable_appliances
        )

    return available_appliances,


# =========================================================
# RUN SEQ2SEQ FOR ALL APPLIANCES
# =========================================================

@app.cell
def _(
    DataLoader,
    PowerScaler,
    Seq2SeqCNN,
    Seq2SeqDataset,
    available_appliances,
    batch_size_config,
    detection_metrics,
    detection_threshold_w_config,
    device_config,
    energy_error,
    epochs_config,
    house_name,
    learning_rate_config,
    load_appliance_data,
    mae,
    max_test_windows_config,
    max_training_windows_config,
    nmae,
    np,
    pd,
    predict_overlapping,
    torch,
    train_model,
    window_size_config,
):

    all_results = []

    all_histories = {}

    for appliance_name in available_appliances:

        print("\n")
        print("=" * 60)
        print(
            f"APPLIANCE: {appliance_name.upper()}"
        )
        print("=" * 60)

        # -------------------------------------------------
        # LOAD DATA
        # -------------------------------------------------

        train_df_current, test_df_current = (
            load_appliance_data(
                house=house_name,
                appliance=appliance_name,
            )
        )

        print(
            "Training rows:",
            len(train_df_current),
        )

        print(
            "Testing rows:",
            len(test_df_current),
        )

        # -------------------------------------------------
        # SCALE USING TRAINING DATA ONLY
        # -------------------------------------------------

        mains_scaler_current = PowerScaler()

        appliance_scaler_current = PowerScaler()

        mains_scaler_current.fit(
            train_df_current["mains_w"].to_numpy()
        )

        appliance_scaler_current.fit(
            train_df_current["appliance_w"].to_numpy()
        )

        # -------------------------------------------------
        # TRAIN DATASET
        # -------------------------------------------------

        train_mains_scaled = (
            mains_scaler_current.transform(
                train_df_current["mains_w"]
                .to_numpy()
            )
        )

        train_appliance_scaled = (
            appliance_scaler_current.transform(
                train_df_current["appliance_w"]
                .to_numpy()
            )
        )

        train_dataset_current = Seq2SeqDataset(
            train_mains_scaled,
            train_appliance_scaled,
            window_size=window_size_config,
        )

        # -------------------------------------------------
        # TRAINING SUBSET
        # -------------------------------------------------

        training_count = min(
            len(train_dataset_current),
            max_training_windows_config,
        )

        train_subset_current = (
            torch.utils.data.Subset(
                train_dataset_current,
                range(training_count),
            )
        )

        train_loader_current = DataLoader(
            train_subset_current,
            batch_size=batch_size_config,
            shuffle=True,
            num_workers=0,
        )

        print(
            "Training windows:",
            training_count,
        )

        # -------------------------------------------------
        # CREATE MODEL
        # -------------------------------------------------

        model_current = Seq2SeqCNN(
            channels=64
        )

        # -------------------------------------------------
        # TRAIN
        # -------------------------------------------------

        history_current = train_model(
            model=model_current,
            loader=train_loader_current,
            epochs=epochs_config,
            learning_rate=learning_rate_config,
            device=device_config,
        )

        all_histories[
            appliance_name
        ] = history_current

        # -------------------------------------------------
        # TEST DATASET
        # -------------------------------------------------

        test_mains_scaled = (
            mains_scaler_current.transform(
                test_df_current["mains_w"]
                .to_numpy()
            )
        )

        test_appliance_scaled = (
            appliance_scaler_current.transform(
                test_df_current["appliance_w"]
                .to_numpy()
            )
        )

        test_dataset_current = Seq2SeqDataset(
            test_mains_scaled,
            test_appliance_scaled,
            window_size=window_size_config,
        )

        test_count = min(
            len(test_dataset_current),
            max_test_windows_config,
        )

        test_subset_current = (
            torch.utils.data.Subset(
                test_dataset_current,
                range(test_count),
            )
        )

        test_loader_current = DataLoader(
            test_subset_current,
            batch_size=batch_size_config,
            shuffle=False,
            num_workers=0,
        )

        # -------------------------------------------------
        # PREDICT
        # -------------------------------------------------

        predicted_scaled = (
            predict_overlapping(
                model=model_current,
                loader=test_loader_current,
                dataset_length=(
                    test_count
                    + window_size_config
                    - 1
                ),
                window_size=window_size_config,
                device=device_config,
            )
        )

        # -------------------------------------------------
        # ALIGN TARGET
        # -------------------------------------------------

        actual_scaled = (
            test_appliance_scaled[
                : len(predicted_scaled)
            ]
        )

        # Remove any positions without predictions
        valid_length = min(
            len(actual_scaled),
            len(predicted_scaled),
        )

        actual_scaled = (
            actual_scaled[:valid_length]
        )

        predicted_scaled = (
            predicted_scaled[:valid_length]
        )

        # -------------------------------------------------
        # CONVERT BACK TO WATTS
        # -------------------------------------------------

        actual_w = (
            appliance_scaler_current
            .inverse_transform(
                actual_scaled
            )
        )

        predicted_w = (
            appliance_scaler_current
            .inverse_transform(
                predicted_scaled
            )
        )

        # Power cannot be negative
        predicted_w = np.maximum(
            predicted_w,
            0,
        )

        # -------------------------------------------------
        # METRICS
        # -------------------------------------------------

        mae_value = mae(
            actual_w,
            predicted_w,
        )

        nmae_value = nmae(
            actual_w,
            predicted_w,
        )

        detection = detection_metrics(
            actual_w,
            predicted_w,
            threshold_w=(
                detection_threshold_w_config
            ),
        )

        energy_error_value = energy_error(
            actual_w,
            predicted_w,
            interval_seconds=6,
        )

        result = {
            "appliance": appliance_name,
            "mae_w": mae_value,
            "nmae": nmae_value,
            "precision": detection[
                "precision"
            ],
            "recall": detection[
                "recall"
            ],
            "f1": detection[
                "f1"
            ],
            "energy_error": (
                energy_error_value
            ),
        }

        all_results.append(result)

        print("\nRESULT")
        print(
            f"MAE:          {mae_value:.2f} W"
        )
        print(
            f"nMAE:         {nmae_value:.4f}"
        )
        print(
            f"Precision:    {detection['precision']:.4f}"
        )
        print(
            f"Recall:       {detection['recall']:.4f}"
        )
        print(
            f"F1:           {detection['f1']:.4f}"
        )
        print(
            f"Energy error: {energy_error_value:.4f}"
        )

    results_df = pd.DataFrame(
        all_results
    )

    print("\n")
    print("=" * 60)
    print("FINAL SEQ2SEQ RESULTS")
    print("=" * 60)

    print(
        results_df.to_string(
            index=False
        )
    )

    return (
        all_histories,
        results_df,
    )


# =========================================================
# SAVE RESULTS
# =========================================================

@app.cell
def _(results_df):

    output_path = (
        "seq2seq_house1_results.csv"
    )

    results_df.to_csv(
        output_path,
        index=False,
    )

    print(
        "Results saved to:",
        output_path,
    )

    return output_path,


if __name__ == "__main__":
    app.run()