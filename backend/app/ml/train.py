"""
ML training pipeline for food waste prediction.

Dataset: Kaggle food waste prediction dataset
Target : food_waste_kg (continuous regression target)

Key dataset facts discovered during inspection
───────────────────────────────────────────────
- 911 rows, no duplicates.
- staff_experience has 164 missing values (NaN stored as float NaN).
- waste_category has inconsistent casing: 'dairy', 'MeAt', 'MEAT',
  'Vegetables', 'GRAINS' — normalised to lower-case before encoding.
- staff_experience values: 'intermediate', 'Beginner', 'Intermediate',
  'EXPERT' — normalised to lower-case.
- date column is dropped (year/month can be re-added if needed).
- ID column is dropped (arbitrary index).

This module is a standalone script AND importable function.
Run:  python -m app.ml.train
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.core.config import (
    METADATA_PATH,
    MODEL_PATH,
    RANDOM_SEED,
    TRAIN_CSV,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Column definitions (discovered by inspection)
# ─────────────────────────────────────────────────────────────────────────────

TARGET_COL = "food_waste_kg"
DROP_COLS = ["ID", "date"]  # non-informative for this baseline

NUMERICAL_FEATURES = [
    "meals_served",
    "kitchen_staff",
    "temperature_C",
    "humidity_percent",
    "day_of_week",
    "special_event",
    "past_waste_kg",
]

CATEGORICAL_FEATURES = [
    "staff_experience",  # has missing values → imputed to "unknown"
    "waste_category",    # inconsistent casing → normalised
]

ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing helpers
# ─────────────────────────────────────────────────────────────────────────────


def _normalise_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case + strip categorical columns so OHE is consistent."""
    df = df.copy()
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
            # Treat the string literal 'nan' (produced by str(float('nan')))
            # as a proper NaN so the imputer handles it correctly.
            df[col] = df[col].where(df[col] != "nan", other=None)
    return df


def load_and_clean(csv_path: Path) -> pd.DataFrame:
    """Load CSV and apply cleaning / validation."""
    df = pd.read_csv(csv_path)

    missing_features = [c for c in ALL_FEATURES if c not in df.columns]
    if missing_features:
        raise ValueError(
            f"CSV at {csv_path} is missing expected feature columns: "
            f"{missing_features}"
        )

    df = _normalise_categoricals(df)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline construction
# ─────────────────────────────────────────────────────────────────────────────


def build_pipeline() -> Pipeline:
    """Return an unfitted sklearn Pipeline."""
    numerical_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
    )

    categorical_transformer = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="constant", fill_value="unknown"),
            ),
            (
                "ohe",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numerical_transformer, NUMERICAL_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])


# ─────────────────────────────────────────────────────────────────────────────
# Training entry-point
# ─────────────────────────────────────────────────────────────────────────────


def train(csv_path: Path | None = None) -> dict:
    """
    Train the pipeline, evaluate on a held-out validation split, save
    artefacts, and return the evaluation metrics dict.
    """
    csv_path = csv_path or TRAIN_CSV
    logger.info("Loading training data from %s", csv_path)
    df = load_and_clean(csv_path)

    if TARGET_COL not in df.columns:
        raise ValueError(
            f"Target column '{TARGET_COL}' not found in {csv_path}. "
            "Cannot train without ground-truth labels."
        )

    X = df[ALL_FEATURES]
    y = df[TARGET_COL]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )

    logger.info(
        "Train rows: %d  |  Validation rows: %d", len(X_train), len(X_val)
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_val)
    mae = float(mean_absolute_error(y_val, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))
    r2 = float(r2_score(y_val, y_pred))

    logger.info("Validation — MAE=%.3f  RMSE=%.3f  R²=%.4f", mae, rmse, r2)

    # ── Save artefacts ────────────────────────────────────────────────────────
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    logger.info("Pipeline saved to %s", MODEL_PATH)

    from datetime import datetime, timezone

    metadata = {
        "feature_names": ALL_FEATURES,
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "target": TARGET_COL,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "notes": [
            "Prototype model trained on Kaggle synthetic/competition dataset.",
            "Predictions should not be used as the sole basis for food-safety decisions.",
            "staff_experience missing values (164/911 rows) imputed to 'unknown'.",
            "waste_category values normalised to lower-case before encoding.",
        ],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    logger.info("Feature metadata saved to %s", METADATA_PATH)

    return metadata


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = train()
    print("\n=== Training complete ===")
    print(f"  MAE  : {result['mae']:.3f} kg")
    print(f"  RMSE : {result['rmse']:.3f} kg")
    print(f"  R²   : {result['r2']:.4f}")
    sys.exit(0)
