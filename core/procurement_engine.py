"""
P24 Procurement & Purchase Orders Engine
"""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ProcurementEngine:
    """Items, Suppliers, Purchase Requests, POs, GRN."""

    STATUSES_PR = {"draft", "pending_approval", "approved", "rejected"}
    STATUSES_PO = {"draft", "submitted", "approved", "partially_received", "received", "closed", "cancelled"}
    PRIORITIES = {"low", "normal", "high", "urgent"}

    def __init__(self, db: Session):
        self.db = db

    # ── ITEMS ──

    def create_item(self, tenant_id: str, company_id: str, code: str, name: str, item_type: str, **kw) -> str:
        iid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_items (id, tenant_id, company_id, code, name_en, name_ar, "
            "item_type, category, unit_of_measure, standard_cost, gl_account_id) "
            "VALUES (:id, :tid, :cid, :code, :name, :ar, :itype, :cat, :uom, :cost, :gl)"
        ), {"id": iid, "tid": tenant_id, "cid": company_id, "code": code,
            "name": name, "ar": kw.get("name_ar"), "itype": item_type,
            "cat": kw.get("category"), "uom": kw.get("unit_of_measure", "unit"),
            "cost": kw.get("standard_cost", 0), "gl": kw.get("gl_account_id")})
        self.db.flush()
        return iid

    def list_items(self, company_id: str, tenant_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"cid": company_id}
        tenant_filter = ""
        if tenant_id:
            tenant_filter = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        rows = self.db.execute(text(
            f"SELECT id, code, name_en, item_type, category, unit_of_measure, standard_cost, is_active "
            f"FROM dbp_items WHERE company_id = :cid{tenant_filter} ORDER BY code"
        ), params).fetchall()
        return [{"id": r[0], "code": r[1], "name_en": r[2], "item_type": r[3],
                 "category": r[4], "unit_of_measure": r[5],
                 "standard_cost": float(r[6]) if r[6] else 0, "is_active": bool(r[7])}
                for r in rows]

    # ── SUPPLIERS ──

    def create_supplier(self, tenant_id: str, company_id: str, name: str, **kw) -> str:
        sid = str(uuid.uuid4())
        scode = self._next_code("suppliers", company_id, "SUP")
        self.db.execute(text(
            "INSERT INTO dbp_suppliers (id, tenant_id, company_id, code, name, "
            "contact_name, email, phone, address, tax_number, payment_terms, currency_code, gl_account_id) "
            "VALUES (:id, :tid, :cid, :code, :name, :cn, :email, :phone, :addr, :tax, :pt, :cc, :gl)"
        ), {"id": sid, "tid": tenant_id, "cid": company_id, "code": scode,
            "name": name, "cn": kw.get("contact_name"), "email": kw.get("email"),
            "phone": kw.get("phone"), "addr": kw.get("address"),
            "tax": kw.get("tax_number"), "pt": kw.get("payment_terms", "net30"),
            "cc": kw.get("currency_code", "SAR"), "gl": kw.get("gl_account_id")})
        self.db.flush()
        return sid

    def list_suppliers(self, company_id: str, tenant_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"cid": company_id}
        tenant_filter = ""
        if tenant_id:
            tenant_filter = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        rows = self.db.execute(text(
            f"SELECT id, code, name, contact_name, email, phone, payment_terms, currency_code, is_active "
            f"FROM dbp_suppliers WHERE company_id = :cid{tenant_filter} ORDER BY name"
        ), params).fetchall()
        return [{"id": r[0], "code": r[1], "name": r[2], "contact_name": r[3],
                 "email": r[4], "phone": r[5], "payment_terms": r[6],
                 "currency_code": r[7], "is_active": bool(r[8])} for r in rows]

    # ── PURCHASE REQUESTS ──

    def create_purchase_request(self, tenant_id: str, company_id: str, requester_id: str, **kw) -> str:
        rid = str(uuid.uuid4())
        pnum = self._next_code("requests", company_id, "PR")
        self.db.execute(text(
            "INSERT INTO dbp_purchase_requests (id, tenant_id, company_id, request_number, "
            "request_date, requester_id, department_id, description, priority) "
            "VALUES (:id, :tid, :cid, :rn, :rd, :reqid, :did, :desc, :prio)"
        ), {"id": rid, "tid": tenant_id, "cid": company_id, "rn": pnum,
            "rd": kw.get("request_date"), "reqid": requester_id,
            "did": kw.get("department_id"), "desc": kw.get("description"),
            "prio": kw.get("priority", "normal")})
        self.db.flush()
        return rid

    def approve_purchase_request(self, request_id: str, approved_by: str, tenant_id: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"rid": request_id}
        tscope = ""
        if tenant_id:
            tscope = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT status FROM dbp_purchase_requests WHERE id = :rid" + tscope
        ), params).fetchone()
        if not row:
            return {"success": False, "error": "Request not found"}
        if row[0] != "pending_approval":
            return {"success": False, "error": f"Cannot approve request in '{row[0]}' status"}
        self.db.execute(text(
            "UPDATE dbp_purchase_requests SET status='approved', approved_by = :ab WHERE id = :rid"
        ), {"ab": approved_by, "rid": request_id})
        self.db.flush()
        return {"success": True, "status": "approved"}

    def list_purchase_requests(self, company_id: str, status: str | None = None, tenant_id: str | None = None) -> list[dict]:
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
            f"SELECT id, request_number, request_date, requester_id, priority, status, description "
            f"FROM dbp_purchase_requests WHERE {where} ORDER BY request_date DESC"
        ), params).fetchall()
        return [{"id": r[0], "request_number": r[1], "request_date": str(r[2]) if r[2] else None,
                 "requester_id": r[3], "priority": r[4], "status": r[5], "description": r[6]}
                for r in rows]

    # ── PURCHASE ORDERS ──

    def create_purchase_order(self, tenant_id: str, company_id: str, supplier_id: str,
                               order_date: str, lines: list[dict], **kw) -> str:
        oid = str(uuid.uuid4())
        ocode = self._next_code("orders", company_id, "PO")
        total = sum(l.get("quantity", 0) * l.get("unit_price", 0) for l in lines)
        tax_total = sum(l.get("tax_amount", l.get("quantity", 0) * l.get("unit_price", 0) * l.get("tax_rate", 0) / 100) for l in lines)

        self.db.execute(text(
            "INSERT INTO dbp_purchase_orders (id, tenant_id, company_id, order_number, "
            "supplier_id, request_id, order_date, expected_date, total_amount, tax_amount, "
            "currency_code, notes, created_by, cost_center_id) "
            "VALUES (:id, :tid, :cid, :on, :sid, :rid, :od, :ed, :ta, :tx, :cc, :notes, :cb, :ccid)"
        ), {"id": oid, "tid": tenant_id, "cid": company_id, "on": ocode,
            "sid": supplier_id, "rid": kw.get("request_id"), "od": order_date,
            "ed": kw.get("expected_date"), "ta": total, "tx": tax_total,
            "cc": kw.get("currency_code", "SAR"), "notes": kw.get("notes"),
            "cb": kw.get("created_by"), "ccid": kw.get("cost_center_id")})

        for i, line in enumerate(lines, 1):
            lid = str(uuid.uuid4())
            lt = line["quantity"] * line["unit_price"]
            self.db.execute(text(
                "INSERT INTO dbp_purchase_order_lines (id, tenant_id, order_id, line_number, "
                "item_id, description, quantity, unit_price, line_total, tax_rate, tax_amount) "
                "VALUES (:id, :tid, :oid, :ln, :iid, :desc, :qty, :up, :lt, :tr, :txa)"
            ), {"id": lid, "tid": tenant_id, "oid": oid, "ln": i,
                "iid": line.get("item_id"), "desc": line.get("description"),
                "qty": line["quantity"], "up": line["unit_price"],
                "lt": lt, "tr": line.get("tax_rate", 0),
                "txa": line.get("tax_amount", lt * line.get("tax_rate", 0) / 100)})
        self.db.flush()
        return oid

    def get_purchase_order(self, order_id: str, tenant_id: str | None = None) -> dict | None:
        params: dict[str, Any] = {"oid": order_id}
        tscope = ""
        if tenant_id:
            tscope = " AND o.tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT o.id, o.order_number, o.supplier_id, s.name, o.order_date, o.expected_date, "
            "o.status, o.total_amount, o.tax_amount, o.currency_code, o.notes "
            "FROM dbp_purchase_orders o LEFT JOIN dbp_suppliers s ON o.supplier_id = s.id WHERE o.id = :oid" + tscope
        ), params).fetchone()
        if not row:
            return None
        lines = self.db.execute(text(
            "SELECT l.id, l.line_number, l.item_id, i.code, l.description, "
            "l.quantity, l.unit_price, l.line_total, l.quantity_received, l.tax_rate "
            "FROM dbp_purchase_order_lines l LEFT JOIN dbp_items i ON l.item_id = i.id "
            "WHERE l.order_id = :oid ORDER BY l.line_number"
        ), {"oid": order_id}).fetchall()
        return {
            "id": row[0], "order_number": row[1], "supplier_id": row[2],
            "supplier_name": row[3], "order_date": str(row[4]) if row[4] else None,
            "expected_date": str(row[5]) if row[5] else None, "status": row[6],
            "total_amount": float(row[7]) if row[7] else 0,
            "tax_amount": float(row[8]) if row[8] else 0,
            "currency_code": row[9], "notes": row[10],
            "lines": [{"id": l[0], "line_number": l[1], "item_id": l[2], "item_code": l[3],
                       "description": l[4], "quantity": float(l[5]), "unit_price": float(l[6]),
                       "line_total": float(l[7]), "quantity_received": float(l[8]),
                       "tax_rate": float(l[9]) if l[9] else 0} for l in lines]
        }

    def approve_purchase_order(self, order_id: str, approved_by: str, tenant_id: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"oid": order_id}
        tscope = ""
        if tenant_id:
            tscope = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT status FROM dbp_purchase_orders WHERE id = :oid" + tscope
        ), params).fetchone()
        if not row:
            return {"success": False, "error": "Order not found"}
        if row[0] != "submitted":
            return {"success": False, "error": f"Cannot approve order in '{row[0]}' status"}
        self.db.execute(text(
            "UPDATE dbp_purchase_orders SET status='approved', approved_by = :ab WHERE id = :oid"
        ), {"ab": approved_by, "oid": order_id})
        self.db.flush()
        return {"success": True, "status": "approved"}

    def list_purchase_orders(self, company_id: str, status: str | None = None, tenant_id: str | None = None) -> list[dict]:
        conditions = ["o.company_id = :cid"]
        params: dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("o.tenant_id = :tid")
            params["tid"] = tenant_id
        if status:
            conditions.append("o.status = :st")
            params["st"] = status
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT o.id, o.order_number, s.name, o.order_date, o.status, o.total_amount, o.currency_code "
            f"FROM dbp_purchase_orders o LEFT JOIN dbp_suppliers s ON o.supplier_id = s.id "
            f"WHERE {where} ORDER BY o.order_date DESC"
        ), params).fetchall()
        return [{"id": r[0], "order_number": r[1], "supplier_name": r[2],
                 "order_date": str(r[3]) if r[3] else None, "status": r[4],
                 "total_amount": float(r[5]) if r[5] else 0, "currency_code": r[6]}
                for r in rows]

    # ── GRN (Goods Received Note) ──

    def receive_goods(self, order_id: str, line_id: str, quantity: float,
                      received_date: str, received_by: str, tenant_id: str | None = None, notes: str | None = None) -> dict[str, Any]:
        oparams: dict[str, Any] = {"oid": order_id}
        oscope = ""
        if tenant_id:
            oscope = " AND tenant_id = :tid"
            oparams["tid"] = tenant_id
        order = self.db.execute(text(
            "SELECT status FROM dbp_purchase_orders WHERE id = :oid" + oscope
        ), oparams).fetchone()
        if not order:
            return {"success": False, "error": "Order not found"}
        if order[0] not in ("approved", "partially_received"):
            return {"success": False, "error": f"Cannot receive goods for order in '{order[0]}' status"}

        line = self.db.execute(text(
            "SELECT quantity, quantity_received FROM dbp_purchase_order_lines WHERE id = :lid"
        ), {"lid": line_id}).fetchone()
        if not line:
            return {"success": False, "error": "Line not found"}
        remaining = float(line[0]) - float(line[1])
        if quantity > remaining:
            return {"success": False, "error": f"Quantity {quantity} exceeds remaining {remaining}"}

        grn_id = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_grn_items (id, tenant_id, order_id, line_id, quantity_received, received_date, received_by, notes) "
            "VALUES (:id, (SELECT tenant_id FROM dbp_purchase_orders WHERE id=:oid), :oid, :lid, :qty, :rd, :rb, :notes)"
        ), {"id": grn_id, "oid": order_id, "lid": line_id, "qty": quantity,
            "rd": received_date, "rb": received_by, "notes": notes})
        self.db.execute(text(
            "UPDATE dbp_purchase_order_lines SET quantity_received = quantity_received + :qty WHERE id = :lid"
        ), {"qty": quantity, "lid": line_id})

        all_received = self.db.execute(text(
            "SELECT SUM(quantity), SUM(quantity_received) FROM dbp_purchase_order_lines WHERE order_id = :oid"
        ), {"oid": order_id}).fetchone()
        new_status = "received" if float(all_received[0]) <= float(all_received[1]) else "partially_received"
        self.db.execute(text(
            "UPDATE dbp_purchase_orders SET status = :st WHERE id = :oid"
        ), {"st": new_status, "oid": order_id})
        self.db.flush()
        return {"success": True, "grn_id": grn_id, "new_status": new_status}

    # ── HELPERS ──

    def _next_code(self, entity: str, company_id: str, prefix: str) -> str:
        table_map = {"suppliers": ("dbp_suppliers", "code"),
                     "requests": ("dbp_purchase_requests", "request_number"),
                     "orders": ("dbp_purchase_orders", "order_number")}
        table, col = table_map.get(entity, (f"dbp_{entity}", "code"))
        last = self.db.execute(text(
            f"SELECT {col} FROM {table} WHERE company_id = :cid ORDER BY created_at DESC LIMIT 1"
        ), {"cid": company_id}).fetchone()
        if last and last[0]:
            try:
                num = int(last[0].replace(f"{prefix}-", "")) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"{prefix}-{num:06d}"
