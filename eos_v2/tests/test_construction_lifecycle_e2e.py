from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.accounting.module_posting import PostingInstruction
from eos_v2.application.accounting.service import AccountingService
from eos_v2.application.foundation.posting import project_cost_posting, purchase_confirmation_posting
from eos_v2.application.metadata.service import MetadataService
from eos_v2.application.records.service import DynamicRecordService, InMemoryRecordRepository
from eos_v2.domain.accounting.entities import Account, AccountType, JournalEntry
from eos_v2.modules.industry.construction_flow import ConstructionFlow, ContractMode, FlowStatus
from eos_v2.modules.industry.construction_real_estate import build_pack
from eos_v2.modules.inventory import StockBalance
from eos_v2.modules.projects.costs import ProjectCost
from eos_v2.modules.purchasing import PurchaseOrderLine, PurchaseOrderStatus
from eos_v2.application.foundation.services import FoundationService


class InMemoryAccountingRepository:
    def __init__(self, accounts: tuple[Account, ...]) -> None:
        self.accounts = {account.id: account for account in accounts}
        self.entries: list[JournalEntry] = []

    def get_account(self, account_id: UUID) -> Account:
        return self.accounts[account_id]

    def save_entry(self, entry: JournalEntry) -> None:
        self.entries.append(entry)


def test_construction_real_estate_lifecycle_integrates_metadata_records_operations_and_accounting() -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    context_token = set_tenant_context(TenantContext(tenant_id, actor_id))
    try:
        # 1. Install/publish the same metadata definitions used by the industry pack.
        pack = build_pack(tenant_id)
        metadata = MetadataService()
        definitions = {definition.name: metadata.publish(definition) for definition in pack.entities}
        records = DynamicRecordService(InMemoryRecordRepository())

        land = records.create(
            definitions["land_parcel"],
            {"code": "LAND-001", "area": "1000", "status": "acquired"},
        )
        project = records.create(
            definitions["development_project"],
            {"code": "PRJ-001", "name": "EOS Residence", "budget": "350", "land_parcel_id": str(land.id)},
        )
        unit = records.create(
            definitions["property_unit"],
            {"code": "UNIT-001", "unit_type": "villa", "area": "250", "list_price": "500", "status": "ready", "project_id": str(project.id)},
        )
        work_package = records.create(
            definitions["construction_work_package"],
            {"code": "WP-001", "name": "Core Construction", "planned_cost": "250", "status": "planned", "project_id": str(project.id)},
        )
        customer_id = uuid4()
        contract_record = records.create(
            definitions["property_contract"],
            {"contract_number": "CON-001", "customer_id": str(customer_id), "contract_value": "500", "status": "draft", "unit_id": str(unit.id)},
        )

        # 2. Run the operational purchasing flow and receive construction material into inventory.
        supplier_id = uuid4()
        purchase = FoundationService.create_purchase_order(
            supplier_id,
            "USD",
            (PurchaseOrderLine(uuid4(), Decimal("1"), Decimal("250")),),
        )
        purchase = FoundationService.transition_purchase_order(purchase, PurchaseOrderStatus.CONFIRMED)
        purchase_posting = purchase_confirmation_posting(purchase, uuid4(), uuid4())

        # The foundation service deliberately keeps persistence behind a repository. For this E2E,
        # carry the resulting balance through the same application service boundary.
        _, stock = FoundationService.apply_inventory_movement(
            purchase.lines[0].item_id,
            purchase.lines[0].quantity,
            "purchasing.receipt",
            StockBalance(tenant_id=tenant_id, item_id=purchase.lines[0].item_id, quantity=Decimal("0")),
        )
        assert stock.quantity == Decimal("1")

        # 3. Attribute the remaining project spend to the work package.
        project_cost = ProjectCost(
            tenant_id=tenant_id,
            project_id=project.id,
            work_package_id=work_package.id,
            amount=Decimal("100"),
            category="land",
            source="land.acquisition",
        )
        cost_posting = project_cost_posting(project_cost, uuid4(), uuid4())

        # 4. Drive the construction lifecycle from acquisition to close.
        flow = ConstructionFlow(
            tenant_id=tenant_id,
            land_id=land.id,
            project_id=project.id,
            unit_id=unit.id,
            customer_id=customer_id,
            mode=ContractMode.SALE,
            land_cost=project_cost.amount,
            construction_cost=purchase.lines[0].total,
            contract_value=Decimal("500"),
        )
        flow = flow.start_development().mark_unit_ready().contract().deliver().close()

        # 5. Post operational events into the accounting kernel using the same tenant context.
        cash_or_inventory = purchase_posting.debit_account_id
        payable = purchase_posting.credit_account_id
        cost_account = cost_posting.debit_account_id
        project_payable = cost_posting.credit_account_id
        accounts = (
            Account(tenant_id, "1200", "Inventory", AccountType.ASSET, id=cash_or_inventory),
            Account(tenant_id, "2100", "Accounts Payable", AccountType.LIABILITY, id=payable),
            Account(tenant_id, "5100", "Project Cost", AccountType.EXPENSE, id=cost_account),
            Account(tenant_id, "2110", "Project Payable", AccountType.LIABILITY, id=project_payable),
        )
        accounting_repository = InMemoryAccountingRepository(accounts)
        accounting = AccountingService(accounting_repository)
        for instruction, description in (
            (purchase_posting, "Construction material purchase"),
            (cost_posting, "Land acquisition project cost"),
        ):
            accounting.post(
                JournalEntry(
                    tenant_id=tenant_id,
                    entry_date=date.today(),
                    currency="USD",
                    description=description,
                    lines=instruction.lines(),
                )
            )

        assert contract_record.data["contract_value"] == Decimal("500")
        assert flow.status is FlowStatus.CLOSED
        assert flow.total_cost == Decimal("350")
        assert flow.projected_margin == Decimal("150")
        assert len(accounting_repository.entries) == 2
        assert all(entry.posted for entry in accounting_repository.entries)
        assert all(entry.tenant_id == tenant_id for entry in accounting_repository.entries)
    finally:
        reset_tenant_context(context_token)
