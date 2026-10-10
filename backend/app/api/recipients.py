"""Recipient organization CRUD endpoints."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.database import get_db
from app.db.models import RecipientOrganization
from app.schemas.recipient import (
    RecipientCreate,
    RecipientListOut,
    RecipientOut,
    RecipientUpdate,
)

router = APIRouter(prefix="/api/recipients", tags=["recipients"])


def _to_out(r: RecipientOrganization) -> RecipientOut:
    """Convert ORM model to Pydantic schema (handles JSON categories)."""
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


@router.post("", response_model=RecipientOut, status_code=201, summary="Create recipient")
def create_recipient(data: RecipientCreate, db: Session = Depends(get_db)):
    obj = RecipientOrganization(
        organization_name=data.organization_name,
        location=data.location,
        accepted_food_categories=json.dumps(data.accepted_food_categories),
        capacity_kg=data.capacity_kg,
        contact_details=data.contact_details,
        is_active=data.is_active,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_out(obj)


@router.get("", response_model=RecipientListOut, summary="List recipients")
def list_recipients(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    is_active: Optional[bool] = None,
    food_category: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(RecipientOrganization)
    if is_active is not None:
        q = q.filter(RecipientOrganization.is_active == is_active)
    if location:
        q = q.filter(RecipientOrganization.location.ilike(f"%{location}%"))
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    if food_category:
        cat_lower = food_category.strip().lower()
        filtered = [
            r for r in rows
            if cat_lower in [c.lower() for c in _to_out(r).accepted_food_categories]
        ]
        items = filtered
    else:
        items = rows

    return RecipientListOut(
        total=total, page=page, page_size=page_size,
        items=[_to_out(r) for r in items],
    )


@router.get("/{recipient_id}", response_model=RecipientOut, summary="Get one recipient")
def get_recipient(recipient_id: int, db: Session = Depends(get_db)):
    r = db.query(RecipientOrganization).filter(
        RecipientOrganization.id == recipient_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    return _to_out(r)


@router.patch("/{recipient_id}", response_model=RecipientOut, summary="Update recipient")
def update_recipient(
    recipient_id: int, data: RecipientUpdate, db: Session = Depends(get_db)
):
    r = db.query(RecipientOrganization).filter(
        RecipientOrganization.id == recipient_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "accepted_food_categories" and value is not None:
            setattr(r, field, json.dumps(value))
        else:
            setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return _to_out(r)


@router.delete("/{recipient_id}", status_code=204, summary="Deactivate or delete recipient")
def delete_recipient(recipient_id: int, db: Session = Depends(get_db)):
    r = db.query(RecipientOrganization).filter(
        RecipientOrganization.id == recipient_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Soft-delete: deactivate if they have plans; hard-delete otherwise
    if r.plans:
        r.is_active = False
        db.commit()
    else:
        db.delete(r)
        db.commit()
