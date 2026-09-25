"""Pluggable Industry Pack Registry.

Industry packs register themselves here at import time. The registry provides:
- Dynamic pack discovery
- Uniform metadata interface
- Runtime pack lookup by pack_id
"""

import logging
from typing import Any

logger = logging.getLogger("2to-eos.marketplace.industry_packs")

_registry: dict[str, dict[str, Any]] = {}


def register_industry_pack(
    pack_id: str,
    pack_name: str,
    description: str,
    entities: list[dict[str, Any]],
    workflows: list[dict[str, Any]] | None = None,
    kpi_categories: list[str] | None = None,
    rules: list[dict[str, Any]] | None = None,
) -> None:
    """Register an industry pack."""
    _registry[pack_id.lower()] = {
        "id": pack_id.lower(),
        "name": pack_name,
        "description": description,
        "entities": entities,
        "workflows": workflows or [],
        "kpi_categories": kpi_categories or [],
        "rules": rules or [],
    }
    logger.info("Industry pack registered: %s", pack_name)


def get_industry_pack(pack_id: str) -> dict[str, Any] | None:
    """Get industry pack metadata by ID."""
    return _registry.get(pack_id.lower())


def list_industry_packs() -> list[dict[str, Any]]:
    """List all registered industry packs (summary)."""
    return [
        {
            "id": info["id"],
            "name": info["name"],
            "description": info["description"],
            "entity_count": len(info["entities"]),
            "kpi_categories": info["kpi_categories"],
        }
        for info in _registry.values()
    ]


def get_industry_pack_full(pack_id: str) -> dict[str, Any] | None:
    """Get full industry pack details."""
    return _registry.get(pack_id.lower())


def _register_builtin_industry_packs() -> None:
    """Register built-in industry packs."""

    # Construction Industry Pack
    register_industry_pack(
        pack_id="construction",
        pack_name="Construction Industry Pack",
        description="Full construction project management: projects, contracts, BOQs, procurement, claims, progress tracking, and financial integration.",
        entities=[
            {"id": "project", "name": "Project", "description": "Construction projects with budget, client, location, and status tracking"},
            {"id": "contract", "name": "Contract", "description": "Main, sub, and supply contracts linked to projects"},
            {"id": "boq", "name": "Bill of Quantities", "description": "Versioned BOQs with line items for quantity and rate tracking"},
            {"id": "budget", "name": "Budget", "description": "Versioned project budgets with line items and status lifecycle"},
            {"id": "progress_claim", "name": "Progress Claim", "description": "Progress claims against contracts with period-based tracking"},
            {"id": "change_order", "name": "Change Order", "description": "Change orders with cost and time impact tracking"},
            {"id": "subcontract", "name": "Subcontract", "description": "Subcontractor agreements with scope, value, and dates"},
            {"id": "procurement", "name": "Procurement", "description": "Procurement requisitions with priority and workflow"},
            {"id": "purchase_order", "name": "Purchase Order", "description": "POs linked to procurements with supplier and currency"},
            {"id": "goods_receipt", "name": "Goods Receipt", "description": "GRNs for receiving goods into site warehouses"},
            {"id": "supplier_invoice", "name": "Supplier Invoice", "description": "Supplier invoices with tax and approval workflow"},
            {"id": "payment", "name": "Payment", "description": "Supplier payments with method and approval workflow"},
            {"id": "site_warehouse", "name": "Site Warehouse", "description": "On-site warehouses per project"},
        ],
        workflows=[
            {"id": "project_lifecycle", "name": "Project Lifecycle", "states": ["planning", "active", "on_hold", "completed", "cancelled"]},
            {"id": "procurement_approval", "name": "Procurement Approval", "states": ["draft", "pending", "approved", "rejected"]},
            {"id": "claim_approval", "name": "Claim Approval", "states": ["draft", "submitted", "reviewed", "approved", "paid"]},
        ],
        kpi_categories=["project_health", "financial", "procurement", "claims", "cash_flow"],
        rules=[
            {"id": "budget_threshold", "name": "Budget Threshold Warning", "description": "Alert when budget exceeds threshold"},
            {"id": "claim_approval_gate", "name": "Claim Approval Gate", "description": "Require approval for high-value claims"},
            {"id": "po_approval_gate", "name": "PO Approval Gate", "description": "Require approval for high-value purchase orders"},
        ],
    )

    # Retail Industry Pack (stub)
    register_industry_pack(
        pack_id="retail",
        pack_name="Retail Industry Pack",
        description="Retail operations: products, POS transactions, inventory counts, and loyalty members.",
        entities=[
            {"id": "product", "name": "Product", "description": "Product catalog with SKU, pricing, and categories"},
            {"id": "pos_transaction", "name": "POS Transaction", "description": "Point-of-sale transactions with line items"},
            {"id": "inventory_count", "name": "Inventory Count", "description": "Physical inventory counts and adjustments"},
            {"id": "loyalty_member", "name": "Loyalty Member", "description": "Customer loyalty program members"},
        ],
        workflows=[
            {"id": "inventory_adjustment", "name": "Inventory Adjustment", "states": ["counted", "reviewed", "approved"]},
        ],
        kpi_categories=["sales", "inventory", "customer", "loyalty"],
    )

    # Manufacturing Industry Pack (stub)
    register_industry_pack(
        pack_id="manufacturing",
        pack_name="Manufacturing Industry Pack",
        description="Manufacturing operations: BOM, work orders, production tracking, quality control.",
        entities=[
            {"id": "bom", "name": "Bill of Materials", "description": "Product BOMs with components and quantities"},
            {"id": "work_order", "name": "Work Order", "description": "Production work orders with routing and scheduling"},
            {"id": "production_tracking", "name": "Production Tracking", "description": "Shop floor production tracking with yield and scrap"},
            {"id": "quality_inspection", "name": "Quality Inspection", "description": "QC inspections with pass/fail and defect tracking"},
        ],
        workflows=[
            {"id": "work_order_lifecycle", "name": "Work Order Lifecycle", "states": ["planned", "released", "in_progress", "completed", "closed"]},
        ],
        kpi_categories=["production", "quality", "efficiency", "cost"],
    )


_register_builtin_industry_packs()
