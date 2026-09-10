import os

from core.reliability import IdempotencyStore


def test_idempotency_hash_is_deterministic_for_equivalent_payloads():
    first = IdempotencyStore.request_hash({"amount": 10, "items": [1, 2]})
    second = IdempotencyStore.request_hash({"items": [1, 2], "amount": 10})
    assert first == second
    assert len(first) == 64


def test_idempotency_hash_changes_when_payload_changes():
    first = IdempotencyStore.request_hash({"amount": 10})
    second = IdempotencyStore.request_hash({"amount": 11})
    assert first != second


def test_rs256_key_selection_does_not_require_hs256_secret(monkeypatch):
    monkeypatch.setenv("EOS_ALGORITHM", "RS256")
    monkeypatch.delenv("EOS_SECRET_KEY", raising=False)
    monkeypatch.setenv("EOS_JWT_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\ncontract-private\n-----END PRIVATE KEY-----")
    monkeypatch.setenv("EOS_JWT_PUBLIC_KEY", "-----BEGIN PUBLIC KEY-----\ncontract-public\n-----END PUBLIC KEY-----")

    from core.production_auth import _get_signing_key, _get_verification_key

    assert _get_signing_key().startswith("-----BEGIN PRIVATE KEY-----")
    assert _get_verification_key().startswith("-----BEGIN PUBLIC KEY-----")


def test_rs256_contract_ignores_stale_hs256_environment(monkeypatch):
    monkeypatch.setenv("EOS_ALGORITHM", "RS256")
    monkeypatch.setenv("EOS_SECRET_KEY", "legacy-hs256-secret-that-must-not-be-required")
    monkeypatch.setenv("EOS_JWT_PRIVATE_KEY", "PRIVATE")
    monkeypatch.setenv("EOS_JWT_PUBLIC_KEY", "PUBLIC")

    from core.production_auth import _get_signing_key

    assert _get_signing_key() == "PRIVATE"
