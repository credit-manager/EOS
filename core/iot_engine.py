"""
P48 IoT & Device Management Engine
"""
import uuid, json
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class IoTEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------- devices
    def create_device(self, tenant_id, device_name, device_type, device_model=None,
                      serial_number=None, firmware_version=None, location=None,
                      metadata=None):
        did = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_iot_devices "
            "(id, tenant_id, device_name, device_type, device_model, serial_number, "
            "firmware_version, status, location, metadata, created_at) "
            "VALUES (:id,:tid,:dn,:dt,:dm,:sn,:fv,'online',:lo,:md,NOW())"
        ), {"id": did, "tid": tenant_id, "dn": device_name, "dt": device_type,
            "dm": device_model, "sn": serial_number, "fv": firmware_version,
            "lo": location, "md": json.dumps(metadata) if metadata else None})
        return did

    def list_devices(self, tenant_id, device_type=None, status=None):
        q = "SELECT id, device_name, device_type, device_model, serial_number, firmware_version, status, location, last_heartbeat_at, created_at FROM dbp_iot_devices WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if device_type:
            q += " AND device_type=:dt"
            params["dt"] = device_type
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "device_name": r[1], "device_type": r[2],
                 "device_model": r[3], "serial_number": r[4],
                 "firmware_version": r[5], "status": r[6],
                 "location": r[7],
                 "last_heartbeat_at": str(r[8]) if r[8] else None,
                 "created_at": str(r[9]) if r[9] else None} for r in rows]

    def get_device(self, tenant_id, device_id):
        r = self.db.execute(text(
            "SELECT id, device_name, device_type, device_model, serial_number, firmware_version, status, location, metadata, last_heartbeat_at, created_at "
            "FROM dbp_iot_devices WHERE id=:id AND tenant_id=:tid"
        ), {"id": device_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "device_name": r[1], "device_type": r[2],
                "device_model": r[3], "serial_number": r[4],
                "firmware_version": r[5], "status": r[6],
                "location": r[7], "metadata": r[8],
                "last_heartbeat_at": str(r[9]) if r[9] else None,
                "created_at": str(r[10]) if r[10] else None}

    def update_device(self, tenant_id, device_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": device_id, "tid": tenant_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_iot_devices SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": device_id, "updated": True}

    def heartbeat(self, tenant_id, device_id):
        self.db.execute(text(
            "UPDATE dbp_iot_devices SET last_heartbeat_at=NOW(), status='online' WHERE id=:id AND tenant_id=:tid"
        ), {"id": device_id, "tid": tenant_id})
        return {"id": device_id, "status": "online"}

    # -------------------------------------------------- telemetry
    def record_telemetry(self, tenant_id, device_id, metric_name, metric_value,
                         unit=None, quality_score=1.0):
        tid2 = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_iot_telemetry "
            "(id, tenant_id, device_id, metric_name, metric_value, unit, quality_score, recorded_at) "
            "VALUES (:id,:ti,:di,:mn,:mv,:u,:qs,NOW())"
        ), {"id": tid2, "ti": tenant_id, "di": device_id,
            "mn": metric_name, "mv": metric_value, "u": unit,
            "qs": quality_score})
        return tid2

    def get_telemetry(self, tenant_id, device_id=None, metric_name=None, limit=100):
        q = "SELECT id, device_id, metric_name, metric_value, unit, quality_score, recorded_at FROM dbp_iot_telemetry WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if device_id:
            q += " AND device_id=:di"
            params["di"] = device_id
        if metric_name:
            q += " AND metric_name=:mn"
            params["mn"] = metric_name
        q += " ORDER BY recorded_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "device_id": r[1], "metric_name": r[2],
                 "metric_value": r[3], "unit": r[4],
                 "quality_score": r[5],
                 "recorded_at": str(r[6]) if r[6] else None} for r in rows]

    # -------------------------------------------------- alerts
    def create_alert(self, tenant_id, device_id, alert_type, severity, message=None):
        aid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_iot_alerts "
            "(id, tenant_id, device_id, alert_type, severity, message, created_at) "
            "VALUES (:id,:tid,:di,:at,:sv,:me,NOW())"
        ), {"id": aid, "tid": tenant_id, "di": device_id,
            "at": alert_type, "sv": severity, "me": message})
        return aid

    def acknowledge_alert(self, tenant_id, alert_id, acknowledged_by):
        self.db.execute(text(
            "UPDATE dbp_iot_alerts SET is_acknowledged=true, acknowledged_by=:ab, acknowledged_at=NOW() "
            "WHERE id=:id AND tenant_id=:tid"
        ), {"id": alert_id, "tid": tenant_id, "ab": acknowledged_by})
        return {"id": alert_id, "acknowledged": True}

    def list_alerts(self, tenant_id, device_id=None, is_acknowledged=None, severity=None):
        q = "SELECT id, device_id, alert_type, severity, message, is_acknowledged, created_at FROM dbp_iot_alerts WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if device_id:
            q += " AND device_id=:di"
            params["di"] = device_id
        if is_acknowledged is not None:
            q += " AND is_acknowledged=:ia"
            params["ia"] = is_acknowledged
        if severity:
            q += " AND severity=:sv"
            params["sv"] = severity
        q += " ORDER BY created_at DESC LIMIT 100"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "device_id": r[1], "alert_type": r[2],
                 "severity": r[3], "message": r[4],
                 "is_acknowledged": r[5],
                 "created_at": str(r[6]) if r[6] else None} for r in rows]

    # -------------------------------------------------- rules
    def create_rule(self, tenant_id, rule_name, condition_config, action_config,
                    device_type=None):
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_iot_rules "
            "(id, tenant_id, rule_name, device_type, condition_config, action_config, created_at) "
            "VALUES (:id,:tid,:rn,:dt,:cc,:ac,NOW())"
        ), {"id": rid, "tid": tenant_id, "rn": rule_name,
            "dt": device_type,
            "cc": json.dumps(condition_config),
            "ac": json.dumps(action_config)})
        return rid

    def list_rules(self, tenant_id, device_type=None, is_active=None):
        q = "SELECT id, rule_name, device_type, is_active, created_at FROM dbp_iot_rules WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if device_type:
            q += " AND device_type=:dt"
            params["dt"] = device_type
        if is_active is not None:
            q += " AND is_active=:ia"
            params["ia"] = is_active
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "rule_name": r[1], "device_type": r[2],
                 "is_active": r[3],
                 "created_at": str(r[4]) if r[4] else None} for r in rows]

    def update_rule(self, tenant_id, rule_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": rule_id, "tid": tenant_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_iot_rules SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": rule_id, "updated": True}

    # -------------------------------------------------- firmware
    def create_firmware(self, tenant_id, device_type, version, changelog=None,
                        download_url=None, file_size_bytes=None):
        fid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_iot_firmware "
            "(id, tenant_id, device_type, version, changelog, download_url, file_size_bytes, created_at) "
            "VALUES (:id,:tid,:dt,:ve,:cl,:du,:fs,NOW())"
        ), {"id": fid, "tid": tenant_id, "dt": device_type,
            "ve": version, "cl": changelog, "du": download_url,
            "fs": file_size_bytes})
        return fid

    def list_firmware(self, tenant_id, device_type=None):
        q = "SELECT id, device_type, version, changelog, download_url, file_size_bytes, is_active, created_at FROM dbp_iot_firmware WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if device_type:
            q += " AND device_type=:dt"
            params["dt"] = device_type
        q += " ORDER BY created_at DESC"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "device_type": r[1], "version": r[2],
                 "changelog": r[3], "download_url": r[4],
                 "file_size_bytes": r[5], "is_active": r[6],
                 "created_at": str(r[7]) if r[7] else None} for r in rows]
