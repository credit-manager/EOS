import sys
sys.path.insert(0, r"D:\EOS\Eos final")
from database import SessionLocal
from sqlalchemy import text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()
try:
    # Find our demo tenant
    r = db.execute(text("SELECT tenant_id FROM dbp_saas_tenants WHERE slug = 'demo'"))
    row = r.fetchone()
    if not row:
        print("No demo tenant found")
        sys.exit(1)
    tenant_id = row[0]
    print(f"Tenant: {tenant_id}")

    # Hash password properly with bcrypt
    pw_hash = pwd_context.hash("admin123")

    # Update the user's password hash
    result = db.execute(text(
        "UPDATE dbp_users SET password_hash = :pw WHERE email = :e AND tenant_id = :t"
    ), {"pw": pw_hash, "e": "admin@demo.com", "t": tenant_id})
    db.commit()
    print(f"Updated password for admin@demo.com ({result.rowcount} rows)")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
