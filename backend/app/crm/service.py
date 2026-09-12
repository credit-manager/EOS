from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import Activity, Contact, Note, Opportunity

# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

def create_contact(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None = None,
    company: str | None = None,
    job_title: str | None = None,
    lead_source: str | None = None,
    status: str = "lead",
    request_id: str | None = None,
) -> Contact:
    existing = db.scalar(
        select(Contact).where(Contact.tenant_id == tenant_id, Contact.email == email)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="contact email already exists for this tenant")
    contact = Contact(
        tenant_id=tenant_id,
        created_by=user_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        company=company,
        job_title=job_title,
        lead_source=lead_source,
        status=status,
    )
    db.add(contact)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.contact.created",
        resource_type="contact",
        resource_id=contact.id,
        request_id=request_id,
        metadata={"email": email, "first_name": first_name, "last_name": last_name},
    )
    db.flush()
    return contact


def get_contact(db: Session, *, tenant_id: UUID, contact_id: UUID) -> Contact:
    contact = db.get(Contact, contact_id)
    if contact is None or contact.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="contact not found")
    return contact


def list_contacts(db: Session, *, tenant_id: UUID, status: str | None = None) -> list[Contact]:
    stmt = select(Contact).where(Contact.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(Contact.status == status)
    return db.scalars(stmt.order_by(Contact.created_at.desc())).all()


def update_contact(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contact_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Contact:
    contact = get_contact(db, tenant_id=tenant_id, contact_id=contact_id)
    allowed = {
        "first_name", "last_name", "email", "phone", "company",
        "job_title", "lead_source", "status",
    }
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(contact, key, value)
    contact.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.contact.updated",
        resource_type="contact",
        resource_id=contact.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return contact


def delete_contact(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contact_id: UUID,
    request_id: str | None = None,
) -> None:
    contact = get_contact(db, tenant_id=tenant_id, contact_id=contact_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.contact.deleted",
        resource_type="contact",
        resource_id=contact.id,
        request_id=request_id,
    )
    db.delete(contact)
    db.flush()


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------

def create_opportunity(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    title: str,
    contact_id: UUID | None = None,
    value: float = 0,
    currency: str = "USD",
    stage: str = "prospecting",
    probability: int = 0,
    expected_close_date=None,
    assigned_to: UUID | None = None,
    request_id: str | None = None,
) -> Opportunity:
    if contact_id is not None:
        get_contact(db, tenant_id=tenant_id, contact_id=contact_id)
    opp = Opportunity(
        tenant_id=tenant_id,
        created_by=user_id,
        contact_id=contact_id,
        title=title,
        value=value,
        currency=currency,
        stage=stage,
        probability=probability,
        expected_close_date=expected_close_date,
        assigned_to=assigned_to,
    )
    db.add(opp)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.opportunity.created",
        resource_type="opportunity",
        resource_id=opp.id,
        request_id=request_id,
        metadata={"title": title, "stage": stage},
    )
    db.flush()
    return opp


def get_opportunity(db: Session, *, tenant_id: UUID, opportunity_id: UUID) -> Opportunity:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None or opp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="opportunity not found")
    return opp


def list_opportunities(
    db: Session, *, tenant_id: UUID, stage: str | None = None
) -> list[Opportunity]:
    stmt = select(Opportunity).where(Opportunity.tenant_id == tenant_id)
    if stage:
        stmt = stmt.where(Opportunity.stage == stage)
    return db.scalars(stmt.order_by(Opportunity.created_at.desc())).all()


def update_opportunity(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    opportunity_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Opportunity:
    opp = get_opportunity(db, tenant_id=tenant_id, opportunity_id=opportunity_id)
    allowed = {
        "title", "contact_id", "value", "currency", "stage",
        "probability", "expected_close_date", "assigned_to",
    }
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(opp, key, value)
    opp.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.opportunity.updated",
        resource_type="opportunity",
        resource_id=opp.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return opp


def transition_opportunity_stage(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    opportunity_id: UUID,
    stage: str,
    request_id: str | None = None,
) -> Opportunity:
    opp = get_opportunity(db, tenant_id=tenant_id, opportunity_id=opportunity_id)
    valid_transitions = {
        "prospecting": {"qualification"},
        "qualification": {"proposal"},
        "proposal": {"negotiation"},
        "negotiation": {"closed_won", "closed_lost"},
    }
    allowed = valid_transitions.get(opp.stage, set())
    if stage not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition opportunity from '{opp.stage}' to '{stage}'",
        )
    opp.stage = stage
    opp.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action=f"crm.opportunity.{stage}",
        resource_type="opportunity",
        resource_id=opp.id,
        request_id=request_id,
    )
    db.flush()
    return opp


def delete_opportunity(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    opportunity_id: UUID,
    request_id: str | None = None,
) -> None:
    opp = get_opportunity(db, tenant_id=tenant_id, opportunity_id=opportunity_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.opportunity.deleted",
        resource_type="opportunity",
        resource_id=opp.id,
        request_id=request_id,
    )
    db.delete(opp)
    db.flush()


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------

def create_activity(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contact_id: UUID,
    opportunity_id: UUID | None = None,
    activity_type: str,
    subject: str,
    description: str | None = None,
    due_date=None,
    status: str = "pending",
    request_id: str | None = None,
) -> Activity:
    get_contact(db, tenant_id=tenant_id, contact_id=contact_id)
    if opportunity_id is not None:
        get_opportunity(db, tenant_id=tenant_id, opportunity_id=opportunity_id)
    activity = Activity(
        tenant_id=tenant_id,
        created_by=user_id,
        contact_id=contact_id,
        opportunity_id=opportunity_id,
        activity_type=activity_type,
        subject=subject,
        description=description,
        due_date=due_date,
        status=status,
    )
    db.add(activity)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.activity.created",
        resource_type="activity",
        resource_id=activity.id,
        request_id=request_id,
        metadata={"activity_type": activity_type, "subject": subject},
    )
    db.flush()
    return activity


def get_activity(db: Session, *, tenant_id: UUID, activity_id: UUID) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="activity not found")
    return activity


def list_activities(
    db: Session, *, tenant_id: UUID, contact_id: UUID | None = None
) -> list[Activity]:
    stmt = select(Activity).where(Activity.tenant_id == tenant_id)
    if contact_id:
        stmt = stmt.where(Activity.contact_id == contact_id)
    return db.scalars(stmt.order_by(Activity.created_at.desc())).all()


def update_activity(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    activity_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Activity:
    activity = get_activity(db, tenant_id=tenant_id, activity_id=activity_id)
    allowed = {
        "contact_id", "opportunity_id", "activity_type", "subject",
        "description", "due_date", "status",
    }
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(activity, key, value)
    if data.get("status") == "completed" and activity.completed_at is None:
        activity.completed_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.activity.updated",
        resource_type="activity",
        resource_id=activity.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return activity


def complete_activity(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    activity_id: UUID,
    request_id: str | None = None,
) -> Activity:
    activity = get_activity(db, tenant_id=tenant_id, activity_id=activity_id)
    if activity.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"cannot complete activity in '{activity.status}' status",
        )
    activity.status = "completed"
    activity.completed_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.activity.completed",
        resource_type="activity",
        resource_id=activity.id,
        request_id=request_id,
    )
    db.flush()
    return activity


def delete_activity(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    activity_id: UUID,
    request_id: str | None = None,
) -> None:
    activity = get_activity(db, tenant_id=tenant_id, activity_id=activity_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.activity.deleted",
        resource_type="activity",
        resource_id=activity.id,
        request_id=request_id,
    )
    db.delete(activity)
    db.flush()


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------

def create_note(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contact_id: UUID,
    opportunity_id: UUID | None = None,
    content: str,
    request_id: str | None = None,
) -> Note:
    get_contact(db, tenant_id=tenant_id, contact_id=contact_id)
    if opportunity_id is not None:
        get_opportunity(db, tenant_id=tenant_id, opportunity_id=opportunity_id)
    note = Note(
        tenant_id=tenant_id,
        created_by=user_id,
        contact_id=contact_id,
        opportunity_id=opportunity_id,
        content=content,
    )
    db.add(note)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.note.created",
        resource_type="note",
        resource_id=note.id,
        request_id=request_id,
        metadata={"contact_id": str(contact_id)},
    )
    db.flush()
    return note


def get_note(db: Session, *, tenant_id: UUID, note_id: UUID) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="note not found")
    return note


def list_notes(
    db: Session, *, tenant_id: UUID, contact_id: UUID | None = None
) -> list[Note]:
    stmt = select(Note).where(Note.tenant_id == tenant_id)
    if contact_id:
        stmt = stmt.where(Note.contact_id == contact_id)
    return db.scalars(stmt.order_by(Note.created_at.desc())).all()


def delete_note(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    note_id: UUID,
    request_id: str | None = None,
) -> None:
    note = get_note(db, tenant_id=tenant_id, note_id=note_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="crm.note.deleted",
        resource_type="note",
        resource_id=note.id,
        request_id=request_id,
    )
    db.delete(note)
    db.flush()
