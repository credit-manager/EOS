import sys
sys.path.insert(0, r"D:\EOS\Eos final")
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    r = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
    tables = [row[0] for row in r.fetchall()]
    print(f"Tables: {len(tables)}")
    for t in tables[:15]:
        print(f"  {t}")
    if len(tables) > 15:
        print(f"  ... and {len(tables)-15} more")

    # Check for users
    try:
        r2 = db.execute(text("SELECT email, tenant_id, role FROM dbp_users LIMIT 5"))
        users = r2.fetchall()
        print(f"\nUsers: {len(users)}")
        for u in users:
            print(f"  {u[0]} | tenant={u[1]} | role={u[2]}")
    except:
        print("\nNo dbp_users table or different schema")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
