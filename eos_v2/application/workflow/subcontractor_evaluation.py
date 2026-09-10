from __future__ import annotations

from typing import Final
from uuid import UUID

from eos_v2.application.records.service import DynamicRecordService, RecordRepository
from eos_v2.domain.metadata.entities import EntityDefinition


EVALUATION_ENTITY: Final[str] = "subcontractor_evaluation"
ALLOWED_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "draft": frozenset({"submitted"}),
    "submitted": frozenset({"approved", "rejected"}),
    "rejected": frozenset({"draft"}),
    "approved": frozenset(),
}


class SubcontractorEvaluationWorkflow:
    """Small explicit workflow proving metadata records can enter a domain-safe state machine."""

    def __init__(self, repository: RecordRepository) -> None:
        self.records = DynamicRecordService(repository)

    def transition(
        self,
        definition: EntityDefinition,
        record_id: UUID,
        target_status: str,
        expected_row_version: int,
    ):
        if definition.name != EVALUATION_ENTITY:
            raise ValueError("This workflow only applies to subcontractor_evaluation")
        current = self.records.get(record_id)
        current_status = str(current.data.get("status", "draft"))
        allowed = ALLOWED_TRANSITIONS.get(current_status, frozenset())
        if target_status not in allowed:
            raise ValueError(f"Invalid workflow transition: {current_status} -> {target_status}")
        updated_data = dict(current.data)
        updated_data["status"] = target_status
        return self.records.update(definition, record_id, updated_data, expected_row_version)
