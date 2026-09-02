"""
P25 Inventory Management Engine
"""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class InventoryEngine:
    """Warehouses, Stock, Movements, Stock Takes."""

    MOVEMENT_TYPES = {"purchase_receive", "sales_issue", "transfer_in", "transfer_out",
                      "adjustment_plus", "adjustment_minus", "return_in", "return_out"}

    def __init__(self, db: Session):
        self.db = db

    # ── WAREHOUSES ──

    def create_warehouse(self, tenant_id: str, company_id: str, name: str, **kw) -> str:
        wid = str(uuid.uuid4())
        code = kw.get("code") or self._next_code(company_id, "WH")
        self.db.execute(text(
            "INSERT INTO dbp_warehouses (id, tenant_id, company_id, code, name, location, manager_id) "
            "VALUES (:id, :tid, :cid, :code, :name, :loc, :mgr)"
        ), {"id": wid, "tid": tenant_id, "cid": company_id, "code": code,
            "name": name, "loc": kw.get("location"), "mgr": kw.get("manager_id")})
        self.db.flush()
        return wid

    def list_warehouses(self, company_id: str, tenant_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"cid": company_id}
        tf = ""
        if tenant_id:
            tf = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        rows = self.db.execute(text(
            f"SELECT id, code, name, location, manager_id, is_active "
            f"FROM dbp_warehouses WHERE company_id = :cid{tf} ORDER BY code"
        ), params).fetchall()
        return [{"id": r[0], "code": r[1], "name": r[2], "location": r[3],
                 "manager_id": r[4], "is_active": bool(r[5])} for r in rows]

    # ── STOCK ──

    def get_stock(self, company_id: str, item_id: str | None = None, warehouse_id: str | None = None,
                  tenant_id: str | None = None) -> list[dict]:
        conditions = ["s.company_id = :cid"]
        params: dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("s.tenant_id = :tid")
            params["tid"] = tenant_id
        if item_id:
            conditions.append("s.item_id = :iid")
            params["iid"] = item_id
        if warehouse_id:
            conditions.append("s.warehouse_id = :wid")
            params["wid"] = warehouse_id
        where = " AND ".join(conditions)

        rows = self.db.execute(text(
            f"SELECT s.id, s.item_id, i.code, i.name_en, s.warehouse_id, w.name, "
            f"s.quantity_on_hand, s.quantity_reserved, s.reorder_level, s.max_level "
            f"FROM dbp_stock s "
            f"LEFT JOIN dbp_items i ON s.item_id = i.id "
            f"LEFT JOIN dbp_warehouses w ON s.warehouse_id = w.id "
            f"WHERE {where} ORDER BY i.code, w.name"
        ), params).fetchall()
        return [{"id": r[0], "item_id": r[1], "item_code": r[2], "item_name": r[3],
                 "warehouse_id": r[4], "warehouse_name": r[5],
                 "quantity_on_hand": float(r[6]) if r[6] else 0,
                 "quantity_reserved": float(r[7]) if r[7] else 0,
                 "reorder_level": float(r[8]) if r[8] else 0,
                 "max_level": float(r[9]) if r[9] else 0} for r in rows]

    def _upsert_stock(self, company_id: str, tenant_id: str, item_id: str, warehouse_id: str, delta: float):
        row = self.db.execute(text(
            "SELECT id FROM dbp_stock WHERE company_id = :cid AND item_id = :iid AND warehouse_id = :wid"
        ), {"cid": company_id, "iid": item_id, "wid": warehouse_id}).fetchone()
        if row:
            self.db.execute(text(
                "UPDATE dbp_stock SET quantity_on_hand = quantity_on_hand + :delta WHERE id = :sid"
            ), {"delta": delta, "sid": row[0]})
        else:
            sid = str(uuid.uuid4())
            self.db.execute(text(
                "INSERT INTO dbp_stock (id, tenant_id, company_id, item_id, warehouse_id, quantity_on_hand) "
                "VALUES (:id, :tid, :cid, :iid, :wid, :qty)"
            ), {"id": sid, "tid": tenant_id, "cid": company_id, "iid": item_id,
                "wid": warehouse_id, "qty": delta})

    def _record_movement(self, tenant_id: str, company_id: str, item_id: str,
                         warehouse_id: str, movement_type: str, quantity: float,
                         reference_type: str | None = None, reference_id: str | None = None,
                         notes: str | None = None, moved_by: str | None = None) -> str:
        mid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_stock_movements (id, tenant_id, company_id, item_id, warehouse_id, "
            "movement_type, quantity, reference_type, reference_id, notes, moved_by) "
            "VALUES (:id, :tid, :cid, :iid, :wid, :mt, :qty, :rt, :ri, :notes, :mb)"
        ), {"id": mid, "tid": tenant_id, "cid": company_id, "iid": item_id,
            "wid": warehouse_id, "mt": movement_type, "qty": quantity,
            "rt": reference_type, "ri": reference_id, "notes": notes, "mb": moved_by})
        return mid

    def receive_stock(self, company_id: str, tenant_id: str, item_id: str, warehouse_id: str,
                      quantity: float, movement_type: str = "purchase_receive",
                      reference_type: str | None = None, reference_id: str | None = None,
                      notes: str | None = None, moved_by: str | None = None) -> dict[str, Any]:
        if quantity <= 0:
            return {"success": False, "error": "Quantity must be positive"}
        self._upsert_stock(company_id, tenant_id, item_id, warehouse_id, quantity)
        mid = self._record_movement(tenant_id, company_id, item_id, warehouse_id,
                                     movement_type, quantity, reference_type, reference_id, notes, moved_by)
        self.db.flush()
        return {"success": True, "movement_id": mid}

    def issue_stock(self, company_id: str, tenant_id: str, item_id: str, warehouse_id: str,
                    quantity: float, movement_type: str = "sales_issue",
                    reference_type: str | None = None, reference_id: str | None = None,
                    notes: str | None = None, moved_by: str | None = None) -> dict[str, Any]:
        if quantity <= 0:
            return {"success": False, "error": "Quantity must be positive"}
        current = self.db.execute(text(
            "SELECT quantity_on_hand FROM dbp_stock WHERE company_id = :cid AND item_id = :iid AND warehouse_id = :wid"
        ), {"cid": company_id, "iid": item_id, "wid": warehouse_id}).fetchone()
        avail = float(current[0]) if current else 0
        if quantity > avail:
            return {"success": False, "error": f"Insufficient stock: {avail} available"}
        self._upsert_stock(company_id, tenant_id, item_id, warehouse_id, -quantity)
        mid = self._record_movement(tenant_id, company_id, item_id, warehouse_id,
                                     movement_type, -quantity, reference_type, reference_id, notes, moved_by)
        self.db.flush()
        return {"success": True, "movement_id": mid}

    def transfer_stock(self, company_id: str, tenant_id: str, item_id: str,
                       from_warehouse_id: str, to_warehouse_id: str,
                       quantity: float, notes: str | None = None, moved_by: str | None = None) -> dict[str, Any]:
        if quantity <= 0:
            return {"success": False, "error": "Quantity must be positive"}
        if from_warehouse_id == to_warehouse_id:
            return {"success": False, "error": "Source and destination warehouses must differ"}
        result = self.issue_stock(company_id, tenant_id, item_id, from_warehouse_id, quantity,
                                   movement_type="transfer_out", notes=notes, moved_by=moved_by)
        if not result["success"]:
            return result
        self.receive_stock(company_id, tenant_id, item_id, to_warehouse_id, quantity,
                           movement_type="transfer_in", notes=notes, moved_by=moved_by)
        self.db.flush()
        return {"success": True}

    def list_movements(self, company_id: str, item_id: str | None = None, warehouse_id: str | None = None,
                       movement_type: str | None = None, limit: int = 100,
                       tenant_id: str | None = None) -> list[dict]:
        conditions = ["company_id = :cid"]
        params: dict[str, Any] = {"cid": company_id, "lim": limit}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        if item_id:
            conditions.append("item_id = :iid")
            params["iid"] = item_id
        if warehouse_id:
            conditions.append("warehouse_id = :wid")
            params["wid"] = warehouse_id
        if movement_type:
            conditions.append("movement_type = :mt")
            params["mt"] = movement_type
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, item_id, warehouse_id, movement_type, quantity, reference_type, "
            f"reference_id, notes, created_at FROM dbp_stock_movements "
            f"WHERE {where} ORDER BY created_at DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "item_id": r[1], "warehouse_id": r[2], "movement_type": r[3],
                 "quantity": float(r[4]), "reference_type": r[5], "reference_id": r[6],
                 "notes": r[7], "created_at": r[8].isoformat() if r[8] else None} for r in rows]

    def get_low_stock_alerts(self, company_id: str, tenant_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"cid": company_id}
        tf = ""
        if tenant_id:
            tf = " AND s.tenant_id = :tid"
            params["tid"] = tenant_id
        rows = self.db.execute(text(
            f"SELECT s.item_id, i.code, i.name_en, w.name, s.quantity_on_hand, s.reorder_level "
            f"FROM dbp_stock s "
            f"LEFT JOIN dbp_items i ON s.item_id = i.id "
            f"LEFT JOIN dbp_warehouses w ON s.warehouse_id = w.id "
            f"WHERE s.company_id = :cid{tf} AND s.reorder_level > 0 AND s.quantity_on_hand <= s.reorder_level "
            f"ORDER BY i.code"
        ), params).fetchall()
        return [{"item_id": r[0], "item_code": r[1], "item_name": r[2],
                 "warehouse_name": r[3], "quantity_on_hand": float(r[4]),
                 "reorder_level": float(r[5])} for r in rows]

    def _next_code(self, company_id: str, prefix: str) -> str:
        last = self.db.execute(text(
            "SELECT code FROM dbp_warehouses WHERE company_id = :cid ORDER BY created_at DESC LIMIT 1"
        ), {"cid": company_id}).fetchone()
        if last and last[0]:
            try:
                num = int(last[0].replace(f"{prefix}-", "")) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"{prefix}-{num:04d}"
