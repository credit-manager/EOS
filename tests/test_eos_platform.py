"""Focused automated tests for the current EOS metadata-driven core."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Base, DBPEntity, DBPField
from main import app


def test_models_expose_canonical_metadata_types():
    assert Base is not None
    assert DBPEntity.__tablename__ == "dbp_entities"
    assert DBPField.__tablename__ == "dbp_fields"


def test_metadata_entity_creation(db_session: Session):
    entity = DBPEntity(
        name_en="Test Entity",
        name_ar="كيان اختبار",
        code="test_entity",
        faculty="operations",
        tenant_id="tenant-a",
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)

    assert entity.id
    assert entity.code == "test_entity"
    assert entity.tenant_id == "tenant-a"


def test_metadata_field_creation(db_session: Session):
    entity = DBPEntity(
        name_en="Customer",
        code="customer",
        faculty="sales",
        tenant_id="tenant-a",
    )
    db_session.add(entity)
    db_session.flush()

    field = DBPField(
        entity_id=entity.id,
        code="name",
        label_en="Name",
        field_type="string",
    )
    db_session.add(field)
    db_session.commit()

    assert field.id
    assert field.entity_id == entity.id


def test_tenant_scoped_entities_are_distinguishable(db_session: Session):
    first = DBPEntity(
        name_en="Tenant A Entity",
        code="tenant_a_entity",
        faculty="operations",
        tenant_id="tenant-a",
    )
    second = DBPEntity(
        name_en="Tenant B Entity",
        code="tenant_b_entity",
        faculty="operations",
        tenant_id="tenant-b",
    )
    db_session.add_all([first, second])
    db_session.commit()

    rows = (
        db_session.query(DBPEntity)
        .filter(DBPEntity.tenant_id == "tenant-a")
        .all()
    )
    assert [row.code for row in rows] == ["tenant_a_entity"]


def test_ai_composer_engine_imports():
    from core.ai_composer import AIComposerEngine

    assert AIComposerEngine is not None


def test_builder_engine_initializes(db_session: Session):
    from core.builder_engine import BuilderEngine

    builder = BuilderEngine(db_session)
    assert builder.db is db_session


def test_builder_validation_rejects_invalid_entity():
    from core.builder_engine import BuilderEngine

    validation = BuilderEngine.__new__(BuilderEngine).validate_draft(
        {"custom_entities": [{"entity_code": "INVALID-CODE", "fields": []}]}
    )
    assert validation["valid"] is False
    assert validation["errors"]


def test_root_endpoint_is_reachable():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code in {200, 404}


def test_dynamic_metadata_types_are_importable():
    from core.metadata_engine import MetadataEngine

    assert MetadataEngine is not None


@pytest.mark.asyncio
async def test_asyncio_integration_fixture():
    await __import__("asyncio").sleep(0)
    assert True
