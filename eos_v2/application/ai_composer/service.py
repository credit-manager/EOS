from __future__ import annotations

from dataclasses import replace
from typing import Protocol
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.ai_composer.entities import ComposerProposal, ProposalChange, ProposalStatus
from eos_v2.domain.metadata.entities import EntityDefinition
from eos_v2.application.metadata.versioning import MetadataVersioningService


class ComposerProvider(Protocol):
    name: str

    def propose(self, prompt: str, tenant_id: UUID) -> tuple[ProposalChange, ...]: ...


class ProposalRepository(Protocol):
    def add(self, proposal: ComposerProposal) -> None: ...
    def get(self, proposal_id: UUID) -> ComposerProposal: ...
    def update(self, proposal: ComposerProposal) -> None: ...


class AIComposerService:
    """AI proposes metadata only; policy and a human approval perform publication."""

    def __init__(self, repository: ProposalRepository, provider: ComposerProvider, metadata_repository) -> None:
        self.repository = repository
        self.provider = provider
        self.metadata_repository = metadata_repository

    def propose(self, prompt: str) -> ComposerProposal:
        context = get_tenant_context()
        changes = self.provider.propose(prompt, context.tenant_id)
        proposal = ComposerProposal(
            tenant_id=context.tenant_id,
            actor_id=context.actor_id,
            prompt=prompt,
            changes=changes,
            provider=self.provider.name,
        )
        self.repository.add(proposal)
        return proposal

    def get(self, proposal_id: UUID) -> ComposerProposal:
        proposal = self.repository.get(proposal_id)
        self._assert_tenant(proposal.tenant_id)
        return proposal

    def approve(self, proposal_id: UUID) -> ComposerProposal:
        proposal = self.get(proposal_id)
        if proposal.status is not ProposalStatus.DRAFT:
            raise ValueError("Only draft proposals can be approved")
        context = get_tenant_context()
        for change in proposal.changes:
            if change.entity.tenant_id != context.tenant_id:
                raise PermissionError("Proposal contains a cross-tenant metadata change")
        versioning = MetadataVersioningService(self.metadata_repository)
        for change in proposal.changes:
            versioning.publish_new_version(change.entity)
        approved = replace(proposal, status=ProposalStatus.APPROVED, decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        self.repository.update(approved)
        return approved

    def reject(self, proposal_id: UUID) -> ComposerProposal:
        proposal = self.get(proposal_id)
        if proposal.status is not ProposalStatus.DRAFT:
            raise ValueError("Only draft proposals can be rejected")
        rejected = replace(proposal, status=ProposalStatus.REJECTED, decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        self.repository.update(rejected)
        return rejected

    @staticmethod
    def _assert_tenant(tenant_id: UUID) -> None:
        if tenant_id != get_tenant_context().tenant_id:
            raise PermissionError("Proposal tenant does not match current tenant")
