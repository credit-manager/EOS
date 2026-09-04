"""
EOS Customer Portal Engine
Self-service portal for customers to view invoices, quotes, orders, payments
"""
import hashlib
import secrets
import uuid

from sqlalchemy import text


class CustomerPortalEngine:
    def __init__(self, db):
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_portal_users ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, customer_id TEXT NOT NULL, "
            "email TEXT NOT NULL, password_hash TEXT NOT NULL, "
            "full_name TEXT, is_active BOOLEAN DEFAULT TRUE, "
            "last_login TIMESTAMP, created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_portal_sessions ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, "
            "session_token TEXT UNIQUE NOT NULL, "
            "expires_at TIMESTAMP NOT NULL, created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_portal_notifications ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, "
            "title TEXT NOT NULL, message TEXT, is_read BOOLEAN DEFAULT FALSE, "
            "link TEXT, created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.commit()

    def _hash_password(self, password):
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${h.hex()}"

    def _verify_password(self, password, stored):
        if '$' not in stored:
            return hashlib.sha256(password.encode()).hexdigest() == stored
        salt, h = stored.split('$', 1)
        new_h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return secrets.compare_digest(new_h.hex(), h)

    def register_portal_user(self, tenant_id, customer_id, email, password, full_name=None):
        uid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_portal_users (id, tenant_id, customer_id, email, password_hash, full_name) "
            "VALUES (:id, :t, :cid, :email, :pw, :name)"
        ), {"id": uid, "t": tenant_id, "cid": customer_id,
             "email": email, "pw": self._hash_password(password), "name": full_name})
        self.db.commit()
        return {"user_id": uid, "message": "Portal user registered"}

    def portal_login(self, tenant_id, email, password):
        row = self.db.execute(text(
            "SELECT * FROM dbp_portal_users WHERE tenant_id = :t AND email = :email AND is_active = TRUE"
        ), {"t": tenant_id, "email": email}).fetchone()
        if not row:
            return {"error": "Invalid credentials"}
        rd = dict(row._mapping)
        if not self._verify_password(password, rd["password_hash"]):
            return {"error": "Invalid credentials"}
        token = secrets.token_urlsafe(32)
        session_id = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_portal_sessions (id, tenant_id, user_id, session_token, expires_at) "
            "VALUES (:id, :t, :uid, :token, NOW() + INTERVAL '24 hours')"
        ), {"id": session_id, "t": tenant_id, "uid": rd["id"], "token": token})
        self.db.execute(text(
            "UPDATE dbp_portal_users SET last_login = NOW() WHERE id = :id"
        ), {"id": rd["id"]})
        self.db.commit()
        return {"session_token": token, "user_id": rd["id"], "full_name": rd["full_name"]}

    def get_portal_user(self, session_token):
        row = self.db.execute(text(
            "SELECT pu.* FROM dbp_portal_users pu "
            "JOIN dbp_portal_sessions ps ON pu.id = ps.user_id "
            "WHERE ps.session_token = :token AND ps.expires_at > NOW()"
        ), {"token": session_token}).fetchone()
        return dict(row._mapping) if row else None

    def get_customer_invoices(self, tenant_id, customer_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_trading_sales_invoices WHERE tenant_id = :t AND customer_id = :cid "
            "ORDER BY created_at DESC"
        ), {"t": tenant_id, "cid": customer_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_customer_orders(self, tenant_id, customer_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_trading_sales_orders WHERE tenant_id = :t AND customer_id = :cid "
            "ORDER BY created_at DESC"
        ), {"t": tenant_id, "cid": customer_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_customer_payments(self, tenant_id, customer_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_payment_transactions WHERE tenant_id = :t AND customer_id = :cid "
            "ORDER BY created_at DESC"
        ), {"t": tenant_id, "cid": customer_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_portal_notifications(self, user_id, unread_only=False):
        query = "SELECT * FROM dbp_portal_notifications WHERE user_id = :uid"
        params = {"uid": user_id}
        if unread_only:
            query += " AND is_read = FALSE"
        query += " ORDER BY created_at DESC LIMIT 50"
        rows = self.db.execute(text(query), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def mark_notification_read(self, notification_id):
        self.db.execute(text(
            "UPDATE dbp_portal_notifications SET is_read = TRUE WHERE id = :id"
        ), {"id": notification_id})
        self.db.commit()

    def get_portal_summary(self, tenant_id, customer_id):
        invoices = self.db.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(total),0) FROM dbp_trading_sales_invoices "
            "WHERE tenant_id = :t AND customer_id = :cid"
        ), {"t": tenant_id, "cid": customer_id}).fetchone()
        orders = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_trading_sales_orders WHERE tenant_id = :t AND customer_id = :cid"
        ), {"t": tenant_id, "cid": customer_id}).fetchone()
        payments = self.db.execute(text(
            "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
            "WHERE tenant_id = :t AND customer_id = :cid AND status = 'completed'"
        ), {"t": tenant_id, "cid": customer_id}).fetchone()
        return {
            "total_invoices": invoices[0] if invoices else 0,
            "total_invoice_amount": float(invoices[1]) if invoices else 0,
            "total_orders": orders[0] if orders else 0,
            "total_payments": float(payments[0]) if payments else 0,
        }
