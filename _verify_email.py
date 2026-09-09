import sys
sys.path.insert(0, r"D:\EOS\Eos final")
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    result = db.execute(text(
        "UPDATE dbp_users SET email_verified = true, verification_token_hash = NULL "
        "WHERE email = 'admin@demo.com'"
    ))
    db.commit()
    print(f"Email verified for admin@demo.com ({result.rowcount} rows)")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
