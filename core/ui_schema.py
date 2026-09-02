"""
P14 UI Schema Engine — converts DBP metadata into unified UI/OpenAPI schemas.

Design:
  - Metadata describes the UI; Security Engine decides final visibility
  - Supports: form schema, list schema, detail schema, OpenAPI components
  - All security filters applied before returning to caller
"""
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.security import _role_matches

# ──────────────────────────────────────────────────────────────
# FIELD TYPE → UI WIDGET MAPPING
# ──────────────────────────────────────────────────────────────

FIELD_TYPE_MAP = {
    "string": {"widget": "text", "input_type": "text"},
    "number": {"widget": "number", "input_type": "number"},
    "boolean": {"widget": "checkbox", "input_type": "checkbox"},
    "date": {"widget": "date", "input_type": "date"},
    "datetime": {"widget": "datetime", "input_type": "datetime-local"},
    "email": {"widget": "text", "input_type": "email"},
    "text": {"widget": "textarea", "input_type": "text"},
    "select": {"widget": "select", "input_type": "select"},
    "relation": {"widget": "autocomplete", "input_type": "text"},
    "currency": {"widget": "currency", "input_type": "number"},
    "percentage": {"widget": "number", "input_type": "number"},
}


# ──────────────────────────────────────────────────────────────
# UI SCHEMA ENGINE
# ──────────────────────────────────────────────────────────────

class UISchemaEngine:
    """
    Generates UI schemas from DBP entity/field/relationship metadata.
    Respects field-level and row-level security.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_entity_meta(self, entity_code: str) -> dict[str, Any] | None:
        """Fetch entity + fields + relationships from DB."""
        entity = self.db.execute(
            text("SELECT id, code, name_en, name_ar, faculty, table_mapping "
                 "FROM dbp_entities WHERE code = :code"),
            {"code": entity_code},
        ).fetchone()

        if not entity:
            return None

        entity_id = entity[0]

        fields = self.db.execute(
            text("SELECT code, label_en, label_ar, field_type, is_required, "
                 "ui_config, enum_values, is_sensitive, writable_roles, "
                 "visible_roles, validation_rules "
                 "FROM dbp_fields WHERE entity_id = :eid ORDER BY "
                 "COALESCE(ui_config->>'order', '999') ASC"),
            {"eid": entity_id},
        ).fetchall()

        relationships = self.db.execute(
            text("SELECT code, target_entity_code, relationship_type, "
                 "source_column, lookup_field, is_required "
                 "FROM dbp_relationships WHERE entity_id = :eid"),
            {"eid": entity_id},
        ).fetchall()

        return {
            "entity_id": entity_id,
            "code": entity[1],
            "name_en": entity[2],
            "name_ar": entity[3],
            "faculty": entity[4],
            "table_mapping": entity[5],
            "fields": [
                {
                    "code": f[0],
                    "label_en": f[1] or f[0],
                    "label_ar": f[2],
                    "field_type": f[3],
                    "is_required": bool(f[4]),
                    "ui_config": f[5] if isinstance(f[5], dict) else {},
                    "enum_values": f[6] if isinstance(f[6], list) else [],
                    "is_sensitive": bool(f[7]),
                    "writable_roles": f[8] if isinstance(f[8], list) else [],
                    "visible_roles": f[9] if isinstance(f[9], list) else [],
                    "validation_rules": f[10] if isinstance(f[10], dict) else {},
                }
                for f in fields
            ],
            "relationships": [
                {
                    "code": r[0],
                    "target_entity_code": r[1],
                    "relationship_type": r[2],
                    "source_column": r[3],
                    "lookup_field": r[4],
                    "is_required": bool(r[5]),
                }
                for r in relationships
            ],
        }

    # ──────────────────────────────────────────────────────────
    # FORM SCHEMA (Create / Edit)
    # ──────────────────────────────────────────────────────────

    def get_form_schema(
        self,
        entity_code: str,
        mode: str = "create",
        user_roles: list[str] | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any] | None:
        """
        Generate a form schema for create or edit mode.
        Respects field-level security (writable_roles, visible_roles).
        """
        meta = self.get_entity_meta(entity_code)
        if not meta:
            return None

        field_security = {}
        for f in meta["fields"]:
            field_security[f["code"]] = {
                "is_sensitive": f["is_sensitive"],
                "writable_roles": f["writable_roles"],
                "visible_roles": f["visible_roles"],
            }

        user_roles = user_roles or []

        form_fields = []
        for f in meta["fields"]:
            ui_config = f["ui_config"]
            f["field_type"]

            # Security: check writable
            if mode == "create" or mode == "edit":
                if not is_admin and f["writable_roles"]:
                    if not _role_matches(user_roles, f["writable_roles"]):
                        if mode == "create":
                            continue  # hide non-writable fields on create
                        else:
                            # on edit: show as readonly
                            form_fields.append(_build_field_schema(f, ui_config, readonly=True))
                            continue

            # Security: check visible
            if not is_admin and f["visible_roles"]:
                if not _role_matches(user_roles, f["visible_roles"]):
                    continue  # hidden entirely

            # Always hide system columns
            if f["code"] in ("id", "tenant_id", "created_at", "deleted_at", "deleted_by"):
                if mode == "create" or f["code"] == "id":
                    continue

            form_fields.append(_build_field_schema(f, ui_config, readonly=False))

        # Add relationship fields as autocomplete widgets
        for rel in meta["relationships"]:
            if rel["relationship_type"] == "many_to_one":
                form_fields.append({
                    "name": rel["source_column"],
                    "label": rel["source_column"],
                    "widget": "autocomplete",
                    "input_type": "text",
                    "required": rel["is_required"],
                    "readonly": False,
                    "hidden": False,
                    "relation": {
                        "entity_code": rel["target_entity_code"],
                        "display_field": rel["lookup_field"],
                        "relationship_type": rel["relationship_type"],
                    },
                })

        return {
            "entity_code": entity_code,
            "entity_name": meta["name_en"],
            "entity_name_ar": meta["name_ar"],
            "mode": mode,
            "fields": form_fields,
            "actions": _get_actions(mode),
        }

    # ──────────────────────────────────────────────────────────
    # LIST SCHEMA (Table / Grid)
    # ──────────────────────────────────────────────────────────

    def get_list_schema(
        self,
        entity_code: str,
        user_roles: list[str] | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any] | None:
        """
        Generate a list/table schema.
        Shows visible columns, sortable, filterable fields.
        """
        meta = self.get_entity_meta(entity_code)
        if not meta:
            return None

        user_roles = user_roles or []
        columns = []
        filters = []

        for f in meta["fields"]:
            # Skip system columns
            if f["code"] in ("tenant_id", "deleted_at", "deleted_by"):
                continue

            # Security: visible check
            if not is_admin and f["visible_roles"]:
                if not _role_matches(user_roles, f["visible_roles"]):
                    continue

            is_sensitive = f["is_sensitive"]

            columns.append({
                "field": f["code"],
                "label": f["label_en"],
                "label_ar": f["label_ar"],
                "type": f["field_type"],
                "sortable": True,
                "maskable": is_sensitive,
                "display": "***" if is_sensitive else None,
            })

            # Build filter options
            if f["field_type"] in ("string", "email"):
                filters.append({
                    "field": f["code"],
                    "label": f["label_en"],
                    "type": "text",
                    "operators": ["eq", "ne", "contains", "startswith"],
                })
            elif f["field_type"] == "number":
                filters.append({
                    "field": f["code"],
                    "label": f["label_en"],
                    "type": "number",
                    "operators": ["eq", "ne", "gt", "gte", "lt", "lte"],
                })
            elif f["field_type"] == "boolean":
                filters.append({
                    "field": f["code"],
                    "label": f["label_en"],
                    "type": "boolean",
                    "operators": ["eq"],
                })
            elif f["field_type"] == "date":
                filters.append({
                    "field": f["code"],
                    "label": f["label_en"],
                    "type": "date",
                    "operators": ["eq", "ne", "gt", "gte", "lt", "lte"],
                })

        # Relationship columns (many_to_one as lookup)
        for rel in meta["relationships"]:
            if rel["relationship_type"] == "many_to_one":
                columns.append({
                    "field": rel["source_column"],
                    "label": rel["source_column"],
                    "type": "relation",
                    "sortable": False,
                    "maskable": False,
                    "relation": {
                        "entity_code": rel["target_entity_code"],
                        "display_field": rel["lookup_field"],
                    },
                })

        return {
            "entity_code": entity_code,
            "entity_name": meta["name_en"],
            "entity_name_ar": meta["name_ar"],
            "columns": columns,
            "filters": filters,
            "actions": {
                "create": True,
                "export": True,
                "bulk_delete": True,
                "bulk_update": True,
            },
            "pagination": {
                "default_limit": 50,
                "max_limit": 500,
            },
        }

    # ──────────────────────────────────────────────────────────
    # DETAIL / VIEW SCHEMA
    # ──────────────────────────────────────────────────────────

    def get_detail_schema(
        self,
        entity_code: str,
        user_roles: list[str] | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any] | None:
        """
        Generate a detail/view schema.
        Shows all visible fields + nested relationships.
        """
        meta = self.get_entity_meta(entity_code)
        if not meta:
            return None

        user_roles = user_roles or []
        sections = []

        # Main fields section
        main_fields = []
        for f in meta["fields"]:
            if f["code"] in ("tenant_id", "deleted_at", "deleted_by"):
                continue

            if not is_admin and f["visible_roles"]:
                if not _role_matches(user_roles, f["visible_roles"]):
                    continue

            main_fields.append({
                "name": f["code"],
                "label": f["label_en"],
                "label_ar": f["label_ar"],
                "type": f["field_type"],
                "maskable": f["is_sensitive"],
            })

        sections.append({
            "title": meta["name_en"],
            "title_ar": meta["name_ar"],
            "fields": main_fields,
        })

        # Relationship sections
        for rel in meta["relationships"]:
            sections.append({
                "title": f"{rel['code']} ({rel['relationship_type']})",
                "type": "relation",
                "entity_code": rel["target_entity_code"],
                "display_field": rel["lookup_field"],
                "relationship_type": rel["relationship_type"],
                "source_column": rel["source_column"],
            })

        return {
            "entity_code": entity_code,
            "entity_name": meta["name_en"],
            "entity_name_ar": meta["name_ar"],
            "sections": sections,
            "actions": {
                "edit": True,
                "delete": True,
                "restore": True,
            },
        }

    # ──────────────────────────────────────────────────────────
    # OPENAPI SCHEMA (for /docs)
    # ──────────────────────────────────────────────────────────

    def get_openapi_schema(self, entity_code: str) -> dict[str, Any] | None:
        """
        Generate OpenAPI-compatible request/response schemas
        for a dynamic entity.
        """
        meta = self.get_entity_meta(entity_code)
        if not meta:
            return None

        # Build JSON Schema properties
        properties = {}
        required = []
        for f in meta["fields"]:
            if f["code"] in ("id", "tenant_id", "created_at", "deleted_at", "deleted_by"):
                continue

            json_type, fmt = _field_type_to_json(f["field_type"])
            prop: dict[str, Any] = {"type": json_type}
            if fmt:
                prop["format"] = fmt

            if f["label_en"]:
                prop["description"] = f["label_en"]
            if f["enum_values"]:
                prop["enum"] = f["enum_values"]
            if f["ui_config"].get("min") is not None:
                prop["minimum"] = f["ui_config"]["min"]
            if f["ui_config"].get("max") is not None:
                prop["maximum"] = f["ui_config"]["max"]
            if f["ui_config"].get("min_length") is not None:
                prop["minLength"] = f["ui_config"]["min_length"]
            if f["ui_config"].get("max_length") is not None:
                prop["maxLength"] = f["ui_config"]["max_length"]
            if f["ui_config"].get("pattern"):
                prop["pattern"] = f["ui_config"]["pattern"]
            if f["is_sensitive"]:
                prop["description"] = f"[SENSITIVE] {prop.get('description', '')}"

            properties[f["code"]] = prop
            if f["is_required"]:
                required.append(f["code"])

        create_schema = {
            "type": "object",
            "properties": properties,
        }
        if required:
            create_schema["required"] = required

        response_properties = {"id": {"type": "string", "format": "uuid"}}
        response_properties.update(properties)

        record_schema = {
            "type": "object",
            "properties": response_properties,
        }

        # Query parameters
        query_params = []
        for f in meta["fields"]:
            if f["code"] in ("tenant_id", "deleted_at", "deleted_by"):
                continue
            query_params.append({
                "name": f["code"],
                "in": "query",
                "required": False,
                "schema": {"type": "string"},
                "description": f"Filter by {f['label_en']} (operators: eq,ne,contains,gt,lt)",
            })

        query_params.extend([
            {"name": "sort", "in": "query", "required": False,
             "schema": {"type": "string"},
             "description": "Sort field (prefix - for desc)"},
            {"name": "limit", "in": "query", "required": False,
             "schema": {"type": "integer", "default": 50, "maximum": 500}},
            {"name": "offset", "in": "query", "required": False,
             "schema": {"type": "integer", "default": 0}},
            {"name": "include", "in": "query", "required": False,
             "schema": {"type": "string"},
             "description": "Include related entities (comma-separated)"},
            {"name": "include_deleted", "in": "query", "required": False,
             "schema": {"type": "boolean", "default": False},
             "description": "Admin only: include soft-deleted records"},
        ])

        return {
            "entity_code": entity_code,
            "entity_name": meta["name_en"],
            "schemas": {
                f"Create{entity_code.title()}": create_schema,
                f"{entity_code.title()}Record": record_schema,
                f"{entity_code.title()}List": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": f"#/components/schemas/{entity_code.title()}Record"},
                        },
                        "count": {"type": "integer"},
                    },
                },
            },
            "query_parameters": query_params,
            "endpoints": {
                "list": {
                    "method": "GET",
                    "path": f"/api/v1/dynamic/entities/{entity_code}/records",
                    "description": f"List {meta['name_en']} records",
                },
                "create": {
                    "method": "POST",
                    "path": f"/api/v1/dynamic/entities/{entity_code}/records",
                    "description": f"Create a {meta['name_en']} record",
                },
                "get": {
                    "method": "GET",
                    "path": f"/api/v1/dynamic/entities/{entity_code}/records/{{record_id}}",
                    "description": f"Get a {meta['name_en']} record",
                },
                "update": {
                    "method": "PUT",
                    "path": f"/api/v1/dynamic/entities/{entity_code}/records/{{record_id}}",
                    "description": f"Update a {meta['name_en']} record",
                },
                "delete": {
                    "method": "DELETE",
                    "path": f"/api/v1/dynamic/entities/{entity_code}/records/{{record_id}}",
                    "description": f"Delete a {meta['name_en']} record",
                },
            },
        }


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _build_field_schema(field: dict, ui_config: dict, readonly: bool = False) -> dict[str, Any]:
    """Build a single field schema for form UI."""
    ftype = field["field_type"]
    mapping = FIELD_TYPE_MAP.get(ftype, FIELD_TYPE_MAP["string"])

    # Override widget from ui_config
    widget = ui_config.get("widget", mapping["widget"])
    input_type = ui_config.get("input_type", mapping["input_type"])

    schema: dict[str, Any] = {
        "name": field["code"],
        "label": field["label_en"],
        "label_ar": field["label_ar"],
        "widget": widget,
        "input_type": input_type,
        "required": field["is_required"],
        "readonly": readonly,
        "hidden": False,
    }

    # Enum / select options
    if field["enum_values"]:
        schema["options"] = [{"value": v, "label": v} for v in field["enum_values"]]
        schema["widget"] = "select"

    # Validation hints
    if ui_config.get("min") is not None:
        schema["min"] = ui_config["min"]
    if ui_config.get("max") is not None:
        schema["max"] = ui_config["max"]
    if ui_config.get("min_length") is not None:
        schema["min_length"] = ui_config["min_length"]
    if ui_config.get("max_length") is not None:
        schema["max_length"] = ui_config["max_length"]
    if ui_config.get("pattern"):
        schema["pattern"] = ui_config["pattern"]
    if ui_config.get("placeholder"):
        schema["placeholder"] = ui_config["placeholder"]
    if ui_config.get("help_text"):
        schema["help_text"] = ui_config["help_text"]

    # Sensitive flag for UI hint
    if field["is_sensitive"]:
        schema["sensitive"] = True

    return schema


def _get_actions(mode: str) -> dict[str, bool]:
    """Return available actions per form mode."""
    if mode == "create":
        return {"submit": True, "cancel": True, "reset": True}
    elif mode == "edit":
        return {"submit": True, "cancel": True, "reset": True, "delete": True}
    return {}


def _field_type_to_json(field_type: str) -> tuple:
    """Convert DBP field type to JSON Schema type + format."""
    mapping = {
        "string": ("string", None),
        "number": ("number", None),
        "boolean": ("boolean", None),
        "date": ("string", "date"),
        "datetime": ("string", "date-time"),
        "email": ("string", "email"),
        "text": ("string", None),
        "select": ("string", None),
        "relation": ("string", "uuid"),
        "currency": ("number", None),
        "percentage": ("number", None),
    }
    return mapping.get(field_type, ("string", None))
