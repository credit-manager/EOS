from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
import json

from models import DBPEntity, DBPField


class MetadataEngine:

    def __init__(self, db: Session):
        self.db = db

    def get_entity_by_code(
        self,
        code: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return entity metadata scoped to the effective tenant.

        Tenant-specific metadata is isolated by tenant_id while platform/shared
        metadata remains available through NULL tenant ownership for legacy
        installations that still contain shared definitions.
        """
        query = self.db.query(DBPEntity).filter(DBPEntity.code == code)
        if tenant_id is not None:
            query = query.filter(
                (DBPEntity.tenant_id == tenant_id)
                | (DBPEntity.tenant_id.is_(None))
            )

        entity = query.first()

        if not entity:
            return None

        return {
            k: v
            for k, v in entity.__dict__.items()
            if k != "_sa_instance_state"
        }

    def get_entity_fields(
        self,
        entity_id: str,
        tenant_id: Optional[str] = None,
    ) -> list:
        """Return fields only for an entity visible in the effective tenant."""
        query = (
            self.db.query(DBPField)
            .join(DBPEntity, DBPEntity.id == DBPField.entity_id)
            .filter(DBPField.entity_id == entity_id)
        )
        if tenant_id is not None:
            query = query.filter(
                (DBPEntity.tenant_id == tenant_id)
                | (DBPEntity.tenant_id.is_(None))
            )

        fields = (
            query
            .order_by(
                text("CAST(ui_config->>'order' AS INTEGER) ASC")
            )
            .all()
        )

        return [
            {
                k: v
                for k, v in field.__dict__.items()
                if k != "_sa_instance_state"
            }
            for field in fields
        ]

    def get_full_schema(
        self,
        code: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a tenant-scoped metadata schema."""
        entity = self.get_entity_by_code(code, tenant_id=tenant_id)

        if not entity:
            raise ValueError(f"الكيان '{code}' غير موجود")

        return {
            "entity": entity,
            "fields": self.get_entity_fields(entity["id"], tenant_id=tenant_id)
        }

    def validate_data(
        self,
        code: str,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ):

        schema = self.get_full_schema(code, tenant_id=tenant_id)
        errors = {}

        for field in schema["fields"]:

            val = data.get(field["code"])

            if (
                field["is_required"]
                and (val is None or str(val).strip() == "")
            ):
                errors[field["code"]] = "مطلوب"

            elif (
                val is not None
                and field["field_type"] == "enum"
                and field["enum_values"]
            ):

                enum_list = field["enum_values"]

                if isinstance(enum_list, str):
                    enum_list = json.loads(enum_list)

                if val not in enum_list:
                    errors[field["code"]] = (
                        f"يجب أن يكون: {enum_list}"
                    )

        if errors:
            raise ValueError(
                json.dumps(errors, ensure_ascii=False)
            )

        return True
