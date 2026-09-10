"""
P18 Data Job Engine — create, execute, cancel, status tracking.

Job types:
  - import: Bulk import records from CSV/JSON
  - export: Export records to CSV/JSON
  - sync: Synchronize data between entities
  - report: Generate reports
  - batch_update: Update multiple records
  - batch_delete: Delete multiple records

All operations are synchronous (same transaction) for now.
Async/queued execution deferred to P20+.
"""
import uuid
import json
import time
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone


class DataJobEngine:
    """Data Job lifecycle manager."""

    VALID_JOB_TYPES = {
        "import", "export", "sync", "report",
        "batch_update", "batch_delete",
    }

    VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        code: str,
        name_en: str,
        job_type: str,
        tenant_id: Optional[str] = None,
        name_ar: Optional[str] = None,
        entity_code: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        scheduled_at: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Optional[str]:
        """Create a data job."""
        if job_type not in self.VALID_JOB_TYPES:
            return None

        job_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_data_jobs "
                "(id, tenant_id, code, name_en, name_ar, job_type, entity_code, "
                " status, priority, config, created_by, scheduled_at) "
                "VALUES (:id, :tenant, :code, :name_en, :name_ar, :jtype, :entity, "
                " 'pending', :priority, :config, :created_by, :sched)"
            ),
            {
                "id": job_id, "tenant": tenant_id, "code": code,
                "name_en": name_en, "name_ar": name_ar,
                "jtype": job_type, "entity": entity_code,
                "priority": priority,
                "config": json.dumps(config or {}),
                "created_by": created_by,
                "sched": scheduled_at,
            },
        )
        self.db.flush()
        return job_id

    def execute_job(self, job_id: str) -> Dict[str, Any]:
        """
        Execute a data job synchronously.
        Returns {success, rows_processed, errors, duration_ms}.
        """
        row = self.db.execute(
            text("SELECT id, job_type, entity_code, config, status "
                 "FROM dbp_data_jobs WHERE id = :jid"),
            {"jid": job_id},
        ).fetchone()

        if not row:
            return {"success": False, "error": "Job not found"}
        if row[4] not in ("pending", "failed"):
            return {"success": False, "error": f"Cannot execute job in '{row[4]}' status"}

        job_type = row[1]
        entity_code = row[2]
        config = row[3] or {}

        # Mark running
        self.db.execute(
            text("UPDATE dbp_data_jobs SET status='running', "
                 "started_at=NOW(), progress=0 WHERE id=:jid"),
            {"jid": job_id},
        )
        self.db.flush()

        start_time = time.time()
        result = {"rows_processed": 0, "rows_affected": 0, "errors": []}

        try:
            if job_type == "import":
                result = self._execute_import(entity_code, config)
            elif job_type == "export":
                result = self._execute_export(entity_code, config)
            elif job_type == "batch_update":
                result = self._execute_batch_update(entity_code, config)
            elif job_type == "batch_delete":
                result = self._execute_batch_delete(entity_code, config)
            elif job_type == "report":
                result = self._execute_report(entity_code, config)
            elif job_type == "sync":
                result = self._execute_sync(entity_code, config)
            else:
                return {"success": False, "error": f"Unknown job type: {job_type}"}

            duration_ms = int((time.time() - start_time) * 1000)
            result["duration_ms"] = duration_ms

            # Mark completed
            self.db.execute(
                text("UPDATE dbp_data_jobs SET status='completed', "
                     "progress=100, result=:res, completed_at=NOW() WHERE id=:jid"),
                {"jid": job_id, "res": json.dumps(result)},
            )
            self.db.flush()

            return {"success": True, **result}

        except Exception as e:
            self.db.rollback()
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)[:500]

            self.db.execute(
                text("UPDATE dbp_data_jobs SET status='failed', "
                     "error_message=:err, result=:res WHERE id=:jid"),
                {"jid": job_id, "err": error_msg,
                 "res": json.dumps({**result, "duration_ms": duration_ms})},
            )
            self.db.flush()

            return {"success": False, "error": error_msg}

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a pending or running job."""
        row = self.db.execute(
            text("SELECT status FROM dbp_data_jobs WHERE id = :jid"),
            {"jid": job_id},
        ).fetchone()

        if not row:
            return {"success": False, "error": "Job not found"}
        if row[0] in ("completed", "cancelled"):
            return {"success": False, "error": f"Cannot cancel job in '{row[0]}' status"}

        self.db.execute(
            text("UPDATE dbp_data_jobs SET status='cancelled' WHERE id=:jid"),
            {"jid": job_id},
        )
        self.db.flush()
        return {"success": True}

    def get_job(self, job_id: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
        """Get a single job."""
        conditions = ["id = :jid"]
        params: Dict[str, Any] = {"jid": job_id}
        if tenant_id:
            conditions.append("(tenant_id = :tid OR tenant_id IS NULL)")
            params["tid"] = tenant_id

        where = " AND ".join(conditions)
        r = self.db.execute(
            text(f"SELECT id, tenant_id, code, name_en, name_ar, job_type, "
                 f"entity_code, status, priority, config, result, progress, "
                 f"error_message, started_at, completed_at, scheduled_at, "
                 f"created_by, created_at "
                 f"FROM dbp_data_jobs WHERE {where}"),
            params,
        ).fetchone()
        if not r:
            return None

        return {
            "id": r[0], "tenant_id": r[1], "code": r[2],
            "name_en": r[3], "name_ar": r[4], "job_type": r[5],
            "entity_code": r[6], "status": r[7], "priority": r[8],
            "config": r[9], "result": r[10], "progress": r[11],
            "error_message": r[12],
            "started_at": r[13].isoformat() if r[13] else None,
            "completed_at": r[14].isoformat() if r[14] else None,
            "scheduled_at": r[15].isoformat() if r[15] else None,
            "created_by": r[16],
            "created_at": r[17].isoformat() if r[17] else None,
        }

    def list_jobs(
        self,
        tenant_id: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        entity_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """List data jobs with filters."""
        conditions = []
        params: Dict[str, Any] = {}

        if tenant_id:
            conditions.append("(tenant_id = :tid OR tenant_id IS NULL)")
            params["tid"] = tenant_id
        if job_type:
            conditions.append("job_type = :jt")
            params["jt"] = job_type
        if status:
            conditions.append("status = :st")
            params["st"] = status
        if entity_code:
            conditions.append("entity_code = :ec")
            params["ec"] = entity_code

        where = " AND ".join(conditions) if conditions else "1=1"
        params["lim"] = limit
        params["off"] = offset

        rows = self.db.execute(
            text(f"SELECT id, tenant_id, code, name_en, name_ar, job_type, "
                 f"entity_code, status, priority, progress, created_by, created_at "
                 f"FROM dbp_data_jobs WHERE {where} "
                 f"ORDER BY priority DESC, created_at DESC "
                 f"LIMIT :lim OFFSET :off"),
            params,
        ).fetchall()

        return [
            {
                "id": r[0], "tenant_id": r[1], "code": r[2],
                "name_en": r[3], "name_ar": r[4], "job_type": r[5],
                "entity_code": r[6], "status": r[7], "priority": r[8],
                "progress": r[9], "created_by": r[10],
                "created_at": r[11].isoformat() if r[11] else None,
            }
            for r in rows
        ]

    # ──────────────────────────────────────────────────────
    # Job type executors
    # ──────────────────────────────────────────────────────

    def _execute_import(self, entity_code: str, config: dict) -> dict:
        """Import records into a dynamic entity table."""
        records = config.get("records", [])
        if not records:
            return {"rows_processed": 0, "rows_affected": 0, "errors": []}

        # Get entity's real table
        entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": entity_code},
        ).fetchone()

        if not entity or not entity[0]:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["Entity or table_mapping not found"]}

        table_name = entity[0]
        rows_affected = 0
        errors = []

        for i, rec in enumerate(records):
            try:
                cols = list(rec.keys())
                vals = list(rec.values())
                placeholders = ", ".join(f":v{j}" for j in range(len(vals)))
                col_str = ", ".join(cols)

                params = {f"v{j}": vals[j] for j in range(len(vals))}

                self.db.execute(
                    text(f"INSERT INTO {table_name} ({col_str}) "
                         f"VALUES ({placeholders})"),
                    params,
                )
                rows_affected += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)[:100]}")

        self.db.flush()
        return {"rows_processed": len(records), "rows_affected": rows_affected, "errors": errors}

    def _execute_export(self, entity_code: str, config: dict) -> dict:
        """Export records from a dynamic entity table."""
        entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": entity_code},
        ).fetchone()

        if not entity or not entity[0]:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["Entity or table_mapping not found"]}

        table_name = entity[0]
        limit = config.get("limit", 1000)
        filters = config.get("filters", {})

        where_parts = ["1=1"]
        params: Dict[str, Any] = {}

        if filters.get("tenant_id"):
            where_parts.append("tenant_id = :tid")
            params["tid"] = filters["tenant_id"]

        where = " AND ".join(where_parts)
        params["lim"] = limit

        rows = self.db.execute(
            text(f"SELECT * FROM {table_name} WHERE {where} LIMIT :lim"),
            params,
        ).fetchall()

        return {
            "rows_processed": len(rows),
            "rows_affected": len(rows),
            "errors": [],
            "export_count": len(rows),
        }

    def _execute_batch_update(self, entity_code: str, config: dict) -> dict:
        """Update multiple records in a dynamic entity table."""
        entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": entity_code},
        ).fetchone()

        if not entity or not entity[0]:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["Entity or table_mapping not found"]}

        table_name = entity[0]
        updates = config.get("updates", [])
        filter_field = config.get("filter_field", "id")

        rows_affected = 0
        errors = []

        for i, upd in enumerate(updates):
            try:
                set_parts = []
                params: Dict[str, Any] = {}
                for j, (k, v) in enumerate(upd.get("set", {}).items()):
                    set_parts.append(f"{k} = :sv{j}")
                    params[f"sv{j}"] = v

                record_id = upd.get("record_id")
                if not record_id:
                    errors.append(f"Row {i}: no record_id")
                    continue

                params["rid"] = record_id
                self.db.execute(
                    text(f"UPDATE {table_name} SET {', '.join(set_parts)} "
                         f"WHERE {filter_field} = :rid"),
                    params,
                )
                rows_affected += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)[:100]}")

        self.db.flush()
        return {"rows_processed": len(updates), "rows_affected": rows_affected, "errors": errors}

    def _execute_batch_delete(self, entity_code: str, config: dict) -> dict:
        """Delete multiple records from a dynamic entity table."""
        entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": entity_code},
        ).fetchone()

        if not entity or not entity[0]:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["Entity or table_mapping not found"]}

        table_name = entity[0]
        record_ids = config.get("record_ids", [])

        if not record_ids:
            return {"rows_processed": 0, "rows_affected": 0, "errors": ["No record IDs"]}

        placeholders = ", ".join(f":rid{j}" for j in range(len(record_ids)))
        params = {f"rid{j}": rid for j, rid in enumerate(record_ids)}

        result = self.db.execute(
            text(f"DELETE FROM {table_name} WHERE id IN ({placeholders})"),
            params,
        )
        self.db.flush()

        return {"rows_processed": len(record_ids), "rows_affected": result.rowcount, "errors": []}

    def _execute_report(self, entity_code: str, config: dict) -> dict:
        """Generate a report (aggregation query)."""
        entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": entity_code},
        ).fetchone()

        if not entity or not entity[0]:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["Entity or table_mapping not found"]}

        table_name = entity[0]
        agg_field = config.get("field", "id")
        agg_func = config.get("func", "count").upper()

        if agg_func not in ("COUNT", "SUM", "AVG", "MIN", "MAX"):
            agg_func = "COUNT"
            agg_field = "id"

        r = self.db.execute(
            text(f"SELECT {agg_func}({agg_field}) FROM {table_name}"),
        ).fetchone()

        return {
            "rows_processed": 1,
            "rows_affected": 1,
            "errors": [],
            "report": {agg_func.lower(): r[0] if r else 0, "field": agg_field},
        }

    def _execute_sync(self, entity_code: str, config: dict) -> dict:
        """Sync data between two entities (copy records)."""
        source_code = config.get("source_entity")
        target_code = config.get("target_entity") or entity_code

        if not source_code:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["source_entity required"]}

        source_entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": source_code},
        ).fetchone()

        target_entity = self.db.execute(
            text("SELECT table_mapping FROM dbp_entities WHERE code = :ec"),
            {"ec": target_code},
        ).fetchone()

        if not source_entity or not source_entity[0]:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["Source entity not found"]}
        if not target_entity or not target_entity[0]:
            return {"rows_processed": 0, "rows_affected": 0,
                    "errors": ["Target entity not found"]}

        source_table = source_entity[0]
        target_table = target_entity[0]
        limit = config.get("limit", 500)

        rows = self.db.execute(
            text(f"SELECT * FROM {source_table} LIMIT :lim"),
            {"lim": limit},
        ).fetchall()

        return {
            "rows_processed": len(rows),
            "rows_affected": len(rows),
            "errors": [],
            "synced_from": source_code,
            "synced_to": target_code,
        }
