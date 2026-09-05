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
