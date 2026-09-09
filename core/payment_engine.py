"""
EOS Payment Gateway Engine
Supports: Stripe, Mada, STC Pay, Bank Transfer, Cash

Runtime code deliberately contains no schema DDL. Payment settlement is an
explicit state transition and starts as pending; a trusted provider/webhook
path must confirm completion.
"""
from __future__ import annotations

import json
import secrets
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import text


class PaymentGatewayEngine:
    _MAX_LIST_LIMIT = 200
    _GATEWAY_TYPES = {"stripe", "mada", "stc_pay", "bank_transfer", "cash", "manual"}
    _TRANSACTION_TYPES = {"payment", "refund", "authorization", "capture"}

    def __init__(self, db):
        self.db = db

    @classmethod
    def _limit(cls, value: Any, default: int = 50) -> int:
        try:
            return max(1, min(int(value), cls._MAX_LIST_LIMIT))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _amount(value: Any) -> Decimal:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("Payment amount must be a valid decimal") from exc
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Payment amount must be positive")
        return amount

    @staticmethod
    def _currency(value: Any) -> str:
        currency = str(value or "SAR").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("Currency must be a 3-letter ISO code")
        return currency

    @staticmethod
    def _safe_gateway_config(config: Optional[dict]) -> dict:
        if not config:
            return {}
        secret_names = {"secret", "secret_key", "api_key", "password", "token", "private_key", "client_secret"}
        return {
            str(key): ("[REDACTED]" if str(key).lower() in secret_names else value)
            for key, value in config.items()
        }

    def list_gateways(self, tenant_id):
        rows = self.db.execute(
            text(
                "SELECT id, tenant_id, gateway_name, gateway_type, is_active, created_at "
                "FROM dbp_payment_gateways WHERE tenant_id=:t ORDER BY created_at DESC"
            ),
            {"t": tenant_id},
        ).fetchall()
        return [dict(row._mapping) for row in rows]

    def create_gateway(self, tenant_id, name, gw_type, config=None):
        gateway_name = str(name).strip()
        gateway_type = str(gw_type).strip().lower()
        if not gateway_name:
            raise ValueError("Gateway name is required")
        if gateway_type not in self._GATEWAY_TYPES:
            raise ValueError("Unsupported gateway type")
        if config is not None and not isinstance(config, dict):
            raise ValueError("Gateway config must be an object")

        gid = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_payment_gateways "
                "(id, tenant_id, gateway_name, gateway_type, config) "
                "VALUES (:id, :t, :name, :type, :config)"
            ),
            {
                "id": gid,
                "t": tenant_id,
                "name": gateway_name,
                "type": gateway_type,
                "config": json.dumps(config or {}),
            },
        )
        self.db.commit()
        return {"gateway_id": gid, "message": f"Gateway {gateway_name} created"}

    def create_transaction(
        self,
        tenant_id,
        amount,
        currency="SAR",
        tx_type="payment",
        ref_type=None,
        ref_id=None,
        customer_id=None,
        method=None,
    ):
        amount_value = self._amount(amount)
        transaction_type = str(tx_type or "payment").strip().lower()
        if transaction_type not in self._TRANSACTION_TYPES:
            raise ValueError("Unsupported transaction type")
        tid = str(uuid.uuid4())
        ref_number = f"TXN-{secrets.token_hex(4).upper()}"
        self.db.execute(
            text(
                "INSERT INTO dbp_payment_transactions "
                "(id, tenant_id, transaction_type, amount, currency, status, reference_type, "
                "reference_id, customer_id, payment_method, gateway_response) "
                "VALUES (:id, :t, :type, :amt, :cur, 'pending', :rtype, :rid, :cid, :method, :resp)"
            ),
            {
                "id": tid,
                "t": tenant_id,
                "type": transaction_type,
                "amt": amount_value,
                "cur": self._currency(currency),
                "rtype": ref_type,
                "rid": ref_id,
                "cid": customer_id,
                "method": method,
                "resp": json.dumps({"ref_number": ref_number}),
            },
        )
        self.db.commit()
        return {"transaction_id": tid, "ref_number": ref_number, "status": "pending"}

    def complete_transaction(self, transaction_id, tenant_id, gateway_response=None):
        row = self.db.execute(
            text(
                "SELECT id, status FROM dbp_payment_transactions "
                "WHERE id=:id AND tenant_id=:t FOR UPDATE"
            ),
            {"id": transaction_id, "t": tenant_id},
        ).fetchone()
        if not row:
            return {"error": "Transaction not found"}
        if row[1] == "completed":
            return {"status": "completed", "transaction_id": transaction_id, "idempotent": True}
        if row[1] != "pending":
            return {"error": f"Transaction cannot be completed from status {row[1]}"}
        self.db.execute(
            text(
                "UPDATE dbp_payment_transactions SET status='completed', completed_at=NOW(), "
                "gateway_response = COALESCE(gateway_response,'{}'::jsonb) || :resp "
                "WHERE id=:id AND tenant_id=:t AND status='pending'"
            ),
            {
                "id": transaction_id,
                "t": tenant_id,
                "resp": json.dumps(gateway_response or {}),
            },
        )
        self.db.commit()
        return {"status": "completed", "transaction_id": transaction_id}

    def fail_transaction(self, transaction_id, tenant_id, reason=""):
        row = self.db.execute(
            text(
                "SELECT id, status FROM dbp_payment_transactions "
                "WHERE id=:id AND tenant_id=:t FOR UPDATE"
            ),
            {"id": transaction_id, "t": tenant_id},
        ).fetchone()
        if not row:
            return {"error": "Transaction not found"}
        if row[1] == "failed":
            return {"status": "failed", "transaction_id": transaction_id, "idempotent": True}
        if row[1] != "pending":
            return {"error": f"Transaction cannot be failed from status {row[1]}"}
        self.db.execute(
            text(
                "UPDATE dbp_payment_transactions SET status='failed', "
                "gateway_response = COALESCE(gateway_response,'{}'::jsonb) || :resp "
                "WHERE id=:id AND tenant_id=:t AND status='pending'"
            ),
            {"id": transaction_id, "t": tenant_id, "resp": json.dumps({"failure_reason": str(reason)[:500]})},
        )
        self.db.commit()
        return {"status": "failed", "transaction_id": transaction_id}

    def refund_transaction(self, transaction_id, tenant_id, amount=None):
        row = self.db.execute(
            text(
                "SELECT * FROM dbp_payment_transactions "
                "WHERE id=:id AND tenant_id=:t FOR UPDATE"
            ),
            {"id": transaction_id, "t": tenant_id},
        ).fetchone()
        if not row:
            return {"error": "Transaction not found"}
        row_dict = dict(row._mapping)
        if row_dict["transaction_type"] == "refund":
            return {"error": "Cannot refund a refund transaction"}
        if row_dict["status"] != "completed":
            return {"error": "Only completed transactions can be refunded"}

        original_amount = Decimal(str(row_dict["amount"] or 0))
        already_refunded = self.db.execute(
            text(
                "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
                "WHERE reference_type='payment' AND reference_id=:ref "
                "AND transaction_type='refund' AND tenant_id=:t AND status='completed'"
            ),
            {"ref": transaction_id, "t": tenant_id},
        ).fetchone()[0]
        refundable = original_amount - Decimal(str(already_refunded or 0))
        refund_amount = refundable if amount is None else self._amount(amount)
        if refund_amount > refundable:
            return {"error": f"Refund amount {refund_amount} exceeds refundable {refundable}"}

        refund_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_payment_transactions "
                "(id, tenant_id, transaction_type, amount, currency, status, reference_type, reference_id, completed_at) "
                "VALUES (:id,:t,'refund',:amt,:cur,'completed','payment',:ref,NOW())"
            ),
            {"id": refund_id, "t": tenant_id, "amt": refund_amount, "cur": row_dict["currency"], "ref": transaction_id},
        )
        self.db.commit()
        return {"refund_id": refund_id, "amount": float(refund_amount), "status": "completed"}

    def list_transactions(self, tenant_id, status=None, limit=50):
        query = "SELECT * FROM dbp_payment_transactions WHERE tenant_id=:t"
        params = {"t": tenant_id, "lim": self._limit(limit)}
        if status:
            query += " AND status=:s"
            params["s"] = str(status).strip().lower()
        query += " ORDER BY created_at DESC LIMIT :lim"
        rows = self.db.execute(text(query), params).fetchall()
        return [dict(row._mapping) for row in rows]

    def get_transaction(self, transaction_id, tenant_id):
        row = self.db.execute(
            text("SELECT * FROM dbp_payment_transactions WHERE id=:id AND tenant_id=:t"),
            {"id": transaction_id, "t": tenant_id},
        ).fetchone()
        return dict(row._mapping) if row else None

    def create_payment_link(self, tenant_id, amount, description=None, email=None, expires_hours=24):
        amount_value = self._amount(amount)
        try:
            hours = int(expires_hours)
        except (TypeError, ValueError) as exc:
            raise ValueError("expires_hours must be an integer") from exc
        if not 1 <= hours <= 720:
            raise ValueError("expires_hours must be between 1 and 720")
        link_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        self.db.execute(
            text(
                "INSERT INTO dbp_payment_links "
                "(id, tenant_id, link_token, amount, currency, description, customer_email, expires_at) "
                "VALUES (:id,:t,:token,:amt,'SAR',:desc,:email,NOW() + (:hrs || ' hours')::interval)"
            ),
            {"id": link_id, "t": tenant_id, "token": token, "amt": amount_value, "desc": description, "email": email, "hrs": str(hours)},
        )
        self.db.commit()
        return {"link_id": link_id, "payment_url": f"/pay/{token}"}

    def process_bank_transfer(self, tenant_id, amount, bank_name, account_number, reference):
        if not str(bank_name).strip() or not str(account_number).strip() or not str(reference).strip():
            raise ValueError("Bank transfer details are required")
        tx = self.create_transaction(tenant_id, amount, method="bank_transfer")
        self.db.execute(
            text(
                "UPDATE dbp_payment_transactions SET gateway_response = COALESCE(gateway_response,'{}'::jsonb) || :resp "
                "WHERE id=:id AND tenant_id=:t"
            ),
            {
                "id": tx["transaction_id"],
                "t": tenant_id,
                "resp": json.dumps({
                    "bank_name": str(bank_name)[:120],
                    "account_last4": str(account_number)[-4:],
                    "transfer_reference": str(reference)[:120],
                }),
            },
        )
        self.db.commit()
        return tx

    def process_cash(self, tenant_id, amount, received_by=None):
        return self.create_transaction(tenant_id, amount, method="cash")

    def get_summary(self, tenant_id):
        total = self.db.execute(
            text(
                "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
                "WHERE tenant_id=:t AND status='completed' AND transaction_type='payment'"
            ),
            {"t": tenant_id},
        ).fetchone()[0]
        refunded = self.db.execute(
            text(
                "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
                "WHERE tenant_id=:t AND status='completed' AND transaction_type='refund'"
            ),
            {"t": tenant_id},
        ).fetchone()[0]
        pending = self.db.execute(
            text("SELECT COUNT(*) FROM dbp_payment_transactions WHERE tenant_id=:t AND status='pending'"),
            {"t": tenant_id},
        ).fetchone()[0]
        return {
            "total_collected": float(total),
            "total_refunded": float(refunded),
            "net_amount": float(total - refunded),
            "pending_count": pending,
        }
