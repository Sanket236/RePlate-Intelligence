"""Tests for API routes — food, recipients, agent, predictions, health."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest


def _food_payload(**kwargs):
    now = datetime.now(timezone.utc)
    base = dict(
        donor_name="API Test Donor",
        food_name="Test Bread",
        food_category="grains",
        quantity_kg=20.0,
        prepared_at=(now - timedelta(hours=1)).isoformat(),
        expiry_at=(now + timedelta(hours=23)).isoformat(),
        pickup_location="downtown, demo city",
    )
    base.update(kwargs)
    return base


def _recipient_payload(**kwargs):
    base = dict(
        organization_name="API Test Org",
        location="downtown, demo city",
        accepted_food_categories=["grains", "dairy"],
        capacity_kg=200.0,
    )
    base.update(kwargs)
    return base


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Dataset info ──────────────────────────────────────────────────────────────

def test_dataset_info(client):
    r = client.get("/api/dataset/info")
    assert r.status_code == 200
    data = r.json()
    assert "files" in data
    assert "detected_target" in data


# ── Food CRUD ─────────────────────────────────────────────────────────────────

def test_create_food(client):
    r = client.post("/api/food", json=_food_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["food_name"] == "Test Bread"
    assert body["status"] == "available"


def test_get_food(client):
    create_r = client.post("/api/food", json=_food_payload())
    food_id = create_r.json()["id"]
    r = client.get(f"/api/food/{food_id}")
    assert r.status_code == 200
    assert r.json()["id"] == food_id


def test_get_food_not_found(client):
    r = client.get("/api/food/99999")
    assert r.status_code == 404


def test_list_food(client):
    client.post("/api/food", json=_food_payload())
    r = client.get("/api/food")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert "items" in data


def test_update_food(client):
    create_r = client.post("/api/food", json=_food_payload())
    food_id = create_r.json()["id"]
    r = client.patch(f"/api/food/{food_id}", json={"quantity_kg": 15.0})
    assert r.status_code == 200
    assert r.json()["quantity_kg"] == 15.0


def test_delete_food(client):
    create_r = client.post("/api/food", json=_food_payload())
    food_id = create_r.json()["id"]
    r = client.delete(f"/api/food/{food_id}")
    assert r.status_code == 204
    r2 = client.get(f"/api/food/{food_id}")
    assert r2.status_code == 404


def test_create_food_invalid_expiry(client):
    now = datetime.now(timezone.utc)
    r = client.post(
        "/api/food",
        json=_food_payload(
            prepared_at=(now).isoformat(),
            expiry_at=(now - timedelta(hours=1)).isoformat(),
        ),
    )
    assert r.status_code == 422


def test_create_food_negative_quantity(client):
    r = client.post("/api/food", json=_food_payload(quantity_kg=-10))
    assert r.status_code == 422


# ── Recipient CRUD ────────────────────────────────────────────────────────────

def test_create_recipient(client):
    r = client.post("/api/recipients", json=_recipient_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["organization_name"] == "API Test Org"
    assert "grains" in body["accepted_food_categories"]


def test_get_recipient_not_found(client):
    r = client.get("/api/recipients/99999")
    assert r.status_code == 404


def test_list_recipients(client):
    client.post("/api/recipients", json=_recipient_payload())
    r = client.get("/api/recipients")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1


def test_update_recipient(client):
    cr = client.post("/api/recipients", json=_recipient_payload())
    rid = cr.json()["id"]
    r = client.patch(f"/api/recipients/{rid}", json={"capacity_kg": 250.0})
    assert r.status_code == 200
    assert r.json()["capacity_kg"] == 250.0


def test_delete_recipient_no_plans(client):
    cr = client.post("/api/recipients", json=_recipient_payload())
    rid = cr.json()["id"]
    r = client.delete(f"/api/recipients/{rid}")
    assert r.status_code == 204


# ── Agent workflow ────────────────────────────────────────────────────────────

def _setup_food_and_recipient(client):
    """Create food + compatible recipient; return (food_id, recipient_id)."""
    now = datetime.now(timezone.utc)
    food_r = client.post(
        "/api/food",
        json=dict(
            donor_name="Donor",
            food_name="Surplus Veg",
            food_category="grains",
            quantity_kg=50.0,
            prepared_at=(now - timedelta(hours=1)).isoformat(),
            expiry_at=(now + timedelta(hours=24)).isoformat(),
            pickup_location="downtown, demo city",
        ),
    )
    assert food_r.status_code == 201
    food_id = food_r.json()["id"]

    rec_r = client.post(
        "/api/recipients",
        json=dict(
            organization_name="Compatible Org",
            location="downtown, demo city",
            accepted_food_categories=["grains"],
            capacity_kg=200.0,
        ),
    )
    assert rec_r.status_code == 201
    recipient_id = rec_r.json()["id"]
    return food_id, recipient_id


def test_agent_plan_creates_proposal(client):
    food_id, _ = _setup_food_and_recipient(client)
    r = client.post(f"/api/agent/plan/{food_id}")
    assert r.status_code == 200
    body = r.json()
    assert "proposed_plan" in body
    assert body["proposed_plan"] is not None
    assert body["proposed_plan"]["status"] == "proposed"


def test_agent_plan_not_found(client):
    r = client.post("/api/agent/plan/99999")
    assert r.status_code == 404


def test_agent_approve_plan(client):
    food_id, _ = _setup_food_and_recipient(client)
    plan_r = client.post(f"/api/agent/plan/{food_id}")
    plan_id = plan_r.json()["proposed_plan"]["id"]

    r = client.post(f"/api/agent/plan/{plan_id}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_agent_reject_plan(client):
    food_id, _ = _setup_food_and_recipient(client)
    plan_r = client.post(f"/api/agent/plan/{food_id}")
    plan_id = plan_r.json()["proposed_plan"]["id"]

    r = client.post(f"/api/agent/plan/{plan_id}/reject")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_agent_invalid_status_transition(client):
    """Cannot approve an already-rejected plan."""
    food_id, _ = _setup_food_and_recipient(client)
    plan_r = client.post(f"/api/agent/plan/{food_id}")
    plan_id = plan_r.json()["proposed_plan"]["id"]

    client.post(f"/api/agent/plan/{plan_id}/reject")
    r = client.post(f"/api/agent/plan/{plan_id}/approve")
    assert r.status_code == 400
