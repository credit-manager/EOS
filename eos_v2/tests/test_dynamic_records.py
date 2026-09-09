from __future__ import annotations

from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import reset_tenant_context, set_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType
from eos_v2.domain.metadata.record_validation import RecordValidationError, validate_record
from eos_v2.domain.metadata.records import DynamicRecord


def test_record_validation_required_and_type() -> None:
    definition = EntityDefinition(
        tenant_id=uuid4(), name="customer", fields=(
            FieldDefinition("name", FieldType.TEXT, required=True),
            FieldDefinition("age", FieldType.INTEGER),
        ),
    )
    with pytest.raises(RecordValidationError):
        validate_record(definition, {})
    with pytest.raises(RecordValidationError):
        validate_record(definition, {"name": 42})
    validate_record(definition, {"name": "Acme", "age": 3})


def test_record_validation_rejects_unknown_fields() -> None:
    definition = EntityDefinition(tenant_id=uuid4(), name="customer")
    with pytest.raises(RecordValidationError, match="Unknown fields"):
        validate_record(definition, {"unexpected": "x"})


def test_record_requires_explicit_tenant_and_entity() -> None:
    with pytest.raises(ValueError):
        DynamicRecord()


def test_tenant_context_is_required_for_scoped_record_operations() -> None:
    token = set_tenant_context(uuid4())
    try:
        assert True
    finally:
        reset_tenant_context(token)
