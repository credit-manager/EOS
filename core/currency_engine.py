"""
EOS Multi-Currency Engine
Supports: Currency definitions, exchange rates, conversions, gain/loss tracking
"""
import uuid, json
from datetime import datetime, date
from sqlalchemy import text


class MultiCurrencyEngine:
    def __init__(self, db):
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_currencies ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, code TEXT NOT NULL, name_en TEXT NOT NULL, "
            "name_ar TEXT, symbol TEXT, decimal_places INT DEFAULT 2, is_base BOOLEAN DEFAULT FALSE, "
            "is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_exchange_rates ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, from_currency TEXT NOT NULL, to_currency TEXT NOT NULL, "
            "rate DECIMAL(20,8) NOT NULL, source TEXT DEFAULT 'manual', "
            "rate_date DATE NOT NULL, created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_currency_transactions ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, transaction_id TEXT, "
            "original_currency TEXT NOT NULL, original_amount DECIMAL(15,2) NOT NULL, "
            "base_currency TEXT NOT NULL, base_amount DECIMAL(15,2) NOT NULL, "
            "exchange_rate DECIMAL(20,8) NOT NULL, "
            "gain_loss DECIMAL(15,2) DEFAULT 0, "
            "created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.commit()

    def list_currencies(self, tenant_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_currencies WHERE tenant_id = :t AND is_active = TRUE ORDER BY code"
        ), {"t": tenant_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_currency(self, tenant_id, code, name, symbol=None, decimal_places=2, is_base=False):
        cid = str(uuid.uuid4())
        if is_base:
            self.db.execute(text(
                "UPDATE dbp_currencies SET is_base = FALSE WHERE tenant_id = :t"
            ), {"t": tenant_id})
        self.db.execute(text(
            "INSERT INTO dbp_currencies (id, tenant_id, code, name_en, symbol, decimal_places, is_base) "
            "VALUES (:id, :t, :code, :name, :sym, :dp, :base)"
        ), {"id": cid, "t": tenant_id, "code": code, "name": name,
             "sym": symbol, "dp": decimal_places, "base": is_base})
        self.db.commit()
        return {"currency_id": cid, "code": code, "message": f"Currency {code} created"}

    def get_base_currency(self, tenant_id):
        row = self.db.execute(text(
            "SELECT * FROM dbp_currencies WHERE tenant_id = :t AND is_base = TRUE"
        ), {"t": tenant_id}).fetchone()
        return dict(row._mapping) if row else None

    def set_exchange_rate(self, tenant_id, from_currency, to_currency, rate, source="manual", effective_date=None):
        eid = str(uuid.uuid4())
        eff_date = effective_date or date.today().isoformat()
        self.db.execute(text(
            "DELETE FROM dbp_exchange_rates "
            "WHERE tenant_id = :t AND from_currency = :fc AND to_currency = :tc"
        ), {"t": tenant_id, "fc": from_currency, "tc": to_currency})
        self.db.execute(text(
            "INSERT INTO dbp_exchange_rates "
            "(id, tenant_id, from_currency, to_currency, rate, source, rate_date) "
            "VALUES (:id, :t, :fc, :tc, :rate, :src, :eff)"
        ), {"id": eid, "t": tenant_id, "fc": from_currency, "tc": to_currency,
             "rate": float(rate), "src": source, "eff": eff_date})
        self.db.commit()
        return {"rate_id": eid, "rate": float(rate), "message": f"Rate {from_currency}/{to_currency} = {rate}"}

    def get_exchange_rate(self, tenant_id, from_currency, to_currency):
        if from_currency == to_currency:
            return 1.0
        row = self.db.execute(text(
            "SELECT rate FROM dbp_exchange_rates "
            "WHERE tenant_id = :t AND from_currency = :fc AND to_currency = :tc "
            "ORDER BY rate_date DESC LIMIT 1"
        ), {"t": tenant_id, "fc": from_currency, "tc": to_currency}).fetchone()
        return float(row[0]) if row else None

    def list_exchange_rates(self, tenant_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_exchange_rates WHERE tenant_id = :t "
            "ORDER BY from_currency, to_currency"
        ), {"t": tenant_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def convert(self, tenant_id, amount, from_currency, to_currency):
        rate = self.get_exchange_rate(tenant_id, from_currency, to_currency)
        if rate is None:
            return {"error": f"No exchange rate for {from_currency}/{to_currency}"}
        converted = float(amount) * rate
        return {
            "original_amount": float(amount),
            "original_currency": from_currency,
            "converted_amount": round(converted, 2),
            "to_currency": to_currency,
            "exchange_rate": rate
        }

    def record_currency_transaction(self, tenant_id, transaction_id, original_currency,
                                     original_amount, base_currency, exchange_rate):
        base_amount = float(original_amount) * float(exchange_rate)
        ctid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_currency_transactions "
            "(id, tenant_id, transaction_id, original_currency, original_amount, "
            "base_currency, base_amount, exchange_rate) "
            "VALUES (:id, :t, :tid, :oc, :oa, :bc, :ba, :er)"
        ), {"id": ctid, "t": tenant_id, "tid": transaction_id,
             "oc": original_currency, "oa": float(original_amount),
             "bc": base_currency, "ba": round(base_amount, 2), "er": float(exchange_rate)})
        self.db.commit()
        return {"currency_transaction_id": ctid, "base_amount": round(base_amount, 2)}

    def calculate_gain_loss(self, tenant_id, transaction_id, settlement_rate):
        row = self.db.execute(text(
            "SELECT * FROM dbp_currency_transactions WHERE transaction_id = :tid"
        ), {"tid": transaction_id}).fetchone()
        if not row:
            return {"error": "Currency transaction not found"}
        rd = dict(row._mapping)
        expected_base = float(rd["original_amount"]) * float(rd["exchange_rate"])
        actual_base = float(rd["original_amount"]) * float(settlement_rate)
        gain_loss = actual_base - expected_base
        self.db.execute(text(
            "UPDATE dbp_currency_transactions SET gain_loss = :gl WHERE id = :id"
        ), {"gl": round(gain_loss, 2), "id": rd["id"]})
        self.db.commit()
        return {
            "transaction_id": transaction_id,
            "expected_base": round(expected_base, 2),
            "actual_base": round(actual_base, 2),
            "gain_loss": round(gain_loss, 2),
            "is_gain": gain_loss > 0
        }

    def get_currency_summary(self, tenant_id):
        total_transactions = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_currency_transactions WHERE tenant_id = :t"
        ), {"t": tenant_id}).fetchone()[0]
        total_gain_loss = self.db.execute(text(
            "SELECT COALESCE(SUM(gain_loss),0) FROM dbp_currency_transactions WHERE tenant_id = :t"
        ), {"t": tenant_id}).fetchone()[0]
        currencies = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_currencies WHERE tenant_id = :t AND is_active = TRUE"
        ), {"t": tenant_id}).fetchone()[0]
        rates = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_exchange_rates WHERE tenant_id = :t"
        ), {"t": tenant_id}).fetchone()[0]
        return {
            "total_currencies": currencies,
            "total_rates": rates,
            "total_transactions": total_transactions,
            "total_gain_loss": float(total_gain_loss)
        }
