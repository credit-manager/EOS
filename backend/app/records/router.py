import re
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..db import commit_db, get_db
from ..metadata.models import MetadataEntity
from ..tenant import require_tenant
from ..workflow.service import start_instance
from .models import Record
from .schemas import RecordCreate, RecordResponse, RecordUpdate

router = APIRouter(prefix="/api/v1/entities/{entity_code}/records", tags=["records"])
_DEFAULT_ACTIONS = {"create", "read", "update", "delete"}


def _get_published(db: Session, tenant_id: UUID, entity_code: str) -> MetadataEntity:
    row = db.scalar(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="published metadata entity not found")
    return row


def _allowed(metadata: MetadataEntity, role: str, action: str) -> bool:
    if role == "admin":
        return action in _DEFAULT_ACTIONS
    permissions = metadata.definition.get("permissions")
    if not isinstance(permissions, dict):
        return action in _DEFAULT_ACTIONS
    member_actions = permissions.get("member", _DEFAULT_ACTIONS)
    return action in set(member_actions)


def _require_permission(request: Request, metadata: MetadataEntity, action: str) -> None:
    role = getattr(request.state, "role", "member")
    if not _allowed(metadata, role, action):
        raise HTTPException(status_code=403, detail=f"{action} permission denied")


def _validate_value(db: Session, tenant_id: UUID, code: str, value: object, field: dict) -> None:
    if value is None:
        if not field.get("nullable", False):
            raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: null is not allowed"]})
        return

    field_type = field["type"]
    valid = True
    if field_type == "text":
        valid = isinstance(value, str)
        if valid:
            min_len = field.get("min_length")
            max_len = field.get("max_length")
            if min_len is not None and len(value) < min_len:
                valid = False
            if max_len is not None and len(value) > max_len:
                valid = False
            pattern = field.get("pattern")
            if pattern and not re.search(pattern, value):
                valid = False
    elif field_type == "integer":
        valid = isinstance(value, int) and not isinstance(value, bool)
        if valid:
            min_val = field.get("min_value")
            max_val = field.get("max_value")
            if min_val is not None and value < min_val:
                valid = False
            if max_val is not None and value > max_val:
                valid = False
    elif field_type == "decimal":
        try:
            decimal_value = Decimal(str(value))
            valid = decimal_value.is_finite()
            if valid:
                min_val = field.get("min_value")
                max_val = field.get("max_value")
                if min_val is not None and decimal_value < Decimal(str(min_val)):
                    valid = False
                if max_val is not None and decimal_value > Decimal(str(max_val)):
                    valid = False
        except (InvalidOperation, ValueError, TypeError):
            valid = False
    elif field_type == "boolean":
        valid = isinstance(value, bool)
    elif field_type == "date":
        if isinstance(value, str):
            try:
                date.fromisoformat(value)
            except ValueError:
                valid = False
        else:
            valid = False
    elif field_type in {"uuid", "relation"}:
        try:
            referenced_id = UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            valid = False
        else:
            if field_type == "relation":
                target_entity = field["target_entity"]
                target_metadata = _get_published(db, tenant_id, target_entity)
                target = db.scalar(
                    select(Record).where(
                        Record.id == referenced_id,
                        Record.tenant_id == tenant_id,
                        Record.entity_code == target_metadata.code,
                    )
                )
                valid = target is not None
    elif field_type == "enum":
        valid = isinstance(value, str)
        if valid:
            options = field.get("options") or []
            allowed_values = {opt.get("value") for opt in options}
            valid = value in allowed_values
    elif field_type == "email":
        valid = isinstance(value, str) and bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))
    elif field_type == "url":
        valid = isinstance(value, str) and bool(re.match(r"^https?://", value))
    elif field_type == "json":
        valid = isinstance(value, (dict, list))
    elif field_type == "array":
        valid = isinstance(value, list)
        if valid:
            item_type = field.get("item_type")
            if item_type:
                item_field = {
                    "type": item_type,
                    "code": code,
                    "min_value": field.get("min_value"),
                    "max_value": field.get("max_value"),
                    "min_length": field.get("min_length"),
                    "max_length": field.get("max_length"),
                    "pattern": field.get("pattern"),
                }
                for i, item in enumerate(value):
                    _validate_value(db, tenant_id, f"{code}[{i}]", item, item_field)

    if not valid:
        errors: list[str] = []
        if field_type == "text":
            if not isinstance(value, str):
                errors.append(f"{code}: expected text, got {type(value).__name__}")
            else:
                min_len = field.get("min_length")
                max_len = field.get("max_length")
                pattern = field.get("pattern")
                if min_len is not None and len(value) < min_len:
                    errors.append(f"{code}: minimum length is {min_len}")
                if max_len is not None and len(value) > max_len:
                    errors.append(f"{code}: maximum length is {max_len}")
                if pattern and not re.search(pattern, value):
                    errors.append(f"{code}: does not match pattern '{pattern}'")
        elif field_type == "integer":
            min_val = field.get("min_value")
            max_val = field.get("max_value")
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"{code}: expected integer, got {type(value).__name__}")
            else:
                if min_val is not None and value < min_val:
                    errors.append(f"{code}: minimum value is {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"{code}: maximum value is {max_val}")
        elif field_type == "decimal":
            errors.append(f"{code}: expected decimal, got {type(value).__name__}")
        elif field_type == "relation":
            errors.append(f"{code}: relation to {field.get('target_entity')} not found")
        elif field_type == "enum":
            options = field.get("options") or []
            allowed = [opt.get("value") for opt in options]
            errors.append(f"{code}: must be one of {allowed}")
        else:
            errors.append(f"{code}: expected {field_type}")
        raise HTTPException(status_code=422, detail={"invalid_fields": errors})


def _validate(payload: dict, metadata: MetadataEntity, db: Session, tenant_id: UUID) -> None:
    fields = {field["code"]: field for field in metadata.definition["fields"]}
    unknown = set(payload) - set(fields)
    missing = {code for code, field in fields.items() if field.get("required") and code not in payload}
    if unknown or missing:
        detail: dict[str, list[str]] = {}
        if unknown:
            detail["unknown_fields"] = sorted(unknown)
        if missing:
            detail["missing_fields"] = sorted(missing)
        raise HTTPException(status_code=422, detail=detail)
    for code, value in payload.items():
        _validate_value(db, tenant_id, code, value, fields[code])


def _filter_expression(metadata: MetadataEntity, field_code: str, raw_value: str):
    fields = {field["code"]: field for field in metadata.definition["fields"]}
    field = fields.get(field_code)
    if field is None:
        raise HTTPException(status_code=400, detail="filter_field is not defined in metadata")

    field_type = field["type"]
    try:
        if field_type == "integer":
            value = int(raw_value)
            return Record.data[field_code].as_integer() == value
        if field_type == "decimal":
            value = Decimal(raw_value)
            if not value.is_finite():
                raise ValueError
            return Record.data[field_code].as_string() == str(value)
        if field_type == "boolean":
            normalized = raw_value.lower()
            if normalized not in {"true", "false"}:
                raise ValueError
            return Record.data[field_code].as_boolean() == (normalized == "true")
        if field_type in {"uuid", "relation"}:
            value = str(UUID(raw_value))
            return Record.data[field_code].as_string() == value
        if field_type == "date":
            value = date.fromisoformat(raw_value)
            return Record.data[field_code].as_string() == value.isoformat()
        return Record.data[field_code].as_string() == raw_value
    except (ValueError, InvalidOperation) as exc:
        raise HTTPException(status_code=422, detail=f"invalid filter value for {field_code}") from exc


def _response(row: Record) -> RecordResponse:
    return RecordResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        entity_code=row.entity_code,
        data=row.data,
        version=row.version,
        workflow_instance_id=row.workflow_instance_id,
    )


@router.post("", response_model=RecordResponse, status_code=201)
def create_record(
    entity_code: str,
    payload: RecordCreate,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> RecordResponse:
    metadata = _get_published(db, tenant_id, entity_code)
    _require_permission(request, metadata, "create")
    data = dict(payload.data)
    for field_def in metadata.definition.get("fields", []):
        code = field_def["code"]
        if code not in data and field_def.get("default") is not None:
            data[code] = field_def["default"]
    _validate(data, metadata, db, tenant_id)
    row = Record(tenant_id=tenant_id, entity_code=entity_code, data=data)
    db.add(row)
    db.flush()

    workflow = metadata.definition.get("workflow")
    if isinstance(workflow, dict) and workflow.get("auto_start_on_create", True):
        instance = start_instance(
            db,
            tenant_id=tenant_id,
            user_id=request.state.user_id,
            workflow_code=str(workflow["code"]),
            reference_type=str(workflow["reference_type"]),
            reference_id=row.id,
            request_id=request.state.request_id,
        )
        row.workflow_instance_id = instance.id

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="record.created",
        resource_type=entity_code,
        resource_id=row.id,
        metadata={"workflow_instance_id": str(row.workflow_instance_id) if row.workflow_instance_id else None},
        request_id=request.state.request_id,
    )
    commit_db(db)
    db.refresh(row)
    return _response(row)


@router.get("", response_model=list[RecordResponse])
def list_records(
    entity_code: str,
    request: Request,
    filter_field: str | None = Query(default=None, min_length=1, max_length=100),
    filter_value: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[RecordResponse]:
    metadata = _get_published(db, tenant_id, entity_code)
    _require_permission(request, metadata, "read")
    if (filter_field is None) != (filter_value is None):
        raise HTTPException(status_code=400, detail="filter_field and filter_value must be provided together")

    query = select(Record).where(Record.tenant_id == tenant_id, Record.entity_code == entity_code)
    if filter_field is not None and filter_value is not None:
        query = query.where(_filter_expression(metadata, filter_field, filter_value))
    rows = db.scalars(query.order_by(Record.created_at.desc()).offset(offset).limit(limit)).all()
    return [_response(row) for row in rows]


@router.get("/{record_id}", response_model=RecordResponse)
def get_record(
    entity_code: str,
    record_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> RecordResponse:
    metadata = _get_published(db, tenant_id, entity_code)
    _require_permission(request, metadata, "read")
    row = db.scalar(
        select(Record).where(
            Record.id == record_id,
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="record not found")
    return _response(row)


@router.patch("/{record_id}", response_model=RecordResponse)
def update_record(
    entity_code: str,
    record_id: UUID,
    payload: RecordUpdate,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> RecordResponse:
    metadata = _get_published(db, tenant_id, entity_code)
    _require_permission(request, metadata, "update")
    _validate(payload.data, metadata, db, tenant_id)
    row = db.scalar(
        select(Record).where(
            Record.id == record_id,
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="record not found")
    if row.version != payload.version:
        raise HTTPException(status_code=409, detail="record version conflict")
    merged = dict(row.data)
    merged.update(payload.data)
    for field_def in metadata.definition.get("fields", []):
        code = field_def["code"]
        if code not in merged and field_def.get("default") is not None:
            merged[code] = field_def["default"]
    _validate(merged, metadata, db, tenant_id)
    row.data = merged
    row.version += 1
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="record.updated",
        resource_type=entity_code,
        resource_id=row.id,
        metadata={"version": row.version},
        request_id=request.state.request_id,
    )
    commit_db(db)
    db.refresh(row)
    return _response(row)


@router.delete("/{record_id}", status_code=204)
def delete_record(
    entity_code: str,
    record_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> None:
    metadata = _get_published(db, tenant_id, entity_code)
    _require_permission(request, metadata, "delete")
    row = db.scalar(
        select(Record).where(
            Record.id == record_id,
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="record not found")
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="record.deleted",
        resource_type=entity_code,
        resource_id=row.id,
        metadata={"workflow_instance_id": str(row.workflow_instance_id) if row.workflow_instance_id else None},
        request_id=request.state.request_id,
    )
    db.delete(row)
    commit_db(db)
