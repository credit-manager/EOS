"""EOS Payment Gateway Engine.

Supports Stripe, Mada, STC Pay, bank transfer and cash while keeping all
mutations tenant-scoped and making critical payment writes idempotent.
"""
import json
import os
import secrets
import uuid
from decimal import Decimal

from sqlalchemy import text

from core.reliability import IdempotencyStore, OutboxStore


class PaymentGatewayEngine:
    def __init__(self, db):
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        if os.getenv("EOS_AUTH_MODE", "test").lower() == "production" or os.getenv("EOS_RUNTIME_SCHEMA", "true").lower() != "true":
            return
        self.db.execute(text("CREATE TABLE IF NOT EXISTS dbp_payment_gateways (id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, tenant_id TEXT NOT NULL, gateway_name TEXT NOT NULL, gateway_type TEXT NOT NULL, is_active BOOLEAN DEFAULT TRUE, config JSONB DEFAULT '{}', created_at TIMESTAMP DEFAULT NOW())"))
        self.db.execute(text("CREATE TABLE IF NOT EXISTS dbp_payment_transactions (id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, tenant_id TEXT NOT NULL, gateway_id TEXT, transaction_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, currency TEXT DEFAULT 'SAR', status TEXT DEFAULT 'pending', reference_type TEXT, reference_id TEXT, customer_id TEXT, payment_method TEXT, gateway_response JSONB DEFAULT '{}', created_at TIMESTAMP DEFAULT NOW(), completed_at TIMESTAMP)"))
        self.db.execute(text("CREATE TABLE IF NOT EXISTS dbp_payment_links (id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, tenant_id TEXT NOT NULL, link_token TEXT UNIQUE NOT NULL, amount DECIMAL(15,2) NOT NULL, currency TEXT DEFAULT 'SAR', description TEXT, customer_email TEXT, status TEXT DEFAULT 'active', expires_at TIMESTAMP, created_at TIMESTAMP DEFAULT NOW())"))
        self.db.execute(text("CREATE TABLE IF NOT EXISTS dbp_idempotency_keys (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, key TEXT NOT NULL, request_hash TEXT NOT NULL, status_code INTEGER, response_body TEXT, created_at TIMESTAMP DEFAULT NOW(), completed_at TIMESTAMP, UNIQUE(tenant_id,key))"))
        self.db.execute(text("CREATE TABLE IF NOT EXISTS dbp_outbox_events (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, event_type TEXT NOT NULL, aggregate_type TEXT NOT NULL, aggregate_id TEXT NOT NULL, payload JSONB NOT NULL, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, available_at TIMESTAMP DEFAULT NOW(), processed_at TIMESTAMP, last_error TEXT, created_at TIMESTAMP DEFAULT NOW(), UNIQUE(tenant_id,event_type,aggregate_type,aggregate_id))"))
        self.db.commit()

    def list_gateways(self, tenant_id):
        rows = self.db.execute(text("SELECT * FROM dbp_payment_gateways WHERE tenant_id = :t ORDER BY created_at DESC"), {"t": tenant_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_gateway(self, tenant_id, name, gw_type, config=None):
        gid = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO dbp_payment_gateways (id, tenant_id, gateway_name, gateway_type, config) VALUES (:id, :t, :name, :type, :config)"), {"id": gid, "t": tenant_id, "name": name, "type": gw_type, "config": json.dumps(config or {})})
        self.db.commit()
        return {"gateway_id": gid, "message": f"Gateway {name} created"}

    def create_transaction(self, tenant_id, amount, currency="SAR", tx_type="payment", ref_type=None, ref_id=None, customer_id=None, method=None, idempotency_key=None, gateway_metadata=None):
        if amount is None or float(amount) <= 0:
            raise ValueError("Payment amount must be positive")
        currency = (currency or "SAR").upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("Currency must be a 3-letter ISO code")
        metadata = gateway_metadata or {}
        idem = IdempotencyStore(self.db)
        request_payload = {"amount": str(amount), "currency": currency, "transaction_type": tx_type, "reference_type": ref_type, "reference_id": ref_id, "customer_id": customer_id, "payment_method": method, "gateway_metadata": metadata}
        if idempotency_key:
            replay = idem.reserve(tenant_id, idempotency_key, request_payload)
            if replay is not None:
                body = replay.get("response_body") or {}
                if isinstance(body, dict):
                    body["idempotent_replay"] = True
                return body
        tid = str(uuid.uuid4())
        ref_number = f"TXN-{secrets.token_hex(4).upper()}"
        response = {"transaction_id": tid, "ref_number": ref_number, "status": "pending"}
        gateway_response = {"ref_number": ref_number}
        if metadata:
            gateway_response["metadata"] = metadata
        try:
            self.db.execute(text("INSERT INTO dbp_payment_transactions (id, tenant_id, transaction_type, amount, currency, status, reference_type, reference_id, customer_id, payment_method, gateway_response) VALUES (:id, :t, :type, :amt, :cur, 'pending', :rtype, :rid, :cid, :method, :resp)"), {"id": tid, "t": tenant_id, "type": tx_type, "amt": float(amount), "cur": currency, "rtype": ref_type, "rid": ref_id, "cid": customer_id, "method": method, "resp": json.dumps(gateway_response)})
            OutboxStore(self.db).enqueue(tenant_id, "payment.created", "payment_transaction", tid, response)
            if idempotency_key:
                idem.complete(tenant_id, idempotency_key, 200, response)
            self.db.commit()
            return response
        except Exception:
            self.db.rollback()
            raise

    def complete_transaction(self, transaction_id, tenant_id, gateway_response=None, idempotency_key=None):
        request_payload = {"transaction_id": transaction_id, "gateway_response": gateway_response or {}, "operation": "complete"}
        idem = IdempotencyStore(self.db)
        if idempotency_key:
            replay = idem.reserve(tenant_id, idempotency_key, request_payload)
            if replay is not None:
                return replay.get("response_body") or {}
        try:
            row = self.db.execute(text("SELECT id, status FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t FOR UPDATE"), {"id": transaction_id, "t": tenant_id}).fetchone()
            if not row:
                raise LookupError("Transaction not found")
            if row.status == "completed":
                response = {"status": "completed", "transaction_id": transaction_id}
            elif row.status == "failed":
                raise ValueError("Failed transaction cannot be completed")
            else:
                self.db.execute(text("UPDATE dbp_payment_transactions SET status='completed', completed_at=NOW(), gateway_response = gateway_response || :resp WHERE id = :id AND tenant_id = :t"), {"id": transaction_id, "t": tenant_id, "resp": json.dumps(gateway_response or {})})
                response = {"status": "completed", "transaction_id": transaction_id}
            if idempotency_key:
                idem.complete(tenant_id, idempotency_key, 200, response)
            self.db.commit()
            return response
        except Exception:
            self.db.rollback()
            raise

    def fail_transaction(self, transaction_id, tenant_id, reason="", idempotency_key=None):
        request_payload = {"transaction_id": transaction_id, "reason": reason, "operation": "fail"}
        idem = IdempotencyStore(self.db)
        if idempotency_key:
            replay = idem.reserve(tenant_id, idempotency_key, request_payload)
            if replay is not None:
                return replay.get("response_body") or {}
        try:
            row = self.db.execute(text("SELECT id, status FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t FOR UPDATE"), {"id": transaction_id, "t": tenant_id}).fetchone()
            if not row:
                raise LookupError("Transaction not found")
            if row.status == "completed":
                raise ValueError("Completed transaction cannot be failed")
            self.db.execute(text("UPDATE dbp_payment_transactions SET status='failed', gateway_response = gateway_response || :resp WHERE id = :id AND tenant_id = :t"), {"id": transaction_id, "t": tenant_id, "resp": json.dumps({"failure_reason": reason})})
            response = {"status": "failed", "transaction_id": transaction_id}
            if idempotency_key:
                idem.complete(tenant_id, idempotency_key, 200, response)
            self.db.commit()
            return response
        except Exception:
            self.db.rollback()
            raise

    def refund_transaction(self, transaction_id, tenant_id, amount=None, idempotency_key=None):
        row = self.db.execute(text("SELECT * FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t FOR UPDATE"), {"id": transaction_id, "t": tenant_id}).fetchone()
        if not row:
            return {"error": "Transaction not found"}
        row_dict = dict(row._mapping)
        if row_dict["transaction_type"] == "refund":
            return {"error": "Cannot refund a refund transaction"}
        if idempotency_key:
            idem = IdempotencyStore(self.db)
            replay = idem.reserve(tenant_id, idempotency_key, {"transaction_id": transaction_id, "amount": str(amount) if amount is not None else None})
            if replay is not None:
                body = replay.get("response_body") or {}
                if isinstance(body, dict):
                    body["idempotent_replay"] = True
                return body
        already_refunded = self.db.execute(text("SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions WHERE reference_type='payment' AND reference_id=:ref AND transaction_type='refund' AND tenant_id = :t"), {"ref": transaction_id, "t": tenant_id}).fetchone()[0]
        refundable = Decimal(str(row_dict["amount"] or 0)) - Decimal(str(already_refunded or 0))
        refund_amount = refundable if amount is None else Decimal(str(amount))
        if refund_amount <= 0:
            return {"error": "Nothing left to refund"}
        if refund_amount > refundable:
            return {"error": f"Refund amount {refund_amount} exceeds refundable {refundable} for this transaction"}
        refund_id = str(uuid.uuid4())
        response = {"refund_id": refund_id, "amount": float(refund_amount), "status": "completed"}
        try:
            self.db.execute(text("INSERT INTO dbp_payment_transactions (id, tenant_id, transaction_type, amount, currency, status, reference_type, reference_id) VALUES (:id, :t, 'refund', :amt, :cur, 'completed', 'payment', :ref)"), {"id": refund_id, "t": row_dict["tenant_id"], "amt": refund_amount, "cur": row_dict["currency"], "ref": transaction_id})
            OutboxStore(self.db).enqueue(tenant_id, "payment.refunded", "payment_transaction", transaction_id, response)
            if idempotency_key:
                IdempotencyStore(self.db).complete(tenant_id, idempotency_key, 200, response)
            self.db.commit()
            return response
        except Exception:
            self.db.rollback()
            raise

    def list_transactions(self, tenant_id, status=None, limit=50):
        query = "SELECT * FROM dbp_payment_transactions WHERE tenant_id = :t"
        params = {"t": tenant_id}
        if status:
            query += " AND status = :s"
            params["s"] = status
        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit
        rows = self.db.execute(text(query), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_transaction(self, transaction_id, tenant_id):
        row = self.db.execute(text("SELECT * FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t"), {"id": transaction_id, "t": tenant_id}).fetchone()
        return dict(row._mapping) if row else None

    def create_payment_link(self, tenant_id, amount, description=None, email=None, expires_hours=24, idempotency_key=None):
        if amount is None or float(amount) <= 0:
            raise ValueError("Payment amount must be positive")
        idem = IdempotencyStore(self.db)
        request_payload = {"amount": str(amount), "description": description, "customer_email": email, "expires_hours": expires_hours, "operation": "create_payment_link"}
        if idempotency_key:
            replay = idem.reserve(tenant_id, idempotency_key, request_payload)
            if replay is not None:
                return replay.get("response_body") or {}
        link_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        response = {"link_id": link_id, "payment_url": f"/pay/{token}", "token": token}
        try:
            self.db.execute(text("INSERT INTO dbp_payment_links (id, tenant_id, link_token, amount, description, customer_email, expires_at) VALUES (:id, :t, :token, :amt, :desc, :email, NOW() + (:hrs || ' hours')::interval)"), {"id": link_id, "t": tenant_id, "token": token, "amt": float(amount), "desc": description, "email": email, "hrs": str(expires_hours)})
            if idempotency_key:
                idem.complete(tenant_id, idempotency_key, 200, response)
            self.db.commit()
            return response
        except Exception:
            self.db.rollback()
            raise

    def process_bank_transfer(self, tenant_id, amount, bank_name, account_number, reference, idempotency_key=None):
        if not account_number:
            raise ValueError("Bank account number is required")
        if not bank_name:
            raise ValueError("Bank name is required")
        if not reference:
            raise ValueError("Bank transfer reference is required")
        metadata = {"bank_name": bank_name, "account_number_last4": account_number[-4:], "reference": reference}
        return self.create_transaction(tenant_id, amount, method="bank_transfer", ref_type="bank_transfer", ref_id=reference, idempotency_key=idempotency_key, gateway_metadata=metadata)

    def process_cash(self, tenant_id, amount, received_by=None, idempotency_key=None):
        metadata = {"received_by": received_by} if received_by else None
        return self.create_transaction(tenant_id, amount, method="cash", idempotency_key=idempotency_key, gateway_metadata=metadata)

    def get_summary(self, tenant_id):
        total = self.db.execute(text("SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions WHERE tenant_id = :t AND status = 'completed' AND transaction_type = 'payment'"), {"t": tenant_id}).fetchone()[0]
        refunded = self.db.execute(text("SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions WHERE tenant_id = :t AND status = 'completed' AND transaction_type = 'refund'"), {"t": tenant_id}).fetchone()[0]
        pending = self.db.execute(text("SELECT COUNT(*) FROM dbp_payment_transactions WHERE tenant_id = :t AND status = 'pending'"), {"t": tenant_id}).fetchone()[0]
        return {"total_collected": float(total), "total_refunded": float(refunded), "net_amount": float(total - refunded), "pending_count": pending}
