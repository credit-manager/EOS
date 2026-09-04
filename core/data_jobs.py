"""P18 Data Job Engine — tenant-scoped synchronous jobs.

Dynamic table/column names are validated as SQL identifiers and every
operation requires an explicit tenant context. Tenant filters are never
accepted from job configuration; the authenticated tenant is authoritative.
"""

import json
import re
import time
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


class DataJobEngine:
    VALID_JOB_TYPES = {"import", "export", "sync", "report", "batch_update", "batch_delete"}
    VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _identifier(value: str, label: str) -> str:
        if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"Invalid {label}")
        return value

    def _entity_table(self, entity_code: str, tenant_id: str) -> str | None:
        row = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code=:ec AND (tenant_id=:tid OR tenant_id IS NULL) ORDER BY CASE WHEN tenant_id=:tid THEN 0 ELSE 1 END LIMIT 1"),
            {"ec": entity_code, "tid": tenant_id},
        ).fetchone()
        if not row or not row[0]:
            return None
        return self._identifier(row[0], "table mapping")

    def _has_tenant_column(self, table_name: str) -> bool:
        row = self.db.execute(
            text("SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=:table AND column_name='tenant_id' LIMIT 1"),
            {"table": table_name},
        ).fetchone()
        return bool(row)

    def create_job(self, code: str, name_en: str, job_type: str, tenant_id: str | None = None,
                   name_ar: str | None = None, entity_code: str | None = None,
                   config: dict[str, Any] | None = None, priority: int = 0,
                   scheduled_at: str | None = None, created_by: str | None = None) -> str | None:
        if not tenant_id or job_type not in self.VALID_JOB_TYPES:
            return None
        job_id = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_data_jobs (id,tenant_id,code,name_en,name_ar,job_type,entity_code,status,priority,config,created_by,scheduled_at) "
            "VALUES (:id,:tenant,:code,:name_en,:name_ar,:jtype,:entity,'pending',:priority,:config,:created_by,:sched)"),
            {"id": job_id, "tenant": tenant_id, "code": code, "name_en": name_en,
             "name_ar": name_ar, "jtype": job_type, "entity": entity_code,
             "priority": max(min(int(priority), 100), -100), "config": json.dumps(config or {}),
             "created_by": created_by, "sched": scheduled_at})
        self.db.flush()
        return job_id

    def execute_job(self, job_id: str, tenant_id: str | None = None) -> dict[str, Any]:
        if not tenant_id:
            return {"success": False, "error": "Tenant context required"}
        row = self.db.execute(text(
            "SELECT id,job_type,entity_code,config,status FROM dbp_data_jobs WHERE id=:jid AND tenant_id=:tid FOR UPDATE"),
            {"jid": job_id, "tid": tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Job not found"}
        if row[4] not in ("pending", "failed"):
            return {"success": False, "error": f"Cannot execute job in '{row[4]}' status"}
        try:
            config = row[3] or {}
            if isinstance(config, str):
                config = json.loads(config)
            self.db.execute(text("UPDATE dbp_data_jobs SET status='running',started_at=NOW(),progress=0 WHERE id=:jid AND tenant_id=:tid"), {"jid":job_id,"tid":tenant_id})
            self.db.flush()
            started = time.time()
            if row[1] == "import":
                result = self._execute_import(row[2], config, tenant_id)
            elif row[1] == "export":
                result = self._execute_export(row[2], config, tenant_id)
            elif row[1] == "batch_update":
                result = self._execute_batch_update(row[2], config, tenant_id)
            elif row[1] == "batch_delete":
                result = self._execute_batch_delete(row[2], config, tenant_id)
            elif row[1] == "report":
                result = self._execute_report(row[2], config, tenant_id)
            elif row[1] == "sync":
                result = self._execute_sync(row[2], config, tenant_id)
            else:
                raise ValueError("Unknown job type")
            result["duration_ms"] = int((time.time() - started) * 1000)
            self.db.execute(text("UPDATE dbp_data_jobs SET status='completed',progress=100,result=:res,completed_at=NOW() WHERE id=:jid AND tenant_id=:tid"), {"jid":job_id,"tid":tenant_id,"res":json.dumps(result)})
            self.db.flush()
            return {"success": True, **result}
        except Exception as exc:
            self.db.rollback()
            message = str(exc)[:500]
            self.db.execute(text("UPDATE dbp_data_jobs SET status='failed',error_message=:err WHERE id=:jid AND tenant_id=:tid"), {"jid":job_id,"tid":tenant_id,"err":message})
            self.db.flush()
            return {"success": False, "error": message}

    def cancel_job(self, job_id: str, tenant_id: str | None = None) -> dict[str, Any]:
        if not tenant_id:
            return {"success": False, "error": "Tenant context required"}
        row = self.db.execute(text("SELECT status FROM dbp_data_jobs WHERE id=:jid AND tenant_id=:tid FOR UPDATE"), {"jid":job_id,"tid":tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Job not found"}
        if row[0] in ("completed", "cancelled"):
            return {"success": False, "error": f"Cannot cancel job in '{row[0]}' status"}
        self.db.execute(text("UPDATE dbp_data_jobs SET status='cancelled' WHERE id=:jid AND tenant_id=:tid"), {"jid":job_id,"tid":tenant_id})
        self.db.flush()
        return {"success": True}

    def get_job(self, job_id: str, tenant_id: str | None = None) -> dict | None:
        if not tenant_id:
            return None
        r = self.db.execute(text("SELECT id,tenant_id,code,name_en,name_ar,job_type,entity_code,status,priority,config,result,progress,error_message,started_at,completed_at,scheduled_at,created_by,created_at FROM dbp_data_jobs WHERE id=:jid AND tenant_id=:tid"), {"jid":job_id,"tid":tenant_id}).fetchone()
        if not r:
            return None
        return {"id":r[0],"tenant_id":r[1],"code":r[2],"name_en":r[3],"name_ar":r[4],"job_type":r[5],"entity_code":r[6],"status":r[7],"priority":r[8],"config":r[9],"result":r[10],"progress":r[11],"error_message":r[12],"started_at":r[13].isoformat() if r[13] else None,"completed_at":r[14].isoformat() if r[14] else None,"scheduled_at":r[15].isoformat() if r[15] else None,"created_by":r[16],"created_at":r[17].isoformat() if r[17] else None}

    def list_jobs(self, tenant_id: str | None = None, job_type: str | None = None, status: str | None = None,
                  entity_code: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        if not tenant_id:
            return []
        conditions = ["tenant_id=:tid"]
        params: dict[str, Any] = {"tid": tenant_id, "lim": min(max(int(limit), 1), 500), "off": max(int(offset), 0)}
        if job_type:
            if job_type not in self.VALID_JOB_TYPES: return []
            conditions.append("job_type=:jt"); params["jt"] = job_type
        if status:
            if status not in self.VALID_STATUSES: return []
            conditions.append("status=:st"); params["st"] = status
        if entity_code:
            conditions.append("entity_code=:ec"); params["ec"] = entity_code
        rows = self.db.execute(text(f"SELECT id,tenant_id,code,name_en,name_ar,job_type,entity_code,status,priority,progress,created_by,created_at FROM dbp_data_jobs WHERE {' AND '.join(conditions)} ORDER BY priority DESC,created_at DESC LIMIT :lim OFFSET :off"), params).fetchall()
        return [{"id":r[0],"tenant_id":r[1],"code":r[2],"name_en":r[3],"name_ar":r[4],"job_type":r[5],"entity_code":r[6],"status":r[7],"priority":r[8],"progress":r[9],"created_by":r[10],"created_at":r[11].isoformat() if r[11] else None} for r in rows]

    def _require_table(self, entity_code: str, tenant_id: str) -> tuple[str, bool]:
        if not entity_code:
            raise ValueError("entity_code required")
        table = self._entity_table(entity_code, tenant_id)
        if not table:
            raise ValueError("Entity or table mapping not found")
        has_tenant = self._has_tenant_column(table)
        if not has_tenant:
            raise ValueError("Dynamic job requires a tenant-scoped entity table")
        return table, has_tenant

    def _execute_import(self, entity_code: str, config: dict, tenant_id: str) -> dict:
        table, _ = self._require_table(entity_code, tenant_id)
        records = config.get("records", [])
        if not isinstance(records, list): raise ValueError("records must be a list")
        affected = 0; errors = []
        for i, rec in enumerate(records):
            try:
                if not isinstance(rec, dict): raise ValueError("record must be an object")
                clean = {self._identifier(k, "column"): v for k, v in rec.items() if k != "tenant_id"}
                if not clean: raise ValueError("record contains no writable fields")
                clean["tenant_id"] = tenant_id
                cols = list(clean); placeholders = [f":v{j}" for j in range(len(cols))]
                params = {f"v{j}": clean[c] for j, c in enumerate(cols)}
                self.db.execute(text(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"), params)
                affected += 1
            except Exception as exc: errors.append(f"Row {i}: {str(exc)[:100]}")
        self.db.flush()
        return {"rows_processed":len(records),"rows_affected":affected,"errors":errors}

    def _execute_export(self, entity_code: str, config: dict, tenant_id: str) -> dict:
        table, _ = self._require_table(entity_code, tenant_id)
        limit = min(max(int(config.get("limit", 1000)), 1), 10000)
        rows = self.db.execute(text(f"SELECT * FROM {table} WHERE tenant_id=:tid LIMIT :lim"), {"tid":tenant_id,"lim":limit}).fetchall()
        return {"rows_processed":len(rows),"rows_affected":len(rows),"errors":[],"export_count":len(rows)}

    def _execute_batch_update(self, entity_code: str, config: dict, tenant_id: str) -> dict:
        table, _ = self._require_table(entity_code, tenant_id)
        updates = config.get("updates", []); errors=[]; affected=0
        if not isinstance(updates, list): raise ValueError("updates must be a list")
        for i, upd in enumerate(updates):
            try:
                record_id = upd.get("record_id"); sets = upd.get("set", {})
                if not record_id or not isinstance(sets, dict): raise ValueError("record_id and set are required")
                parts=[]; params={"rid":record_id,"tid":tenant_id}
                for j,(key,value) in enumerate(sets.items()):
                    key=self._identifier(key,"column")
                    if key == "tenant_id": raise ValueError("tenant_id cannot be changed")
                    parts.append(f"{key}=:v{j}"); params[f"v{j}"]=value
                if not parts: raise ValueError("no fields to update")
                result=self.db.execute(text(f"UPDATE {table} SET {', '.join(parts)} WHERE id=:rid AND tenant_id=:tid"),params); affected += result.rowcount
            except Exception as exc: errors.append(f"Row {i}: {str(exc)[:100]}")
        self.db.flush(); return {"rows_processed":len(updates),"rows_affected":affected,"errors":errors}

    def _execute_batch_delete(self, entity_code: str, config: dict, tenant_id: str) -> dict:
        table, _ = self._require_table(entity_code, tenant_id)
        ids=config.get("record_ids", [])
        if not isinstance(ids,list) or not ids: return {"rows_processed":0,"rows_affected":0,"errors":["No record IDs"]}
        params={"tid":tenant_id}; placeholders=[]
        for j,rid in enumerate(ids): placeholders.append(f":rid{j}"); params[f"rid{j}"]=rid
        result=self.db.execute(text(f"DELETE FROM {table} WHERE tenant_id=:tid AND id IN ({', '.join(placeholders)})"),params)
        self.db.flush(); return {"rows_processed":len(ids),"rows_affected":result.rowcount,"errors":[]}

    def _execute_report(self, entity_code: str, config: dict, tenant_id: str) -> dict:
        table,_=self._require_table(entity_code,tenant_id)
        field=self._identifier(config.get("field","id"),"report field")
        func=str(config.get("func","count")).upper()
        if func not in {"COUNT","SUM","AVG","MIN","MAX"}: func="COUNT"; field="id"
        r=self.db.execute(text(f"SELECT {func}({field}) FROM {table} WHERE tenant_id=:tid"),{"tid":tenant_id}).fetchone()
        return {"rows_processed":1,"rows_affected":1,"errors":[],"report":{func.lower():r[0] if r else 0,"field":field}}

    def _execute_sync(self, entity_code: str, config: dict, tenant_id: str) -> dict:
        source=config.get("source_entity")
        target=config.get("target_entity") or entity_code
        if not source: raise ValueError("source_entity required")
        source_table,_=self._require_table(source,tenant_id); target_table,_=self._require_table(target,tenant_id)
        limit=min(max(int(config.get("limit",500)),1),5000)
        rows=self.db.execute(text(f"SELECT * FROM {source_table} WHERE tenant_id=:tid LIMIT :lim"),{"tid":tenant_id,"lim":limit}).fetchall()
        # Sync execution is intentionally read-only until an explicit mapping is supplied;
        # never copy arbitrary source rows into a target schema.
        return {"rows_processed":len(rows),"rows_affected":0,"errors":[],"synced_from":source,"synced_to":target,"target_table":target_table,"mode":"preview"}
