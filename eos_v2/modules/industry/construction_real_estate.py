from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition
from eos_v2.modules.industry import IndustryPack

KEY = "construction-real-estate"
VERSION = "1.0.0"


def _field(name: str, field_type: FieldType, *, required: bool = False, unique: bool = False) -> FieldDefinition:
    return FieldDefinition(name=name, field_type=field_type, required=required, unique=unique)


def build_pack(tenant_id: UUID) -> IndustryPack:
    land = EntityDefinition(tenant_id=tenant_id, name="land_parcel", label="Land Parcel", fields=(_field("code", FieldType.TEXT, required=True, unique=True), _field("area", FieldType.DECIMAL, required=True), _field("status", FieldType.TEXT, required=True)))
    project = EntityDefinition(tenant_id=tenant_id, name="development_project", label="Development Project", fields=(_field("code", FieldType.TEXT, required=True, unique=True), _field("name", FieldType.TEXT, required=True), _field("budget", FieldType.DECIMAL, required=True)), relationships=(RelationshipDefinition("land_parcel_id", land.id, required=True),))
    unit = EntityDefinition(tenant_id=tenant_id, name="property_unit", label="Property Unit", fields=(_field("code", FieldType.TEXT, required=True, unique=True), _field("unit_type", FieldType.TEXT, required=True), _field("area", FieldType.DECIMAL, required=True), _field("list_price", FieldType.DECIMAL, required=True), _field("status", FieldType.TEXT, required=True)), relationships=(RelationshipDefinition("project_id", project.id, required=True),))
    contract = EntityDefinition(tenant_id=tenant_id, name="property_contract", label="Property Contract", fields=(_field("contract_number", FieldType.TEXT, required=True, unique=True), _field("customer_id", FieldType.UUID, required=True), _field("contract_value", FieldType.DECIMAL, required=True), _field("status", FieldType.TEXT, required=True)), relationships=(RelationshipDefinition("unit_id", unit.id, required=True),))
    work_package = EntityDefinition(tenant_id=tenant_id, name="construction_work_package", label="Construction Work Package", fields=(_field("code", FieldType.TEXT, required=True, unique=True), _field("name", FieldType.TEXT, required=True), _field("planned_cost", FieldType.DECIMAL, required=True), _field("status", FieldType.TEXT, required=True)), relationships=(RelationshipDefinition("project_id", project.id, required=True),))
    return IndustryPack(KEY, VERSION, "Construction & Real Estate", tenant_id, (land, project, unit, contract, work_package))


@dataclass(frozen=True, slots=True)
class ConstructionRealEstatePack:
    key: str = KEY
    version: str = VERSION

    def build(self, tenant_id: UUID) -> IndustryPack:
        return build_pack(tenant_id)
