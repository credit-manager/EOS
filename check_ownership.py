from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Check table ownership
result = db.execute(text("""
    SELECT
        schemaname,
        tablename,
        tableowner
    FROM pg_tables
    WHERE tablename IN ('account_statements', 'dbp_entities')
"""))

print("Table ownership:")
for row in result:
    print(f"  {row[1]:25s} owner={row[2]}")

# Check current user
current = db.execute(text("SELECT current_user")).scalar()
print(f"\nCurrent user: {current}")

# Check if we can create index on account_statements
try:
    db.execute(text("""
        CREATE INDEX CONCURRENTLY idx_account_statements_tenant_test
        ON account_statements(tenant_id)
    """))
    db.commit()
    print("CREATE INDEX: SUCCESS")
    # Drop the test index
    db.execute(text("DROP INDEX idx_account_statements_tenant_test"))
    db.commit()
except Exception as e:
    db.rollback()
    print(f"CREATE INDEX: FAILED - {e}")

db.close()
