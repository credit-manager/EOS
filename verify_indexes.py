from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

r = db.execute(text("""
    SELECT indexname, tablename
    FROM pg_indexes
    WHERE indexname LIKE 'idx%tenant%'
    ORDER BY tablename
"""))

print("Tenant indexes created by remediation:")
for row in r:
    print(f"  {row[1]:25s} {row[0]}")

# Also check test_products
r2 = db.execute(text("""
    SELECT indexname, tablename
    FROM pg_indexes
    WHERE tablename = 'test_products'
"""))

print("\ntest_products indexes:")
for row in r2:
    print(f"  {row[1]:25s} {row[0]}")

db.close()
