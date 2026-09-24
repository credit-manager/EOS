import re
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..db import get_db
from ..events.service import publish as publish_event
from ..formula import evaluate_formula
from ..graph.service import relation_edges
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


def _check_field_permissions(
    request: Request,
    metadata: MetadataEntity,
    field_codes: set[str],
    action: str,
) -> set[str]:
    """
    Check field-level permissions and return set of allowed field codes.
    Metadata Engine V2 - Field-level permissions support.
    """
    role = getattr(request.state, "role", "member")
    fields = metadata.definition.get("fields", [])

    allowed_fields = set()
    for field in fields:
        field_code = field.get("code", "")
        if field_code not in field_codes:
            continue

        permissions = field.get("permissions")
        if not permissions:
            # No field-level permissions, use entity-level
            allowed_fields.add(field_code)
            continue

        # Check field-level permissions
        if action == "read":
            allowed_roles = permissions.get("read", ["admin", "member"])
            if role in allowed_roles or role == "admin":
                allowed_fields.add(field_code)
        elif action == "write":
            allowed_roles = permissions.get("write", ["admin"])
            if role in allowed_roles or role == "admin":
                allowed_fields.add(field_code)
        elif action == "hidden":
            hidden_roles = permissions.get("hidden", [])
            if role not in hidden_roles and role != "admin":
                allowed_fields.add(field_code)
        else:
            # For other actions, use entity-level permissions
            allowed_fields.add(field_code)

    return allowed_fields


def _validate_value(db: Session, tenant_id: UUID, code: str, value: object, field: dict) -> None:
    if value is None:
        if not field.get("nullable", False):
            raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: null is not allowed"]})
        return

    field_type = field["type"]
    valid = True
    if field_type == "text":
        valid = isinstance(value, str)
    elif field_type == "integer":
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif field_type == "decimal":
        try:
            decimal_value = Decimal(str(value))
            valid = decimal_value.is_finite()
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

    if not valid:
        expected = f"relation to {field.get('target_entity')}" if field_type == "relation" else field_type
        raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: expected {expected}"]})


def _validate_field_rules(code: str, value: object, field: dict) -> None:
    rules = field.get("validation")
    if not isinstance(rules, dict) or value is None:
        return
    field_type = field["type"]
    if field_type == "text" and isinstance(value, str):
        if rules.get("min_length") is not None and len(value) < int(rules["min_length"]):
            raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: shorter than min_length"]})
        if rules.get("max_length") is not None and len(value) > int(rules["max_length"]):
            raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: longer than max_length"]})
        pattern = rules.get("pattern")
        if pattern and re.fullmatch(pattern, value) is None:
            raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: does not match pattern"]})
    if field_type in {"integer", "decimal"}:
        try:
            numeric = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return
        if rules.get("min") is not None and numeric < Decimal(str(rules["min"])):
            raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: below minimum"]})
        if rules.get("max") is not None and numeric > Decimal(str(rules["max"])):
            raise HTTPException(status_code=422, detail={"invalid_fields": [f"{code}: above maximum"]})


def _prepare(payload: dict, metadata: MetadataEntity, db: Session, tenant_id: UUID, request: Request | None = None) -> dict:
    fields = {field["code"]: field for field in metadata.definition["fields"]}
    computed = {code for code, field in fields.items() if field.get("computed")}
    readonly = {code for code, field in fields.items() if field.get("readonly")}

    unknown = set(payload) - set(fields)
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_fields": sorted(unknown)})
    rejected = set(payload) & (computed | readonly)
    if rejected:
        raise HTTPException(status_code=422, detail={"readonly_fields": sorted(rejected)})

    # Metadata Engine V2 - Field-level permission check
    if request is not None and payload:
        writable_fields = _check_field_permissions(request, metadata, set(payload.keys()), "write")
        non_writable = set(payload.keys()) - writable_fields
        if non_writable:
            raise HTTPException(status_code=403, detail={"field_permission_denied": sorted(non_writable)})

    missing = {
        code
        for code, field in fields.items()
        if field.get("required") and code not in payload and code not in computed
    }
    if missing:
        raise HTTPException(status_code=422, detail={"missing_fields": sorted(missing)})

    data = dict(payload)
    for code, field in fields.items():
        if code in data or code in computed:
            continue
        default = field.get("default")
        if default is not None:
            data[code] = default

    for code, value in data.items():
        _validate_value(db, tenant_id, code, value, fields[code])
        _validate_field_rules(code, value, fields[code])
    return data


def _apply_computed(data: dict, metadata: MetadataEntity) -> dict:
    result = dict(data)
    for field in metadata.definition.get("fields", []):
        computed = field.get("computed")
        if not isinstance(computed, dict):
            continue
        formula = computed.get("formula")
        if not formula:
            continue
        value = evaluate_formula(str(formula), result)
        if value is None:
            continue
        if field["type"] == "integer":
            value = int(round(value))
        result[field["code"]] = value
    return result


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


def _response(row: Record, metadata: MetadataEntity | None = None, request: Request | None = None) -> RecordResponse:
    """Return record response, filtering hidden fields if metadata and request provided."""
    data = row.data

    # Metadata Engine V2 - Filter hidden fields
    if metadata is not None and request is not None:
        role = getattr(request.state, "role", "member")
        fields = metadata.definition.get("fields", [])
        filtered_data = {}

        for field in fields:
            field_code = field.get("code", "")
            if field_code not in data:
                continue

            permissions = field.get("permissions")
            if not permissions:
                # No field-level permissions, include field
                filtered_data[field_code] = data[field_code]
                continue

            # Check if field is hidden for this role
            hidden_roles = permissions.get("hidden", [])
            if role not in hidden_roles or role == "admin":
                filtered_data[field_code] = data[field_code]

        data = filtered_data

    return RecordResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        entity_code=row.entity_code,
        data=data,
        version=row.version,
        workflow_instance_id=row.workflow_instance_id,
    )


def _publish_graph_edges(
    db: Session,
    *,
    request: Request,
    entity_code: str,
    row_id: UUID,
    edges: list[dict],
    created: bool,
) -> None:
    for edge in edges:
        publish_event(
            db,
            tenant_id=request.state.tenant_id,
            event_type="graph.relationship.created" if created else "graph.relationship.removed",
            entity_type=entity_code,
            entity_id=str(row_id),
            actor_id=str(request.state.user_id),
            payload={
                "source_entity": entity_code,
                "source_id": str(row_id),
                "field": edge["field"],
                "target_entity": edge["target_entity"],
                "target_id": edge["target_id"],
            },
            request_id=request.state.request_id,
        )


def _edge_key(edge: dict) -> tuple[str, str]:
    return edge["field"], edge["target_id"]


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
    data = _prepare(payload.data, metadata, db, tenant_id, request)
    data = _apply_computed(data, metadata)
    row = Record(tenant_id=tenant_id, entity_code=entity_code, data=data)
    db.add(row)
    db.flush()

    _publish_graph_edges(
        db,
        request=request,
        entity_code=entity_code,
        row_id=row.id,
        edges=relation_edges(metadata, data),
        created=True,
    )

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
    db.commit()
    db.refresh(row)
    return _response(row, metadata, request)


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
    return [_response(row, metadata, request) for row in rows]


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
    return _response(row, metadata, request)


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
    new_data = _prepare(payload.data, metadata, db, tenant_id, request)
    new_data = _apply_computed(new_data, metadata)
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
    old_data = row.data
    old_keys = set(map(_edge_key, relation_edges(metadata, old_data)))
    new_edges = relation_edges(metadata, new_data)
    new_keys = set(map(_edge_key, new_edges))
    row.data = new_data
    row.version += 1
    removed = [edge for edge in relation_edges(metadata, old_data) if _edge_key(edge) not in new_keys]
    for edge in new_edges:
        if _edge_key(edge) not in old_keys:
            _publish_graph_edges(
                db, request=request, entity_code=entity_code,
                row_id=row.id, edges=[edge], created=True,
            )
    for edge in removed:
        _publish_graph_edges(
            db, request=request, entity_code=entity_code,
            row_id=row.id, edges=[edge], created=False,
        )
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
    db.commit()
    db.refresh(row)
    return _response(row, metadata, request)


@router.delete("/{record_id}", status_code=204, response_model=None)
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
    _publish_graph_edges(
        db,
        request=request,
        entity_code=entity_code,
        row_id=row.id,
        edges=relation_edges(metadata, row.data),
        created=False,
    )
    db.delete(row)
    db.commit()
