"""Dynamic CRUD engine — generates working APIs from Builder metadata."""
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import Session

from ..db import Base, engine
from .models import BuilderField, BuilderObject

logger = logging.getLogger("2to-eos.builder.crud")

FIELD_TYPE_MAP = {
    "text": String(500),
    "number": String(50),
    "boolean": String(10),
    "date": String(30),
    "email": String(200),
    "phone": String(50),
    "url": String(500),
    "select": String(200),
    "multiselect": Text,
    "json": Text,
}


def _table_name(object_code: str) -> str:
    return f"builder_{object_code.lower().replace(' ', '_')}"


class DynamicCRUDService:
    """Provides CRUD operations for any Builder-defined object."""

    def __init__(self, db: Session):
        self.db = db

    def ensure_table(self, object_id: str, tenant_id: str) -> BuilderObject | None:
        """Ensure the dynamic table exists for a Builder object."""
        obj = self.db.query(BuilderObject).filter(
            BuilderObject.id == object_id, BuilderObject.tenant_id == tenant_id
        ).first()
        if not obj:
            return None

        table_name = _table_name(obj.code)
        fields = (
            self.db.query(BuilderField)
            .filter(BuilderField.object_id == object_id, BuilderField.is_active)
            .order_by(BuilderField.sort_order)
            .all()
        )

        columns = [
            Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
            Column("tenant_id", String(36), nullable=False, index=True),
            Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
            Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        ]

        for field in fields:
            col_type = FIELD_TYPE_MAP.get(field.field_type, String(500))
            columns.append(Column(field.code, col_type, nullable=not field.is_required))

        columns.append(Column("data_json", Text, nullable=True))

        from sqlalchemy import MetaData, Table
        metadata = MetaData()
        table = Table(table_name, metadata, *columns, extend_existing=True)

        try:
            metadata.create_all(engine)
            logger.info("Ensured table '%s' exists for object %s", table_name, obj.code)
        except Exception as e:
            logger.error("Failed to create table '%s': %s", table_name, e)
            return None

        return obj

    def create(self, object_id: str, tenant_id: str, data: dict) -> dict:
        """Create a record for a Builder object."""
        obj = self.ensure_table(object_id, tenant_id)
        if not obj:
            raise ValueError("Object not found")

        table_name = _table_name(obj.code)
        fields = self._get_fields(object_id)

        record_id = str(uuid.uuid4())
        row_data = {
            "id": record_id,
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        extra_data = {}
        for field in fields:
            if field.code in data:
                row_data[field.code] = str(data[field.code]) if data[field.code] is not None else None
            elif field.default_value:
                row_data[field.code] = field.default_value
            else:
                row_data[field.code] = None

        for k, v in data.items():
            if k not in {f.code for f in fields} and k not in ("id", "tenant_id"):
                extra_data[k] = v

        if extra_data:
            row_data["data_json"] = json.dumps(extra_data)

        from sqlalchemy import text
        cols = ", ".join(row_data.keys())
        placeholders = ", ".join([f":{k}" for k in row_data.keys()])
        stmt = text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})")
        self.db.execute(stmt, row_data)
        self.db.commit()

        return {"id": record_id, **data}

    def list(self, object_id: str, tenant_id: str, limit: int = 50, offset: int = 0):
        """List records for a Builder object."""
        obj = self.db.query(BuilderObject).filter(
            BuilderObject.id == object_id, BuilderObject.tenant_id == tenant_id
        ).first()
        if not obj:
            return []

        table_name = _table_name(obj.code)
        from sqlalchemy import text
        stmt = text(f"SELECT * FROM {table_name} WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT :lim OFFSET :off")
        rows = self.db.execute(stmt, {"tid": tenant_id, "lim": limit, "off": offset}).fetchall()
        return [dict(row._mapping) for row in rows]

    def get(self, object_id: str, tenant_id: str, record_id: str) -> dict | None:
        """Get a single record."""
        obj = self.db.query(BuilderObject).filter(
            BuilderObject.id == object_id, BuilderObject.tenant_id == tenant_id
        ).first()
        if not obj:
            return None

        table_name = _table_name(obj.code)
        from sqlalchemy import text
        stmt = text(f"SELECT * FROM {table_name} WHERE id = :rid AND tenant_id = :tid")
        row = self.db.execute(stmt, {"rid": record_id, "tid": tenant_id}).fetchone()
        return dict(row._mapping) if row else None

    def update(self, object_id: str, tenant_id: str, record_id: str, data: dict) -> dict | None:
        """Update a record."""
        obj = self.db.query(BuilderObject).filter(
            BuilderObject.id == object_id, BuilderObject.tenant_id == tenant_id
        ).first()
        if not obj:
            return None

        table_name = _table_name(obj.code)
        fields = self._get_fields(object_id)
        field_codes = {f.code for f in fields}

        set_parts = ["updated_at = :now"]
        params = {"rid": record_id, "tid": tenant_id, "now": datetime.utcnow()}

        for k, v in data.items():
            if k in field_codes:
                set_parts.append(f"{k} = :{k}")
                params[k] = str(v) if v is not None else None

        from sqlalchemy import text
        stmt = text(f"UPDATE {table_name} SET {', '.join(set_parts)} WHERE id = :rid AND tenant_id = :tid")
        self.db.execute(stmt, params)
        self.db.commit()

        return self.get(object_id, tenant_id, record_id)

    def delete(self, object_id: str, tenant_id: str, record_id: str) -> bool:
        """Delete a record."""
        obj = self.db.query(BuilderObject).filter(
            BuilderObject.id == object_id, BuilderObject.tenant_id == tenant_id
        ).first()
        if not obj:
            return False

        table_name = _table_name(obj.code)
        from sqlalchemy import text
        stmt = text(f"DELETE FROM {table_name} WHERE id = :rid AND tenant_id = :tid")
        self.db.execute(stmt, {"rid": record_id, "tid": tenant_id})
        self.db.commit()
        return True

    def _get_fields(self, object_id: str):
        return (
            self.db.query(BuilderField)
            .filter(BuilderField.object_id == object_id, BuilderField.is_active)
            .order_by(BuilderField.sort_order)
            .all()
        )

    def get_schema(self, object_id: str, tenant_id: str) -> dict:
        """Get the schema for a Builder object (for frontend form generation)."""
        obj = self.db.query(BuilderObject).filter(
            BuilderObject.id == object_id, BuilderObject.tenant_id == tenant_id
        ).first()
        if not obj:
            return {}

        fields = self._get_fields(object_id)
        return {
            "object_code": obj.code,
            "object_name": obj.name,
            "fields": [
                {
                    "code": f.code,
                    "name": f.name,
                    "type": f.field_type,
                    "required": f.is_required,
                    "unique": f.is_unique,
                    "default": f.default_value,
                    "options": f.options,
                    "validation": f.validation_rules,
                }
                for f in fields
            ],
        }
