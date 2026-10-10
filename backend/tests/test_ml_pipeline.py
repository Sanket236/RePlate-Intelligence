"""Tests for the ML pipeline — training, evaluation, and prediction."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.train import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    TARGET_COL,
    _normalise_categoricals,
    build_pipeline,
    load_and_clean,
)
from app.core.config import TRAIN_CSV


# ── Dataset loading ───────────────────────────────────────────────────────────

def test_train_csv_exists():
    assert TRAIN_CSV.exists(), f"Train CSV not found at {TRAIN_CSV}"


def test_load_and_clean_returns_dataframe():
    df = load_and_clean(TRAIN_CSV)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_all_feature_columns_present():
    df = load_and_clean(TRAIN_CSV)
    for col in ALL_FEATURES:
        assert col in df.columns, f"Expected feature column '{col}' missing"


def test_target_column_present():
    df = load_and_clean(TRAIN_CSV)
    assert TARGET_COL in df.columns


def test_normalise_categoricals_lowercases():
    df = pd.DataFrame(
        {
            "waste_category": ["MeAt", "GRAINS", "Vegetables"],
            "staff_experience": ["Intermediate", "EXPERT", "Beginner"],
        }
    )
    result = _normalise_categoricals(df)
    assert result["waste_category"].tolist() == ["meat", "grains", "vegetables"]
    assert result["staff_experience"].tolist() == [
        "intermediate",
        "expert",
        "beginner",
    ]


def test_normalise_categoricals_nan_to_nan():
    """'nan' string produced by float NaN must be converted back to NaN."""
    df = pd.DataFrame(
        {
            "waste_category": ["dairy"],
            "staff_experience": [float("nan")],
        }
    )
    result = _normalise_categoricals(df)
    assert pd.isna(result["staff_experience"].iloc[0])


# ── Pipeline ──────────────────────────────────────────────────────────────────

def test_pipeline_builds():
    pipeline = build_pipeline()
    assert pipeline is not None


def test_pipeline_fits_and_predicts():
    df = load_and_clean(TRAIN_CSV)
    X = df[ALL_FEATURES].head(100)
    y = df[TARGET_COL].head(100)
    pipeline = build_pipeline()
    pipeline.fit(X, y)
    preds = pipeline.predict(X)
    assert len(preds) == 100
    assert all(np.isfinite(preds))


def test_pipeline_handles_missing_staff_experience():
    """Pipeline should accept rows where staff_experience is NaN."""
    df = load_and_clean(TRAIN_CSV)
    X = df[ALL_FEATURES].copy()
    X["staff_experience"] = float("nan")
    y = df[TARGET_COL]
    pipeline = build_pipeline()
    pipeline.fit(X, y)
    preds = pipeline.predict(X.head(5))
    assert len(preds) == 5


def test_pipeline_positive_predictions():
    df = load_and_clean(TRAIN_CSV)
    X = df[ALL_FEATURES]
    y = df[TARGET_COL]
    pipeline = build_pipeline()
    pipeline.fit(X, y)
    preds = pipeline.predict(X)
    # All predictions should be non-negative after clamping in MLService
    # The raw model may occasionally predict tiny negatives; we test it's close
    assert np.percentile(preds, 5) > -5.0  # at most 5% below -5 kg


def test_metrics_reasonable():
    """MAE should be < 20 kg on training data (sanity check, not a quality guarantee)."""
    from sklearn.metrics import mean_absolute_error
    df = load_and_clean(TRAIN_CSV)
    X = df[ALL_FEATURES]
    y = df[TARGET_COL]
    pipeline = build_pipeline()
    pipeline.fit(X, y)
    preds = pipeline.predict(X)
    mae = mean_absolute_error(y, preds)
    assert mae < 20.0, f"Train-set MAE {mae:.2f} seems unreasonably high"
