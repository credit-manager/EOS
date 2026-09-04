"""
P34 API Rate Limiting & Quotas Engine
"""
import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session


class APIQuotaEngine:
    def __init__(self, db: Session):
        self.db = db

    # ── API Keys ────────────────────────────────────────────────

    def create_api_key(self, tenant_id, company_id, name, permissions=None,
                       rate_limit_read=200, rate_limit_write=50,
                       expires_at=None) -> dict:
        kid = str(uuid4())
        plain_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        self.db.execute(text(
            "INSERT INTO dbp_api_keys "
            "(id, tenant_id, company_id, key_hash, name, permissions, "
            "rate_limit_read, rate_limit_write, is_active) "
            "VALUES (:id,:tid,:cid,:kh,:name,:perms,:rlr,:rlw,true)"
        ), {
            "id": kid, "tid": tenant_id, "cid": company_id,
            "kh": key_hash, "name": name, "perms": permissions,
            "rlr": rate_limit_read, "rlw": rate_limit_write,
        })
        self.db.flush()
        return {"id": kid, "key": plain_key, "name": name}

    def list_api_keys(self, tenant_id, company_id=None) -> list[dict]:
        conditions = ["tenant_id = :tid"]
        params: dict = {"tid": tenant_id}
        if company_id:
            conditions.append("company_id = :cid")
            params["cid"] = company_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, company_id, name, permissions, "
            f"rate_limit_read, rate_limit_write, is_active, expires_at, "
            f"last_used_at, created_at "
            f"FROM dbp_api_keys WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "company_id": r[2],
                 "name": r[3], "permissions": r[4],
                 "rate_limit_read": r[5], "rate_limit_write": r[6],
                 "is_active": bool(r[7]),
                 "expires_at": r[8].isoformat() if r[8] else None,
                 "last_used_at": r[9].isoformat() if r[9] else None,
                 "created_at": r[10].isoformat() if r[10] else None}
                for r in rows]

    def revoke_api_key(self, key_id) -> dict:
        row = self.db.execute(text(
            "SELECT id FROM dbp_api_keys WHERE id = :kid"
        ), {"kid": key_id}).fetchone()
        if not row:
            return {"success": False, "error": "API key not found"}
        self.db.execute(text(
            "UPDATE dbp_api_keys SET is_active = false WHERE id = :kid"
        ), {"kid": key_id})
        self.db.flush()
        return {"success": True}

    def validate_api_key(self, plain_key) -> dict | None:
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        row = self.db.execute(text(
            "SELECT id, tenant_id, company_id, name, permissions, "
            "rate_limit_read, rate_limit_write, is_active, expires_at "
            "FROM dbp_api_keys WHERE key_hash = :kh"
        ), {"kh": key_hash}).fetchone()
        if not row:
            return None
        if not row[7]:
            return None
        if row[8] and row[8] < datetime.now(timezone.utc):
            return None
        now = datetime.now(timezone.utc)
        self.db.execute(text(
            "UPDATE dbp_api_keys SET last_used_at = :now WHERE id = :kid"
        ), {"now": now, "kid": row[0]})
        self.db.flush()
        return {"id": row[0], "tenant_id": row[1], "company_id": row[2],
                "name": row[3], "permissions": row[4],
                "rate_limit_read": row[5], "rate_limit_write": row[6]}

    # ── Usage Logging ───────────────────────────────────────────

    def log_api_usage(self, tenant_id, api_key_id, endpoint, method,
                      status_code, response_time_ms=None) -> str:
        lid = str(uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_api_usage_logs "
            "(id, tenant_id, api_key_id, endpoint, method, status_code, "
            "response_time_ms) "
            "VALUES (:id,:tid,:akid,:ep,:m,:sc,:rt)"
        ), {
            "id": lid, "tid": tenant_id, "akid": api_key_id,
            "ep": endpoint, "m": method, "sc": status_code,
            "rt": response_time_ms,
        })
        self.db.flush()
        return lid

    def get_usage_stats(self, tenant_id, api_key_id=None,
                        from_date=None, to_date=None) -> dict:
        conditions = ["tenant_id = :tid"]
        params: dict = {"tid": tenant_id}
        if api_key_id:
            conditions.append("api_key_id = :akid")
            params["akid"] = api_key_id
        if from_date:
            conditions.append("created_at >= :fd")
            params["fd"] = from_date
        if to_date:
            conditions.append("created_at <= :td")
            params["td"] = to_date
        where = " AND ".join(conditions)

        total = self.db.execute(text(
            f"SELECT COUNT(*) FROM dbp_api_usage_logs WHERE {where}"
        ), params).scalar()

        by_endpoint_rows = self.db.execute(text(
            f"SELECT endpoint, COUNT(*) as cnt "
            f"FROM dbp_api_usage_logs WHERE {where} "
            f"GROUP BY endpoint ORDER BY cnt DESC"
        ), params).fetchall()

        by_method_rows = self.db.execute(text(
            f"SELECT method, COUNT(*) as cnt "
            f"FROM dbp_api_usage_logs WHERE {where} "
            f"GROUP BY method ORDER BY cnt DESC"
        ), params).fetchall()

        by_status_rows = self.db.execute(text(
            f"SELECT status_code, COUNT(*) as cnt "
            f"FROM dbp_api_usage_logs WHERE {where} "
            f"GROUP BY status_code ORDER BY cnt DESC"
        ), params).fetchall()

        avg_rt = self.db.execute(text(
            f"SELECT AVG(response_time_ms) FROM dbp_api_usage_logs "
            f"WHERE {where} AND response_time_ms IS NOT NULL"
        ), params).scalar()

        return {
            "total_requests": total,
            "by_endpoint": {r[0]: r[1] for r in by_endpoint_rows},
            "by_method": {r[0]: r[1] for r in by_method_rows},
            "by_status_code": {str(r[0]): r[1] for r in by_status_rows},
            "avg_response_time": float(avg_rt) if avg_rt else None,
        }

    # ── Rate Limit Rules ────────────────────────────────────────

    def create_rate_limit_rule(self, tenant_id, company_id,
                               endpoint_pattern, method, rate_limit,
                               window_seconds=60) -> str:
        rid = str(uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_rate_limit_rules "
            "(id, tenant_id, company_id, endpoint_pattern, method, "
            "rate_limit, window_seconds, is_active) "
            "VALUES (:id,:tid,:cid,:ep,:m,:rl,:ws,true)"
        ), {
            "id": rid, "tid": tenant_id, "cid": company_id,
            "ep": endpoint_pattern, "m": method,
            "rl": rate_limit, "ws": window_seconds,
        })
        self.db.flush()
        return rid

    def list_rate_limit_rules(self, tenant_id, company_id=None) -> list[dict]:
        conditions = ["tenant_id = :tid"]
        params: dict = {"tid": tenant_id}
        if company_id:
            conditions.append("company_id = :cid")
            params["cid"] = company_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, company_id, endpoint_pattern, method, "
            f"rate_limit, burst_limit, window_seconds, is_active, created_at "
            f"FROM dbp_rate_limit_rules WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "company_id": r[2],
                 "endpoint_pattern": r[3], "method": r[4],
                 "rate_limit": r[5], "burst_limit": r[6],
                 "window_seconds": r[7], "is_active": bool(r[8]),
                 "created_at": r[9].isoformat() if r[9] else None}
                for r in rows]

    def check_rate_limit(self, tenant_id, endpoint, method) -> dict:
        rows = self.db.execute(text(
            "SELECT id, rate_limit, window_seconds "
            "FROM dbp_rate_limit_rules "
            "WHERE tenant_id = :tid AND is_active = true "
            "AND (endpoint_pattern = :ep OR endpoint_pattern = '*')"
            "AND (method = :m OR method = '*')"
            "ORDER BY created_at DESC LIMIT 1"
        ), {"tid": tenant_id, "ep": endpoint, "m": method}).fetchall()
        if not rows:
            return {"allowed": True, "remaining": -1,
                    "reset_at": None, "rule_id": None}
        rule_id, rate_limit, window_seconds = rows[0][0], rows[0][1], rows[0][2]
        now = datetime.now(timezone.utc)
        cutoff = datetime.fromtimestamp(
            now.timestamp() - window_seconds, tz=timezone.utc)
        count = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_api_usage_logs "
            "WHERE tenant_id = :tid AND endpoint = :ep AND method = :m "
            "AND created_at >= :cutoff"
        ), {"tid": tenant_id, "ep": endpoint, "m": method,
            "cutoff": cutoff}).scalar()
        remaining = max(0, rate_limit - count)
        reset_at = datetime.fromtimestamp(
            now.timestamp() + window_seconds, tz=timezone.utc)
        return {"allowed": count < rate_limit, "remaining": remaining,
                "reset_at": reset_at.isoformat(), "rule_id": rule_id}
