from __future__ import annotations

from fastapi.testclient import TestClient

from eos_v2.app.app import create_app
from eos_v2.app.config import Settings


def test_metrics_hidden_without_token() -> None:
    app = create_app(Settings(environment="test", secret_key="s" * 40))
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 404


def test_metrics_hidden_with_wrong_token() -> None:
    app = create_app(Settings(environment="test", secret_key="s" * 40, metrics_token="correct-token-value"))
    client = TestClient(app)

    response = client.get("/metrics", headers={"X-Metrics-Token": "wrong-token"})

    assert response.status_code == 404


def test_metrics_accessible_with_correct_token() -> None:
    app = create_app(Settings(environment="test", secret_key="s" * 40, metrics_token="correct-token-value"))
    client = TestClient(app)

    response = client.get("/metrics", headers={"X-Metrics-Token": "correct-token-value"})

    assert response.status_code == 200


def test_production_requires_metrics_token() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql://user:pass@localhost/db",
        secret_key="s" * 40,
        allowed_hosts=("example.com",),
        cors_origins=("https://example.com",),
        metrics_token="short",
    )
    try:
        settings.validate()
    except ValueError as exc:
        assert "EOS_METRICS_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected validation error for short metrics token")
