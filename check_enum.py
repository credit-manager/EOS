from database import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()
r = db.execute(text("""
    SELECT enum_values
    FROM dbp_fields
    WHERE code = 'account_type'
    AND entity_id = (SELECT id FROM dbp_entities WHERE code = 'account')
"""))
row = r.fetchone()
if row and row[0]:
    vals = row[0] if isinstance(row[0], list) else json.loads(row[0])
    print(f"account_type enum values: {vals}")
else:
    print("No enum values found")

db.close()
