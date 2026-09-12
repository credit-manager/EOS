from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import commit_db, get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/crm", tags=["crm"])


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

@router.post("/contacts", status_code=201, response_model=schemas.ContactResponse)
def create_contact(
    payload: schemas.ContactCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    contact = service.create_contact(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        job_title=payload.job_title,
        lead_source=payload.lead_source,
        status=payload.status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return contact


@router.get("/contacts", response_model=list[schemas.ContactResponse])
def list_contacts(
    status: str | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_contacts(db, tenant_id=tenant_id, status=status)


@router.get("/contacts/{contact_id}", response_model=schemas.ContactResponse)
def get_contact(
    contact_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_contact(db, tenant_id=tenant_id, contact_id=contact_id)


@router.patch("/contacts/{contact_id}", response_model=schemas.ContactResponse)
def update_contact(
    contact_id: UUID,
    payload: schemas.ContactUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    contact = service.update_contact(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contact_id=contact_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return contact


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(
    contact_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_contact(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contact_id=contact_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

@router.post("/opportunities", status_code=201, response_model=schemas.OpportunityResponse)
def create_opportunity(
    payload: schemas.OpportunityCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    opp = service.create_opportunity(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        title=payload.title,
        contact_id=payload.contact_id,
        value=payload.value,
        currency=payload.currency,
        stage=payload.stage,
        probability=payload.probability,
        expected_close_date=payload.expected_close_date,
        assigned_to=payload.assigned_to,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return opp


@router.get("/opportunities", response_model=list[schemas.OpportunityResponse])
def list_opportunities(
    stage: str | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_opportunities(db, tenant_id=tenant_id, stage=stage)


@router.get("/opportunities/{opportunity_id}", response_model=schemas.OpportunityResponse)
def get_opportunity(
    opportunity_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_opportunity(db, tenant_id=tenant_id, opportunity_id=opportunity_id)


@router.patch("/opportunities/{opportunity_id}", response_model=schemas.OpportunityResponse)
def update_opportunity(
    opportunity_id: UUID,
    payload: schemas.OpportunityUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    opp = service.update_opportunity(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        opportunity_id=opportunity_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return opp


@router.post("/opportunities/{opportunity_id}/stage", response_model=schemas.OpportunityResponse)
def transition_opportunity_stage(
    opportunity_id: UUID,
    stage: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    opp = service.transition_opportunity_stage(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        opportunity_id=opportunity_id,
        stage=stage,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return opp


@router.delete("/opportunities/{opportunity_id}", status_code=204)
def delete_opportunity(
    opportunity_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_opportunity(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        opportunity_id=opportunity_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

@router.post("/activities", status_code=201, response_model=schemas.ActivityResponse)
def create_activity(
    payload: schemas.ActivityCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    activity = service.create_activity(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contact_id=payload.contact_id,
        opportunity_id=payload.opportunity_id,
        activity_type=payload.activity_type,
        subject=payload.subject,
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return activity


@router.get("/activities", response_model=list[schemas.ActivityResponse])
def list_activities(
    contact_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_activities(db, tenant_id=tenant_id, contact_id=contact_id)


@router.get("/activities/{activity_id}", response_model=schemas.ActivityResponse)
def get_activity(
    activity_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_activity(db, tenant_id=tenant_id, activity_id=activity_id)


@router.patch("/activities/{activity_id}", response_model=schemas.ActivityResponse)
def update_activity(
    activity_id: UUID,
    payload: schemas.ActivityUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    activity = service.update_activity(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        activity_id=activity_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return activity


@router.post("/activities/{activity_id}/complete", response_model=schemas.ActivityResponse)
def complete_activity(
    activity_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    activity = service.complete_activity(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        activity_id=activity_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return activity


@router.delete("/activities/{activity_id}", status_code=204)
def delete_activity(
    activity_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_activity(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        activity_id=activity_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@router.post("/notes", status_code=201, response_model=schemas.NoteResponse)
def create_note(
    payload: schemas.NoteCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    note = service.create_note(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contact_id=payload.contact_id,
        opportunity_id=payload.opportunity_id,
        content=payload.content,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return note


@router.get("/notes", response_model=list[schemas.NoteResponse])
def list_notes(
    contact_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_notes(db, tenant_id=tenant_id, contact_id=contact_id)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_note(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        note_id=note_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
