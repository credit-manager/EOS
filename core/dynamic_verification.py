from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
import uuid
import re

from models import DBPEntity, DBPField
from core.metadata_engine import MetadataEngine


class DynamicVerificationEngine:
    """
    Conservative verification layer.

    Important distinction:
        dbp_entities.tenant_id
        !=
        actual table tenant_id column

    Tenant capability is determined ONLY from the real table schema.

    Tenant VALUE for SCOPED operations comes ONLY from
    authenticated context — NOT from entity metadata or payload.
    """

    def __init__(self, db: Session, entity_code: str):
        self.db = db
        self.entity_code = entity_code

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
        entity = (
            self.db.query(DBPEntity)
            .filter(DBPEntity.code == self.entity_code)
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
        }

        self.table_name = entity.table_mapping

    def _inspect_table(self) -> None:
        if not self.table_name:
            return

        try:
            # Use raw SQL via self.db session (NOT inspect()) to avoid pool exhaustion
            table_check = self.db.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = :tname AND table_schema = 'public'"
                ),
                {"tname": self.table_name}
            ).fetchone()

            if not table_check:
                self.table_valid = False
                return

            self.table_valid = True

            columns = self.db.execute(
                text(
                    "SELECT c.column_name, c.is_nullable, c.data_type, "
                    "c.character_maximum_length "
                    "FROM information_schema.columns c "
                    "WHERE c.table_name = :tname AND c.table_schema = 'public' "
                    "ORDER BY c.ordinal_position"
                ),
                {"tname": self.table_name}
            ).fetchall()

            # real_columns: {lowercase: original} — matches inspector format
            self.real_columns = {
                col[0].lower(): col[0]
                for col in columns
            }

            # not_null_columns: list of column names where IS_NULLABLE = 'NO'
            # Matches inspector: not column.get("nullable", True) — i.e. not-nullable
            self.not_null_columns = [
                col[0]
                for col in columns
                if col[1] == "NO"
            ]

            if "tenant_id" in self.real_columns:
                self.tenant_capability = "SCOPED"
            else:
                self.tenant_capability = "NONE"

            # Detect PK via pg_constraint (avoids inspector)
            pk_rows = self.db.execute(
                text(
                    "SELECT a.attname, t.typname "
                    "FROM pg_constraint c "
                    "JOIN pg_attribute a ON a.attrelid = c.conrelid "
                    "AND a.attnum = ANY(c.conkey) "
                    "JOIN pg_class cl ON cl.oid = c.conrelid "
                    "JOIN pg_type t ON t.oid = a.atttypid "
                    "WHERE c.contype = 'p' "
                    "AND cl.relname = :tname "
                    "ORDER BY array_position(c.conkey, a.attnum) "
                    "LIMIT 1"
                ),
                {"tname": self.table_name}
            ).fetchone()

            if pk_rows:
                self.pk_column = pk_rows[0]
                self.pk_type = pk_rows[1]
            else:
                self.pk_column = "id"
                self.pk_type = "uuid"

        except Exception:
            self.table_valid = False
            self.real_columns = {}
            self.tenant_capability = "NONE"
            self.pk_column = "id"
            self.pk_type = "uuid"

    def generate_pk_value(self) -> Any:
        """
        Generate a primary key value based on the PK column type.
        
        Supports:
        - UUID (default)
        - INTEGER (auto-increment simulation)
        - VARCHAR/STRING (UUID or custom format)
        """
        if "uuid" in self.pk_type:
            return str(uuid.uuid4())
        elif "int" in self.pk_type:
            # For integer PKs, we need to find the max value and increment
            try:
                query = text(f"SELECT MAX({self.pk_column}) FROM {self.table_name}")
                result = self.db.execute(query).scalar()
                return (result or 0) + 1
            except Exception:
                return 1
        else:
            # For string PKs, use UUID
            return str(uuid.uuid4())

    def get_pk_column(self) -> str:
        """Get the primary key column name."""
        return self.pk_column

    def entity_exists(self) -> bool:
        return self.entity_meta is not None

    def has_table_mapping(self) -> bool:
        return bool(
            self.entity_meta
            and self.entity_meta.get("table_mapping")
        )

    def is_table_valid(self) -> bool:
        """Check if table_mapping points to a real PostgreSQL table."""
        return self.table_valid

    def has_tenant_id_column(self) -> bool:
        return self.tenant_capability == "SCOPED"

    def detect_tenant_handling(self) -> str:
        return self.tenant_capability

    def validate_table_mapping(self) -> Optional[str]:
        """
        Validate that table_mapping is safe to use in SQL.
        Returns error message if invalid, None if valid.
        """
        if not self.table_name:
            return "Table mapping غير موجود"

        if not self.table_valid:
            return f"الجدول '{self.table_name}' غير موجود في قاعدة البيانات"

        # Verify table name contains only safe characters
        import re
        if not re.match(r'^[a-z0-9_]+$', self.table_name):
            return f"اسم الجدول '{self.table_name}' يحتوي على أحرف غير آمنة"

        return None

    def get_not_null_columns(self) -> List[str]:
        return list(self.not_null_columns)

    def validate_not_null_columns(
        self,
        data: Dict[str, Any],
        exclude_cols: Optional[List[str]] = None
    ) -> List[str]:
        exclude_cols = set(exclude_cols or [])
        exclude_cols.add("id")

        errors = []
        for col in self.not_null_columns:
            if col in exclude_cols:
                continue
            if col not in data or data[col] is None:
                errors.append(
                    f"{col}: الحقل مطلوب (NOT NULL في قاعدة البيانات)"
                )
        return errors

    def get_table_columns(self) -> List[str]:
        return list(self.real_columns.values())

    def check_column_exists(self, column_name: str) -> bool:
        if not column_name:
            return False
        return column_name.lower() in self.real_columns

    def get_valid_columns(
        self,
        payload: Dict[str, Any]
    ) -> List[str]:
        return [
            key
            for key in payload.keys()
            if self.check_column_exists(key)
        ]

    def validate_data(
        self,
        data: Dict[str, Any]
    ) -> bool:
        if not self.entity_exists():
            raise ValueError(
                f"الكيان '{self.entity_code}' غير موجود"
            )

        engine = MetadataEngine(self.db)
        return engine.validate_data(self.entity_code, data)

    def validate_required_fields(
        self,
        data: Dict[str, Any]
    ) -> bool:
        return self.validate_data(data)

    def validate_enum_fields(
        self,
        data: Dict[str, Any]
    ) -> bool:
        return True

    def get_unique_constraints(self) -> List[List[str]]:
        """Get actual unique constraints as lists of column groups."""
        if not self.table_name:
            return []

        try:
            constraints = []

            # Get unique constraints from pg_constraint via raw SQL
            rows = self.db.execute(
                text(
                    "SELECT a.attname "
                    "FROM pg_constraint c "
                    "JOIN pg_attribute a ON a.attrelid = c.conrelid "
                    "AND a.attnum = ANY(c.conkey) "
                    "JOIN pg_class cl ON cl.oid = c.conrelid "
                    "JOIN pg_namespace n ON n.oid = cl.relnamespace "
                    "WHERE c.contype = 'u' "
                    "AND cl.relname = :tname "
                    "ORDER BY c.conname, array_position(c.conkey, a.attnum)"
                ),
                {"tname": self.table_name}
            ).fetchall()

            # Group columns per constraint
            current_group = []
            for row in rows:
                if row[0] not in current_group:
                    current_group.append(row[0])
            if current_group:
                constraints.append(current_group)

            return constraints

        except Exception:
            return []

    def check_duplicate_by_unique_fields(
        self,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Check for duplicate records based on unique constraints.

        For composite constraints like (tenant_id, code),
        the check is scoped to the tenant if tenant_id is provided.
        """
        if not self.table_name:
            return []

        errors = []
        constraints = self.get_unique_constraints()

        for cols in constraints:
            # Skip constraints where not all columns are in data
            if not all(c in data for c in cols):
                continue

            # Skip constraints where all values are None
            values = [data[c] for c in cols]
            if all(v is None for v in values):
                continue

            # Build WHERE clause
            conditions = []
            params = {}
            for i, col in enumerate(cols):
                conditions.append(f"{col} = :val_{i}")
                params[f"val_{i}"] = data[col]

            where_clause = " AND ".join(conditions)

            # For composite constraints with tenant_id,
            # scope to the same tenant
            if (
                "tenant_id" in cols
                and tenant_id
                and "tenant_id" in data
            ):
                # Already scoped by tenant_id in the constraint
                pass
            elif (
                "tenant_id" not in cols
                and tenant_id
                and self.check_column_exists("tenant_id")
            ):
                # Single-column unique constraint on a SCOPED table
                # Add tenant scoping
                where_clause += " AND tenant_id = :tenant_scope"
                params["tenant_scope"] = tenant_id

            query = text(
                f"""
                SELECT 1
                FROM {self.table_name}
                WHERE {where_clause}
                LIMIT 1
                """
            )

            row = self.db.execute(query, params).first()

            if row:
                col_names = ", ".join(cols)
                errors.append(
                    f"{col_names}: موجود بالفعل"
                )

        return errors
