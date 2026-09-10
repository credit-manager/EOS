from unittest.mock import MagicMock

import pytest

from core.subscription_engine import SubscriptionEngine


def _row(*values):
    return values


def test_subscription_listing_is_tenant_scoped():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = []

    SubscriptionEngine(db).list_subscriptions("tenant-a", limit=50)

    statement, params = db.execute.call_args.args
    sql_text = str(statement)
    assert "WHERE tenant_id=:tid" in sql_text
    assert params["tid"] == "tenant-a"
    assert params["lim"] == 50


def test_license_update_rejects_client_controlled_sql_identifier():
    db = MagicMock()
    engine = SubscriptionEngine(db)

    with pytest.raises(ValueError, match="unsupported license fields"):
        engine.update_license("tenant-a", "license-1", **{"status = 'active' --": "x"})

    db.execute.assert_not_called()


def test_license_update_allows_only_declared_fields():
    db = MagicMock()
    db.execute.return_value.rowcount = 1

    result = SubscriptionEngine(db).update_license(
        "tenant-a", "license-1", status="active", max_seats=25
    )

    statement, params = db.execute.call_args.args
    assert "status=:status" in str(statement)
    assert "max_seats=:max_seats" in str(statement)
    assert params["tid"] == "tenant-a"
    assert params["id"] == "license-1"
    assert result == {"id": "license-1", "updated": True}


def test_payment_creation_is_pending_and_cannot_cross_tenants():
    db = MagicMock()
    db.execute.return_value.fetchone.side_effect = [None]
    engine = SubscriptionEngine(db)

    with pytest.raises(ValueError, match="invoice does not belong"):
        engine.create_payment("tenant-a", "invoice-from-b", "10.00")

    db.execute.reset_mock()
    db.execute.return_value.fetchone.side_effect = None
    db.execute.return_value.fetchone.return_value = _row(1)
    payment_id = engine.create_payment("tenant-a", "invoice-a", "10.00")

    statement, params = db.execute.call_args.args
    assert "'pending'" in str(statement)
    assert params["tid"] == "tenant-a"
    assert payment_id


def test_invoice_creation_requires_same_tenant_subscription():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None

    with pytest.raises(ValueError, match="subscription does not belong"):
        SubscriptionEngine(db).create_invoice(
            "tenant-a", "subscription-from-b", "INV-1", "25.00"
        )
