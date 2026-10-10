"""Pydantic schemas for ML prediction endpoints."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """
    Feature schema derived from the actual Kaggle dataset columns.

    Dataset columns (excluding ID, date, food_waste_kg):
      meals_served, kitchen_staff, temperature_C, humidity_percent,
      day_of_week, special_event, past_waste_kg, staff_experience,
      waste_category
    """

    meals_served: int = Field(
        ..., ge=1, description="Number of meals served in the session"
    )
    kitchen_staff: int = Field(..., ge=1, description="Number of kitchen staff")
    temperature_C: float = Field(..., description="Ambient temperature in Celsius")
    humidity_percent: float = Field(
        ..., ge=0, le=100, description="Humidity percentage"
    )
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Mon, 6=Sun)")
    special_event: int = Field(..., ge=0, le=1, description="1 if special event, else 0")
    past_waste_kg: float = Field(
        ..., ge=0, description="Historical average waste in kg"
    )
    staff_experience: Optional[str] = Field(
        None,
        description="Staff experience level: Beginner, Intermediate, or Expert",
    )
    waste_category: str = Field(
        ...,
        description="Category of food waste: dairy, meat, vegetables, or grains",
    )


class PredictionResponse(BaseModel):
    predicted_food_waste_kg: float
    model_status: str
    input_features: dict[str, Any]
    disclaimer: str


class TrainResponse(BaseModel):
    status: str
    mae: float
    r2: float
    rmse: float
    train_rows: int
    val_rows: int
    feature_names: list[str]
    notes: list[str]


class ModelMetrics(BaseModel):
    mae: float
    r2: float
    rmse: float
    train_rows: int
    val_rows: int
    trained_at: Optional[str]
    model_ready: bool


class FeatureSchema(BaseModel):
    name: str
    dtype: str
    description: str
    required: bool
    example: Any
