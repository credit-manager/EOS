import sys
sys.path.insert(0, r"D:\EOS\Eos final")
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Check existing tenants
    r = db.execute(text("SELECT id, tenant_id, name, slug FROM dbp_saas_tenants LIMIT 10"))
    tenants = r.fetchall()
    print("Existing tenants:")
    for t in tenants:
        print(f"  id={t[0]} | tenant_id={t[1]} | name={t[2]} | slug={t[3]}")

    if not tenants:
        print("\nNo tenants found. Creating one...")
        import uuid
        tid = str(uuid.uuid4())
        db.execute(text(
            "INSERT INTO dbp_saas_tenants (id, tenant_id, name, slug, status, created_at, updated_at) "
            "VALUES (:id, :t, 'Demo Company', 'demo', 'active', NOW(), NOW())"
        ), {"id": tid, "t": tid})
        db.commit()
        print(f"Created tenant with id={tid}")

    # Pick first tenant
    r = db.execute(text("SELECT tenant_id FROM dbp_saas_tenants LIMIT 1"))
    tenant_id = r.fetchone()[0]
    print(f"\nUsing tenant: {tenant_id}")

    # Create admin user
    import uuid, hashlib
    user_id = str(uuid.uuid4())
    email = "admin@demo.com"
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()

    r = db.execute(text("SELECT id FROM dbp_users WHERE email = :e"), {"e": email})
    if r.fetchone():
        print(f"User {email} already exists")
    else:
        db.execute(text(
            "INSERT INTO dbp_users (id, tenant_id, email, password_hash, first_name, last_name, role, is_active, created_at, updated_at) "
            "VALUES (:id, :t, :e, :pw, 'Admin', 'User', 'admin', true, NOW(), NOW())"
        ), {"id": user_id, "t": tenant_id, "e": email, "pw": password_hash})
        db.commit()
        print(f"Created user: {email}")

    # List users
    r = db.execute(text("SELECT email, tenant_id, role FROM dbp_users ORDER BY created_at DESC LIMIT 10"))
    print("\nAll users:")
    for row in r.fetchall():
        print(f"  {row[0]} | tenant={row[1]} | role={row[2]}")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
