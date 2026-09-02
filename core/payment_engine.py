"""
EOS Payment Gateway Engine
Supports: Stripe, Mada, STC Pay, Bank Transfer, Cash
"""
import json
import secrets
import uuid
from decimal import Decimal

from sqlalchemy import text


class PaymentGatewayEngine:
    def __init__(self, db):
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_payment_gateways ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, gateway_name TEXT NOT NULL, "
            "gateway_type TEXT NOT NULL, is_active BOOLEAN DEFAULT TRUE, "
            "config JSONB DEFAULT '{}', created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_payment_transactions ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, gateway_id TEXT, "
            "transaction_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, "
            "currency TEXT DEFAULT 'SAR', status TEXT DEFAULT 'pending', "
            "reference_type TEXT, reference_id TEXT, customer_id TEXT, "
            "payment_method TEXT, gateway_response JSONB DEFAULT '{}', "
            "created_at TIMESTAMP DEFAULT NOW(), completed_at TIMESTAMP)"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_payment_links ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, link_token TEXT UNIQUE NOT NULL, "
            "amount DECIMAL(15,2) NOT NULL, currency TEXT DEFAULT 'SAR', "
            "description TEXT, customer_email TEXT, status TEXT DEFAULT 'active', "
            "expires_at TIMESTAMP, created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.commit()

    def list_gateways(self, tenant_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_payment_gateways WHERE tenant_id = :t ORDER BY created_at DESC"
        ), {"t": tenant_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_gateway(self, tenant_id, name, gw_type, config=None):
        gid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_payment_gateways (id, tenant_id, gateway_name, gateway_type, config) "
            "VALUES (:id, :t, :name, :type, :config)"
        ), {"id": gid, "t": tenant_id, "name": name, "type": gw_type,
             "config": json.dumps(config or {})})
        self.db.commit()
        return {"gateway_id": gid, "message": f"Gateway {name} created"}

    def create_transaction(self, tenant_id, amount, currency="SAR", tx_type="payment",
                           ref_type=None, ref_id=None, customer_id=None, method=None):
        if amount is None or float(amount) <= 0:
            raise ValueError("Payment amount must be positive")
        tid = str(uuid.uuid4())
        ref_number = f"TXN-{secrets.token_hex(4).upper()}"
        self.db.execute(text(
            "INSERT INTO dbp_payment_transactions "
            "(id, tenant_id, transaction_type, amount, currency, status, reference_type, "
            "reference_id, customer_id, payment_method, gateway_response) "
            "VALUES (:id, :t, :type, :amt, :cur, 'pending', :rtype, :rid, :cid, :method, :resp)"
        ), {"id": tid, "t": tenant_id, "type": tx_type, "amt": float(amount),
             "cur": currency, "rtype": ref_type, "rid": ref_id, "cid": customer_id,
             "method": method, "resp": json.dumps({"ref_number": ref_number})})
        self.db.commit()
        return {"transaction_id": tid, "ref_number": ref_number, "status": "pending"}

    def complete_transaction(self, transaction_id, tenant_id, gateway_response=None):
        row = self.db.execute(text(
            "SELECT id FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t"
        ), {"id": transaction_id, "t": tenant_id}).fetchone()
        if not row:
            return {"error": "Transaction not found"}
        self.db.execute(text(
            "UPDATE dbp_payment_transactions SET status='completed', completed_at=NOW(), "
            "gateway_response = gateway_response || :resp WHERE id = :id AND tenant_id = :t"
        ), {"id": transaction_id, "t": tenant_id,
            "resp": json.dumps(gateway_response or {})})
        self.db.commit()
        return {"status": "completed", "transaction_id": transaction_id}

    def fail_transaction(self, transaction_id, tenant_id, reason=""):
        row = self.db.execute(text(
            "SELECT id FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t"
        ), {"id": transaction_id, "t": tenant_id}).fetchone()
        if not row:
            return {"error": "Transaction not found"}
        self.db.execute(text(
            "UPDATE dbp_payment_transactions SET status='failed', "
            "gateway_response = gateway_response || :resp WHERE id = :id AND tenant_id = :t"
        ), {"id": transaction_id, "t": tenant_id,
            "resp": json.dumps({"failure_reason": reason})})
        self.db.commit()
        return {"status": "failed", "transaction_id": transaction_id}

    def refund_transaction(self, transaction_id, tenant_id, amount=None):
        # Fixed H9: lock the transaction row against concurrent refunds,
        # preventing double-refund race conditions.
        # P80.5D FIX: scope every refund read/write to the caller's tenant so a
        # tenant cannot refund another tenant's transactions or drain its refundable.
        row = self.db.execute(text(
            "SELECT * FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t FOR UPDATE"
        ), {"id": transaction_id, "t": tenant_id}).fetchone()
        if not row:
            return {"error": "Transaction not found"}
        row_dict = dict(row._mapping)

        if row_dict["transaction_type"] == "refund":
            return {"error": "Cannot refund a refund transaction"}

        original_amount = row_dict["amount"]

        # Fixed H10: validate refund amount against the original transaction,
        # and subtract any amounts already refunded for this transaction to
        # prevent over-refunding.
        already_refunded = self.db.execute(text(
            "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
            "WHERE reference_type='payment' AND reference_id=:ref AND "
            "transaction_type='refund' AND tenant_id = :t"
        ), {"ref": transaction_id, "t": tenant_id}).fetchone()[0]

        refundable = Decimal(str(original_amount or 0)) - Decimal(str(already_refunded or 0))
        if amount is None:
            refund_amount = refundable
        else:
            refund_amount = Decimal(str(amount))

        if refund_amount <= 0:
            return {"error": "Nothing left to refund"}
        if refund_amount > refundable:
            return {"error": f"Refund amount {refund_amount} exceeds refundable {refundable} for this transaction"}

        refund_id = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_payment_transactions "
            "(id, tenant_id, transaction_type, amount, currency, status, reference_type, reference_id) "
            "VALUES (:id, :t, 'refund', :amt, :cur, 'completed', 'payment', :ref)"
        ), {"id": refund_id, "t": row_dict["tenant_id"], "amt": refund_amount,
             "cur": row_dict["currency"], "ref": transaction_id})
        self.db.commit()
        return {"refund_id": refund_id, "amount": float(refund_amount), "status": "completed"}

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
        row = self.db.execute(text(
            "SELECT * FROM dbp_payment_transactions WHERE id = :id AND tenant_id = :t"
        ), {"id": transaction_id, "t": tenant_id}).fetchone()
        return dict(row._mapping) if row else None

    def create_payment_link(self, tenant_id, amount, description=None, email=None, expires_hours=24):
        if amount is None or float(amount) <= 0:
            raise ValueError("Payment amount must be positive")
        link_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        self.db.execute(text(
            "INSERT INTO dbp_payment_links "
            "(id, tenant_id, link_token, amount, description, customer_email, expires_at) "
            "VALUES (:id, :t, :token, :amt, :desc, :email, NOW() + (:hrs || ' hours')::interval)"
        ), {"id": link_id, "t": tenant_id, "token": token, "amt": float(amount),
             "desc": description, "email": email, "hrs": str(expires_hours)})
        self.db.commit()
        return {"link_id": link_id, "payment_url": f"/pay/{token}", "token": token}

    def process_bank_transfer(self, tenant_id, amount, bank_name, account_number, reference):
        tx = self.create_transaction(tenant_id, amount, method="bank_transfer")
        self.db.execute(text(
            "UPDATE dbp_payment_transactions SET gateway_response = gateway_response || :resp WHERE id = :id"
        ), {"id": tx["transaction_id"], "resp": json.dumps({
            "bank_name": bank_name, "account_number": account_number,
            "transfer_reference": reference
        })})
        self.db.commit()
        return tx

    def process_cash(self, tenant_id, amount, received_by=None):
        return self.create_transaction(tenant_id, amount, method="cash")

    def get_summary(self, tenant_id):
        total = self.db.execute(text(
            "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
            "WHERE tenant_id = :t AND status = 'completed' AND transaction_type = 'payment'"
        ), {"t": tenant_id}).fetchone()[0]
        refunded = self.db.execute(text(
            "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
            "WHERE tenant_id = :t AND status = 'completed' AND transaction_type = 'refund'"
        ), {"t": tenant_id}).fetchone()[0]
        pending = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_payment_transactions "
            "WHERE tenant_id = :t AND status = 'pending'"
        ), {"t": tenant_id}).fetchone()[0]
        return {
            "total_collected": float(total),
            "total_refunded": float(refunded),
            "net_amount": float(total - refunded),
            "pending_count": pending
        }
