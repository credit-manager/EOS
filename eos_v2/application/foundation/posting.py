from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.application.accounting.module_posting import PostingInstruction
from eos_v2.modules.projects.costs import ProjectCost
from eos_v2.modules.purchasing import PurchaseOrder, PurchaseOrderStatus
from eos_v2.modules.sales import SalesOrder, SalesOrderStatus


def sales_confirmation_posting(order: SalesOrder, receivable_account: UUID, revenue_account: UUID) -> PostingInstruction:
    if order.tenant_id != get_tenant_context().tenant_id:
        raise PermissionError("Cross-tenant accounting operation denied")
    if order.status is not SalesOrderStatus.CONFIRMED:
        raise ValueError("Only confirmed sales orders can produce a posting instruction")
    amount = sum((line.total for line in order.lines), Decimal("0"))
    return PostingInstruction(receivable_account, revenue_account, amount, "sales.order", order.id)


def purchase_confirmation_posting(order: PurchaseOrder, inventory_account: UUID, payable_account: UUID) -> PostingInstruction:
    if order.tenant_id != get_tenant_context().tenant_id:
        raise PermissionError("Cross-tenant accounting operation denied")
    if order.status is not PurchaseOrderStatus.CONFIRMED:
        raise ValueError("Only confirmed purchase orders can produce a posting instruction")
    amount = sum((line.total for line in order.lines), Decimal("0"))
    return PostingInstruction(inventory_account, payable_account, amount, "purchasing.order", order.id)


def project_cost_posting(cost: ProjectCost, project_cost_account: UUID, payable_account: UUID) -> PostingInstruction:
    if cost.tenant_id != get_tenant_context().tenant_id:
        raise PermissionError("Cross-tenant accounting operation denied")
    return PostingInstruction(project_cost_account, payable_account, cost.amount, cost.posting_source(), cost.id)
