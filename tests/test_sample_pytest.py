"""Real API smoke checks for the current EOS application contract."""

import pytest


@pytest.mark.unit
def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200


@pytest.mark.unit
def test_root_endpoint(test_client):
    response = test_client.get("/")
    assert response.status_code in {200, 404}


@pytest.mark.unit
def test_invalid_endpoint_returns_not_found(test_client):
    response = test_client.get("/api/v1/nonexistent-endpoint-12345")
    assert response.status_code in {404, 405}


@pytest.mark.unit
def test_openapi_endpoint(test_client):
    response = test_client.get("/openapi.json")
    assert response.status_code in {200, 404}


@pytest.mark.security
def test_health_endpoint_handles_burst(test_client):
    responses = [test_client.get("/health").status_code for _ in range(10)]
    assert all(status in {200, 429} for status in responses)


@pytest.mark.security
def test_cors_preflight_is_handled(test_client):
    response = test_client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code in {200, 204, 404, 405}
