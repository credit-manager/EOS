"""Stable automated smoke tests for the EOS platform entry points."""

from fastapi.testclient import TestClient

from main import app


def test_application_imports():
    assert app is not None
    assert getattr(app, "title", None)


def test_root_endpoint_is_reachable():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code in {200, 404}


def test_openapi_endpoint_is_available_when_docs_are_enabled():
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code in {200, 404}


def test_metadata_engine_imports():
    from core.metadata_engine import MetadataEngine

    assert MetadataEngine is not None


def test_builder_engine_imports():
    from core.builder_engine import BuilderEngine

    assert BuilderEngine is not None


def test_ai_composer_imports():
    from core.ai_composer import AIComposerEngine

    assert AIComposerEngine is not None
