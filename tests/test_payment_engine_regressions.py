from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.payment_engine import PaymentGatewayEngine


def test_payment_engine_does_not_execute_runtime_schema_ddl():
    db = MagicMock()
    engine = PaymentGatewayEngine(db)
    db.execute.assert_not_called()
    assert engine._limit(500) == 200


def test_payment_amount_rejects_non_finite_or_non_positive_values():
    with pytest.raises(ValueError):
        PaymentGatewayEngine._amount("NaN")
    with pytest.raises(ValueError):
        PaymentGatewayEngine._amount("Infinity")
    with pytest.raises(ValueError):
        PaymentGatewayEngine._amount("0")
    assert PaymentGatewayEngine._amount("12.50") == Decimal("12.50")


def test_gateway_config_secret_values_are_not_exposed_by_sanitizer():
    redacted = PaymentGatewayEngine._safe_gateway_config(
        {"api_key": "secret", "password": "pw", "region": "me-central-1"}
    )
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["region"] == "me-central-1"


def test_payment_link_expiry_is_bounded():
    db = MagicMock()
    with pytest.raises(ValueError):
        PaymentGatewayEngine(db).create_payment_link("tenant-a", "10", expires_hours=0)
    with pytest.raises(ValueError):
        PaymentGatewayEngine(db).create_payment_link("tenant-a", "10", expires_hours=721)


def test_payment_idempotency_replays_same_request_without_insert():
    db = MagicMock()
    existing = MagicMock()
    existing.__getitem__.side_effect = ["tx-existing", "pending", "same-fingerprint"]
    db.execute.return_value.fetchone.return_value = existing
    engine = PaymentGatewayEngine(db)

    result = engine.create_transaction(
        "tenant-a", "10.00", "sar", "payment", "invoice", "inv-1", "cust-1", "cash",
        idempotency_key="request-123",
    )

    assert result["transaction_id"] == "tx-existing"
    assert result["idempotent"] is True
    db.commit.assert_not_called()


def test_payment_idempotency_rejects_same_key_for_different_request():
    db = MagicMock()
    existing = MagicMock()
    existing.__getitem__.side_effect = ["tx-existing", "pending", "different-fingerprint"]
    db.execute.return_value.fetchone.return_value = existing
    engine = PaymentGatewayEngine(db)

    with pytest.raises(ValueError, match="different payment parameters"):
        engine.create_transaction(
            "tenant-a", "10.00", "sar", "payment", "invoice", "inv-1", "cust-1", "cash",
            idempotency_key="request-123",
        )
