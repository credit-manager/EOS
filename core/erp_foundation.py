"""
P21 ERP Foundation Engine
  Company, Branch, Department, Fiscal Year, Currency, Cost Center CRUD
"""
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class ERPFoundationEngine:
    """ERP Foundation — organizational structure management."""

    def __init__(self, db: Session):
        self.db = db

    def _verify_company_tenant(self, company_id: str, tenant_id: str):
        """Raise 403 unless the company belongs to the calling tenant.

        P80.5D FIX: prevents a tenant from creating branches/departments/fiscal
        years/cost centers under a company owned by another tenant, and from
        updating another tenant's company.
        """
        row = self.db.execute(text(
            "SELECT tenant_id FROM dbp_companies WHERE id = :cid"
        ), {"cid": company_id}).fetchone()
        if not row or row[0] != tenant_id:
            from fastapi import HTTPException
            raise HTTPException(403, detail="Company does not belong to your tenant")

    # ── COMPANY ──

    def create_company(self, tenant_id: str, code: str, name_en: str, **kw) -> str:
        existing = self.db.execute(text(
            "SELECT id FROM dbp_companies WHERE tenant_id = :tid AND code = :code"
        ), {"tid": tenant_id, "code": code}).fetchone()
        if existing:
            return None
        cid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_companies (id, tenant_id, code, name_en, name_ar, legal_name, "
            "tax_number, commercial_registration, address, city, country, phone, email, "
            "base_currency, fiscal_year_start_month) "
            "VALUES (:id, :tid, :code, :ne, :na, :ln, :tn, :cr, :addr, :city, :country, "
            ":phone, :email, :bc, :fysm)"
        ), {"id": cid, "tid": tenant_id, "code": code, "ne": name_en,
            "na": kw.get("name_ar"), "ln": kw.get("legal_name"),
            "tn": kw.get("tax_number"), "cr": kw.get("commercial_registration"),
            "addr": kw.get("address"), "city": kw.get("city"),
            "country": kw.get("country", "SA"), "phone": kw.get("phone"),
            "email": kw.get("email"), "bc": kw.get("base_currency", "SAR"),
            "fysm": kw.get("fiscal_year_start_month", 1)})
        self.db.flush()
        return cid

    def get_companies(self, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, code, name_en, name_ar, country, base_currency, is_active, created_at "
            "FROM dbp_companies WHERE tenant_id = :tid ORDER BY code"
        ), {"tid": tenant_id}).fetchall()
        return [{"id": r[0], "code": r[1], "name_en": r[2], "name_ar": r[3],
                 "country": r[4], "base_currency": r[5], "is_active": bool(r[6]),
                 "created_at": r[7].isoformat() if r[7] else None} for r in rows]

    def get_company(self, company_id: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
        conditions = ["id = :cid"]
        params: Dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        where = " AND ".join(conditions)
        r = self.db.execute(text(
            f"SELECT id, tenant_id, code, name_en, name_ar, legal_name, tax_number, "
            f"commercial_registration, address, city, country, phone, email, "
            f"base_currency, fiscal_year_start_month, is_active, created_at "
            f"FROM dbp_companies WHERE {where}"
        ), params).fetchone()
        if not r:
            return None
        return {"id": r[0], "tenant_id": r[1], "code": r[2], "name_en": r[3],
                "name_ar": r[4], "legal_name": r[5], "tax_number": r[6],
                "commercial_registration": r[7], "address": r[8],
                "city": r[9], "country": r[10], "phone": r[11], "email": r[12],
                "base_currency": r[13], "fiscal_year_start_month": r[14],
                "is_active": bool(r[15]),
                "created_at": r[16].isoformat() if r[16] else None}

    def update_company(self, company_id: str, data: Dict[str, Any], tenant_id: str) -> bool:
        allowed = {"name_en", "name_ar", "legal_name", "tax_number", "address",
                    "city", "country", "phone", "email", "base_currency", "is_active"}
        sets = []
        params: Dict[str, Any] = {"cid": company_id, "tid": tenant_id}
        for k, v in data.items():
            if k in allowed:
                sets.append(f"{k} = :{k}")
                params[k] = v
        if not sets:
            return False
        self.db.execute(text(f"UPDATE dbp_companies SET {', '.join(sets)} "
                             f"WHERE id = :cid AND tenant_id = :tid"), params)
        self.db.flush()
        return True

    # ── BRANCH ──

    def create_branch(self, tenant_id: str, company_id: str, code: str, name_en: str, **kw) -> str:
        self._verify_company_tenant(company_id, tenant_id)
        bid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_branches (id, tenant_id, company_id, code, name_en, name_ar, "
            "address, city, country, phone, is_headquarters) "
            "VALUES (:id, :tid, :cid, :code, :ne, :na, :addr, :city, :country, :phone, :hq)"
        ), {"id": bid, "tid": tenant_id, "cid": company_id, "code": code,
            "ne": name_en, "na": kw.get("name_ar"), "addr": kw.get("address"),
            "city": kw.get("city"), "country": kw.get("country"),
            "phone": kw.get("phone"), "hq": kw.get("is_headquarters", False)})
        self.db.flush()
        return bid

    def get_branches(self, company_id: str, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, code, name_en, name_ar, city, is_headquarters, is_active "
            "FROM dbp_branches WHERE company_id = :cid AND tenant_id = :t ORDER BY code"
        ), {"cid": company_id, "t": tenant_id}).fetchall()
        return [{"id": r[0], "code": r[1], "name_en": r[2], "name_ar": r[3],
                 "city": r[4], "is_headquarters": bool(r[5]), "is_active": bool(r[6])}
                for r in rows]

    # ── DEPARTMENT ──

    def create_department(self, tenant_id: str, company_id: str, code: str, name_en: str, **kw) -> str:
        self._verify_company_tenant(company_id, tenant_id)
        did = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_departments (id, tenant_id, company_id, parent_id, branch_id, "
            "code, name_en, name_ar, cost_center_id, manager_id) "
            "VALUES (:id, :tid, :cid, :pid, :brid, :code, :ne, :na, :ccid, :mid)"
        ), {"id": did, "tid": tenant_id, "cid": company_id,
            "pid": kw.get("parent_id"), "brid": kw.get("branch_id"),
            "code": code, "ne": name_en, "na": kw.get("name_ar"),
            "ccid": kw.get("cost_center_id"), "mid": kw.get("manager_id")})
        self.db.flush()
        return did

    def get_departments(self, company_id: str, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, parent_id, branch_id, code, name_en, name_ar, manager_id, is_active "
            "FROM dbp_departments WHERE company_id = :cid AND tenant_id = :t ORDER BY code"
        ), {"cid": company_id, "t": tenant_id}).fetchall()
        return [{"id": r[0], "parent_id": r[1], "branch_id": r[2], "code": r[3],
                 "name_en": r[4], "name_ar": r[5], "manager_id": r[6],
                 "is_active": bool(r[7])} for r in rows]

    def get_department_tree(self, company_id: str, tenant_id: str) -> List[Dict]:
        """Get departments as nested tree."""
        all_deps = self.get_departments(company_id, tenant_id)
        by_parent = {}
        for d in all_deps:
            pid = d["parent_id"] or "root"
            by_parent.setdefault(pid, []).append(d)

        def build(parent_id):
            return [
                {**d, "children": build(d["id"])}
                for d in by_parent.get(parent_id, [])
            ]

        return build("root")

    # ── FISCAL YEAR ──

    def create_fiscal_year(self, tenant_id: str, company_id: str, code: str,
                           name: str, start_date: str, end_date: str) -> str:
        self._verify_company_tenant(company_id, tenant_id)
        fyid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_fiscal_years (id, tenant_id, company_id, code, name, start_date, end_date) "
            "VALUES (:id, :tid, :cid, :code, :name, :sd, :ed)"
        ), {"id": fyid, "tid": tenant_id, "cid": company_id,
            "code": code, "name": name, "sd": start_date, "ed": end_date})
        self.db.flush()
        return fyid

    def get_fiscal_years(self, company_id: str, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, code, name, start_date, end_date, is_closed, is_active "
            "FROM dbp_fiscal_years WHERE company_id = :cid AND tenant_id = :t ORDER BY start_date DESC"
        ), {"cid": company_id, "t": tenant_id}).fetchall()
        return [{"id": r[0], "code": r[1], "name": r[2],
                 "start_date": str(r[3]) if r[3] else None,
                 "end_date": str(r[4]) if r[4] else None,
                 "is_closed": bool(r[5]), "is_active": bool(r[6])} for r in rows]

    def close_fiscal_year(self, fy_id: str, tenant_id: str) -> bool:
        result = self.db.execute(text(
            "UPDATE dbp_fiscal_years SET is_closed = true "
            "WHERE id = :fid AND tenant_id = :t AND is_closed = false"
        ), {"fid": fy_id, "t": tenant_id})
        self.db.flush()
        return result.rowcount > 0

    # ── CURRENCY ──

    def get_currencies(self, tenant_id: Optional[str] = None) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, code, name_en, name_ar, symbol, decimal_places, is_base "
            "FROM dbp_currencies WHERE (tenant_id = :tid OR tenant_id IS NULL) AND is_active = true "
            "ORDER BY code"
        ), {"tid": tenant_id}).fetchall()
        return [{"id": r[0], "code": r[1], "name_en": r[2], "name_ar": r[3],
                 "symbol": r[4], "decimal_places": r[5], "is_base": bool(r[6])}
                for r in rows]

    # ── COST CENTER ──

    def create_cost_center(self, tenant_id: str, company_id: str, code: str, name_en: str, **kw) -> str:
        self._verify_company_tenant(company_id, tenant_id)
        ccid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_cost_centers (id, tenant_id, company_id, code, name_en, name_ar, parent_id, budget_amount) "
            "VALUES (:id, :tid, :cid, :code, :ne, :na, :pid, :ba)"
        ), {"id": ccid, "tid": tenant_id, "cid": company_id, "code": code,
            "ne": name_en, "na": kw.get("name_ar"),
            "pid": kw.get("parent_id"), "ba": kw.get("budget_amount", 0)})
        self.db.flush()
        return ccid

    def get_cost_centers(self, company_id: str, tenant_id: str) -> List[Dict]:
        rows = self.db.execute(text(
            "SELECT id, parent_id, code, name_en, name_ar, budget_amount, is_active "
            "FROM dbp_cost_centers WHERE company_id = :cid AND tenant_id = :t ORDER BY code"
        ), {"cid": company_id, "t": tenant_id}).fetchall()
        return [{"id": r[0], "parent_id": r[1], "code": r[2], "name_en": r[3],
                 "name_ar": r[4], "budget_amount": float(r[5]) if r[5] else 0,
                 "is_active": bool(r[6])} for r in rows]
