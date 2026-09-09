from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
r = db.execute(text("""
    SELECT column_name, is_nullable, udt_name
    FROM information_schema.columns
    WHERE table_name = 'accounts'
    ORDER BY ordinal_position
"""))
print("accounts table columns:")
for row in r:
    print(f"  {row[0]:20s} nullable={row[1]:3s} type={row[2]}")

db.close()
