"""Tests for matching service eligibility and ranking rules."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.db.models import FoodDonationStatus, RecipientOrganization
from app.services.matching_service import (
    _available_capacity,
    _hours_until_expiry,
    _parse_categories,
    find_matching_recipients,
    rank_recipients,
)
from tests.conftest import make_food_donation, make_recipient


# ── _parse_categories ─────────────────────────────────────────────────────────

def test_parse_categories_list():
    raw = json.dumps(["dairy", "meat"])
    assert _parse_categories(raw) == ["dairy", "meat"]


def test_parse_categories_mixed_case():
    raw = json.dumps(["Dairy", "MEAT"])
    result = _parse_categories(raw)
    assert "dairy" in result
    assert "meat" in result


# ── _hours_until_expiry ───────────────────────────────────────────────────────

def test_hours_until_expiry_future():
    expiry = datetime.now(timezone.utc) + timedelta(hours=10)
    hours = _hours_until_expiry(expiry)
    assert 9.9 < hours < 10.1


def test_hours_until_expiry_past():
    expiry = datetime.now(timezone.utc) - timedelta(hours=2)
    hours = _hours_until_expiry(expiry)
    assert hours < 0


# ── find_matching_recipients ──────────────────────────────────────────────────

def test_find_matching_excludes_inactive(db):
    food = make_food_donation(db, food_category="vegetables")
    make_recipient(
        db,
        accepted_food_categories=json.dumps(["vegetables"]),
        is_active=False,
    )
    result = find_matching_recipients(food, db)
    assert result == []


def test_find_matching_excludes_wrong_category(db):
    food = make_food_donation(db, food_category="dairy")
    make_recipient(
        db,
        accepted_food_categories=json.dumps(["grains"]),
        is_active=True,
    )
    result = find_matching_recipients(food, db)
    assert result == []


def test_find_matching_includes_correct_category(db):
    food = make_food_donation(db, food_category="vegetables")
    recipient = make_recipient(
        db,
        accepted_food_categories=json.dumps(["vegetables", "dairy"]),
        is_active=True,
    )
    result = find_matching_recipients(food, db)
    assert len(result) == 1
    assert result[0].id == recipient.id


def test_find_matching_excludes_expired_food(db):
    now = datetime.now(timezone.utc)
    food = make_food_donation(
        db,
        food_category="vegetables",
        expiry_at=now + timedelta(hours=1),  # too soon (< 4 h)
    )
    make_recipient(
        db,
        accepted_food_categories=json.dumps(["vegetables"]),
        is_active=True,
    )
    result = find_matching_recipients(food, db)
    assert result == []


def test_find_matching_excludes_zero_capacity(db):
    food = make_food_donation(db, food_category="vegetables", quantity_kg=50.0)
    # Create recipient with tiny capacity, already fully allocated
    recipient = make_recipient(
        db,
        accepted_food_categories=json.dumps(["vegetables"]),
        capacity_kg=1.0,
        is_active=True,
    )
    # Fill their capacity with a plan
    from app.db.models import DonationPlan, DonationPlanStatus
    plan = DonationPlan(
        food_donation_id=food.id,
        recipient_id=recipient.id,
        proposed_quantity_kg=1.0,
        matching_score=50,
        status=DonationPlanStatus.proposed,
    )
    db.add(plan)
    db.commit()

    result = find_matching_recipients(food, db)
    assert result == []


# ── rank_recipients ───────────────────────────────────────────────────────────

def test_rank_recipients_ordering(db):
    food = make_food_donation(db, food_category="vegetables", quantity_kg=50.0)
    r_small = make_recipient(
        db,
        organization_name="Small Org",
        accepted_food_categories=json.dumps(["vegetables"]),
        capacity_kg=60.0,
        location="far away",
    )
    r_large = make_recipient(
        db,
        organization_name="Large Org",
        accepted_food_categories=json.dumps(["vegetables"]),
        capacity_kg=500.0,
        location="downtown, demo city",
    )
    candidates = [r_small, r_large]
    ranked = rank_recipients(food, candidates, db)
    # The large org with matching location should score higher
    assert ranked[0]["recipient"].id == r_large.id


def test_rank_recipients_empty(db):
    food = make_food_donation(db)
    result = rank_recipients(food, [], db)
    assert result == []
