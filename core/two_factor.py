"""TOTP-based 2FA with recovery codes, brute-force protection and audit."""
from __future__ import annotations

import base64, hashlib, hmac, secrets, struct, time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

try:
    import pyotp
except ImportError:
    pyotp = None

from sqlalchemy import text
from core.industry_security import uid, now
from core.secret_store import decrypt_text, encrypt_text


def _encrypt_secret(secret: str) -> str:
    """Encrypt 2FA material; never fall back to plaintext."""
    return encrypt_text(secret)


def _decrypt_secret(encrypted_secret: str) -> str:
    """Decrypt 2FA material; fail closed on malformed/legacy plaintext."""
    return decrypt_text(encrypted_secret)


def _generate_secret() -> str:
    if pyotp:
        return pyotp.random_base32()
    return base64.b32encode(secrets.token_bytes(20)).decode()


def _generate_recovery_codes(count: int = 8) -> List[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _check_brute_force(db, user_id: str, ip: str = None) -> Tuple[bool, str]:
    cutoff = (datetime.utcnow() - timedelta(minutes=15)).isoformat()
    result = db.execute(text(
        "SELECT COUNT(*) FROM dbp_2fa_attempts "
        "WHERE user_id = :uid AND attempted_at > :cutoff AND success = FALSE"
    ), {"uid": user_id, "cutoff": cutoff}).scalar()
    if result >= 5:
        return False, "Too many failed attempts. Account locked for 15 minutes."
    if ip:
        ip_count = db.execute(text(
            "SELECT COUNT(*) FROM dbp_2fa_attempts "
            "WHERE ip_address = :ip AND attempted_at > :cutoff AND success = FALSE"
        ), {"ip": ip, "cutoff": cutoff}).scalar()
        if ip_count >= 20:
            return False, "Too many failed attempts from this IP. Try again later."
    return True, ""


def _log_attempt(db, user_id: str, success: bool, ip: str = None, method: str = "totp"):
    db.execute(text(
        "INSERT INTO dbp_2fa_attempts "
        "(id, user_id, method, success, ip_address, attempted_at) "
        "VALUES (:id, :uid, :method, :success, :ip, :at)"
    ), {"id": uid(), "uid": user_id, "method": method, "success": success, "ip": ip, "at": now()})


def get_2fa_status(db, user_id: str) -> Dict:
    row = db.execute(text(
        "SELECT is_enabled, method, recovery_codes_used, created_at, last_used_at "
        "FROM dbp_2fa_settings WHERE user_id = :uid"
    ), {"uid": user_id}).fetchone()
    if not row:
        return {"enabled": False, "method": None}
    recovery_codes = db.execute(text(
        "SELECT code_hash FROM dbp_2fa_recovery_codes WHERE user_id = :uid AND used = FALSE"
    ), {"uid": user_id}).fetchall()
    return {
        "enabled": row[0], "method": row[1], "recovery_codes_remaining": len(recovery_codes),
        "created_at": str(row[3]) if row[3] else None, "last_used_at": str(row[4]) if row[4] else None,
    }


def is_2fa_enabled(db, user_id: str) -> bool:
    row = db.execute(text(
        "SELECT 1 FROM dbp_2fa_settings WHERE user_id = :uid AND is_enabled = TRUE"
    ), {"uid": user_id}).fetchone()
    return row is not None


def enable_2fa(db, user_id: str, method: str = "totp") -> Dict:
    existing = db.execute(text("SELECT id FROM dbp_2fa_settings WHERE user_id = :uid"), {"uid": user_id}).fetchone()
    secret = _generate_secret()
    encrypted_secret = _encrypt_secret(secret)
    recovery_codes = _generate_recovery_codes()
    recovery_hashes = [_hash_code(c) for c in recovery_codes]

    if existing:
        db.execute(text(
            "UPDATE dbp_2fa_settings SET is_enabled=TRUE, method=:method, secret=:secret, "
            "recovery_codes_used=0, updated_at=:now WHERE user_id=:uid"
        ), {"method": method, "secret": encrypted_secret, "now": now(), "uid": user_id})
        db.execute(text("DELETE FROM dbp_2fa_recovery_codes WHERE user_id=:uid"), {"uid": user_id})
    else:
        db.execute(text(
            "INSERT INTO dbp_2fa_settings "
            "(id,user_id,is_enabled,method,secret,recovery_codes_used,created_at,updated_at) "
            "VALUES (:id,:uid,TRUE,:method,:secret,0,:now,:now)"
        ), {"id": uid(), "uid": user_id, "method": method, "secret": encrypted_secret, "now": now()})
    for code_hash in recovery_hashes:
        db.execute(text(
            "INSERT INTO dbp_2fa_recovery_codes (id,user_id,code_hash,used,created_at) "
            "VALUES (:id,:uid,:ch,FALSE,:now)"
        ), {"id": uid(), "uid": user_id, "ch": code_hash, "now": now()})
    db.commit()
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(name=user_id, issuer_name="EOS Platform") if pyotp else None
    return {"secret": secret, "recovery_codes": recovery_codes, "provisioning_uri": provisioning_uri, "method": method}


def disable_2fa(db, user_id: str) -> bool:
    db.execute(text("UPDATE dbp_2fa_settings SET is_enabled=FALSE, updated_at=:now WHERE user_id=:uid"), {"now": now(), "uid": user_id})
    db.execute(text("DELETE FROM dbp_2fa_recovery_codes WHERE user_id=:uid"), {"uid": user_id})
    db.commit()
    return True


def verify_totp(db, user_id: str, code: str, ip: str = None) -> Tuple[bool, str]:
    allowed, msg = _check_brute_force(db, user_id, ip)
    if not allowed:
        return False, msg
    row = db.execute(text(
        "SELECT secret FROM dbp_2fa_settings WHERE user_id=:uid AND is_enabled=TRUE"
    ), {"uid": user_id}).fetchone()
    if not row:
        return False, "2FA not enabled"
    secret = _decrypt_secret(row[0])
    valid = pyotp.TOTP(secret).verify(code, valid_window=1) if pyotp else _fallback_totp_verify(secret, code)
    _log_attempt(db, user_id, valid, ip, "totp")
    if valid:
        db.execute(text("UPDATE dbp_2fa_settings SET last_used_at=:now WHERE user_id=:uid"), {"now": now(), "uid": user_id})
    db.commit()
    return valid, "OK" if valid else "Invalid code"


def verify_recovery_code(db, user_id: str, code: str, ip: str = None) -> Tuple[bool, str]:
    allowed, msg = _check_brute_force(db, user_id, ip)
    if not allowed:
        return False, msg
    code_hash = _hash_code(code.upper().strip())
    row = db.execute(text(
        "SELECT id FROM dbp_2fa_recovery_codes WHERE user_id=:uid AND code_hash=:ch AND used=FALSE FOR UPDATE"
    ), {"uid": user_id, "ch": code_hash}).fetchone()
    if not row:
        _log_attempt(db, user_id, False, ip, "recovery")
        db.commit()
        return False, "Invalid recovery code"
    db.execute(text("UPDATE dbp_2fa_recovery_codes SET used=TRUE, used_at=:now WHERE id=:id"), {"now": now(), "id": row[0]})
    db.execute(text(
        "UPDATE dbp_2fa_settings SET recovery_codes_used=recovery_codes_used+1, last_used_at=:now WHERE user_id=:uid"
    ), {"now": now(), "uid": user_id})
    _log_attempt(db, user_id, True, ip, "recovery")
    db.commit()
    return True, "OK"


def _fallback_totp_verify(secret: str, code: str) -> bool:
    counter = int(time.time()) // 30
    for offset in (-1, 0, 1):
        try:
            key = base64.b32decode(secret, casefold=True)
            msg = struct.pack(">Q", counter + offset)
            digest = hmac.new(key, msg, hashlib.sha1).digest()
            offset_val = digest[-1] & 0x0F
            truncated = struct.unpack(">I", digest[offset_val:offset_val+4])[0] & 0x7FFFFFFF
            expected = str(truncated % 1000000).zfill(6)
            if hmac.compare_digest(code, expected):
                return True
        except Exception:
            continue
    return False
