"""
Matching service — eligibility checks and scoring for recipient matching.

All rules are deterministic Python. No LLM is involved in eligibility or
food-safety decisions.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import CAPACITY_SAFETY_MARGIN, MIN_HOURS_BEFORE_EXPIRY
from app.db.models import DonationPlan, DonationPlanStatus, FoodDonation, RecipientOrganization

logger = logging.getLogger(__name__)


def _parse_categories(raw: str) -> list[str]:
    """Parse JSON-encoded category list stored in the DB."""
    try:
        cats = json.loads(raw)
        return [c.strip().lower() for c in cats]
    except Exception:
        return [raw.strip().lower()]


def _hours_until_expiry(expiry_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    if expiry_at.tzinfo is None:
        expiry_at = expiry_at.replace(tzinfo=timezone.utc)
    delta = expiry_at - now
    return delta.total_seconds() / 3600


def _active_allocated_kg(recipient: RecipientOrganization, db: Session) -> float:
    """Sum of proposed/approved/in_transit plan quantities for a recipient."""
    active_statuses = {
        DonationPlanStatus.proposed,
        DonationPlanStatus.approved,
        DonationPlanStatus.in_transit,
    }
    total = 0.0
    for plan in recipient.plans:
        if plan.status in active_statuses:
            total += plan.proposed_quantity_kg
    return total


def _available_capacity(recipient: RecipientOrganization, db: Session) -> float:
    allocated = _active_allocated_kg(recipient, db)
    usable = recipient.capacity_kg * CAPACITY_SAFETY_MARGIN
    return max(0.0, usable - allocated)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def find_matching_recipients(
    food: FoodDonation, db: Session
) -> list[RecipientOrganization]:
    """
    Return active recipients that:
    1. Accept the food's category.
    2. Have sufficient available capacity.
    3. Food is not expired / too close to expiry.
    """
    hours_left = _hours_until_expiry(food.expiry_at)
    if hours_left < MIN_HOURS_BEFORE_EXPIRY:
        logger.warning(
            "Food ID %d has only %.1f h until expiry — no matching attempted.",
            food.id,
            hours_left,
        )
        return []

    food_cat = food.food_category.strip().lower()

    candidates = (
        db.query(RecipientOrganization)
        .filter(RecipientOrganization.is_active == True)  # noqa: E712
        .all()
    )

    matched = []
    for r in candidates:
        categories = _parse_categories(r.accepted_food_categories)
        if food_cat not in categories:
            continue
        avail = _available_capacity(r, db)
        if avail <= 0:
            continue
        matched.append(r)

    return matched


def rank_recipients(
    food: FoodDonation,
    candidates: list[RecipientOrganization],
    db: Session,
) -> list[dict]:
    """
    Score and rank candidates. Returns list of dicts with keys:
      recipient, score, reasons, available_capacity_kg
    Higher score = better match.

    Scoring components:
    - Category match: +40 (always true for candidates that reach this step)
    - Capacity ratio: +30 * min(available / needed, 1.0)
    - Time urgency:   +20 if expiry < 12 h (prioritise urgent)  else +10
    - Location text match: +10 if pickup_location substring in recipient.location
    """
    if not candidates:
        return []

    hours_left = _hours_until_expiry(food.expiry_at)
    needed = food.quantity_kg
    pickup_loc = food.pickup_location.lower()

    ranked = []
    for r in candidates:
        avail = _available_capacity(r, db)
        reasons = []
        score = 0.0

        # Category compatibility (prerequisite)
        score += 40.0
        reasons.append(
            f"Accepts '{food.food_category}' food category"
        )

        # Capacity score
        cap_ratio = min(avail / needed, 1.0) if needed > 0 else 1.0
        score += 30.0 * cap_ratio
        reasons.append(
            f"Available capacity: {avail:.1f} kg "
            f"(needed: {needed:.1f} kg)"
        )

        # Expiry urgency
        if hours_left < 12:
            score += 20.0
            reasons.append(
                f"Urgent: food expires in {hours_left:.1f} h — prioritised"
            )
        else:
            score += 10.0
            reasons.append(
                f"Food expires in {hours_left:.1f} h — adequate time"
            )

        # Location proximity (simple text heuristic)
        if any(word in r.location.lower() for word in pickup_loc.split()):
            score += 10.0
            reasons.append("Pickup location is near recipient location")

        ranked.append(
            {
                "recipient": r,
                "score": round(score, 2),
                "reasons": reasons,
                "available_capacity_kg": round(avail, 3),
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def create_donation_plan(
    food: FoodDonation,
    recipient: RecipientOrganization,
    quantity_kg: float,
    score: float,
    reasons: list[str],
    db: Session,
) -> DonationPlan:
    """
    Create a proposed DonationPlan.
    Validates:
    - quantity_kg > 0
    - quantity_kg <= food.quantity_kg
    - quantity_kg <= available capacity
    - No duplicate active plan for same (food, recipient) pair
    """
    if quantity_kg <= 0:
        raise ValueError("proposed_quantity_kg must be positive")

    if quantity_kg > food.quantity_kg:
        raise ValueError(
            f"Proposed quantity {quantity_kg} kg exceeds food quantity "
            f"{food.quantity_kg} kg"
        )

    avail = _available_capacity(recipient, db)
    if quantity_kg > avail:
        raise ValueError(
            f"Proposed quantity {quantity_kg} kg exceeds recipient's "
            f"available capacity {avail:.1f} kg"
        )

    # Guard against duplicate active plans
    active_statuses = {
        DonationPlanStatus.proposed,
        DonationPlanStatus.approved,
        DonationPlanStatus.in_transit,
    }
    existing = (
        db.query(DonationPlan)
        .filter(
            DonationPlan.food_donation_id == food.id,
            DonationPlan.recipient_id == recipient.id,
            DonationPlan.status.in_(list(active_statuses)),
        )
        .first()
    )
    if existing:
        raise ValueError(
            f"An active donation plan (ID {existing.id}) already exists "
            f"for food {food.id} → recipient {recipient.id}."
        )

    plan = DonationPlan(
        food_donation_id=food.id,
        recipient_id=recipient.id,
        proposed_quantity_kg=quantity_kg,
        matching_score=score,
        match_reason="; ".join(reasons),
        status=DonationPlanStatus.proposed,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
