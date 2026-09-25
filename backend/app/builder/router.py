"""EOS Builder router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant
from .schemas import (
    BuilderAutomationCreate,
    BuilderAutomationResponse,
    BuilderDashboardCreate,
    BuilderDashboardResponse,
    BuilderFieldCreate,
    BuilderFieldResponse,
    BuilderObjectCreate,
    BuilderObjectResponse,
    BuilderRelationCreate,
    BuilderRelationResponse,
    BuilderRuleCreate,
    BuilderRuleResponse,
    BuilderViewCreate,
    BuilderViewResponse,
    BuilderWidgetCreate,
    BuilderWidgetResponse,
    BuilderWorkflowCreate,
    BuilderWorkflowResponse,
)
from .service import BuilderService

router = APIRouter(prefix="/api/v1/builder", tags=["builder"])


# Objects

@router.post("/objects", response_model=BuilderObjectResponse, status_code=201)
def create_object(
    payload: BuilderObjectCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderObjectResponse:
    svc = BuilderService(db)
    obj = svc.create_object(str(tenant_id), payload.model_dump())
    return BuilderObjectResponse.model_validate(obj)


@router.get("/objects", response_model=list[BuilderObjectResponse])
def list_objects(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderObjectResponse]:
    svc = BuilderService(db)
    return [BuilderObjectResponse.model_validate(o) for o in svc.list_objects(str(tenant_id))]


@router.get("/objects/{object_id}", response_model=BuilderObjectResponse)
def get_object(
    object_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderObjectResponse:
    svc = BuilderService(db)
    obj = svc.get_object(object_id, str(tenant_id))
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return BuilderObjectResponse.model_validate(obj)


@router.patch("/objects/{object_id}", response_model=BuilderObjectResponse)
def update_object(
    object_id: str,
    payload: BuilderObjectCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderObjectResponse:
    svc = BuilderService(db)
    obj = svc.update_object(object_id, str(tenant_id), payload.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return BuilderObjectResponse.model_validate(obj)


@router.delete("/objects/{object_id}", status_code=204, response_class=Response, response_model=None)
def delete_object(
    object_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> None:
    svc = BuilderService(db)
    if not svc.delete_object(object_id, str(tenant_id)):
        raise HTTPException(status_code=404, detail="Object not found")


# Fields

@router.post("/objects/{object_id}/fields", response_model=BuilderFieldResponse, status_code=201)
def create_field(
    object_id: str,
    payload: BuilderFieldCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderFieldResponse:
    svc = BuilderService(db)
    field = svc.create_field(object_id, str(tenant_id), payload.model_dump())
    if not field:
        raise HTTPException(status_code=404, detail="Object not found")
    return BuilderFieldResponse.model_validate(field)


@router.get("/objects/{object_id}/fields", response_model=list[BuilderFieldResponse])
def list_fields(
    object_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderFieldResponse]:
    svc = BuilderService(db)
    return [BuilderFieldResponse.model_validate(f) for f in svc.list_fields(object_id, str(tenant_id))]


# Relations

@router.post("/relations", response_model=BuilderRelationResponse, status_code=201)
def create_relation(
    payload: BuilderRelationCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderRelationResponse:
    svc = BuilderService(db)
    rel = svc.create_relation(str(tenant_id), payload.model_dump())
    return BuilderRelationResponse.model_validate(rel)


@router.get("/relations", response_model=list[BuilderRelationResponse])
def list_relations(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderRelationResponse]:
    svc = BuilderService(db)
    return [BuilderRelationResponse.model_validate(r) for r in svc.list_relations(str(tenant_id))]


# Workflows

@router.post("/workflows", response_model=BuilderWorkflowResponse, status_code=201)
def create_workflow(
    payload: BuilderWorkflowCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderWorkflowResponse:
    svc = BuilderService(db)
    wf = svc.create_workflow(str(tenant_id), payload.model_dump())
    return BuilderWorkflowResponse.model_validate(wf)


@router.get("/workflows", response_model=list[BuilderWorkflowResponse])
def list_workflows(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderWorkflowResponse]:
    svc = BuilderService(db)
    return [BuilderWorkflowResponse.model_validate(w) for w in svc.list_workflows(str(tenant_id))]


# Rules

@router.post("/rules", response_model=BuilderRuleResponse, status_code=201)
def create_rule(
    payload: BuilderRuleCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderRuleResponse:
    svc = BuilderService(db)
    rule = svc.create_rule(str(tenant_id), payload.model_dump())
    return BuilderRuleResponse.model_validate(rule)


@router.get("/rules", response_model=list[BuilderRuleResponse])
def list_rules(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderRuleResponse]:
    svc = BuilderService(db)
    return [BuilderRuleResponse.model_validate(r) for r in svc.list_rules(str(tenant_id))]


# Views

@router.post("/views", response_model=BuilderViewResponse, status_code=201)
def create_view(
    payload: BuilderViewCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderViewResponse:
    svc = BuilderService(db)
    view = svc.create_view(str(tenant_id), payload.model_dump())
    return BuilderViewResponse.model_validate(view)


@router.get("/views", response_model=list[BuilderViewResponse])
def list_views(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderViewResponse]:
    svc = BuilderService(db)
    return [BuilderViewResponse.model_validate(v) for v in svc.list_views(str(tenant_id))]


# Dashboards

@router.post("/dashboards", response_model=BuilderDashboardResponse, status_code=201)
def create_dashboard(
    payload: BuilderDashboardCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderDashboardResponse:
    svc = BuilderService(db)
    dash = svc.create_dashboard(str(tenant_id), payload.model_dump())
    return BuilderDashboardResponse.model_validate(dash)


@router.get("/dashboards", response_model=list[BuilderDashboardResponse])
def list_dashboards(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderDashboardResponse]:
    svc = BuilderService(db)
    return [BuilderDashboardResponse.model_validate(d) for d in svc.list_dashboards(str(tenant_id))]


# Widgets

@router.post("/dashboards/{dashboard_id}/widgets", response_model=BuilderWidgetResponse, status_code=201)
def create_widget(
    dashboard_id: str,
    payload: BuilderWidgetCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderWidgetResponse:
    svc = BuilderService(db)
    widget = svc.create_widget(dashboard_id, str(tenant_id), payload.model_dump())
    if not widget:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return BuilderWidgetResponse.model_validate(widget)


@router.get("/dashboards/{dashboard_id}/widgets", response_model=list[BuilderWidgetResponse])
def list_widgets(
    dashboard_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderWidgetResponse]:
    svc = BuilderService(db)
    return [BuilderWidgetResponse.model_validate(w) for w in svc.list_widgets(dashboard_id, str(tenant_id))]


# Automations

@router.post("/automations", response_model=BuilderAutomationResponse, status_code=201)
def create_automation(
    payload: BuilderAutomationCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BuilderAutomationResponse:
    svc = BuilderService(db)
    auto = svc.create_automation(str(tenant_id), payload.model_dump())
    return BuilderAutomationResponse.model_validate(auto)


@router.get("/automations", response_model=list[BuilderAutomationResponse])
def list_automations(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BuilderAutomationResponse]:
    svc = BuilderService(db)
    return [BuilderAutomationResponse.model_validate(a) for a in svc.list_automations(str(tenant_id))]


# Export

@router.get("/export")
def export_schema(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    svc = BuilderService(db)
    data = svc.export_schema(str(tenant_id))
    return {
        "objects": [BuilderObjectResponse.model_validate(o).model_dump() for o in data["objects"]],
        "fields": [BuilderFieldResponse.model_validate(f).model_dump() for f in data["fields"]],
        "relations": [BuilderRelationResponse.model_validate(r).model_dump() for r in data["relations"]],
        "workflows": [BuilderWorkflowResponse.model_validate(w).model_dump() for w in data["workflows"]],
        "rules": [BuilderRuleResponse.model_validate(r).model_dump() for r in data["rules"]],
        "views": [BuilderViewResponse.model_validate(v).model_dump() for v in data["views"]],
        "dashboards": [BuilderDashboardResponse.model_validate(d).model_dump() for d in data["dashboards"]],
        "automations": [BuilderAutomationResponse.model_validate(a).model_dump() for a in data["automations"]],
    }


# ---------------------------------------------------------------------------
# EOS Builder - Deploy: convert builder objects to metadata entities
# ---------------------------------------------------------------------------

class DeployResponse(BaseModel):
    deployed_objects: int
    deployed_fields: int
    metadata_entities: list[dict]


# Builder field types that map directly onto Metadata Engine FieldType values.
_BUILDER_TYPE_MAP = {
    "text": "text",
    "long_text": "rich_text",
    "textarea": "rich_text",
    "number": "decimal",
    "integer": "integer",
    "decimal": "decimal",
    "currency": "currency",
    "percent": "percentage",
    "boolean": "boolean",
    "checkbox": "boolean",
    "date": "date",
    "datetime": "date",
    "email": "email",
    "phone": "phone",
    "url": "url",
    "select": "select",
    "dropdown": "select",
    "multiselect": "multi_select",
    "multi_select": "multi_select",
    "json": "json",
    "file": "file",
    "rating": "rating",
    "location": "location",
    "relation": "relation",
}


def _safe_field_code(raw: str) -> str | None:
    """Normalize a builder field code into the metadata pattern ^[a-z][a-z0-9_]*$."""
    import re

    code = (raw or "").strip().lower()
    code = re.sub(r"[^a-z0-9_]", "_", code)
    if not code:
        return None
    if not code[0].isalpha():
        code = f"f_{code}"
    return code[:100]


def _builder_definition(svc: BuilderService, obj, relations, tenant_id: str) -> dict:
    """Convert one Builder object (fields + relations + workflow) into a
    runtime-consumable Metadata definition payload."""
    fields = svc.list_fields(obj.id, tenant_id)
    used_codes: set[str] = set()
    def_fields: list[dict] = []

    for field in fields:
        code = _safe_field_code(field.code)
        if not code or code in used_codes:
            continue
        raw_type = (field.field_type or "text").strip().lower()
        ftype = _BUILDER_TYPE_MAP.get(raw_type, "text")
        field_def: dict = {
            "code": code,
            "type": ftype,
            "required": bool(field.is_required),
            "nullable": not bool(field.is_required),
            "label": field.name,
        }
        if field.default_value is not None and ftype not in ("file", "rich_text"):
            field_def["default"] = field.default_value
        if field.validation_rules:
            vr = field.validation_rules
            validation = {}
            for key in ("min", "max", "pattern", "min_length", "max_length"):
                if isinstance(vr, dict) and vr.get(key) is not None:
                    validation[key] = vr[key]
            if validation:
                field_def["validation"] = validation
        if ftype in ("select", "multi_select"):
            options = field.options or []
            select_options = []
            for opt in options:
                if isinstance(opt, dict) and opt.get("value"):
                    select_options.append({"value": str(opt["value"]), "label": str(opt.get("label", opt["value"]))})
                elif isinstance(opt, str) and opt:
                    select_options.append({"value": opt, "label": opt})
            if not select_options:
                # select without options would fail metadata validation; degrade to text.
                field_def["type"] = "text"
            else:
                field_def["select_options"] = select_options
        def_fields.append(field_def)
        used_codes.add(code)

    # Relations become relation fields on the source entity.
    for rel in relations:
        if rel.source_object_id != obj.id or not rel.is_active:
            continue
        target_obj = svc.get_object(rel.target_object_id, tenant_id)
        if target_obj is None:
            continue
        rel_code = _safe_field_code(f"{rel.code}_id")
        target_code = _safe_field_code(target_obj.code)
        if not rel_code or rel_code in used_codes or not target_code:
            continue
        def_fields.append({
            "code": rel_code,
            "type": "relation",
            "required": bool(rel.is_required),
            "nullable": not bool(rel.is_required),
            "label": rel.name,
            "target_entity": target_code,
        })
        used_codes.add(rel_code)

    if not def_fields:
        def_fields.append({"code": "name", "type": "text", "required": True, "nullable": False, "label": "Name"})

    definition: dict = {
        "code": _safe_field_code(obj.code) or "entity",
        "name": obj.name[:200],
        "fields": def_fields,
        "permissions": {
            "admin": ["create", "read", "update", "delete"],
            "member": ["create", "read", "update"],
        },
    }

    workflows = [w for w in svc.list_workflows(tenant_id) if w.object_id == obj.id and w.is_active]
    if workflows:
        wf_code = _safe_field_code(workflows[0].code)
        if wf_code:
            definition["workflow"] = {
                "code": wf_code,
                "reference_type": definition["code"],
                "auto_start_on_create": True,
            }

    return definition


@router.post("/deploy", response_model=DeployResponse)
def deploy_objects(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DeployResponse:
    """Deploy builder objects to the metadata engine as versioned Draft entities.

    Versioning/publish semantics are owned by the Metadata Engine service
    (backend/app/metadata/service.py); the Builder only produces definitions.
    """
    from ..metadata.service import deploy_definition

    svc = BuilderService(db)
    objects = svc.list_objects(str(tenant_id))
    relations = svc.list_relations(str(tenant_id))

    deployed_objects = 0
    deployed_fields = 0
    metadata_entities = []

    for obj in objects:
        definition = _builder_definition(svc, obj, relations, str(tenant_id))
        row = deploy_definition(
            db,
            tenant_id=tenant_id,
            actor_id=getattr(request.state, "user_id", None),
            code=definition["code"],
            name=definition["name"],
            definition=definition,
            request_id=getattr(request.state, "request_id", None),
        )
        metadata_entities.append({
            "code": row.code,
            "name": row.name,
            "version": row.version,
            "published": row.published_at is not None,
            "fields_count": len(definition["fields"]),
        })
        deployed_objects += 1
        deployed_fields += len(definition["fields"])

    return DeployResponse(
        deployed_objects=deployed_objects,
        deployed_fields=deployed_fields,
        metadata_entities=metadata_entities,
    )


# ---------------------------------------------------------------------------
# Dynamic CRUD endpoints — work with any Builder-defined object
# ---------------------------------------------------------------------------

from pydantic import Field as PydanticField
from .crud_service import DynamicCRUDService


class DynamicRecordCreate(BaseModel):
    data: dict


class DynamicRecordUpdate(BaseModel):
    data: dict


class DynamicRecordResponse(BaseModel):
    id: str
    data: dict


class DynamicSchemaResponse(BaseModel):
    object_code: str
    object_name: str
    fields: list[dict]


@router.get("/objects/{object_id}/schema", response_model=DynamicSchemaResponse)
def get_object_schema(
    object_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    crud = DynamicCRUDService(db)
    schema = crud.get_schema(object_id, str(tenant_id))
    if not schema:
        raise HTTPException(404, "Object not found")
    return schema


@router.post("/objects/{object_id}/records", status_code=201)
def create_record(
    object_id: str,
    payload: DynamicRecordCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    crud = DynamicCRUDService(db)
    try:
        result = crud.create(object_id, str(tenant_id), payload.data)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"Failed to create record: {e}")


@router.get("/objects/{object_id}/records")
def list_records(
    object_id: str,
    limit: int = 50,
    offset: int = 0,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    crud = DynamicCRUDService(db)
    return crud.list(object_id, str(tenant_id), limit=limit, offset=offset)


@router.get("/objects/{object_id}/records/{record_id}")
def get_record(
    object_id: str,
    record_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    crud = DynamicCRUDService(db)
    result = crud.get(object_id, str(tenant_id), record_id)
    if not result:
        raise HTTPException(404, "Record not found")
    return result


@router.patch("/objects/{object_id}/records/{record_id}")
def update_record(
    object_id: str,
    record_id: str,
    payload: DynamicRecordUpdate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    crud = DynamicCRUDService(db)
    result = crud.update(object_id, str(tenant_id), record_id, payload.data)
    if not result:
        raise HTTPException(404, "Record not found")
    return result


@router.delete("/objects/{object_id}/records/{record_id}", status_code=204, response_class=Response, response_model=None)
def delete_record(
    object_id: str,
    record_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    crud = DynamicCRUDService(db)
    if not crud.delete(object_id, str(tenant_id), record_id):
        raise HTTPException(404, "Record not found")
