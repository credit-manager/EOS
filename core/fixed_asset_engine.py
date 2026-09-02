"""
P29 Fixed Assets Management Engine
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class FixedAssetEngine:
    """Fixed Assets: register, depreciation, transfers, disposal."""

    METHODS = {"straight_line", "declining_balance"}

    def __init__(self, db: Session):
        self.db = db

    def create_asset(self, tenant_id: str, company_id: str, name: str,
                     acquisition_date: str, acquisition_cost: float,
                     useful_life_years: int, **kw) -> str:
        aid = str(uuid.uuid4())
        acode = self._next_code(company_id, "FA")
        cost = float(acquisition_cost)
        self.db.execute(text(
            "INSERT INTO dbp_fixed_assets (id, tenant_id, company_id, asset_code, name, "
            "description, category, acquisition_date, acquisition_cost, salvage_value, "
            "useful_life_years, depreciation_method, book_value, location, employee_id, "
            "status, gl_account_id, depreciation_gl_account_id) "
            "VALUES (:id, :tid, :cid, :code, :name, :desc, :cat, :ad, :ac, :sv, "
            ":uly, :dm, :bv, :loc, :eid, 'active', :gl, :dgl)"
        ), {"id": aid, "tid": tenant_id, "cid": company_id, "code": acode,
            "name": name, "desc": kw.get("description"), "cat": kw.get("category"),
            "ad": acquisition_date, "ac": cost, "sv": float(kw.get("salvage_value", 0)),
            "uly": useful_life_years, "dm": kw.get("depreciation_method", "straight_line"),
            "bv": cost, "loc": kw.get("location"), "eid": kw.get("employee_id"),
            "gl": kw.get("gl_account_id"), "dgl": kw.get("depreciation_gl_account_id")})
        self.db.flush()
        return aid

    def list_assets(self, company_id: str, tenant_id: str | None = None,
                    status: str | None = None) -> list[dict]:
        conditions = ["company_id = :cid"]
        params: dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, asset_code, name, category, acquisition_cost, book_value, "
            f"accumulated_depreciation, status, depreciation_method, useful_life_years "
            f"FROM dbp_fixed_assets WHERE {where} ORDER BY asset_code"
        ), params).fetchall()
        return [{"id": r[0], "asset_code": r[1], "name": r[2], "category": r[3],
                 "acquisition_cost": float(r[4]), "book_value": float(r[5]),
                 "accumulated_depreciation": float(r[6]), "status": r[7],
                 "depreciation_method": r[8], "useful_life_years": r[9]} for r in rows]

    def get_asset(self, asset_id: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, asset_code, name, description, category, acquisition_date, "
            "acquisition_cost, salvage_value, useful_life_years, depreciation_method, "
            "accumulated_depreciation, book_value, location, employee_id, status "
            "FROM dbp_fixed_assets WHERE id = :aid"
        ), {"aid": asset_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "asset_code": row[1], "name": row[2], "description": row[3],
                "category": row[4], "acquisition_date": str(row[5]) if row[5] else None,
                "acquisition_cost": float(row[6]), "salvage_value": float(row[7]),
                "useful_life_years": row[8], "depreciation_method": row[9],
                "accumulated_depreciation": float(row[10]),
                "book_value": float(row[11]), "location": row[12],
                "employee_id": row[13], "status": row[14]}

    def update_asset(self, asset_id: str, **kw) -> dict[str, Any]:
        row = self.db.execute(text("SELECT id FROM dbp_fixed_assets WHERE id = :aid"), {"aid": asset_id}).fetchone()
        if not row:
            return {"success": False, "error": "Asset not found"}
        allowed = {"name", "description", "category", "location", "employee_id", "status"}
        updates = {k: v for k, v in kw.items() if k in allowed}
        if not updates:
            return {"success": False, "error": "No valid fields to update"}
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        params = {"aid": asset_id, **updates}
        self.db.execute(text(f"UPDATE dbp_fixed_assets SET {set_clause} WHERE id = :aid"), params)
        self.db.flush()
        return {"success": True}

    def calculate_depreciation(self, asset_id: str, period_start: str, period_end: str) -> dict[str, Any]:
        a = self.db.execute(text(
            "SELECT acquisition_cost, salvage_value, useful_life_years, "
            "depreciation_method, accumulated_depreciation, book_value, acquisition_date "
            "FROM dbp_fixed_assets WHERE id = :aid"
        ), {"aid": asset_id}).fetchone()
        if not a:
            return {"success": False, "error": "Asset not found"}
        cost, salvage, life, method, acc_dep, bv, _acq_date = (
            float(a[0]), float(a[1]), a[2], a[3], float(a[4]), float(a[5]), a[6])
        remaining_life = life - int(acc_dep / ((cost - salvage) / life)) if (cost - salvage) > 0 else 0
        if remaining_life <= 0:
            return {"success": False, "error": "Asset fully depreciated"}

        ps = datetime.strptime(period_start, "%Y-%m-%d").date()
        pe = datetime.strptime(period_end, "%Y-%m-%d").date()
        months = (pe.year - ps.year) * 12 + (pe.month - ps.month) + 1

        if method == "straight_line":
            annual = (cost - salvage) / life
            depr = annual * months / 12
        else:
            annual_rate = 1 / life * 2
            depr = bv * annual_rate * months / 12

        depr = min(depr, bv - salvage)
        depr = max(0, depr)
        new_acc = acc_dep + depr
        new_bv = bv - depr
        return {"depreciation_amount": round(depr, 2), "accumulated_after": round(new_acc, 2),
                "book_value_after": round(new_bv, 2), "remaining_useful_life": remaining_life}

    def run_depreciation(self, tenant_id: str, company_id: str, period_start: str,
                         period_end: str, processed_by: str | None = None) -> str:
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_asset_depreciation_runs (id, tenant_id, company_id, "
            "period_start, period_end, processed_by) VALUES (:id, :tid, :cid, :ps, :pe, :pb)"
        ), {"id": rid, "tid": tenant_id, "cid": company_id, "ps": period_start,
            "pe": period_end, "pb": processed_by})

        assets = self.db.execute(text(
            "SELECT id FROM dbp_fixed_assets WHERE company_id = :cid AND tenant_id = :tid AND status = 'active'"
        ), {"cid": company_id, "tid": tenant_id}).fetchall()
        total = 0
        for a in assets:
            dep_result = self.calculate_depreciation(a[0], period_start, period_end)
            if not dep_result.get("success") is False and dep_result.get("depreciation_amount", 0) > 0:
                lid = str(uuid.uuid4())
                amt = dep_result["depreciation_amount"]
                self.db.execute(text(
                    "INSERT INTO dbp_asset_depreciation_lines (id, tenant_id, run_id, asset_id, "
                    "depreciation_amount, accumulated_after, book_value_after) "
                    "VALUES (:id, :tid, :rid, :aid, :da, :aa, :bva)"
                ), {"id": lid, "tid": tenant_id, "rid": rid, "aid": a[0],
                    "da": amt, "aa": dep_result["accumulated_after"],
                    "bva": dep_result["book_value_after"]})
                self.db.execute(text(
                    "UPDATE dbp_fixed_assets SET accumulated_depreciation = :ad, book_value = :bv WHERE id = :aid"
                ), {"ad": dep_result["accumulated_after"], "bv": dep_result["book_value_after"], "aid": a[0]})
                total += amt

        self.db.execute(text(
            "UPDATE dbp_asset_depreciation_runs SET total_depreciation = :td, status = 'completed' WHERE id = :rid"
        ), {"td": total, "rid": rid})
        self.db.flush()
        return rid

    def list_depreciation_runs(self, company_id: str, tenant_id: str | None = None) -> list[dict]:
        conditions = ["company_id = :cid"]
        params: dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, period_start, period_end, status, total_depreciation "
            f"FROM dbp_asset_depreciation_runs WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "period_start": str(r[1]) if r[1] else None,
                 "period_end": str(r[2]) if r[2] else None, "status": r[3],
                 "total_depreciation": float(r[4]) if r[4] else 0} for r in rows]

    def get_depreciation_run(self, run_id: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, period_start, period_end, status, total_depreciation "
            "FROM dbp_asset_depreciation_runs WHERE id = :rid"
        ), {"rid": run_id}).fetchone()
        if not row:
            return None
        lines = self.db.execute(text(
            "SELECT l.id, l.asset_id, a.asset_code, a.name, l.depreciation_amount, "
            "l.accumulated_after, l.book_value_after "
            "FROM dbp_asset_depreciation_lines l LEFT JOIN dbp_fixed_assets a ON l.asset_id = a.id "
            "WHERE l.run_id = :rid"
        ), {"rid": run_id}).fetchall()
        return {"id": row[0], "period_start": str(row[1]) if row[1] else None,
                "period_end": str(row[2]) if row[2] else None, "status": row[3],
                "total_depreciation": float(row[4]) if row[4] else 0,
                "lines": [{"id": l[0], "asset_id": l[1], "asset_code": l[2],
                           "asset_name": l[3], "depreciation_amount": float(l[4]),
                           "accumulated_after": float(l[5]),
                           "book_value_after": float(l[6])} for l in lines]}

    def dispose_asset(self, asset_id: str, disposal_date: str,
                      disposal_amount: float | None = None, notes: str | None = None) -> dict[str, Any]:
        row = self.db.execute(text(
            "SELECT status, book_value, accumulated_depreciation FROM dbp_fixed_assets WHERE id = :aid"
        ), {"aid": asset_id}).fetchone()
        if not row:
            return {"success": False, "error": "Asset not found"}
        if row[0] != "active":
            return {"success": False, "error": f"Cannot dispose asset in '{row[0]}' status"}
        self.db.execute(text(
            "UPDATE dbp_fixed_assets SET status = 'disposed' WHERE id = :aid"
        ), {"aid": asset_id})
        self.db.flush()
        return {"success": True, "book_value_at_disposal": float(row[1]),
                "accumulated_depreciation": float(row[2])}

    def transfer_asset(self, asset_id: str, to_location: str, transfer_date: str,
                       transferred_by: str, notes: str | None = None) -> str:
        asset = self.db.execute(text(
            "SELECT location FROM dbp_fixed_assets WHERE id = :aid"
        ), {"aid": asset_id}).fetchone()
        if not asset:
            raise ValueError("Asset not found")
        tid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_asset_transfers (id, tenant_id, asset_id, from_location, "
            "to_location, transfer_date, transferred_by, notes) "
            "VALUES (:id, (SELECT tenant_id FROM dbp_fixed_assets WHERE id=:aid), "
            ":aid, :fl, :tl, :td, :tb, :notes)"
        ), {"id": tid, "aid": asset_id, "fl": asset[0], "tl": to_location,
            "td": transfer_date, "tb": transferred_by, "notes": notes})
        self.db.execute(text(
            "UPDATE dbp_fixed_assets SET location = :loc WHERE id = :aid"
        ), {"loc": to_location, "aid": asset_id})
        self.db.flush()
        return tid

    def list_asset_transfers(self, asset_id: str | None = None,
                             company_id: str | None = None) -> list[dict]:
        conditions = []
        params: dict[str, Any] = {}
        if asset_id:
            conditions.append("t.asset_id = :aid")
            params["aid"] = asset_id
        if company_id:
            conditions.append("a.company_id = :cid")
            params["cid"] = company_id
        if not conditions:
            conditions.append("1=1")
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT t.id, t.asset_id, a.asset_code, a.name, t.from_location, "
            f"t.to_location, t.transfer_date, t.transferred_by, t.notes "
            f"FROM dbp_asset_transfers t LEFT JOIN dbp_fixed_assets a ON t.asset_id = a.id "
            f"WHERE {where} ORDER BY t.created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "asset_id": r[1], "asset_code": r[2], "asset_name": r[3],
                 "from_location": r[4], "to_location": r[5],
                 "transfer_date": str(r[6]) if r[6] else None,
                 "transferred_by": r[7], "notes": r[8]} for r in rows]

    def _next_code(self, company_id: str, prefix: str) -> str:
        last = self.db.execute(text(
            "SELECT asset_code FROM dbp_fixed_assets WHERE company_id = :cid ORDER BY created_at DESC LIMIT 1"
        ), {"cid": company_id}).fetchone()
        if last and last[0]:
            try:
                num = int(last[0].replace(f"{prefix}-", "")) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"{prefix}-{num:06d}"
