"""Tenant-scoped metadata access and validation for EOS DBP."""
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import DBPEntity, DBPField


class MetadataEngine:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _require_tenant(tenant_id: str) -> str:
        if not tenant_id or not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id is required")
        return tenant_id.strip()

    def get_entity_by_code(self, code: str, tenant_id: str) -> dict[str, Any] | None:
        tenant_id = self._require_tenant(tenant_id)
        entity = (
            self.db.query(DBPEntity)
            .filter(
                DBPEntity.code == code,
                (DBPEntity.tenant_id == tenant_id) | (DBPEntity.tenant_id == "platform"),
            )
            .first()
        )
        if not entity:
            return None
        return {k: v for k, v in entity.__dict__.items() if k != "_sa_instance_state"}

    def get_entity_fields(self, entity_id: str, tenant_id: str) -> list:
        tenant_id = self._require_tenant(tenant_id)
        fields = (
            self.db.query(DBPField)
            .join(DBPEntity, DBPEntity.id == DBPField.entity_id)
            .filter(
                DBPField.entity_id == entity_id,
                (DBPEntity.tenant_id == tenant_id) | (DBPEntity.tenant_id == "platform"),
            )
            .order_by(text("CAST(ui_config->>'order' AS INTEGER) ASC"))
            .all()
        )
        return [{k: v for k, v in field.__dict__.items() if k != "_sa_instance_state"} for field in fields]

    def get_full_schema(self, code: str, tenant_id: str) -> dict[str, Any]:
        entity = self.get_entity_by_code(code, tenant_id)
        if not entity:
            raise ValueError(f"الكيان '{code}' غير موجود")
        return {"entity": entity, "fields": self.get_entity_fields(entity["id"], tenant_id)}

    def validate_data(self, code: str, data: dict[str, Any], tenant_id: str) -> bool:
        schema = self.get_full_schema(code, tenant_id)
        errors = {}
        for field in schema["fields"]:
            val = data.get(field["code"])
            if field["is_required"] and (val is None or str(val).strip() == ""):
                errors[field["code"]] = "مطلوب"
            elif val is not None and field["field_type"] == "enum" and field["enum_values"]:
                enum_list = field["enum_values"]
                if isinstance(enum_list, str):
                    enum_list = json.loads(enum_list)
                if val not in enum_list:
                    errors[field["code"]] = f"يجب أن يكون: {enum_list}"
        if errors:
            raise ValueError(json.dumps(errors, ensure_ascii=False))
        return True
