"""
Seed script — inserts clearly-labelled DEMO recipients and one demo food donation.

All names, locations, and contact details are fictitious and labelled [DEMO].
Run: python -m scripts.seed_demo_data
"""
import json
import sys
from pathlib import Path

# Ensure backend/ is on the path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import SessionLocal, init_db
from app.db.models import FoodDonation, FoodDonationStatus, RecipientOrganization

DEMO_RECIPIENTS = [
    {
        "organization_name": "[DEMO] City Food Bank",
        "location": "downtown, demo city",
        "accepted_food_categories": json.dumps(
            ["dairy", "meat", "vegetables", "grains"]
        ),
        "capacity_kg": 500.0,
        "contact_details": "[DEMO] contact@cityfoodbank.example",
        "is_active": True,
    },
    {
        "organization_name": "[DEMO] Community Kitchen North",
        "location": "north district, demo city",
        "accepted_food_categories": json.dumps(["vegetables", "grains"]),
        "capacity_kg": 200.0,
        "contact_details": "[DEMO] info@commkitchennorth.example",
        "is_active": True,
    },
    {
        "organization_name": "[DEMO] Shelter Meals East",
        "location": "east side, demo city",
        "accepted_food_categories": json.dumps(["dairy", "meat", "grains"]),
        "capacity_kg": 150.0,
        "contact_details": "[DEMO] meals@sheltereast.example",
        "is_active": True,
    },
    {
        "organization_name": "[DEMO] School Lunch Program",
        "location": "central, demo city",
        "accepted_food_categories": json.dumps(["dairy", "vegetables", "grains"]),
        "capacity_kg": 100.0,
        "contact_details": "[DEMO] lunch@schoolprogram.example",
        "is_active": True,
    },
    {
        "organization_name": "[DEMO] Rural Aid Network",
        "location": "rural outskirts, demo city",
        "accepted_food_categories": json.dumps(["vegetables", "grains", "dairy"]),
        "capacity_kg": 300.0,
        "contact_details": "[DEMO] aid@ruralnetwork.example",
        "is_active": False,  # intentionally inactive for testing
    },
]

from datetime import datetime, timedelta, timezone


def _demo_food():
    now = datetime.now(timezone.utc)
    return FoodDonation(
        donor_name="[DEMO] Hotel Grand",
        food_name="[DEMO] Mixed Vegetables Surplus",
        food_category="vegetables",
        quantity_kg=80.0,
        prepared_at=now - timedelta(hours=2),
        expiry_at=now + timedelta(hours=22),
        storage_conditions="Refrigerated at 4°C",
        pickup_location="downtown, demo city",
        status=FoodDonationStatus.available,
    )


def seed():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(RecipientOrganization).count()
        if existing > 0:
            print(
                f"Database already contains {existing} recipients — skipping seed."
            )
        else:
            for data in DEMO_RECIPIENTS:
                db.add(RecipientOrganization(**data))
            db.commit()
            print(f"Inserted {len(DEMO_RECIPIENTS)} DEMO recipients.")

        food_count = db.query(FoodDonation).count()
        if food_count == 0:
            db.add(_demo_food())
            db.commit()
            print("Inserted 1 DEMO food donation.")
        else:
            print(f"Database already has {food_count} food donations — skipping.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed complete.")
