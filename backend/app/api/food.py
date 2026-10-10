"""Food donation CRUD endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.database import get_db
from app.db.models import FoodDonationStatus
from app.schemas.food import (
    FoodDonationCreate,
    FoodDonationListOut,
    FoodDonationOut,
    FoodDonationUpdate,
)
from app.services import donation_service

router = APIRouter(prefix="/api/food", tags=["food"])


@router.post("", response_model=FoodDonationOut, status_code=201, summary="Register surplus food")
def create_food(data: FoodDonationCreate, db: Session = Depends(get_db)):
    return donation_service.create_food_donation(data, db)


@router.get("", response_model=FoodDonationListOut, summary="List food donations")
def list_food(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    status: Optional[FoodDonationStatus] = None,
    food_category: Optional[str] = None,
    donor_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    total, items = donation_service.list_food_donations(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        food_category=food_category,
        donor_name=donor_name,
    )
    return FoodDonationListOut(
        total=total, page=page, page_size=page_size, items=items
    )


@router.get("/{food_id}", response_model=FoodDonationOut, summary="Get one food donation")
def get_food(food_id: int, db: Session = Depends(get_db)):
    obj = donation_service.get_food_donation(food_id, db)
    if not obj:
        raise HTTPException(status_code=404, detail="Food donation not found")
    return obj


@router.patch("/{food_id}", response_model=FoodDonationOut, summary="Update food donation")
def update_food(
    food_id: int, data: FoodDonationUpdate, db: Session = Depends(get_db)
):
    obj = donation_service.update_food_donation(food_id, data, db)
    if not obj:
        raise HTTPException(status_code=404, detail="Food donation not found")
    return obj


@router.delete("/{food_id}", status_code=204, summary="Delete food donation")
def delete_food(food_id: int, db: Session = Depends(get_db)):
    deleted = donation_service.delete_food_donation(food_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Food donation not found")
