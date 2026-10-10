"""Agentic AI workflow endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DonationPlan, DonationPlanStatus, PLAN_TRANSITIONS
from app.schemas.donationplan import (
    AgentPlanResponse,
    DonationPlanOut,
    DonationPlanStatusUpdate,
    RankedRecipient,
)
from app.schemas.food import FoodDonationOut
from app.schemas.recipient import RecipientOut
from app.services import agent_service

import json

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _plan_to_out(plan: DonationPlan) -> DonationPlanOut:
    return DonationPlanOut.model_validate(plan)


def _recipient_out(r) -> RecipientOut:
    try:
        cats = json.loads(r.accepted_food_categories)
    except Exception:
        cats = [r.accepted_food_categories]
    return RecipientOut(
        id=r.id,
        organization_name=r.organization_name,
        location=r.location,
        accepted_food_categories=cats,
        capacity_kg=r.capacity_kg,
        contact_details=r.contact_details,
        is_active=r.is_active,
    )


@router.post(
    "/plan/{food_id}",
    response_model=AgentPlanResponse,
    summary="Run planning workflow for a food donation",
)
def plan_food(food_id: int, db: Session = Depends(get_db)):
    try:
        result = agent_service.run_planning_workflow(food_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    ranked = [
        RankedRecipient(
            recipient=_recipient_out(r["recipient"]),
            score=r["score"],
            reasons=r["reasons"],
            available_capacity_kg=r["available_capacity_kg"],
        )
        for r in result["ranked_recipients"]
    ]

    proposed_plan = (
        _plan_to_out(result["proposed_plan"])
        if result["proposed_plan"]
        else None
    )

    return AgentPlanResponse(
        food_donation=FoodDonationOut.model_validate(result["food_donation"]),
        ranked_recipients=ranked,
        proposed_plan=proposed_plan,
        explanation=result["explanation"],
        fallback_mode=result["fallback_mode"],
        warnings=result["warnings"],
    )


@router.get(
    "/plan/{plan_id}",
    response_model=DonationPlanOut,
    summary="Get a donation plan",
)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(DonationPlan).filter(DonationPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Donation plan not found")
    return _plan_to_out(plan)


@router.post(
    "/plan/{plan_id}/approve",
    response_model=DonationPlanOut,
    summary="Approve a donation plan (explicit human action)",
)
def approve_plan(plan_id: int, db: Session = Depends(get_db)):
    try:
        plan = agent_service.approve_donation_plan(plan_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _plan_to_out(plan)


@router.post(
    "/plan/{plan_id}/reject",
    response_model=DonationPlanOut,
    summary="Reject a donation plan",
)
def reject_plan(plan_id: int, db: Session = Depends(get_db)):
    try:
        plan = agent_service.update_donation_status(
            plan_id, DonationPlanStatus.rejected, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _plan_to_out(plan)


@router.patch(
    "/plan/{plan_id}/status",
    response_model=DonationPlanOut,
    summary="Update donation plan status",
)
def update_plan_status(
    plan_id: int,
    data: DonationPlanStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        plan = agent_service.update_donation_status(plan_id, data.status, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _plan_to_out(plan)
