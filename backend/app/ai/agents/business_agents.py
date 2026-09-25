"""AI Business Agents - specialized agents for business operations."""
import json
import logging
from typing import Any

from ..service import BaseAgent

logger = logging.getLogger("2to-eos.ai.agents")


class FinanceAgent(BaseAgent):
    """Finance Agent - handles financial queries, analysis, and reporting."""

    def run(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "")
        intent = self._classify_finance_intent(query)

        if intent == "trial_balance":
            result = self._execute_tool("get_financial_summary", {}, context)
            return self._format_trial_balance(result, query)

        if intent == "account_analysis":
            result = self._execute_tool("get_financial_summary", {}, context)
            return self._format_account_analysis(result, query)

        if intent == "budget_check":
            result = self._execute_tool("get_project_health", {}, context)
            return self._format_budget_check(result, query)

        if intent == "cash_flow":
            result = self._execute_tool("get_financial_summary", {}, context)
            return self._format_cash_flow(result, query)

        result = self._execute_tool("get_financial_summary", {}, context)
        return self._format_general(result, query)

    def _classify_finance_intent(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["trial balance", " balances", " ledger"]):
            return "trial_balance"
        if any(w in q for w in ["account", "accounts", "revenue", "expense", "asset", "liability"]):
            return "account_analysis"
        if any(w in q for w in ["budget", "utilization", "spending", "over budget"]):
            return "budget_check"
        if any(w in q for w in ["cash flow", "cash", "liquidity", "payment"]):
            return "cash_flow"
        return "general"

    def _format_trial_balance(self, result: dict, query: str) -> dict:
        accounts = result.get("accounts", [])
        lines = []
        for acc in accounts[:15]:
            lines.append(f"  {acc['code']} {acc['name']}: Dr {acc['debit']:,} | Cr {acc['credit']:,}")

        return {
            "response": (
                f"Trial Balance Summary:\n"
                f"Total Accounts: {result['total_accounts']}\n"
                f"Total Debits: {result['total_debit']:,}\n"
                f"Total Credits: {result['total_credit']:,}\n"
                f"Balanced: {'Yes' if result['is_balanced'] else 'No'}\n\n"
                f"Account Details:\n" + "\n".join(lines)
            ),
            "data": result,
            "agent": self.code,
        }

    def _format_account_analysis(self, result: dict, query: str) -> dict:
        accounts = result.get("accounts", [])
        by_type: dict[str, list] = {}
        for acc in accounts:
            t = acc["type"]
            by_type.setdefault(t, []).append(acc)

        lines = [f"Account Analysis ({result['total_accounts']} accounts):"]
        for acc_type, accs in by_type.items():
            total_dr = sum(a["debit"] for a in accs)
            total_cr = sum(a["credit"] for a in accs)
            lines.append(f"\n  {acc_type.upper()}: {len(accs)} accounts, Dr {total_dr:,} | Cr {total_cr:,}")
            for a in accs[:5]:
                lines.append(f"    - {a['code']} {a['name']}: {a['debit']:,}/{a['credit']:,}")

        return {
            "response": "\n".join(lines),
            "data": result,
            "agent": self.code,
        }

    def _format_budget_check(self, result: dict, query: str) -> dict:
        at_risk = result.get("at_risk", [])
        if at_risk:
            lines = [f"Projects at Risk ({len(at_risk)}):"]
            for p in at_risk:
                lines.append(f"  - {p['name']}: {p['utilization_pct']}% utilized [{p['risk_level'].upper()}]")
        else:
            lines = ["All projects within budget parameters."]
        return {
            "response": "\n".join(lines),
            "data": result,
            "agent": self.code,
        }

    def _format_cash_flow(self, result: dict, query: str) -> dict:
        return {
            "response": (
                f"Cash Position:\n"
                f"Total Debits: {result['total_debit']:,}\n"
                f"Total Credits: {result['total_credit']:,}\n"
                f"Net Position: {result['total_debit'] - result['total_credit']:,}"
            ),
            "data": result,
            "agent": self.code,
        }

    def _format_general(self, result: dict, query: str) -> dict:
        return {
            "response": (
                f"Financial Overview:\n"
                f"  Accounts: {result['total_accounts']}\n"
                f"  Posted Entries: {result['posted_entries']}\n"
                f"  Debits: {result['total_debit']:,} | Credits: {result['total_credit']:,}\n"
                f"  Balanced: {'Yes' if result['is_balanced'] else 'No'}"
            ),
            "data": result,
            "agent": self.code,
        }


class ProcurementAgent(BaseAgent):
    """Procurement Agent - handles supplier and purchase order queries."""

    def run(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "")
        intent = self._classify_procurement_intent(query)

        result = self._execute_tool("get_procurement_analysis", {}, context)
        procurements = result.get("procurements", [])
        suppliers = result.get("suppliers", [])

        if intent == "pending_orders":
            pending = [p for p in procurements if p["status"] in ("draft", "pending", "requested")]
            lines = [f"Pending Procurements ({len(pending)}):"]
            for p in pending:
                lines.append(f"  - {p['title']} | {p['amount']:,} | {p['priority']}")
            return {"response": "\n".join(lines), "data": result, "agent": self.code}

        if intent == "supplier_analysis":
            lines = [f"Supplier Analysis ({len(suppliers)} suppliers):"]
            for s in suppliers:
                lines.append(f"  - {s['name']}: Rating {s['rating']}/5, Orders: {s['total_orders']}")
            return {"response": "\n".join(lines), "data": result, "agent": self.code}

        return {
            "response": (
                f"Procurement Overview:\n"
                f"  Total: {result['total_procurements']} | Pending: {result['pending_count']}\n"
                f"  Total Value: {result['total_value']:,}\n"
                f"  Suppliers: {len(suppliers)}"
            ),
            "data": result,
            "agent": self.code,
        }

    def _classify_procurement_intent(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["pending", "waiting", "draft", "open"]):
            return "pending_orders"
        if any(w in q for w in ["supplier", "vendor", "rating"]):
            return "supplier_analysis"
        return "general"


class ProjectAgent(BaseAgent):
    """Project Agent - handles project health, progress, and risk queries."""

    def run(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "")
        result = self._execute_tool("get_project_health", {}, context)
        projects = result.get("projects", [])
        at_risk = result.get("at_risk", [])

        intent = self._classify_project_intent(query)

        if intent == "at_risk":
            if at_risk:
                lines = [f"Projects at Risk ({len(at_risk)}):"]
                for p in at_risk:
                    lines.append(
                        f"  - {p['name']}: {p['utilization_pct']}% budget used "
                        f"[{p['risk_level'].upper()}] Margin: {p['margin']}"
                    )
            else:
                lines = ["No projects currently at risk."]
            return {"response": "\n".join(lines), "data": result, "agent": self.code}

        if intent == "overview":
            lines = [f"Project Portfolio ({len(projects)} projects):"]
            for p in projects:
                status_icon = {"active": "🟢", "completed": "✅", "planning": "🔵"}.get(p["status"], "⚪")
                lines.append(
                    f"  {status_icon} {p['name']}: {p['status']} | "
                    f"Budget: {p['budget']:,} | Used: {p['utilization_pct']}%"
                )
            return {"response": "\n".join(lines), "data": result, "agent": self.code}

        return {
            "response": (
                f"Project Health:\n"
                f"  Total: {result['total_projects']}\n"
                f"  At Risk: {len(at_risk)}\n"
                + ("\n".join(
                    f"  - {p['name']}: {p['utilization_pct']}% [{p['risk_level']}]"
                    for p in at_risk[:5]
                ) if at_risk else "  All projects healthy.")
            ),
            "data": result,
            "agent": self.code,
        }

    def _classify_project_intent(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["risk", "over budget", "behind", "late", "problem"]):
            return "at_risk"
        if any(w in q for w in ["all", "overview", "portfolio", "list", "show"]):
            return "overview"
        return "general"


class ExecutiveAgent(BaseAgent):
    """Executive Agent - high-level business intelligence and cross-domain analysis."""

    def run(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "")

        financial = self._execute_tool("get_financial_summary", {}, context)
        projects = self._execute_tool("get_project_health", {}, context)
        procurement = self._execute_tool("get_procurement_analysis", {}, context)
        workflow = self._execute_tool("get_workflow_status", {}, context)
        events = self._execute_tool("get_recent_events", {"limit": 5}, context)

        intent = self._classify_executive_intent(query)

        if intent == "risk_summary":
            at_risk = projects.get("at_risk", [])
            pending = workflow.get("pending_approvals", 0)
            lines = ["Executive Risk Summary:"]
            if at_risk:
                lines.append(f"\n  Projects at Risk ({len(at_risk)}):")
                for p in at_risk:
                    lines.append(f"    - {p['name']}: {p['utilization_pct']}% [{p['risk_level']}]")
            if pending > 0:
                lines.append(f"\n  Pending Approvals: {pending}")
            return {"response": "\n".join(lines), "data": {"financial": financial, "projects": projects, "workflow": workflow}, "agent": self.code}

        if intent == "business_health":
            lines = [
                "Business Health Dashboard:",
                f"\n  Financial: {financial['total_accounts']} accounts, Dr {financial['total_debit']:,} | Cr {financial['total_credit']:,}",
                f"  Projects: {projects['total_projects']} total, {len(projects.get('at_risk', []))} at risk",
                f"  Procurement: {procurement['total_procurements']} orders, {procurement['pending_count']} pending",
                f"  Workflows: {workflow['total_instances']} instances, {workflow['pending_approvals']} approvals pending",
            ]
            return {"response": "\n".join(lines), "data": {"financial": financial, "projects": projects, "procurement": procurement, "workflow": workflow}, "agent": self.code}

        return {
            "response": (
                f"Executive Summary:\n"
                f"  Financial: {financial['total_accounts']} accounts, balanced={'Yes' if financial['is_balanced'] else 'No'}\n"
                f"  Projects: {projects['total_projects']} ({len(projects.get('at_risk', []))} at risk)\n"
                f"  Procurement: {procurement['total_procurements']} ({procurement['pending_count']} pending)\n"
                f"  Approvals: {workflow['pending_approvals']} pending"
            ),
            "data": {"financial": financial, "projects": projects, "procurement": procurement, "workflow": workflow},
            "agent": self.code,
        }

    def _classify_executive_intent(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["risk", "problem", "issue", "alert"]):
            return "risk_summary"
        if any(w in q for w in ["health", "overview", "status", "dashboard", "summary"]):
            return "business_health"
        return "general"


# Agent type registry
BUSINESS_AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "finance": FinanceAgent,
    "procurement": ProcurementAgent,
    "project": ProjectAgent,
    "executive": ExecutiveAgent,
}
