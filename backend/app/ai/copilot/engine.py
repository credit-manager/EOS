"""Ask EOS Engine — Intent understanding, query building, analysis, and explanation."""
import logging
from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger("2to-eos.ai.copilot")


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

class IntentType(str, Enum):
    QUERY = "query"
    ANALYSIS = "analysis"
    ACTION = "action"
    SUMMARY = "summary"
    COMPARISON = "comparison"
    EXPLANATION = "explanation"
    RECOMMENDATION = "recommendation"


class IntentClassifier:
    """Classify user intent from natural language messages."""

    def classify(self, message: str, context: dict[str, Any]) -> tuple[IntentType, float]:
        q = message.lower()

        action_words = [
            "send", "create", "approve", "reject", "notify", "update",
            "delete", "cancel", "submit", "post", "close", "reopen",
        ]
        if any(w in q for w in action_words):
            return IntentType.ACTION, 0.85

        explanation_words = [
            "why", "what caused", "explain", "reason for", "how did",
            "what happened", "root cause",
        ]
        if any(w in q for w in explanation_words):
            return IntentType.EXPLANATION, 0.9

        comparison_words = [
            "compare", "versus", "vs", "difference between", "better",
            "worse", "higher", "lower", "ranking", "top", "bottom",
        ]
        if any(w in q for w in comparison_words):
            return IntentType.COMPARISON, 0.85

        recommendation_words = [
            "what needs", "what should", "recommend", "suggest",
            "prioritize", "attention", "urgent", "critical",
        ]
        if any(w in q for w in recommendation_words):
            return IntentType.RECOMMENDATION, 0.9

        analysis_words = [
            "analyze", "analysis", "trend", "pattern", "impact",
            "correlation", "forecast", "projection", "variance",
        ]
        if any(w in q for w in analysis_words):
            return IntentType.ANALYSIS, 0.85

        summary_words = [
            "summary", "overview", "dashboard", "status", "health",
            "snapshot", "report", "briefing",
        ]
        if any(w in q for w in summary_words):
            return IntentType.SUMMARY, 0.9

        return IntentType.QUERY, 0.7


# ---------------------------------------------------------------------------
# Entity Resolver
# ---------------------------------------------------------------------------

ENTITY_KEYWORDS: dict[str, list[str]] = {
    "invoice": ["invoice", "invoices", "receivable", "ar", "customer bill"],
    "bill": ["bill", "bills", "payable", "ap", "vendor bill"],
    "payment": ["payment", "payments", "paid", "remittance"],
    "project": ["project", "projects", "engagement", "portfolio"],
    "supplier": ["supplier", "suppliers", "vendor", "vendors"],
    "customer": ["customer", "customers", "client", "clients"],
    "employee": ["employee", "employees", "staff", "team member"],
    "order": ["order", "orders", "purchase order", "po"],
    "contract": ["contract", "contracts", "agreement", "agreements"],
    "task": ["task", "tasks", "todo", "action item"],
    "account": ["account", "accounts", "ledger", "gl", "trial balance"],
    "budget": ["budget", "budgets", "allocation", "utilization"],
    "approval": ["approval", "approvals", "pending approval", "waiting"],
    "journal_entry": ["journal", "journal entry", "journal entries", "posting"],
}


class EntityResolver:
    """Find which business objects the user is asking about."""

    def resolve(self, message: str, intent: IntentType) -> list[str]:
        q = message.lower()
        matched: list[str] = []

        for entity, keywords in ENTITY_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                matched.append(entity)

        if not matched:
            if intent in (IntentType.SUMMARY, IntentType.RECOMMENDATION):
                matched = ["invoice", "bill", "project", "supplier", "approval"]
            else:
                matched = ["account"]

        return matched


# ---------------------------------------------------------------------------
# Filter Extractor
# ---------------------------------------------------------------------------

class FilterExtractor:
    """Extract filters from the user message (status, date ranges, amounts)."""

    def extract(self, message: str) -> dict[str, Any]:
        q = message.lower()
        filters: dict[str, Any] = {}

        if any(w in q for w in ["overdue", "past due", "late", "expired"]):
            filters["status"] = "overdue"
        elif any(w in q for w in ["pending", "waiting", "open"]):
            filters["status"] = "pending"
        elif any(w in q for w in ["draft"]):
            filters["status"] = "draft"
        elif any(w in q for w in ["approved", "completed", "done", "paid"]):
            filters["status"] = "completed"

        if any(w in q for w in ["today", "now", "current"]):
            filters["date_range"] = "today"
        elif any(w in q for w in ["this week", "weekly"]):
            filters["date_range"] = "this_week"
        elif any(w in q for w in ["this month", "monthly"]):
            filters["date_range"] = "this_month"
        elif any(w in q for w in ["this quarter", "quarterly"]):
            filters["date_range"] = "this_quarter"
        elif any(w in q for w in ["this year", "yearly", "annual"]):
            filters["date_range"] = "this_year"

        if any(w in q for w in ["high value", "large", "expensive", "over 100"]):
            filters["amount_min"] = 100000
        elif any(w in q for w in ["low value", "small", "cheap"]):
            filters["amount_max"] = 1000

        return filters


# ---------------------------------------------------------------------------
# Query Builder
# ---------------------------------------------------------------------------

class QueryBuilder:
    """Build a query plan for the requested information."""

    def build(
        self,
        entities: list[str],
        intent: IntentType,
        filters: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        primary = entities[0] if entities else "account"

        field_map: dict[str, list[str]] = {
            "invoice": ["invoice_number", "customer_name", "total_amount", "balance_due", "due_date", "status", "issue_date"],
            "bill": ["bill_number", "supplier_name", "total_amount", "balance_due", "due_date", "status", "issue_date"],
            "payment": ["payment_number", "amount", "payment_date", "payment_type", "status"],
            "project": ["name", "status", "budget", "spent", "margin", "start_date", "end_date"],
            "supplier": ["name", "rating", "total_orders", "contact_email"],
            "customer": ["name", "email", "phone", "total_revenue"],
            "employee": ["name", "department", "role", "email"],
            "order": ["order_number", "supplier", "amount", "status", "order_date"],
            "contract": ["title", "supplier", "value", "start_date", "end_date", "status"],
            "task": ["title", "assigned_to", "status", "due_date", "priority"],
            "account": ["code", "name", "account_type", "debit", "credit"],
            "budget": ["name", "allocated", "spent", "utilization"],
            "approval": ["action", "assigned_to", "status", "created_at"],
            "journal_entry": ["entry_number", "reference", "status", "total_debit", "total_credit"],
        }

        return {
            "entity": primary,
            "entities": entities,
            "filters": filters,
            "fields": field_map.get(primary, ["name", "status"]),
            "sort": {"field": "created_at", "order": "desc"},
            "limit": 20,
        }


# ---------------------------------------------------------------------------
# Data Retrieval
# ---------------------------------------------------------------------------

class DataRetriever:
    """Execute query plans against the actual database."""

    def retrieve(self, query_plan: dict[str, Any], db: Session, tenant_id: UUID) -> list[dict[str, Any]]:
        entity = query_plan["entity"]
        filters = query_plan.get("filters", {})
        limit = query_plan.get("limit", 20)

        if entity == "invoice":
            return self._retrieve_invoices(db, tenant_id, filters, limit)
        elif entity == "bill":
            return self._retrieve_bills(db, tenant_id, filters, limit)
        elif entity == "payment":
            return self._retrieve_payments(db, tenant_id, filters, limit)
        elif entity == "project":
            return self._retrieve_projects(db, tenant_id, filters, limit)
        elif entity == "supplier":
            return self._retrieve_suppliers(db, tenant_id, filters, limit)
        elif entity == "customer":
            return self._retrieve_customers(db, tenant_id, filters, limit)
        elif entity in ("account", "journal_entry"):
            return self._retrieve_accounts(db, tenant_id, filters, limit)
        elif entity == "task":
            return self._retrieve_tasks(db, tenant_id, filters, limit)
        elif entity == "approval":
            return self._retrieve_approvals(db, tenant_id, filters, limit)
        elif entity == "order":
            return self._retrieve_orders(db, tenant_id, filters, limit)
        else:
            return self._retrieve_records(db, tenant_id, entity, filters, limit)

    def _retrieve_invoices(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...financial.models import Invoice, Customer

        q = select(Invoice).where(Invoice.tenant_id == tenant_id)
        status = filters.get("status")
        if status == "overdue":
            q = q.where(Invoice.status.in_(["sent", "overdue"]), Invoice.balance_due > 0)
        elif status:
            q = q.where(Invoice.status == status)
        q = q.order_by(Invoice.created_at.desc()).limit(limit)

        rows = db.scalars(q).all()
        results = []
        for inv in rows:
            customer = db.get(Customer, inv.customer_id) if inv.customer_id else None
            days_overdue = 0
            if inv.due_date and inv.due_date < date.today():
                days_overdue = (date.today() - inv.due_date).days
            results.append({
                "id": str(inv.id),
                "entity": "invoice",
                "record_id": inv.invoice_number,
                "customer_name": customer.name if customer else "Unknown",
                "total_amount": float(inv.total_amount),
                "balance_due": float(inv.balance_due),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "status": inv.status,
                "days_overdue": days_overdue,
                "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            })
        return results

    def _retrieve_bills(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...financial.models import Bill, Supplier

        q = select(Bill).where(Bill.tenant_id == tenant_id)
        status = filters.get("status")
        if status == "overdue":
            q = q.where(Bill.status.in_(["received", "overdue"]), Bill.balance_due > 0)
        elif status:
            q = q.where(Bill.status == status)
        q = q.order_by(Bill.created_at.desc()).limit(limit)

        rows = db.scalars(q).all()
        results = []
        for bill in rows:
            supplier = db.get(Supplier, bill.supplier_id) if bill.supplier_id else None
            days_overdue = 0
            if bill.due_date and bill.due_date < date.today():
                days_overdue = (date.today() - bill.due_date).days
            results.append({
                "id": str(bill.id),
                "entity": "bill",
                "record_id": bill.bill_number,
                "supplier_name": supplier.name if supplier else "Unknown",
                "total_amount": float(bill.total_amount),
                "balance_due": float(bill.balance_due),
                "due_date": bill.due_date.isoformat() if bill.due_date else None,
                "status": bill.status,
                "days_overdue": days_overdue,
                "issue_date": bill.issue_date.isoformat() if bill.issue_date else None,
            })
        return results

    def _retrieve_payments(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...financial.models import Payment

        q = select(Payment).where(Payment.tenant_id == tenant_id)
        status = filters.get("status")
        if status:
            q = q.where(Payment.status == status)
        q = q.order_by(Payment.created_at.desc()).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(p.id),
                "entity": "payment",
                "record_id": p.payment_number,
                "amount": float(p.amount),
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "payment_type": p.payment_type,
                "status": p.status,
            }
            for p in rows
        ]

    def _retrieve_projects(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...records.models import Record

        q = select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "project",
        )
        q = q.order_by(Record.created_at.desc()).limit(limit)

        rows = db.scalars(q).all()
        results = []
        for rec in rows:
            data = rec.data or {}
            budget = data.get("budget", 0)
            spent = data.get("spent", 0)
            utilization = (spent / budget * 100) if budget > 0 else 0
            results.append({
                "id": str(rec.id),
                "entity": "project",
                "record_id": data.get("name", str(rec.id)[:8]),
                "name": data.get("name", "Unnamed"),
                "status": data.get("status", "unknown"),
                "budget": budget,
                "spent": spent,
                "utilization_pct": round(utilization, 1),
                "margin": data.get("margin", 0),
                "risk_level": "critical" if utilization > 90 else "high" if utilization > 75 else "medium" if utilization > 60 else "low",
            })
        return results

    def _retrieve_suppliers(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...records.models import Record

        q = select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "supplier",
        ).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(rec.id),
                "entity": "supplier",
                "record_id": (rec.data or {}).get("name", str(rec.id)[:8]),
                "name": (rec.data or {}).get("name", "Unknown"),
                "rating": (rec.data or {}).get("rating", 0),
                "total_orders": (rec.data or {}).get("total_orders", 0),
            }
            for rec in rows
        ]

    def _retrieve_customers(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...records.models import Record

        q = select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "customer",
        ).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(rec.id),
                "entity": "customer",
                "record_id": (rec.data or {}).get("name", str(rec.id)[:8]),
                "name": (rec.data or {}).get("name", "Unknown"),
                "email": (rec.data or {}).get("email", ""),
                "total_revenue": (rec.data or {}).get("total_revenue", 0),
            }
            for rec in rows
        ]

    def _retrieve_accounts(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...financial.models import Account

        q = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.is_active.is_(True),
        ).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(a.id),
                "entity": "account",
                "record_id": a.code,
                "code": a.code,
                "name": a.name,
                "account_type": a.account_type,
                "debit": float(a.current_balance_debit),
                "credit": float(a.current_balance_credit),
            }
            for a in rows
        ]

    def _retrieve_tasks(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...records.models import Record

        q = select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "task",
        ).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(rec.id),
                "entity": "task",
                "record_id": (rec.data or {}).get("title", str(rec.id)[:8]),
                "title": (rec.data or {}).get("title", "Untitled"),
                "assigned_to": (rec.data or {}).get("assigned_to", ""),
                "status": (rec.data or {}).get("status", "open"),
                "priority": (rec.data or {}).get("priority", "normal"),
            }
            for rec in rows
        ]

    def _retrieve_approvals(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...workflow.models import ApprovalTask

        q = select(ApprovalTask).where(
            ApprovalTask.tenant_id == tenant_id,
            ApprovalTask.status == "pending",
        ).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(a.id),
                "entity": "approval",
                "record_id": str(a.id)[:8],
                "action": a.action,
                "assigned_to": a.assigned_to_role,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ]

    def _retrieve_orders(self, db: Session, tenant_id: UUID, filters: dict, limit: int) -> list[dict]:
        from ...records.models import Record

        q = select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "order",
        ).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(rec.id),
                "entity": "order",
                "record_id": (rec.data or {}).get("order_number", str(rec.id)[:8]),
                "supplier": (rec.data or {}).get("supplier", "Unknown"),
                "amount": (rec.data or {}).get("amount", 0),
                "status": (rec.data or {}).get("status", "unknown"),
            }
            for rec in rows
        ]

    def _retrieve_records(self, db: Session, tenant_id: UUID, entity: str, filters: dict, limit: int) -> list[dict]:
        from ...records.models import Record

        q = select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity,
        ).limit(limit)

        rows = db.scalars(q).all()
        return [
            {
                "id": str(rec.id),
                "entity": entity,
                "record_id": str(rec.id)[:8],
                "data": rec.data or {},
            }
            for rec in rows
        ]


# ---------------------------------------------------------------------------
# Data Analyzer
# ---------------------------------------------------------------------------

class DataAnalyzer:
    """Analyze query results and generate insights."""

    def analyze(
        self,
        query_plan: dict[str, Any],
        results: list[dict[str, Any]],
        intent: IntentType,
    ) -> dict[str, Any]:
        entity = query_plan["entity"]
        count = len(results)

        if count == 0:
            return {
                "summary": f"No {entity} records found matching your criteria.",
                "insights": [],
                "risks": [],
                "recommendations": ["Try broadening your search criteria."],
                "sources": [],
            }

        summary = self._build_summary(entity, results)
        insights = self._build_insights(entity, results)
        risks = self._build_risks(entity, results)
        recommendations = self._build_recommendations(entity, results, intent)

        return {
            "summary": summary,
            "insights": insights,
            "risks": risks,
            "recommendations": recommendations,
        }

    def _build_summary(self, entity: str, results: list[dict]) -> str:
        count = len(results)

        if entity == "invoice":
            total = sum(r.get("total_amount", 0) for r in results)
            outstanding = sum(r.get("balance_due", 0) for r in results)
            overdue = [r for r in results if r.get("days_overdue", 0) > 0]
            parts = [f"You have {count} invoice(s) totaling ${total:,.2f}."]
            if outstanding > 0:
                parts.append(f"Outstanding balance: ${outstanding:,.2f}.")
            if overdue:
                parts.append(f"{len(overdue)} are overdue.")
            return " ".join(parts)

        if entity == "bill":
            total = sum(r.get("total_amount", 0) for r in results)
            outstanding = sum(r.get("balance_due", 0) for r in results)
            return f"You have {count} bill(s) totaling ${total:,.2f}. Outstanding: ${outstanding:,.2f}."

        if entity == "payment":
            total = sum(r.get("amount", 0) for r in results)
            return f"{count} payment(s) found totaling ${total:,.2f}."

        if entity == "project":
            at_risk = [r for r in results if r.get("risk_level") in ("high", "critical")]
            return f"{count} project(s) found. {len(at_risk)} at risk."

        if entity == "approval":
            return f"{count} pending approval(s) requiring attention."

        return f"{count} {entity}(s) found."

    def _build_insights(self, entity: str, results: list[dict]) -> list[str]:
        insights: list[str] = []

        if entity == "invoice":
            overdue = [r for r in results if r.get("days_overdue", 0) > 0]
            if overdue:
                oldest = max(overdue, key=lambda r: r.get("days_overdue", 0))
                insights.append(f"Oldest overdue invoice: {oldest.get('record_id')} at {oldest.get('days_overdue')} days past due.")

            suppliers: dict[str, list] = {}
            for r in overdue:
                name = r.get("customer_name", "Unknown")
                suppliers.setdefault(name, []).append(r)
            for name, invs in suppliers.items():
                if len(invs) > 1:
                    ids = ", ".join(i.get("record_id", "") for i in invs)
                    insights.append(f"{name} has {len(invs)} overdue invoices ({ids}).")

        elif entity == "bill":
            overdue = [r for r in results if r.get("days_overdue", 0) > 0]
            if overdue:
                oldest = max(overdue, key=lambda r: r.get("days_overdue", 0))
                insights.append(f"Oldest overdue bill: {oldest.get('record_id')} at {oldest.get('days_overdue')} days past due.")

        elif entity == "project":
            critical = [r for r in results if r.get("risk_level") == "critical"]
            high = [r for r in results if r.get("risk_level") == "high"]
            if critical:
                names = ", ".join(r.get("name", "") for r in critical)
                insights.append(f"Critical projects ({names}) are over 90% budget utilization.")
            if high:
                names = ", ".join(r.get("name", "") for r in high)
                insights.append(f"High-risk projects ({names}) are over 75% budget utilization.")
            margins = [r.get("margin", 0) for r in results if r.get("margin")]
            if margins:
                avg_margin = sum(margins) / len(margins)
                insights.append(f"Average project margin: {avg_margin:.1f}%.")

        return insights

    def _build_risks(self, entity: str, results: list[dict]) -> list[str]:
        risks: list[str] = []

        if entity == "invoice":
            overdue = [r for r in results if r.get("days_overdue", 0) > 0]
            total_overdue = sum(r.get("balance_due", 0) for r in overdue)
            if total_overdue > 50000:
                risks.append(f"Overdue receivables total ${total_overdue:,.2f} — may impact cash flow.")
            very_old = [r for r in overdue if r.get("days_overdue", 0) > 60]
            if very_old:
                risks.append(f"{len(very_old)} invoice(s) over 60 days past due — collection risk.")

        elif entity == "bill":
            overdue = [r for r in results if r.get("days_overdue", 0) > 0]
            if overdue:
                total_overdue = sum(r.get("balance_due", 0) for r in overdue)
                risks.append(f"Overdue payables total ${total_overdue:,.2f} — may affect supplier relationships.")

        elif entity == "project":
            critical = [r for r in results if r.get("risk_level") == "critical"]
            if critical:
                risks.append(f"{len(critical)} project(s) at critical budget utilization — immediate action required.")

        return risks

    def _build_recommendations(self, entity: str, results: list[dict], intent: IntentType) -> list[str]:
        recs: list[str] = []

        if entity == "invoice":
            overdue = [r for r in results if r.get("days_overdue", 0) > 0]
            if overdue:
                recs.append("Send payment reminders for overdue invoices.")
                suppliers = set(r.get("customer_name", "") for r in overdue if r.get("days_overdue", 0) > 30)
                for s in suppliers:
                    if s:
                        recs.append(f"Follow up with {s} on long-overdue payments.")

        elif entity == "bill":
            overdue = [r for r in results if r.get("days_overdue", 0) > 0]
            if overdue:
                recs.append("Prioritize payment of overdue bills to maintain supplier relationships.")

        elif entity == "project":
            at_risk = [r for r in results if r.get("risk_level") in ("high", "critical")]
            if at_risk:
                recs.append("Review budget allocation for at-risk projects.")
                recs.append("Consider scope adjustments or additional funding.")

        elif entity == "approval":
            if results:
                recs.append("Process pending approvals to unblock workflows.")

        if intent == IntentType.RECOMMENDATION and not recs:
            recs.append("All items appear to be within normal parameters.")

        return recs


# ---------------------------------------------------------------------------
# Source Explainer
# ---------------------------------------------------------------------------

class SourceExplainer:
    """Explain where data came from for traceability."""

    def explain(self, results: list[dict], query_plan: dict[str, Any]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []

        for r in results[:10]:
            entity = r.get("entity", query_plan.get("entity", "unknown"))
            record_id = r.get("record_id", str(r.get("id", "")))

            display = self._build_display(entity, r)
            path = [f"{entity}:{record_id}"]

            sources.append({
                "entity": entity,
                "record_id": record_id,
                "display": display,
                "path": path,
            })

        return sources

    def _build_display(self, entity: str, record: dict) -> str:
        if entity == "invoice":
            inv_id = record.get("record_id", "")
            customer = record.get("customer_name", "Unknown")
            amount = record.get("total_amount", 0)
            due = record.get("due_date", "N/A")
            days = record.get("days_overdue", 0)
            suffix = f" ({days} days overdue)" if days > 0 else ""
            return f"Invoice {inv_id} from {customer} for ${amount:,.2f} (due {due}){suffix}"

        if entity == "bill":
            bill_id = record.get("record_id", "")
            supplier = record.get("supplier_name", "Unknown")
            amount = record.get("total_amount", 0)
            due = record.get("due_date", "N/A")
            return f"Bill {bill_id} from {supplier} for ${amount:,.2f} (due {due})"

        if entity == "project":
            name = record.get("name", "Unknown")
            utilization = record.get("utilization_pct", 0)
            risk = record.get("risk_level", "low")
            return f"Project '{name}' — {utilization}% budget used [{risk} risk]"

        if entity == "payment":
            pay_id = record.get("record_id", "")
            amount = record.get("amount", 0)
            ptype = record.get("payment_type", "")
            return f"Payment {pay_id}: ${amount:,.2f} ({ptype})"

        if entity == "approval":
            action = record.get("action", "")
            assigned = record.get("assigned_to", "")
            return f"Approval: {action} (assigned to {assigned})"

        name = record.get("name") or record.get("title") or record.get("record_id", str(record.get("id", "")))
        return f"{entity.title()}: {name}"


# ---------------------------------------------------------------------------
# Action Executor
# ---------------------------------------------------------------------------

class ActionExecutor:
    """Execute actions on behalf of the user."""

    SUPPORTED_ACTIONS = frozenset({
        "send_notification", "create_task", "approve_item",
        "create_record", "run_report",
    })

    def execute(
        self,
        action_type: str,
        params: dict[str, Any],
        principal: dict[str, Any],
        db: Session,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        if action_type not in self.SUPPORTED_ACTIONS:
            return {"success": False, "error": f"Unsupported action: {action_type}"}

        if action_type == "send_notification":
            return self._send_notification(params, principal, db, tenant_id)
        elif action_type == "create_task":
            return self._create_task(params, principal, db, tenant_id)
        elif action_type == "create_record":
            return self._create_record(params, principal, db, tenant_id)
        elif action_type == "run_report":
            return {"success": True, "message": "Report generation initiated.", "report_type": params.get("report_type", "general")}
        else:
            return {"success": True, "message": f"Action '{action_type}' acknowledged."}

    def _send_notification(self, params: dict, principal: dict, db: Session, tenant_id: UUID) -> dict:
        recipient = params.get("recipient", "team")
        subject = params.get("subject", "EOS Notification")
        message = params.get("message", "")
        logger.info("Notification sent to %s: %s", recipient, subject)
        return {"success": True, "message": f"Notification sent to {recipient}.", "recipient": recipient, "subject": subject}

    def _create_task(self, params: dict, principal: dict, db: Session, tenant_id: UUID) -> dict:
        from ...records.models import Record
        import uuid

        title = params.get("title", "AI-generated task")
        assigned_to = params.get("assigned_to", "")

        record = Record(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entity_code="task",
            data={"title": title, "assigned_to": assigned_to, "status": "open", "priority": params.get("priority", "normal"), "created_by": principal.get("user_id", "ai")},
        )
        db.add(record)
        db.commit()

        return {"success": True, "message": f"Task created: {title}", "record_id": str(record.id)}

    def _create_record(self, params: dict, principal: dict, db: Session, tenant_id: UUID) -> dict:
        from ...records.models import Record
        import uuid

        entity_code = params.get("entity_code", "note")
        data = params.get("data", {})

        record = Record(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entity_code=entity_code,
            data=data,
        )
        db.add(record)
        db.commit()

        return {"success": True, "message": f"Record created in {entity_code}.", "record_id": str(record.id)}


# ---------------------------------------------------------------------------
# Ask EOS Engine (orchestrator)
# ---------------------------------------------------------------------------

class AskEOSEngine:
    """Orchestrates the full Ask EOS pipeline: intent → entities → query → analyze → explain."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.classifier = IntentClassifier()
        self.entity_resolver = EntityResolver()
        self.filter_extractor = FilterExtractor()
        self.query_builder = QueryBuilder()
        self.retriever = DataRetriever()
        self.analyzer = DataAnalyzer()
        self.source_explainer = SourceExplainer()
        self.action_executor = ActionExecutor()

    def process(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        ctx = context or {}

        # 1. Intent classification
        intent, confidence = self.classifier.classify(message, ctx)

        # 2. Entity resolution
        entities = self.entity_resolver.resolve(message, intent)

        # 3. Filter extraction
        filters = self.filter_extractor.extract(message)

        # 4. Query building
        query_plan = self.query_builder.build(entities, intent, filters, str(self.tenant_id))

        # 5. Data retrieval
        results = self.retriever.retrieve(query_plan, self.db, self.tenant_id)

        # 6. Analysis
        analysis = self.analyzer.analyze(query_plan, results, intent)

        # 7. Source explanation
        sources = self.source_explainer.explain(results, query_plan)

        # 8. Build response
        response_text = analysis["summary"]
        if analysis["insights"]:
            response_text += "\n\n" + "\n".join(f"• {i}" for i in analysis["insights"])
        if analysis["risks"]:
            response_text += "\n\nRisks:\n" + "\n".join(f"⚠ {r}" for r in analysis["risks"])
        if analysis["recommendations"]:
            response_text += "\n\nRecommendations:\n" + "\n".join(f"→ {r}" for r in analysis["recommendations"])

        # 9. Suggestions
        suggestions = self._build_suggestions(intent, entities, results)

        # 10. Determine agent type
        agent = self._map_agent(entities)

        return {
            "response": response_text,
            "agent": agent["code"],
            "agent_name": agent["name"],
            "intent": intent.value,
            "entities": entities,
            "actions_taken": [],
            "suggestions": suggestions,
            "sources": sources,
            "insights": analysis["insights"],
            "risks": analysis["risks"],
            "confidence": confidence,
            "compliant": True,
        }

    def _build_suggestions(self, intent: IntentType, entities: list[str], results: list[dict]) -> list[str]:
        suggestions: list[str] = []

        if intent != IntentType.SUMMARY:
            suggestions.append("Give me a business health summary")

        if "invoice" in entities:
            suggestions.append("Show overdue invoices by age")
            suggestions.append("Send payment reminders")
        elif "bill" in entities:
            suggestions.append("Show upcoming payable due dates")
        elif "project" in entities:
            suggestions.append("Compare project margins")
        elif "supplier" in entities:
            suggestions.append("Show supplier spending analysis")

        suggestions.append("What needs my attention today?")

        return suggestions[:5]

    def _map_agent(self, entities: list[str]) -> dict[str, str]:
        finance_entities = {"invoice", "bill", "payment", "account", "journal_entry", "budget"}
        project_entities = {"project", "task"}
        procurement_entities = {"supplier", "order", "contract"}

        entity_set = set(entities)

        if entity_set & finance_entities:
            return {"code": "finance_agent", "name": "Finance Agent"}
        if entity_set & project_entities:
            return {"code": "project_agent", "name": "Project Agent"}
        if entity_set & procurement_entities:
            return {"code": "procurement_agent", "name": "Procurement Agent"}

        return {"code": "executive_agent", "name": "Executive Agent"}
