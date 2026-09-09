"""
P61 User Engine — Production user management.
Handles registration, login, email verification, password reset.
Password hashing via bcrypt. Tokens stored as SHA-256 hashes.
"""
import uuid, secrets, hashlib, re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 30
TOKEN_EXPIRE_HOURS = 24
RESET_TOKEN_EXPIRE_HOURS = 2


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _validate_password(password: str) -> Optional[str]:
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Za-z]", password):
        return "Password must contain at least one letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    return None


class UserEngine:
    def __init__(self, db: Session):
        self.db = db

    def _revoke_refresh_sessions(self, user_id: str) -> None:
        """Invalidate all refresh sessions after credential/account changes."""
        self.db.execute(text(
            "UPDATE dbp_refresh_tokens SET revoked_at = NOW() "
            "WHERE user_id = :user_id AND revoked_at IS NULL"
        ), {"user_id": user_id})

    def register(self, tenant_id: str, email: str, password: str,
                 first_name: str, last_name: str,
                 first_name_ar: Optional[str] = None,
                 last_name_ar: Optional[str] = None,
                 phone: Optional[str] = None,
                 role: str = "admin") -> Dict[str, Any]:
        err = _validate_password(password)
        if err:
            return {"success": False, "error": err}
        existing = self.db.execute(text("SELECT id FROM dbp_users WHERE email = :email"), {"email": email.lower()}).fetchone()
        if existing:
            return {"success": False, "error": "Email already registered"}
        uid = str(uuid.uuid4())
        pw_hash = pwd_context.hash(password)
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
        self.db.execute(text(
            "INSERT INTO dbp_users (id, tenant_id, email, password_hash, first_name, last_name, first_name_ar, last_name_ar, phone, role, is_active, email_verified, verification_token_hash, verification_expires_at) "
            "VALUES (:id, :tid, :email, :pw, :fn, :ln, :fnar, :lnar, :phone, :role, true, false, :vth, :vea)"
        ), {"id": uid, "tid": tenant_id, "email": email.lower(), "pw": pw_hash, "fn": first_name, "ln": last_name,
            "fnar": first_name_ar, "lnar": last_name_ar, "phone": phone, "role": role, "vth": token_hash, "vea": expires})
        self.db.flush()
        return {"success": True, "user_id": uid, "email": email.lower(), "verification_token": token, "requires_verification": True}

    def verify_email(self, token: str) -> Dict[str, Any]:
        token_hash = _hash_token(token)
        row = self.db.execute(text(
            "SELECT id, verification_expires_at FROM dbp_users WHERE verification_token_hash = :th AND email_verified = false"
        ), {"th": token_hash}).fetchone()
        if not row:
            return {"success": False, "error": "Invalid or expired verification token"}
        expires = row[1]
        if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return {"success": False, "error": "Verification token expired"}
        self.db.execute(text(
            "UPDATE dbp_users SET email_verified = true, verification_token_hash = NULL, verification_expires_at = NULL, updated_at = NOW() WHERE id = :id"
        ), {"id": row[0]})
        self.db.flush()
        return {"success": True, "user_id": row[0]}

    def login(self, email: str, password: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        row = self.db.execute(text(
            "SELECT id, tenant_id, email, password_hash, first_name, last_name, role, is_active, email_verified, failed_login_attempts, locked_until "
            "FROM dbp_users WHERE email = :email"
        ), {"email": email.lower()}).fetchone()
        if not row:
            return {"success": False, "error": "Invalid email or password"}
        user_id, tenant_id = row[0], row[1]
        is_active, email_verified = row[7], row[8]
        failed_attempts = row[9] or 0
        locked_until = row[10]
        if not is_active:
            return {"success": False, "error": "Account is deactivated"}
        if locked_until:
            if locked_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                return {"success": False, "error": "Account is locked. Try again later."}
            self.db.execute(text("UPDATE dbp_users SET failed_login_attempts = 0, locked_until = NULL WHERE id = :id"), {"id": user_id})
        if not pwd_context.verify(password, row[3]):
            new_attempts = failed_attempts + 1
            lock_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES) if new_attempts >= MAX_FAILED_LOGINS else None
            self.db.execute(text("UPDATE dbp_users SET failed_login_attempts = :a, locked_until = :lu WHERE id = :id"), {"a": new_attempts, "lu": lock_until, "id": user_id})
            self.db.flush()
            return {"success": False, "error": "Invalid email or password"}
        if not email_verified:
            return {"success": False, "error": "Email not verified. Check your inbox.", "requires_verification": True}
        self.db.execute(text("UPDATE dbp_users SET failed_login_attempts = 0, locked_until = NULL, last_login_at = NOW() WHERE id = :id"), {"id": user_id})
        self.db.flush()
        return {"success": True, "user_id": user_id, "tenant_id": tenant_id, "email": row[2], "first_name": row[4], "last_name": row[5], "role": row[6]}

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, tenant_id, email, first_name, last_name, first_name_ar, last_name_ar, phone, role, is_active, email_verified, last_login_at, created_at "
            "FROM dbp_users WHERE id = :id"
        ), {"id": user_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "tenant_id": row[1], "email": row[2], "first_name": row[3], "last_name": row[4], "first_name_ar": row[5],
                "last_name_ar": row[6], "phone": row[7], "role": row[8], "is_active": row[9], "email_verified": row[10],
                "last_login_at": str(row[11]) if row[11] else None, "created_at": str(row[12]) if row[12] else None}

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, tenant_id, email, password_hash, first_name, last_name, role, is_active, email_verified FROM dbp_users WHERE email = :email"
        ), {"email": email.lower()}).fetchone()
        if not row:
            return None
        return {"id": row[0], "tenant_id": row[1], "email": row[2], "password_hash": row[3], "first_name": row[4], "last_name": row[5],
                "role": row[6], "is_active": row[7], "email_verified": row[8]}

    def request_password_reset(self, email: str) -> Dict[str, Any]:
        row = self.db.execute(text("SELECT id FROM dbp_users WHERE email = :email AND is_active = true"), {"email": email.lower()}).fetchone()
        if not row:
            return {"success": True, "message": "If email exists, reset link sent"}
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
        self.db.execute(text("UPDATE dbp_users SET reset_token_hash = :th, reset_expires_at = :exp, updated_at = NOW() WHERE id = :id"),
                        {"th": token_hash, "exp": expires, "id": row[0]})
        self.db.flush()
        return {"success": True, "reset_token": token, "message": "If email exists, reset link sent"}

    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        err = _validate_password(new_password)
        if err:
            return {"success": False, "error": err}
        token_hash = _hash_token(token)
        row = self.db.execute(text("SELECT id, reset_expires_at FROM dbp_users WHERE reset_token_hash = :th AND is_active = true"), {"th": token_hash}).fetchone()
        if not row:
            return {"success": False, "error": "Invalid or expired reset token"}
        if row[1] and row[1].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return {"success": False, "error": "Reset token expired"}
        pw_hash = pwd_context.hash(new_password)
        self.db.execute(text(
            "UPDATE dbp_users SET password_hash = :pw, reset_token_hash = NULL, reset_expires_at = NULL, failed_login_attempts = 0, locked_until = NULL, updated_at = NOW() WHERE id = :id"
        ), {"pw": pw_hash, "id": row[0]})
        self._revoke_refresh_sessions(row[0])
        self.db.flush()
        return {"success": True, "message": "Password reset successful"}

    def change_password(self, user_id: str, current_password: str, new_password: str) -> Dict[str, Any]:
        row = self.db.execute(text("SELECT password_hash FROM dbp_users WHERE id = :id AND is_active = true"), {"id": user_id}).fetchone()
        if not row:
            return {"success": False, "error": "User not found"}
        if not pwd_context.verify(current_password, row[0]):
            return {"success": False, "error": "Current password is incorrect"}
        err = _validate_password(new_password)
        if err:
            return {"success": False, "error": err}
        pw_hash = pwd_context.hash(new_password)
        self.db.execute(text("UPDATE dbp_users SET password_hash = :pw, updated_at = NOW() WHERE id = :id"), {"pw": pw_hash, "id": user_id})
        self._revoke_refresh_sessions(user_id)
        self.db.flush()
        return {"success": True, "message": "Password changed"}

    def list_users(self, tenant_id: str, limit: int = 50) -> list:
        rows = self.db.execute(text(
            "SELECT id, email, first_name, last_name, role, is_active, email_verified, last_login_at, created_at FROM dbp_users WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT :lim"
        ), {"tid": tenant_id, "lim": limit}).fetchall()
        return [{"id": r[0], "email": r[1], "first_name": r[2], "last_name": r[3], "role": r[4], "is_active": r[5],
                 "email_verified": r[6], "last_login_at": str(r[7]) if r[7] else None, "created_at": str(r[8]) if r[8] else None} for r in rows]

    def get_user_by_id_tenant(self, user_id: str, tenant_id: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, email, first_name, last_name, first_name_ar, last_name_ar, phone, role, is_active, email_verified, last_login_at, created_at "
            "FROM dbp_users WHERE id = :id AND tenant_id = :tid"
        ), {"id": user_id, "tid": tenant_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "first_name": row[2], "last_name": row[3], "first_name_ar": row[4], "last_name_ar": row[5],
                "phone": row[6], "role": row[7], "is_active": row[8], "email_verified": row[9],
                "last_login_at": str(row[10]) if row[10] else None, "created_at": str(row[11]) if row[11] else None}

    def update_user(self, user_id: str, tenant_id: str, data: dict) -> Dict[str, Any]:
        allowed = {"first_name", "last_name", "first_name_ar", "last_name_ar", "phone"}
        fields = []
        params = {"id": user_id, "tid": tenant_id}
        for key in allowed:
            if key in data:
                fields.append(f"{key} = :{key}")
                params[key] = data[key]
        if not fields:
            return {"success": False, "error": "No valid fields to update"}
        fields.append("updated_at = NOW()")
        result = self.db.execute(text(f"UPDATE dbp_users SET {', '.join(fields)} WHERE id = :id AND tenant_id = :tid"), params)
        if result.rowcount == 0:
            return {"success": False, "error": "User not found"}
        self.db.flush()
        return {"success": True, "message": "User updated"}

    def change_role(self, user_id: str, tenant_id: str, new_role: str) -> Dict[str, Any]:
        result = self.db.execute(text("UPDATE dbp_users SET role = :role, updated_at = NOW() WHERE id = :id AND tenant_id = :tid"),
                                 {"role": new_role, "id": user_id, "tid": tenant_id})
        if result.rowcount == 0:
            return {"success": False, "error": "User not found"}
        self._revoke_refresh_sessions(user_id)
        self.db.flush()
        return {"success": True, "message": "Role changed"}

    def deactivate_user(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        result = self.db.execute(text("UPDATE dbp_users SET is_active = false, updated_at = NOW() WHERE id = :id AND tenant_id = :tid"),
                                 {"id": user_id, "tid": tenant_id})
        if result.rowcount == 0:
            return {"success": False, "error": "User not found"}
        self._revoke_refresh_sessions(user_id)
        self.db.flush()
        return {"success": True, "message": "User deactivated"}

    def invite_user(self, tenant_id: str, email: str, first_name: str, last_name: str, role: str = "user") -> Dict[str, Any]:
        existing = self.db.execute(text("SELECT id FROM dbp_users WHERE email = :email"), {"email": email.lower()}).fetchone()
        if existing:
            return {"success": False, "error": "Email already registered"}
        uid = str(uuid.uuid4())
        temp_password = secrets.token_urlsafe(16)
        pw_hash = pwd_context.hash(temp_password)
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
        self.db.execute(text(
            "INSERT INTO dbp_users (id, tenant_id, email, password_hash, first_name, last_name, role, is_active, email_verified, verification_token_hash, verification_expires_at) "
            "VALUES (:id, :tid, :email, :pw, :fn, :ln, :role, true, false, :th, :exp)"
        ), {"id": uid, "tid": tenant_id, "email": email.lower(), "pw": pw_hash, "fn": first_name, "ln": last_name,
            "role": role, "th": _hash_token(token), "exp": expires})
        self.db.flush()
        return {"success": True, "user_id": uid, "verification_token": token}
