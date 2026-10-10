"""
Donation CRUD service — business logic layer between API and DB.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import FoodDonation, FoodDonationStatus
from app.schemas.food import FoodDonationCreate, FoodDonationUpdate

logger = logging.getLogger(__name__)


def create_food_donation(
    data: FoodDonationCreate, db: Session
) -> FoodDonation:
    obj = FoodDonation(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    logger.info("Created FoodDonation id=%d", obj.id)
    return obj


def get_food_donation(food_id: int, db: Session) -> Optional[FoodDonation]:
    return db.query(FoodDonation).filter(FoodDonation.id == food_id).first()


def list_food_donations(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status: Optional[FoodDonationStatus] = None,
    food_category: Optional[str] = None,
    donor_name: Optional[str] = None,
) -> tuple[int, list[FoodDonation]]:
    q = db.query(FoodDonation)
    if status:
        q = q.filter(FoodDonation.status == status)
    if food_category:
        q = q.filter(
            FoodDonation.food_category.ilike(f"%{food_category}%")
        )
    if donor_name:
        q = q.filter(FoodDonation.donor_name.ilike(f"%{donor_name}%"))
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return total, items


def update_food_donation(
    food_id: int, data: FoodDonationUpdate, db: Session
) -> Optional[FoodDonation]:
    obj = get_food_donation(food_id, db)
    if not obj:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_food_donation(food_id: int, db: Session) -> bool:
    obj = get_food_donation(food_id, db)
    if not obj:
        return False
    if obj.status in (
        FoodDonationStatus.fully_allocated,
        FoodDonationStatus.partially_allocated,
    ):
        # Mark as withdrawn instead of hard-delete when plans exist
        obj.status = FoodDonationStatus.withdrawn
        db.commit()
        logger.info("FoodDonation id=%d marked withdrawn", food_id)
    else:
        db.delete(obj)
        db.commit()
        logger.info("FoodDonation id=%d deleted", food_id)
    return True
