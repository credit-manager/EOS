"""
EOS Bank Reconciliation Engine
Links bank statements with payment transactions and accounting entries
"""
import uuid, json
from datetime import datetime
from sqlalchemy import text


class BankReconciliationEngine:
    def __init__(self, db):
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_bank_accounts ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, company_id TEXT, account_name TEXT NOT NULL, "
            "bank_name TEXT, account_number TEXT, iban TEXT, "
            "currency TEXT DEFAULT 'SAR', opening_balance DECIMAL(15,2) DEFAULT 0, "
            "current_balance DECIMAL(15,2) DEFAULT 0, is_active BOOLEAN DEFAULT TRUE, "
            "created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_bank_statements ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, bank_account_id TEXT NOT NULL, "
            "statement_date DATE NOT NULL, opening_balance DECIMAL(15,2) NOT NULL, "
            "closing_balance DECIMAL(15,2) NOT NULL, "
            "status TEXT DEFAULT 'pending', imported_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_bank_statement_lines ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, statement_id TEXT NOT NULL, "
            "transaction_date DATE NOT NULL, description TEXT, "
            "debit DECIMAL(15,2) DEFAULT 0, credit DECIMAL(15,2) DEFAULT 0, "
            "balance DECIMAL(15,2) DEFAULT 0, reference TEXT, "
            "matched_transaction_id TEXT, match_status TEXT DEFAULT 'unmatched', "
            "created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_reconciliation_logs ("
            "id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, "
            "tenant_id TEXT NOT NULL, bank_account_id TEXT NOT NULL, "
            "statement_id TEXT, action TEXT NOT NULL, "
            "details JSONB DEFAULT '{}', reconciled_by TEXT, "
            "created_at TIMESTAMP DEFAULT NOW())"
        ))
        self.db.commit()

    def list_bank_accounts(self, tenant_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_bank_accounts WHERE tenant_id = :t AND is_active = TRUE ORDER BY account_name"
        ), {"t": tenant_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_bank_account(self, tenant_id, account_name, bank_name=None,
                             account_number=None, iban=None, currency="SAR", opening_balance=0):
        bid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_bank_accounts "
            "(id, tenant_id, company_id, account_name, bank_name, account_number, iban, currency_code, current_balance) "
            "VALUES (:id, :t, :t, :name, :bank, :acct, :iban, :cur, :cb)"
        ), {"id": bid, "t": tenant_id, "name": account_name, "bank": bank_name,
             "acct": account_number, "iban": iban, "cur": currency,
             "cb": float(opening_balance)})
        self.db.commit()
        return {"account_id": bid, "message": f"Bank account {account_name} created"}

    def import_statement(self, tenant_id, bank_account_id, statement_date, opening_balance,
                          closing_balance, lines):
        sid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_bank_statements "
            "(id, tenant_id, bank_account_id, statement_date, opening_balance, closing_balance) "
            "VALUES (:id, :t, :bid, :sd, :ob, :cb)"
        ), {"id": sid, "t": tenant_id, "bid": bank_account_id,
             "sd": statement_date, "ob": float(opening_balance), "cb": float(closing_balance)})
        for line in lines:
            lid = str(uuid.uuid4())
            self.db.execute(text(
                "INSERT INTO dbp_bank_statement_lines "
                "(id, tenant_id, statement_id, transaction_date, description, debit, credit, balance, reference) "
                "VALUES (:id, :t, :sid, :td, :desc, :dr, :cr, :bal, :ref)"
            ), {"id": lid, "t": tenant_id, "sid": sid,
                 "td": line.get("date", statement_date), "desc": line.get("description", ""),
                 "dr": float(line.get("debit", 0)), "cr": float(line.get("credit", 0)),
                 "bal": float(line.get("balance", 0)), "ref": line.get("reference", "")})
        self.db.commit()
        return {"statement_id": sid, "lines_imported": len(lines)}

    def list_statements(self, tenant_id, bank_account_id=None):
        query = "SELECT * FROM dbp_bank_statements WHERE tenant_id = :t"
        params = {"t": tenant_id}
        if bank_account_id:
            query += " AND bank_account_id = :bid"
            params["bid"] = bank_account_id
        query += " ORDER BY statement_date DESC"
        rows = self.db.execute(text(query), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_statement_lines(self, statement_id):
        rows = self.db.execute(text(
            "SELECT * FROM dbp_bank_statement_lines WHERE statement_id = :sid ORDER BY transaction_date"
        ), {"sid": statement_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def auto_match(self, tenant_id, statement_id):
        lines = self.db.execute(text(
            "SELECT * FROM dbp_bank_statement_lines WHERE statement_id = :sid AND match_status = 'unmatched'"
        ), {"sid": statement_id}).fetchall()
        matched = 0
        for line in lines:
            ld = dict(line._mapping)
            amount = float(ld["credit"]) - float(ld["debit"])
            payment_rows = self.db.execute(text(
                "SELECT * FROM dbp_payment_transactions "
                "WHERE tenant_id = :t AND ABS(amount - :amt) < 0.01 AND status = 'completed' "
                "AND id NOT IN (SELECT matched_transaction_id FROM dbp_bank_statement_lines "
                "WHERE matched_transaction_id IS NOT NULL) LIMIT 1"
            ), {"t": tenant_id, "amt": abs(amount)}).fetchone()
            if payment_rows:
                self.db.execute(text(
                    "UPDATE dbp_bank_statement_lines SET matched_transaction_id = :mid, match_status = 'auto_matched' "
                    "WHERE id = :id"
                ), {"mid": dict(payment_rows._mapping)["id"], "id": ld["id"]})
                matched += 1
        self.db.commit()
        self._log(tenant_id, None, statement_id, "auto_match", {"matched": matched})
        return {"statement_id": statement_id, "matched": matched, "total_unmatched": len(lines)}

    def manual_match(self, tenant_id, line_id, transaction_id):
        self.db.execute(text(
            "UPDATE dbp_bank_statement_lines SET matched_transaction_id = :mid, match_status = 'manual_matched' "
            "WHERE id = :id"
        ), {"mid": transaction_id, "id": line_id})
        self.db.commit()
        self._log(tenant_id, None, None, "manual_match", {"line_id": line_id, "transaction_id": transaction_id})
        return {"line_id": line_id, "transaction_id": transaction_id, "status": "manual_matched"}

    def unreconcile(self, tenant_id, line_id):
        self.db.execute(text(
            "UPDATE dbp_bank_statement_lines SET matched_transaction_id = NULL, match_status = 'unmatched' "
            "WHERE id = :id"
        ), {"id": line_id})
        self.db.commit()
        return {"line_id": line_id, "status": "unmatched"}

    def get_reconciliation_status(self, tenant_id, bank_account_id):
        total = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_bank_statement_lines bl "
            "JOIN dbp_bank_statements bs ON bl.statement_id = bs.id "
            "WHERE bs.tenant_id = :t AND bs.bank_account_id = :bid"
        ), {"t": tenant_id, "bid": bank_account_id}).fetchone()[0]
        matched = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_bank_statement_lines bl "
            "JOIN dbp_bank_statements bs ON bl.statement_id = bs.id "
            "WHERE bs.tenant_id = :t AND bs.bank_account_id = :bid AND bl.match_status != 'unmatched'"
        ), {"t": tenant_id, "bid": bank_account_id}).fetchone()[0]
        return {
            "total_lines": total,
            "matched": matched,
            "unmatched": total - matched,
            "match_rate": round(matched / total * 100, 1) if total > 0 else 0
        }

    def get_unmatched_lines(self, tenant_id, bank_account_id):
        rows = self.db.execute(text(
            "SELECT bl.* FROM dbp_bank_statement_lines bl "
            "JOIN dbp_bank_statements bs ON bl.statement_id = bs.id "
            "WHERE bs.tenant_id = :t AND bs.bank_account_id = :bid AND bl.match_status = 'unmatched' "
            "ORDER BY bl.transaction_date"
        ), {"t": tenant_id, "bid": bank_account_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def _log(self, tenant_id, bank_account_id, statement_id, action, details):
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_reconciliation_logs "
            "(id, tenant_id, bank_account_id, statement_id, action, details) "
            "VALUES (:id, :t, :bid, :sid, :act, :det)"
        ), {"id": lid, "t": tenant_id, "bid": bank_account_id,
             "sid": statement_id, "act": action, "det": json.dumps(details)})
        self.db.commit()
