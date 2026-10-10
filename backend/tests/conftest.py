"""Pytest configuration and shared fixtures."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.db import models as _models  # noqa: F401 — ensures ORM classes registered
from app.db.models import FoodDonation, FoodDonationStatus, RecipientOrganization
from app.main import app

# ── Shared in-memory SQLite (same connection reused) ─────────────────────────
# Use a named shared-cache URI so every new connection sees the same data.
TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared&uri=true"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "uri": True},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """
    TestClient whose get_db dependency yields the same session as `db`,
    ensuring it operates on the same in-memory database.
    """
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Neutralise init_db so the lifespan startup won't touch the prod DB
    import app.db.database as _db_module
    import app.main as _main_module
    original_init_db = _db_module.init_db

    def _noop_init_db():
        pass  # tables already created in test_engine by the `db` fixture

    # Patch in both modules so whichever reference is called is a no-op
    _db_module.init_db = _noop_init_db
    _main_module.init_db = _noop_init_db

    # Re-create the lifespan context referencing the patched init_db
    from contextlib import asynccontextmanager
    import logging
    _logger = logging.getLogger("app.main")

    @asynccontextmanager
    async def _test_lifespan(application):
        _noop_init_db()
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _test_lifespan

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.router.lifespan_context = original_lifespan
    _db_module.init_db = original_init_db
    _main_module.init_db = original_init_db
    app.dependency_overrides.clear()


# ── Helper factories ──────────────────────────────────────────────────────────

def make_food_donation(db, **kwargs) -> FoodDonation:
    now = datetime.now(timezone.utc)
    defaults = dict(
        donor_name="Test Donor",
        food_name="Test Food",
        food_category="vegetables",
        quantity_kg=50.0,
        prepared_at=now - timedelta(hours=1),
        expiry_at=now + timedelta(hours=23),
        storage_conditions="Refrigerated",
        pickup_location="downtown, demo city",
        status=FoodDonationStatus.available,
    )
    defaults.update(kwargs)
    obj = FoodDonation(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_recipient(db, **kwargs) -> RecipientOrganization:
    defaults = dict(
        organization_name="Test Org",
        location="downtown, demo city",
        accepted_food_categories=json.dumps(["vegetables", "dairy", "grains"]),
        capacity_kg=200.0,
        contact_details="test@example.com",
        is_active=True,
    )
    defaults.update(kwargs)
    obj = RecipientOrganization(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
