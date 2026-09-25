"""Registry of Business Object configurations -- pre-built + user-defined."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .business_object import (
    BusinessObjectConfig,
    EntityAIConfig,
    EntityAnalyticsConfig,
    EntityDocumentConfig,
    EntityFinancialConfig,
    EntityPermissionConfig,
    EntityRuleConfig,
    EntityWorkflowConfig,
    RelationshipConfig,
)

logger = logging.getLogger("2to-eos.metadata.registry")


_PREBUILT_CUSTOMER = BusinessObjectConfig(
    entity_code="customer",
    entity_name="Customer",
    description="Customer master data",
    fields=[
        {"code": "name", "name": "Name", "type": "text", "required": True},
        {"code": "email", "name": "Email", "type": "email"},
        {"code": "phone", "name": "Phone", "type": "phone"},
        {"code": "address", "name": "Address", "type": "text"},
        {"code": "credit_limit", "name": "Credit Limit", "type": "currency"},
        {"code": "status", "name": "Status", "type": "select", "options": ["active", "inactive", "blocked"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="invoice", relation_type="one_to_many", foreign_key="customer_id", label="Invoices"),
        RelationshipConfig(target_entity="payment", relation_type="one_to_many", foreign_key="customer_id", label="Payments"),
        RelationshipConfig(target_entity="contract", relation_type="one_to_many", foreign_key="customer_id", label="Contracts"),
        RelationshipConfig(target_entity="opportunity", relation_type="one_to_many", foreign_key="customer_id", label="Opportunities"),
    ],
    rules=[
        EntityRuleConfig(
            rule_id="customer_credit_check",
            event_type="on_status_change",
            condition="credit_limit > 100000",
            action="require_approval",
            params={"approver_role": "finance_manager"},
        ),
    ],
    permissions=EntityPermissionConfig(
        roles={
            "admin": ["create", "read", "update", "delete", "approve"],
            "sales_manager": ["create", "read", "update", "approve"],
            "sales_rep": ["create", "read", "update"],
            "viewer": ["read"],
        },
    ),
    workflow=EntityWorkflowConfig(
        states=["draft", "pending_approval", "active", "inactive", "blocked"],
        initial_state="draft",
        transitions=[
            {"from": "draft", "to": "pending_approval", "actor": "owner", "condition": None},
            {"from": "pending_approval", "to": "active", "actor": "approver", "condition": None},
            {"from": "active", "to": "inactive", "actor": "owner", "condition": None},
            {"from": "active", "to": "blocked", "actor": "admin", "condition": "credit_exceeded"},
            {"from": "inactive", "to": "active", "actor": "owner", "condition": None},
        ],
        approval_required=True,
        approvers=["finance_manager", "admin"],
    ),
    financial=EntityFinancialConfig(
        has_financial_impact=True,
        posting_rules=[
            {"debit": "accounts_receivable", "credit": "revenue", "trigger": "invoice.approved"},
        ],
        amount_field="credit_limit",
    ),
    analytics=EntityAnalyticsConfig(
        kpis=[
            {"code": "total_revenue", "formula": "SUM(invoices.amount)", "group_by": "quarter"},
            {"code": "outstanding_balance", "formula": "SUM(invoices.amount) - SUM(payments.amount)"},
        ],
        dashboards=["sales_dashboard"],
        drill_down_enabled=True,
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True, summarizable=True, auto_classify=True),
)


_PREBUILT_SUPPLIER = BusinessObjectConfig(
    entity_code="supplier",
    entity_name="Supplier",
    description="Supplier / vendor master data",
    fields=[
        {"code": "name", "name": "Name", "type": "text", "required": True},
        {"code": "email", "name": "Email", "type": "email"},
        {"code": "phone", "name": "Phone", "type": "phone"},
        {"code": "address", "name": "Address", "type": "text"},
        {"code": "tax_id", "name": "Tax ID", "type": "text"},
        {"code": "payment_terms", "name": "Payment Terms", "type": "select", "options": ["net_30", "net_60", "cod"]},
        {"code": "status", "name": "Status", "type": "select", "options": ["active", "inactive", "blocked"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="purchase_order", relation_type="one_to_many", foreign_key="supplier_id", label="Purchase Orders"),
        RelationshipConfig(target_entity="contract", relation_type="one_to_many", foreign_key="supplier_id", label="Contracts"),
    ],
    permissions=EntityPermissionConfig(),
    workflow=EntityWorkflowConfig(
        states=["draft", "pending_approval", "active", "inactive"],
        initial_state="draft",
        transitions=[
            {"from": "draft", "to": "pending_approval", "actor": "owner", "condition": None},
            {"from": "pending_approval", "to": "active", "actor": "approver", "condition": None},
            {"from": "active", "to": "inactive", "actor": "admin", "condition": None},
        ],
        approval_required=True,
        approvers=["procurement_manager"],
    ),
    analytics=EntityAnalyticsConfig(
        kpis=[{"code": "total_spend", "formula": "SUM(purchase_orders.total)", "group_by": "quarter"}],
    ),
    ai=EntityAIConfig(searchable=True, summarizable=True),
)


_PREBUILT_PROJECT = BusinessObjectConfig(
    entity_code="project",
    entity_name="Project",
    description="Project management entity",
    fields=[
        {"code": "name", "name": "Name", "type": "text", "required": True},
        {"code": "description", "name": "Description", "type": "rich_text"},
        {"code": "start_date", "name": "Start Date", "type": "date"},
        {"code": "end_date", "name": "End Date", "type": "date"},
        {"code": "budget", "name": "Budget", "type": "currency"},
        {"code": "spent", "name": "Spent", "type": "currency"},
        {"code": "status", "name": "Status", "type": "select", "options": ["planning", "active", "on_hold", "completed", "cancelled"]},
        {"code": "priority", "name": "Priority", "type": "select", "options": ["low", "medium", "high", "critical"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="employee", relation_type="many_to_many", foreign_key="project_members", label="Team Members"),
        RelationshipConfig(target_entity="task", relation_type="one_to_many", foreign_key="project_id", label="Tasks"),
        RelationshipConfig(target_entity="invoice", relation_type="one_to_many", foreign_key="project_id", label="Invoices"),
    ],
    rules=[
        EntityRuleConfig(
            rule_id="project_budget_alert",
            event_type="on_update",
            condition="spent > budget * 0.9",
            action="notify",
            params={"channel": "finance", "message": "Project budget 90% consumed"},
        ),
    ],
    permissions=EntityPermissionConfig(
        roles={
            "admin": ["create", "read", "update", "delete", "approve"],
            "project_manager": ["create", "read", "update", "approve"],
            "member": ["read", "update"],
            "viewer": ["read"],
        },
    ),
    workflow=EntityWorkflowConfig(
        states=["planning", "active", "on_hold", "completed", "cancelled"],
        initial_state="planning",
        transitions=[
            {"from": "planning", "to": "active", "actor": "project_manager", "condition": None},
            {"from": "active", "to": "on_hold", "actor": "project_manager", "condition": None},
            {"from": "on_hold", "to": "active", "actor": "project_manager", "condition": None},
            {"from": "active", "to": "completed", "actor": "project_manager", "condition": "all_tasks_done"},
            {"from": "active", "to": "cancelled", "actor": "admin", "condition": None},
        ],
    ),
    financial=EntityFinancialConfig(has_financial_impact=True, amount_field="budget", tax_applicable=False),
    analytics=EntityAnalyticsConfig(
        kpis=[
            {"code": "budget_utilization", "formula": "spent / budget * 100", "group_by": "status"},
            {"code": "task_completion", "formula": "completed_tasks / total_tasks * 100"},
        ],
        dashboards=["project_dashboard"],
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True, summarizable=True, suggested_actions=True),
)


_PREBUILT_INVOICE = BusinessObjectConfig(
    entity_code="invoice",
    entity_name="Invoice",
    description="Sales invoice",
    fields=[
        {"code": "invoice_number", "name": "Invoice Number", "type": "text", "required": True},
        {"code": "customer_id", "name": "Customer", "type": "relation", "target_entity": "customer"},
        {"code": "issue_date", "name": "Issue Date", "type": "date", "required": True},
        {"code": "due_date", "name": "Due Date", "type": "date", "required": True},
        {"code": "subtotal", "name": "Subtotal", "type": "currency"},
        {"code": "tax_amount", "name": "Tax Amount", "type": "currency"},
        {"code": "total", "name": "Total", "type": "currency"},
        {"code": "status", "name": "Status", "type": "select", "options": ["draft", "sent", "paid", "overdue", "cancelled"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="customer", relation_type="many_to_one", foreign_key="customer_id", label="Customer", required=True),
        RelationshipConfig(target_entity="payment", relation_type="one_to_many", foreign_key="invoice_id", label="Payments"),
    ],
    rules=[
        EntityRuleConfig(
            rule_id="invoice_overdue_check",
            event_type="on_status_change",
            condition="due_date < TODAY() AND status != 'paid'",
            action="set_field",
            params={"field": "status", "value": "overdue"},
        ),
    ],
    permissions=EntityPermissionConfig(
        roles={
            "admin": ["create", "read", "update", "delete", "approve"],
            "accountant": ["create", "read", "update"],
            "viewer": ["read"],
        },
    ),
    workflow=EntityWorkflowConfig(
        states=["draft", "sent", "paid", "overdue", "cancelled"],
        initial_state="draft",
        transitions=[
            {"from": "draft", "to": "sent", "actor": "accountant", "condition": None},
            {"from": "sent", "to": "paid", "actor": "system", "condition": "payment_received"},
            {"from": "sent", "to": "overdue", "actor": "system", "condition": "past_due_date"},
            {"from": "draft", "to": "cancelled", "actor": "admin", "condition": None},
        ],
    ),
    documents=EntityDocumentConfig(document_types=["invoice", "receipt"], required=False, ocr_enabled=True),
    financial=EntityFinancialConfig(
        has_financial_impact=True,
        posting_rules=[
            {"debit": "accounts_receivable", "credit": "revenue", "trigger": "invoice.sent"},
            {"debit": "cash", "credit": "accounts_receivable", "trigger": "invoice.paid"},
        ],
        currency_field="currency",
        amount_field="total",
        tax_applicable=True,
    ),
    analytics=EntityAnalyticsConfig(
        kpis=[
            {"code": "total_invoiced", "formula": "SUM(total)", "group_by": "month"},
            {"code": "avg_invoice_value", "formula": "AVG(total)"},
        ],
        dashboards=["finance_dashboard"],
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True, summarizable=True, auto_classify=True),
)


_PREBUILT_PURCHASE_ORDER = BusinessObjectConfig(
    entity_code="purchase_order",
    entity_name="Purchase Order",
    description="Purchase order to suppliers",
    fields=[
        {"code": "po_number", "name": "PO Number", "type": "text", "required": True},
        {"code": "supplier_id", "name": "Supplier", "type": "relation", "target_entity": "supplier"},
        {"code": "order_date", "name": "Order Date", "type": "date", "required": True},
        {"code": "expected_delivery", "name": "Expected Delivery", "type": "date"},
        {"code": "subtotal", "name": "Subtotal", "type": "currency"},
        {"code": "tax_amount", "name": "Tax Amount", "type": "currency"},
        {"code": "total", "name": "Total", "type": "currency"},
        {"code": "status", "name": "Status", "type": "select", "options": ["draft", "pending_approval", "approved", "sent", "received", "cancelled"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="supplier", relation_type="many_to_one", foreign_key="supplier_id", label="Supplier", required=True),
        RelationshipConfig(target_entity="invoice", relation_type="one_to_many", foreign_key="po_id", label="Invoices"),
    ],
    rules=[
        EntityRuleConfig(
            rule_id="po_approval_required",
            event_type="on_submit",
            condition="total > 10000",
            action="require_approval",
            params={"approver_role": "procurement_manager"},
        ),
    ],
    permissions=EntityPermissionConfig(
        roles={
            "admin": ["create", "read", "update", "delete", "approve"],
            "procurement_manager": ["create", "read", "update", "approve"],
            "procurement_staff": ["create", "read", "update"],
            "viewer": ["read"],
        },
    ),
    workflow=EntityWorkflowConfig(
        states=["draft", "pending_approval", "approved", "sent", "received", "cancelled"],
        initial_state="draft",
        transitions=[
            {"from": "draft", "to": "pending_approval", "actor": "owner", "condition": None},
            {"from": "pending_approval", "to": "approved", "actor": "approver", "condition": None},
            {"from": "approved", "to": "sent", "actor": "procurement_staff", "condition": None},
            {"from": "sent", "to": "received", "actor": "system", "condition": "goods_received"},
            {"from": "draft", "to": "cancelled", "actor": "admin", "condition": None},
        ],
        approval_required=True,
        approvers=["procurement_manager"],
    ),
    documents=EntityDocumentConfig(document_types=["purchase_order", "delivery_note", "receipt"]),
    financial=EntityFinancialConfig(
        has_financial_impact=True,
        posting_rules=[
            {"debit": "inventory", "credit": "accounts_payable", "trigger": "po.received"},
        ],
        amount_field="total",
        tax_applicable=True,
    ),
    analytics=EntityAnalyticsConfig(
        kpis=[{"code": "total_purchases", "formula": "SUM(total)", "group_by": "quarter"}],
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True),
)


_PREBUILT_PAYMENT = BusinessObjectConfig(
    entity_code="payment",
    entity_name="Payment",
    description="Payment transactions",
    fields=[
        {"code": "payment_number", "name": "Payment Number", "type": "text", "required": True},
        {"code": "customer_id", "name": "Customer", "type": "relation", "target_entity": "customer"},
        {"code": "invoice_id", "name": "Invoice", "type": "relation", "target_entity": "invoice"},
        {"code": "amount", "name": "Amount", "type": "currency", "required": True},
        {"code": "payment_date", "name": "Payment Date", "type": "date", "required": True},
        {"code": "method", "name": "Method", "type": "select", "options": ["bank_transfer", "credit_card", "cash", "check"]},
        {"code": "status", "name": "Status", "type": "select", "options": ["pending", "completed", "failed", "refunded"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="customer", relation_type="many_to_one", foreign_key="customer_id", label="Customer"),
        RelationshipConfig(target_entity="invoice", relation_type="many_to_one", foreign_key="invoice_id", label="Invoice"),
    ],
    permissions=EntityPermissionConfig(),
    workflow=EntityWorkflowConfig(
        states=["pending", "completed", "failed", "refunded"],
        initial_state="pending",
        transitions=[
            {"from": "pending", "to": "completed", "actor": "system", "condition": "payment_confirmed"},
            {"from": "pending", "to": "failed", "actor": "system", "condition": "payment_declined"},
            {"from": "completed", "to": "refunded", "actor": "admin", "condition": None},
        ],
    ),
    financial=EntityFinancialConfig(
        has_financial_impact=True,
        posting_rules=[
            {"debit": "cash", "credit": "accounts_receivable", "trigger": "payment.completed"},
        ],
        amount_field="amount",
    ),
    analytics=EntityAnalyticsConfig(
        kpis=[{"code": "total_collected", "formula": "SUM(amount)", "group_by": "month"}],
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True),
)


_PREBUILT_CONTRACT = BusinessObjectConfig(
    entity_code="contract",
    entity_name="Contract",
    description="Business contracts and agreements",
    fields=[
        {"code": "title", "name": "Title", "type": "text", "required": True},
        {"code": "customer_id", "name": "Customer", "type": "relation", "target_entity": "customer"},
        {"code": "supplier_id", "name": "Supplier", "type": "relation", "target_entity": "supplier"},
        {"code": "start_date", "name": "Start Date", "type": "date", "required": True},
        {"code": "end_date", "name": "End Date", "type": "date"},
        {"code": "value", "name": "Contract Value", "type": "currency"},
        {"code": "status", "name": "Status", "type": "select", "options": ["draft", "pending_approval", "active", "expired", "terminated"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="customer", relation_type="many_to_one", foreign_key="customer_id", label="Customer"),
        RelationshipConfig(target_entity="supplier", relation_type="many_to_one", foreign_key="supplier_id", label="Supplier"),
    ],
    permissions=EntityPermissionConfig(),
    workflow=EntityWorkflowConfig(
        states=["draft", "pending_approval", "active", "expired", "terminated"],
        initial_state="draft",
        transitions=[
            {"from": "draft", "to": "pending_approval", "actor": "owner", "condition": None},
            {"from": "pending_approval", "to": "active", "actor": "approver", "condition": None},
            {"from": "active", "to": "expired", "actor": "system", "condition": "past_end_date"},
            {"from": "active", "to": "terminated", "actor": "admin", "condition": None},
        ],
        approval_required=True,
        approvers=["legal_manager"],
    ),
    documents=EntityDocumentConfig(document_types=["contract", "amendment"], required=True),
    analytics=EntityAnalyticsConfig(
        kpis=[{"code": "total_contract_value", "formula": "SUM(value)", "group_by": "status"}],
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True, summarizable=True),
)


_PREBUILT_EMPLOYEE = BusinessObjectConfig(
    entity_code="employee",
    entity_name="Employee",
    description="Employee master data",
    fields=[
        {"code": "first_name", "name": "First Name", "type": "text", "required": True},
        {"code": "last_name", "name": "Last Name", "type": "text", "required": True},
        {"code": "email", "name": "Email", "type": "email", "required": True},
        {"code": "department", "name": "Department", "type": "select", "options": ["engineering", "sales", "marketing", "finance", "hr", "operations"]},
        {"code": "title", "name": "Job Title", "type": "text"},
        {"code": "hire_date", "name": "Hire Date", "type": "date"},
        {"code": "salary", "name": "Salary", "type": "currency"},
        {"code": "status", "name": "Status", "type": "select", "options": ["active", "on_leave", "terminated"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="project", relation_type="many_to_many", foreign_key="project_members", label="Projects"),
    ],
    permissions=EntityPermissionConfig(
        roles={
            "admin": ["create", "read", "update", "delete"],
            "hr_manager": ["create", "read", "update"],
            "employee": ["read"],
        },
    ),
    analytics=EntityAnalyticsConfig(
        kpis=[{"code": "headcount", "formula": "COUNT(*)", "group_by": "department"}],
        dashboards=["hr_dashboard"],
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True, summarizable=True),
)


_PREBUILT_PRODUCT = BusinessObjectConfig(
    entity_code="product",
    entity_name="Product",
    description="Product / service catalog",
    fields=[
        {"code": "sku", "name": "SKU", "type": "text", "required": True},
        {"code": "name", "name": "Name", "type": "text", "required": True},
        {"code": "description", "name": "Description", "type": "rich_text"},
        {"code": "unit_price", "name": "Unit Price", "type": "currency", "required": True},
        {"code": "cost", "name": "Cost", "type": "currency"},
        {"code": "category", "name": "Category", "type": "select", "options": ["software", "hardware", "service", "subscription"]},
        {"code": "status", "name": "Status", "type": "select", "options": ["active", "discontinued"]},
    ],
    relationships=[],
    permissions=EntityPermissionConfig(),
    analytics=EntityAnalyticsConfig(
        kpis=[
            {"code": "total_products", "formula": "COUNT(*)"},
            {"code": "avg_price", "formula": "AVG(unit_price)", "group_by": "category"},
        ],
    ),
    ai=EntityAIConfig(searchable=True, auto_classify=True),
)


_PREBUILT_ASSET = BusinessObjectConfig(
    entity_code="asset",
    entity_name="Asset",
    description="Fixed assets and equipment",
    fields=[
        {"code": "asset_tag", "name": "Asset Tag", "type": "text", "required": True},
        {"code": "name", "name": "Name", "type": "text", "required": True},
        {"code": "category", "name": "Category", "type": "select", "options": ["it_equipment", "furniture", "vehicle", "building", "machinery"]},
        {"code": "purchase_date", "name": "Purchase Date", "type": "date"},
        {"code": "purchase_cost", "name": "Purchase Cost", "type": "currency"},
        {"code": "depreciation_method", "name": "Depreciation Method", "type": "select", "options": ["straight_line", "declining_balance", "none"]},
        {"code": "useful_life_years", "name": "Useful Life (Years)", "type": "integer"},
        {"code": "assigned_to", "name": "Assigned To", "type": "relation", "target_entity": "employee"},
        {"code": "status", "name": "Status", "type": "select", "options": ["active", "in_maintenance", "retired", "disposed"]},
    ],
    relationships=[
        RelationshipConfig(target_entity="employee", relation_type="many_to_one", foreign_key="assigned_to", label="Assigned To"),
    ],
    permissions=EntityPermissionConfig(),
    financial=EntityFinancialConfig(has_financial_impact=True, amount_field="purchase_cost"),
    analytics=EntityAnalyticsConfig(
        kpis=[{"code": "total_asset_value", "formula": "SUM(purchase_cost)", "group_by": "category"}],
        dashboards=["asset_dashboard"],
    ),
    ai=EntityAIConfig(context_enabled=True, searchable=True),
)


PREBUILT_OBJECTS: dict[str, BusinessObjectConfig] = {
    "customer": _PREBUILT_CUSTOMER,
    "supplier": _PREBUILT_SUPPLIER,
    "project": _PREBUILT_PROJECT,
    "invoice": _PREBUILT_INVOICE,
    "purchase_order": _PREBUILT_PURCHASE_ORDER,
    "payment": _PREBUILT_PAYMENT,
    "contract": _PREBUILT_CONTRACT,
    "employee": _PREBUILT_EMPLOYEE,
    "product": _PREBUILT_PRODUCT,
    "asset": _PREBUILT_ASSET,
}


class BusinessObjectRegistry:
    """Central registry for Business Object configurations.

    Resolves from tenant-specific DB overrides first, then falls back to
    the pre-built definitions above.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._cache: dict[str, BusinessObjectConfig] = {}

    def get(self, entity_code: str, tenant_id: str | None = None) -> BusinessObjectConfig | None:
        """Get business object config -- check DB first, then prebuilt."""
        cache_key = f"{tenant_id}:{entity_code}" if tenant_id else entity_code
        if cache_key in self._cache:
            return self._cache[cache_key]

        if tenant_id:
            from uuid import UUID

            from .models import MetadataEntity

            row = self.db.scalar(
                select(MetadataEntity).where(
                    MetadataEntity.tenant_id == UUID(tenant_id),
                    MetadataEntity.code == entity_code,
                ).order_by(MetadataEntity.version.desc())
            )
            if row is not None and row.definition:
                try:
                    config = BusinessObjectConfig.from_dict(row.definition)
                    self._cache[cache_key] = config
                    return config
                except Exception:
                    logger.warning("Failed to parse stored definition for %s", entity_code)

        config = PREBUILT_OBJECTS.get(entity_code)
        if config is not None:
            self._cache[cache_key] = config
        return config

    def register(self, config: BusinessObjectConfig, tenant_id: str) -> None:
        """Register a custom business object for a tenant."""
        cache_key = f"{tenant_id}:{config.entity_code}"
        self._cache[cache_key] = config
        logger.info("Registered business object %s for tenant %s", config.entity_code, tenant_id)

    def list_all(self, tenant_id: str | None = None) -> list[BusinessObjectConfig]:
        """List all business objects (prebuilt + custom)."""
        result: list[BusinessObjectConfig] = list(PREBUILT_OBJECTS.values())
        seen = {c.entity_code for c in result}

        if tenant_id:
            from uuid import UUID

            from .models import MetadataEntity

            rows = self.db.scalars(
                select(MetadataEntity).where(
                    MetadataEntity.tenant_id == UUID(tenant_id),
                    MetadataEntity.published_at.is_not(None),
                ).order_by(MetadataEntity.code, MetadataEntity.version.desc())
            ).all()
            latest: dict[str, Any] = {}
            for row in rows:
                latest.setdefault(row.code, row)
            for code, row in latest.items():
                if code not in seen and row.definition:
                    try:
                        result.append(BusinessObjectConfig.from_dict(row.definition))
                    except Exception:
                        logger.warning("Skipping invalid definition for %s", code)

        return sorted(result, key=lambda c: c.entity_code)

    def get_relationships(self, entity_code: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
        """Get all relationships for an entity."""
        config = self.get(entity_code, tenant_id)
        if config is None:
            return []
        return [r.to_dict() for r in config.relationships]

    def get_graph_path(self, from_entity: str, to_entity: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
        """Find the shortest path between two entities in the business graph using BFS."""
        if from_entity == to_entity:
            return [{"entity": from_entity, "relation": None}]

        all_objects = {c.entity_code: c for c in self.list_all(tenant_id)}
        if from_entity not in all_objects or to_entity not in all_objects:
            return []

        adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for code, config in all_objects.items():
            neighbors: list[tuple[str, dict[str, Any]]] = []
            for rel in config.relationships:
                neighbors.append((rel.target_entity, rel.to_dict()))
            adjacency[code] = neighbors

        visited: set[str] = {from_entity}
        queue: deque[tuple[str, list[dict[str, Any]]]] = deque([(from_entity, [])])

        while queue:
            current, path = queue.popleft()
            for neighbor, rel_data in adjacency.get(current, []):
                if neighbor in visited:
                    continue
                new_path = path + [{"entity": current, "relation": rel_data}]
                if neighbor == to_entity:
                    new_path.append({"entity": to_entity, "relation": None})
                    return new_path
                visited.add(neighbor)
                queue.append((neighbor, new_path))

        return []
