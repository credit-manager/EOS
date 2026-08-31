import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text


class SystemEngine:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ config
    def get_config(self, tenant_id: str, config_key: str) -> Optional[Dict]:
        row = self.db.execute(
            text("SELECT * FROM dbp_system_config WHERE tenant_id=:tid AND config_key=:ck"),
            {"tid": tenant_id, "ck": config_key},
        ).mappings().first()
        return self._serialize(row) if row else None

    def set_config(self, tenant_id: str, config_key: str, config_value, **kw) -> str:
        existing = self.get_config(tenant_id, config_key)
        if existing:
            self.db.execute(
                text("UPDATE dbp_system_config SET config_value=:cv, updated_at=now() "
                     "WHERE tenant_id=:tid AND config_key=:ck"),
                {"cv": json.dumps(config_value), "tid": tenant_id, "ck": config_key},
            )
            self.db.commit()
            return existing["id"]
        cid = str(uuid4())
        self.db.execute(
            text("INSERT INTO dbp_system_config "
                 "(id,tenant_id,config_key,config_value,description,category,is_sensitive,created_at,updated_at) "
                 "VALUES (:id,:tid,:ck,:cv,:desc,:cat,:sens,now(),now())"),
            {
                "id": cid,
                "tid": tenant_id,
                "ck": config_key,
                "cv": json.dumps(config_value),
                "desc": kw.get("description"),
                "cat": kw.get("category", "general"),
                "sens": kw.get("is_sensitive", False),
            },
        )
        self.db.commit()
        return cid

    def list_configs(self, tenant_id: str, category: str = None) -> List[Dict]:
        sql = "SELECT * FROM dbp_system_config WHERE tenant_id=:tid"
        params: dict = {"tid": tenant_id}
        if category:
            sql += " AND category=:cat"
            params["cat"] = category
        sql += " ORDER BY created_at DESC"
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    def delete_config(self, tenant_id: str, config_key: str) -> Dict:
        existing = self.get_config(tenant_id, config_key)
        if not existing:
            return None
        self.db.execute(
            text("DELETE FROM dbp_system_config WHERE tenant_id=:tid AND config_key=:ck"),
            {"tid": tenant_id, "ck": config_key},
        )
        self.db.commit()
        return {"deleted": config_key}

    # ---------------------------------------------------------- integration logs
    def log_integration(self, tenant_id: str, integration_type: str,
                        direction: str, status: str, **kw) -> str:
        lid = str(uuid4())
        self.db.execute(
            text("INSERT INTO dbp_integration_logs "
                 "(id,tenant_id,company_id,integration_type,direction,status,"
                 "entity_type,entity_id,payload_summary,error_message,duration_ms,created_at) "
                 "VALUES (:id,:tid,:cid,:itype,:dir,:status,:etype,:eid,:payload,:err,:dur,now())"),
            {
                "id": lid,
                "tid": tenant_id,
                "cid": kw.get("company_id"),
                "itype": integration_type,
                "dir": direction,
                "status": status,
                "etype": kw.get("entity_type"),
                "eid": kw.get("entity_id"),
                "payload": kw.get("payload_summary"),
                "err": kw.get("error_message"),
                "dur": kw.get("duration_ms"),
            },
        )
        self.db.commit()
        return lid

    def list_integration_logs(self, tenant_id: str, company_id: str = None,
                              integration_type: str = None, status: str = None,
                              limit: int = 100) -> List[Dict]:
        sql = "SELECT * FROM dbp_integration_logs WHERE tenant_id=:tid"
        params: dict = {"tid": tenant_id}
        if company_id:
            sql += " AND company_id=:cid"
            params["cid"] = company_id
        if integration_type:
            sql += " AND integration_type=:itype"
            params["itype"] = integration_type
        if status:
            sql += " AND status=:status"
            params["status"] = status
        sql += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    # -------------------------------------------------------------- data imports
    def create_data_import(self, tenant_id: str, company_id: str,
                           import_type: str, **kw) -> str:
        iid = str(uuid4())
        self.db.execute(
            text("INSERT INTO dbp_data_imports "
                 "(id,tenant_id,company_id,import_type,file_name,record_count,"
                 "success_count,error_count,status,errors,started_at,completed_at,"
                 "created_by,created_at) "
                 "VALUES (:id,:tid,:cid,:itype,:fname,:rcount,:scount,:ecount,"
                 ":status,:errors,:started,:completed,:creator,now())"),
            {
                "id": iid,
                "tid": tenant_id,
                "cid": company_id,
                "itype": import_type,
                "fname": kw.get("file_name"),
                "rcount": kw.get("record_count", 0),
                "scount": kw.get("success_count", 0),
                "ecount": kw.get("error_count", 0),
                "status": kw.get("status", "pending"),
                "errors": json.dumps(kw.get("errors")) if kw.get("errors") is not None else None,
                "started": kw.get("started_at"),
                "completed": kw.get("completed_at"),
                "creator": kw.get("created_by"),
            },
        )
        self.db.commit()
        return iid

    def update_data_import(self, import_id: str, tenant_id: str, **kw) -> Dict:
        row = self.db.execute(
            text("SELECT * FROM dbp_data_imports WHERE id=:id AND tenant_id=:tenant_id"),
            {"id": import_id, "tenant_id": tenant_id},
        ).mappings().first()
        if not row:
            return None
        sets = []
        params: dict = {"id": import_id, "tenant_id": tenant_id}
        for field in ("success_count", "error_count", "status", "errors", "completed_at"):
            if field in kw and kw[field] is not None:
                val = json.dumps(kw[field]) if field == "errors" else kw[field]
                sets.append(f"{field}=:{field}")
                params[field] = val
        if sets:
            self.db.execute(text(f"UPDATE dbp_data_imports SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tenant_id"), params)
            self.db.commit()
        updated = self.db.execute(
            text("SELECT * FROM dbp_data_imports WHERE id=:id AND tenant_id=:tenant_id"), {"id": import_id, "tenant_id": tenant_id},
        ).mappings().first()
        return self._serialize(updated)

    def list_data_imports(self, company_id: str, tenant_id: str = None,
                          status: str = None) -> List[Dict]:
        sql = "SELECT * FROM dbp_data_imports WHERE company_id=:cid"
        params: dict = {"cid": company_id}
        if tenant_id:
            sql += " AND tenant_id=:tid"
            params["tid"] = tenant_id
        if status:
            sql += " AND status=:status"
            params["status"] = status
        sql += " ORDER BY created_at DESC"
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    # -------------------------------------------------------------- data exports
    def create_data_export(self, tenant_id: str, company_id: str,
                           export_type: str, record_count: int, **kw) -> str:
        eid = str(uuid4())
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        self.db.execute(
            text("INSERT INTO dbp_data_exports "
                 "(id,tenant_id,company_id,export_type,record_count,file_format,"
                 "status,download_url,expires_at,created_by,created_at) "
                 "VALUES (:id,:tid,:cid,:etype,:rcount,:fformat,"
                 ":status,:url,:expires,:creator,now())"),
            {
                "id": eid,
                "tid": tenant_id,
                "cid": company_id,
                "etype": export_type,
                "rcount": record_count,
                "fformat": kw.get("file_format", "csv"),
                "status": kw.get("status", "completed"),
                "url": kw.get("download_url"),
                "expires": expires,
                "creator": kw.get("created_by"),
            },
        )
        self.db.commit()
        return eid

    def list_data_exports(self, company_id: str, tenant_id: str = None,
                          export_type: str = None) -> List[Dict]:
        sql = "SELECT * FROM dbp_data_exports WHERE company_id=:cid"
        params: dict = {"cid": company_id}
        if tenant_id:
            sql += " AND tenant_id=:tid"
            params["tid"] = tenant_id
        if export_type:
            sql += " AND export_type=:etype"
            params["etype"] = export_type
        sql += " ORDER BY created_at DESC"
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    # ------------------------------------------------------------- system health
    def get_system_health(self) -> Dict:
        now = datetime.now(timezone.utc)
        module_tables = [
            "dbp_companies", "dbp_currencies", "dbp_audit_trail",
            "dbp_employees", "dbp_payments", "dbp_sales_invoices",
        ]
        modules = []
        for tbl in module_tables:
            exists = self.db.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='{tbl}')"
            )).scalar()
            modules.append({"name": tbl, "status": "active" if exists else "inactive"})
        return {
            "status": "healthy",
            "version": "1.0.0",
            "modules": modules,
            "timestamp": now.isoformat(),
        }

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _serialize(row) -> Dict:
        d = dict(row)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
            elif hasattr(v, "isoformat"):
                d[k] = str(v)
        return d
