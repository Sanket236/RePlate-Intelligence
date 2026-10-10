"""Pydantic schemas for RecipientOrganization endpoints."""
from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RecipientCreate(BaseModel):
    organization_name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=300)
    accepted_food_categories: list[str] = Field(
        ..., min_length=1, description="List of accepted food category strings"
    )
    capacity_kg: float = Field(..., gt=0)
    contact_details: Optional[str] = Field(None, max_length=300)
    is_active: bool = True

    @field_validator("accepted_food_categories")
    @classmethod
    def categories_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("accepted_food_categories must not be empty")
        return [c.strip().lower() for c in v if c.strip()]


class RecipientUpdate(BaseModel):
    organization_name: Optional[str] = Field(None, min_length=1, max_length=200)
    location: Optional[str] = Field(None, min_length=1, max_length=300)
    accepted_food_categories: Optional[list[str]] = None
    capacity_kg: Optional[float] = Field(None, gt=0)
    contact_details: Optional[str] = Field(None, max_length=300)
    is_active: Optional[bool] = None

    @field_validator("accepted_food_categories")
    @classmethod
    def categories_not_empty(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            if not v:
                raise ValueError("accepted_food_categories must not be empty")
            return [c.strip().lower() for c in v if c.strip()]
        return v


class RecipientOut(BaseModel):
    id: int
    organization_name: str
    location: str
    accepted_food_categories: list[str]
    capacity_kg: float
    contact_details: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}

    @field_validator("accepted_food_categories", mode="before")
    @classmethod
    def parse_categories(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v


class RecipientListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RecipientOut]
