"""Marketplace foundation router."""
from uuid import UUID, uuid4
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..auth.security import Principal, require_principal
from ..db import get_db
from ..marketplace.models import MarketplaceInstallation
from .schemas import (
    MarketplaceAppCreate,
    MarketplaceAppResponse,
    MarketplaceAuthorCreate,
    MarketplaceAuthorResponse,
    MarketplaceCategoryCreate,
    MarketplaceCategoryResponse,
    MarketplaceInstallationResponse,
    MarketplaceOrderCreate,
    MarketplaceOrderResponse,
    MarketplaceReviewCreate,
    MarketplaceReviewResponse,
)
from .service import MarketplaceService
from ..tenant import require_tenant

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


# Apps

@router.post("/apps", response_model=MarketplaceAppResponse, status_code=201)
def create_app(
    payload: MarketplaceAppCreate,
    db: Session = Depends(get_db),
) -> MarketplaceAppResponse:
    svc = MarketplaceService(db)
    app = svc.create_app(payload.model_dump())
    return MarketplaceAppResponse.model_validate(app)


@router.get("/apps", response_model=list[MarketplaceAppResponse])
def list_apps(
    category: str | None = Query(default=None),
    pricing_model: str | None = Query(default=None),
    is_featured: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MarketplaceAppResponse]:
    svc = MarketplaceService(db)
    apps, _ = svc.list_apps(category=category, pricing_model=pricing_model, is_featured=is_featured, search=search, limit=limit, offset=offset)
    return [MarketplaceAppResponse.model_validate(a) for a in apps]


@router.get("/apps/{app_id}", response_model=MarketplaceAppResponse)
def get_app(
    app_id: str,
    db: Session = Depends(get_db),
) -> MarketplaceAppResponse:
    svc = MarketplaceService(db)
    app = svc.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return MarketplaceAppResponse.model_validate(app)


@router.post("/apps/{app_id}/publish", response_model=MarketplaceAppResponse)
def publish_app(
    app_id: str,
    db: Session = Depends(get_db),
) -> MarketplaceAppResponse:
    svc = MarketplaceService(db)
    app = svc.publish_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return MarketplaceAppResponse.model_validate(app)


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
) -> dict:
    svc = MarketplaceService(db)
    return svc.get_stats()


# Categories

@router.post("/categories", response_model=MarketplaceCategoryResponse, status_code=201)
def create_category(
    payload: MarketplaceCategoryCreate,
    db: Session = Depends(get_db),
) -> MarketplaceCategoryResponse:
    svc = MarketplaceService(db)
    cat = svc.create_category(payload.model_dump())
    return MarketplaceCategoryResponse.model_validate(cat)


@router.get("/categories", response_model=list[MarketplaceCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
) -> list[MarketplaceCategoryResponse]:
    svc = MarketplaceService(db)
    return [MarketplaceCategoryResponse.model_validate(c) for c in svc.list_categories()]


# Reviews

@router.post("/reviews", response_model=MarketplaceReviewResponse, status_code=201)
def create_review(
    payload: MarketplaceReviewCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MarketplaceReviewResponse:
    svc = MarketplaceService(db)
    review = svc.create_review(str(tenant_id), "user-id", payload.model_dump())
    return MarketplaceReviewResponse.model_validate(review)


@router.get("/apps/{app_id}/reviews", response_model=list[MarketplaceReviewResponse])
def list_reviews(
    app_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[MarketplaceReviewResponse]:
    svc = MarketplaceService(db)
    return [MarketplaceReviewResponse.model_validate(r) for r in svc.list_reviews(app_id, limit=limit)]


# Installations

@router.post("/apps/{app_id}/install", response_model=MarketplaceInstallationResponse)
def install_app(
    app_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MarketplaceInstallationResponse:
    svc = MarketplaceService(db)
    app = svc.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    installation = svc.install_app(app_id, str(tenant_id), "user-id", app.version)
    return MarketplaceInstallationResponse.model_validate(installation)


@router.get("/installations", response_model=list[MarketplaceInstallationResponse])
def list_installations(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[MarketplaceInstallationResponse]:
    svc = MarketplaceService(db)
    return [MarketplaceInstallationResponse.model_validate(i) for i in svc.list_installations(str(tenant_id))]


# Orders

@router.post("/orders", response_model=MarketplaceOrderResponse, status_code=201)
def create_order(
    payload: MarketplaceOrderCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MarketplaceOrderResponse:
    svc = MarketplaceService(db)
    order = svc.create_order(str(tenant_id), "user-id", payload.model_dump())
    return MarketplaceOrderResponse.model_validate(order)


@router.get("/orders", response_model=list[MarketplaceOrderResponse])
def list_orders(
    tenant_id: UUID = Depends(require_tenant),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[MarketplaceOrderResponse]:
    svc = MarketplaceService(db)
    return [MarketplaceOrderResponse.model_validate(o) for o in svc.list_orders(str(tenant_id), limit=limit)]


# Authors

@router.post("/authors", response_model=MarketplaceAuthorResponse, status_code=201)
def create_author(
    payload: MarketplaceAuthorCreate,
    db: Session = Depends(get_db),
) -> MarketplaceAuthorResponse:
    svc = MarketplaceService(db)
    author = svc.create_author("user-id", payload.model_dump())
    return MarketplaceAuthorResponse.model_validate(author)


@router.get("/authors", response_model=list[MarketplaceAuthorResponse])
def list_authors(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[MarketplaceAuthorResponse]:
    svc = MarketplaceService(db)
    return [MarketplaceAuthorResponse.model_validate(a) for a in svc.list_authors(limit=limit)]


@router.get("/authors/{author_id}", response_model=MarketplaceAuthorResponse)
def get_author(
    author_id: str,
    db: Session = Depends(get_db),
) -> MarketplaceAuthorResponse:
    svc = MarketplaceService(db)
    author = svc.get_author(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return MarketplaceAuthorResponse.model_validate(author)


# ---------------------------------------------------------------------------
# Industry Packs
# ---------------------------------------------------------------------------

INDUSTRY_PACKS = {
    "construction": {
        "name": "Construction Industry Pack",
        "description": "Pre-built entities, workflows, and configurations for construction companies",
        "entities": [
            {
                "code": "project",
                "name": "Construction Project",
                "fields": [
                    {"code": "name", "type": "text", "label": "Project Name", "required": True},
                    {"code": "project_number", "type": "text", "label": "Project Number"},
                    {"code": "client_name", "type": "text", "label": "Client Name"},
                    {"code": "status", "type": "select", "label": "Status", "options": ["planning", "active", "on_hold", "completed", "cancelled"]},
                    {"code": "start_date", "type": "date", "label": "Start Date"},
                    {"code": "end_date", "type": "date", "label": "End Date"},
                    {"code": "budget", "type": "decimal", "label": "Budget"},
                    {"code": "actual_cost", "type": "decimal", "label": "Actual Cost"},
                    {"code": "location", "type": "text", "label": "Location"},
                    {"code": "project_manager", "type": "text", "label": "Project Manager"},
                ],
            },
            {
                "code": "boq",
                "name": "Bill of Quantities",
                "fields": [
                    {"code": "project_id", "type": "relation", "label": "Project", "target_entity": "project"},
                    {"code": "item_code", "type": "text", "label": "Item Code"},
                    {"code": "description", "type": "text", "label": "Description"},
                    {"code": "unit", "type": "text", "label": "Unit"},
                    {"code": "quantity", "type": "decimal", "label": "Quantity"},
                    {"code": "unit_price", "type": "decimal", "label": "Unit Price"},
                    {"code": "total_price", "type": "decimal", "label": "Total Price"},
                ],
            },
            {
                "code": "variation",
                "name": "Variation Order",
                "fields": [
                    {"code": "project_id", "type": "relation", "label": "Project", "target_entity": "project"},
                    {"code": "variation_number", "type": "text", "label": "Variation Number"},
                    {"code": "description", "type": "text", "label": "Description"},
                    {"code": "reason", "type": "text", "label": "Reason"},
                    {"code": "amount", "type": "decimal", "label": "Amount"},
                    {"code": "status", "type": "select", "label": "Status", "options": ["pending", "approved", "rejected"]},
                ],
            },
            {
                "code": "daily_report",
                "name": "Daily Site Report",
                "fields": [
                    {"code": "project_id", "type": "relation", "label": "Project", "target_entity": "project"},
                    {"code": "report_date", "type": "date", "label": "Report Date"},
                    {"code": "weather", "type": "text", "label": "Weather"},
                    {"code": "workers_on_site", "type": "integer", "label": "Workers on Site"},
                    {"code": "equipment_on_site", "type": "text", "label": "Equipment on Site"},
                    {"code": "work_completed", "type": "text", "label": "Work Completed"},
                    {"code": "issues", "type": "text", "label": "Issues"},
                ],
            },
        ],
    },
    "retail": {
        "name": "Retail Industry Pack",
        "description": "Pre-built entities, workflows, and configurations for retail businesses",
        "entities": [
            {
                "code": "product",
                "name": "Product",
                "fields": [
                    {"code": "name", "type": "text", "label": "Product Name", "required": True},
                    {"code": "sku", "type": "text", "label": "SKU"},
                    {"code": "barcode", "type": "text", "label": "Barcode"},
                    {"code": "category", "type": "text", "label": "Category"},
                    {"code": "price", "type": "decimal", "label": "Price"},
                    {"code": "cost", "type": "decimal", "label": "Cost"},
                    {"code": "stock_quantity", "type": "integer", "label": "Stock Quantity"},
                    {"code": "reorder_level", "type": "integer", "label": "Reorder Level"},
                    {"code": "supplier", "type": "text", "label": "Supplier"},
                ],
            },
            {
                "code": "pos_transaction",
                "name": "POS Transaction",
                "fields": [
                    {"code": "transaction_number", "type": "text", "label": "Transaction Number"},
                    {"code": "register_id", "type": "text", "label": "Register ID"},
                    {"code": "cashier", "type": "text", "label": "Cashier"},
                    {"code": "subtotal", "type": "decimal", "label": "Subtotal"},
                    {"code": "tax", "type": "decimal", "label": "Tax"},
                    {"code": "total", "type": "decimal", "label": "Total"},
                    {"code": "payment_method", "type": "select", "label": "Payment Method", "options": ["cash", "card", "mobile", "gift_card"]},
                    {"code": "transaction_date", "type": "datetime", "label": "Transaction Date"},
                ],
            },
            {
                "code": "inventory_count",
                "name": "Inventory Count",
                "fields": [
                    {"code": "product_id", "type": "relation", "label": "Product", "target_entity": "product"},
                    {"code": "count_date", "type": "date", "label": "Count Date"},
                    {"code": "system_quantity", "type": "integer", "label": "System Quantity"},
                    {"code": "actual_quantity", "type": "integer", "label": "Actual Quantity"},
                    {"code": "variance", "type": "integer", "label": "Variance"},
                    {"code": "counted_by", "type": "text", "label": "Counted By"},
                ],
            },
            {
                "code": "loyalty_member",
                "name": "Loyalty Member",
                "fields": [
                    {"code": "member_number", "type": "text", "label": "Member Number"},
                    {"code": "name", "type": "text", "label": "Name"},
                    {"code": "email", "type": "text", "label": "Email"},
                    {"code": "phone", "type": "text", "label": "Phone"},
                    {"code": "points_balance", "type": "integer", "label": "Points Balance"},
                    {"code": "tier", "type": "select", "label": "Tier", "options": ["bronze", "silver", "gold", "platinum"]},
                    {"code": "join_date", "type": "date", "label": "Join Date"},
                ],
            },
        ],
    },
}


@router.get("/industry-packs")
def list_industry_packs():
    return [
        {"id": k, "name": v["name"], "description": v["description"], "entity_count": len(v["entities"])}
        for k, v in INDUSTRY_PACKS.items()
    ]


# ---------------------------------------------------------------------------
# Industry Pack Registry endpoints (must be before {pack_id} routes)
# ---------------------------------------------------------------------------

@router.get("/industry-packs/registry")
def list_industry_packs_registry() -> list[dict]:
    """List all registered industry packs."""
    from .industry_pack_registry import list_industry_packs
    return list_industry_packs()


@router.get("/industry-packs/registry/{pack_id}")
def get_industry_pack_registry_info(pack_id: str) -> dict:
    """Get full industry pack details from registry."""
    from .industry_pack_registry import get_industry_pack_full
    info = get_industry_pack_full(pack_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Industry pack not found: {pack_id}")
    return info


@router.post("/industry-packs/registry/{pack_id}/install")
def install_industry_pack_from_registry(
    pack_id: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Install an industry pack for the current tenant from the registry."""
    from .industry_pack_registry import get_industry_pack_full
    info = get_industry_pack_full(pack_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Industry pack not found: {pack_id}")

    existing = db.scalar(
        select(MarketplaceInstallation).where(
            MarketplaceInstallation.tenant_id == str(tenant_id),
            MarketplaceInstallation.app_id == f"industry-{pack_id}",
        )
    )
    if existing and existing.status == "active":
        return {"status": "already_installed", "pack_id": pack_id, "installation_id": existing.id}

    if existing:
        existing.status = "active"
        existing.uninstalled_at = None
        db.commit()
        return {"status": "reactivated", "pack_id": pack_id, "installation_id": existing.id}

    installation = MarketplaceInstallation(
        tenant_id=str(tenant_id),
        app_id=f"industry-{pack_id}",
        user_id=str(principal.user_id),
        version="1.0.0",
        status="active",
    )
    db.add(installation)
    db.commit()
    db.refresh(installation)

    return {
        "status": "installed",
        "pack_id": pack_id,
        "pack_name": info["name"],
        "installation_id": installation.id,
        "entities_count": len(info["entities"]),
        "workflows_count": len(info["workflows"]),
    }


@router.get("/industry-packs/{pack_id}")
def get_industry_pack(pack_id: str):
    pack = INDUSTRY_PACKS.get(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Industry pack not found")
    return {"id": pack_id, **pack}


@router.post("/industry-packs/{pack_id}/install")
def install_industry_pack(
    pack_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    pack = INDUSTRY_PACKS.get(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Industry pack not found")

    # Create MarketplaceInstallation record
    existing_installation = db.scalar(
        select(MarketplaceInstallation).where(
            MarketplaceInstallation.tenant_id == str(tenant_id),
            MarketplaceInstallation.app_id == f"industry-{pack_id}",
        )
    )
    if existing_installation and existing_installation.status == "active":
        return {"status": "already_installed", "pack_id": pack_id, "installation_id": existing_installation.id}
    if existing_installation:
        existing_installation.status = "active"
        existing_installation.uninstalled_at = None
        db.commit()
        return {"status": "reactivated", "pack_id": pack_id, "installation_id": existing_installation.id}

    installation = MarketplaceInstallation(
        tenant_id=str(tenant_id),
        app_id=f"industry-{pack_id}",
        user_id=str(uuid4()),
        version="1.0.0",
        status="active",
    )
    db.add(installation)
    db.commit()
    db.refresh(installation)

    from ..metadata.models import MetadataEntity
    from ..workflow.models import WorkflowDefinition
    from ..rules.models import Rule
    from ..metadata.models import MetadataDashboardKPI
    installed = []

    # Phase 1: Seed metadata entities (fields + relations)
    for entity_def in pack["entities"]:
        existing = db.scalar(
            select(MetadataEntity).where(
                MetadataEntity.tenant_id == tenant_id,
                MetadataEntity.code == entity_def["code"],
            )
        )
        if existing is None:
            entity = MetadataEntity(
                tenant_id=tenant_id,
                code=entity_def["code"],
                name=entity_def["name"],
                definition={"fields": entity_def["fields"]},
                version=1,
            )
            db.add(entity)
            installed.append(entity_def["code"])

    # Phase 2: Seed a starter workflow for the first entity
    starter_workflow_code = f"{pack_id}_starter"
    if not db.scalar(
        select(WorkflowDefinition).where(
            WorkflowDefinition.tenant_id == tenant_id,
            WorkflowDefinition.code == starter_workflow_code,
        )
    ):
        starter = WorkflowDefinition(
            tenant_id=tenant_id,
            code=starter_workflow_code,
            name=f"{pack['name']} - Starter Approval",
            version=1,
            initial_state="draft",
            is_active=True,
            created_by=uuid4(),
            definition={
                "states": [
                    {"name": "draft", "label": "Draft"},
                    {"name": "pending_review", "label": "Pending Review"},
                    {"name": "approved", "label": "Approved"},
                    {"name": "rejected", "label": "Rejected"},
                ],
                "transitions": [
                    {
                        "from_state": "draft",
                        "to_state": "pending_review",
                        "action": "submit_for_review",
                        "roles": ["admin"],
                        "requires_approval": False,
                        "actions": [],
                    },
                    {
                        "from_state": "pending_review",
                        "to_state": "approved",
                        "action": "approve",
                        "roles": ["admin"],
                        "requires_approval": True,
                        "actions": [],
                    },
                    {
                        "from_state": "pending_review",
                        "to_state": "rejected",
                        "action": "reject",
                        "roles": ["admin"],
                        "requires_approval": True,
                        "actions": [],
                    },
                ],
            },
        )
        db.add(starter)
        db.flush()

    # Phase 3: Seed a starter rule for the pack
    starter_rule_code = f"{pack_id}_starter_rule"
    if not db.scalar(
        select(Rule).where(
            Rule.tenant_id == tenant_id,
            Rule.name == starter_rule_code,
        )
    ):
        rule = Rule(
            tenant_id=tenant_id,
            name=starter_rule_code,
            description=f"Automatic validation rule for {pack_id} records",
            event_type=pack["entities"][0]["code"],
            actions_json=json.dumps({"op": "warn", "message": f"Review {pack_id} record before finalizing"}),
            enabled=True,
        )
        db.add(rule)
        db.flush()

    # Phase 4: Seed a starter dashboard KPI
    kpi_code = f"{pack_id}_kpi_count"
    if not db.scalar(
        select(MetadataDashboardKPI).where(
            MetadataDashboardKPI.tenant_id == tenant_id,
            MetadataDashboardKPI.code == kpi_code,
        )
    ):
        kpi = MetadataDashboardKPI(
            tenant_id=tenant_id,
            code=kpi_code,
            name=f"{pack['name']} - Record Count",
            description=f"Total number of {pack_id} records",
            entity_code=pack["entities"][0]["code"],
            kpi_type="count",
            formula_json=json.dumps({"type": "count", "entity": pack["entities"][0]["code"]}),
        )
        db.add(kpi)

    db.commit()
    return {"pack_id": pack_id, "installed_entities": installed, "status": "success"}


# ---------------------------------------------------------------------------
# Marketplace App Install endpoints
# ---------------------------------------------------------------------------

class AppInstallRequest(BaseModel):
    app_id: str
    config: dict | None = None


class AppInstallResponse(BaseModel):
    installation_id: str
    app_id: str
    tenant_id: str
    status: str
    version: str


@router.post("/install", response_model=AppInstallResponse, status_code=201)
def install_marketplace_app(
    payload: AppInstallRequest,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    svc = MarketplaceService(db)
    app = svc.get_app(payload.app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Check if already installed
    existing = db.scalar(
        select(MarketplaceInstallation).where(
            MarketplaceInstallation.app_id == payload.app_id,
            MarketplaceInstallation.tenant_id == str(tenant_id),
            MarketplaceInstallation.status == "active",
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="App already installed")

    installation = svc.install_app(
        app_id=payload.app_id,
        tenant_id=str(tenant_id),
        user_id=str(principal.user_id),
        version=app.version,
    )

    audit_record(
        db, tenant_id=tenant_id, actor_id=principal.user_id,
        action="marketplace.app_installed", resource_type="marketplace_app",
        resource_id=UUID(payload.app_id), metadata={"app_id": payload.app_id, "config": payload.config},
        request_id=getattr(principal, "request_id", None),
    )
    db.commit()

    return AppInstallResponse(
        installation_id=str(installation.id),
        app_id=payload.app_id,
        tenant_id=str(tenant_id),
        status="active",
        version=app.version,
    )


@router.get("/installations")
def list_installations(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    svc = MarketplaceService(db)
    installations = svc.list_installations(str(tenant_id))
    return [
        {
            "id": str(i.id),
            "app_id": i.app_id,
            "version": i.version,
            "status": i.status,
            "installed_at": i.installed_at,
        }
        for i in installations
    ]


@router.post("/installations/{installation_id}/uninstall")
def uninstall_app(
    installation_id: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    installation = db.scalar(
        select(MarketplaceInstallation).where(
            MarketplaceInstallation.id == installation_id,
            MarketplaceInstallation.tenant_id == str(tenant_id),
        )
    )
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")
    installation.status = "uninstalled"
    installation.uninstalled_at = datetime.utcnow()
    db.commit()
    return {"status": "uninstalled"}
