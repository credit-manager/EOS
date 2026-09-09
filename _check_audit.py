from database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
rows = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'audit_logs' ORDER BY ordinal_position")).fetchall()
for r in rows: print(r[0])
db.close()
