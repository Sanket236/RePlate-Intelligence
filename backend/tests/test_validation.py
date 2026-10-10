"""Tests for Pydantic input validation schemas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.food import FoodDonationCreate, FoodDonationUpdate
from app.schemas.prediction import PredictionRequest
from app.schemas.recipient import RecipientCreate


# ── FoodDonationCreate ────────────────────────────────────────────────────────

def _valid_food_payload(**kwargs):
    now = datetime.now(timezone.utc)
    base = dict(
        donor_name="Test Donor",
        food_name="Surplus Rice",
        food_category="grains",
        quantity_kg=30.0,
        prepared_at=now,
        expiry_at=now + timedelta(hours=24),
        pickup_location="downtown",
    )
    base.update(kwargs)
    return base


def test_food_create_valid():
    obj = FoodDonationCreate(**_valid_food_payload())
    assert obj.quantity_kg == 30.0


def test_food_create_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        FoodDonationCreate(**_valid_food_payload(quantity_kg=-5.0))


def test_food_create_zero_quantity_rejected():
    with pytest.raises(ValidationError):
        FoodDonationCreate(**_valid_food_payload(quantity_kg=0.0))


def test_food_create_expiry_before_prepared_rejected():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        FoodDonationCreate(**_valid_food_payload(
            prepared_at=now,
            expiry_at=now - timedelta(hours=1),
        ))


def test_food_create_expiry_equal_prepared_rejected():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        FoodDonationCreate(**_valid_food_payload(
            prepared_at=now, expiry_at=now
        ))


def test_food_create_missing_required_field():
    payload = _valid_food_payload()
    del payload["donor_name"]
    with pytest.raises(ValidationError):
        FoodDonationCreate(**payload)


# ── RecipientCreate ───────────────────────────────────────────────────────────

def test_recipient_create_valid():
    obj = RecipientCreate(
        organization_name="Demo Org",
        location="downtown",
        accepted_food_categories=["Dairy", "MEAT"],
        capacity_kg=100.0,
    )
    # Categories should be lowercased
    assert "dairy" in obj.accepted_food_categories
    assert "meat" in obj.accepted_food_categories


def test_recipient_create_empty_categories_rejected():
    with pytest.raises(ValidationError):
        RecipientCreate(
            organization_name="Demo",
            location="here",
            accepted_food_categories=[],
            capacity_kg=100.0,
        )


def test_recipient_create_negative_capacity_rejected():
    with pytest.raises(ValidationError):
        RecipientCreate(
            organization_name="Demo",
            location="here",
            accepted_food_categories=["dairy"],
            capacity_kg=-10.0,
        )


# ── PredictionRequest ─────────────────────────────────────────────────────────

def _valid_prediction_payload(**kwargs):
    base = dict(
        meals_served=300,
        kitchen_staff=12,
        temperature_C=22.0,
        humidity_percent=55.0,
        day_of_week=2,
        special_event=0,
        past_waste_kg=25.0,
        staff_experience="intermediate",
        waste_category="vegetables",
    )
    base.update(kwargs)
    return base


def test_prediction_request_valid():
    req = PredictionRequest(**_valid_prediction_payload())
    assert req.meals_served == 300


def test_prediction_request_invalid_day_of_week():
    with pytest.raises(ValidationError):
        PredictionRequest(**_valid_prediction_payload(day_of_week=7))


def test_prediction_request_negative_meals_rejected():
    with pytest.raises(ValidationError):
        PredictionRequest(**_valid_prediction_payload(meals_served=0))


def test_prediction_request_humidity_out_of_range():
    with pytest.raises(ValidationError):
        PredictionRequest(**_valid_prediction_payload(humidity_percent=110.0))


def test_prediction_request_staff_experience_optional():
    """staff_experience is optional — omitting it must not raise."""
    payload = _valid_prediction_payload()
    del payload["staff_experience"]
    req = PredictionRequest(**payload)
    assert req.staff_experience is None
