"""
P50 Platform Maturity & Certification Engine
"""
import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class PlatformMaturityEngine:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------ certification
    def create_score(self, tenant_id, certification_level, total_score,
                     max_score, status="pending", expires_at=None):
        sid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_certification_scores "
            "(id, tenant_id, certification_level, total_score, max_score, status, assessed_at, expires_at, created_at) "
            "VALUES (:id,:tid,:cl,:ts,:ms,:st,NOW(),:ea,NOW())"
        ), {"id": sid, "tid": tenant_id, "cl": certification_level,
            "ts": total_score, "ms": max_score, "st": status,
            "ea": expires_at})
        return sid

    def list_scores(self, tenant_id, status=None):
        q = "SELECT id, certification_level, total_score, max_score, status, assessed_at, expires_at, created_at FROM dbp_certification_scores WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "certification_level": r[1],
                 "total_score": r[2], "max_score": r[3],
                 "status": r[4],
                 "assessed_at": str(r[5]) if r[5] else None,
                 "expires_at": str(r[6]) if r[6] else None,
                 "created_at": str(r[7]) if r[7] else None} for r in rows]

    def get_score(self, tenant_id, score_id):
        r = self.db.execute(text(
            "SELECT id, certification_level, total_score, max_score, status, assessed_at, expires_at, created_at "
            "FROM dbp_certification_scores WHERE id=:id AND tenant_id=:tid"
        ), {"id": score_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "certification_level": r[1],
                "total_score": r[2], "max_score": r[3],
                "status": r[4],
                "assessed_at": str(r[5]) if r[5] else None,
                "expires_at": str(r[6]) if r[6] else None,
                "created_at": str(r[7]) if r[7] else None}

    # ------------------------------------------------ maturity metrics
    def record_metric(self, tenant_id, metric_category, metric_name,
                      metric_value, target_value=None):
        mid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_maturity_metrics "
            "(id, tenant_id, metric_category, metric_name, metric_value, target_value, status, measured_at) "
            "VALUES (:id,:tid,:mc,:mn,:mv,:tv,'measured',NOW())"
        ), {"id": mid, "tid": tenant_id, "mc": metric_category,
            "mn": metric_name, "mv": metric_value, "tv": target_value})
        return mid

    def list_metrics(self, tenant_id, metric_category=None):
        q = "SELECT id, metric_category, metric_name, metric_value, target_value, status, measured_at FROM dbp_maturity_metrics WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if metric_category:
            q += " AND metric_category=:mc"
            params["mc"] = metric_category
        q += " ORDER BY measured_at DESC"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "metric_category": r[1], "metric_name": r[2],
                 "metric_value": r[3], "target_value": r[4],
                 "status": r[5],
                 "measured_at": str(r[6]) if r[6] else None} for r in rows]

    # ------------------------------------------------ platform features
    def register_feature(self, feature_name, feature_category, version_added,
                         is_stable=False, metadata=None):
        fid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_platform_features "
            "(id, feature_name, feature_category, version_added, is_stable, metadata, created_at) "
            "VALUES (:id,:fn,:fc,:va,:is2,:md,NOW())"
        ), {"id": fid, "fn": feature_name, "fc": feature_category,
            "va": version_added, "is2": is_stable,
            "md": json.dumps(metadata) if metadata else None})
        return fid

    def list_features(self, feature_category=None, is_stable=None):
        q = "SELECT id, feature_name, feature_category, version_added, is_stable, created_at FROM dbp_platform_features WHERE 1=1"
        params: dict[str, Any] = {}
        if feature_category:
            q += " AND feature_category=:fc"
            params["fc"] = feature_category
        if is_stable is not None:
            q += " AND is_stable=:is2"
            params["is2"] = is_stable
        q += " ORDER BY feature_category, version_added"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "feature_name": r[1],
                 "feature_category": r[2], "version_added": r[3],
                 "is_stable": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    def update_feature(self, feature_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": feature_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_platform_features SET {', '.join(sets)} WHERE id=:id"
        ), params)
        return {"id": feature_id, "updated": True}

    # ------------------------------------------------ upgrade history
    def record_upgrade(self, tenant_id, from_version, to_version, upgrade_type,
                       notes=None):
        uid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_upgrade_history "
            "(id, tenant_id, from_version, to_version, upgrade_type, status, notes, started_at, completed_at) "
            "VALUES (:id,:tid,:fv,:tv,:ut,'completed',:no,NOW(),NOW())"
        ), {"id": uid, "tid": tenant_id, "fv": from_version,
            "tv": to_version, "ut": upgrade_type, "no": notes})
        return uid

    def list_upgrades(self, tenant_id, upgrade_type=None):
        q = "SELECT id, from_version, to_version, upgrade_type, status, notes, completed_at FROM dbp_upgrade_history WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if upgrade_type:
            q += " AND upgrade_type=:ut"
            params["ut"] = upgrade_type
        q += " ORDER BY completed_at DESC"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "from_version": r[1], "to_version": r[2],
                 "upgrade_type": r[3], "status": r[4],
                 "notes": r[5],
                 "completed_at": str(r[6]) if r[6] else None} for r in rows]

    # ------------------------------------------------ platform health
    def record_health(self, tenant_id, component_name, health_score, status,
                      details=None):
        hid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_platform_health "
            "(id, tenant_id, component_name, health_score, status, details, checked_at) "
            "VALUES (:id,:tid,:cn,:hs,:st,:de,NOW())"
        ), {"id": hid, "tid": tenant_id, "cn": component_name,
            "hs": health_score, "st": status,
            "de": json.dumps(details) if details else None})
        return hid

    def list_health(self, tenant_id, component_name=None):
        q = "SELECT id, component_name, health_score, status, details, checked_at FROM dbp_platform_health WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if component_name:
            q += " AND component_name=:cn"
            params["cn"] = component_name
        q += " ORDER BY checked_at DESC LIMIT 100"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "component_name": r[1],
                 "health_score": r[2], "status": r[3],
                 "details": r[4],
                 "checked_at": str(r[5]) if r[5] else None} for r in rows]
