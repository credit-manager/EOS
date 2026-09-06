from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from eos_v2.application.ai_composer.providers import OpenAICompatibleComposerProvider
from eos_v2.application.ai_composer.service import AIComposerService
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
    )


@router.post("/proposals", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
def create_proposal(request: Request, payload: ProposalRequest, identity=Depends(get_current_identity)) -> ProposalResponse:
    require_permission(identity, Permission.ADMIN)
    with request.app.state.database.session() as session:
        try:
            proposal = _service(request, session).propose(payload.prompt)
            session.commit()
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
    with request.app.state.database.session() as session:
        try:
            proposal = _service(request, session).get(proposal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Proposal not found") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=404, detail="Proposal not found") from exc
    return _response(proposal)


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalResponse)
def approve_proposal(request: Request, proposal_id: UUID, identity=Depends(get_current_identity)) -> ProposalResponse:
    require_permission(identity, Permission.ADMIN)
    with request.app.state.database.session() as session:
        try:
            proposal = _service(request, session).approve(proposal_id)
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
    with request.app.state.database.session() as session:
        try:
            proposal = _service(request, session).reject(proposal_id)
            session.commit()
        except KeyError as exc:
            session.rollback()
            raise HTTPException(status_code=404, detail="Proposal not found") from exc
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=404, detail="Proposal not found") from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(proposal)
