"""
P22 Accounting Engine — Chart of Accounts, Journal Entries, Double-Entry Bookkeeping, GL, Trial Balance
"""
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal


class AccountingEngine:
    """Double-entry accounting engine with strict tenant/company ownership."""

    ACCOUNT_TYPES = {
        "asset", "liability", "equity", "revenue", "expense",
    }

    JOURNAL_ENTRY_TYPES = {
        "standard", "adjusting", "closing", "opening", "reversing",
    }

    def __init__(self, db: Session):
        self.db = db

    def _verify_company_tenant(self, company_id: str, tenant_id: str):
        """Raise 403 unless the company belongs to the calling tenant."""
        row = self.db.execute(text(
            "SELECT tenant_id FROM dbp_companies WHERE id = :cid"
        ), {"cid": company_id}).fetchone()
        if not row or row[0] != tenant_id:
            from fastapi import HTTPException
            raise HTTPException(403, detail="Company does not belong to your tenant")

    def _verify_account_tenant(self, account_id: str, tenant_id: str, company_id: str):
        """Raise 403 unless an account belongs to the same tenant and company."""
        row = self.db.execute(text(
            "SELECT tenant_id, company_id FROM dbp_accounts WHERE id = :aid"
        ), {"aid": account_id}).fetchone()
        if not row or row[0] != tenant_id or str(row[1]) != str(company_id):
            from fastapi import HTTPException
            raise HTTPException(404, detail="Account not found")

    # ── CHART OF ACCOUNTS ──

    def create_account(self, tenant_id: str, company_id: str, code: str, name_en: str,
                       account_type: str, **kw) -> Optional[str]:
        if account_type not in self.ACCOUNT_TYPES:
            return None
        self._verify_company_tenant(company_id, tenant_id)
        existing = self.db.execute(text(
            "SELECT id FROM dbp_accounts WHERE tenant_id = :tid AND company_id = :cid AND code = :code"
        ), {"tid": tenant_id, "cid": company_id, "code": code}).fetchone()
        if existing:
            return None

        aid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_accounts (id, tenant_id, company_id, code, name_en, name_ar, "
            "account_type, parent_id, currency_code, opening_balance, description) "
            "VALUES (:id, :tid, :cid, :code, :ne, :na, :at, :pid, :cc, :ob, :desc)"
        ), {"id": aid, "tid": tenant_id, "cid": company_id, "code": code,
            "ne": name_en, "na": kw.get("name_ar"), "at": account_type,
            "pid": kw.get("parent_id"), "cc": kw.get("currency_code", "SAR"),
            "ob": kw.get("opening_balance", 0), "desc": kw.get("description")})
        self.db.flush()
        return aid

    def get_accounts(self, company_id: str, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, parent_id, code, name_en, name_ar, account_type, "
            "currency_code, is_active, current_balance, opening_balance "
            "FROM dbp_accounts WHERE company_id = :cid AND tenant_id = :t ORDER BY code"
        ), {"cid": company_id, "t": tenant_id}).fetchall()
        return [{"id": r[0], "parent_id": r[1], "code": r[2], "name_en": r[3],
                 "name_ar": r[4], "account_type": r[5], "currency_code": r[6],
                 "is_active": bool(r[7]), "current_balance": float(r[8]) if r[8] else 0,
                 "opening_balance": float(r[9]) if r[9] else 0} for r in rows]

    def get_account_tree(self, company_id: str, tenant_id: str) -> List[Dict]:
        accounts = self.get_accounts(company_id, tenant_id)
        by_parent = {}
        for a in accounts:
            pid = a["parent_id"] or "root"
            by_parent.setdefault(pid, []).append(a)

        def build(parent_id):
            return [{**a, "children": build(a["id"])} for a in by_parent.get(parent_id, [])]
        return build("root")

    # ── JOURNAL ENTRIES ──

    def create_journal_entry(self, tenant_id: str, company_id: str,
                             entry_date: str, entry_type: str,
                             description: str = None, reference: str = None,
                             fiscal_year_id: str = None,
                             created_by: str = None) -> Optional[str]:
        if entry_type not in self.JOURNAL_ENTRY_TYPES:
            return None
        self._verify_company_tenant(company_id, tenant_id)

        entry_number = self._next_entry_number(tenant_id, company_id)

        jeid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_journal_entries (id, tenant_id, company_id, fiscal_year_id, "
            "entry_number, entry_date, entry_type, description, reference, created_by) "
            "VALUES (:id, :tid, :cid, :fyid, :en, :ed, :et, :desc, :ref, :cb)"
        ), {"id": jeid, "tid": tenant_id, "cid": company_id,
            "fyid": fiscal_year_id, "en": entry_number, "ed": entry_date,
            "et": entry_type, "desc": description, "ref": reference, "cb": created_by})
        self.db.flush()
        return jeid

    def add_journal_line(self, journal_entry_id: str, account_id: str, tenant_id: str,
                         debit: float = 0, credit: float = 0,
                         description: str = None,
                         cost_center_id: str = None) -> Optional[str]:
        if debit < 0 or credit < 0 or (debit == 0 and credit == 0):
            return None

        # Resolve both ownership dimensions from the parent entry before the
        # insert.  The tenant_id is explicitly persisted because journal lines
        # are independently RLS-protected and their tenant_id is NOT NULL.
        parent = self.db.execute(text(
            "SELECT tenant_id, company_id FROM dbp_journal_entries WHERE id = :jid"
        ), {"jid": journal_entry_id}).fetchone()
        if not parent or parent[0] != tenant_id:
            from fastapi import HTTPException
            raise HTTPException(404, detail="Journal entry not found")
        company_id = parent[1]
        self._verify_account_tenant(account_id, tenant_id, company_id)

        lid = str(uuid.uuid4())
        max_order = self.db.execute(text(
            "SELECT MAX(line_order) FROM dbp_journal_lines WHERE journal_entry_id = :jid"
        ), {"jid": journal_entry_id}).scalar() or 0

        self.db.execute(text(
            "INSERT INTO dbp_journal_lines "
            "(id, tenant_id, journal_entry_id, account_id, debit, credit, description, cost_center_id, line_order) "
            "VALUES (:id, :tid, :jid, :aid, :dr, :cr, :desc, :ccid, :lo)"
        ), {"id": lid, "tid": tenant_id, "jid": journal_entry_id, "aid": account_id,
            "dr": debit, "cr": credit, "desc": description,
            "ccid": cost_center_id, "lo": max_order + 1})
        self.db.flush()
        return lid

    def post_journal_entry(self, je_id: str, tenant_id: str) -> Dict[str, Any]:
        """Post a journal entry (validate balance, update GL)."""
        entry = self.db.execute(text(
            "SELECT id, status, company_id FROM dbp_journal_entries "
            "WHERE id = :jid AND tenant_id = :t FOR UPDATE"
        ), {"jid": je_id, "t": tenant_id}).fetchone()

        if not entry:
            return {"success": False, "error": "Entry not found"}
        if entry[1] != "draft":
            return {"success": False, "error": f"Cannot post entry in '{entry[1]}' status"}

        lines = self.db.execute(text(
            "SELECT id, account_id, debit, credit FROM dbp_journal_lines "
            "WHERE journal_entry_id = :jid AND tenant_id = :t ORDER BY line_order"
        ), {"jid": je_id, "t": tenant_id}).fetchall()

        if not lines:
            return {"success": False, "error": "No lines in journal entry"}

        total_debit = sum(Decimal(str(l[2] or 0)) for l in lines)
        total_credit = sum(Decimal(str(l[3] or 0)) for l in lines)

        if abs(total_debit - total_credit) > Decimal("0.001"):
            return {"success": False, "error": f"Entry not balanced: debit={total_debit}, credit={total_credit}"}

        # Update GL balances only for accounts owned by the same tenant and
        # company as the journal entry.
        for line in lines:
            aid = line[1]
            dr = float(line[2])
            cr = float(line[3])
            self.db.execute(text(
                "UPDATE dbp_accounts SET current_balance = current_balance + :dr - :cr "
                "WHERE id = :aid AND tenant_id = :t AND company_id = :cid"
            ), {"aid": aid, "dr": dr, "cr": cr, "t": tenant_id, "cid": entry[2]})

        # Mark posted
        self.db.execute(text(
            "UPDATE dbp_journal_entries SET status='posted', is_posted=true, "
            "posted_at=NOW(), total_debit=:td, total_credit=:tc WHERE id = :jid AND tenant_id = :t"
        ), {"jid": je_id, "t": tenant_id, "td": total_debit, "tc": total_credit})
        self.db.flush()

        return {"success": True, "total_debit": float(total_debit), "total_credit": float(total_credit),
                "lines_count": len(lines)}

    def get_journal_entry(self, je_id: str, tenant_id: str) -> Optional[Dict]:
        r = self.db.execute(text(
            "SELECT id, entry_number, entry_date, entry_type, description, reference, "
            "status, total_debit, total_credit, is_posted, created_by, created_at "
            "FROM dbp_journal_entries WHERE id = :jid AND tenant_id = :t"
        ), {"jid": je_id, "t": tenant_id}).fetchone()
        if not r:
            return None

        lines = self.db.execute(text(
            "SELECT l.id, l.account_id, a.code, a.name_en, l.debit, l.credit, "
            "l.description, l.cost_center_id "
            "FROM dbp_journal_lines l "
            "LEFT JOIN dbp_accounts a ON l.account_id = a.id "
            "WHERE l.journal_entry_id = :jid AND l.tenant_id = :t ORDER BY l.line_order"
        ), {"jid": je_id, "t": tenant_id}).fetchall()

        return {
            "id": r[0], "entry_number": r[1],
            "entry_date": str(r[2]) if r[2] else None,
            "entry_type": r[3], "description": r[4], "reference": r[5],
            "status": r[6], "total_debit": float(r[7]) if r[7] else 0,
            "total_credit": float(r[8]) if r[8] else 0,
            "is_posted": bool(r[9]), "created_by": r[10],
            "created_at": r[11].isoformat() if r[11] else None,
            "lines": [
                {"id": l[0], "account_id": l[1], "account_code": l[2],
                 "account_name": l[3], "debit": float(l[4]) if l[4] else 0,
                 "credit": float(l[5]) if l[5] else 0,
                 "description": l[6], "cost_center_id": l[7]}
                for l in lines
            ],
        }

    def list_journal_entries(self, company_id: str, tenant_id: str, status: Optional[str] = None,
                             limit: int = 50, offset: int = 0) -> List[Dict]:
        conditions = ["company_id = :cid", "tenant_id = :t"]
        params: Dict[str, Any] = {"cid": company_id, "t": tenant_id, "lim": limit, "off": offset}
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = " AND ".join(conditions)

        rows = self.db.execute(text(
            f"SELECT id, entry_number, entry_date, entry_type, description, "
            f"status, total_debit, total_credit, created_at "
            f"FROM dbp_journal_entries WHERE {where} "
            f"ORDER BY entry_date DESC, entry_number DESC LIMIT :lim OFFSET :off"
        ), params).fetchall()

        return [{"id": r[0], "entry_number": r[1],
                 "entry_date": str(r[2]) if r[2] else None,
                 "entry_type": r[3], "description": r[4], "status": r[5],
                 "total_debit": float(r[6]) if r[6] else 0,
                 "total_credit": float(r[7]) if r[7] else 0,
                 "created_at": r[8].isoformat() if r[8] else None} for r in rows]

    # ── TRIAL BALANCE ──

    def get_trial_balance(self, company_id: str, tenant_id: str) -> Dict[str, Any]:
        accounts = self.db.execute(text(
            "SELECT id, code, name_en, account_type, current_balance "
            "FROM dbp_accounts WHERE company_id = :cid AND tenant_id = :t "
            "AND is_active = true ORDER BY code"
        ), {"cid": company_id, "t": tenant_id}).fetchall()

        result = []
        total_debit = 0
        total_credit = 0

        for a in accounts:
            balance = float(a[4]) if a[4] else 0
            if balance > 0:
                debit = balance
                credit = 0
            else:
                debit = 0
                credit = abs(balance)
            total_debit += debit
            total_credit += credit
            result.append({
                "account_id": a[0], "account_code": a[1], "account_name": a[2],
                "account_type": a[3], "debit": debit, "credit": credit,
            })

        return {
            "total_debit": total_debit,
            "total_credit": total_credit,
            "is_balanced": abs(total_debit - total_credit) < 0.001,
            "accounts": result,
        }

    # ── HELPERS ──

    def _next_entry_number(self, tenant_id: str, company_id: str) -> str:
        # Atomic per-tenant/company counter prevents duplicate entry numbers.
        from core.industry_security import uid
        seq_name = f"JE-{company_id}"
        row = self.db.execute(text(
            "INSERT INTO number_sequences "
            "(id, tenant_id, name, prefix, current_number, increment_by, padding, entity_type, is_active) "
            "VALUES (:id, :t, :name, 'JE', 1, 1, 6, 'journal_entry', true) "
            "ON CONFLICT (tenant_id, name) DO UPDATE "
            "SET current_number = number_sequences.current_number + number_sequences.increment_by "
            "RETURNING current_number, padding"
        ), {"id": uid(), "t": tenant_id, "name": seq_name}).fetchone()
        num = int(row[0]) if row else 1
        padding = int(row[1]) if row and row[1] else 6
        return f"JE-{num:0{padding}d}"
