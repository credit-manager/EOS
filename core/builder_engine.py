"""
P54 Self-Service ERP Builder Engine
Draft editing → Preview → Approval Gate → Publish (real entities) → Versioning → Rollback.
Generic platform capability — no business-specific code.

Publishing registers custom entities into the dynamic platform metadata
(dbp_entities/dbp_fields) with real physical tables, making them immediately
usable via standard Dynamic CRUD (/api/v1/dynamic/entities/{code}/records).

Tenant model:
- entity_code is reusable across tenants;
- dbp_entities uniqueness is (tenant_id, code) for tenant entities;
- physical builder tables are shared and always contain tenant_id, so tenant
  data remains isolated without multiplying tables per customer;
- global/system entities (tenant_id IS NULL) remain globally unique.

Transaction model:
- draft saves are independent transactions;
- publish is one database transaction, including PostgreSQL DDL;
- rollback is one transaction and reconciles target metadata/schema before
  creating a new immutable rollback version;
- physical tables are never dropped during rollback because that can destroy
  tenant data. Obsolete columns remain inert and are no longer exposed by
  metadata. A later schema garbage-collection process can remove them only
  after an explicit retention/safety policy.
"""
import json
import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.ai_composer import MODULE_DEPENDENCIES

ENTITY_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,99}$")
FIELD_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,99}$")
VALID_FIELD_TYPES = {"string", "text", "integer", "float", "number", "boolean",
                     "date", "datetime", "enum", "json"}

FIELD_SQL_TYPES = {
    "string": "VARCHAR(255)", "text": "TEXT", "integer": "INTEGER",
    "float": "DOUBLE PRECISION", "number": "DOUBLE PRECISION", "boolean": "BOOLEAN",
    "date": "DATE", "datetime": "TIMESTAMP", "enum": "VARCHAR(50)", "json": "JSONB",
}
BUILDER_TABLE_PREFIX = "bld_"


def _new_draft_from_composer(composer_config: dict | None) -> dict[str, Any]:
    composer_config = composer_config or {}
    return {
        "industry": composer_config.get("industry"),
        "settings": composer_config.get("settings", {"currency": "SAR"}),
        "modules": [{"code": m, "enabled": True} for m in composer_config.get("modules", [])],
        "custom_entities": [], "relationships": [],
        "roles": composer_config.get("roles", {}),
        "workflows": composer_config.get("workflows", []),
        "kpis": composer_config.get("kpis", []),
    }


class BuilderEngine:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, tenant_id: str, name: str,
                       composer_session_id: str | None = None,
                       initial_config: dict | None = None) -> dict[str, Any]:
        pid = str(uuid.uuid4())
        draft = _new_draft_from_composer(initial_config)
        if composer_session_id:
            row = self.db.execute(text(
                "SELECT generated_config FROM dbp_composer_sessions WHERE id=:sid AND tenant_id=:tid"
            ), {"sid": composer_session_id, "tid": tenant_id}).fetchone()
            if not row:
                return {"success": False, "error": "Composer session not found"}
            cfg = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            draft = _new_draft_from_composer(cfg)
        self.db.execute(text(
            "INSERT INTO dbp_builder_projects "
            "(id, tenant_id, name, source_composer_session_id, status, draft_config) "
            "VALUES (:id,:tid,:name,:sid,'draft',:cfg)"
        ), {"id": pid, "tid": tenant_id, "name": name, "sid": composer_session_id,
            "cfg": json.dumps(draft)})
        self.db.flush()
        return {"success": True, "project_id": pid, "draft_config": draft}

    def get_project(self, tenant_id: str, project_id: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id,tenant_id,name,source_composer_session_id,status,draft_config,"
            "published_version_id,created_at,updated_at FROM dbp_builder_projects "
            "WHERE id=:pid AND tenant_id=:tid"
        ), {"pid": project_id, "tid": tenant_id}).fetchone()
        if not row: return None
        cfg = row[5] if isinstance(row[5], dict) else json.loads(row[5])
        return {"id":row[0],"tenant_id":row[1],"name":row[2],"source_composer_session_id":row[3],
                "status":row[4],"draft_config":cfg,"published_version_id":row[6],
                "created_at":str(row[7]) if row[7] else None,"updated_at":str(row[8]) if row[8] else None}

    def list_projects(self, tenant_id: str) -> list[dict]:
        rows = self.db.execute(text(
            "SELECT id,name,status,created_at,updated_at FROM dbp_builder_projects "
            "WHERE tenant_id=:tid ORDER BY created_at DESC"
        ), {"tid":tenant_id}).fetchall()
        return [{"id":r[0],"name":r[1],"status":r[2],"created_at":str(r[3]) if r[3] else None,
                 "updated_at":str(r[4]) if r[4] else None} for r in rows]

    def update_settings(self, tenant_id: str, pid: str, settings: dict) -> bool:
        proj=self.get_project(tenant_id,pid)
        if not proj:return False
        merged=dict(proj["draft_config"].get("settings",{})); merged.update(settings)
        proj["draft_config"]["settings"]=merged
        return self._save_draft(tenant_id,pid,proj["draft_config"])

    def set_modules(self, tenant_id: str, pid: str, modules: list[dict]) -> dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        seen={}
        for m in modules:
            code=m.get("code")
            if not code or not ENTITY_CODE_RE.match(code):
                return {"success":False,"error":f"Invalid module code: {code!r}"}
            seen[code]=bool(m.get("enabled",True))
        existing={m["code"]:m.get("enabled",True) for m in proj["draft_config"].get("modules",[])}
        existing.update(seen); proj["draft_config"]["modules"]= [{"code":c,"enabled":e} for c,e in sorted(existing.items())]
        return {"success":self._save_draft(tenant_id,pid,proj["draft_config"])}

    def add_entity(self, tenant_id: str, pid: str, entity_def: dict) -> dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        ecode=entity_def.get("entity_code")
        if not ecode or not ENTITY_CODE_RE.match(ecode):return {"success":False,"error":f"Invalid entity_code: {ecode!r}"}
        if not entity_def.get("name_en"):return {"success":False,"error":"name_en required"}
        fields=entity_def.get("fields",[])
        if not fields:return {"success":False,"error":"At least one field required"}
        seen=set()
        for fld in fields:
            fcode=fld.get("code")
            if not fcode or not FIELD_CODE_RE.match(fcode):return {"success":False,"error":f"Invalid field code: {fcode!r}"}
            if fcode in seen:return {"success":False,"error":f"Duplicate field: {fcode}"}
            seen.add(fcode)
            if fld.get("field_type") not in VALID_FIELD_TYPES:return {"success":False,"error":f"Invalid field_type: {fld.get('field_type')!r}"}
            if fld.get("field_type")=="enum" and not fld.get("enum_values"):return {"success":False,"error":f"Enum field '{fcode}' requires enum_values"}
        cfg=proj["draft_config"]; entities={e["entity_code"]:e for e in cfg.get("custom_entities",[])}
        if ecode in entities:return {"success":False,"error":f"Entity '{ecode}' already exists in draft"}
        entities[ecode]={"entity_code":ecode,"name_en":entity_def["name_en"],"name_ar":entity_def.get("name_ar"),
                         "faculty":entity_def.get("faculty","operations"),"fields":fields}
        cfg["custom_entities"]=list(entities.values()); self._save_draft(tenant_id,pid,cfg)
        return {"success":True,"entity_code":ecode}

    def remove_entity(self, tenant_id: str, pid: str, ecode: str) -> dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        cfg=proj["draft_config"]; before=len(cfg.get("custom_entities",[]))
        cfg["custom_entities"]=[e for e in cfg.get("custom_entities",[]) if e["entity_code"]!=ecode]
        if len(cfg["custom_entities"])==before:return {"success":False,"error":f"Entity '{ecode}' not in draft"}
        self._save_draft(tenant_id,pid,cfg); return {"success":True}

    def add_relationship(self, tenant_id: str, pid: str, rel: dict) -> dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        if not rel.get("from_entity") or not rel.get("to_entity"):return {"success":False,"error":"from_entity and to_entity required"}
        proj["draft_config"].setdefault("relationships",[]).append(rel); self._save_draft(tenant_id,pid,proj["draft_config"]); return {"success":True}

    def set_roles(self, tenant_id: str, pid: str, roles: dict) -> bool:
        proj=self.get_project(tenant_id,pid)
        if not proj:return False
        proj["draft_config"]["roles"]=roles; return self._save_draft(tenant_id,pid,proj["draft_config"])

    def add_workflow(self, tenant_id: str, pid: str, wf: dict) -> dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        if not wf.get("name"):return {"success":False,"error":"Workflow name required"}
        proj["draft_config"].setdefault("workflows",[]).append(wf); self._save_draft(tenant_id,pid,proj["draft_config"]); return {"success":True}

    def add_kpi(self, tenant_id: str, pid: str, kpi: dict) -> dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        if not kpi.get("name"):return {"success":False,"error":"KPI name required"}
        proj["draft_config"].setdefault("kpis",[]).append(kpi); self._save_draft(tenant_id,pid,proj["draft_config"]); return {"success":True}

    def validate_draft(self,cfg:dict)->dict[str,Any]:
        errors=[]; warnings=[]; enabled=[m["code"] for m in cfg.get("modules",[]) if m.get("enabled")]
        for mod in enabled:
            for dep in MODULE_DEPENDENCIES.get(mod,[]):
                if dep not in enabled:errors.append(f"Module '{mod}' requires '{dep}'")
        known=set()
        for ent in cfg.get("custom_entities",[]):
            code=ent.get("entity_code")
            if not code or not ENTITY_CODE_RE.match(code):errors.append(f"Invalid entity code: {code!r}"); continue
            if code in known:errors.append(f"Duplicate entity: {code}")
            known.add(code)
            fields=ent.get("fields",[]); fseen=set()
            for fld in fields:
                fc=fld.get("code")
                if not fc or not FIELD_CODE_RE.match(fc):errors.append(f"Invalid field code in '{code}': {fc!r}")
                elif fc in fseen:errors.append(f"Duplicate field '{fc}' in '{code}'")
                else:fseen.add(fc)
                if fld.get("field_type") not in VALID_FIELD_TYPES:errors.append(f"Invalid field type in '{code}.{fc}'")
        for r in cfg.get("relationships",[]):
            if r.get("from_entity") not in known:errors.append(f"Relationship references unknown entity '{r.get('from_entity')}'")
            if r.get("to_entity") not in known:errors.append(f"Relationship references unknown entity '{r.get('to_entity')}'")
        tables=set()
        for ent in cfg.get("custom_entities",[]):
            t=BUILDER_TABLE_PREFIX+ent.get("entity_code","")
            if t in tables:errors.append(f"Table collision: {t}")
            tables.add(t)
        return {"valid":not errors,"errors":errors,"warnings":warnings,"summary":{
            "enabled_modules":len(enabled),"disabled_modules":sum(1 for m in cfg.get("modules",[]) if not m.get("enabled")),
            "custom_entities":len(cfg.get("custom_entities",[])),"total_fields":sum(len(e.get("fields",[])) for e in cfg.get("custom_entities",[])),
            "relationships":len(cfg.get("relationships",[])),"roles":len(cfg.get("roles",{})),"workflows":len(cfg.get("workflows",[])),"kpis":len(cfg.get("kpis",[]))}}

    def preview(self,tenant_id:str,pid:str)->dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return None
        return {"project_id":pid,"project_name":proj["name"],"status":proj["status"],"config":proj["draft_config"],"validation":self.validate_draft(proj["draft_config"])}

    def publish(self, tenant_id: str, pid: str, published_by: str, confirmed: bool, change_summary: str = "") -> dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        if not confirmed:return {"success":False,"error":"Explicit approval required: pass confirmed=true to publish"}
        cfg=proj["draft_config"]; validation=self.validate_draft(cfg)
        if not validation["valid"]:return {"success":False,"error":"Validation failed","validation":validation}
        try:
            self.db.execute(text("SELECT id FROM dbp_builder_projects WHERE id=:pid AND tenant_id=:tid FOR UPDATE"),{"pid":pid,"tid":tenant_id}).fetchone()
            created=[]; registered=[]
            for ent in cfg.get("custom_entities",[]):
                tbl=BUILDER_TABLE_PREFIX+ent["entity_code"]
                self._ensure_physical_table(tbl,ent["fields"])
                created.append(tbl); self._register_entity(tenant_id,tbl,ent); registered.append(ent["entity_code"])
            last=self.db.execute(text("SELECT COALESCE(MAX(version_number),0) FROM dbp_builder_versions WHERE project_id=:pid AND tenant_id=:tid FOR UPDATE"),{"pid":pid,"tid":tenant_id}).fetchone()
            next_ver=int(last[0])+1; vid=str(uuid.uuid4())
            self.db.execute(text("UPDATE dbp_builder_versions SET is_active=false WHERE project_id=:pid AND tenant_id=:tid"),{"pid":pid,"tid":tenant_id})
            self.db.execute(text("INSERT INTO dbp_builder_versions (id,tenant_id,project_id,version_number,config,change_summary,published_by,is_active) VALUES (:id,:tid,:pid,:vn,:cfg,:sum,:by,true)"),
                             {"id":vid,"tid":tenant_id,"pid":pid,"vn":next_ver,"cfg":json.dumps(cfg),"sum":change_summary or f"Version {next_ver}","by":published_by})
            self.db.execute(text("UPDATE dbp_builder_projects SET status='published',published_version_id=:vid,updated_at=NOW() WHERE id=:pid AND tenant_id=:tid"),{"vid":vid,"pid":pid,"tid":tenant_id})
            self.db.commit()
            return {"success":True,"version_number":next_ver,"version_id":vid,"entities_published":registered,"tables_created":created,"validation":validation}
        except Exception as exc:
            self.db.rollback()
            return {"success":False,"error":f"Activation failed; transaction rolled back: {exc}"}

    def get_active_config(self,tenant_id:str)->dict | None:
        row=self.db.execute(text("SELECT v.id,v.project_id,v.version_number,v.config,v.published_by,v.published_at FROM dbp_builder_versions v JOIN dbp_builder_projects p ON p.id=v.project_id WHERE v.tenant_id=:tid AND v.is_active=true ORDER BY v.published_at DESC LIMIT 1"),{"tid":tenant_id}).fetchone()
        if not row:return None
        cfg=row[3] if isinstance(row[3],dict) else json.loads(row[3])
        return {"version_id":row[0],"project_id":row[1],"version_number":row[2],"config":cfg,"published_by":row[4],"published_at":str(row[5]) if row[5] else None}

    def list_versions(self,tenant_id:str,pid:str)->list[dict]:
        rows=self.db.execute(text("SELECT id,version_number,change_summary,published_by,published_at,is_active FROM dbp_builder_versions WHERE project_id=:pid AND tenant_id=:tid ORDER BY version_number DESC"),{"pid":pid,"tid":tenant_id}).fetchall()
        return [{"id":r[0],"version_number":r[1],"change_summary":r[2],"published_by":r[3],"published_at":str(r[4]) if r[4] else None,"is_active":r[5]} for r in rows]

    def rollback(self,tenant_id:str,pid:str,version_id:str,rolled_back_by:str)->dict[str,Any]:
        proj=self.get_project(tenant_id,pid)
        if not proj:return {"success":False,"error":"Project not found"}
        try:
            self.db.execute(text("SELECT id FROM dbp_builder_projects WHERE id=:pid AND tenant_id=:tid FOR UPDATE"),{"pid":pid,"tid":tenant_id}).fetchone()
            row=self.db.execute(text("SELECT config FROM dbp_builder_versions WHERE id=:vid AND project_id=:pid AND tenant_id=:tid"),{"vid":version_id,"pid":pid,"tid":tenant_id}).fetchone()
            if not row:return {"success":False,"error":"Version not found"}
            target_cfg=row[0] if isinstance(row[0],dict) else json.loads(row[0])
            current_codes={e["entity_code"] for e in proj["draft_config"].get("custom_entities",[])}
            target_codes={e["entity_code"] for e in target_cfg.get("custom_entities",[])}
            removed=[]; restored=[]
            for ent in target_cfg.get("custom_entities",[]):
                tbl=BUILDER_TABLE_PREFIX+ent["entity_code"]
                self._ensure_physical_table(tbl,ent.get("fields",[]))
                self._register_entity(tenant_id,tbl,ent)
                restored.append(ent["entity_code"])
            for ecode in current_codes-target_codes:
                self._unregister_entity(tenant_id,BUILDER_TABLE_PREFIX+ecode,ecode); removed.append(ecode)
            last=self.db.execute(text("SELECT COALESCE(MAX(version_number),0) FROM dbp_builder_versions WHERE project_id=:pid AND tenant_id=:tid FOR UPDATE"),{"pid":pid,"tid":tenant_id}).fetchone()
            next_ver=int(last[0])+1; vid=str(uuid.uuid4())
            self.db.execute(text("UPDATE dbp_builder_versions SET is_active=false WHERE project_id=:pid AND tenant_id=:tid"),{"pid":pid,"tid":tenant_id})
            self.db.execute(text("INSERT INTO dbp_builder_versions (id,tenant_id,project_id,version_number,config,change_summary,published_by,is_active) VALUES (:id,:tid,:pid,:vn,:cfg,:sum,:by,true)"),
                             {"id":vid,"tid":tenant_id,"pid":pid,"vn":next_ver,"cfg":json.dumps(target_cfg),"sum":f"Rollback to version snapshot {version_id}","by":rolled_back_by})
            self.db.execute(text("UPDATE dbp_builder_projects SET status='published',draft_config=:cfg,published_version_id=:vid,updated_at=NOW() WHERE id=:pid AND tenant_id=:tid"),{"cfg":json.dumps(target_cfg),"vid":vid,"pid":pid,"tid":tenant_id})
            self.db.commit()
            return {"success":True,"rolled_back_to_version_id":version_id,"new_version_number":next_ver,"entities_restored":restored,"entities_removed":removed}
        except Exception as exc:
            self.db.rollback(); return {"success":False,"error":f"Rollback failed; transaction rolled back: {exc}"}

    def _save_draft(self,tenant_id:str,pid:str,cfg:dict)->bool:
        self.db.execute(text("UPDATE dbp_builder_projects SET draft_config=:cfg,updated_at=NOW() WHERE id=:pid AND tenant_id=:tid"),{"cfg":json.dumps(cfg),"pid":pid,"tid":tenant_id})
        self.db.commit(); return True

    def _ensure_physical_table(self,table_name:str,fields:list[dict]):
        """Apply schema changes inside the caller's transaction. Never commit here."""
        if not re.match(r"^[a-z][a-z0-9_]{0,62}$",table_name): raise ValueError("Unsafe table name")
        col_defs=["id VARCHAR(36) PRIMARY KEY","tenant_id VARCHAR(100) NOT NULL"]
        for fld in fields:
            code=fld["code"]
            if not FIELD_CODE_RE.match(code): raise ValueError(f"Unsafe field code: {code}")
            sqltype=FIELD_SQL_TYPES[fld["field_type"]]; notnull=" NOT NULL" if fld.get("is_required") else ""
            col_defs.append(f"{code} {sqltype}{notnull}")
        col_defs.append("created_at TIMESTAMP DEFAULT NOW()")
        self.db.execute(text(f"CREATE TABLE IF NOT EXISTS public.{table_name} ({', '.join(col_defs)})"))
        for fld in fields:
            code=fld["code"]; sqltype=FIELD_SQL_TYPES[fld["field_type"]]
            self.db.execute(text(f"ALTER TABLE public.{table_name} ADD COLUMN IF NOT EXISTS {code} {sqltype}"))

    def _register_entity(self,tenant_id:str,table_name:str,ent:dict):
        # Entity codes are tenant-scoped. A global/system entity is never
        # implicitly reused by a tenant custom entity.
        existing=self.db.execute(text("SELECT id,tenant_id,is_system FROM dbp_entities WHERE code=:code AND tenant_id=:tid"),{"code":ent["entity_code"],"tid":tenant_id}).fetchone()
        if existing:
            if existing[2]: raise RuntimeError(f"Entity code '{ent['entity_code']}' is reserved as a system entity")
            self._sync_fields(existing[0],ent); return
        eid=str(uuid.uuid4())
        self.db.execute(text("INSERT INTO dbp_entities (id,tenant_id,code,name_en,name_ar,faculty,table_mapping,is_system,metadata_schema) VALUES (:id,:tid,:code,:nen,:nar,:fac,:tbl,false,'{}')"),
                         {"id":eid,"tid":tenant_id,"code":ent["entity_code"],"nen":ent["name_en"],"nar":ent.get("name_ar"),"fac":ent.get("faculty","operations"),"tbl":table_name})
        self._sync_fields(eid,ent)

    def _sync_fields(self,entity_id:str,ent:dict):
        desired={f["code"]:f for f in ent.get("fields",[])}
        current=self.db.execute(text("SELECT id,code FROM dbp_fields WHERE entity_id=:eid"),{"eid":entity_id}).fetchall()
        current_map={r[1]:r[0] for r in current}
        for code,fid in current_map.items():
            if code not in desired:self.db.execute(text("DELETE FROM dbp_fields WHERE id=:fid"),{"fid":fid})
        for order,(code,fld) in enumerate(desired.items(),1):
            enums=json.dumps(fld.get("enum_values",[])); ui=json.dumps({"component":"input","order":order})
            if code in current_map:
                self.db.execute(text("UPDATE dbp_fields SET label_en=:len,label_ar=:lar,field_type=:ftype,is_required=:req,enum_values=CAST(:enums AS JSONB),ui_config=CAST(:ui AS JSONB) WHERE entity_id=:eid AND code=:code"),
                                 {"len":fld.get("label_en",code),"lar":fld.get("label_ar"),"ftype":fld["field_type"],"req":bool(fld.get("is_required")),"enums":enums,"ui":ui,"eid":entity_id,"code":code})
            else:
                self.db.execute(text("INSERT INTO dbp_fields (id,entity_id,code,label_en,label_ar,field_type,is_required,ui_config,enum_values) VALUES (:id,:eid,:code,:len,:lar,:ftype,:req,CAST(:ui AS JSONB),CAST(:enums AS JSONB)"),
                                 {"id":str(uuid.uuid4()),"eid":entity_id,"code":code,"len":fld.get("label_en",code),"lar":fld.get("label_ar"),"ftype":fld["field_type"],"req":bool(fld.get("is_required")),"enums":enums,"ui":ui})
        self.db.flush()

    def _unregister_entity(self,tenant_id:str,table_name:str,ecode:str):
        row=self.db.execute(text("SELECT id FROM dbp_entities WHERE code=:code AND tenant_id=:tid AND is_system=false"),{"code":ecode,"tid":tenant_id}).fetchone()
        if not row:return
        self.db.execute(text("DELETE FROM dbp_fields WHERE entity_id=:eid"),{"eid":row[0]})
        self.db.execute(text("DELETE FROM dbp_relationships WHERE entity_id=:eid"),{"eid":row[0]})
        self.db.execute(text("DELETE FROM dbp_entities WHERE id=:eid"),{"eid":row[0]})
        self.db.flush()
