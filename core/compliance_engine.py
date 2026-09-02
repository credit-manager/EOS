"""
P46 Compliance Automation & Policy Engine
"""
import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ComplianceEngine:
    def __init__(self, db: Session):
        self.db = db

    def create_policy(self, tenant_id, policy_name, policy_type, rules_config,
                      description=None, severity="medium"):
        pid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_compliance_policies "
            "(id, tenant_id, policy_name, policy_type, description, rules_config, severity, created_at) "
            "VALUES (:id,:tid,:pn,:pt,:de,:rc,:sv,NOW())"
        ), {"id": pid, "tid": tenant_id, "pn": policy_name, "pt": policy_type,
            "de": description, "rc": json.dumps(rules_config), "sv": severity})
        return pid

    def list_policies(self, tenant_id, is_active=None):
        q = "SELECT id, policy_name, policy_type, severity, is_active, created_at FROM dbp_compliance_policies WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if is_active is not None:
            q += " AND is_active=:ia"
            params["ia"] = is_active
        q += " ORDER BY created_at DESC"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "policy_name": r[1], "policy_type": r[2],
                 "severity": r[3], "is_active": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    def get_policy(self, tenant_id, policy_id):
        r = self.db.execute(text(
            "SELECT id, policy_name, policy_type, description, rules_config, severity, is_active, created_at "
            "FROM dbp_compliance_policies WHERE id=:id AND tenant_id=:tid"
        ), {"id": policy_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "policy_name": r[1], "policy_type": r[2],
                "description": r[3], "rules_config": r[4],
                "severity": r[5], "is_active": r[6],
                "created_at": str(r[7]) if r[7] else None}

    def update_policy(self, tenant_id, policy_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": policy_id, "tid": tenant_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_compliance_policies SET {', '.join(sets)}, updated_at=NOW() WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": policy_id, "updated": True}

    def delete_policy(self, tenant_id, policy_id):
        r = self.db.execute(text(
            "DELETE FROM dbp_compliance_policies WHERE id=:id AND tenant_id=:tid"
        ), {"id": policy_id, "tid": tenant_id})
        return r.rowcount > 0

    # -------------------------------------------------- checks
    def create_check(self, tenant_id, policy_id, check_name, check_type,
                     target_entity=None):
        cid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_compliance_checks "
            "(id, tenant_id, policy_id, check_name, check_type, target_entity, status, created_at) "
            "VALUES (:id,:tid,:pi,:cn,:ct,:te,'pending',NOW())"
        ), {"id": cid, "tid": tenant_id, "pi": policy_id, "cn": check_name,
            "ct": check_type, "te": target_entity})
        return cid

    def run_check(self, check_id, status, result_detail=None):
        self.db.execute(text(
            "UPDATE dbp_compliance_checks SET status=:st, result_detail=:rd, ran_at=NOW() WHERE id=:id"
        ), {"st": status, "rd": json.dumps(result_detail) if result_detail else None, "id": check_id})
        return {"id": check_id, "status": status}

    def list_checks(self, tenant_id, policy_id=None, status=None, limit=50):
        q = "SELECT id, policy_id, check_name, check_type, target_entity, status, result_detail, ran_at FROM dbp_compliance_checks WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if policy_id:
            q += " AND policy_id=:pi"
            params["pi"] = policy_id
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "policy_id": r[1], "check_name": r[2],
                 "check_type": r[3], "target_entity": r[4],
                 "status": r[5], "result_detail": r[6],
                 "ran_at": str(r[7]) if r[7] else None} for r in rows]

    # ------------------------------------------------ violations
    def create_violation(self, tenant_id, policy_id, violation_type, severity,
                         entity_type=None, entity_id=None, description=None,
                         check_id=None, assigned_to=None):
        vid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_compliance_violations "
            "(id, tenant_id, policy_id, check_id, entity_type, entity_id, "
            "violation_type, severity, description, assigned_to, created_at) "
            "VALUES (:id,:tid,:pi,:ci,:et,:ei,:vt,:sv,:de,:at,NOW())"
        ), {"id": vid, "tid": tenant_id, "pi": policy_id, "ci": check_id,
            "et": entity_type, "ei": entity_id, "vt": violation_type,
            "sv": severity, "de": description, "at": assigned_to})
        return vid

    def list_violations(self, tenant_id, status=None, severity=None, limit=50):
        q = "SELECT id, policy_id, entity_type, entity_id, violation_type, severity, status, assigned_to, created_at FROM dbp_compliance_violations WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if status:
            q += " AND status=:st"
            params["st"] = status
        if severity:
            q += " AND severity=:sv"
            params["sv"] = severity
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "policy_id": r[1], "entity_type": r[2],
                 "entity_id": r[3], "violation_type": r[4],
                 "severity": r[5], "status": r[6],
                 "assigned_to": r[7],
                 "created_at": str(r[8]) if r[8] else None} for r in rows]

    def resolve_violation(self, tenant_id, violation_id):
        self.db.execute(text(
            "UPDATE dbp_compliance_violations SET status='resolved', resolved_at=NOW() "
            "WHERE id=:id AND tenant_id=:tid"
        ), {"id": violation_id, "tid": tenant_id})
        return {"id": violation_id, "status": "resolved"}

    # ------------------------------------------------ audit log
    def log_action(self, tenant_id, action, entity_type=None, entity_id=None,
                   actor_id=None, details=None):
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_compliance_audit_log "
            "(id, tenant_id, action, entity_type, entity_id, actor_id, details, created_at) "
            "VALUES (:id,:tid,:ac,:et,:ei,:ai,:de,NOW())"
        ), {"id": lid, "tid": tenant_id, "ac": action,
            "et": entity_type, "ei": entity_id, "ai": actor_id,
            "de": json.dumps(details) if details else None})
        return lid

    def list_audit_log(self, tenant_id, action=None, limit=50):
        q = "SELECT id, action, entity_type, entity_id, actor_id, details, created_at FROM dbp_compliance_audit_log WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if action:
            q += " AND action=:ac"
            params["ac"] = action
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "action": r[1], "entity_type": r[2],
                 "entity_id": r[3], "actor_id": r[4],
                 "details": r[5],
                 "created_at": str(r[6]) if r[6] else None} for r in rows]

    # ------------------------------------------------ frameworks
    def create_framework(self, tenant_id, framework_name, framework_type,
                         requirements=None, version=None):
        fid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_compliance_frameworks "
            "(id, tenant_id, framework_name, framework_type, version, requirements, status, created_at) "
            "VALUES (:id,:tid,:fn,:ft,:ve,:rq,'active',NOW())"
        ), {"id": fid, "tid": tenant_id, "fn": framework_name,
            "ft": framework_type, "ve": version,
            "rq": json.dumps(requirements) if requirements else None})
        return fid

    def list_frameworks(self, tenant_id, framework_type=None):
        q = "SELECT id, framework_name, framework_type, version, status, created_at FROM dbp_compliance_frameworks WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if framework_type:
            q += " AND framework_type=:ft"
            params["ft"] = framework_type
        q += " ORDER BY created_at"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "framework_name": r[1], "framework_type": r[2],
                 "version": r[3], "status": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]
