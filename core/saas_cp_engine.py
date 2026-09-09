"""
P41 SaaS Control Plane Engine
"""
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class SaaSCPEngine:
    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------- saas tenants
    def create_tenant(self, tenant_id, name, slug, plan_id=None,
                      max_users=10, max_companies=1, settings=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_saas_tenants "
            "(id, tenant_id, name, slug, plan_id, max_users, max_companies, settings, created_at, updated_at) "
            "VALUES (:id,:tid,:na,:sl,:pi,:mu,:mc,:se,NOW(),NOW())"
        ), {"id": eid, "tid": tenant_id, "na": name, "sl": slug,
            "pi": plan_id, "mu": max_users, "mc": max_companies,
            "se": __import__('json').dumps(settings) if settings else None})
        return eid

    def list_tenants(self, status=None, limit=50):
        q = "SELECT id, tenant_id, name, slug, status, plan_id, max_users, max_companies, created_at FROM dbp_saas_tenants"
        params: Dict[str, Any] = {}
        if status:
            q += " WHERE status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "name": r[2],
                 "slug": r[3], "status": r[4], "plan_id": r[5],
                 "max_users": r[6], "max_companies": r[7],
                 "created_at": str(r[8]) if r[8] else None} for r in rows]

    def get_tenant(self, tenant_id):
        r = self.db.execute(text(
            "SELECT id, tenant_id, name, slug, status, plan_id, max_users, max_companies, settings, created_at "
            "FROM dbp_saas_tenants WHERE tenant_id=:tid"
        ), {"tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "tenant_id": r[1], "name": r[2],
                "slug": r[3], "status": r[4], "plan_id": r[5],
                "max_users": r[6], "max_companies": r[7],
                "settings": r[8], "created_at": str(r[9]) if r[9] else None}

    def update_tenant(self, tenant_id, name=None, status=None, plan_id=None,
                      max_users=None, max_companies=None, settings=None):
        sets = ["updated_at=NOW()"]
        params: Dict[str, Any] = {"tid": tenant_id}
        if name is not None:
            sets.append("name=:na")
            params["na"] = name
        if status is not None:
            sets.append("status=:st")
            params["st"] = status
        if plan_id is not None:
            sets.append("plan_id=:pi")
            params["pi"] = plan_id
        if max_users is not None:
            sets.append("max_users=:mu")
            params["mu"] = max_users
        if max_companies is not None:
            sets.append("max_companies=:mc")
            params["mc"] = max_companies
        if settings is not None:
            sets.append("settings=:se")
            params["se"] = __import__('json').dumps(settings)
        self.db.execute(text(
            f"UPDATE dbp_saas_tenants SET {', '.join(sets)} WHERE tenant_id=:tid"
        ), params)
        return {"tenant_id": tenant_id, "updated": True}

    # ------------------------------------------------------------- saas plans
    def create_plan(self, tenant_id, plan_name, plan_code, price_monthly=0,
                    price_yearly=0, max_users=10, max_companies=1,
                    max_storage_gb=5, features=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_saas_plans "
            "(id, tenant_id, plan_name, plan_code, price_monthly, price_yearly, "
            "max_users, max_companies, max_storage_gb, features, created_at, updated_at) "
            "VALUES (:id,:tid,:pn,:pc,:pm,:py,:mu,:mc,:ms,:fe,NOW(),NOW())"
        ), {"id": eid, "tid": tenant_id, "pn": plan_name, "pc": plan_code,
            "pm": price_monthly, "py": price_yearly, "mu": max_users,
            "mc": max_companies, "ms": max_storage_gb,
            "fe": __import__('json').dumps(features) if features else None})
        return eid

    def list_plans(self, tenant_id, is_active=None, limit=50):
        q = "SELECT id, plan_name, plan_code, price_monthly, price_yearly, max_users, max_companies, max_storage_gb, is_active, created_at FROM dbp_saas_plans WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if is_active is not None:
            q += " AND is_active=:ia"
            params["ia"] = is_active
        q += " ORDER BY price_monthly ASC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "plan_name": r[1], "plan_code": r[2],
                 "price_monthly": r[3], "price_yearly": r[4],
                 "max_users": r[5], "max_companies": r[6],
                 "max_storage_gb": r[7], "is_active": r[8],
                 "created_at": str(r[9]) if r[9] else None} for r in rows]

    def get_plan(self, tenant_id, plan_id):
        r = self.db.execute(text(
            "SELECT id, plan_name, plan_code, price_monthly, price_yearly, "
            "max_users, max_companies, max_storage_gb, features, is_active, created_at "
            "FROM dbp_saas_plans WHERE id=:id AND tenant_id=:tid"
        ), {"id": plan_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "plan_name": r[1], "plan_code": r[2],
                "price_monthly": r[3], "price_yearly": r[4],
                "max_users": r[5], "max_companies": r[6],
                "max_storage_gb": r[7], "features": r[8],
                "is_active": r[9], "created_at": str(r[10]) if r[10] else None}

    def update_plan(self, tenant_id, plan_id, is_active=None, price_monthly=None,
                    price_yearly=None):
        sets = ["updated_at=NOW()"]
        params: Dict[str, Any] = {"id": plan_id, "tid": tenant_id}
        if is_active is not None:
            sets.append("is_active=:ia")
            params["ia"] = is_active
        if price_monthly is not None:
            sets.append("price_monthly=:pm")
            params["pm"] = price_monthly
        if price_yearly is not None:
            sets.append("price_yearly=:py")
            params["py"] = price_yearly
        self.db.execute(text(
            f"UPDATE dbp_saas_plans SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": plan_id, "updated": True}

    # ----------------------------------------------------------- saas features
    def create_feature(self, feature_name, feature_code, description=None,
                       category=None, is_default=False):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_saas_features "
            "(id, feature_name, feature_code, description, category, is_default, created_at) "
            "VALUES (:id,:fn,:fc,:de,:ca,:df,NOW())"
        ), {"id": eid, "fn": feature_name, "fc": feature_code,
            "de": description, "ca": category, "df": is_default})
        return eid

    def list_features(self, category=None, limit=50):
        q = "SELECT id, feature_name, feature_code, description, category, is_default, created_at FROM dbp_saas_features"
        params: Dict[str, Any] = {}
        if category:
            q += " WHERE category=:ca"
            params["ca"] = category
        q += " ORDER BY category, feature_name LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "feature_name": r[1], "feature_code": r[2],
                 "description": r[3], "category": r[4],
                 "is_default": r[5],
                 "created_at": str(r[6]) if r[6] else None} for r in rows]

    def get_feature(self, feature_id):
        r = self.db.execute(text(
            "SELECT id, feature_name, feature_code, description, category, is_default, created_at "
            "FROM dbp_saas_features WHERE id=:id"
        ), {"id": feature_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "feature_name": r[1], "feature_code": r[2],
                "description": r[3], "category": r[4],
                "is_default": r[5], "created_at": str(r[6]) if r[6] else None}

    # ------------------------------------------------- tenant features
    def enable_tenant_feature(self, tenant_id, feature_id, config=None):
        existing = self.db.execute(text(
            "SELECT id FROM dbp_saas_tenant_features WHERE tenant_id=:tid AND feature_id=:fi"
        ), {"tid": tenant_id, "fi": feature_id}).fetchone()
        if existing:
            self.db.execute(text(
                "UPDATE dbp_saas_tenant_features SET is_enabled=true, config=:cf, enabled_at=NOW() "
                "WHERE tenant_id=:tid AND feature_id=:fi"
            ), {"cf": __import__('json').dumps(config) if config else None,
                "tid": tenant_id, "fi": feature_id})
            return existing[0]
        else:
            eid = str(uuid.uuid4())
            self.db.execute(text(
                "INSERT INTO dbp_saas_tenant_features "
                "(id, tenant_id, feature_id, is_enabled, config, enabled_at, created_at) "
                "VALUES (:id,:tid,:fi,true,:cf,NOW(),NOW())"
            ), {"id": eid, "tid": tenant_id, "fi": feature_id,
                "cf": __import__('json').dumps(config) if config else None})
            return eid

    def disable_tenant_feature(self, tenant_id, feature_id):
        self.db.execute(text(
            "UPDATE dbp_saas_tenant_features SET is_enabled=false "
            "WHERE tenant_id=:tid AND feature_id=:fi"
        ), {"tid": tenant_id, "fi": feature_id})
        return {"tenant_id": tenant_id, "feature_id": feature_id, "disabled": True}

    def list_tenant_features(self, tenant_id, is_enabled=None):
        q = ("SELECT tf.id, f.id, f.feature_name, f.feature_code, tf.is_enabled, tf.config, tf.enabled_at "
             "FROM dbp_saas_tenant_features tf "
             "JOIN dbp_saas_features f ON tf.feature_id = f.id "
             "WHERE tf.tenant_id=:tid")
        params: Dict[str, Any] = {"tid": tenant_id}
        if is_enabled is not None:
            q += " AND tf.is_enabled=:ie"
            params["ie"] = is_enabled
        q += " ORDER BY f.feature_name"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "feature_id": r[1], "feature_name": r[2],
                 "feature_code": r[3], "is_enabled": r[4],
                 "config": r[5], "enabled_at": str(r[6]) if r[6] else None} for r in rows]

    # ----------------------------------------------------------- usage tracking
    def record_usage(self, tenant_id, usage_type, usage_value, period_start=None,
                     period_end=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_saas_usage "
            "(id, tenant_id, usage_type, usage_value, period_start, period_end, recorded_at) "
            "VALUES (:id,:tid,:ut,:uv,:ps,:pe,NOW())"
        ), {"id": eid, "tid": tenant_id, "ut": usage_type,
            "uv": usage_value, "ps": period_start, "pe": period_end})
        return eid

    def list_usage(self, tenant_id, usage_type=None, limit=50):
        q = "SELECT id, tenant_id, usage_type, usage_value, period_start, period_end, recorded_at FROM dbp_saas_usage WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if usage_type:
            q += " AND usage_type=:ut"
            params["ut"] = usage_type
        q += " ORDER BY recorded_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "usage_type": r[2],
                 "usage_value": r[3],
                 "period_start": str(r[4]) if r[4] else None,
                 "period_end": str(r[5]) if r[5] else None,
                 "recorded_at": str(r[6]) if r[6] else None} for r in rows]

    def get_usage_summary(self, tenant_id, usage_type):
        r = self.db.execute(text(
            "SELECT SUM(usage_value) as total, COUNT(*) as records "
            "FROM dbp_saas_usage WHERE tenant_id=:tid AND usage_type=:ut"
        ), {"tid": tenant_id, "ut": usage_type}).fetchone()
        return {"total": r[0] or 0, "records": r[1] or 0}
