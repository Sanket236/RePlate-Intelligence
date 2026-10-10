"""ML prediction service — loads the saved pipeline and serves predictions."""
from __future__ import annotations

import json
import logging
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.config import METADATA_PATH, MODEL_PATH
from app.ml.train import ALL_FEATURES, CATEGORICAL_FEATURES

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "This is a prototype model trained on a synthetic/competition dataset. "
    "Predictions are indicative estimates only and must not be used as the "
    "sole basis for food-safety or redistribution decisions."
)


class MLService:
    """Singleton-style service that loads the pipeline once at startup."""

    def __init__(self) -> None:
        self._pipeline = None
        self._metadata: dict | None = None
        self._load()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load(self) -> None:
        if MODEL_PATH.exists() and METADATA_PATH.exists():
            try:
                self._pipeline = joblib.load(MODEL_PATH)
                self._metadata = json.loads(METADATA_PATH.read_text())
                logger.info("ML pipeline loaded from %s", MODEL_PATH)
            except Exception as exc:
                logger.warning("Failed to load ML pipeline: %s", exc)
                self._pipeline = None
                self._metadata = None
        else:
            logger.info(
                "No trained model found at %s — call POST /api/model/train first.",
                MODEL_PATH,
            )

    def reload(self) -> None:
        """Reload artefacts from disk (called after training)."""
        self._load()

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._pipeline is not None

    @property
    def metadata(self) -> dict | None:
        return self._metadata

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Accept a feature dict, validate it, run inference, and return a
        structured response.
        """
        if not self.is_ready:
            raise RuntimeError(
                "Model not ready. Train the model via POST /api/model/train."
            )

        # Normalise categorical strings (match training pre-processing)
        normalised = dict(features)
        for col in CATEGORICAL_FEATURES:
            if col in normalised and normalised[col] is not None:
                normalised[col] = str(normalised[col]).strip().lower()

        # Build a single-row DataFrame with the expected feature columns
        row = {col: [normalised.get(col)] for col in ALL_FEATURES}
        X = pd.DataFrame(row)

        prediction = float(self._pipeline.predict(X)[0])
        # Clamp to non-negative (tree models can occasionally predict tiny negatives)
        prediction = max(0.0, prediction)

        return {
            "predicted_food_waste_kg": round(prediction, 3),
            "model_status": "prototype",
            "input_features": features,
            "disclaimer": _DISCLAIMER,
        }

    def get_feature_schema(self) -> list[dict]:
        return [
            {
                "name": "meals_served",
                "dtype": "integer",
                "description": "Number of meals served",
                "required": True,
                "example": 300,
            },
            {
                "name": "kitchen_staff",
                "dtype": "integer",
                "description": "Number of kitchen staff on duty",
                "required": True,
                "example": 12,
            },
            {
                "name": "temperature_C",
                "dtype": "float",
                "description": "Ambient temperature in °C",
                "required": True,
                "example": 22.5,
            },
            {
                "name": "humidity_percent",
                "dtype": "float",
                "description": "Relative humidity (%)",
                "required": True,
                "example": 55.0,
            },
            {
                "name": "day_of_week",
                "dtype": "integer",
                "description": "Day of week (0=Monday … 6=Sunday)",
                "required": True,
                "example": 2,
            },
            {
                "name": "special_event",
                "dtype": "integer (0 or 1)",
                "description": "1 if a special event is scheduled, 0 otherwise",
                "required": True,
                "example": 0,
            },
            {
                "name": "past_waste_kg",
                "dtype": "float",
                "description": "Historical average food waste for similar sessions (kg)",
                "required": True,
                "example": 25.0,
            },
            {
                "name": "staff_experience",
                "dtype": "string",
                "description": "Staff experience level: beginner | intermediate | expert",
                "required": False,
                "example": "intermediate",
            },
            {
                "name": "waste_category",
                "dtype": "string",
                "description": "Primary waste food category: dairy | meat | vegetables | grains",
                "required": True,
                "example": "vegetables",
            },
        ]


# Module-level singleton
ml_service = MLService()
