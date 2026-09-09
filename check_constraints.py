from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

r = db.execute(text("""
    SELECT conname, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'test_products'::regclass
    AND contype = 'u'
"""))

for row in r:
    print(f"Constraint: {row[0]}")
    print(f"Definition: {row[1]}")

db.close()
