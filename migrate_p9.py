"""P9 migration: add on_delete and junction columns to dbp_relationships."""
import sys
sys.path.insert(0, ".")
from database import engine
from sqlalchemy import text

columns_to_add = [
    ("on_delete", "VARCHAR(20) DEFAULT 'restrict'"),
    ("junction_table", "VARCHAR(100) DEFAULT ''"),
    ("junction_source_col", "VARCHAR(100) DEFAULT ''"),
    ("junction_target_col", "VARCHAR(100) DEFAULT ''"),
]

with engine.connect() as conn:
    for col_name, col_def in columns_to_add:
        try:
            conn.execute(text(f"ALTER TABLE dbp_relationships ADD COLUMN {col_name} {col_def}"))
            print(f"Added: {col_name}")
        except Exception as e:
            print(f"{col_name}: {str(e)[:80]}")
    conn.commit()

print("Migration complete")
