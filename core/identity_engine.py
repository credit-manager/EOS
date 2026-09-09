"""
P47 Identity Federation & SSO Engine
"""
import uuid, hashlib, secrets
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class IdentityEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------- SSO providers
    def create_provider(self, tenant_id, provider_name, provider_type,
                        client_id, client_secret=None, metadata_url=None):
        pid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_sso_providers "
            "(id, tenant_id, provider_name, provider_type, client_id, client_secret_enc, metadata_url, created_at) "
            "VALUES (:id,:tid,:pn,:pt,:ci,:cs,:mu,NOW())"
        ), {"id": pid, "tid": tenant_id, "pn": provider_name,
            "pt": provider_type, "ci": client_id,
            "cs": client_secret, "mu": metadata_url})
        return pid

    def list_providers(self, tenant_id, is_active=None):
        q = "SELECT id, provider_name, provider_type, client_id, is_active, created_at FROM dbp_sso_providers WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if is_active is not None:
            q += " AND is_active=:ia"
            params["ia"] = is_active
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "provider_name": r[1], "provider_type": r[2],
                 "client_id": r[3], "is_active": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    def update_provider(self, tenant_id, provider_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": provider_id, "tid": tenant_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_sso_providers SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": provider_id, "updated": True}

    # -------------------------------------------------- SSO sessions
    def create_session(self, tenant_id, user_id, provider_id, sso_session_id,
                       ip_address=None, user_agent=None, expires_at=None):
        sid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_sso_sessions "
            "(id, tenant_id, user_id, provider_id, sso_session_id, ip_address, user_agent, expires_at, created_at) "
            "VALUES (:id,:tid,:ui,:pi,:si,:ip,:ua,:ea,NOW())"
        ), {"id": sid, "tid": tenant_id, "ui": user_id, "pi": provider_id,
            "si": sso_session_id, "ip": ip_address, "ua": user_agent,
            "ea": expires_at})
        return sid

    def list_sessions(self, tenant_id, user_id=None):
        q = "SELECT id, user_id, provider_id, sso_session_id, ip_address, created_at FROM dbp_sso_sessions WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if user_id:
            q += " AND user_id=:ui"
            params["ui"] = user_id
        q += " ORDER BY created_at DESC LIMIT 50"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "user_id": r[1], "provider_id": r[2],
                 "sso_session_id": r[3], "ip_address": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    # -------------------------------------------------- MFA
    def setup_mfa(self, tenant_id, user_id, mfa_type):
        mid = str(uuid.uuid4())
        secret = secrets.token_hex(20)
        self.db.execute(text(
            "INSERT INTO dbp_mfa_configs "
            "(id, tenant_id, user_id, mfa_type, secret_enc, is_enabled, created_at) "
            "VALUES (:id,:tid,:ui,:mt,:se,false,NOW())"
        ), {"id": mid, "tid": tenant_id, "ui": user_id,
            "mt": mfa_type, "se": secret})
        return {"id": mid, "secret": secret}

    def enable_mfa(self, tenant_id, mfa_id):
        self.db.execute(text(
            "UPDATE dbp_mfa_configs SET is_enabled=true WHERE id=:id AND tenant_id=:tid"
        ), {"id": mfa_id, "tid": tenant_id})
        return {"id": mfa_id, "enabled": True}

    def list_mfa(self, tenant_id, user_id=None):
        q = "SELECT id, user_id, mfa_type, is_enabled, last_used_at, created_at FROM dbp_mfa_configs WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if user_id:
            q += " AND user_id=:ui"
            params["ui"] = user_id
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "user_id": r[1], "mfa_type": r[2],
                 "is_enabled": r[3],
                 "last_used_at": str(r[4]) if r[4] else None,
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    def disable_mfa(self, tenant_id, mfa_id):
        self.db.execute(text(
            "UPDATE dbp_mfa_configs SET is_enabled=false WHERE id=:id AND tenant_id=:tid"
        ), {"id": mfa_id, "tid": tenant_id})
        return {"id": mfa_id, "disabled": True}

    # ------------------------------------------------ role mappings
    def create_role_mapping(self, tenant_id, provider_id, external_role,
                            internal_role):
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_role_mappings "
            "(id, tenant_id, provider_id, external_role, internal_role, created_at) "
            "VALUES (:id,:tid,:pi,:er,:ir,NOW())"
        ), {"id": rid, "tid": tenant_id, "pi": provider_id,
            "er": external_role, "ir": internal_role})
        return rid

    def list_role_mappings(self, tenant_id, provider_id=None):
        q = "SELECT id, provider_id, external_role, internal_role, created_at FROM dbp_role_mappings WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if provider_id:
            q += " AND provider_id=:pi"
            params["pi"] = provider_id
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "provider_id": r[1], "external_role": r[2],
                 "internal_role": r[3],
                 "created_at": str(r[4]) if r[4] else None} for r in rows]

    def delete_role_mapping(self, tenant_id, mapping_id):
        r = self.db.execute(text(
            "DELETE FROM dbp_role_mappings WHERE id=:id AND tenant_id=:tid"
        ), {"id": mapping_id, "tid": tenant_id})
        return r.rowcount > 0

    # ----------------------------------------------------- API keys
    def create_api_key(self, tenant_id, key_name, permissions=None, expires_at=None):
        kid = str(uuid.uuid4())
        raw_key = f"dbp_{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        self.db.execute(text(
            "INSERT INTO dbp_api_keys "
            "(id, tenant_id, key_name, key_hash, permissions, expires_at, created_at) "
            "VALUES (:id,:tid,:kn,:kh,:pe,:ea,NOW())"
        ), {"id": kid, "tid": tenant_id, "kn": key_name,
            "kh": key_hash,
            "pe": __import__('json').dumps(permissions) if permissions else None,
            "ea": expires_at})
        return {"id": kid, "key": raw_key, "key_hash": key_hash}

    def list_api_keys(self, tenant_id, is_active=None):
        q = "SELECT id, key_name, key_hash, permissions, is_active, last_used_at, expires_at, created_at FROM dbp_api_keys WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if is_active is not None:
            q += " AND is_active=:ia"
            params["ia"] = is_active
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "key_name": r[1], "key_hash": r[2][:16] + "...",
                 "permissions": r[3], "is_active": r[4],
                 "last_used_at": str(r[5]) if r[5] else None,
                 "expires_at": str(r[6]) if r[6] else None,
                 "created_at": str(r[7]) if r[7] else None} for r in rows]

    def revoke_api_key(self, tenant_id, key_id):
        self.db.execute(text(
            "UPDATE dbp_api_keys SET is_active=false WHERE id=:id AND tenant_id=:tid"
        ), {"id": key_id, "tid": tenant_id})
        return {"id": key_id, "revoked": True}
