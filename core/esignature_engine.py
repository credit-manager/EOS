"""
P33 E-Signature & Enhanced Approval Workflows Engine
"""
import uuid
from datetime import datetime, date, timezone
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class ESignatureEngine:
    def __init__(self, db: Session):
        self.db = db

    # ── Signature Requests ──────────────────────────────────────

    def create_signature_request(self, tenant_id, company_id, title, signers,
                                 requested_by, **kw):
        rid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.db.execute(text(
            "INSERT INTO dbp_signature_requests "
            "(id, tenant_id, company_id, reference_type, reference_id, title, "
            "description, status, requested_by, created_at) "
            "VALUES (:id,:tid,:cid,:rt,:ri,:title,:desc,'pending',:rb,:cat)"
        ), {
            "id": rid, "tid": tenant_id, "cid": company_id,
            "rt": kw.get("reference_type"), "ri": kw.get("reference_id"),
            "title": title, "desc": kw.get("description"),
            "rb": requested_by, "cat": now,
        })
        for s in signers:
            sid = str(uuid.uuid4())
            self.db.execute(text(
                "INSERT INTO dbp_signature_signers "
                "(id, tenant_id, request_id, signer_id, signer_email, signer_name, "
                "order_number, status) "
                "VALUES (:id,:tid,:rid,:sid,:se,:sn,:on,'pending')"
            ), {
                "id": sid, "tid": tenant_id, "rid": rid,
                "sid": s["signer_id"], "se": s.get("signer_email"),
                "sn": s.get("signer_name"), "on": s.get("order_number", 1),
            })
        self.db.flush()
        return rid

    def get_signature_request(self, request_id) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, tenant_id, company_id, reference_type, reference_id, "
            "title, description, status, requested_by, created_at, completed_at "
            "FROM dbp_signature_requests WHERE id = :rid"
        ), {"rid": request_id}).fetchone()
        if not row:
            return None
        signers = self._get_signers(request_id)
        return {
            "id": row[0], "tenant_id": row[1], "company_id": row[2],
            "reference_type": row[3], "reference_id": row[4],
            "title": row[5], "description": row[6], "status": row[7],
            "requested_by": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "completed_at": row[10].isoformat() if row[10] else None,
            "signers": signers,
        }

    def _get_signers(self, request_id) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, tenant_id, request_id, signer_id, signer_email, "
            "signer_name, order_number, status, signature_data, signed_at, "
            "rejection_reason "
            "FROM dbp_signature_signers WHERE request_id = :rid "
            "ORDER BY order_number"
        ), {"rid": request_id}).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "request_id": r[2],
                "signer_id": r[3], "signer_email": r[4], "signer_name": r[5],
                "order_number": r[6], "status": r[7],
                "signature_data": r[8],
                "signed_at": r[9].isoformat() if r[9] else None,
                "rejection_reason": r[10]} for r in rows]

    def sign(self, request_id, signer_id, signature_data) -> Dict:
        row = self.db.execute(text(
            "SELECT id, status FROM dbp_signature_signers "
            "WHERE request_id = :rid AND signer_id = :sid"
        ), {"rid": request_id, "sid": signer_id}).fetchone()
        if not row:
            return {"success": False, "error": "Signer not found"}
        if row[1] != "pending":
            return {"success": False, "error": f"Signer status is {row[1]}, cannot sign"}
        now = datetime.now(timezone.utc)
        self.db.execute(text(
            "UPDATE dbp_signature_signers "
            "SET status = 'signed', signature_data = :sd, signed_at = :now "
            "WHERE id = :id"
        ), {"sd": signature_data, "now": now, "id": row[0]})
        pending = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_signature_signers "
            "WHERE request_id = :rid AND status = 'pending'"
        ), {"rid": request_id}).scalar()
        if pending == 0:
            self.db.execute(text(
                "UPDATE dbp_signature_requests "
                "SET status = 'completed', completed_at = :now WHERE id = :rid"
            ), {"now": now, "rid": request_id})
        self.db.flush()
        return {"success": True, "all_signed": pending == 0}

    def reject(self, request_id, signer_id, reason) -> Dict:
        row = self.db.execute(text(
            "SELECT id, status FROM dbp_signature_signers "
            "WHERE request_id = :rid AND signer_id = :sid"
        ), {"rid": request_id, "sid": signer_id}).fetchone()
        if not row:
            return {"success": False, "error": "Signer not found"}
        if row[1] != "pending":
            return {"success": False, "error": f"Signer status is {row[1]}, cannot reject"}
        self.db.execute(text(
            "UPDATE dbp_signature_signers "
            "SET status = 'rejected', rejection_reason = :reason WHERE id = :id"
        ), {"reason": reason, "id": row[0]})
        self.db.execute(text(
            "UPDATE dbp_signature_requests SET status = 'rejected' WHERE id = :rid"
        ), {"rid": request_id})
        self.db.flush()
        return {"success": True}

    def list_signature_requests(self, company_id, tenant_id=None, status=None) -> List[Dict]:
        conditions = ["company_id = :cid"]
        params: dict = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, company_id, reference_type, reference_id, "
            f"title, description, status, requested_by, created_at, completed_at "
            f"FROM dbp_signature_requests WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "company_id": r[2],
                "reference_type": r[3], "reference_id": r[4],
                "title": r[5], "description": r[6], "status": r[7],
                "requested_by": r[8],
                "created_at": r[9].isoformat() if r[9] else None,
                "completed_at": r[10].isoformat() if r[10] else None}
                for r in rows]

    # ── Approval Templates ──────────────────────────────────────

    def create_approval_template(self, tenant_id, company_id, name, entity_type,
                                 steps, **kw) -> str:
        tid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_approval_templates "
            "(id, tenant_id, company_id, name, entity_type, description, is_active) "
            "VALUES (:id,:tid,:cid,:name,:et,:desc,true)"
        ), {
            "id": tid, "tid": tenant_id, "cid": company_id,
            "name": name, "et": entity_type, "desc": kw.get("description"),
        })
        for s in steps:
            sid = str(uuid.uuid4())
            self.db.execute(text(
                "INSERT INTO dbp_approval_template_steps "
                "(id, tenant_id, template_id, step_number, approver_role, "
                "approver_id, sla_hours, auto_approve) "
                "VALUES (:id,:tid,:tpl,:sn,:ar,:ai,:sla,:aa)"
            ), {
                "id": sid, "tid": tenant_id, "tpl": tid,
                "sn": s["step_number"],
                "ar": s.get("approver_role"), "ai": s.get("approver_id"),
                "sla": s.get("sla_hours", 48),
                "aa": s.get("auto_approve", False),
            })
        self.db.flush()
        return tid

    def list_approval_templates(self, company_id, tenant_id=None) -> List[Dict]:
        conditions = ["company_id = :cid"]
        params: dict = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, company_id, name, entity_type, description, "
            f"is_active, created_at "
            f"FROM dbp_approval_templates WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "company_id": r[2],
                "name": r[3], "entity_type": r[4], "description": r[5],
                "is_active": bool(r[6]),
                "created_at": r[7].isoformat() if r[7] else None}
                for r in rows]

    def get_approval_template(self, template_id) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, tenant_id, company_id, name, entity_type, description, "
            "is_active, created_at "
            "FROM dbp_approval_templates WHERE id = :tid"
        ), {"tid": template_id}).fetchone()
        if not row:
            return None
        steps_rows = self.db.execute(text(
            "SELECT id, tenant_id, template_id, step_number, approver_role, "
            "approver_id, sla_hours, auto_approve "
            "FROM dbp_approval_template_steps WHERE template_id = :tid "
            "ORDER BY step_number"
        ), {"tid": template_id}).fetchall()
        steps = [{"id": r[0], "tenant_id": r[1], "template_id": r[2],
                  "step_number": r[3], "approver_role": r[4],
                  "approver_id": r[5], "sla_hours": r[6],
                  "auto_approve": bool(r[7])} for r in steps_rows]
        return {
            "id": row[0], "tenant_id": row[1], "company_id": row[2],
            "name": row[3], "entity_type": row[4], "description": row[5],
            "is_active": bool(row[6]),
            "created_at": row[7].isoformat() if row[7] else None,
            "steps": steps,
        }

    # ── Delegations ─────────────────────────────────────────────

    def create_delegation(self, tenant_id, company_id, delegator_id, delegate_id,
                          start_date, end_date, entity_type=None) -> str:
        did = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_delegations "
            "(id, tenant_id, company_id, delegator_id, delegate_id, "
            "entity_type, start_date, end_date, is_active) "
            "VALUES (:id,:tid,:cid,:di,:de,:et,:sd,:ed,true)"
        ), {
            "id": did, "tid": tenant_id, "cid": company_id,
            "di": delegator_id, "de": delegate_id, "et": entity_type,
            "sd": start_date, "ed": end_date,
        })
        self.db.flush()
        return did

    def list_delegations(self, company_id, tenant_id=None) -> List[Dict]:
        conditions = ["company_id = :cid"]
        params: dict = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, company_id, delegator_id, delegate_id, "
            f"entity_type, start_date, end_date, is_active, created_at "
            f"FROM dbp_delegations WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "company_id": r[2],
                "delegator_id": r[3], "delegate_id": r[4],
                "entity_type": r[5],
                "start_date": r[6].isoformat() if r[6] else None,
                "end_date": r[7].isoformat() if r[7] else None,
                "is_active": bool(r[8]),
                "created_at": r[9].isoformat() if r[9] else None}
                for r in rows]

    def get_active_delegation(self, company_id, delegator_id,
                              entity_type=None) -> Optional[Dict]:
        today = date.today()
        conditions = [
            "company_id = :cid", "delegator_id = :di",
            "is_active = true", "start_date <= :today", "end_date >= :today",
        ]
        params: dict = {"cid": company_id, "di": delegator_id, "today": today}
        if entity_type:
            conditions.append("entity_type = :et")
            params["et"] = entity_type
        where = " AND ".join(conditions)
        row = self.db.execute(text(
            f"SELECT id, tenant_id, company_id, delegator_id, delegate_id, "
            f"entity_type, start_date, end_date, is_active, created_at "
            f"FROM dbp_delegations WHERE {where} LIMIT 1"
        ), params).fetchone()
        if not row:
            return None
        return {"id": row[0], "tenant_id": row[1], "company_id": row[2],
                "delegator_id": row[3], "delegate_id": row[4],
                "entity_type": row[5],
                "start_date": row[6].isoformat() if row[6] else None,
                "end_date": row[7].isoformat() if row[7] else None,
                "is_active": bool(row[8]),
                "created_at": row[9].isoformat() if row[9] else None}
