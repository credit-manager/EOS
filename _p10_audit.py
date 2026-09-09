"""P10.1 Architecture Audit — Check current schema for soft delete readiness"""
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 60)
print("P10.1 ARCHITECTURE AUDIT")
print("=" * 60)

# 1. Check test_products columns
print("\n--- test_products columns ---")
rows = db.execute(text(
    "SELECT column_name, data_type, is_nullable "
    "FROM information_schema.columns "
    "WHERE table_name = 'test_products' ORDER BY ordinal_position"
)).fetchall()
for r in rows:
    print(f"  {r[0]:25s} {r[1]:25s} nullable={r[2]}")
has_deleted_at = any(r[0] == 'deleted_at' for r in rows)
has_deleted_by = any(r[0] == 'deleted_by' for r in rows)
print(f"\n  deleted_at exists: {has_deleted_at}")
print(f"  deleted_by exists: {has_deleted_by}")

# 2. Check DBP metadata tables
print("\n--- DBP metadata tables ---")
tables = db.execute(text(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_name LIKE 'dbp_%' "
    "ORDER BY table_name"
)).fetchall()
for t in tables:
    print(f"  {t[0]}")

# 3. Check how delete is currently used
print("\n--- Current delete operations in codebase ---")
print("  dynamic_crud.py: DELETE /entities/{code}/records/{id}")
print("  dynamic_crud.py: DELETE /entities/{code}/records/bulk-delete")
print("  relationships.py: DELETE /entities/{code}/relationships/{rel_code}")
print("  (All currently use physical DELETE)")

# 4. Check relationship count
print("\n--- Active relationships ---")
r = db.execute(text("SELECT COUNT(*) FROM dbp_relationships")).scalar()
print(f"  Total relationships: {r}")

# 5. Check entities with their table mappings
print("\n--- Entities and table mappings ---")
ents = db.execute(text("SELECT code, table_mapping FROM dbp_entities")).fetchall()
for e in ents:
    print(f"  {e[0]:30s} -> {e[1]}")

# 6. Count records per table
print("\n--- Record counts ---")
for e in ents:
    if e[1]:
        try:
            count = db.execute(text(f"SELECT COUNT(*) FROM {e[1]}")).scalar()
            print(f"  {e[1]:30s}: {count} rows")
        except Exception as ex:
            print(f"  {e[1]:30s}: ERROR - {ex}")

# 7. Test P9 relationship on_delete values
print("\n--- P9 relationship on_delete values ---")
rels = db.execute(text("SELECT code, relationship_type, on_delete FROM dbp_relationships")).fetchall()
for r in rels:
    print(f"  {r[0]}: type={r[1]}, on_delete={r[2]}")

# 8. Check export/import implications
print("\n--- Export/Import implications ---")
print("  Export: Should exclude soft-deleted records")
print("  Import: Should not import soft-deleted records")
print("  Template: No changes needed (deleted_at/deleted_by are system fields)")

# 9. Query engine implications
print("\n--- Query Engine (P7) implications ---")
print("  Default filter: WHERE deleted_at IS NULL")
print("  P7 filters must NOT allow filtering on deleted_at (security)")

# 10. Bulk delete implications
print("\n--- Bulk Delete (P8.3) implications ---")
print("  Currently: physical DELETE")
print("  After P10: soft DELETE (set deleted_at/deleted_by)")
print("  Atomic mode: If one fails, all roll back")

db.close()

print("\n" + "=" * 60)
print("AUDIT SUMMARY")
print("=" * 60)
print(f"  deleted_at column: {'EXISTS' if has_deleted_at else 'MISSING — needs migration'}")
print(f"  deleted_by column: {'EXISTS' if has_deleted_by else 'MISSING — needs migration'}")
print(f"  Entities affected: {len(ents)}")
print(f"  Tables to migrate: {len([e for e in ents if e[1]])}")
print(f"  Relationships to consider: {r}")
print(f"  Current approach: PHYSICAL DELETE (all endpoints)")
print(f"  Target approach: SOFT DELETE + RESTORE")
