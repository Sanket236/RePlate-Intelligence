"""Evaluate a trained pipeline on an arbitrary labelled dataset."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.ml.train import ALL_FEATURES, TARGET_COL, load_and_clean


def evaluate(pipeline, csv_path: Path) -> dict:
    """
    Evaluate *pipeline* on the CSV at *csv_path*.
    The CSV must contain the target column.
    """
    df = load_and_clean(csv_path)

    if TARGET_COL not in df.columns:
        raise ValueError(
            f"Target column '{TARGET_COL}' not found in {csv_path}."
        )

    X = df[ALL_FEATURES]
    y = df[TARGET_COL]
    y_pred = pipeline.predict(X)

    return {
        "mae": float(mean_absolute_error(y, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y, y_pred))),
        "r2": float(r2_score(y, y_pred)),
        "n_rows": len(y),
    }
