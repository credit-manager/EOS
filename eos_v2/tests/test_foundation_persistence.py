from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.infrastructure.db.foundation_models import FoundationBase
from eos_v2.infrastructure.db.foundation_repository import FoundationRepository
from eos_v2.modules.hr import Employee
from eos_v2.modules.projects import Project, ProjectStatus


def test_foundation_persistence_is_tenant_scoped():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    FoundationBase.metadata.create_all(engine)
    tenant_a, tenant_b = uuid4(), uuid4()
    token = set_tenant_context(TenantContext(tenant_a, uuid4()))
    try:
        employee = Employee(tenant_id=tenant_a, employee_number="E-001", name="Alice", hire_date=date(2026, 1, 1))
        project = Project(tenant_id=tenant_a, code="P-001", name="Build", start_date=date(2026, 1, 1), status=ProjectStatus.PLANNED)
        with Session(engine) as session:
            repo = FoundationRepository(session)
            repo.save_employee(employee)
            repo.save_project(project)
            session.commit()
            assert repo.get_employee(employee.id).name == "Alice"
            assert repo.get_project(project.id).code == "P-001"
    finally:
        reset_tenant_context(token)

    token = set_tenant_context(TenantContext(tenant_b, uuid4()))
    try:
        with Session(engine) as session:
            repo = FoundationRepository(session)
            with pytest.raises(KeyError): repo.get_employee(employee.id)
            with pytest.raises(KeyError): repo.get_project(project.id)
    finally:
        reset_tenant_context(token)


def test_stock_balance_isolated_by_tenant():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    FoundationBase.metadata.create_all(engine)
    item = uuid4()
    tenant_a, tenant_b = uuid4(), uuid4()
    for tenant in (tenant_a, tenant_b):
        token = set_tenant_context(TenantContext(tenant, uuid4()))
        try:
            from eos_v2.application.foundation.services import FoundationService
            with Session(engine) as session:
                repo = FoundationRepository(session)
                movement, balance = FoundationService.apply_inventory_movement(item, Decimal("5"), "receipt", repo.get_stock(item))
                repo.save_inventory(movement, balance)
                session.commit()
                assert repo.get_stock(item).quantity == Decimal("5")
        finally:
            reset_tenant_context(token)
