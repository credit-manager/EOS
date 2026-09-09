from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

result = db.execute(text("SELECT id, code FROM accounts WHERE code LIKE 'TEST-%'"))
rows = result.fetchall()
print(f"Found {len(rows)} test records:")
for row in rows:
    print(f"  id={row[0]}, code={row[1]}")

if rows:
    codes = [row[1] for row in rows]
    print(f"\nDeleting test records with codes: {codes}")
    db.execute(text("DELETE FROM accounts WHERE code LIKE 'TEST-%'"))
    db.commit()
    print("Deleted.")

db.close()
