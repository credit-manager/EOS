from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    r = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'customers' ORDER BY ordinal_position"))
    print("customers columns:", [(row[0], row[1]) for row in r])

    r2 = db.execute(text("SELECT * FROM customers LIMIT 3"))
    print("customers rows:", [dict(row._mapping) for row in r2])

    r3 = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'dbp_customers' ORDER BY ordinal_position"))
    print("dbp_customers columns:", [(row[0], row[1]) for row in r3])

    r4 = db.execute(text("SELECT * FROM dbp_customers LIMIT 3"))
    print("dbp_customers rows:", [dict(row._mapping) for row in r4])
finally:
    db.close()
