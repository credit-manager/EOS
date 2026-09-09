"""
P10 Migration — Add deleted_at, deleted_by to all entity tables.
Soft Delete support.
"""
import sys
sys.path.insert(0, '.')
from database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

print("=" * 60)
print("P10 MIGRATION: Adding deleted_at, deleted_by columns")
print("=" * 60)

# Get all entity tables
tables = db.execute(text(
    "SELECT code, table_mapping FROM dbp_entities "
    "WHERE table_mapping IS NOT NULL"
)).fetchall()

for entity_code, table_name in tables:
    if not table_name:
        continue

    print(f"\n--- {entity_code} -> {table_name} ---")

    # Check if columns already exist
    existing = db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :tname AND column_name IN ('deleted_at', 'deleted_by')"
    ), {"tname": table_name}).fetchall()

    existing_cols = {r[0] for r in existing}

    if 'deleted_at' not in existing_cols:
        db.execute(text(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN deleted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL"
        ))
        print(f"  Added: deleted_at (TIMESTAMP, DEFAULT NULL)")
    else:
        print(f"  deleted_at already exists — skipping")

    if 'deleted_by' not in existing_cols:
        db.execute(text(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN deleted_by VARCHAR DEFAULT NULL"
        ))
        print(f"  Added: deleted_by (VARCHAR, DEFAULT NULL)")
    else:
        print(f"  deleted_by already exists — skipping")

db.commit()

# Verify
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

for entity_code, table_name in tables:
    if not table_name:
        continue
    cols = db.execute(text(
        "SELECT column_name, data_type, column_default "
        "FROM information_schema.columns "
        "WHERE table_name = :tname "
        "AND column_name IN ('deleted_at', 'deleted_by') "
        "ORDER BY column_name"
    ), {"tname": table_name}).fetchall()

    print(f"\n  {table_name}:")
    for c in cols:
        print(f"    {c[0]:15s} type={c[1]:45s} default={c[2]}")

db.close()
print("\nMigration complete!")
