"""Tests for the billing module."""
import uuid
import pytest
from backend.app.db import Base, engine, SessionLocal
from backend.app.billing.models import Plan, Subscription, Invoice
from backend.app.billing.seed import PLANS


@pytest.fixture(autouse=True, scope="session")
def _create_billing_tables():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_plans(db):
    for plan_data in PLANS:
        existing = db.query(Plan).filter(Plan.code == plan_data["code"]).first()
        if not existing:
            plan = Plan(id=str(uuid.uuid4()), **plan_data)
            db.add(plan)
    db.commit()


@pytest.fixture(autouse=True)
def clean_subscriptions(db):
    """Clear subscriptions before each test."""
    db.query(Subscription).delete()
    db.commit()
    yield
    db.query(Subscription).delete()
    db.commit()


def _get_token(client) -> str:
    from backend.tests.conftest import TEST_PASSWORD
    resp = client.post(
        "/api/v1/auth/token",
        json={"email": "test@2to-eos.local", "password": TEST_PASSWORD},
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return ""


class TestBillingPlans:
    def test_list_plans(self, client, seed_plans):
        resp = client.get("/api/v1/billing/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) >= 3
        codes = [p["code"] for p in plans]
        assert "starter" in codes
        assert "professional" in codes
        assert "enterprise" in codes

    def test_plan_structure(self, client, seed_plans):
        resp = client.get("/api/v1/billing/plans")
        plan = resp.json()[0]
        assert "id" in plan
        assert "code" in plan
        assert "name" in plan
        assert "price_monthly" in plan
        assert "features" in plan


class TestBillingSubscription:
    def test_get_subscription_none(self, client, seed_plans):
        token = _get_token(client)
        if not token:
            pytest.skip("No auth token")
        resp = client.get(
            "/api/v1/billing/subscription",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "none"

    def test_subscribe(self, client, seed_plans):
        token = _get_token(client)
        if not token:
            pytest.skip("No auth token")
        resp = client.post(
            "/api/v1/billing/subscribe",
            json={"plan_code": "starter", "billing_cycle": "monthly"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert "subscription_id" in data

    def test_get_active_subscription(self, client, seed_plans):
        token = _get_token(client)
        if not token:
            pytest.skip("No auth token")
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/api/v1/billing/subscribe",
            json={"plan_code": "professional", "billing_cycle": "yearly"},
            headers=headers,
        )
        resp = client.get(
            "/api/v1/billing/subscription",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"

    def test_duplicate_subscribe_rejected(self, client, seed_plans):
        token = _get_token(client)
        if not token:
            pytest.skip("No auth token")
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/api/v1/billing/subscribe",
            json={"plan_code": "starter"},
            headers=headers,
        )
        resp = client.post(
            "/api/v1/billing/subscribe",
            json={"plan_code": "starter"},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_subscribe_invalid_plan(self, client, seed_plans):
        token = _get_token(client)
        if not token:
            pytest.skip("No auth token")
        resp = client.post(
            "/api/v1/billing/subscribe",
            json={"plan_code": "nonexistent"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_cancel_subscription(self, client, seed_plans):
        token = _get_token(client)
        if not token:
            pytest.skip("No auth token")
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/api/v1/billing/subscribe",
            json={"plan_code": "starter"},
            headers=headers,
        )
        resp = client.post(
            "/api/v1/billing/subscription/cancel", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancellation_scheduled"

    def test_cancel_no_subscription(self, client, seed_plans):
        token = _get_token(client)
        if not token:
            pytest.skip("No auth token")
        headers = {"Authorization": f"Bearer {token}"}

        # First ensure no subscription exists by cancelling any active one
        resp = client.get("/api/v1/billing/subscription", headers=headers)
        if resp.status_code == 200 and resp.json().get("status") == "active":
            client.post("/api/v1/billing/subscription/cancel", headers=headers)

        # Now try to cancel again - should be 404
        resp = client.post("/api/v1/billing/subscription/cancel", headers=headers)
        assert resp.status_code == 404
