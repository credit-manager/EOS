"""
P39 + P59 Production Ops Engine — backups, scheduled jobs, alert rules,
alert history, deployments, monitoring metrics, SaaS metrics & alerts.
"""
import json
import time
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ProductionOpsEngine:
    def __init__(self, db: Session):
        self.db = db

    # ── BACKUP JOBS ──

    def create_backup_job(self, tenant_id: str, company_id: str | None,
                          backup_type: str, target_tables: list[str] | None = None,
                          created_by: str | None = None) -> str:
        bid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_backup_jobs "
            "(id, tenant_id, company_id, backup_type, target_tables, status, created_by) "
            "VALUES (:id, :t, :co, :bt, CAST(:tt AS JSONB), 'pending', :cb)"
        ), {"id": bid, "t": tenant_id, "co": company_id, "bt": backup_type,
            "tt": json.dumps(target_tables or []), "cb": created_by})
        self.db.flush()
        return bid

    def list_backup_jobs(self, tenant_id: str, backup_type: str | None = None,
                         status: str | None = None, limit: int = 50) -> list[dict]:
        conds, params = ["tenant_id = :t"], {"t": tenant_id, "lim": limit}
        if backup_type:
            conds.append("backup_type = :bt")
            params["bt"] = backup_type
        if status:
            conds.append("status = :st")
            params["st"] = status
        where = " AND ".join(conds)
        rows = self.db.execute(text(
            f"SELECT id, backup_type, status, file_path, file_size_bytes, created_at "
            f"FROM dbp_backup_jobs WHERE {where} ORDER BY created_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "backup_type": r[1], "status": r[2], "file_path": r[3],
                 "file_size_bytes": r[4], "created_at": str(r[5]) if r[5] else None}
                for r in rows]

    def get_backup_job(self, tenant_id: str, backup_id: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, backup_type, status, file_path, file_size_bytes, "
            "checksum, started_at, completed_at, error_message "
            "FROM dbp_backup_jobs WHERE id = :id AND tenant_id = :t"
        ), {"id": backup_id, "t": tenant_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "backup_type": row[1], "status": row[2],
                "file_path": row[3], "file_size_bytes": row[4], "checksum": row[5],
                "started_at": str(row[6]) if row[6] else None,
                "completed_at": str(row[7]) if row[7] else None,
                "error_message": row[8]}

    def update_backup_status(self, tenant_id: str, backup_id: str, status: str,
                             file_path: str | None = None,
                             file_size_bytes: int | None = None,
                             checksum: str | None = None,
                             error_message: str | None = None) -> dict | None:
        row = self.db.execute(text(
            "SELECT id FROM dbp_backup_jobs WHERE id = :id AND tenant_id = :t"
        ), {"id": backup_id, "t": tenant_id}).fetchone()
        if not row:
            return None
        extras = {}
        if status == "running":
            extras["started_at"] = "NOW()"
        elif status in ("completed", "failed"):
            extras["completed_at"] = "NOW()"
        sets = ["status = :st"]
        params = {"id": backup_id, "t": tenant_id, "st": status}
        if file_path:
            sets.append("file_path = :fp")
            params["fp"] = file_path
        if file_size_bytes is not None:
            sets.append("file_size_bytes = :fs")
            params["fs"] = file_size_bytes
        if checksum:
            sets.append("checksum = :ck")
            params["ck"] = checksum
        if error_message:
            sets.append("error_message = :em")
            params["em"] = error_message
        if "started_at" in extras:
            sets.append("started_at = NOW()")
        if "completed_at" in extras:
            sets.append("completed_at = NOW()")
        self.db.execute(text(
            f"UPDATE dbp_backup_jobs SET {', '.join(sets)} WHERE id = :id AND tenant_id = :t"
        ), params)
        self.db.flush()
        return self.get_backup_job(tenant_id, backup_id)

    # ── SCHEDULED JOBS ──

    def create_scheduled_job(self, tenant_id: str, job_name: str, job_type: str,
                             cron_expression: str | None = None,
                             interval_seconds: int | None = None,
                             payload: dict | None = None) -> str:
        jid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_scheduled_jobs "
            "(id, tenant_id, job_name, job_type, cron_expression, interval_seconds, "
            "payload, is_active, last_run_at, next_run_at, run_count, last_status) "
            "VALUES (:id, :t, :jn, :jt, :ce, :iv, CAST(:pl AS JSONB), true, NULL, NULL, 0, NULL)"
        ), {"id": jid, "t": tenant_id, "jn": job_name, "jt": job_type,
            "ce": cron_expression, "iv": interval_seconds,
            "pl": json.dumps(payload or {})})
        self.db.flush()
        return jid

    def list_scheduled_jobs(self, tenant_id: str) -> list[dict]:
        rows = self.db.execute(text(
            "SELECT id, job_name, job_type, cron_expression, interval_seconds, "
            "is_active, last_run_at, run_count FROM dbp_scheduled_jobs "
            "WHERE tenant_id = :t ORDER BY job_name"
        ), {"t": tenant_id}).fetchall()
        return [{"id": r[0], "job_name": r[1], "job_type": r[2],
                 "cron_expression": r[3], "interval_seconds": r[4],
                 "is_active": r[5], "last_run_at": str(r[6]) if r[6] else None,
                 "run_count": r[7]} for r in rows]

    def get_scheduled_job(self, tenant_id: str, job_id: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, job_name, job_type, cron_expression, interval_seconds, "
            "payload, is_active, last_run_at, run_count, error_count "
            "FROM dbp_scheduled_jobs WHERE id = :id AND tenant_id = :t"
        ), {"id": job_id, "t": tenant_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "job_name": row[1], "job_type": row[2],
                "cron_expression": row[3], "interval_seconds": row[4],
                "payload": row[5] if isinstance(row[5], dict) else {},
                "is_active": row[6],
                "last_run_at": str(row[7]) if row[7] else None,
                "run_count": row[8], "error_count": row[9]}

    def update_scheduled_job(self, tenant_id: str, job_id: str,
                             is_active: bool | None = None,
                             cron_expression: str | None = None,
                             interval_seconds: int | None = None,
                             payload: dict | None = None) -> dict:
        sets, params = [], {"id": job_id, "t": tenant_id}
        if is_active is not None:
            sets.append("is_active = :ia")
            params["ia"] = is_active
        if cron_expression:
            sets.append("cron_expression = :ce")
            params["ce"] = cron_expression
        if interval_seconds is not None:
            sets.append("interval_seconds = :iv")
            params["iv"] = interval_seconds
        if payload:
            sets.append("payload = CAST(:pl AS JSONB)")
            params["pl"] = json.dumps(payload)
        if sets:
            self.db.execute(text(
                f"UPDATE dbp_scheduled_jobs SET {', '.join(sets)} "
                f"WHERE id = :id AND tenant_id = :t"
            ), params)
            self.db.flush()
        return self.get_scheduled_job(tenant_id, job_id)

    def delete_scheduled_job(self, tenant_id: str, job_id: str) -> bool:
        row = self.db.execute(text(
            "SELECT id FROM dbp_scheduled_jobs WHERE id = :id AND tenant_id = :t"
        ), {"id": job_id, "t": tenant_id}).fetchone()
        if not row:
            return False
        self.db.execute(text(
            "DELETE FROM dbp_scheduled_jobs WHERE id = :id AND tenant_id = :t"
        ), {"id": job_id, "t": tenant_id})
        self.db.flush()
        return True

    # ── ALERT RULES ──

    def create_alert_rule(self, tenant_id: str, rule_name: str,
                          metric_name: str, condition_op: str,
                          threshold_value: float,
                          company_id: str | None = None,
                          severity: str = "warning",
                          notification_channels: list[str] | None = None,
                          cooldown_minutes: int = 5) -> str:
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_alert_rules "
            "(id, tenant_id, company_id, rule_name, metric_name, condition_op, "
            "threshold_value, severity, notification_channels, cooldown_minutes, "
            "is_active, last_triggered_at) "
            "VALUES (:id, :t, :co, :rn, :mn, :co2, :tv, :sv, CAST(:nc AS JSONB), "
            ":cm, true, NULL)"
        ), {"id": rid, "t": tenant_id, "co": company_id, "rn": rule_name,
            "mn": metric_name, "co2": condition_op, "tv": threshold_value,
            "sv": severity, "nc": json.dumps(notification_channels or []), "cm": cooldown_minutes})
        self.db.flush()
        return rid

    def list_alert_rules(self, tenant_id: str) -> list[dict]:
        rows = self.db.execute(text(
            "SELECT id, rule_name, metric_name, condition_op, threshold_value, "
            "severity, is_active FROM dbp_alert_rules "
            "WHERE tenant_id = :t ORDER BY rule_name"
        ), {"t": tenant_id}).fetchall()
        return [{"id": r[0], "rule_name": r[1], "metric_name": r[2],
                 "condition_op": r[3], "threshold_value": float(r[4]),
                 "severity": r[5], "is_active": r[6]}
                for r in rows]

    def get_alert_rule(self, tenant_id: str, rule_id: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, rule_name, metric_name, condition_op, threshold_value, "
            "severity, notification_channels, cooldown_minutes, is_active, "
            "last_triggered_at "
            "FROM dbp_alert_rules WHERE id = :id AND tenant_id = :t"
        ), {"id": rule_id, "t": tenant_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "rule_name": row[1], "metric_name": row[2],
                "condition_op": row[3], "threshold_value": float(row[4]),
                "severity": row[5], "notification_channels": row[6] if isinstance(row[6], list) else [],
                "cooldown_minutes": row[7], "is_active": row[8],
                "last_triggered_at": str(row[9]) if row[9] else None}

    def update_alert_rule(self, tenant_id: str, rule_id: str,
                          is_active: bool | None = None,
                          threshold_value: float | None = None,
                          severity: str | None = None) -> dict:
        sets, params = [], {"id": rule_id, "t": tenant_id}
        if is_active is not None:
            sets.append("is_active = :ia")
            params["ia"] = is_active
        if threshold_value is not None:
            sets.append("threshold_value = :tv")
            params["tv"] = threshold_value
        if severity:
            sets.append("severity = :sv")
            params["sv"] = severity
        if sets:
            self.db.execute(text(
                f"UPDATE dbp_alert_rules SET {', '.join(sets)} "
                f"WHERE id = :id AND tenant_id = :t"
            ), params)
            self.db.flush()
        return self.get_alert_rule(tenant_id, rule_id)

    # ── ALERT HISTORY ──

    def trigger_alert(self, tenant_id: str, rule_id: str, rule_name: str,
                      metric_name: str, actual_value: float,
                      threshold_value: float, severity: str = "warning",
                      message: str | None = None) -> str:
        aid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_alert_history "
            "(id, tenant_id, rule_id, rule_name, metric_name, actual_value, "
            "threshold_value, severity, message, status, triggered_at) "
            "VALUES (:id, :t, :ri, :rn, :mn, :av, :tv, :sv, :msg, 'active', NOW())"
        ), {"id": aid, "t": tenant_id, "ri": rule_id, "rn": rule_name,
            "mn": metric_name, "av": actual_value, "tv": threshold_value,
            "sv": severity, "msg": message or f"{metric_name} exceeded threshold"})
        self.db.execute(text(
            "UPDATE dbp_alert_rules SET last_triggered_at = NOW() WHERE id = :id"
        ), {"id": rule_id})
        self.db.flush()
        return aid

    def list_alert_history(self, tenant_id: str, status: str | None = None,
                           severity: str | None = None, limit: int = 50) -> list[dict]:
        conds, params = ["tenant_id = :t"], {"t": tenant_id, "lim": limit}
        if status:
            conds.append("status = :st")
            params["st"] = status
        if severity:
            conds.append("severity = :sv")
            params["sv"] = severity
        where = " AND ".join(conds)
        rows = self.db.execute(text(
            f"SELECT id, rule_name, metric_name, actual_value, threshold_value, "
            f"severity, message, status, triggered_at, acknowledged_at, resolved_at "
            f"FROM dbp_alert_history WHERE {where} ORDER BY triggered_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "rule_name": r[1], "metric_name": r[2],
                 "actual_value": float(r[3]) if r[3] else None,
                 "threshold_value": float(r[4]) if r[4] else None,
                 "severity": r[5], "message": r[6], "status": r[7],
                 "triggered_at": str(r[8]) if r[8] else None,
                 "acknowledged_at": str(r[9]) if r[9] else None,
                 "resolved_at": str(r[10]) if r[10] else None} for r in rows]

    def acknowledge_alert(self, tenant_id: str, alert_id: str,
                          acknowledged_by: str = "system") -> dict:
        row = self.db.execute(text(
            "SELECT id FROM dbp_alert_history WHERE id = :id AND tenant_id = :t"
        ), {"id": alert_id, "t": tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Alert not found"}
        self.db.execute(text(
            "UPDATE dbp_alert_history SET status = 'acknowledged', "
            "acknowledged_by = :ab, acknowledged_at = NOW() WHERE id = :id"
        ), {"id": alert_id, "ab": acknowledged_by})
        self.db.flush()
        return {"success": True}

    def resolve_alert(self, tenant_id: str, alert_id: str) -> dict:
        row = self.db.execute(text(
            "SELECT id FROM dbp_alert_history WHERE id = :id AND tenant_id = :t"
        ), {"id": alert_id, "t": tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Alert not found"}
        self.db.execute(text(
            "UPDATE dbp_alert_history SET status = 'resolved', "
            "resolved_at = NOW() WHERE id = :id"
        ), {"id": alert_id})
        self.db.flush()
        return {"success": True}

    # ── DEPLOYMENTS ──

    def create_deployment(self, tenant_id: str, version: str, environment: str,
                          deployed_by: str | None = None,
                          commit_sha: str | None = None,
                          release_notes: str | None = None) -> str:
        did = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_deployments "
            "(id, tenant_id, version, environment, deployed_by, commit_sha, "
            "release_notes, status, started_at) "
            "VALUES (:id, :t, :v, :env, :db, :cs, :rn, 'deploying', NOW())"
        ), {"id": did, "t": tenant_id, "v": version, "env": environment,
            "db": deployed_by, "cs": commit_sha, "rn": release_notes})
        self.db.flush()
        return did

    def list_deployments(self, tenant_id: str, environment: str | None = None,
                         status: str | None = None, limit: int = 20) -> list[dict]:
        conds, params = ["tenant_id = :t"], {"t": tenant_id, "lim": limit}
        if environment:
            conds.append("environment = :env")
            params["env"] = environment
        if status:
            conds.append("status = :st")
            params["st"] = status
        where = " AND ".join(conds)
        rows = self.db.execute(text(
            f"SELECT id, version, environment, status, deployed_by, started_at "
            f"FROM dbp_deployments WHERE {where} ORDER BY started_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "version": r[1], "environment": r[2],
                 "status": r[3], "deployed_by": r[4],
                 "deployed_at": str(r[5]) if r[5] else None} for r in rows]

    def get_deployment(self, tenant_id: str, deployment_id: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, version, environment, status, deployed_by, commit_sha, "
            "release_notes, started_at, completed_at, rollback_reason "
            "FROM dbp_deployments WHERE id = :id AND tenant_id = :t"
        ), {"id": deployment_id, "t": tenant_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "version": row[1], "environment": row[2],
                "status": row[3], "deployed_by": row[4], "commit_sha": row[5],
                "release_notes": row[6],
                "deployed_at": str(row[7]) if row[7] else None,
                "completed_at": str(row[8]) if row[8] else None,
                "rollback_reason": row[9]}

    def update_deployment_status(self, tenant_id: str, deployment_id: str,
                                 status: str,
                                 rollback_reason: str | None = None) -> dict:
        row = self.db.execute(text(
            "SELECT id FROM dbp_deployments WHERE id = :id AND tenant_id = :t"
        ), {"id": deployment_id, "t": tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Deployment not found"}
        sets = ["status = :st"]
        params = {"id": deployment_id, "st": status}
        if status in ("completed", "failed", "rolled_back"):
            sets.append("completed_at = NOW()")
        if rollback_reason:
            sets.append("rollback_reason = :rr")
            params["rr"] = rollback_reason
        self.db.execute(text(
            f"UPDATE dbp_deployments SET {', '.join(sets)} WHERE id = :id"
        ), params)
        self.db.flush()
        return self.get_deployment(tenant_id, deployment_id)

    # ── MONITORING METRICS (P39 original) ──

    def record_metric(self, tenant_id: str, metric_name: str,
                      metric_value: float, unit: str | None = None,
                      tags: dict | None = None, source: str | None = None) -> str:
        mid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_monitoring_metrics "
            "(id, tenant_id, metric_name, metric_value, unit, tags, source, recorded_at) "
            "VALUES (:id, :t, :mn, :mv, :u, CAST(:tg AS JSONB), :src, NOW())"
        ), {"id": mid, "t": tenant_id, "mn": metric_name, "mv": metric_value,
            "u": unit, "tg": json.dumps(tags or {}), "src": source})
        self.db.flush()
        return mid

    def list_metrics(self, tenant_id: str, metric_name: str | None = None,
                     source: str | None = None, limit: int = 100) -> list[dict]:
        conds, params = ["tenant_id = :t"], {"t": tenant_id, "lim": limit}
        if metric_name:
            conds.append("metric_name = :mn")
            params["mn"] = metric_name
        if source:
            conds.append("source = :src")
            params["src"] = source
        where = " AND ".join(conds)
        rows = self.db.execute(text(
            f"SELECT id, metric_name, metric_value, unit, tags, source, recorded_at "
            f"FROM dbp_monitoring_metrics WHERE {where} ORDER BY recorded_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "metric_name": r[1], "metric_value": float(r[2]),
                 "unit": r[3], "tags": r[4] if isinstance(r[4], dict) else {},
                 "source": r[5], "recorded_at": str(r[6]) if r[6] else None}
                for r in rows]

    def get_latest_metric(self, tenant_id: str, metric_name: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, metric_name, metric_value, unit, tags, source, recorded_at "
            "FROM dbp_monitoring_metrics WHERE tenant_id = :t AND metric_name = :mn "
            "ORDER BY recorded_at DESC LIMIT 1"
        ), {"t": tenant_id, "mn": metric_name}).fetchone()
        if not row:
            return None
        return {"id": row[0], "metric_name": row[1], "metric_value": float(row[2]),
                "unit": row[3], "tags": row[4] if isinstance(row[4], dict) else {},
                "source": row[5], "recorded_at": str(row[6]) if row[6] else None}

    # ── SAAS METRICS (P59) ──

    def record_saas_metric(self, tenant_id: str, metric_name: str,
                           metric_value: float, labels: dict | None = None) -> str:
        mid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_saas_metrics (id, tenant_id, metric_name, metric_value, labels) "
            "VALUES (:id, :t, :n, :v, CAST(:l AS JSONB))"
        ), {"id": mid, "t": tenant_id, "n": metric_name, "v": metric_value,
            "l": json.dumps(labels or {})})
        self.db.flush()
        return mid

    def get_saas_metrics(self, tenant_id: str, metric_name: str | None = None,
                         limit: int = 100) -> list[dict]:
        conds, params = ["tenant_id = :t"], {"t": tenant_id, "lim": limit}
        if metric_name:
            conds.append("metric_name = :n")
            params["n"] = metric_name
        where = " AND ".join(conds)
        rows = self.db.execute(text(
            f"SELECT id, metric_name, metric_value, labels, recorded_at "
            f"FROM dbp_saas_metrics WHERE {where} ORDER BY recorded_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "metric_name": r[1], "metric_value": float(r[2]),
                 "labels": r[3] if isinstance(r[3], dict) else {},
                 "recorded_at": str(r[4]) if r[4] else None} for r in rows]

    # ── SAAS ALERTS (P59) ──

    def create_saas_alert(self, tenant_id: str, alert_type: str,
                          severity: str, message: str) -> str:
        aid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_saas_alerts (id, tenant_id, alert_type, severity, message) "
            "VALUES (:id, :t, :tp, :sv, :msg)"
        ), {"id": aid, "t": tenant_id, "tp": alert_type, "sv": severity, "msg": message})
        self.db.flush()
        return aid

    def resolve_saas_alert(self, tenant_id: str, alert_id: str) -> bool:
        row = self.db.execute(text(
            "SELECT id FROM dbp_saas_alerts WHERE id = :id AND tenant_id = :t AND status = 'active'"
        ), {"id": alert_id, "t": tenant_id}).fetchone()
        if not row:
            return False
        self.db.execute(text(
            "UPDATE dbp_saas_alerts SET status='resolved', resolved_at=NOW() WHERE id = :id"
        ), {"id": alert_id})
        self.db.flush()
        return True

    def list_saas_alerts(self, tenant_id: str, status: str | None = None,
                         limit: int = 50) -> list[dict]:
        conds, params = ["tenant_id = :t"], {"t": tenant_id, "lim": limit}
        if status:
            conds.append("status = :st")
            params["st"] = status
        where = " AND ".join(conds)
        rows = self.db.execute(text(
            f"SELECT id, alert_type, severity, message, status, created_at "
            f"FROM dbp_saas_alerts WHERE {where} ORDER BY created_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "alert_type": r[1], "severity": r[2],
                 "message": r[3], "status": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    def health_check(self, tenant_id: str) -> dict[str, Any]:
        db_ok = False
        try:
            self.db.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            pass
        alerts_active = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_saas_alerts WHERE tenant_id = :t AND status = 'active'"
        ), {"t": tenant_id}).fetchone()[0]
        return {"database": "ok" if db_ok else "error",
                "active_alerts": int(alerts_active),
                "platform": "ok", "timestamp": time.time()}
