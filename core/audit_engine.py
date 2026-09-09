"""
P31 Audit & Compliance Engine
"""
import uuid
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class AuditComplianceEngine:
    def __init__(self, db: Session):
        self.db = db

    def _parse_json(self, val):
        if val is None:
            return None
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        return val

    def log_audit_event(self, tenant_id, company_id, entity_type, action,
                        actor_id=None, actor_email=None, entity_id=None,
                        old_values=None, new_values=None, ip_address=None,
                        request_id=None, correlation_id=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_audit_trail (id, tenant_id, company_id, entity_type, entity_id, "
            "action, actor_id, actor_email, old_values, new_values, ip_address, request_id, "
            "correlation_id) VALUES (:id,:tid,:cid,:et,:eid,:act,:aid,:ae,:ov,:nv,:ip,:rid,:cid2)"
        ), {"id": eid, "tid": tenant_id, "cid": company_id, "et": entity_type,
            "eid": entity_id, "act": action, "aid": actor_id, "ae": actor_email,
            "ov": json.dumps(old_values) if old_values else None,
            "nv": json.dumps(new_values) if new_values else None,
            "ip": ip_address, "rid": request_id, "cid2": correlation_id})
        self.db.flush()
        return eid

    def get_audit_trail(self, company_id, entity_type=None, entity_id=None,
                        actor_id=None, from_date=None, to_date=None, limit=100, tenant_id=None):
        conditions = ["company_id = :cid"]
        params = {"cid": company_id, "lim": limit}
        if tenant_id:
            conditions.append("tenant_id = :tid"); params["tid"] = tenant_id
        if entity_type:
            conditions.append("entity_type = :et"); params["et"] = entity_type
        if entity_id:
            conditions.append("entity_id = :eid"); params["eid"] = entity_id
        if actor_id:
            conditions.append("actor_id = :aid"); params["aid"] = actor_id
        if from_date:
            conditions.append("created_at >= :fd"); params["fd"] = from_date
        if to_date:
            conditions.append("created_at <= :td"); params["td"] = to_date + "T23:59:59"
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, entity_type, entity_id, action, actor_id, actor_email, "
            f"old_values, new_values, ip_address, request_id, created_at "
            f"FROM dbp_audit_trail WHERE {where} ORDER BY created_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "entity_type": r[1], "entity_id": r[2], "action": r[3],
                 "actor_id": r[4], "actor_email": r[5],
                 "old_values": self._parse_json(r[6]), "new_values": self._parse_json(r[7]),
                 "ip_address": r[8], "request_id": r[9],
                 "created_at": r[10].isoformat() if r[10] else None} for r in rows]

    def get_entity_history(self, company_id, entity_type, entity_id):
        return self.get_audit_trail(company_id, entity_type=entity_type, entity_id=entity_id, limit=500)

    def log_access(self, tenant_id, user_id, user_email, action, resource_type,
                   resource_id=None, access_granted=True, denial_reason=None, ip_address=None):
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_data_access_logs (id, tenant_id, user_id, user_email, action, "
            "resource_type, resource_id, access_granted, denial_reason, ip_address) "
            "VALUES (:id,:tid,:uid,:ue,:act,:rt,:rid,:ag,:dr,:ip)"
        ), {"id": lid, "tid": tenant_id, "uid": user_id, "ue": user_email,
            "act": action, "rt": resource_type, "rid": resource_id,
            "ag": access_granted, "dr": denial_reason, "ip": ip_address})
        self.db.flush()
        return lid

    def get_access_logs(self, company_id=None, tenant_id=None, user_id=None,
                        resource_type=None, from_date=None, to_date=None, limit=100):
        conditions = []
        params = {"lim": limit}
        if company_id:
            conditions.append("l.tenant_id = (SELECT tenant_id FROM dbp_audit_trail LIMIT 1)")
        if tenant_id:
            conditions.append("l.tenant_id = :tid"); params["tid"] = tenant_id
        if user_id:
            conditions.append("l.user_id = :uid"); params["uid"] = user_id
        if resource_type:
            conditions.append("l.resource_type = :rt"); params["rt"] = resource_type
        if from_date:
            conditions.append("l.created_at >= :fd"); params["fd"] = from_date
        if to_date:
            conditions.append("l.created_at <= :td"); params["td"] = to_date + "T23:59:59"
        if not conditions:
            conditions.append("1=1")
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT l.id, l.user_id, l.user_email, l.action, l.resource_type, "
            f"l.resource_id, l.access_granted, l.denial_reason, l.created_at "
            f"FROM dbp_data_access_logs l WHERE {where} ORDER BY l.created_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "user_id": r[1], "user_email": r[2], "action": r[3],
                 "resource_type": r[4], "resource_id": r[5],
                 "access_granted": bool(r[6]), "denial_reason": r[7],
                 "created_at": r[8].isoformat() if r[8] else None} for r in rows]

    def create_compliance_rule(self, tenant_id, company_id, rule_code, name,
                                entity_type, **kw):
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_compliance_rules (id, tenant_id, company_id, rule_code, name, "
            "entity_type, description, category, severity, rule_expression) "
            "VALUES (:id,:tid,:cid,:rc,:name,:et,:desc,:cat,:sev,:re)"
        ), {"id": rid, "tid": tenant_id, "cid": company_id, "rc": rule_code,
            "name": name, "et": entity_type, "desc": kw.get("description"),
            "cat": kw.get("category"), "sev": kw.get("severity", "medium"),
            "re": kw.get("rule_expression")})
        self.db.flush()
        return rid

    def list_compliance_rules(self, company_id, tenant_id=None, category=None):
        conditions = ["company_id = :cid"]
        params = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid"); params["tid"] = tenant_id
        if category:
            conditions.append("category = :cat"); params["cat"] = category
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, rule_code, name, description, category, severity, entity_type, "
            f"is_active, created_at FROM dbp_compliance_rules WHERE {where} ORDER BY rule_code"
        ), params).fetchall()
        return [{"id": r[0], "rule_code": r[1], "name": r[2], "description": r[3],
                 "category": r[4], "severity": r[5], "entity_type": r[6],
                 "is_active": bool(r[7]),
                 "created_at": r[8].isoformat() if r[8] else None} for r in rows]

    def update_compliance_rule(self, rule_id, **kw):
        row = self.db.execute(text("SELECT id FROM dbp_compliance_rules WHERE id = :rid"), {"rid": rule_id}).fetchone()
        if not row:
            return {"success": False, "error": "Rule not found"}
        allowed = {"name", "description", "category", "severity", "is_active", "rule_expression"}
        updates = {k: v for k, v in kw.items() if k in allowed}
        if not updates:
            return {"success": False, "error": "No valid fields"}
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        self.db.execute(text(f"UPDATE dbp_compliance_rules SET {set_clause} WHERE id = :rid"), {"rid": rule_id, **updates})
        self.db.flush()
        return {"success": True}

    def run_compliance_check(self, company_id, tenant_id=None):
        params = {"cid": company_id}
        tid_filter = ""
        if tenant_id:
            tid_filter = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        action_counts = self.db.execute(text(
            f"SELECT action, COUNT(*) FROM dbp_audit_trail WHERE company_id = :cid{tid_filter} "
            f"AND created_at >= NOW() - INTERVAL '30 days' GROUP BY action"
        ), params).fetchall()
        denied = self.db.execute(text(
            f"SELECT COUNT(*) FROM dbp_data_access_logs WHERE access_granted = false "
            f"AND created_at >= NOW() - INTERVAL '30 days'"
        )).scalar() or 0
        active_rules = self.db.execute(text(
            f"SELECT COUNT(*) FROM dbp_compliance_rules WHERE company_id = :cid AND is_active = true"
        ), {"cid": company_id}).scalar() or 0
        return {"audit_events_30d": {r[0]: r[1] for r in action_counts},
                "denied_access_30d": int(denied), "active_rules": int(active_rules)}

    def create_audit_export(self, tenant_id, company_id, export_type, from_date, to_date,
                             entity_types=None, exported_by=None):
        xid = str(uuid.uuid4())
        conditions = ["company_id = :cid", "created_at >= :fd", "created_at <= :td"]
        params = {"cid": company_id, "fd": from_date, "td": to_date + "T23:59:59"}
        if entity_types:
            types_list = [t.strip() for t in entity_types.split(",")]
            conditions.append("entity_type = ANY(:types)")
            params["types"] = types_list
        where = " AND ".join(conditions)
        count = self.db.execute(text(
            f"SELECT COUNT(*) FROM dbp_audit_trail WHERE {where}"
        ), params).scalar() or 0
        self.db.execute(text(
            "INSERT INTO dbp_audit_exports (id, tenant_id, company_id, export_type, "
            "entity_types, from_date, to_date, status, record_count, exported_by, completed_at) "
            "VALUES (:id,:tid,:cid,:xt,:et,:fd,:td,'completed',:rc,:eb,NOW())"
        ), {"id": xid, "tid": tenant_id, "cid": company_id, "xt": export_type,
            "et": entity_types, "fd": from_date, "td": to_date, "rc": count, "eb": exported_by})
        self.db.flush()
        return xid

    def list_audit_exports(self, company_id, tenant_id=None):
        conditions = ["company_id = :cid"]
        params = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid"); params["tid"] = tenant_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, export_type, entity_types, from_date, to_date, status, "
            f"record_count, exported_by, created_at FROM dbp_audit_exports "
            f"WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "export_type": r[1], "entity_types": r[2],
                 "from_date": str(r[3]) if r[3] else None,
                 "to_date": str(r[4]) if r[4] else None, "status": r[5],
                 "record_count": r[6], "exported_by": r[7],
                 "created_at": r[8].isoformat() if r[8] else None} for r in rows]
