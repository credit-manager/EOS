"""Check what fails in test_p21 when seed data is present."""
import subprocess, sys, os

# Seed companies first like 38.1 does
sys.path.insert(0, '.')
from database import SessionLocal
from sqlalchemy import text as sa

db = SessionLocal()
try:
    db.execute(sa("DELETE FROM dbp_companies WHERE id IN ('co_cert_a','co_cert_b')"))
    db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_cert_a','tenant_a','CCERTA','Cert Company A')"))
    db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_cert_b','tenant_b','CCERTB','Cert Company B')"))
    db.commit()
finally:
    db.close()

# Now run test_p21
result = subprocess.run([sys.executable, 'test_p21.py'], capture_output=True, text=True, timeout=300, env=os.environ.copy())
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-500:])
