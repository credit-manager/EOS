"""
P43 Subscription & Licensing Engine

The SaaS billing subsystem is platform-owned data. Every read/write is scoped
by tenant, and client-controlled SQL identifiers are restricted to a fixed
allowlist. Payment records are never marked completed merely because an API
caller submitted a transaction id; settlement must be confirmed by a trusted
payment-provider/webhook path.
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session


class SubscriptionEngine:
    _LICENSE_UPDATE_FIELDS = {
        "license_type",
        "max_seats",
        "valid_from",
        "valid_until",
        "status",
        "features",
    }
    _MAX_LIST_LIMIT = 200

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _bounded_limit(value: int, default: int = 50) -> int:
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(limit, SubscriptionEngine._MAX_LIST_LIMIT))

    @staticmethod
    def _positive_amount(value: Any) -> Decimal:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("amount must be a valid decimal") from exc
        if not amount.is_finite() or amount <= 0:
            raise ValueError("amount must be greater than zero")
        return amount

    @staticmethod
    def _currency(value: Any) -> str:
        currency = str(value or "USD").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a 3-letter ISO currency code")
        return currency

    def create_subscription(self, tenant_id, plan_id, billing_cycle="monthly", trial_end=None):
        if not str(plan_id).strip():
            raise ValueError("plan_id is required")
        if billing_cycle not in {"monthly", "annual", "yearly"}:
            raise ValueError("invalid billing cycle")

        sid = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_subscriptions "
                "(id, tenant_id, plan_id, billing_cycle, status, trial_end, created_at) "
                "VALUES (:id,:tid,:pl,:bc,'active',:te,NOW())"
            ),
            {"id": sid, "tid": tenant_id, "pl": str(plan_id).strip(), "bc": billing_cycle, "te": trial_end},
        )
        return sid

    def get_subscription(self, tenant_id):
        row = self.db.execute(
            text(
                "SELECT id, tenant_id, plan_id, status, billing_cycle, "
                "current_period_start, current_period_end, trial_end, "
                "cancelled_at, created_at "
                "FROM dbp_subscriptions WHERE tenant_id=:tid "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tenant_id},
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "tenant_id": row[1],
            "plan_id": row[2],
            "status": row[3],
            "billing_cycle": row[4],
            "current_period_start": str(row[5]) if row[5] else None,
            "current_period_end": str(row[6]) if row[6] else None,
            "trial_end": str(row[7]) if row[7] else None,
            "cancelled_at": str(row[8]) if row[8] else None,
            "created_at": str(row[9]) if row[9] else None,
        }

    def cancel_subscription(self, tenant_id):
        result = self.db.execute(
            text(
                "UPDATE dbp_subscriptions SET status='cancelled', cancelled_at=NOW() "
                "WHERE tenant_id=:tid AND status <> 'cancelled'"
            ),
            {"tid": tenant_id},
        )
        if result.rowcount == 0:
            return {"status": "not_found"}
        return {"status": "cancelled"}

    def list_subscriptions(self, tenant_id, status=None, limit=50):
        q = (
            "SELECT id, tenant_id, plan_id, status, billing_cycle, created_at "
            "FROM dbp_subscriptions WHERE tenant_id=:tid"
        )
        params: Dict[str, Any] = {"tid": tenant_id, "lim": self._bounded_limit(limit)}
        if status:
            q += " AND status=:st"
            params["st"] = str(status).strip()
        q += " ORDER BY created_at DESC LIMIT :lim"
        rows = self.db.execute(text(q), params).fetchall()
        return [
            {
                "id": row[0],
                "tenant_id": row[1],
                "plan_id": row[2],
                "status": row[3],
                "billing_cycle": row[4],
                "created_at": str(row[5]) if row[5] else None,
            }
            for row in rows
        ]

    # -------------------------------------------------------- invoices
    def _subscription_belongs_to_tenant(self, tenant_id, subscription_id) -> bool:
        row = self.db.execute(
            text(
                "SELECT 1 FROM dbp_subscriptions "
                "WHERE id=:sid AND tenant_id=:tid LIMIT 1"
            ),
            {"sid": subscription_id, "tid": tenant_id},
        ).fetchone()
        return row is not None

    def create_invoice(
        self,
        tenant_id,
        subscription_id,
        invoice_number,
        amount,
        currency="USD",
        due_date=None,
        line_items=None,
    ):
        if not self._subscription_belongs_to_tenant(tenant_id, subscription_id):
            raise ValueError("subscription does not belong to tenant")
        if not str(invoice_number).strip():
            raise ValueError("invoice_number is required")

        inv_id = str(uuid.uuid4())
        amount_value = self._positive_amount(amount)
        currency_value = self._currency(currency)
        self.db.execute(
            text(
                "INSERT INTO dbp_invoices_saas "
                "(id, tenant_id, subscription_id, invoice_number, amount, currency, "
                "status, due_date, line_items, created_at) "
                "VALUES (:id,:tid,:si,:in2,:am,:cu,'pending',:dd,:li,NOW())"
            ),
            {
                "id": inv_id,
                "tid": tenant_id,
                "si": subscription_id,
                "in2": str(invoice_number).strip(),
                "am": amount_value,
                "cu": currency_value,
                "dd": due_date,
                "li": json.dumps(line_items) if line_items is not None else None,
            },
        )
        return inv_id

    def get_invoice(self, tenant_id, invoice_id):
        row = self.db.execute(
            text(
                "SELECT id, tenant_id, subscription_id, invoice_number, amount, "
                "currency, status, due_date, paid_at, line_items, created_at "
                "FROM dbp_invoices_saas WHERE id=:id AND tenant_id=:tid"
            ),
            {"id": invoice_id, "tid": tenant_id},
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "tenant_id": row[1],
            "subscription_id": row[2],
            "invoice_number": row[3],
            "amount": row[4],
            "currency": row[5],
            "status": row[6],
            "due_date": str(row[7]) if row[7] else None,
            "paid_at": str(row[8]) if row[8] else None,
            "line_items": row[9],
            "created_at": str(row[10]) if row[10] else None,
        }

    def update_invoice_status(self, tenant_id, invoice_id, status):
        allowed = {"pending", "paid", "void", "overdue", "failed"}
        normalized = str(status).strip().lower()
        if normalized not in allowed:
            raise ValueError("invalid invoice status")
        sets = ["status=:st"]
        params: Dict[str, Any] = {"id": invoice_id, "tid": tenant_id, "st": normalized}
        if normalized == "paid":
            sets.append("paid_at=COALESCE(paid_at, NOW())")
        elif normalized != "paid":
            sets.append("paid_at=NULL")
        self.db.execute(
            text(
                f"UPDATE dbp_invoices_saas SET {', '.join(sets)} "
                "WHERE id=:id AND tenant_id=:tid"
            ),
            params,
        )
        return {"id": invoice_id, "status": normalized}

    def list_invoices(self, tenant_id, status=None, limit=20):
        q = (
            "SELECT id, invoice_number, amount, currency, status, due_date, paid_at, created_at "
            "FROM dbp_invoices_saas WHERE tenant_id=:tid"
        )
        params: Dict[str, Any] = {"tid": tenant_id, "lim": self._bounded_limit(limit)}
        if status:
            q += " AND status=:st"
            params["st"] = str(status).strip().lower()
        q += " ORDER BY created_at DESC LIMIT :lim"
        rows = self.db.execute(text(q), params).fetchall()
        return [
            {
                "id": row[0],
                "invoice_number": row[1],
                "amount": row[2],
                "currency": row[3],
                "status": row[4],
                "due_date": str(row[5]) if row[5] else None,
                "paid_at": str(row[6]) if row[6] else None,
                "created_at": str(row[7]) if row[7] else None,
            }
            for row in rows
        ]

    # -------------------------------------------------------- payments
    def _invoice_belongs_to_tenant(self, tenant_id, invoice_id) -> bool:
        row = self.db.execute(
            text(
                "SELECT 1 FROM dbp_invoices_saas "
                "WHERE id=:iid AND tenant_id=:tid LIMIT 1"
            ),
            {"iid": invoice_id, "tid": tenant_id},
        ).fetchone()
        return row is not None

    def create_payment(
        self,
        tenant_id,
        invoice_id,
        amount,
        currency="USD",
        payment_method=None,
        transaction_id=None,
    ):
        if invoice_id is not None and not self._invoice_belongs_to_tenant(tenant_id, invoice_id):
            raise ValueError("invoice does not belong to tenant")
        amount_value = self._positive_amount(amount)
        currency_value = self._currency(currency)
        pid = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_payments_saas "
                "(id, tenant_id, invoice_id, amount, currency, payment_method, "
                "status, transaction_id, created_at) "
                "VALUES (:id,:tid,:ii,:am,:cu,:pm,'pending',:ti,NOW())"
            ),
            {
                "id": pid,
                "tid": tenant_id,
                "ii": invoice_id,
                "am": amount_value,
                "cu": currency_value,
                "pm": payment_method,
                "ti": transaction_id,
            },
        )
        return pid

    def list_payments(self, tenant_id, limit=20):
        rows = self.db.execute(
            text(
                "SELECT id, invoice_id, amount, currency, payment_method, status, "
                "transaction_id, paid_at, created_at "
                "FROM dbp_payments_saas WHERE tenant_id=:tid "
                "ORDER BY created_at DESC LIMIT :lim"
            ),
            {"tid": tenant_id, "lim": self._bounded_limit(limit)},
        ).fetchall()
        return [
            {
                "id": row[0],
                "invoice_id": row[1],
                "amount": row[2],
                "currency": row[3],
                "payment_method": row[4],
                "status": row[5],
                "transaction_id": row[6],
                "paid_at": str(row[7]) if row[7] else None,
                "created_at": str(row[8]) if row[8] else None,
            }
            for row in rows
        ]

    # -------------------------------------------------------- licenses
    def create_license(
        self,
        tenant_id,
        license_key,
        license_type,
        max_seats=5,
        valid_from=None,
        valid_until=None,
        features=None,
    ):
        max_seats = int(max_seats)
        if max_seats < 1 or max_seats > 1_000_000:
            raise ValueError("max_seats out of allowed range")
        if not str(license_key).strip() or not str(license_type).strip():
            raise ValueError("license_key and license_type are required")

        lid = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_licenses "
                "(id, tenant_id, license_key, license_type, max_seats, "
                "valid_from, valid_until, status, features, created_at) "
                "VALUES (:id,:tid,:lk,:lt,:ms,:vf,:vu,'active',:fe,NOW())"
            ),
            {
                "id": lid,
                "tid": tenant_id,
                "lk": str(license_key).strip(),
                "lt": str(license_type).strip(),
                "ms": max_seats,
                "vf": valid_from,
                "vu": valid_until,
                "fe": json.dumps(features) if features is not None else None,
            },
        )
        return lid

    def get_license(self, tenant_id, license_id):
        row = self.db.execute(
            text(
                "SELECT id, tenant_id, license_key, license_type, max_seats, "
                "valid_from, valid_until, status, features, created_at "
                "FROM dbp_licenses WHERE id=:id AND tenant_id=:tid"
            ),
            {"id": license_id, "tid": tenant_id},
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "tenant_id": row[1],
            "license_key": row[2],
            "license_type": row[3],
            "max_seats": row[4],
            "valid_from": str(row[5]) if row[5] else None,
            "valid_until": str(row[6]) if row[6] else None,
            "status": row[7],
            "features": row[8],
            "created_at": str(row[9]) if row[9] else None,
        }

    def update_license(self, tenant_id, license_id, **kwargs):
        unknown = set(kwargs) - self._LICENSE_UPDATE_FIELDS
        if unknown:
            raise ValueError(f"unsupported license fields: {sorted(unknown)}")
        if not kwargs:
            return None
        if "max_seats" in kwargs:
            kwargs["max_seats"] = int(kwargs["max_seats"])
            if kwargs["max_seats"] < 1 or kwargs["max_seats"] > 1_000_000:
                raise ValueError("max_seats out of allowed range")
        if "status" in kwargs:
            kwargs["status"] = str(kwargs["status"]).strip().lower()
            if kwargs["status"] not in {"active", "suspended", "cancelled", "expired"}:
                raise ValueError("invalid license status")
        if "license_type" in kwargs:
            kwargs["license_type"] = str(kwargs["license_type"]).strip()
        if "features" in kwargs and not isinstance(kwargs["features"], (dict, list, type(None))):
            raise ValueError("features must be an object, array, or null")
        if "features" in kwargs and kwargs["features"] is not None:
            kwargs["features"] = json.dumps(kwargs["features"])

        sets = [f"{field}=:{field}" for field in kwargs]
        params: Dict[str, Any] = {"id": license_id, "tid": tenant_id, **kwargs}
        result = self.db.execute(
            text(
                f"UPDATE dbp_licenses SET {', '.join(sets)}, updated_at=NOW() "
                "WHERE id=:id AND tenant_id=:tid"
            ),
            params,
        )
        if result.rowcount == 0:
            raise ValueError("license not found")
        return {"id": license_id, "updated": True}

    def list_licenses(self, tenant_id, status=None, limit=50):
        q = (
            "SELECT id, license_key, license_type, max_seats, status, created_at "
            "FROM dbp_licenses WHERE tenant_id=:tid"
        )
        params: Dict[str, Any] = {"tid": tenant_id, "lim": self._bounded_limit(limit)}
        if status:
            q += " AND status=:st"
            params["st"] = str(status).strip().lower()
        q += " ORDER BY created_at DESC LIMIT :lim"
        rows = self.db.execute(text(q), params).fetchall()
        return [
            {
                "id": row[0],
                "license_key": row[1],
                "license_type": row[2],
                "max_seats": row[3],
                "status": row[4],
                "created_at": str(row[5]) if row[5] else None,
            }
            for row in rows
        ]

    # --------------------------------------------------- usage meters
    def record_usage(
        self,
        tenant_id,
        meter_name,
        meter_value,
        unit=None,
        period_start=None,
        period_end=None,
        overage_rate=0,
    ):
        if not str(meter_name).strip():
            raise ValueError("meter_name is required")
        try:
            meter_value = Decimal(str(meter_value))
            overage_rate = Decimal(str(overage_rate))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("meter_value and overage_rate must be decimal numbers") from exc
        if not meter_value.is_finite() or meter_value < 0:
            raise ValueError("meter_value must be non-negative")
        if not overage_rate.is_finite() or overage_rate < 0:
            raise ValueError("overage_rate must be non-negative")

        uid = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_usage_meters "
                "(id, tenant_id, meter_name, meter_value, unit, "
                "period_start, period_end, overage_rate, recorded_at) "
                "VALUES (:id,:tid,:mn,:mv,:un,:ps,:pe,:or,NOW())"
            ),
            {
                "id": uid,
                "tid": tenant_id,
                "mn": str(meter_name).strip(),
                "mv": meter_value,
                "un": unit,
                "ps": period_start,
                "pe": period_end,
                "or": overage_rate,
            },
        )
        return uid

    def get_usage(self, tenant_id, meter_name=None, limit=50):
        q = (
            "SELECT id, meter_name, meter_value, unit, period_start, period_end, "
            "overage_rate, recorded_at FROM dbp_usage_meters WHERE tenant_id=:tid"
        )
        params: Dict[str, Any] = {"tid": tenant_id, "lim": self._bounded_limit(limit)}
        if meter_name:
            q += " AND meter_name=:mn"
            params["mn"] = str(meter_name).strip()
        q += " ORDER BY recorded_at DESC LIMIT :lim"
        rows = self.db.execute(text(q), params).fetchall()
        return [
            {
                "id": row[0],
                "meter_name": row[1],
                "meter_value": row[2],
                "unit": row[3],
                "period_start": str(row[4]) if row[4] else None,
                "period_end": str(row[5]) if row[5] else None,
                "overage_rate": row[6],
                "recorded_at": str(row[7]) if row[7] else None,
            }
            for row in rows
        ]
