"""
P74.9 Two-Factor Authentication (2FA) — Core Module
====================================================
TOTP-based 2FA with recovery codes, brute force protection, and audit.

Flow:
  Login → Username+Password → 2FA Required? → TOTP Code → Access Token
  
Features:
  - Enable/Disable per user or tenant-wide
  - TOTP (RFC 6238) compatible with Google Authenticator, Authy, etc.
  - Recovery codes (one-time use)
  - Brute force protection (max 5 attempts per 15 min)
  - Audit logging for all 2FA events
"""
import sys, os, hashlib, hmac, time, secrets, struct, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

try:
    import pyotp
except ImportError:
    pyotp = None

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Fernet = None

from sqlalchemy import text
from core.industry_security import uid, now

# Get encryption key from environment (must be set for production)
ENCRYPTION_KEY = os.getenv("EOS_2FA_ENCRYPTION_KEY")
if not ENCRYPTION_KEY and CRYPTO_AVAILABLE:
    # Generate a new key if not set (for development only)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"⚠️  WARNING: EOS_2FA_ENCRYPTION_KEY not set. Generated temporary key: {ENCRYPTION_KEY}")
    print("   Set this in your .env file for production!")

def _get_cipher() -> Optional[Fernet]:
    """Get Fernet cipher instance for encrypting/decrypting 2FA secrets."""
    if not CRYPTO_AVAILABLE or not ENCRYPTION_KEY:
        return None
    return Fernet(ENCRYPTION_KEY.encode())

def _encrypt_secret(secret: str) -> str:
    """Encrypt 2FA secret before storing in database."""
    cipher = _get_cipher()
    if cipher:
        return cipher.encrypt(secret.encode()).decode()
    # Fallback to plain text only in dev without crypto (NOT FOR PRODUCTION)
    return secret

def _decrypt_secret(encrypted_secret: str) -> str:
    """Decrypt 2FA secret from database."""
    cipher = _get_cipher()
    if cipher:
        try:
            return cipher.decrypt(encrypted_secret.encode()).decode()
        except Exception:
            # If decryption fails, return as-is (might be unencrypted old data)
            return encrypted_secret
    # Fallback to plain text only in dev without crypto
    return encrypted_secret


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
    ), {
        "id": uid(), "uid": user_id, "method": method,
        "success": success, "ip": ip, "at": now()
    })


def get_2fa_status(db, user_id: str) -> Dict:
    row = db.execute(text(
        "SELECT is_enabled, method, recovery_codes_used, created_at, last_used_at "
        "FROM dbp_2fa_settings WHERE user_id = :uid"
    ), {"uid": user_id}).fetchone()
    
    if not row:
        return {"enabled": False, "method": None}
    
    recovery_codes = db.execute(text(
        "SELECT code_hash FROM dbp_2fa_recovery_codes "
        "WHERE user_id = :uid AND used = FALSE"
    ), {"uid": user_id}).fetchall()
    
    return {
        "enabled": row[0],
        "method": row[1],
        "recovery_codes_remaining": len(recovery_codes),
        "created_at": str(row[3]) if row[3] else None,
        "last_used_at": str(row[4]) if row[4] else None,
    }


def enable_2fa(db, user_id: str, method: str = "totp") -> Dict:
    existing = db.execute(text(
        "SELECT id FROM dbp_2fa_settings WHERE user_id = :uid"
    ), {"uid": user_id}).fetchone()
    
    secret = _generate_secret()
    encrypted_secret = _encrypt_secret(secret)  # ENCRYPT before storing
    recovery_codes = _generate_recovery_codes()
    recovery_hashes = [_hash_code(c) for c in recovery_codes]
    
    if existing:
        db.execute(text(
            "UPDATE dbp_2fa_settings "
            "SET is_enabled = TRUE, method = :method, secret = :secret, "
            "recovery_codes_used = 0, updated_at = :now "
            "WHERE user_id = :uid"
        ), {"method": method, "secret": encrypted_secret, "now": now(), "uid": user_id})
        
        db.execute(text(
            "DELETE FROM dbp_2fa_recovery_codes WHERE user_id = :uid"
        ), {"uid": user_id})
    else:
        db.execute(text(
            "INSERT INTO dbp_2fa_settings "
            "(id, user_id, is_enabled, method, secret, recovery_codes_used, created_at, updated_at) "
            "VALUES (:id, :uid, TRUE, :method, :secret, 0, :now, :now)"
        ), {"id": uid(), "uid": user_id, "method": method, "secret": encrypted_secret, "now": now()})
    
    for code_hash in recovery_hashes:
        db.execute(text(
            "INSERT INTO dbp_2fa_recovery_codes "
            "(id, user_id, code_hash, used, created_at) "
            "VALUES (:id, :uid, :ch, FALSE, :now)"
        ), {"id": uid(), "uid": user_id, "ch": code_hash, "now": now()})
    
    db.commit()
    
    if pyotp:
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name="EOS Platform"
        )
    else:
        provisioning_uri = None
    
    return {
        "secret": secret,  # Return plain secret to user (for QR code generation)
        "recovery_codes": recovery_codes,
        "provisioning_uri": provisioning_uri,
        "method": method,
    }


def disable_2fa(db, user_id: str) -> bool:
    db.execute(text(
        "UPDATE dbp_2fa_settings SET is_enabled = FALSE, updated_at = :now "
        "WHERE user_id = :uid"
    ), {"now": now(), "uid": user_id})
    
    db.execute(text(
        "DELETE FROM dbp_2fa_recovery_codes WHERE user_id = :uid"
    ), {"uid": user_id})
    
    db.commit()
    return True


def verify_totp(db, user_id: str, code: str, ip: str = None) -> Tuple[bool, str]:
    allowed, msg = _check_brute_force(db, user_id, ip)
    if not allowed:
        return False, msg
    
    row = db.execute(text(
        "SELECT secret FROM dbp_2fa_settings "
        "WHERE user_id = :uid AND is_enabled = TRUE"
    ), {"uid": user_id}).fetchone()
    
    if not row:
        return False, "2FA not enabled"
    
    encrypted_secret = row[0]
    secret = _decrypt_secret(encrypted_secret)  # DECRYPT before using
    
    if pyotp:
        totp = pyotp.TOTP(secret)
        valid = totp.verify(code, valid_window=1)
    else:
        valid = _fallback_totp_verify(secret, code)
    
    _log_attempt(db, user_id, valid, ip, "totp")
    
    if valid:
        db.execute(text(
            "UPDATE dbp_2fa_settings SET last_used_at = :now WHERE user_id = :uid"
        ), {"now": now(), "uid": user_id})
    
    db.commit()
    return valid, "Invalid code" if not valid else "OK"


def verify_recovery_code(db, user_id: str, code: str, ip: str = None) -> Tuple[bool, str]:
    allowed, msg = _check_brute_force(db, user_id, ip)
    if not allowed:
        return False, msg
    
    code_hash = _hash_code(code.upper().strip())
    
    row = db.execute(text(
        "SELECT id FROM dbp_2fa_recovery_codes "
        "WHERE user_id = :uid AND code_hash = :ch AND used = FALSE"
    ), {"uid": user_id, "ch": code_hash}).fetchone()
    
    if not row:
        _log_attempt(db, user_id, False, ip, "recovery")
        return False, "Invalid recovery code"
    
    db.execute(text(
        "UPDATE dbp_2fa_recovery_codes SET used = TRUE, used_at = :now WHERE id = :id"
    ), {"now": now(), "id": row[0]})
    
    db.execute(text(
        "UPDATE dbp_2fa_settings SET recovery_codes_used = recovery_codes_used + 1, "
        "last_used_at = :now WHERE user_id = :uid"
    ), {"now": now(), "uid": user_id})
    
    _log_attempt(db, user_id, True, ip, "recovery")
    db.commit()
    
    return True, "OK"


def _fallback_totp_verify(secret: str, code: str) -> bool:
    counter = int(time.time()) // 30
    for offset in [-1, 0, 1]:
        try:
            key = base64.b32decode(secret, casefold=True)
            msg = struct.pack(">Q", counter + offset)
            h = hmac.new(key, msg, hashlib.sha1).digest()
            offset_val = h[-1] & 0x0F
            truncated = struct.unpack(">I", h[offset_val:offset_val+4])[0]
            truncated &= 0x7FFFFFFF
            expected = str(truncated % 1000000).zfill(6)
            if hmac.compare_digest(code, expected):
                return True
        except Exception:
            continue
    return False
