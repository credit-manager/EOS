"""
Index Remediation Script

Creates missing tenant_id indexes identified in the audit.
READ-ONLY on models.py, metadata_engine.py, dynamic_crud.py.
Only modifies PostgreSQL schema (adds indexes).
"""

from database import SessionLocal
from sqlalchemy import text


def create_indexes(db):
    """Create missing tenant_id indexes."""
    print("=== INDEX REMEDIATION ===\n")

    indexes_to_create = [
        {
            "table": "account_statements",
            "column": "tenant_id",
            "index_name": "idx_account_statements_tenant",
        },
        {
            "table": "dbp_entities",
            "column": "tenant_id",
            "index_name": "idx_dbp_entities_tenant",
        },
    ]

    for idx in indexes_to_create:
        table = idx["table"]
        column = idx["column"]
        index_name = idx["index_name"]

        print(f"Creating index: {index_name}")

        # Check if index already exists
        exists = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = :table_name
                AND indexname = :index_name
            )
        """), {"table_name": table, "index_name": index_name}).scalar()

        if exists:
            print(f"  SKIP: Index already exists")
            continue

        # Create index
        try:
            db.execute(text(f"""
                CREATE INDEX {index_name}
                ON {table}({column})
            """))
            db.commit()
            print(f"  OK: Created")
        except Exception as e:
            db.rollback()
            print(f"  ERROR: {e}")


def verify_indexes(db):
    """Verify all tenant_id indexes exist."""
    print("\n=== VERIFICATION ===\n")

    # Get all tables with tenant_id
    tables = db.execute(text("""
        SELECT DISTINCT table_name
        FROM information_schema.columns
        WHERE column_name = 'tenant_id'
        AND table_schema = 'public'
    """)).fetchall()

    missing = []
    for (table_name,) in tables:
        has_index = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = :table_name
                AND indexdef LIKE '%tenant_id%'
            )
        """), {"table_name": table_name}).scalar()

        if not has_index:
            missing.append(table_name)
            print(f"  MISSING: {table_name}.tenant_id")
        else:
            print(f"  OK: {table_name}.tenant_id indexed")

    if missing:
        print(f"\n  WARNING: {len(missing)} tables still missing tenant_id index")
    else:
        print(f"\n  All {len(tables)} SCOPED tables have tenant_id indexes")


def check_models_vs_db(db):
    """Check models.py vs DB schema compatibility."""
    print("\n=== MODELS vs DB SCHEMA CHECK ===\n")

    # Read models.py
    import os
    models_file = r"D:\EOS\Eos final\models.py"

    if not os.path.exists(models_file):
        print("  SKIP: models.py not found")
        return

    with open(models_file, 'r', encoding='utf-8') as f:
        models_code = f.read()

    # Check DBPEntity tenant_id definition
    if "tenant_id = Column" in models_code:
        print("  models.py: DBPEntity.tenant_id column defined")

        # Check if index=True is in models.py
        import re
        match = re.search(
            r"tenant_id\s*=\s*Column\([^)]*index\s*=\s*True[^)]*\)",
            models_code
        )
        if match:
            print("  models.py: index=True specified")
        else:
            print("  models.py: index=True NOT specified")
    else:
        print("  models.py: DBPEntity.tenant_id NOT found")

    # Check actual DB indexes
    has_index = db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'dbp_entities'
            AND indexdef LIKE '%tenant_id%'
        )
    """)).scalar()

    print(f"  PostgreSQL: dbp_entities.tenant_id indexed = {has_index}")

    # Check nullable
    nullable = db.execute(text("""
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_name = 'dbp_entities'
        AND column_name = 'tenant_id'
    """)).scalar()

    print(f"  PostgreSQL: dbp_entities.tenant_id nullable = {nullable}")

    if nullable == 'YES':
        print("  NOTE: tenant_id is nullable (accepted per architectural decision)")


def main():
    db = SessionLocal()

    try:
        create_indexes(db)
        verify_indexes(db)
        check_models_vs_db(db)

        print("\n=== REMEDIATION COMPLETE ===")
        print("No protected files were modified.")
        print("Only PostgreSQL indexes were created.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
