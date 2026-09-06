from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, clear_tenant_context, set_tenant_context
from eos_v2.application.ai_composer.service import AIComposerService
from eos_v2.domain.ai_composer.entities import ProposalChange, ProposalStatus
from eos_v2.domain.metadata.entities import EntityDefinition


@pytest.fixture(autouse=True)
def clean_tenant_context():
    clear_tenant_context()
    yield
    clear_tenant_context()


class Provider:
    name = "test"

    def __init__(self, changes):
        self.changes = changes

    def propose(self, prompt, tenant_id):
        return tuple(ProposalChange(EntityDefinition(tenant_id=tenant_id, name=name), "test proposal") for name in self.changes)


class ProposalRepo:
    def __init__(self):
        self.items = {}

    def add(self, proposal):
        self.items[proposal.id] = proposal

    def get(self, proposal_id):
        if proposal_id not in self.items:
            raise KeyError(proposal_id)
        return self.items[proposal_id]

    def update(self, proposal):
        self.items[proposal.id] = proposal


class MetadataRepo:
    def __init__(self):
        self.items = {}

    def get(self, entity_id):
        if entity_id not in self.items:
            raise KeyError(entity_id)
        return self.items[entity_id]

    def get_latest_version(self, entity_name):
        versions = [e.version for e in self.items.values() if e.name == entity_name]
        return max(versions) if versions else None

    def add(self, definition):
        self.items[definition.id] = definition


def test_ai_proposal_is_draft_until_admin_approval():
    tenant = uuid4()
    actor = uuid4()
    set_tenant_context(TenantContext(tenant, actor))
    proposals = ProposalRepo()
    metadata = MetadataRepo()
    service = AIComposerService(proposals, Provider(["customer"]), metadata)

    proposal = service.propose("Create a customer entity")
    assert proposal.status is ProposalStatus.DRAFT
    assert proposal.decided_by is None
    assert not metadata.items

    approved = service.approve(proposal.id)
    assert approved.status is ProposalStatus.APPROVED
    assert approved.decided_by == actor
    assert approved.decided_at is not None
    assert len(metadata.items) == 1
    assert next(iter(metadata.items.values())).published


def test_ai_proposal_cannot_cross_tenants():
    tenant_a = uuid4()
    tenant_b = uuid4()
    actor = uuid4()
    set_tenant_context(TenantContext(tenant_a, actor))
    proposals = ProposalRepo()
    metadata = MetadataRepo()
    service = AIComposerService(proposals, Provider(["customer"]), metadata)
    proposal = service.propose("Create a customer entity")

    set_tenant_context(TenantContext(tenant_b, actor))
    with pytest.raises(PermissionError):
        service.get(proposal.id)
