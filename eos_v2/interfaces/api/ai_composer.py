from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from eos_v2.application.ai_composer.providers import OpenAICompatibleComposerProvider
from eos_v2.application.ai_composer.service import AIComposerService
from eos_v2.application.audit.service import record_event
from eos_v2.domain.ai_composer.entities import ProposalStatus
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.ai_composer_repository import SqlAlchemyComposerProposalRepository
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.interfaces.api.auth import get_current_identity, require_permission

router = APIRouter(prefix="/api/v1/ai-composer", tags=["ai-composer"])


class ProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=12000)


class ProposalResponse(BaseModel):
    id: UUID
    status: ProposalStatus
    provider: str
    prompt: str
    changes: list[dict[str, object]]
    created_at: str
    decided_at: str | None
    decided_by: UUID | None


def _service(request: Request, session) -> AIComposerService:
    settings = request.app.state.settings
    provider = OpenAICompatibleComposerProvider(settings.ai_base_url, settings.ai_api_key, settings.ai_model, settings.ai_timeout_seconds)
    return AIComposerService(SqlAlchemyComposerProposalRepository(session), provider, SqlAlchemyMetadataRepository(session))


def _response(proposal) -> ProposalResponse:
    return ProposalResponse(
        id=proposal.id,
        status=proposal.status,
        provider=proposal.provider,
        prompt=proposal.prompt,
        changes=[
            {"entity": change.entity.name, "label": change.entity.label, "version": change.entity.version, "rationale": change.rationale}
            for change in proposal.changes
        ],
        created_at=proposal.created_at.isoformat(),
        decided_at=proposal.decided_at.isoformat() if proposal.decided_at else None,
        decided_by=proposal.decided_by,
    )


def _require_database(request: Request):
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return database


@router.post("/proposals", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
def create_proposal(request: Request, payload: ProposalRequest, identity=Depends(get_current_identity)) -> ProposalResponse:
    require_permission(identity, Permission.ADMIN)
    with _require_database(request).session() as session:
        try:
            proposal = _service(request, session).propose(payload.prompt)
            record_event(
                session,
                action="ai_composer.proposal_created",
                resource_type="ai_composer_proposal",
                resource_id=proposal.id,
                actor_id=identity.actor.id,
                request_id=request.headers.get("X-Request-ID"),
                metadata={"provider": proposal.provider, "change_count": len(proposal.changes)},
            )
            session.commit()
        except httpx.HTTPError as exc:
            session.rollback()
            raise HTTPException(status_code=502, detail="AI provider unavailable") from exc
        except RuntimeError as exc:
            session.rollback()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            session.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _response(proposal)


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
def get_proposal(request: Request, proposal_id: UUID, identity=Depends(get_current_identity)) -> ProposalResponse:
    require_permission(identity, Permission.READ)
    with _require_database(request).session() as session:
        try:
            proposal = _service(request, session).get(proposal_id)
        except (KeyError, PermissionError) as exc:
            raise HTTPException(status_code=404, detail="Proposal not found") from exc
    return _response(proposal)


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalResponse)
def approve_proposal(request: Request, proposal_id: UUID, identity=Depends(get_current_identity)) -> ProposalResponse:
    require_permission(identity, Permission.ADMIN)
    with _require_database(request).session() as session:
        try:
            proposal = _service(request, session).approve(proposal_id)
            record_event(
                session,
                action="ai_composer.proposal_approved",
                resource_type="ai_composer_proposal",
                resource_id=proposal.id,
                actor_id=identity.actor.id,
                request_id=request.headers.get("X-Request-ID"),
            )
            session.commit()
        except KeyError as exc:
            session.rollback()
            raise HTTPException(status_code=404, detail="Proposal not found") from exc
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(proposal)


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalResponse)
def reject_proposal(request: Request, proposal_id: UUID, identity=Depends(get_current_identity)) -> ProposalResponse:
    require_permission(identity, Permission.ADMIN)
    with _require_database(request).session() as session:
        try:
            proposal = _service(request, session).reject(proposal_id)
            record_event(
                session,
                action="ai_composer.proposal_rejected",
                resource_type="ai_composer_proposal",
                resource_id=proposal.id,
                actor_id=identity.actor.id,
                request_id=request.headers.get("X-Request-ID"),
            )
            session.commit()
        except KeyError as exc:
            session.rollback()
            raise HTTPException(status_code=404, detail="Proposal not found") from exc
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(proposal)
