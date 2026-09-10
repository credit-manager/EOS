"""EOS Payment Gateway Engine.

Runtime code deliberately contains no schema DDL. Payment settlement is an
explicit state transition and starts as pending; a trusted provider/webhook
path must confirm completion. Gateway credentials are encrypted at rest.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import text

from core.secret_store import contains_secret, encrypt_json


class PaymentGatewayEngine:
    _MAX_LIST_LIMIT = 200
    _GATEWAY_TYPES = {"stripe", "mada", "stc_pay", "bank_transfer", "cash", "manual"}
    _TRANSACTION_TYPES = {"payment", "refund", "authorization", "capture"}
    _SECRET_CONFIG_KEYS = {
        "api_key", "apikey", "secret", "secret_key", "client_secret", "password",
        "token", "access_token", "refresh_token", "private_key", "webhook_secret",
        "signing_secret", "encryption_key",
    }

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

    @classmethod
    def _safe_gateway_config(cls, config: Optional[dict]) -> dict:
        """Return a log/UI-safe copy of gateway configuration without secrets."""
        if config is None:
            return {}
        if not isinstance(config, dict):
            raise ValueError("Gateway config must be an object")

        def redact(value: Any, key: str = "") -> Any:
            normalized = key.strip().lower().replace("-", "_")
            if normalized in cls._SECRET_CONFIG_KEYS or any(
                marker in normalized for marker in ("secret", "password", "token", "private_key")
            ):
                return "[REDACTED]"
            if isinstance(value, dict):
                return {str(k): redact(v, str(k)) for k, v in value.items()}
            if isinstance(value, list):
                return [redact(item, key) for item in value]
            return value

        return redact(config)

    @staticmethod
    def _serialize_gateway_config(config: Optional[dict]) -> str:
        if config is None:
            return "{}"
        if not isinstance(config, dict):
            raise ValueError("Gateway config must be an object")
        if contains_secret(config):
            return json.dumps({
                "encrypted": True,
                "ciphertext": encrypt_json(config),
                "version": 1,
            }, separators=(",", ":"))
        return json.dumps(config, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _idempotency_hash(key: str) -> str:
        return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def _request_fingerprint(amount: Decimal, currency: str, transaction_type: str,
                             ref_type: Optional[str], ref_id: Optional[str],
                             customer_id: Optional[str], method: Optional[str]) -> str:
        payload = {
            "amount": str(amount), "currency": currency,
            "transaction_type": transaction_type, "reference_type": ref_type,
            "reference_id": ref_id, "customer_id": customer_id, "payment_method": method,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

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

        gid = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_payment_gateways "
                "(id, tenant_id, gateway_name, gateway_type, config) "
                "VALUES (:id, :t, :name, :type, CAST(:config AS JSONB))"
            ),
            {
                "id": gid, "t": tenant_id, "name": gateway_name,
                "type": gateway_type, "config": self._serialize_gateway_config(config),
            },
        )
        self.db.commit()
        return {"gateway_id": gid, "message": f"Gateway {gateway_name} created"}

    def create_transaction(self, tenant_id, amount, currency="SAR", tx_type="payment",
                           ref_type=None, ref_id=None, customer_id=None, method=None,
                           idempotency_key: Optional[str] = None):
        amount_value = self._amount(amount)
        normalized_currency = self._currency(currency)
        transaction_type = str(tx_type or "payment").strip().lower()
        if transaction_type not in self._TRANSACTION_TYPES:
            raise ValueError("Unsupported transaction type")

        key = (idempotency_key or "").strip()
        key_hash = None
        fingerprint = None
        if key:
            if len(key) > 255:
                raise ValueError("Idempotency-Key must not exceed 255 characters")
            key_hash = self._idempotency_hash(key)
            fingerprint = self._request_fingerprint(
                amount_value, normalized_currency, transaction_type,
                ref_type, ref_id, customer_id, method,
            )
            existing = self.db.execute(
                text(
                    "SELECT id, status, idempotency_fingerprint FROM dbp_payment_transactions "
                    "WHERE tenant_id=:t AND idempotency_key_hash=:kh FOR UPDATE"
                ), {"t": tenant_id, "kh": key_hash}
            ).fetchone()
            if existing:
                if existing[2] != fingerprint:
                    raise ValueError("Idempotency-Key was already used with different payment parameters")
                return {"transaction_id": existing[0], "ref_number": None, "status": existing[1], "idempotent": True}

        tid = str(uuid.uuid4())
        ref_number = f"TXN-{secrets.token_hex(4).upper()}"
        try:
            self.db.execute(
                text(
                    "INSERT INTO dbp_payment_transactions "
                    "(id, tenant_id, transaction_type, amount, currency, status, reference_type, "
                    "reference_id, customer_id, payment_method, gateway_response, "
                    "idempotency_key_hash, idempotency_fingerprint) "
                    "VALUES (:id, :t, :type, :amt, :cur, 'pending', :rtype, :rid, :cid, :method, "
                    ":resp, :kh, :fp)"
                ),
                {
                    "id": tid, "t": tenant_id, "type": transaction_type,
                    "amt": amount_value, "cur": normalized_currency, "rtype": ref_type,
                    "rid": ref_id, "cid": customer_id, "method": method,
                    "resp": json.dumps({"ref_number": ref_number}),
                    "kh": key_hash, "fp": fingerprint,
                },
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            if key_hash:
                existing = self.db.execute(
                    text(
                        "SELECT id, status, idempotency_fingerprint FROM dbp_payment_transactions "
                        "WHERE tenant_id=:t AND idempotency_key_hash=:kh"
                    ), {"t": tenant_id, "kh": key_hash}
                ).fetchone()
                if existing:
                    if existing[2] != fingerprint:
                        raise ValueError("Idempotency-Key was already used with different payment parameters")
                    return {"transaction_id": existing[0], "ref_number": None, "status": existing[1], "idempotent": True}
            raise
        return {"transaction_id": tid, "ref_number": ref_number, "status": "pending", "idempotent": False}

    def complete_transaction(self, transaction_id, tenant_id, gateway_response=None):
        row = self.db.execute(
            text("SELECT id, status FROM dbp_payment_transactions WHERE id=:id AND tenant_id=:t FOR UPDATE"),
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
            {"id": transaction_id, "t": tenant_id, "resp": json.dumps(gateway_response or {})},
        )
        self.db.commit()
        return {"status": "completed", "transaction_id": transaction_id}

    def fail_transaction(self, transaction_id, tenant_id, reason=""):
        row = self.db.execute(
            text("SELECT id, status FROM dbp_payment_transactions WHERE id=:id AND tenant_id=:t FOR UPDATE"),
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
            text("SELECT * FROM dbp_payment_transactions WHERE id=:id AND tenant_id=:t FOR UPDATE"),
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
            ), {"ref": transaction_id, "t": tenant_id}
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
            ), {"id": refund_id, "t": tenant_id, "amt": refund_amount, "cur": row_dict["currency"], "ref": transaction_id}
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
        row = self.db.execute(text("SELECT * FROM dbp_payment_transactions WHERE id=:id AND tenant_id=:t"), {"id": transaction_id, "t": tenant_id}).fetchone()
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
            ), {"id": link_id, "t": tenant_id, "token": token, "amt": amount_value, "desc": description, "email": email, "hrs": str(hours)}
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
            ), {
                "id": tx["transaction_id"], "t": tenant_id,
                "resp": json.dumps({"bank_name": str(bank_name)[:120], "account_last4": str(account_number)[-4:], "transfer_reference": str(reference)[:120]}),
            }
        )
        self.db.commit()
        return tx

    def process_cash(self, tenant_id, amount, received_by=None):
        return self.create_transaction(tenant_id, amount, method="cash")

    def get_summary(self, tenant_id):
        total = self.db.execute(text("SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions WHERE tenant_id=:t AND status='completed' AND transaction_type='payment'"), {"t": tenant_id}).fetchone()[0]
        refunded = self.db.execute(text("SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions WHERE tenant_id=:t AND status='completed' AND transaction_type='refund'"), {"t": tenant_id}).fetchone()[0]
        pending = self.db.execute(text("SELECT COUNT(*) FROM dbp_payment_transactions WHERE tenant_id=:t AND status='pending'"), {"t": tenant_id}).fetchone()[0]
        return {"total_collected": float(total), "total_refunded": float(refunded), "net_amount": float(total - refunded), "pending_count": pending}
