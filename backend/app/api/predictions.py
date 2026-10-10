"""ML training and prediction endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.config import METADATA_PATH, MODEL_PATH, TRAIN_CSV
from app.ml.train import train
from app.schemas.prediction import (
    FeatureSchema,
    ModelMetrics,
    PredictionRequest,
    PredictionResponse,
    TrainResponse,
)
from app.services.ml_service import ml_service

router = APIRouter(prefix="/api", tags=["predictions"])


@router.post("/model/train", response_model=TrainResponse, summary="Train the ML model")
def train_model():
    try:
        meta = train(TRAIN_CSV)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Reload the service so it picks up the newly trained model
    ml_service.reload()

    return TrainResponse(
        status="trained",
        mae=meta["mae"],
        r2=meta["r2"],
        rmse=meta["rmse"],
        train_rows=meta["train_rows"],
        val_rows=meta["val_rows"],
        feature_names=meta["feature_names"],
        notes=meta["notes"],
    )


@router.get("/model/metrics", response_model=ModelMetrics, summary="Latest evaluation metrics")
def model_metrics():
    if not METADATA_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="No metrics found. Train the model first via POST /api/model/train.",
        )
    meta = json.loads(METADATA_PATH.read_text())
    return ModelMetrics(
        mae=meta["mae"],
        r2=meta["r2"],
        rmse=meta["rmse"],
        train_rows=meta["train_rows"],
        val_rows=meta["val_rows"],
        trained_at=meta.get("trained_at"),
        model_ready=ml_service.is_ready,
    )


@router.get(
    "/model/features",
    summary="Feature schema required for prediction",
)
def model_features():
    return {"features": ml_service.get_feature_schema()}


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predict food waste in kg",
)
def predict(request: PredictionRequest):
    if not ml_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Model not ready. Train the model via POST /api/model/train.",
        )
    try:
        result = ml_service.predict(request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PredictionResponse(**result)
