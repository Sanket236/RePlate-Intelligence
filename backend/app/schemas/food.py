"""Pydantic schemas for FoodDonation endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import FoodDonationStatus


class FoodDonationCreate(BaseModel):
    donor_name: str = Field(..., min_length=1, max_length=200)
    food_name: str = Field(..., min_length=1, max_length=200)
    food_category: str = Field(..., min_length=1, max_length=100)
    quantity_kg: float = Field(..., gt=0, description="Must be positive")
    prepared_at: datetime
    expiry_at: datetime
    storage_conditions: Optional[str] = Field(None, max_length=300)
    pickup_location: str = Field(..., min_length=1, max_length=300)

    @model_validator(mode="after")
    def expiry_after_prepared(self) -> "FoodDonationCreate":
        if self.expiry_at <= self.prepared_at:
            raise ValueError("expiry_at must be after prepared_at")
        return self


class FoodDonationUpdate(BaseModel):
    donor_name: Optional[str] = Field(None, min_length=1, max_length=200)
    food_name: Optional[str] = Field(None, min_length=1, max_length=200)
    food_category: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity_kg: Optional[float] = Field(None, gt=0)
    storage_conditions: Optional[str] = Field(None, max_length=300)
    pickup_location: Optional[str] = Field(None, min_length=1, max_length=300)
    status: Optional[FoodDonationStatus] = None


class FoodDonationOut(BaseModel):
    id: int
    donor_name: str
    food_name: str
    food_category: str
    quantity_kg: float
    prepared_at: datetime
    expiry_at: datetime
    storage_conditions: Optional[str]
    pickup_location: str
    status: FoodDonationStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class FoodDonationListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[FoodDonationOut]
