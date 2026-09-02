"""
P43 Subscription & Licensing Engine
"""
import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class SubscriptionEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------- subscriptions
    def create_subscription(self, tenant_id, plan_id, billing_cycle="monthly",
                            trial_end=None):
        sid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_subscriptions "
            "(id, tenant_id, plan_id, billing_cycle, status, trial_end, created_at) "
            "VALUES (:id,:tid,:pl,:bc,'active',:te,NOW())"
        ), {"id": sid, "tid": tenant_id, "pl": plan_id, "bc": billing_cycle,
            "te": trial_end})
        return sid

    def get_subscription(self, tenant_id):
        r = self.db.execute(text(
            "SELECT id, tenant_id, plan_id, status, billing_cycle, "
            "current_period_start, current_period_end, trial_end, "
            "cancelled_at, created_at FROM dbp_subscriptions WHERE tenant_id=:tid"
        ), {"tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "tenant_id": r[1], "plan_id": r[2], "status": r[3],
                "billing_cycle": r[4],
                "current_period_start": str(r[5]) if r[5] else None,
                "current_period_end": str(r[6]) if r[6] else None,
                "trial_end": str(r[7]) if r[7] else None,
                "cancelled_at": str(r[8]) if r[8] else None,
                "created_at": str(r[9]) if r[9] else None}

    def cancel_subscription(self, tenant_id):
        self.db.execute(text(
            "UPDATE dbp_subscriptions SET status='cancelled', cancelled_at=NOW() "
            "WHERE tenant_id=:tid"
        ), {"tid": tenant_id})
        return {"status": "cancelled"}

    def list_subscriptions(self, status=None, limit=50):
        q = "SELECT id, tenant_id, plan_id, status, billing_cycle, created_at FROM dbp_subscriptions"
        params: dict[str, Any] = {}
        if status:
            q += " WHERE status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "plan_id": r[2],
                 "status": r[3], "billing_cycle": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    # -------------------------------------------------------- invoices
    def create_invoice(self, tenant_id, subscription_id, invoice_number,
                       amount, currency="USD", due_date=None, line_items=None):
        inv_id = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_invoices_saas "
            "(id, tenant_id, subscription_id, invoice_number, amount, currency, "
            "status, due_date, line_items, created_at) "
            "VALUES (:id,:tid,:si,:in2,:am,:cu,'pending',:dd,:li,NOW())"
        ), {"id": inv_id, "tid": tenant_id, "si": subscription_id,
            "in2": invoice_number, "am": amount, "cu": currency, "dd": due_date,
            "li": json.dumps(line_items) if line_items else None})
        return inv_id

    def get_invoice(self, tenant_id, invoice_id):
        r = self.db.execute(text(
            "SELECT id, tenant_id, subscription_id, invoice_number, amount, "
            "currency, status, due_date, paid_at, line_items, created_at "
            "FROM dbp_invoices_saas WHERE id=:id AND tenant_id=:tid"
        ), {"id": invoice_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "tenant_id": r[1], "subscription_id": r[2],
                "invoice_number": r[3], "amount": r[4], "currency": r[5],
                "status": r[6], "due_date": str(r[7]) if r[7] else None,
                "paid_at": str(r[8]) if r[8] else None,
                "line_items": r[9], "created_at": str(r[10]) if r[10] else None}

    def update_invoice_status(self, tenant_id, invoice_id, status):
        sets = ["status=:st"]
        params: dict[str, Any] = {"id": invoice_id, "tid": tenant_id, "st": status}
        if status == "paid":
            sets.append("paid_at=NOW()")
        self.db.execute(text(
            f"UPDATE dbp_invoices_saas SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": invoice_id, "status": status}

    def list_invoices(self, tenant_id, status=None, limit=20):
        q = "SELECT id, invoice_number, amount, currency, status, due_date, paid_at, created_at FROM dbp_invoices_saas WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "invoice_number": r[1], "amount": r[2],
                 "currency": r[3], "status": r[4],
                 "due_date": str(r[5]) if r[5] else None,
                 "paid_at": str(r[6]) if r[6] else None,
                 "created_at": str(r[7]) if r[7] else None} for r in rows]

    # -------------------------------------------------------- payments
    def create_payment(self, tenant_id, invoice_id, amount, currency="USD",
                       payment_method=None, transaction_id=None):
        pid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_payments_saas "
            "(id, tenant_id, invoice_id, amount, currency, payment_method, "
            "status, transaction_id, created_at) "
            "VALUES (:id,:tid,:ii,:am,:cu,:pm,'completed',:ti,NOW())"
        ), {"id": pid, "tid": tenant_id, "ii": invoice_id, "am": amount,
            "cu": currency, "pm": payment_method, "ti": transaction_id})
        return pid

    def list_payments(self, tenant_id, limit=20):
        q = "SELECT id, invoice_id, amount, currency, payment_method, status, transaction_id, paid_at, created_at FROM dbp_payments_saas WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT :lim"
        rows = self.db.execute(text(q), {"tid": tenant_id, "lim": limit}).fetchall()
        return [{"id": r[0], "invoice_id": r[1], "amount": r[2],
                 "currency": r[3], "payment_method": r[4], "status": r[5],
                 "transaction_id": r[6],
                 "paid_at": str(r[7]) if r[7] else None,
                 "created_at": str(r[8]) if r[8] else None} for r in rows]

    # -------------------------------------------------------- licenses
    def create_license(self, tenant_id, license_key, license_type,
                       max_seats=5, valid_from=None, valid_until=None, features=None):
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_licenses "
            "(id, tenant_id, license_key, license_type, max_seats, "
            "valid_from, valid_until, status, features, created_at) "
            "VALUES (:id,:tid,:lk,:lt,:ms,:vf,:vu,'active',:fe,NOW())"
        ), {"id": lid, "tid": tenant_id, "lk": license_key, "lt": license_type,
            "ms": max_seats, "vf": valid_from, "vu": valid_until,
            "fe": json.dumps(features) if features else None})
        return lid

    def get_license(self, tenant_id, license_id):
        r = self.db.execute(text(
            "SELECT id, tenant_id, license_key, license_type, max_seats, "
            "valid_from, valid_until, status, features, created_at "
            "FROM dbp_licenses WHERE id=:id AND tenant_id=:tid"
        ), {"id": license_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "tenant_id": r[1], "license_key": r[2],
                "license_type": r[3], "max_seats": r[4],
                "valid_from": str(r[5]) if r[5] else None,
                "valid_until": str(r[6]) if r[6] else None,
                "status": r[7], "features": r[8],
                "created_at": str(r[9]) if r[9] else None}

    def update_license(self, tenant_id, license_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params: dict[str, Any] = {"id": license_id, "tid": tenant_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_licenses SET {', '.join(sets)}, updated_at=NOW() "
            "WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": license_id, "updated": True}

    def list_licenses(self, tenant_id, status=None):
        q = "SELECT id, license_key, license_type, max_seats, status, created_at FROM dbp_licenses WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if status:
            q += " AND status=:st"
            params["st"] = status
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "license_key": r[1], "license_type": r[2],
                 "max_seats": r[3], "status": r[4],
                 "created_at": str(r[5]) if r[5] else None} for r in rows]

    # --------------------------------------------------- usage meters
    def record_usage(self, tenant_id, meter_name, meter_value, unit=None,
                     period_start=None, period_end=None, overage_rate=0):
        uid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_usage_meters "
            "(id, tenant_id, meter_name, meter_value, unit, "
            "period_start, period_end, overage_rate, recorded_at) "
            "VALUES (:id,:tid,:mn,:mv,:un,:ps,:pe,:or,NOW())"
        ), {"id": uid, "tid": tenant_id, "mn": meter_name, "mv": meter_value,
            "un": unit, "ps": period_start, "pe": period_end, "or": overage_rate})
        return uid

    def get_usage(self, tenant_id, meter_name=None, limit=50):
        q = "SELECT id, meter_name, meter_value, unit, period_start, period_end, overage_rate, recorded_at FROM dbp_usage_meters WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if meter_name:
            q += " AND meter_name=:mn"
            params["mn"] = meter_name
        q += " ORDER BY recorded_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "meter_name": r[1], "meter_value": r[2],
                 "unit": r[3], "period_start": str(r[4]) if r[4] else None,
                 "period_end": str(r[5]) if r[5] else None,
                 "overage_rate": r[6],
                 "recorded_at": str(r[7]) if r[7] else None} for r in rows]
