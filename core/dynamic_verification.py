from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import uuid
import re

from models import DBPEntity, DBPField
from core.metadata_engine import MetadataEngine


class DynamicVerificationEngine:
    """Conservative verification layer with tenant-scoped metadata lookup."""

    def __init__(self, db: Session, entity_code: str, tenant_id: Optional[str] = None):
        self.db = db
        self.entity_code = entity_code
        self.tenant_id = tenant_id

        self.entity_meta: Optional[Dict[str, Any]] = None
        self.table_name: Optional[str] = None
        self.table_valid: bool = False
        self.real_columns: Dict[str, Any] = {}
        self.not_null_columns: List[str] = []
        self.tenant_capability = "NONE"
        self.pk_column: str = "id"
        self.pk_type: str = "uuid"

        self._load_entity()
        self._inspect_table()

    def _load_entity(self) -> None:
        # Tenant-owned metadata must never be resolved by code alone.
        # A tenant may reuse the same entity code as another tenant.
        if self.tenant_id is not None:
            entity = (
                self.db.query(DBPEntity)
                .filter(
                    DBPEntity.code == self.entity_code,
                    DBPEntity.tenant_id == self.tenant_id,
                )
                .first()
            )
            # Allow a system/global entity as a fallback for the tenant.
            if entity is None:
                entity = (
                    self.db.query(DBPEntity)
                    .filter(
                        DBPEntity.code == self.entity_code,
                        DBPEntity.tenant_id.is_(None),
                    )
                    .first()
                )
        else:
            # Without authenticated tenant context, only global metadata is
            # eligible. This prevents anonymous code-only metadata selection.
            entity = (
                self.db.query(DBPEntity)
                .filter(
                    DBPEntity.code == self.entity_code,
                    DBPEntity.tenant_id.is_(None),
                )
                .first()
            )

        if not entity:
            return

        self.entity_meta = {
            "id": entity.id,
            "code": entity.code,
            "name_en": entity.name_en,
            "name_ar": entity.name_ar,
            "faculty": entity.faculty,
            "table_mapping": entity.table_mapping,
            "is_system": entity.is_system,
            "tenant_id": entity.tenant_id,
        }
        self.table_name = entity.table_mapping

    def _inspect_table(self) -> None:
        if not self.table_name:
            return
        try:
            table_check = self.db.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = :tname AND table_schema = 'public'"
                ),
                {"tname": self.table_name},
            ).fetchone()
            if not table_check:
                return

            self.table_valid = True
            columns = self.db.execute(
                text(
                    "SELECT c.column_name, c.is_nullable, c.data_type, "
                    "c.character_maximum_length FROM information_schema.columns c "
                    "WHERE c.table_name = :tname AND c.table_schema = 'public' "
                    "ORDER BY c.ordinal_position"
                ),
                {"tname": self.table_name},
            ).fetchall()
            self.real_columns = {col[0].lower(): col[0] for col in columns}
            self.not_null_columns = [col[0] for col in columns if col[1] == "NO"]
            self.tenant_capability = "SCOPED" if "tenant_id" in self.real_columns else "NONE"

            pk_rows = self.db.execute(
                text(
                    "SELECT a.attname, t.typname FROM pg_constraint c "
                    "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey) "
                    "JOIN pg_class cl ON cl.oid = c.conrelid "
                    "JOIN pg_type t ON t.oid = a.atttypid "
                    "WHERE c.contype = 'p' AND cl.relname = :tname "
                    "ORDER BY array_position(c.conkey, a.attnum) LIMIT 1"
                ),
                {"tname": self.table_name},
            ).fetchone()
            if pk_rows:
                self.pk_column, self.pk_type = pk_rows[0], pk_rows[1]
        except Exception:
            self.table_valid = False
            self.real_columns = {}
            self.tenant_capability = "NONE"
            self.pk_column, self.pk_type = "id", "uuid"

    def generate_pk_value(self) -> Any:
        if "uuid" in self.pk_type:
            return str(uuid.uuid4())
        if "int" in self.pk_type:
            try:
                result = self.db.execute(text(f"SELECT MAX({self.pk_column}) FROM {self.table_name}")).scalar()
                return (result or 0) + 1
            except Exception:
                return 1
        return str(uuid.uuid4())

    def get_pk_column(self) -> str:
        return self.pk_column

    def entity_exists(self) -> bool:
        return self.entity_meta is not None

    def has_table_mapping(self) -> bool:
        return bool(self.entity_meta and self.entity_meta.get("table_mapping"))

    def is_table_valid(self) -> bool:
        return self.table_valid

    def has_tenant_id_column(self) -> bool:
        return self.tenant_capability == "SCOPED"

    def detect_tenant_handling(self) -> str:
        return self.tenant_capability

    def validate_table_mapping(self) -> Optional[str]:
        if not self.table_name:
            return "Table mapping غير موجود"
        if not self.table_valid:
            return f"الجدول '{self.table_name}' غير موجود في قاعدة البيانات"
        if not re.match(r"^[a-z0-9_]+$", self.table_name):
            return f"اسم الجدول '{self.table_name}' يحتوي على أحرف غير آمنة"
        return None

    def get_not_null_columns(self) -> List[str]:
        return list(self.not_null_columns)

    def validate_not_null_columns(self, data: Dict[str, Any], exclude_cols: Optional[List[str]] = None) -> List[str]:
        excluded = set(exclude_cols or []) | {"id"}
        return [f"{col}: الحقل مطلوب (NOT NULL في قاعدة البيانات)" for col in self.not_null_columns
                if col not in excluded and (col not in data or data[col] is None)]

    def get_table_columns(self) -> List[str]:
        return list(self.real_columns.values())

    def check_column_exists(self, column_name: str) -> bool:
        return bool(column_name) and column_name.lower() in self.real_columns

    def get_valid_columns(self, payload: Dict[str, Any]) -> List[str]:
        return [key for key in payload.keys() if self.check_column_exists(key)]

    def validate_data(self, data: Dict[str, Any]) -> bool:
        if not self.entity_exists():
            raise ValueError(f"الكيان '{self.entity_code}' غير موجود")
        return MetadataEngine(self.db).validate_data(self.entity_code, data)

    def validate_required_fields(self, data: Dict[str, Any]) -> None:
        return MetadataEngine(self.db).validate_required_fields(self.entity_code, data)

    def validate_enum_fields(self, data: Dict[str, Any]) -> None:
        return MetadataEngine(self.db).validate_enum_fields(self.entity_code, data)

    def check_duplicate_by_unique_fields(self, data: Dict[str, Any], tenant_id: Optional[str] = None) -> List[str]:
        return MetadataEngine(self.db).check_duplicate_by_unique_fields(self.entity_code, data, tenant_id=tenant_id)
