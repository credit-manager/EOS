"""
P40 Production Validation Engine
"""
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class ProductionValidationEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------- validation rules
    def create_validation_rule(self, tenant_id, rule_name, rule_type, check_command,
                               expected_value=None, severity="error"):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_validation_rules "
            "(id, tenant_id, rule_name, rule_type, check_command, expected_value, severity, created_at, updated_at) "
            "VALUES (:id,:tid,:rn,:rt,:cc,:ev,:se,NOW(),NOW())"
        ), {"id": eid, "tid": tenant_id, "rn": rule_name, "rt": rule_type,
            "cc": check_command, "ev": expected_value, "se": severity})
        return eid

    def list_validation_rules(self, tenant_id, rule_type=None, is_active=None, limit=50):
        q = "SELECT id, rule_name, rule_type, check_command, expected_value, severity, is_active, last_run_at, last_status, created_at FROM dbp_validation_rules WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if rule_type:
            q += " AND rule_type=:rt"
            params["rt"] = rule_type
        if is_active is not None:
            q += " AND is_active=:ia"
            params["ia"] = is_active
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "rule_name": r[1], "rule_type": r[2],
                 "check_command": r[3], "expected_value": r[4],
                 "severity": r[5], "is_active": r[6],
                 "last_run_at": str(r[7]) if r[7] else None,
                 "last_status": r[8],
                 "created_at": str(r[9]) if r[9] else None} for r in rows]

    def get_validation_rule(self, tenant_id, rule_id):
        r = self.db.execute(text(
            "SELECT id, rule_name, rule_type, check_command, expected_value, severity, "
            "is_active, last_run_at, last_status, created_at "
            "FROM dbp_validation_rules WHERE id=:id AND tenant_id=:tid"
        ), {"id": rule_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "rule_name": r[1], "rule_type": r[2],
                "check_command": r[3], "expected_value": r[4],
                "severity": r[5], "is_active": r[6],
                "last_run_at": str(r[7]) if r[7] else None,
                "last_status": r[8], "created_at": str(r[9]) if r[9] else None}

    def update_validation_rule(self, tenant_id, rule_id, is_active=None, severity=None,
                               check_command=None):
        sets = ["updated_at=NOW()"]
        params: Dict[str, Any] = {"id": rule_id, "tid": tenant_id}
        if is_active is not None:
            sets.append("is_active=:ia")
            params["ia"] = is_active
        if severity is not None:
            sets.append("severity=:se")
            params["se"] = severity
        if check_command is not None:
            sets.append("check_command=:cc")
            params["cc"] = check_command
        self.db.execute(text(
            f"UPDATE dbp_validation_rules SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": rule_id, "updated": True}

    # ------------------------------------------------------ validation results
    def record_validation_result(self, tenant_id, check_type, status, rule_id=None,
                                 rule_name=None, actual_value=None, expected_value=None,
                                 message=None, execution_time_ms=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_validation_results "
            "(id, tenant_id, rule_id, rule_name, check_type, status, actual_value, expected_value, message, execution_time_ms, validated_at) "
            "VALUES (:id,:tid,:rid,:rn,:ct,:st,:av,:ev,:msg,:etm,NOW())"
        ), {"id": eid, "tid": tenant_id, "rid": rule_id, "rn": rule_name,
            "ct": check_type, "st": status, "av": actual_value,
            "ev": expected_value, "msg": message, "etm": execution_time_ms})
        if rule_id:
            self.db.execute(text(
                "UPDATE dbp_validation_rules SET last_run_at=NOW(), last_status=:st WHERE id=:id"
            ), {"st": status, "id": rule_id})
        return eid

    def list_validation_results(self, tenant_id, check_type=None, status=None, limit=50):
        q = "SELECT id, rule_id, rule_name, check_type, status, actual_value, expected_value, message, execution_time_ms, validated_at FROM dbp_validation_results WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if check_type:
            q += " AND check_type=:ct"
            params["ct"] = check_type
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY validated_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "rule_id": r[1], "rule_name": r[2],
                 "check_type": r[3], "status": r[4],
                 "actual_value": r[5], "expected_value": r[6],
                 "message": r[7], "execution_time_ms": r[8],
                 "validated_at": str(r[9]) if r[9] else None} for r in rows]

    # ----------------------------------------------------------- health checks
    def create_health_check(self, tenant_id, check_name, check_type, target=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_health_checks "
            "(id, tenant_id, check_name, check_type, target, created_at) "
            "VALUES (:id,:tid,:cn,:ct,:tg,NOW())"
        ), {"id": eid, "tid": tenant_id, "cn": check_name, "ct": check_type, "tg": target})
        return eid

    def update_health_check(self, tenant_id, check_id, status, response_time_ms=None,
                            message=None):
        self.db.execute(text(
            "UPDATE dbp_health_checks SET status=:st, response_time_ms=:rtm, message=:msg, last_run_at=NOW() "
            "WHERE id=:id AND tenant_id=:tid"
        ), {"st": status, "rtm": response_time_ms, "msg": message, "id": check_id, "tid": tenant_id})
        return {"id": check_id, "status": status}

    def list_health_checks(self, tenant_id, check_type=None, status=None, limit=50):
        q = "SELECT id, check_name, check_type, target, status, response_time_ms, message, last_run_at, is_active, created_at FROM dbp_health_checks WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if check_type:
            q += " AND check_type=:ct"
            params["ct"] = check_type
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "check_name": r[1], "check_type": r[2],
                 "target": r[3], "status": r[4], "response_time_ms": r[5],
                 "message": r[6], "last_run_at": str(r[7]) if r[7] else None,
                 "is_active": r[8], "created_at": str(r[9]) if r[9] else None} for r in rows]

    def get_health_check(self, tenant_id, check_id):
        r = self.db.execute(text(
            "SELECT id, check_name, check_type, target, status, response_time_ms, message, last_run_at, is_active, created_at "
            "FROM dbp_health_checks WHERE id=:id AND tenant_id=:tid"
        ), {"id": check_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "check_name": r[1], "check_type": r[2],
                "target": r[3], "status": r[4], "response_time_ms": r[5],
                "message": r[6], "last_run_at": str(r[7]) if r[7] else None,
                "is_active": r[8], "created_at": str(r[9]) if r[9] else None}

    # -------------------------------------------------------- ssl certificates
    def register_ssl_certificate(self, tenant_id, domain, issuer=None, serial_number=None,
                                 not_before=None, not_after=None, auto_renew=True):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_ssl_certificates "
            "(id, tenant_id, domain, issuer, serial_number, not_before, not_after, auto_renew, created_at, updated_at) "
            "VALUES (:id,:tid,:do,:is,:sn,:nb,:na,:ar,NOW(),NOW())"
        ), {"id": eid, "tid": tenant_id, "do": domain, "is": issuer,
            "sn": serial_number, "nb": not_before, "na": not_after, "ar": auto_renew})
        return eid

    def list_ssl_certificates(self, tenant_id, domain=None, status=None, limit=50):
        q = "SELECT id, domain, issuer, serial_number, not_before, not_after, status, auto_renew, created_at FROM dbp_ssl_certificates WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if domain:
            q += " AND domain=:do"
            params["do"] = domain
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY not_after ASC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "domain": r[1], "issuer": r[2],
                 "serial_number": r[3],
                 "not_before": str(r[4]) if r[4] else None,
                 "not_after": str(r[5]) if r[5] else None,
                 "status": r[6], "auto_renew": r[7],
                 "created_at": str(r[8]) if r[8] else None} for r in rows]

    def get_ssl_certificate(self, tenant_id, cert_id):
        r = self.db.execute(text(
            "SELECT id, domain, issuer, serial_number, not_before, not_after, status, auto_renew, created_at "
            "FROM dbp_ssl_certificates WHERE id=:id AND tenant_id=:tid"
        ), {"id": cert_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "domain": r[1], "issuer": r[2],
                "serial_number": r[3],
                "not_before": str(r[4]) if r[4] else None,
                "not_after": str(r[5]) if r[5] else None,
                "status": r[6], "auto_renew": r[7],
                "created_at": str(r[8]) if r[8] else None}

    def update_ssl_certificate(self, tenant_id, cert_id, status=None, not_after=None):
        sets = ["updated_at=NOW()"]
        params: Dict[str, Any] = {"id": cert_id, "tid": tenant_id}
        if status is not None:
            sets.append("status=:st")
            params["st"] = status
        if not_after is not None:
            sets.append("not_after=:na")
            params["na"] = not_after
        self.db.execute(text(
            f"UPDATE dbp_ssl_certificates SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": cert_id, "updated": True}

    # -------------------------------------------------- environment configs
    def set_environment_config(self, tenant_id, environment, config_key, config_value,
                               is_sensitive=False, description=None):
        existing = self.db.execute(text(
            "SELECT id FROM dbp_environment_configs WHERE tenant_id=:tid AND environment=:env AND config_key=:ck"
        ), {"tid": tenant_id, "env": environment, "ck": config_key}).fetchone()
        if existing:
            self.db.execute(text(
                "UPDATE dbp_environment_configs SET config_value=:cv, is_sensitive=:is2, "
                "description=:desc, updated_at=NOW() WHERE id=:id"
            ), {"cv": config_value, "is2": is_sensitive, "desc": description, "id": existing[0]})
            return existing[0]
        else:
            eid = str(uuid.uuid4())
            self.db.execute(text(
                "INSERT INTO dbp_environment_configs "
                "(id, tenant_id, environment, config_key, config_value, is_sensitive, description, created_at, updated_at) "
                "VALUES (:id,:tid,:env,:ck,:cv,:is2,:desc,NOW(),NOW())"
            ), {"id": eid, "tid": tenant_id, "env": environment, "ck": config_key,
                "cv": config_value, "is2": is_sensitive, "desc": description})
            return eid

    def list_environment_configs(self, tenant_id, environment=None, limit=50):
        q = "SELECT id, environment, config_key, config_value, is_sensitive, description, created_at, updated_at FROM dbp_environment_configs WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if environment:
            q += " AND environment=:env"
            params["env"] = environment
        q += " ORDER BY environment, config_key LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "environment": r[1], "config_key": r[2],
                 "config_value": r[3], "is_sensitive": r[4],
                 "description": r[5],
                 "created_at": str(r[6]) if r[6] else None,
                 "updated_at": str(r[7]) if r[7] else None} for r in rows]

    def delete_environment_config(self, tenant_id, config_id):
        r = self.db.execute(text(
            "DELETE FROM dbp_environment_configs WHERE id=:id AND tenant_id=:tid"
        ), {"id": config_id, "tid": tenant_id})
        return r.rowcount > 0

    # --------------------------------------------------------- security scans
    def create_security_scan(self, tenant_id, scan_type, target=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_security_scans "
            "(id, tenant_id, scan_type, target, status, started_at, created_at) "
            "VALUES (:id,:tid,:st,:tg,'running',NOW(),NOW())"
        ), {"id": eid, "tid": tenant_id, "st": scan_type, "tg": target})
        return eid

    def update_security_scan(self, tenant_id, scan_id, status, vulnerabilities_found=None,
                             critical_count=None, high_count=None, medium_count=None,
                             low_count=None, report_url=None):
        sets = ["status=:st"]
        params: Dict[str, Any] = {"id": scan_id, "tid": tenant_id, "st": status}
        if vulnerabilities_found is not None:
            sets.append("vulnerabilities_found=:vf")
            params["vf"] = vulnerabilities_found
        if critical_count is not None:
            sets.append("critical_count=:cc")
            params["cc"] = critical_count
        if high_count is not None:
            sets.append("high_count=:hc")
            params["hc"] = high_count
        if medium_count is not None:
            sets.append("medium_count=:mc")
            params["mc"] = medium_count
        if low_count is not None:
            sets.append("low_count=:lc")
            params["lc"] = low_count
        if report_url is not None:
            sets.append("report_url=:ru")
            params["ru"] = report_url
        if status in ("completed", "failed"):
            sets.append("completed_at=NOW()")
        self.db.execute(text(
            f"UPDATE dbp_security_scans SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": scan_id, "status": status}

    def list_security_scans(self, tenant_id, scan_type=None, status=None, limit=20):
        q = "SELECT id, scan_type, target, status, vulnerabilities_found, critical_count, high_count, medium_count, low_count, report_url, started_at, completed_at, created_at FROM dbp_security_scans WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if scan_type:
            q += " AND scan_type=:st2"
            params["st2"] = scan_type
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "scan_type": r[1], "target": r[2],
                 "status": r[3], "vulnerabilities_found": r[4],
                 "critical_count": r[5], "high_count": r[6],
                 "medium_count": r[7], "low_count": r[8],
                 "report_url": r[9],
                 "started_at": str(r[10]) if r[10] else None,
                 "completed_at": str(r[11]) if r[11] else None,
                 "created_at": str(r[12]) if r[12] else None} for r in rows]

    def get_security_scan(self, tenant_id, scan_id):
        r = self.db.execute(text(
            "SELECT id, scan_type, target, status, vulnerabilities_found, critical_count, high_count, medium_count, low_count, report_url, started_at, completed_at, created_at "
            "FROM dbp_security_scans WHERE id=:id AND tenant_id=:tid"
        ), {"id": scan_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "scan_type": r[1], "target": r[2],
                "status": r[3], "vulnerabilities_found": r[4],
                "critical_count": r[5], "high_count": r[6],
                "medium_count": r[7], "low_count": r[8],
                "report_url": r[9],
                "started_at": str(r[10]) if r[10] else None,
                "completed_at": str(r[11]) if r[11] else None,
                "created_at": str(r[12]) if r[12] else None}
