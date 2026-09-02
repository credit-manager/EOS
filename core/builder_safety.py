"""Safety hardening for the dynamic ERP builder.

PostgreSQL DDL is transactional. The original builder committed inside table
creation, which could leave physical tables behind after a later publish step
failed. This patch keeps schema changes in the caller transaction.
"""
from sqlalchemy import text

from core.builder_engine import FIELD_SQL_TYPES, BuilderEngine


def _atomic_ensure_physical_table(self, table_name, fields):
    col_defs = ["id VARCHAR(36) PRIMARY KEY", "tenant_id VARCHAR(100) NOT NULL"]
    for fld in fields:
        sqltype = FIELD_SQL_TYPES[fld["field_type"]]
        notnull = " NOT NULL" if fld.get("is_required") else ""
        col_defs.append(f"{fld['code']} {sqltype}{notnull}")
    col_defs.append("created_at TIMESTAMP DEFAULT NOW()")
    self.db.execute(text(
        f"CREATE TABLE IF NOT EXISTS public.{table_name} ({', '.join(col_defs)})"
    ))
    for fld in fields:
        sqltype = FIELD_SQL_TYPES[fld["field_type"]]
        self.db.execute(text(
            f"ALTER TABLE public.{table_name} ADD COLUMN IF NOT EXISTS {fld['code']} {sqltype}"
        ))
    # Deliberately no commit: publish() owns the transaction.


BuilderEngine._ensure_physical_table = _atomic_ensure_physical_table
