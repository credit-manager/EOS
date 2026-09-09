from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

rows = db.execute(text("""
    SELECT f.code, f.label_en, f.field_type, f.is_required
    FROM dbp_fields f
    JOIN dbp_entities e ON f.entity_id = e.id
    WHERE e.code = 'account'
    ORDER BY f.code
"""))

print("Fields for 'account' entity:")
for row in rows:
    print(f"  {row[0]:20s} type={row[2]:10s} required={row[3]}")

db.close()
