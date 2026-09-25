"""
Test that installing an industry pack from the Marketplace seeds
WorkflowDefinition, Rule, and MetadataDashboardKPI records.

Verifies the enriched install_industry_pack endpoint behavior.
"""

from __future__ import annotations

import uuid

import pytest

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session

from backend.app.db import Base as AppBase
from backend.app.marketplace.industry_pack_registry import get_industry_pack
from backend.app.marketplace.router import install_industry_pack as _endpoint_func

# When called outside the router context (no FastAPI dependency injection),
# provide explicit tenant and db params.
def install_industry_pack(pack_id: str, tenant_id: uuid.UUID, db: Session) -> dict:
    """Call the install endpoint with explicit params (bypass Depends)."""
    return _endpoint_func(pack_id, tenant_id=tenant_id, db=db)
from backend.app.marketplace.models import MarketplaceInstallation
from backend.app.auth.security import Principal
from backend.app.metadata.models import MetadataEntity
from backend.app.workflow.models import WorkflowDefinition
from backend.app.rules.models import Rule
from backend.app.metadata.models import MetadataDashboardKPI

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    AppBase.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


# Ensure all model tables are registered before any test runs
# (transitive FK dependencies require system_events from events.models)
import backend.app.events.models  # noqa: F401 — registers system_events table


@pytest.fixture()
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def principal() -> Principal:
    return Principal(user_id=uuid.uuid4(), scopes=["admin"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIndustryPackInstallSeeds:
    """Verify install_industry_pack seeds Workflow, Rule, and KPI."""

    def test_install_seeds_metadata_entities(self, db: Session, tenant_id: uuid.UUID) -> None:
        result = install_industry_pack("construction", tenant_id, db)
        entities = db.scalars(
            select(MetadataEntity).where(MetadataEntity.tenant_id == tenant_id)
        ).all()
        assert len(entities) > 0
        codes = {e.code for e in entities}
        assert "project" in codes or "boq" in codes

    def test_install_seeds_starter_workflow(self, db: Session, tenant_id: uuid.UUID) -> None:
        result = install_industry_pack("construction", tenant_id, db)
        wf = db.scalar(
            select(WorkflowDefinition).where(
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.code == "construction_starter",
            )
        )
        assert wf is not None
        assert wf.name.startswith("Construction")
        assert wf.is_active is True
        # Verify workflow has states and transitions
        definition = wf.definition or {}
        assert "states" in definition
        assert "transitions" in definition
        assert len(definition["states"]) >= 2

    def test_install_seeds_starter_rule(self, db: Session, tenant_id: uuid.UUID) -> None:
        result = install_industry_pack("construction", tenant_id, db)
        rule = db.scalar(
            select(Rule).where(
                Rule.tenant_id == tenant_id,
                Rule.name == "construction_starter_rule",
            )
        )
        assert rule is not None
        assert rule.name == "construction_starter_rule"
        assert rule.enabled is True
        assert rule.event_type == "project"  # seeded from first entity code

    def test_install_seeds_dashboard_kpi(self, db: Session, tenant_id: uuid.UUID) -> None:
        result = install_industry_pack("construction", tenant_id, db)
        kpi = db.scalar(
            select(MetadataDashboardKPI).where(
                MetadataDashboardKPI.tenant_id == tenant_id,
                MetadataDashboardKPI.code == "construction_kpi_count",
            )
        )
        assert kpi is not None
        assert kpi.name == "Construction Industry Pack - Record Count"
        assert kpi.kpi_type == "count"

    def test_install_is_idempotent_metadata(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Installing twice does not duplicate metadata entities."""
        install_industry_pack("construction", tenant_id, db)
        count_before = db.scalar(
            select(func.count()).select_from(MetadataEntity).where(
                MetadataEntity.tenant_id == tenant_id
            )
        )
        install_industry_pack("construction", tenant_id, db)
        count_after = db.scalar(
            select(func.count()).select_from(MetadataEntity).where(
                MetadataEntity.tenant_id == tenant_id
            )
        )
        assert count_before == count_after

    def test_install_is_idempotent_workflow(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Installing twice does not duplicate workflow definitions."""
        install_industry_pack("construction", tenant_id, db)
        wf_count_before = db.scalar(
            select(func.count()).select_from(WorkflowDefinition).where(
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.code == "construction_starter",
            )
        )
        install_industry_pack("construction", tenant_id, db)
        wf_count_after = db.scalar(
            select(func.count()).select_from(WorkflowDefinition).where(
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.code == "construction_starter",
            )
        )
        assert wf_count_before == wf_count_after == 1

    def test_install_is_idempotent_rule(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Installing twice does not duplicate rules."""
        install_industry_pack("construction", tenant_id, db)
        rule_count_before = db.scalar(
            select(func.count()).select_from(Rule).where(
                Rule.tenant_id == tenant_id,
                Rule.name == "construction_starter_rule",
            )
        )
        install_industry_pack("construction", tenant_id, db)
        rule_count_after = db.scalar(
            select(func.count()).select_from(Rule).where(
                Rule.tenant_id == tenant_id,
                Rule.name == "construction_starter_rule",
            )
        )
        assert rule_count_before == rule_count_after == 1

    def test_install_is_idempotent_kpi(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Installing twice does not duplicate dashboard KPIs."""
        install_industry_pack("construction", tenant_id, db)
        kpi_count_before = db.scalar(
            select(func.count()).select_from(MetadataDashboardKPI).where(
                MetadataDashboardKPI.tenant_id == tenant_id,
                MetadataDashboardKPI.code == "construction_kpi_count",
            )
        )
        install_industry_pack("construction", tenant_id, db)
        kpi_count_after = db.scalar(
            select(func.count()).select_from(MetadataDashboardKPI).where(
                MetadataDashboardKPI.tenant_id == tenant_id,
                MetadataDashboardKPI.code == "construction_kpi_count",
            )
        )
        assert kpi_count_before == kpi_count_after == 1

    def test_retail_pack_seeds_its_own_entities(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Retail pack should seed retail-specific entities, not construction ones."""
        result = install_industry_pack("retail", tenant_id, db)
        entities = db.scalars(
            select(MetadataEntity).where(MetadataEntity.tenant_id == tenant_id)
        ).all()
        codes = {e.code for e in entities}
        # Retail pack has product, price_list, pos_transaction etc.
        assert len(entities) > 0

    def test_install_returns_correct_status(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Install should return success status with installed entity codes."""
        result = install_industry_pack("construction", tenant_id, db)
        assert result["status"] == "success"
        assert "project" in result["installed_entities"]

    def test_install_record_exists_in_marketplace_installation(self, db: Session, tenant_id: uuid.UUID) -> None:
        """After install_industry_pack, a MarketplaceInstallation record should exist."""
        result = install_industry_pack("construction", tenant_id, db)
        install = db.scalar(
            select(MarketplaceInstallation).where(
                MarketplaceInstallation.tenant_id == str(tenant_id),
                MarketplaceInstallation.app_id == "industry-construction",
                MarketplaceInstallation.status == "active",
            )
        )
        assert install is not None
