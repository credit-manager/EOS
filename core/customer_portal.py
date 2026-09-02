"""
P57 Customer Portal Engine — one-stop tenant overview + support tickets.
Aggregates: company, onboarding, subscription, usage, marketplace,
builder projects, notifications, support. Defensive per-section.
"""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.billing_flow import BillingFlowEngine
from core.marketplace_engine import MarketplaceEngine
from core.onboarding_engine import OnboardingEngine


class CustomerPortalEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "company": self._section(self._company, tenant_id),
            "onboarding": self._section(self._onboarding, tenant_id),
            "subscription": self._section(self._subscription, tenant_id),
            "usage": self._section(self._usage, tenant_id),
            "marketplace": self._section(self._marketplace, tenant_id),
            "erp_builder": self._section(self._builder, tenant_id),
            "notifications": self._section(self._notifications, tenant_id),
            "support": self._section(self._support, tenant_id),
        }

    # ── SECTIONS ──

    def _company(self, tid):
        row = self.db.execute(text(
            "SELECT code, name_en FROM dbp_companies WHERE tenant_id = :t "
            "ORDER BY created_at LIMIT 1"), {"t": tid}).fetchone()
        return {"code": row[0], "name_en": row[1]} if row else None

    def _onboarding(self, tid):
        return OnboardingEngine(self.db).get_onboarding_status(tid)

    def _subscription(self, tid):
        data = BillingFlowEngine(self.db).my_subscription(tid)
        if not data:
            return {"plan": None, "status": "no_subscription"}
        sub = data.get("subscription") or {}
        plan = data.get("plan")
        return {"status": sub.get("status"),
                "plan_code": plan["plan_code"] if plan else None,
                "plan_name": plan["plan_name"] if plan else None,
                "license_seats": (data.get("license") or {}).get("seats"),
                "open_amount": next((float(i.get("amount") or 0) for i in
                                      (data.get("recent_invoices") or [])
                                      if i.get("status") == "pending"), 0.0)}

    def _usage(self, tid):
        return BillingFlowEngine(self.db).usage_summary(tid)

    def _marketplace(self, tid):
        installed = MarketplaceEngine(self.db).list_installed(tid)
        return {"count": len(installed), "items": [i["item_code"] for i in installed]}

    def _builder(self, tid):
        rows = self.db.execute(text(
            "SELECT status, COUNT(*) FROM dbp_builder_projects WHERE tenant_id = :t "
            "GROUP BY status"), {"t": tid}).fetchall()
        by_status = {r[0]: int(r[1]) for r in rows}
        return {"projects_total": sum(by_status.values()), "by_status": by_status}

    def _notifications(self, tid):
        try:
            row = self.db.execute(text(
                "SELECT COUNT(*) FROM dbp_tenant_notifications "
                "WHERE tenant_id = :t AND is_read = false"), {"t": tid}).fetchone()
            return {"unread": int(row[0])}
        except Exception:
            self.db.rollback()
            return {"unread": 0}

    def _support(self, tid):
        rows = self.db.execute(text(
            "SELECT status, COUNT(*) FROM dbp_support_tickets WHERE tenant_id = :t "
            "GROUP BY status"), {"t": tid}).fetchall()
        by_status = {r[0]: int(r[1]) for r in rows}
        return {"tickets_total": sum(by_status.values()),
                 "open": by_status.get("open", 0)}

    def _section(self, fn, tid):
        try:
            return {"data": fn(tid), "error": None}
        except Exception as exc:
            try:
                self.db.rollback()
            except Exception:
                pass
            return {"data": None, "error": str(exc)[:200]}

    # ── SUPPORT TICKETS ──

    def create_ticket(self, tenant_id: str, subject: str, message: str,
                      priority: str, created_by: str) -> dict[str, Any]:
        if not subject:
            return {"success": False, "error": "subject required"}
        if priority not in ("low", "normal", "high", "urgent"):
            return {"success": False, "error": "invalid priority"}
        n = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_support_tickets WHERE tenant_id = :t"),
            {"t": tenant_id}).fetchone()[0] + 1
        tid = str(uuid.uuid4())
        tnum = f"TKT-{tenant_id[:8].upper()}-{n:04d}"
        self.db.execute(text(
            "INSERT INTO dbp_support_tickets "
            "(id, tenant_id, ticket_number, subject, message, priority, created_by) "
            "VALUES (:id, :t, :n, :s, :m, :p, :by)"
        ), {"id": tid, "t": tenant_id, "n": tnum, "s": subject,
            "m": message, "p": priority, "by": created_by})
        self.db.flush()
        return {"success": True, "ticket_id": tid, "ticket_number": tnum,
                "status": "open"}

    def list_tickets(self, tenant_id: str, status: str | None = None) -> list[dict]:
        cond, params = "", {"t": tenant_id}
        if status:
            cond = "AND status = :st"
            params["st"] = status
        rows = self.db.execute(text(
            f"SELECT id, ticket_number, subject, priority, status, created_at, resolved_at "
            f"FROM dbp_support_tickets WHERE tenant_id = :t {cond} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "ticket_number": r[1], "subject": r[2],
                 "priority": r[3], "status": r[4],
                 "created_at": str(r[5]) if r[5] else None,
                 "resolved_at": str(r[6]) if r[6] else None} for r in rows]

    def close_ticket(self, tenant_id: str, ticket_id: str) -> dict[str, Any]:
        row = self.db.execute(text(
            "SELECT status FROM dbp_support_tickets WHERE id = :id AND tenant_id = :t"),
            {"id": ticket_id, "t": tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Ticket not found"}
        if row[0] == "closed":
            return {"success": False, "error": "Already closed"}
        self.db.execute(text(
            "UPDATE dbp_support_tickets SET status='closed', resolved_at = NOW() "
            "WHERE id = :id"), {"id": ticket_id})
        self.db.flush()
        return {"success": True}
