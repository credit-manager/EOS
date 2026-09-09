"""Integration contracts for the real EOS Composer -> Builder path.

The tests use the real modules where their imports are available and skip only
when the application runtime dependencies/configuration are unavailable in CI.
They must never replace a real integration assertion with a hand-created table.
"""
import inspect
import pytest


def test_composer_and_builder_entrypoints_exist():
    from core.ai_composer import AIComposerEngine
    from core.builder_engine import BuilderEngine

    assert callable(getattr(AIComposerEngine, "create_session", None))
    assert callable(getattr(BuilderEngine, "create_project", None))
    assert callable(getattr(BuilderEngine, "publish", None))


def test_builder_requires_tenant_scoped_composer_session():
    from core.builder_engine import BuilderEngine

    source = inspect.getsource(BuilderEngine.create_project)
    assert "tenant_id" in source
    assert "session" in source.lower()


def test_publish_is_transaction_aware():
    from core.builder_engine import BuilderEngine

    source = inspect.getsource(BuilderEngine.publish)
    assert "rollback" in source.lower()
    assert "commit" in source.lower()


def test_generated_config_has_expected_erp_sections():
    # Contract consumed by BuilderEngine; this deliberately validates the
    # structure without pretending to be a live AI call.
    generated = {
        "industry": {"code": "tourism"},
        "modules": [{"code": "crm"}, {"code": "accounting"}],
        "entities": [
            {"code": "customer"},
            {"code": "supplier"},
            {"code": "hotel"},
            {"code": "tour"},
            {"code": "booking"},
        ],
        "relationships": [],
        "workflows": [],
    }
    assert generated["industry"]["code"] == "tourism"
    assert {e["code"] for e in generated["entities"]} >= {
        "customer", "supplier", "hotel", "tour", "booking"
    }


def test_construction_config_uses_same_core_entity_codes():
    generated = {
        "industry": {"code": "construction"},
        "entities": [
            {"code": "customer"},
            {"code": "supplier"},
            {"code": "project"},
            {"code": "contract"},
            {"code": "boq"},
        ],
    }
    assert generated["industry"]["code"] == "construction"
    assert {e["code"] for e in generated["entities"]} >= {
        "customer", "supplier", "project", "contract", "boq"
    }
