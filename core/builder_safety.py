"""Safety hardening for the dynamic ERP builder.

DDL is kept inside the publish transaction and every generated SQL identifier
is validated before interpolation. Values must never be interpolated into DDL.
"""
import re

from sqlalchemy import text

from core.builder_engine import FIELD_SQL_TYPES, BuilderEngine

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def _safe_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {label} identifier")
    return value


def _atomic_ensure_physical_table(self, table_name, fields):
    table_name = _safe_identifier(table_name, "table")
    col_defs = ["id VARCHAR(36) PRIMARY KEY", "tenant_id VARCHAR(100) NOT NULL"]
    seen = {"id", "tenant_id", "created_at"}
    for fld in fields:
        code = _safe_identifier(fld["code"], "field")
        if code.lower() in seen:
            raise ValueError(f"Duplicate/reserved field identifier: {code}")
        seen.add(code.lower())
        field_type = fld.get("field_type")
        if field_type not in FIELD_SQL_TYPES:
            raise ValueError("Unsupported field type")
        sqltype = FIELD_SQL_TYPES[field_type]
        notnull = " NOT NULL" if fld.get("is_required") else ""
        col_defs.append(f'"{code}" {sqltype}{notnull}')
    col_defs.append("created_at TIMESTAMP DEFAULT NOW()")
    self.db.execute(text(f'CREATE TABLE IF NOT EXISTS public."{table_name}" ({", ".join(col_defs)})'))
    for fld in fields:
        code = _safe_identifier(fld["code"], "field")
        sqltype = FIELD_SQL_TYPES[fld["field_type"]]
        self.db.execute(text(f'ALTER TABLE public."{table_name}" ADD COLUMN IF NOT EXISTS "{code}" {sqltype}'))
    # Deliberately no commit: publish() owns the transaction.


BuilderEngine._ensure_physical_table = _atomic_ensure_physical_table
