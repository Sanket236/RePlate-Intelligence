"""
Agentic AI orchestration service.

Tools (callable Python functions):
  get_food_donation        — retrieve food record
  find_matching_recipients — find eligible recipients
  rank_recipients          — rank by score
  create_donation_plan     — propose a plan
  approve_donation_plan    — approve (human action required externally)
  update_donation_status   — record status changes

If OPENAI_API_KEY is set, uses GPT for natural-language explanation.
Otherwise falls back to deterministic mode — fully functional.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import LLM_ENABLED, LLM_MODEL, OPENAI_API_KEY
from app.db.models import (
    DonationPlan,
    DonationPlanStatus,
    FoodDonation,
    PLAN_TRANSITIONS,
    RecipientOrganization,
)
from app.services import matching_service

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Agent tools (pure Python, deterministic)
# ─────────────────────────────────────────────────────────────────────────────


def get_food_donation(food_id: int, db: Session) -> Optional[FoodDonation]:
    return db.query(FoodDonation).filter(FoodDonation.id == food_id).first()


def find_matching_recipients(
    food_id: int, db: Session
) -> list[RecipientOrganization]:
    food = get_food_donation(food_id, db)
    if not food:
        raise ValueError(f"FoodDonation id={food_id} not found")
    return matching_service.find_matching_recipients(food, db)


def rank_recipients(food_id: int, db: Session) -> list[dict]:
    food = get_food_donation(food_id, db)
    if not food:
        raise ValueError(f"FoodDonation id={food_id} not found")
    candidates = matching_service.find_matching_recipients(food, db)
    return matching_service.rank_recipients(food, candidates, db)


def create_donation_plan(
    food_id: int,
    recipient_id: int,
    quantity_kg: float,
    db: Session,
) -> DonationPlan:
    food = db.query(FoodDonation).filter(FoodDonation.id == food_id).first()
    if not food:
        raise ValueError(f"FoodDonation id={food_id} not found")
    recipient = (
        db.query(RecipientOrganization)
        .filter(RecipientOrganization.id == recipient_id)
        .first()
    )
    if not recipient:
        raise ValueError(f"RecipientOrganization id={recipient_id} not found")

    ranked = matching_service.rank_recipients(
        food,
        [r for r in matching_service.find_matching_recipients(food, db)
         if r.id == recipient_id],
        db,
    )
    score = ranked[0]["score"] if ranked else 0.0
    reasons = ranked[0]["reasons"] if ranked else ["Manual selection"]

    return matching_service.create_donation_plan(
        food, recipient, quantity_kg, score, reasons, db
    )


def approve_donation_plan(plan_id: int, db: Session) -> DonationPlan:
    plan = db.query(DonationPlan).filter(DonationPlan.id == plan_id).first()
    if not plan:
        raise ValueError(f"DonationPlan id={plan_id} not found")
    _validate_transition(plan, DonationPlanStatus.approved)
    plan.status = DonationPlanStatus.approved
    db.commit()
    db.refresh(plan)
    logger.info("Plan id=%d approved", plan_id)
    return plan


def update_donation_status(
    plan_id: int, new_status: DonationPlanStatus, db: Session
) -> DonationPlan:
    plan = db.query(DonationPlan).filter(DonationPlan.id == plan_id).first()
    if not plan:
        raise ValueError(f"DonationPlan id={plan_id} not found")
    _validate_transition(plan, new_status)
    plan.status = new_status
    db.commit()
    db.refresh(plan)
    return plan


def _validate_transition(plan: DonationPlan, new_status: DonationPlanStatus) -> None:
    allowed = PLAN_TRANSITIONS.get(plan.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition plan from '{plan.status}' to '{new_status}'. "
            f"Allowed: {[s.value for s in allowed]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration (plan workflow)
# ─────────────────────────────────────────────────────────────────────────────


def run_planning_workflow(food_id: int, db: Session) -> dict:
    """
    Execute the full planning workflow for a food donation:
    1. Retrieve food record
    2. Find eligible recipients
    3. Rank them
    4. Create a proposed plan for the top candidate
    5. Return structured response

    Uses LLM for explanation if configured; falls back to template text.
    """
    food = get_food_donation(food_id, db)
    if not food:
        raise ValueError(f"FoodDonation id={food_id} not found")

    ranked = rank_recipients(food_id, db)
    warnings: list[str] = []

    proposed_plan = None
    if ranked:
        top = ranked[0]
        qty = min(food.quantity_kg, top["available_capacity_kg"])
        try:
            proposed_plan = matching_service.create_donation_plan(
                food=food,
                recipient=top["recipient"],
                quantity_kg=qty,
                score=top["score"],
                reasons=top["reasons"],
                db=db,
            )
        except ValueError as exc:
            warnings.append(str(exc))
    else:
        warnings.append(
            "No eligible recipients found. Check that recipients accept "
            f"'{food.food_category}' and have sufficient capacity."
        )

    explanation = _build_explanation(food, ranked, proposed_plan, warnings)

    return {
        "food_donation": food,
        "ranked_recipients": ranked,
        "proposed_plan": proposed_plan,
        "explanation": explanation,
        "fallback_mode": not LLM_ENABLED,
        "warnings": warnings,
    }


def _build_explanation(
    food: FoodDonation,
    ranked: list[dict],
    plan: Optional[DonationPlan],
    warnings: list[str],
) -> str:
    if LLM_ENABLED:
        try:
            return _llm_explanation(food, ranked, plan, warnings)
        except Exception as exc:
            logger.warning("LLM explanation failed, using fallback: %s", exc)

    # ── Deterministic fallback ────────────────────────────────────────────────
    lines = [
        f"Planning summary for '{food.food_name}' ({food.quantity_kg} kg, "
        f"category: {food.food_category}).",
        f"Eligible recipients found: {len(ranked)}.",
    ]
    if ranked:
        top = ranked[0]
        lines.append(
            f"Top match: {top['recipient'].organization_name} "
            f"(score {top['score']:.0f}/100). "
            f"Reasons: {'; '.join(top['reasons'][:2])}."
        )
    if plan:
        lines.append(
            f"Proposed plan ID {plan.id}: {plan.proposed_quantity_kg:.1f} kg "
            f"→ {ranked[0]['recipient'].organization_name}. "
            "Status: PROPOSED — awaiting human approval."
        )
    if warnings:
        lines.append("Warnings: " + "; ".join(warnings))
    lines.append(
        "[Fallback mode — LLM not configured. "
        "Set OPENAI_API_KEY to enable AI-generated explanations.]"
    )
    return " ".join(lines)


def _llm_explanation(
    food: FoodDonation,
    ranked: list[dict],
    plan: Optional[DonationPlan],
    warnings: list[str],
) -> str:
    """Optional GPT-powered explanation. Only called when OPENAI_API_KEY is set."""
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=OPENAI_API_KEY)

    context = {
        "food": {
            "name": food.food_name,
            "category": food.food_category,
            "quantity_kg": food.quantity_kg,
            "expiry_at": food.expiry_at.isoformat(),
            "pickup_location": food.pickup_location,
        },
        "top_recipients": [
            {
                "name": r["recipient"].organization_name,
                "score": r["score"],
                "reasons": r["reasons"],
            }
            for r in ranked[:3]
        ],
        "plan_id": plan.id if plan else None,
        "warnings": warnings,
    }

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FoodBridge AI, an assistant helping food banks "
                    "distribute surplus food. Provide a concise, factual "
                    "1-paragraph explanation of the donation plan. "
                    "Do not invent facts. "
                    "Do not claim pickups are confirmed unless plan.status is 'delivered'."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context),
            },
        ],
        max_tokens=250,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
