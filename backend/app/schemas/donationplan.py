"""Pydantic schemas for DonationPlan endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models import DonationPlanStatus
from app.schemas.food import FoodDonationOut
from app.schemas.recipient import RecipientOut


class DonationPlanOut(BaseModel):
    id: int
    food_donation_id: int
    recipient_id: int
    proposed_quantity_kg: float
    matching_score: float
    match_reason: Optional[str]
    status: DonationPlanStatus
    pickup_time: Optional[datetime]
    created_at: datetime
    food_donation: Optional[FoodDonationOut] = None
    recipient: Optional[RecipientOut] = None

    model_config = {"from_attributes": True}


class DonationPlanStatusUpdate(BaseModel):
    status: DonationPlanStatus
    reason: Optional[str] = Field(None, max_length=500)


class RankedRecipient(BaseModel):
    recipient: RecipientOut
    score: float
    reasons: list[str]
    available_capacity_kg: float


class AgentPlanResponse(BaseModel):
    food_donation: FoodDonationOut
    ranked_recipients: list[RankedRecipient]
    proposed_plan: Optional[DonationPlanOut]
    explanation: str
    fallback_mode: bool
    warnings: list[str]
