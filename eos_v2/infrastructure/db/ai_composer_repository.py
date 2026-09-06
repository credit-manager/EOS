from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from eos_v2.domain.ai_composer.entities import ComposerProposal, ProposalChange, ProposalStatus
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition
from eos_v2.infrastructure.db.ai_composer_models import ComposerProposalModel


def _serialize(proposal: ComposerProposal) -> list[dict]:
    return [
        {
            "rationale": change.rationale,
            "entity": {
                "id": str(change.entity.id),
                "tenant_id": str(change.entity.tenant_id),
                "name": change.entity.name,
                "label": change.entity.label,
                "version": change.entity.version,
                "published": change.entity.published,
                "fields": [
                    {"name": f.name, "field_type": f.field_type.value, "required": f.required, "unique": f.unique}
                    for f in change.entity.fields
                ],
                "relationships": [
                    {"name": r.name, "target_entity_id": str(r.target_entity_id), "required": r.required}
                    for r in change.entity.relationships
                ],
            },
        }
        for change in proposal.changes
    ]


def _deserialize_changes(items: list[dict]) -> tuple[ProposalChange, ...]:
    result: list[ProposalChange] = []
    for item in items:
        raw = item["entity"]
        entity = EntityDefinition(
            id=UUID(raw["id"]),
            tenant_id=UUID(raw["tenant_id"]),
            name=raw["name"],
            label=raw.get("label", ""),
            version=int(raw.get("version", 0)),
            fields=tuple(FieldDefinition(name=f["name"], field_type=FieldType(f["field_type"]), required=bool(f.get("required")), unique=bool(f.get("unique"))) for f in raw.get("fields", [])),
            relationships=tuple(RelationshipDefinition(name=r["name"], target_entity_id=UUID(r["target_entity_id"]), required=bool(r.get("required"))) for r in raw.get("relationships", [])),
            published=bool(raw.get("published", False)),
        )
        result.append(ProposalChange(entity=entity, rationale=item.get("rationale", "AI generated metadata proposal")))
    return tuple(result)


class SqlAlchemyComposerProposalRepository:
    def __init__(self, session) -> None:
        self.session = session

    def add(self, proposal: ComposerProposal) -> None:
        self.session.add(ComposerProposalModel(
            id=proposal.id,
            tenant_id=proposal.tenant_id,
            actor_id=proposal.actor_id,
            prompt=proposal.prompt,
            provider=proposal.provider,
            status=proposal.status.value,
            changes=_serialize(proposal),
            created_at=proposal.created_at,
            decided_at=proposal.decided_at,
        ))

    def get(self, proposal_id: UUID) -> ComposerProposal:
        model = self.session.query(ComposerProposalModel).filter_by(id=proposal_id).first()
        if model is None:
            raise KeyError(proposal_id)
        return ComposerProposal(
            id=model.id,
            tenant_id=model.tenant_id,
            actor_id=model.actor_id,
            prompt=model.prompt,
            provider=model.provider,
            status=ProposalStatus(model.status),
            changes=_deserialize_changes(model.changes),
            created_at=model.created_at,
            decided_at=model.decided_at,
        )

    def update(self, proposal: ComposerProposal) -> None:
        model = self.session.query(ComposerProposalModel).filter_by(id=proposal.id, tenant_id=proposal.tenant_id).first()
        if model is None:
            raise KeyError(proposal.id)
        model.status = proposal.status.value
        model.decided_at = proposal.decided_at
