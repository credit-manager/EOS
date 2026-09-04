"""
P53 AI Business Composer Engine
Converts natural language business requirements into ERP configuration.
Generic platform capability — no industry-specific code.
"""
import json
import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# ═══════════════════════════════════════════════════════════
# INDUSTRY DETECTION RULES (keyword → industry)
# ═══════════════════════════════════════════════════════════
INDUSTRY_KEYWORDS = {
    "construction": [
        "construction", "contracting", "building", "civil", "engineer",
        "\u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a", "\u0627\u0644\u0628\u0646\u0627\u0621",
        "\u0627\u0644\u0639\u0645\u0627\u0631\u0629", "\u0627\u0644\u0645\u0634\u0627\u0631\u064a\u0639",
        "\u0627\u0644\u0645\u0642\u0627\u0648\u0644", "\u0628\u0646\u0627\u0621",
        "\u0645\u0642\u0627\u0648\u0644\u0627\u062a", "\u0645\u0634\u0627\u0631\u064a\u0639",
    ],
    "trading": [
        "trading", "distribution", "wholesale", "import", "export",
        "\u0627\u0644\u062a\u062c\u0627\u0631\u0629", "\u0627\u0644\u062a\u0648\u0632\u064a\u0639",
        "\u0627\u0644\u062a\u0633\u0648\u064a\u0642", "\u0627\u0644\u062a\u0633\u062a\u064a\u0631\u0627\u062f",
        "\u0627\u0644\u0627\u0633\u062a\u064a\u0631\u0627\u062f", "\u0627\u0644\u062a\u0635\u062f\u064a\u0631",
        "\u062a\u062c\u0627\u0631\u0629", "\u062a\u0648\u0632\u064a\u0639",
    ],
    "retail": [
        "retail", "store", "shop", "ecommerce", "pos",
        "\u0627\u0644\u062a\u062c\u0632\u0626\u0629", "\u0627\u0644\u0645\u062a\u062c\u0631",
        "\u0627\u0644\u062f\u0643\u0627\u0646", "\u0627\u0644\u0645\u062a\u062c\u0631",
    ],
    "restaurant": [
        "restaurant", "cafe", "food", "catering", "kitchen",
        "\u0627\u0644\u0645\u0637\u0639\u0627\u0645", "\u0627\u0644\u0645\u0637\u0639\u0645\u0627\u062a",
        "\u0627\u0644\u0645\u0627\u0643\u0644", "\u0627\u0644\u0630\u0643\u0627\u0626\u0629",
        "\u0627\u0644\u0637\u0639\u0627\u0645", "\u0627\u0644\u0623\u0643\u0644",
        "\u0645\u0637\u0639\u0645", "\u0645\u0637\u0627\u0639\u0645", "\u0643\u0627\u0641\u064a\u0647",
    ],
    "services": [
        "consulting", "services", "it", "legal", "accounting firm",
        "\u0627\u0644\u062e\u062f\u0645\u0627\u062a", "\u0627\u0644\u0627\u0633\u062a\u0634\u0627\u0631\u0627\u062a",
        "\u0627\u0644\u0627\u0633\u062a\u0634\u0627\u0631\u0627\u062a \u0627\u0644\u0645\u0647\u0646\u064a\u0629",
        "\u0627\u0644\u0645\u0633\u062a\u0634\u0627\u0631\u064a\u0629",
    ],
    "manufacturing": [
        "manufacturing", "production", "factory", "assembly",
        "\u0627\u0644\u062a\u0635\u0646\u064a\u0639", "\u0627\u0644\u0625\u0646\u062a\u0627\u062c",
        "\u0627\u0644\u0645\u0635\u0646\u0639", "\u0627\u0644\u0645\u0639\u062f\u0627\u062a",
    ],
    "tourism": [
        "tourism", "travel", "hotel", "booking", "tour", "reservation",
        "\u0627\u0644\u0633\u064a\u0627\u062d\u0629", "\u0627\u0644\u0633\u0641\u0631", "\u0627\u0644\u0641\u0646\u0627\u062f\u0642", "\u0627\u0644\u062d\u062c\u0648\u0632\u0627\u062a", "\u0627\u0644\u0631\u062d\u0644\u0627\u062a",
        "\u0627\u0644\u0633\u064a\u0627\u062d\u0629 \u0648\u0627\u0644\u0633\u0641\u0631", "\u0648\u0643\u0627\u0644\u0629 \u0633\u0641\u0631", "\u0634\u0631\u0643\u0629 \u0633\u064a\u0627\u062d\u0629",
        "\u062d\u062c\u0632 \u0641\u0646\u062f\u0642\u064a", "\u062d\u062c\u0632 \u0637\u064a\u0631\u0627\u0646", "\u062a\u0623\u0634\u064a\u0631\u0627\u062a", "\u0639\u0645\u0631\u0629", "\u062d\u062c",
    ],
}

# ═══════════════════════════════════════════════════════════
# BUSINESS TERM → MODULE MAPPING
# ═══════════════════════════════════════════════════════════
TERM_MODULE_MAP = {
    "accounting": ["accounting"],
    "accounts": ["accounting"],
    "\u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a": ["accounting"],
    "\u062d\u0633\u0627\u0628\u0627\u062a": ["accounting"],
    "\u0627\u0644\u0645\u062d\u0627\u0633\u0628\u0627\u062a": ["accounting"],
    "finance": ["finance"],
    "bank": ["finance"],
    "treasury": ["finance"],
    "\u0627\u0644\u0645\u0627\u0644\u064a\u0629": ["finance"],
    "\u0627\u0644\u062e\u0632\u064a\u0646\u0629": ["finance"],
    "\u0627\u0644\u0628\u0646\u0648\u0643": ["finance"],
    "procurement": ["procurement"],
    "purchasing": ["procurement"],
    "purchase orders": ["procurement"],
    "suppliers": ["procurement"],
    "\u0627\u0644\u0645\u0634\u062a\u0631\u064a\u0627\u062a": ["procurement"],
    "\u0645\u0634\u062a\u0631\u064a\u0627\u062a": ["procurement"],
    "\u0627\u0644\u0645\u0648\u0631\u062f\u064a\u0646": ["procurement"],
    "\u0645\u0648\u0631\u062f\u064a\u0646": ["procurement"],
    "\u0627\u0644\u0623\u0648\u0627\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621": ["procurement"],
    "inventory": ["inventory"],
    "warehouse": ["inventory"],
    "stock": ["inventory"],
    "\u0627\u0644\u0645\u062e\u0627\u0632\u0646": ["inventory"],
    "\u0645\u062e\u0627\u0632\u0646": ["inventory"],
    "\u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639\u0627\u062a": ["inventory"],
    "\u0627\u0644\u0645\u062e\u0632\u0646": ["inventory"],
    "sales": ["sales"],
    "customers": ["sales"],
    "invoices": ["sales"],
    "\u0627\u0644\u0645\u0628\u064a\u0639\u0627\u062a": ["sales"],
    "\u0645\u0628\u064a\u0639\u0627\u062a": ["sales"],
    "\u0627\u0644\u0639\u0645\u0644\u0627\u0621": ["sales"],
    "\u0627\u0644\u0641\u0648\u0627\u062a\u064a\u0631": ["sales"],
    "hr": ["hr"],
    "human resources": ["hr"],
    "employees": ["hr"],
    "payroll": ["hr"],
    "\u0627\u0644\u0645\u0648\u0627\u0631\u062f \u0627\u0644\u0628\u0634\u0631\u064a\u0629": ["hr"],
    "\u0627\u0644\u0645\u0648\u0637\u0641\u064a\u0646": ["hr"],
    "\u0645\u0648\u0638\u0641\u064a\u0646": ["hr"],
    "\u0627\u0644\u0645\u0648\u0635\u0641\u064a\u0646": ["hr"],
    "\u0627\u0644\u0637\u0627\u0642\u0645": ["hr"],
    "projects": ["projects"],
    "project management": ["projects"],
    "tasks": ["projects"],
    "\u0627\u0644\u0645\u0634\u0627\u0631\u064a\u0639": ["projects"],
    "\u0645\u0634\u0627\u0631\u064a\u0639": ["projects"],
    "\u0627\u0644\u0645\u0647\u0627\u0645": ["projects"],
    "tourism": ["tourism"],
    "travel": ["tourism"],
    "hotels": ["tourism"],
    "bookings": ["tourism"],
    "tours": ["tourism"],
    "\u0627\u0644\u0633\u064a\u0627\u062d\u0629": ["tourism"],
    "\u0627\u0644\u0633\u0641\u0631": ["tourism"],
    "\u0627\u0644\u0641\u0646\u0627\u062f\u0642": ["tourism"],
    "\u0627\u0644\u062d\u062c\u0648\u0632\u0627\u062a": ["tourism"],
    "\u0627\u0644\u0631\u062d\u0644\u0627\u062a": ["tourism"],
    "\u062a\u0623\u0634\u064a\u0631\u0627\u062a": ["tourism"],
    "\u0639\u0645\u0631\u0629": ["tourism"],
    "\u062d\u062c": ["tourism"],
    "documents": ["documents"],
    "\u0627\u0644\u0645\u0633\u062a\u0646\u062f\u0627\u0639\u0627\u062a": ["documents"],
    "workflow": ["workflow"],
    "approvals": ["workflow"],
    "e-signature": ["workflow"],
    "\u0627\u0644\u0645\u0648\u0627\u0641\u0642\u0627\u062a": ["workflow"],
    "\u0645\u0648\u0627\u0641\u0642\u0627\u062a": ["workflow"],
    "\u0627\u0644\u062a\u0635\u0631\u064a\u062d": ["workflow"],
    "fixed assets": ["fixed_assets"],
    "assets": ["fixed_assets"],
    "\u0627\u0644\u0623\u0635\u0648\u0644 \u0627\u0644\u062b\u0627\u0628\u062a\u0629": ["fixed_assets"],
    "audit": ["audit"],
    "compliance": ["audit"],
    "\u0627\u0644\u062a\u062f\u0642\u0642": ["audit"],
    "bi": ["bi"],
    "reporting": ["bi"],
    "dashboard": ["bi"],
    "\u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631": ["bi"],
    "\u0627\u0644\u0644\u062d\u0635\u0627\u062a": ["bi"],
}

# ═══════════════════════════════════════════════════════════
# MODULE → ENTITIES MAPPING
# ═══════════════════════════════════════════════════════════
MODULE_ENTITIES = {
    "accounting": ["accounts", "journal_entries", "trial_balance"],
    "finance": ["bank_accounts", "payments", "budgets"],
    "procurement": ["suppliers", "purchase_requests", "purchase_orders", "grn"],
    "inventory": ["items", "warehouses", "stock_movements"],
    "sales": ["customers", "quotations", "sales_orders", "invoices"],
    "hr": ["employees", "leave_requests", "attendance", "payroll"],
    "projects": ["projects", "tasks", "milestones", "time_entries"],
    "tourism": ["tour_packages", "bookings", "hotels", "flights", "passengers", "visas", "guides", "transfers"],
    "documents": ["folders", "documents", "versions"],
    "workflow": ["approval_templates", "delegations"],
    "fixed_assets": ["assets", "depreciation"],
    "audit": ["audit_trail", "compliance_rules", "access_logs"],
    "bi": ["dashboards", "reports", "kpis"],
}

# ═══════════════════════════════════════════════════════════
# MODULE → WORKFLOWS MAPPING
# ═══════════════════════════════════════════════════════════
MODULE_WORKFLOWS = {
    "procurement": [
        {"name": "Purchase Request Approval", "trigger": "purchase_request_created",
         "steps": ["department_manager", "finance_approver"]},
        {"name": "PO Approval", "trigger": "purchase_order_created",
         "steps": ["procurement_manager", "finance_manager"]},
    ],
    "sales": [
        {"name": "Quotation Approval", "trigger": "quotation_created",
         "steps": ["sales_manager"]},
        {"name": "Invoice Approval", "trigger": "invoice_above_threshold",
         "steps": ["finance_manager"]},
    ],
    "hr": [
        {"name": "Leave Request", "trigger": "leave_request_created",
         "steps": ["direct_manager", "hr_manager"]},
        {"name": "Payroll Approval", "trigger": "payroll_run_created",
         "steps": ["hr_manager", "finance_manager"]},
    ],
    "projects": [
        {"name": "Project Closure", "trigger": "project_completion",
         "steps": ["project_manager", "general_manager"]},
    ],
    "workflow": [
        {"name": "Generic Approval", "trigger": "entity_created",
         "steps": ["approver"]},
    ],
}

# ═══════════════════════════════════════════════════════════
# MODULE → ROLES & PERMISSIONS
# ═══════════════════════════════════════════════════════════
MODULE_ROLES = {
    "accounting": {"viewer": ["read"], "accountant": ["read", "create", "update"], "controller": ["*"]},
    "finance": {"viewer": ["read"], "treasurer": ["read", "create", "update"], "cfo": ["*"]},
    "procurement": {"viewer": ["read"], "buyer": ["read", "create", "update"], "procurement_manager": ["*"]},
    "inventory": {"viewer": ["read"], "warehouse_keeper": ["read", "create", "update"], "inventory_manager": ["*"]},
    "sales": {"viewer": ["read"], "sales_rep": ["read", "create", "update"], "sales_manager": ["*"]},
    "hr": {"viewer": ["read"], "hr_staff": ["read", "create", "update"], "hr_manager": ["*"]},
    "projects": {"viewer": ["read"], "team_member": ["read", "create"], "project_manager": ["*"]},
    "documents": {"viewer": ["read"], "contributor": ["read", "create"], "admin": ["*"]},
    "workflow": {"requester": ["create"], "approver": ["read", "update"], "admin": ["*"]},
    "audit": {"viewer": ["read"], "auditor": ["read", "create"], "compliance_officer": ["*"]},
    "bi": {"viewer": ["read"], "analyst": ["read", "create"], "admin": ["*"]},
    "fixed_assets": {"viewer": ["read"], "asset_manager": ["read", "create", "update"], "admin": ["*"]},
}

# ═══════════════════════════════════════════════════════════
# MODULE → DASHBOARD KPIs
# ═══════════════════════════════════════════════════════════
MODULE_KPIS = {
    "accounting": [
        {"name": "Total Revenue", "metric": "revenue", "aggregation": "SUM"},
        {"name": "Total Expenses", "metric": "expenses", "aggregation": "SUM"},
        {"name": "Net Profit", "metric": "net_profit", "aggregation": "CALCULATED"},
    ],
    "finance": [
        {"name": "Cash Balance", "metric": "cash_balance", "aggregation": "SUM"},
        {"name": "Bank Balance", "metric": "bank_balance", "aggregation": "SUM"},
    ],
    "procurement": [
        {"name": "Open POs", "metric": "open_pos", "aggregation": "COUNT"},
        {"name": "PO Value", "metric": "po_value", "aggregation": "SUM"},
    ],
    "inventory": [
        {"name": "Stock Value", "metric": "stock_value", "aggregation": "SUM"},
        {"name": "Low Stock Items", "metric": "low_stock", "aggregation": "COUNT"},
    ],
    "sales": [
        {"name": "Revenue", "metric": "sales_revenue", "aggregation": "SUM"},
        {"name": "Open Invoices", "metric": "open_invoices", "aggregation": "COUNT"},
        {"name": "Top Customers", "metric": "customer_revenue", "aggregation": "SUM", "group_by": "customer"},
    ],
    "hr": [
        {"name": "Total Employees", "metric": "employee_count", "aggregation": "COUNT"},
        {"name": "Leave Balance", "metric": "leave_days", "aggregation": "SUM"},
    ],
    "projects": [
        {"name": "Active Projects", "metric": "active_projects", "aggregation": "COUNT"},
        {"name": "Project Budget Utilization", "metric": "budget_used", "aggregation": "AVG"},
    ],
    "bi": [
        {"name": "Data Quality Score", "metric": "data_quality", "aggregation": "AVG"},
    ],
}

# ═══════════════════════════════════════════════════════════
# CORE MODULES — always included in any ERP configuration
# (matches all P52 industry templates: accounting + finance)
# ═══════════════════════════════════════════════════════════
CORE_MODULES = {"accounting", "finance"}

# ═══════════════════════════════════════════════════════════
# MODULE DEPENDENCIES
# ═══════════════════════════════════════════════════════════
MODULE_DEPENDENCIES = {
    "finance": ["accounting"],
    "procurement": ["accounting"],
    "sales": ["accounting"],
    "hr": ["accounting"],
    "fixed_assets": ["accounting"],
    "audit": ["accounting"],
}

# ═══════════════════════════════════════════════════════════
# ARABIC NORMALIZATION — strip conjunctions/articles so that
# "ومشتريات" matches "المشتريات"/"مشتريات", "والفروع" → "فروع"...
# ═══════════════════════════════════════════════════════════
ARABIC_STRIP_PREFIXES = ("\u0648\u0627\u0644", "\u0641\u0627\u0644", "\u0628\u0627\u0644",
                          "\u0643\u0627\u0644", "\u0644\u0644", "\u0627\u0644")


def normalize_arabic(text_input: str) -> str:
    """Return original text plus stripped word stems appended, for robust matching."""
    extra = []
    for raw in text_input.split():
        w = raw.strip("\u060c.,:;\u061b()!?\")(")
        if not w:
            continue
        stem = w
        changed = False
        for pre in ARABIC_STRIP_PREFIXES:
            if stem.startswith(pre) and len(stem) >= len(pre) + 3:
                stem = stem[len(pre):]
                changed = True
                break
        if not changed and len(w) > 3 and w[0] in "\u0648\u0641\u0628\u0643\u0644":
            stem = w[1:]
            changed = True
        if changed and stem:
            extra.append(stem)
    return text_input + (" " + " ".join(extra) if extra else "")


# ═══════════════════════════════════════════════════════════
# LANGUAGE DETECTION
# ═══════════════════════════════════════════════════════════
def detect_language(text_input: str) -> str:
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text_input))
    return "ar" if arabic_chars > len(text_input) * 0.2 else "en"


# ═══════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════
class AIComposerEngine:
    def __init__(self, db: Session):
        self.db = db

    # ── 1. PARSE NATURAL LANGUAGE ──

    def parse_requirements(self, user_input: str) -> dict[str, Any]:
        lang = detect_language(user_input)
        normalized = normalize_arabic(user_input)
        lower = normalized.lower()

        industry = self._detect_industry(lower)
        modules = self._extract_modules(lower)
        branches = self._extract_number(lower, ["branch", "branches", "\u0641\u0631\u0639", "\u0641\u0631\u0648\u0639"])
        employees = self._extract_number(lower, ["employee", "employees", "\u0645\u0648\u0638\u0641", "\u0645\u0648\u0627\u0635\u0641"])
        needs_projects = any(t in lower for t in ["project", "\u0645\u0634\u0631\u0648\u0639", "\u0645\u0634\u0627\u0631\u064a\u0639"])
        needs_workflow = any(t in lower for t in ["approval", "workflow", "\u0645\u0648\u0627\u0641\u0642", "\u062a\u0635\u0631\u064a\u062d"])
        currency = self._extract_currency(lower)

        return {
            "language": lang,
            "industry": industry,
            "modules": modules,
            "branches": branches or 1,
            "employees": employees or 10,
            "needs_projects": needs_projects,
            "needs_workflow": needs_workflow,
            "currency": currency or "SAR",
            "raw_input": user_input,
        }

    def _detect_industry(self, text_lower: str) -> str:
        scores = {}
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[industry] = score
        if scores:
            return max(scores, key=scores.get)
        return "services"

    def _extract_modules(self, text_lower: str) -> list[str]:
        found = set()
        for term, modules in TERM_MODULE_MAP.items():
            if term in text_lower:
                for m in modules:
                    found.add(m)
        # Core modules: every ERP needs GL (accounting) + Treasury (finance)
        found.update(CORE_MODULES)
        return sorted(found)

    def _extract_number(self, text_lower: str, keywords: list[str]) -> int | None:
        words = text_lower.split()
        for kw in keywords:
            for i, w in enumerate(words):
                if kw in w and i > 0:
                    try:
                        return int(words[i - 1].replace(",", ""))
                    except ValueError:
                        pass
        return None

    def _extract_currency(self, text_lower: str) -> str | None:
        currencies = {"sar": "SAR", "usd": "USD", "eur": "EUR", "egp": "EGP",
                       "\u0631\u064a\u0627\u0644": "SAR", "\u062f\u0648\u0644\u0627\u0631": "USD"}
        for key, code in currencies.items():
            if key in text_lower:
                return code
        return None

    # ── 2. GENERATE CONFIGURATION ──

    def generate_config(self, requirements: dict) -> dict[str, Any]:
        modules = requirements["modules"]
        industry = requirements["industry"]

        all_entities = []
        all_workflows = []
        all_roles = {}
        all_permissions = []
        all_kpis = []
        all_accounts = []

        for mod in modules:
            all_entities.extend(MODULE_ENTITIES.get(mod, []))
            all_workflows.extend(MODULE_WORKFLOWS.get(mod, []))
            for role, perms in MODULE_ROLES.get(mod, {}).items():
                all_roles[role] = perms
            all_kpis.extend(MODULE_KPIS.get(mod, []))

        template_accounts = self._get_template_accounts(industry)
        all_accounts = template_accounts

        for role, perms in all_roles.items():
            for perm in perms:
                all_permissions.append({"role": role, "permission": perm})

        relationships = self._infer_relationships(modules)

        config = {
            "industry": industry,
            "modules": modules,
            "entities": all_entities,
            "relationships": relationships,
            "workflows": all_workflows,
            "roles": all_roles,
            "permissions": all_permissions,
            "kpis": all_kpis,
            "accounts": all_accounts,
            "settings": {
                "currency": requirements.get("currency", "SAR"),
                "branches": requirements.get("branches", 1),
                "employees": requirements.get("employees", 10),
            },
        }
        return config

    def _get_template_accounts(self, industry: str) -> list[dict]:
        from core.onboarding_engine import OnboardingEngine
        oe = OnboardingEngine(self.db)
        accounts = oe.get_industry_accounts(industry)
        if accounts:
            return accounts
        return [
            {"code": "1000", "name": "Cash", "account_type": "asset"},
            {"code": "1100", "name": "Bank Account", "account_type": "asset"},
            {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
            {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
            {"code": "4000", "name": "Revenue", "account_type": "revenue"},
            {"code": "5000", "name": "Expenses", "account_type": "expense"},
        ]

    def _infer_relationships(self, modules: list[str]) -> list[dict]:
        rels = []
        if "sales" in modules and "accounting" in modules:
            rels.append({"from": "invoices", "to": "accounts", "type": "journal_entry"})
        if "procurement" in modules and "accounting" in modules:
            rels.append({"from": "purchase_orders", "to": "accounts", "type": "journal_entry"})
        if "procurement" in modules and "inventory" in modules:
            rels.append({"from": "grn", "to": "stock_movements", "type": "stock_update"})
        if "inventory" in modules and "sales" in modules:
            rels.append({"from": "sales_orders", "to": "stock_movements", "type": "stock_issue"})
        if "hr" in modules and "accounting" in modules:
            rels.append({"from": "payroll", "to": "journal_entries", "type": "auto_post"})
        if "projects" in modules and "hr" in modules:
            rels.append({"from": "time_entries", "to": "projects", "type": "cost_tracking"})
        if "documents" in modules:
            rels.append({"from": "documents", "to": "entities", "type": "attachment"})
        return rels

    # ── 3. VALIDATE CONFIGURATION ──

    def validate_config(self, config: dict) -> dict[str, Any]:
        errors = []
        warnings = []
        modules = config.get("modules", [])

        for mod, deps in MODULE_DEPENDENCIES.items():
            if mod in modules:
                for dep in deps:
                    if dep not in modules:
                        errors.append(f"Module '{mod}' requires '{dep}'")

        if "procurement" in modules and "inventory" in modules:
            pass
        elif "procurement" in modules:
            warnings.append("Procurement without Inventory: stock tracking disabled")
        elif "inventory" in modules:
            warnings.append("Inventory without Procurement: no auto-PO creation")

        if not config.get("accounts"):
            errors.append("No chart of accounts defined")
        if not config.get("entities"):
            warnings.append("No entities configured — default entities will be used")

        all_roles = set(config.get("roles", {}).keys())
        for wf in config.get("workflows", []):
            for step in wf.get("steps", []):
                if step not in all_roles:
                    warnings.append(f"Workflow '{wf['name']}' references role '{step}' not in roles")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "modules_count": len(modules),
            "entities_count": len(config.get("entities", [])),
            "relationships_count": len(config.get("relationships", [])),
            "workflows_count": len(config.get("workflows", [])),
            "roles_count": len(config.get("roles", {})),
            "permissions_count": len(config.get("permissions", [])),
            "kpis_count": len(config.get("kpis", [])),
            "accounts_count": len(config.get("accounts", [])),
        }

    # ── 4. PREVIEW ──

    def generate_preview(self, config: dict, validation: dict) -> dict[str, Any]:
        return {
            "modules": config["modules"],
            "entities": config["entities"],
            "relationships": config["relationships"],
            "workflows": config["workflows"],
            "roles": list(config["roles"].keys()),
            "permissions_count": validation["permissions_count"],
            "kpis": [k["name"] for k in config.get("kpis", [])],
            "accounts_count": validation["accounts_count"],
            "settings": config["settings"],
            "summary": {
                "total_modules": validation["modules_count"],
                "total_entities": validation["entities_count"],
                "total_relationships": validation["relationships_count"],
                "total_workflows": validation["workflows_count"],
                "total_roles": validation["roles_count"],
                "total_permissions": validation["permissions_count"],
                "total_kpis": validation["kpis_count"],
                "total_accounts": validation["accounts_count"],
            },
            "validation": validation,
        }

    # ── 5. SESSION MANAGEMENT ──

    def create_session(self, tenant_id: str, user_id: str, user_input: str) -> dict[str, Any]:
        sid = str(uuid.uuid4())
        requirements = self.parse_requirements(user_input)
        config = self.generate_config(requirements)
        validation = self.validate_config(config)
        preview = self.generate_preview(config, validation)

        self.db.execute(text(
            "INSERT INTO dbp_composer_sessions "
            "(id, tenant_id, user_id, natural_language_input, detected_industry, "
            "detected_language, parsed_requirements, generated_config, status, preview_data) "
            "VALUES (:id, :tid, :uid, :input, :ind, :lang, :req, :cfg, :st, :prev)"
        ), {
            "id": sid, "tid": tenant_id, "uid": user_id,
            "input": user_input, "ind": requirements["industry"],
            "lang": requirements["language"],
            "req": json.dumps(requirements), "cfg": json.dumps(config),
            "st": "preview", "prev": json.dumps(preview),
        })
        self.db.flush()
        return {"session_id": sid, "requirements": requirements, "config": config,
                "validation": validation, "preview": preview}

    def get_session(self, session_id: str, tenant_id: str | None = None) -> dict | None:
        """
        Get composer session by ID.
        
        SECURITY FIX (P0): Added tenant_id parameter to enforce multi-tenancy isolation.
        Prevents IDOR vulnerability where knowing a session_id could allow access
        to another tenant's session data.
        
        Args:
            session_id: The session UUID
            tenant_id: Optional tenant ID for isolation check (recommended)
        
        Returns:
            Session dict or None if not found/access denied
        """
        if tenant_id:
            # Enforce tenant isolation - critical security fix
            row = self.db.execute(text(
                "SELECT id, tenant_id, user_id, natural_language_input, detected_industry, "
                "detected_language, parsed_requirements, generated_config, status, preview_data, "
                "approved_by, approved_at, activated_at, activation_result, error_message, "
                "created_at, updated_at "
                "FROM dbp_composer_sessions WHERE id = :sid AND tenant_id = :tid"
            ), {"sid": session_id, "tid": tenant_id}).fetchone()
        else:
            # Fallback without tenant check (not recommended for production)
            row = self.db.execute(text(
                "SELECT id, tenant_id, user_id, natural_language_input, detected_industry, "
                "detected_language, parsed_requirements, generated_config, status, preview_data, "
                "approved_by, approved_at, activated_at, activation_result, error_message, "
                "created_at, updated_at "
                "FROM dbp_composer_sessions WHERE id = :sid"
            ), {"sid": session_id}).fetchone()
        
        if not row:
            return None
        return self._row_to_dict(row)

    def approve_session(self, session_id: str, approved_by: str, tenant_id: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id, tenant_id=tenant_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        if session["status"] != "preview":
            return {"success": False, "error": f"Cannot approve session in '{session['status']}' status"}

        self.db.execute(text(
            "UPDATE dbp_composer_sessions SET status='approved', "
            "approved_by = :ab, approved_at = NOW(), updated_at = NOW() WHERE id = :sid"
        ), {"ab": approved_by, "sid": session_id})
        self.db.flush()
        return {"success": True, "status": "approved"}

    def activate_session(self, session_id: str, tenant_id: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id, tenant_id=tenant_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        if session["status"] != "approved":
            return {"success": False, "error": f"Cannot activate session in '{session['status']}' status"}

        config = session.get("generated_config", {})
        activated_modules = config.get("modules", [])
        activated_entities = config.get("entities", [])

        result = {
            "modules_activated": activated_modules,
            "entities_configured": len(activated_entities),
            "workflows_created": len(config.get("workflows", [])),
            "roles_configured": len(config.get("roles", {})),
            "accounts_created": len(config.get("accounts", [])),
            "kpis_configured": len(config.get("kpis", [])),
        }

        self.db.execute(text(
            "UPDATE dbp_composer_sessions SET status='activated', "
            "activated_at = NOW(), activation_result = :ar, updated_at = NOW() WHERE id = :sid"
        ), {"ar": json.dumps(result), "sid": session_id})
        self.db.flush()
        return {"success": True, "status": "activated", "result": result}

    def list_sessions(self, tenant_id: str, status: str | None = None,
                      limit: int = 50) -> list[dict]:
        conditions = ["tenant_id = :tid"]
        params: dict[str, Any] = {"tid": tenant_id, "lim": limit}
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = f"WHERE {' AND '.join(conditions)}"
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, user_id, detected_industry, status, "
            f"natural_language_input, created_at, activated_at "
            f"FROM dbp_composer_sessions {where} ORDER BY created_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "user_id": r[2],
                 "industry": r[3], "status": r[4],
                 "input": r[5][:100] if r[5] else None,
                 "created_at": str(r[6]) if r[6] else None,
                 "activated_at": str(r[7]) if r[7] else None} for r in rows]

    # ── HELPERS ──

    def _row_to_dict(self, row) -> dict:
        def p(v):
            if v is None:
                return {}
            if isinstance(v, (dict, list)):
                return v
            try:
                return json.loads(v)
            except Exception:
                return v

        return {
            "id": row[0], "tenant_id": row[1], "user_id": row[2],
            "natural_language_input": row[3], "detected_industry": row[4],
            "detected_language": row[5], "parsed_requirements": p(row[6]),
            "generated_config": p(row[7]), "status": row[8],
            "preview_data": p(row[9]),
            "approved_by": row[10],
            "approved_at": str(row[11]) if row[11] else None,
            "activated_at": str(row[12]) if row[12] else None,
            "activation_result": p(row[13]),
            "error_message": row[14],
            "created_at": str(row[15]) if row[15] else None,
            "updated_at": str(row[16]) if row[16] else None,
        }
