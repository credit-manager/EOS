"""Construction Pack - Industry Pack reference implementation.

Provides construction-specific:
- Entities: Project, Contract, BOQ, Budget, ProgressClaim, ChangeOrder,
            Subcontract, SiteWarehouse, Procurement, PurchaseOrder, GoodsReceipt,
            SupplierInvoice, Payment
- KPIs: cost_variance, schedule_variance, burn_rate, claim_coverage,
         procurement_lead_time
- Dashboards: project_health, procurement_pipeline, contract_status,
              cash_projection
- AI Agent: ConstructionAnalystAgent
- Rules: budget_threshold_warning, claim_approval_required,
         po_approval_gate, grn_invoice_matching
- Compliance: retention policies, approval hierarchies
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..events.service import publish as publish_event
from ..financial.models import JournalEntry, JournalLine
from ..construction.models import (
    BOQ,
    Budget,
    ChangeOrder,
    Contract,
    GoodsReceipt,
    Payment,
    Procurement,
    Project,
    ProjectFinancialAccounts,
    ProgressClaim,
    PurchaseOrder,
    SiteWarehouse,
    SupplierInvoice,
)

logger = __import__("logging").getLogger("2to-eos.construction.pack")


# ---------------------------------------------------------------------------
# Construction Pack Service
# ---------------------------------------------------------------------------

class ConstructionPackService:
    """Construction Pack - industry-specific business logic layer."""

    PACK_NAME = "Construction Pack"
    PACK_VERSION = "1.0.0"

    def __init__(self, db: Session, tenant_id):
        self.db = db
        self.tenant_id = tenant_id

    # -------------------------------------------------------------------
    # Pack metadata
    # -------------------------------------------------------------------

    def get_pack_info(self) -> dict:
        return {
            "name": self.PACK_NAME,
            "version": self.PACK_VERSION,
            "domain": "construction",
            "entities": [
                "Project", "Contract", "BOQ", "Budget",
                "ProgressClaim", "ChangeOrder", "Subcontract",
                "SiteWarehouse", "Procurement", "PurchaseOrder",
                "GoodsReceipt", "SupplierInvoice", "Payment",
            ],
            "kpi_categories": ["financial", "schedule", "procurement", "claims"],
            "workflows": [
                "project_lifecycle",
                "contract_approval",
                "procurement_to_payment",
                "claim_to_payment",
                "change_order_approval",
            ],
        }

    # -------------------------------------------------------------------
    # Construction-specific KPIs
    # -------------------------------------------------------------------

    def compute_project_health(self, project_id) -> dict:
        """Compute health KPIs for a single project."""
        project = self.db.get(Project, project_id)
        if project is None or project.tenant_id != self.tenant_id:
            return {"error": "project_not_found"}

        budget = self.db.scalar(
            select(Budget).where(
                Budget.tenant_id == self.tenant_id,
                Budget.project_id == project_id,
                Budget.status.in_(["approved", "baselined"]),
            )
        )
        budget_amount = budget.total_amount if budget else Decimal("0")

        active_claims = self.db.scalars(
            select(ProgressClaim).where(
                ProgressClaim.tenant_id == self.tenant_id,
                ProgressClaim.contract_id.in_(
                    select(Contract.id).where(
                        Contract.tenant_id == self.tenant_id,
                        Contract.project_id == project_id,
                    )
                ),
                ProgressClaim.status.in_(["submitted", "approved"]),
            )
        ).all()
        claimed_amount = sum((c.total_amount for c in active_claims), Decimal("0"))

        approved_pos = self.db.scalars(
            select(PurchaseOrder).where(
                PurchaseOrder.tenant_id == self.tenant_id,
                PurchaseOrder.status.in_(["acknowledged", "partial_received", "received"]),
                PurchaseOrder.procurement_id.in_(
                    select(Procurement.id).where(
                        Procurement.tenant_id == self.tenant_id,
                        Procurement.project_id == project_id,
                    )
                ),
            )
        ).all()
        committed_amount = sum((p.total_amount for p in approved_pos), Decimal("0"))

        # Simple health assessment
        if budget_amount > 0:
            utilization_pct = (committed_amount / budget_amount * 100).quantize(Decimal("0.1"))
        else:
            utilization_pct = Decimal("0")

        if utilization_pct > 90:
            risk_level = "high"
        elif utilization_pct > 70:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "project_id": str(project_id),
            "project_code": project.code,
            "project_name": project.name,
            "status": project.status,
            "budget_amount": float(budget_amount),
            "committed_amount": float(committed_amount),
            "claimed_amount": float(claimed_amount),
            "remaining_budget": float(max(budget_amount - committed_amount, Decimal("0"))),
            "utilization_pct": float(utilization_pct),
            "risk_level": risk_level,
            "active_claims_count": len(active_claims),
            "approved_pos_count": len(approved_pos),
        }

    def compute_project_margin(self, project_id) -> dict:
        """Compute margin KPIs for a project based on contract value vs committed costs."""
        contract = self.db.scalar(
            select(Contract).where(
                Contract.tenant_id == self.tenant_id,
                Contract.project_id == project_id,
                Contract.status.in_(["active", "completed"]),
            )
        )
        if contract is None:
            return {"error": "no_active_contract"}

        committed = self.compute_project_health(project_id)
        if "error" in committed:
            return committed

        contract_value = contract.contract_value
        costs_committed = Decimal(str(committed.get("committed_amount", 0)))
        margin = contract_value - costs_committed
        margin_pct = (margin / contract_value * 100).quantize(Decimal("0.1")) if contract_value > 0 else Decimal("0")

        return {
            "contract_value": float(contract_value),
            "costs_committed": float(costs_committed),
            "margin": float(margin),
            "margin_pct": float(margin_pct),
            "health": committed.get("risk_level", "unknown"),
        }

    def compute_procurement_pipeline(self, project_id = None) -> dict:
        """Compute procurement KPIs."""
        query = select(Procurement).where(Procurement.tenant_id == self.tenant_id)
        if project_id:
            query = query.where(Procurement.project_id == project_id)

        procurements = self.db.scalars(query).all()
        by_status = {}
        total_estimated = Decimal("0")
        for proc in procurements:
            by_status[proc.status] = by_status.get(proc.status, 0) + 1
            total_estimated += proc.total_estimated

        po_query = select(PurchaseOrder).where(PurchaseOrder.tenant_id == self.tenant_id)
        if project_id:
            po_query = po_query.where(
                PurchaseOrder.procurement_id.in_(
                    select(Procurement.id).where(Procurement.project_id == project_id)
                )
            )
        pos = self.db.scalars(po_query).all()
        pos_by_status = {}
        total_po_value = Decimal("0")
        for po in pos:
            pos_by_status[po.status] = pos_by_status.get(po.status, 0) + 1
            total_po_value += po.total_amount

        return {
            "procurements_by_status": by_status,
            "total_procurements": len(procurements),
            "total_estimated_value": float(total_estimated),
            "purchase_orders_by_status": pos_by_status,
            "total_po_value": float(total_po_value),
            "pos_count": len(pos),
        }

    def compute_contract_status(self, project_id = None) -> dict:
        """Compute contract status KPIs."""
        query = select(Contract).where(Contract.tenant_id == self.tenant_id)
        if project_id:
            query = query.where(Contract.project_id == project_id)

        contracts = self.db.scalars(query).all()
        by_status = {}
        total_value = Decimal("0")
        for c in contracts:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            total_value += c.contract_value

        return {
            "contracts_by_status": by_status,
            "total_contracts": len(contracts),
            "total_contract_value": float(total_value),
            "active_contract_value": float(
                sum((c.contract_value for c in contracts if c.status == "active"), Decimal("0"))
            ),
        }

    def compute_claims_kpi(self, project_id = None) -> dict:
        """Compute progress claim KPIs."""
        query = select(ProgressClaim).where(ProgressClaim.tenant_id == self.tenant_id)
        if project_id:
            query = query.where(
                ProgressClaim.contract_id.in_(
                    select(Contract.id).where(Contract.project_id == project_id)
                )
            )
        claims = self.db.scalars(query).all()

        by_status = {}
        total_claimed = Decimal("0")
        total_paid = Decimal("0")
        for claim in claims:
            by_status[claim.status] = by_status.get(claim.status, 0) + 1
            total_claimed += claim.total_amount
            if claim.status == "paid":
                total_paid += claim.total_amount

        return {
            "claims_by_status": by_status,
            "total_claims": len(claims),
            "total_claimed": float(total_claimed),
            "total_paid": float(total_paid),
            "outstanding_claims": float(total_claimed - total_paid),
        }

    # -------------------------------------------------------------------
    # Construction Pack dashboards
    # -------------------------------------------------------------------

    def get_project_health_dashboard(self, project_id = None) -> dict:
        """Project health dashboard for construction pack."""
        if project_id:
            health = self.compute_project_health(project_id)
            margin = self.compute_project_margin(project_id)
            claims = self.compute_claims_kpi(project_id)
            procurement = self.compute_procurement_pipeline(project_id)
            contracts = self.compute_contract_status(project_id)
            return {
                "scope": "single_project",
                "project_id": str(project_id),
                "health": health,
                "margin": margin,
                "claims": claims,
                "procurement": procurement,
                "contracts": contracts,
            }

        # Portfolio-level
        projects = self.db.scalars(
            select(Project).where(Project.tenant_id == self.tenant_id)
        ).all()
        portfolio = {
            "total_projects": len(projects),
            "by_status": {},
            "total_budget": Decimal("0"),
            "at_risk_projects": [],
        }
        for p in projects:
            portfolio["by_status"][p.status] = portfolio["by_status"].get(p.status, 0) + 1
            portfolio["total_budget"] += p.budget
            h = self.compute_project_health(p.id)
            if h.get("risk_level") == "high":
                portfolio["at_risk_projects"].append({
                    "project_id": str(p.id),
                    "project_name": p.name,
                    "risk_level": h.get("risk_level"),
                    "utilization_pct": h.get("utilization_pct"),
                })

        return {
            "scope": "portfolio",
            "portfolio": portfolio,
            "claims": self.compute_claims_kpi(),
            "procurement": self.compute_procurement_pipeline(),
            "contracts": self.compute_contract_status(),
        }

    def get_cash_projection(self, months: int = 3) -> dict:
        """Simple cash projection based on payables (unpaid supplier invoices) and receivables."""
        unpaid_invoices = self.db.scalars(
            select(SupplierInvoice).where(
                SupplierInvoice.tenant_id == self.tenant_id,
                SupplierInvoice.status.in_(["pending_approval", "approved"]),
            )
        ).all()
        upcoming_payments = []
        total_payable = Decimal("0")
        for inv in unpaid_invoices:
            total_payable += inv.total_amount
            upcoming_payments.append({
                "invoice_number": inv.invoice_number,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "amount": float(inv.total_amount),
                "status": inv.status,
            })

        return {
            "projection_period_months": months,
            "unpaid_supplier_invoices": len(unpaid_invoices),
            "total_payable": float(total_payable),
            "upcoming_payments": upcoming_payments[:20],
        }

    # -------------------------------------------------------------------
    # Construction Pack rules
    # -------------------------------------------------------------------

    def create_construction_rules(self) -> list[dict]:
        """Return construction-specific rule definitions ready for the Rules Engine."""
        return [
            {
                "name": "Budget threshold warning",
                "code": "construction_budget_threshold_warning",
                "event_type": "construction.budget.created",
                "conditions": [
                    {"field": "budget.total_amount", "operator": "gte", "value": 100000},
                ],
                "actions": [
                    {"type": "notify", "role": "admin", "title": "High-value budget created",
                     "message": "A budget exceeding 100,000 has been created. Review required."},
                    {"type": "audit", "message": "Budget threshold rule fired"},
                ],
            },
            {
                "name": "Claim approval required for large claims",
                "code": "construction_claim_approval_required",
                "event_type": "construction.progress_claim.created",
                "conditions": [
                    {"field": "claim.total_amount", "operator": "gte", "value": 50000},
                ],
                "actions": [
                    {"type": "notify", "role": "admin", "title": "Large claim submitted",
                     "message": "A progress claim exceeding 50,000 requires review."},
                ],
            },
            {
                "name": "PO approval gate for high value",
                "code": "construction_po_approval_gate",
                "event_type": "construction.purchase_order.created",
                "conditions": [
                    {"field": "purchase_order.total_amount", "operator": "gte", "value": 25000},
                ],
                "actions": [
                    {"type": "notify", "role": "admin", "title": "High-value PO created",
                     "message": "A purchase order exceeding 25,000 has been created."},
                ],
            },
            {
                "name": "GRN to Invoice matching notice",
                "code": "construction_grn_invoice_matching",
                "event_type": "construction.supplier_invoice.created",
                "conditions": [],
                "actions": [
                    {"type": "audit", "message": "Supplier invoice created - GRN matching should be verified"},
                ],
            },
        ]

    # -------------------------------------------------------------------
    # Construction-specific events
    # -------------------------------------------------------------------

    def publish_project_event(self, project: Project, event_type_suffix: str,
                              actor_id, request_id: str | None = None) -> None:
        publish_event(
            self.db,
            tenant_id=self.tenant_id,
            event_type=f"construction.project.{event_type_suffix}",
            entity_type="project",
            entity_id=str(project.id),
            actor_id=str(actor_id),
            payload={"code": project.code, "name": project.name, "status": project.status},
            request_id=request_id,
        )

    def publish_contract_event(self, contract: Contract, event_type_suffix: str,
                               actor_id, request_id: str | None = None) -> None:
        publish_event(
            self.db,
            tenant_id=self.tenant_id,
            event_type=f"construction.contract.{event_type_suffix}",
            entity_type="contract",
            entity_id=str(contract.id),
            actor_id=str(actor_id),
            payload={"contract_number": contract.contract_number, "title": contract.title, "status": contract.status},
            request_id=request_id,
        )

    # -------------------------------------------------------------------
    # Construction-specific financial integration helpers
    # -------------------------------------------------------------------

    def link_invoice_to_financials(self, supplier_invoice: SupplierInvoice,
                                   debit_account_id, credit_account_id) -> JournalEntry | None:
        """Create a journal entry for an approved supplier invoice."""
        if supplier_invoice.status != "approved":
            return None

        entry = JournalEntry(
            tenant_id=self.tenant_id,
            reference_type="supplier_invoice",
            reference_id=supplier_invoice.id,
            reference_number=supplier_invoice.invoice_number,
            description=f"Supplier invoice {supplier_invoice.invoice_number}",
            posted_by=supplier_invoice.approved_by,
            posted_at=supplier_invoice.approved_at or __import__("datetime").datetime.now(),
            currency=supplier_invoice.currency,
        )
        self.db.add(entry)
        self.db.flush()

        # Debit: Purchases / GRNI
        self.db.add(JournalLine(
            entry_id=entry.id,
            account_id=debit_account_id,
            debit=supplier_invoice.total_amount,
            credit=Decimal("0"),
            description=f"Goods/services from invoice {supplier_invoice.invoice_number}",
        ))
        # Credit: Accounts Payable
        self.db.add(JournalLine(
            entry_id=entry.id,
            account_id=credit_account_id,
            debit=Decimal("0"),
            credit=supplier_invoice.total_amount,
            description=f"Accounts payable for invoice {supplier_invoice.invoice_number}",
        ))
        self.db.flush()
        return entry


# ---------------------------------------------------------------------------
# Construction-specific AI Agent
# ---------------------------------------------------------------------------

class ConstructionAnalystAgent:
    """AI agent specialized for construction project analysis."""

    def __init__(self, pack_service: ConstructionPackService):
        self.pack = pack_service

    def analyze_project_health(self, project_id) -> dict:
        health = self.pack.compute_project_health(project_id)
        margin = self.pack.compute_project_margin(project_id)
        claims = self.pack.compute_claims_kpi(project_id)

        findings = []
        if health.get("risk_level") == "high":
            findings.append(f"Project is at HIGH risk: budget utilization at {health.get('utilization_pct')}%")
        if margin.get("margin_pct", 0) < 10:
            findings.append(f"Low margin: {margin.get('margin_pct')}% - review cost commitments")
        if claims.get("outstanding_claims", 0) > 0:
            findings.append(f"{claims['outstanding_claims']} outstanding claim amount pending")

        return {
            "project_id": str(project_id),
            "health_summary": health,
            "margin_summary": margin,
            "claims_summary": claims,
            "findings": findings,
            "recommendations": self._generate_recommendations(health, margin, claims),
        }

    def _generate_recommendations(self, health, margin, claims) -> list[str]:
        recs = []
        if health.get("risk_level") == "high":
            recs.append("Review active purchase orders and claims to reduce exposure")
        if margin.get("margin_pct", 0) < 10:
            recs.append("Evaluate change orders and cost impact before further commitments")
        if claims.get("outstanding_claims", 0) > 0:
            recs.append("Follow up on outstanding progress claims to improve cash flow")
        if not recs:
            recs.append("Project performing within expected parameters")
        return recs


# ---------------------------------------------------------------------------
# Construction Pack initialization
# ---------------------------------------------------------------------------

def get_construction_pack_service(db: Session, tenant_id) -> ConstructionPackService:
    return ConstructionPackService(db, tenant_id)
