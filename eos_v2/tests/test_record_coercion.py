from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from eos_v2.domain.metadata.coercion import coerce_record_data
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition


def test_transport_values_are_coerced_to_domain_types() -> None:
    target = uuid4()
    definition = EntityDefinition(
        name="invoice",
        fields=(
            FieldDefinition("amount", FieldType.DECIMAL),
            FieldDefinition("due_date", FieldType.DATE),
            FieldDefinition("posted_at", FieldType.DATETIME),
            FieldDefinition("customer_id", FieldType.UUID),
        ),
        relationships=(RelationshipDefinition("customer", target),),
    )
    data = coerce_record_data(definition, {
        "amount": "12.50",
        "due_date": "2026-09-06",
        "posted_at": "2026-09-06T12:00:00+00:00",
        "customer_id": str(target),
        "customer": str(target),
    })
    assert data["amount"] == Decimal("12.50")
    assert data["due_date"] == date(2026, 9, 6)
    assert isinstance(data["posted_at"], datetime)
    assert data["customer_id"] == target
    assert data["customer"] == target
