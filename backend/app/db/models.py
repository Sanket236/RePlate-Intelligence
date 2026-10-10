"""SQLAlchemy ORM models for FoodBridge AI."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class FoodDonationStatus(str, enum.Enum):
    available = "available"
    partially_allocated = "partially_allocated"
    fully_allocated = "fully_allocated"
    expired = "expired"
    withdrawn = "withdrawn"


class DonationPlanStatus(str, enum.Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"


# Valid forward transitions for DonationPlan status
PLAN_TRANSITIONS: dict[DonationPlanStatus, set[DonationPlanStatus]] = {
    DonationPlanStatus.proposed: {
        DonationPlanStatus.approved,
        DonationPlanStatus.rejected,
        DonationPlanStatus.cancelled,
    },
    DonationPlanStatus.approved: {
        DonationPlanStatus.in_transit,
        DonationPlanStatus.cancelled,
    },
    DonationPlanStatus.in_transit: {
        DonationPlanStatus.delivered,
        DonationPlanStatus.cancelled,
    },
    DonationPlanStatus.delivered: set(),
    DonationPlanStatus.rejected: set(),
    DonationPlanStatus.cancelled: set(),
}


# ─────────────────────────────────────────────────────────────────────────────
# FoodDonation
# ─────────────────────────────────────────────────────────────────────────────


class FoodDonation(Base):
    __tablename__ = "food_donations"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="ck_food_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    food_category: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expiry_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    storage_conditions: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )
    pickup_location: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[FoodDonationStatus] = mapped_column(
        Enum(FoodDonationStatus),
        default=FoodDonationStatus.available,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    plans: Mapped[list["DonationPlan"]] = relationship(
        "DonationPlan", back_populates="food_donation", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────────────
# RecipientOrganization
# ─────────────────────────────────────────────────────────────────────────────


class RecipientOrganization(Base):
    __tablename__ = "recipient_organizations"
    __table_args__ = (
        CheckConstraint("capacity_kg > 0", name="ck_recipient_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    accepted_food_categories: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON-encoded list stored as text
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    contact_details: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plans: Mapped[list["DonationPlan"]] = relationship(
        "DonationPlan", back_populates="recipient"
    )


# ─────────────────────────────────────────────────────────────────────────────
# DonationPlan
# ─────────────────────────────────────────────────────────────────────────────


class DonationPlan(Base):
    __tablename__ = "donation_plans"
    __table_args__ = (
        CheckConstraint(
            "proposed_quantity_kg > 0", name="ck_plan_quantity_positive"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    food_donation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("food_donations.id"), nullable=False, index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recipient_organizations.id"),
        nullable=False,
        index=True,
    )
    proposed_quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    matching_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DonationPlanStatus] = mapped_column(
        Enum(DonationPlanStatus),
        default=DonationPlanStatus.proposed,
        nullable=False,
    )
    pickup_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    food_donation: Mapped["FoodDonation"] = relationship(
        "FoodDonation", back_populates="plans"
    )
    recipient: Mapped["RecipientOrganization"] = relationship(
        "RecipientOrganization", back_populates="plans"
    )
