"""Executable proof for the canonical Metadata -> Record -> Workflow -> Audit slice."""
from __future__ import annotations

import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.audit.service import record_event
from eos_v2.application.records.service import DynamicRecordService
from eos_v2.application.workflow.subcontractor_evaluation import SubcontractorEvaluationWorkflow
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.infrastructure.db.record_models import DynamicRecordModel
from eos_v2.infrastructure.db.record_repository import SqlAlchemyRecordRepository
from eos_v2.infrastructure.db.session import Database, DatabaseConfig


@pytest.mark.postgres
def test_subcontractor_evaluation_real_postgres_vertical_slice() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required for the PostgreSQL vertical-slice proof")

    tenant_id = uuid4()
    actor_id = uuid4()
    token = set_tenant_context(TenantContext(tenant_id, actor_id))
    database = Database(DatabaseConfig(url))
    entity_name = f"subcontractor_evaluation_{str(tenant_id).replace('-', '')[:8]}"
    try:
        with database.session() as session:
            metadata = SqlAlchemyMetadataRepository(session)
            definition = EntityDefinition(
                tenant_id=tenant_id,
                name=entity_name,
                label="Subcontractor Evaluation",
                fields=(
                    FieldDefinition("subcontractor", FieldType.TEXT, required=True),
                    FieldDefinition("project", FieldType.TEXT, required=True),
                    FieldDefinition("evaluation_date", FieldType.DATE, required=True),
                    FieldDefinition("quality_score", FieldType.INTEGER, required=True),
                    FieldDefinition("safety_score", FieldType.INTEGER, required=True),
                    FieldDefinition("delivery_score", FieldType.INTEGER, required=True),
                    FieldDefinition("total_score", FieldType.INTEGER, required=True),
                    FieldDefinition("status", FieldType.TEXT, required=True),
                    FieldDefinition("notes", FieldType.TEXT),
                ),
                published=True,
            )
            metadata.add(definition)
            session.commit()

            persisted = metadata.get(definition.id)
            assert persisted.published is True
            assert persisted.tenant_id == tenant_id

            service = DynamicRecordService(SqlAlchemyRecordRepository(session))
            record = service.create(
                persisted,
                {
                    "subcontractor": "ACME Subcontracting",
                    "project": "North Campus",
                    "evaluation_date": date.today().isoformat(),
                    "quality_score": 90,
                    "safety_score": 95,
                    "delivery_score": 85,
                    "total_score": 90,
                    "status": "draft",
                    "notes": "Vertical slice proof",
                },
            )
            record_event(
                session,
                action="vertical_slice.evaluation_created",
                resource_type="dynamic_record",
                resource_id=record.id,
                actor_id=actor_id,
                metadata={"status": "draft"},
            )
            session.commit()

            updated = SubcontractorEvaluationWorkflow(SqlAlchemyRecordRepository(session)).transition(
                persisted, record.id, "submitted", record.row_version
            )
            record_event(
                session,
                action="vertical_slice.workflow_transition",
                resource_type="dynamic_record",
                resource_id=updated.id,
                actor_id=actor_id,
                metadata={"from": "draft", "to": "submitted", "row_version": updated.row_version},
            )
            session.commit()

            stored = session.scalar(select(DynamicRecordModel).where(DynamicRecordModel.id == record.id))
            assert stored is not None
            assert stored.tenant_id == tenant_id
            assert stored.row_version == 2
            assert stored.data["status"] == "submitted"

            audit_count = session.scalar(
                text(
                    "SELECT count(*) FROM eos_v2_audit_events "
                    "WHERE tenant_id = :tenant_id AND resource_id = :resource_id"
                ),
                {"tenant_id": str(tenant_id), "resource_id": str(record.id)},
            )
            assert audit_count == 2

            cross_tenant = uuid4()
            other_token = set_tenant_context(TenantContext(cross_tenant, uuid4()))
            try:
                with pytest.raises(KeyError):
                    SqlAlchemyRecordRepository(session).get(record.id)
            finally:
                reset_tenant_context(other_token)
    finally:
        with Session(database.engine) as cleanup:
            cleanup.execute(text("DELETE FROM eos_v2_audit_events WHERE tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})
            cleanup.execute(text("DELETE FROM eos_v2_dynamic_record_unique_values WHERE tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})
            cleanup.execute(text("DELETE FROM eos_v2_dynamic_records WHERE tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})
            cleanup.execute(text("DELETE FROM eos_v2_metadata_entities WHERE tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})
            cleanup.commit()
        reset_tenant_context(token)
        database.engine.dispose()
