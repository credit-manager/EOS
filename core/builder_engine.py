"""P54 Self-Service ERP Builder Engine.
Draft editing -> Preview -> Approval Gate -> Publish -> Versioning -> Rollback.

Dynamic physical-table DDL is delegated to a narrowly scoped PostgreSQL
SECURITY DEFINER function. The application runtime role never receives CREATE
on the public schema. Metadata and runtime data remain tenant-scoped.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.ai_composer import MODULE_DEPENDENCIES

ENTITY_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,99}$")
FIELD_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,99}$")
VALID_FIELD_TYPES = {
    "string", "text", "integer", "float", "number", "boolean",
    "date", "datetime", "enum", "json",
}
FIELD_SQL_TYPES = {
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "integer": "INTEGER",
    "float": "DOUBLE PRECISION",
    "number": "DOUBLE PRECISION",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMP",
    "enum": "VARCHAR(50)",
    "json": "JSONB",
}
BUILDER_TABLE_PREFIX = "bld_"


def _new_draft_from_composer(composer_config: Optional[Dict]) -> Dict[str, Any]:
    composer_config = composer_config or {}
    return {
        "industry": composer_config.get("industry"),
        "settings": composer_config.get("settings", {"currency": "SAR"}),
        "modules": [{"code": m, "enabled": True} for m in composer_config.get("modules", [])],
        "custom_entities": [],
        "relationships": [],
        "roles": composer_config.get("roles", {}),
        "workflows": composer_config.get("workflows", []),
        "kpis": composer_config.get("kpis", []),
    }


class BuilderEngine:
    def __init__(self, db: Session):
        self.db = db

    def create_project(
        self,
        tenant_id: str,
        name: str,
        composer_session_id: Optional[str] = None,
        initial_config: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        pid = str(uuid.uuid4())
        draft = _new_draft_from_composer(initial_config)
        if composer_session_id:
            row = self.db.execute(
                text(
                    "SELECT generated_config FROM dbp_composer_sessions "
                    "WHERE id=:sid AND tenant_id=:tid"
                ),
                {"sid": composer_session_id, "tid": tenant_id},
            ).fetchone()
            if not row:
                return {"success": False, "error": "Composer session not found"}
            cfg = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            draft = _new_draft_from_composer(cfg)
        self.db.execute(
            text(
                "INSERT INTO dbp_builder_projects "
                "(id, tenant_id, name, source_composer_session_id, status, draft_config) "
                "VALUES (:id,:tid,:name,:sid,'draft',:cfg)"
            ),
            {
                "id": pid,
                "tid": tenant_id,
                "name": str(name).strip(),
                "sid": composer_session_id,
                "cfg": json.dumps(draft),
            },
        )
        self.db.flush()
        return {"success": True, "project_id": pid, "draft_config": draft}

    def get_project(self, tenant_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text(
                "SELECT id,tenant_id,name,source_composer_session_id,status,draft_config,"
                "published_version_id,created_at,updated_at FROM dbp_builder_projects "
                "WHERE id=:pid AND tenant_id=:tid"
            ),
            {"pid": project_id, "tid": tenant_id},
        ).fetchone()
        if not row:
            return None
        cfg = row[5] if isinstance(row[5], dict) else json.loads(row[5])
        return {
            "id": row[0],
            "tenant_id": row[1],
            "name": row[2],
            "source_composer_session_id": row[3],
            "status": row[4],
            "draft_config": cfg,
            "published_version_id": row[6],
            "created_at": str(row[7]) if row[7] else None,
            "updated_at": str(row[8]) if row[8] else None,
        }

    def list_projects(self, tenant_id: str) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            text(
                "SELECT id,name,status,created_at,updated_at FROM dbp_builder_projects "
                "WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 200"
            ),
            {"tid": tenant_id},
        ).fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "status": row[2],
                "created_at": str(row[3]) if row[3] else None,
                "updated_at": str(row[4]) if row[4] else None,
            }
            for row in rows
        ]

    def update_settings(self, tenant_id: str, pid: str, settings: Dict) -> bool:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return False
        merged = dict(proj["draft_config"].get("settings", {}))
        merged.update(settings or {})
        proj["draft_config"]["settings"] = merged
        return self._save_draft(tenant_id, pid, proj["draft_config"])

    def set_modules(self, tenant_id: str, pid: str, modules: List[Dict[str, Any]]) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        seen: Dict[str, bool] = {}
        for module in modules:
            code = module.get("code")
            if not isinstance(code, str) or not ENTITY_CODE_RE.fullmatch(code):
                return {"success": False, "error": f"Invalid module code: {code!r}"}
            seen[code] = bool(module.get("enabled", True))
        existing = {
            item["code"]: bool(item.get("enabled", True))
            for item in proj["draft_config"].get("modules", [])
            if isinstance(item, dict) and item.get("code")
        }
        existing.update(seen)
        proj["draft_config"]["modules"] = [
            {"code": code, "enabled": enabled} for code, enabled in sorted(existing.items())
        ]
        return {"success": self._save_draft(tenant_id, pid, proj["draft_config"])}

    def add_entity(self, tenant_id: str, pid: str, entity_def: Dict[str, Any]) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        entity_code = entity_def.get("entity_code")
        if not isinstance(entity_code, str) or not ENTITY_CODE_RE.fullmatch(entity_code):
            return {"success": False, "error": f"Invalid entity_code: {entity_code!r}"}
        if not entity_def.get("name_en"):
            return {"success": False, "error": "name_en required"}
        fields = entity_def.get("fields", [])
        if not isinstance(fields, list) or not fields:
            return {"success": False, "error": "At least one field required"}
        seen = set()
        for field in fields:
            field_code = field.get("code")
            if not isinstance(field_code, str) or not FIELD_CODE_RE.fullmatch(field_code):
                return {"success": False, "error": f"Invalid field code: {field_code!r}"}
            if field_code in seen:
                return {"success": False, "error": f"Duplicate field: {field_code}"}
            seen.add(field_code)
            field_type = field.get("field_type")
            if field_type not in VALID_FIELD_TYPES:
                return {"success": False, "error": f"Invalid field_type: {field_type!r}"}
            if field_type == "enum" and not field.get("enum_values"):
                return {"success": False, "error": f"Enum field '{field_code}' requires enum_values"}
        cfg = proj["draft_config"]
        entities = {e["entity_code"]: e for e in cfg.get("custom_entities", []) if "entity_code" in e}
        if entity_code in entities:
            return {"success": False, "error": f"Entity '{entity_code}' already exists in draft"}
        entities[entity_code] = {
            "entity_code": entity_code,
            "name_en": entity_def["name_en"],
            "name_ar": entity_def.get("name_ar"),
            "faculty": entity_def.get("faculty", "operations"),
            "fields": fields,
        }
        cfg["custom_entities"] = list(entities.values())
        self._save_draft(tenant_id, pid, cfg)
        return {"success": True, "entity_code": entity_code}

    def remove_entity(self, tenant_id: str, pid: str, ecode: str) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        cfg = proj["draft_config"]
        before = len(cfg.get("custom_entities", []))
        cfg["custom_entities"] = [
            entity for entity in cfg.get("custom_entities", []) if entity.get("entity_code") != ecode
        ]
        if len(cfg["custom_entities"]) == before:
            return {"success": False, "error": f"Entity '{ecode}' not in draft"}
        self._save_draft(tenant_id, pid, cfg)
        return {"success": True}

    def add_relationship(self, tenant_id: str, pid: str, rel: Dict[str, Any]) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        if not rel.get("from_entity") or not rel.get("to_entity"):
            return {"success": False, "error": "from_entity and to_entity required"}
        proj["draft_config"].setdefault("relationships", []).append(rel)
        self._save_draft(tenant_id, pid, proj["draft_config"])
        return {"success": True}

    def set_roles(self, tenant_id: str, pid: str, roles: Dict[str, Any]) -> bool:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return False
        proj["draft_config"]["roles"] = roles
        return self._save_draft(tenant_id, pid, proj["draft_config"])

    def add_workflow(self, tenant_id: str, pid: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        if not workflow.get("name"):
            return {"success": False, "error": "Workflow name required"}
        proj["draft_config"].setdefault("workflows", []).append(workflow)
        self._save_draft(tenant_id, pid, proj["draft_config"])
        return {"success": True}

    def add_kpi(self, tenant_id: str, pid: str, kpi: Dict[str, Any]) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        if not kpi.get("name"):
            return {"success": False, "error": "KPI name required"}
        proj["draft_config"].setdefault("kpis", []).append(kpi)
        self._save_draft(tenant_id, pid, proj["draft_config"])
        return {"success": True}

    def validate_draft(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []
        modules = cfg.get("modules", []) if isinstance(cfg, dict) else []
        enabled = [m.get("code") for m in modules if isinstance(m, dict) and m.get("enabled")]
        for module in enabled:
            for dependency in MODULE_DEPENDENCIES.get(module, []):
                if dependency not in enabled:
                    errors.append(f"Module '{module}' requires '{dependency}'")

        known = set()
        entities = cfg.get("custom_entities", []) if isinstance(cfg, dict) else []
        for entity in entities:
            code = entity.get("entity_code") if isinstance(entity, dict) else None
            if not code or not isinstance(code, str) or not ENTITY_CODE_RE.fullmatch(code):
                errors.append(f"Invalid entity code: {code!r}")
                continue
            if code in known:
                errors.append(f"Duplicate entity: {code}")
            known.add(code)
            fields = entity.get("fields", [])
            if not fields:
                errors.append(f"Entity '{code}' requires at least one field")
                continue
            field_names = set()
            for field in fields:
                field_code = field.get("code") if isinstance(field, dict) else None
                if not isinstance(field_code, str) or not FIELD_CODE_RE.fullmatch(field_code):
                    errors.append(f"Invalid field code in '{code}': {field_code!r}")
                    continue
                if field_code in field_names:
                    errors.append(f"Duplicate field '{field_code}' in '{code}'")
                field_names.add(field_code)
                field_type = field.get("field_type")
                if field_type not in VALID_FIELD_TYPES:
                    errors.append(f"Invalid field type in '{code}.{field_code}'")

        for relationship in cfg.get("relationships", []) if isinstance(cfg, dict) else []:
            if relationship.get("from_entity") not in known:
                errors.append(f"Relationship references unknown entity '{relationship.get('from_entity')}'")
            if relationship.get("to_entity") not in known:
                errors.append(f"Relationship references unknown entity '{relationship.get('to_entity')}'")

        tables = set()
        for entity in entities:
            code = entity.get("entity_code") if isinstance(entity, dict) else ""
            table = BUILDER_TABLE_PREFIX + str(code)
            if table in tables:
                errors.append(f"Table collision: {table}")
            tables.add(table)

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "enabled_modules": len(enabled),
                "disabled_modules": sum(1 for item in modules if isinstance(item, dict) and not item.get("enabled")),
                "custom_entities": len(entities),
                "total_fields": sum(len(entity.get("fields", [])) for entity in entities if isinstance(entity, dict)),
                "relationships": len(cfg.get("relationships", [])) if isinstance(cfg, dict) else 0,
                "roles": len(cfg.get("roles", {})) if isinstance(cfg, dict) and isinstance(cfg.get("roles", {}), dict) else 0,
                "workflows": len(cfg.get("workflows", [])) if isinstance(cfg, dict) else 0,
                "kpis": len(cfg.get("kpis", [])) if isinstance(cfg, dict) else 0,
            },
        }

    def preview(self, tenant_id: str, pid: str) -> Optional[Dict[str, Any]]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return None
        return {
            "project_id": pid,
            "project_name": proj["name"],
            "status": proj["status"],
            "config": proj["draft_config"],
            "validation": self.validate_draft(proj["draft_config"]),
        }

    def publish(
        self,
        tenant_id: str,
        pid: str,
        published_by: str,
        confirmed: bool,
        change_summary: str = "",
    ) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        if not confirmed:
            return {"success": False, "error": "Explicit approval required: pass confirmed=true to publish"}
        cfg = proj["draft_config"]
        validation = self.validate_draft(cfg)
        if not validation["valid"]:
            return {"success": False, "error": "Validation failed", "validation": validation}
        try:
            locked = self.db.execute(
                text("SELECT id FROM dbp_builder_projects WHERE id=:pid AND tenant_id=:tid FOR UPDATE"),
                {"pid": pid, "tid": tenant_id},
            ).fetchone()
            if not locked:
                return {"success": False, "error": "Project not found"}
            created: List[str] = []
            registered: List[str] = []
            for entity in cfg.get("custom_entities", []):
                table = BUILDER_TABLE_PREFIX + entity["entity_code"]
                self._ensure_physical_table(table, entity["fields"])
                created.append(table)
                self._register_entity(tenant_id, table, entity)
                registered.append(entity["entity_code"])
            last = self.db.execute(
                text(
                    "SELECT COALESCE(MAX(version_number),0) FROM dbp_builder_versions "
                    "WHERE project_id=:pid AND tenant_id=:tid FOR UPDATE"
                ),
                {"pid": pid, "tid": tenant_id},
            ).fetchone()
            next_version = int(last[0]) + 1
            version_id = str(uuid.uuid4())
            self.db.execute(
                text("UPDATE dbp_builder_versions SET is_active=false WHERE project_id=:pid AND tenant_id=:tid"),
                {"pid": pid, "tid": tenant_id},
            )
            self.db.execute(
                text(
                    "INSERT INTO dbp_builder_versions "
                    "(id,tenant_id,project_id,version_number,config,change_summary,published_by,is_active) "
                    "VALUES (:id,:tid,:pid,:vn,:cfg,:sum,:by,true)"
                ),
                {
                    "id": version_id,
                    "tid": tenant_id,
                    "pid": pid,
                    "vn": next_version,
                    "cfg": json.dumps(cfg),
                    "sum": change_summary or f"Version {next_version}",
                    "by": published_by,
                },
            )
            self.db.execute(
                text(
                    "UPDATE dbp_builder_projects SET status='published',published_version_id=:vid,updated_at=NOW() "
                    "WHERE id=:pid AND tenant_id=:tid"
                ),
                {"vid": version_id, "pid": pid, "tid": tenant_id},
            )
            self.db.commit()
            return {
                "success": True,
                "version_number": next_version,
                "version_id": version_id,
                "entities_published": registered,
                "tables_created": created,
                "validation": validation,
            }
        except Exception:
            self.db.rollback()
            return {"success": False, "error": "Activation failed; transaction rolled back"}

    def get_active_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text(
                "SELECT v.id,v.project_id,v.version_number,v.config,v.published_by,v.published_at "
                "FROM dbp_builder_versions v JOIN dbp_builder_projects p ON p.id=v.project_id "
                "WHERE v.tenant_id=:tid AND v.is_active=true ORDER BY v.published_at DESC LIMIT 1"
            ),
            {"tid": tenant_id},
        ).fetchone()
        if not row:
            return None
        cfg = row[3] if isinstance(row[3], dict) else json.loads(row[3])
        return {
            "version_id": row[0],
            "project_id": row[1],
            "version_number": row[2],
            "config": cfg,
            "published_by": row[4],
            "published_at": str(row[5]) if row[5] else None,
        }

    def list_versions(self, tenant_id: str, pid: str) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            text(
                "SELECT id,version_number,change_summary,published_by,published_at,is_active "
                "FROM dbp_builder_versions WHERE project_id=:pid AND tenant_id=:tid "
                "ORDER BY version_number DESC LIMIT 200"
            ),
            {"pid": pid, "tid": tenant_id},
        ).fetchall()
        return [
            {
                "id": row[0],
                "version_number": row[1],
                "change_summary": row[2],
                "published_by": row[3],
                "published_at": str(row[4]) if row[4] else None,
                "is_active": row[5],
            }
            for row in rows
        ]

    def rollback(self, tenant_id: str, pid: str, version_id: str, rolled_back_by: str) -> Dict[str, Any]:
        proj = self.get_project(tenant_id, pid)
        if not proj:
            return {"success": False, "error": "Project not found"}
        try:
            locked = self.db.execute(
                text("SELECT id FROM dbp_builder_projects WHERE id=:pid AND tenant_id=:tid FOR UPDATE"),
                {"pid": pid, "tid": tenant_id},
            ).fetchone()
            if not locked:
                return {"success": False, "error": "Project not found"}
            row = self.db.execute(
                text(
                    "SELECT config FROM dbp_builder_versions "
                    "WHERE id=:vid AND project_id=:pid AND tenant_id=:tid"
                ),
                {"vid": version_id, "pid": pid, "tid": tenant_id},
            ).fetchone()
            if not row:
                return {"success": False, "error": "Version not found"}
            target_cfg = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            target_validation = self.validate_draft(target_cfg)
            if not target_validation["valid"]:
                return {"success": False, "error": "Target version is invalid", "validation": target_validation}

            current_codes = {
                entity.get("entity_code") for entity in proj["draft_config"].get("custom_entities", [])
                if entity.get("entity_code")
            }
            target_codes = {
                entity.get("entity_code") for entity in target_cfg.get("custom_entities", [])
                if entity.get("entity_code")
            }
            removed: List[str] = []
            restored: List[str] = []
            for entity in target_cfg.get("custom_entities", []):
                table = BUILDER_TABLE_PREFIX + entity["entity_code"]
                self._ensure_physical_table(table, entity.get("fields", []))
                self._register_entity(tenant_id, table, entity)
                restored.append(entity["entity_code"])
            for entity_code in current_codes - target_codes:
                self._unregister_entity(tenant_id, BUILDER_TABLE_PREFIX + entity_code, entity_code)
                removed.append(entity_code)

            last = self.db.execute(
                text(
                    "SELECT COALESCE(MAX(version_number),0) FROM dbp_builder_versions "
                    "WHERE project_id=:pid AND tenant_id=:tid FOR UPDATE"
                ),
                {"pid": pid, "tid": tenant_id},
            ).fetchone()
            next_version = int(last[0]) + 1
            new_version_id = str(uuid.uuid4())
            self.db.execute(
                text("UPDATE dbp_builder_versions SET is_active=false WHERE project_id=:pid AND tenant_id=:tid"),
                {"pid": pid, "tid": tenant_id},
            )
            self.db.execute(
                text(
                    "INSERT INTO dbp_builder_versions "
                    "(id,tenant_id,project_id,version_number,config,change_summary,published_by,is_active) "
                    "VALUES (:id,:tid,:pid,:vn,:cfg,:sum,:by,true)"
                ),
                {
                    "id": new_version_id,
                    "tid": tenant_id,
                    "pid": pid,
                    "vn": next_version,
                    "cfg": json.dumps(target_cfg),
                    "sum": f"Rollback to version snapshot {version_id}",
                    "by": rolled_back_by,
                },
            )
            self.db.execute(
                text(
                    "UPDATE dbp_builder_projects SET status='published',draft_config=:cfg,published_version_id=:vid,updated_at=NOW() "
                    "WHERE id=:pid AND tenant_id=:tid"
                ),
                {"cfg": json.dumps(target_cfg), "vid": new_version_id, "pid": pid, "tid": tenant_id},
            )
            self.db.commit()
            return {
                "success": True,
                "rolled_back_to_version_id": version_id,
                "new_version_number": next_version,
                "entities_restored": restored,
                "entities_removed": removed,
            }
        except Exception:
            self.db.rollback()
            return {"success": False, "error": "Rollback failed; transaction rolled back"}

    def _save_draft(self, tenant_id: str, pid: str, cfg: Dict[str, Any]) -> bool:
        self.db.execute(
            text(
                "UPDATE dbp_builder_projects SET draft_config=:cfg,updated_at=NOW() "
                "WHERE id=:pid AND tenant_id=:tid"
            ),
            {"cfg": json.dumps(cfg), "pid": pid, "tid": tenant_id},
        )
        self.db.commit()
        return True

    def _ensure_physical_table(self, table_name: str, fields: List[Dict[str, Any]]) -> None:
        if not re.fullmatch(r"bld_[a-z][a-z0-9_]{0,99}", table_name) or len(table_name) > 63:
            raise ValueError("Unsafe builder table name")
        columns: List[Dict[str, Any]] = []
        for field in fields:
            code = field.get("code")
            field_type = field.get("field_type")
            if not isinstance(code, str) or not FIELD_CODE_RE.fullmatch(code):
                raise ValueError(f"Unsafe field code: {code}")
            sql_type = FIELD_SQL_TYPES.get(field_type)
            if not sql_type:
                raise ValueError(f"Unsupported field type: {field_type}")
            columns.append({
                "code": code,
                "sql_type": sql_type,
                "not_null": bool(field.get("is_required")),
            })
        self.db.execute(
            text("SELECT public.eos_create_builder_table(:table_name, CAST(:columns AS JSONB))"),
            {"table_name": table_name, "columns": json.dumps(columns)},
        )

    def _register_entity(self, tenant_id: str, table_name: str, entity: Dict[str, Any]) -> None:
        existing = self.db.execute(
            text(
                "SELECT id,tenant_id,is_system FROM dbp_entities "
                "WHERE code=:code AND tenant_id=:tid"
            ),
            {"code": entity["entity_code"], "tid": tenant_id},
        ).fetchone()
        if existing:
            if existing[2]:
                raise RuntimeError(f"Entity code '{entity['entity_code']}' is reserved as a system entity")
            self._sync_fields(existing[0], entity)
            return
        entity_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_entities "
                "(id,tenant_id,code,name_en,name_ar,faculty,table_mapping,is_system,metadata_schema) "
                "VALUES (:id,:tid,:code,:nen,:nar,:fac,:tbl,false,'{}')"
            ),
            {
                "id": entity_id,
                "tid": tenant_id,
                "code": entity["entity_code"],
                "nen": entity["name_en"],
                "nar": entity.get("name_ar"),
                "fac": entity.get("faculty", "operations"),
                "tbl": table_name,
            },
        )
        self._sync_fields(entity_id, entity)

    def _sync_fields(self, entity_id: str, entity: Dict[str, Any]) -> None:
        desired = {field["code"]: field for field in entity.get("fields", [])}
        current = self.db.execute(
            text("SELECT id,code FROM dbp_fields WHERE entity_id=:eid"), {"eid": entity_id}
        ).fetchall()
        current_map = {row[1]: row[0] for row in current}
        for code, field_id in current_map.items():
            if code not in desired:
                self.db.execute(text("DELETE FROM dbp_fields WHERE id=:fid"), {"fid": field_id})
        for order, (code, field) in enumerate(desired.items(), 1):
            enums = json.dumps(field.get("enum_values", []))
            ui = json.dumps({"component": "input", "order": order})
            params = {
                "label_en": field.get("label_en", code),
                "label_ar": field.get("label_ar"),
                "field_type": field["field_type"],
                "required": bool(field.get("is_required")),
                "enums": enums,
                "ui": ui,
                "eid": entity_id,
                "code": code,
            }
            if code in current_map:
                self.db.execute(
                    text(
                        "UPDATE dbp_fields SET label_en=:label_en,label_ar=:label_ar,field_type=:field_type,"
                        "is_required=:required,enum_values=CAST(:enums AS JSONB),ui_config=CAST(:ui AS JSONB) "
                        "WHERE entity_id=:eid AND code=:code"
                    ),
                    params,
                )
            else:
                self.db.execute(
                    text(
                        "INSERT INTO dbp_fields "
                        "(id,entity_id,code,label_en,label_ar,field_type,is_required,ui_config,enum_values) "
                        "VALUES (:id,:eid,:code,:label_en,:label_ar,:field_type,:required,CAST(:ui AS JSONB),CAST(:enums AS JSONB))"
                    ),
                    {"id": str(uuid.uuid4()), **params},
                )
        self.db.flush()

    def _unregister_entity(self, tenant_id: str, table_name: str, entity_code: str) -> None:
        row = self.db.execute(
            text(
                "SELECT id FROM dbp_entities "
                "WHERE code=:code AND tenant_id=:tid AND is_system=false"
            ),
            {"code": entity_code, "tid": tenant_id},
        ).fetchone()
        if not row:
            return
        self.db.execute(text("DELETE FROM dbp_fields WHERE entity_id=:eid"), {"eid": row[0]})
        self.db.execute(text("DELETE FROM dbp_relationships WHERE entity_id=:eid"), {"eid": row[0]})
        self.db.execute(text("DELETE FROM dbp_entities WHERE id=:eid"), {"eid": row[0]})
        self.db.flush()
