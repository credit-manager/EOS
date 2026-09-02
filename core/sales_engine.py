"""
P26 Sales & Invoicing Engine
"""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class SalesEngine:
    """Customers, Quotations, Sales Orders, Invoices, Payments."""

    STATUSES_QUOTE = {"draft", "sent", "accepted", "rejected", "converted"}
    STATUSES_ORDER = {"draft", "confirmed", "partially_delivered", "delivered", "closed", "cancelled"}

    def __init__(self, db: Session):
        self.db = db

    # ── CUSTOMERS ──

    def create_customer(self, tenant_id: str, company_id: str, name: str, **kw) -> str:
        cid_ = str(uuid.uuid4())
        ccode = self._next_code(company_id, "CUS")
        self.db.execute(text(
            "INSERT INTO dbp_customers (id, tenant_id, company_id, code, name, "
            "contact_name, email, phone, address, tax_number, payment_terms, "
            "credit_limit, currency_code) "
            "VALUES (:id, :tid, :cid, :code, :name, :cn, :email, :phone, :addr, "
            ":tax, :pt, :cl, :cc)"
        ), {"id": cid_, "tid": tenant_id, "cid": company_id, "code": ccode,
            "name": name, "cn": kw.get("contact_name"), "email": kw.get("email"),
            "phone": kw.get("phone"), "addr": kw.get("address"),
            "tax": kw.get("tax_number"), "pt": kw.get("payment_terms", "net30"),
            "cl": kw.get("credit_limit", 0), "cc": kw.get("currency_code", "SAR")})
        self.db.flush()
        return cid_

    def list_customers(self, company_id: str, tenant_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"cid": company_id}
        tenant_filter = ""
        if tenant_id:
            tenant_filter = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        rows = self.db.execute(text(
            f"SELECT id, code, name, contact_name, email, phone, payment_terms, "
            f"credit_limit, is_active FROM dbp_customers WHERE company_id = :cid{tenant_filter} "
            f"ORDER BY name"
        ), params).fetchall()
        return [{"id": r[0], "code": r[1], "name": r[2], "contact_name": r[3],
                 "email": r[4], "phone": r[5], "payment_terms": r[6],
                 "credit_limit": float(r[7]) if r[7] is not None else 0,
                 "is_active": bool(r[8])} for r in rows]

    # ── QUOTATIONS ──

    def create_quotation(self, tenant_id: str, company_id: str, customer_id: str,
                         quote_date: str, lines: list[dict], **kw) -> str:
        qid = str(uuid.uuid4())
        qnum = self._next_code(company_id, "QT")
        total, tax_total = self._calc_totals(lines)

        self.db.execute(text(
            "INSERT INTO dbp_sales_quotations (id, tenant_id, company_id, quote_number, "
            "customer_id, quote_date, valid_until, total_amount, tax_amount, "
            "currency_code, notes, created_by) "
            "VALUES (:id, :tid, :cid, :qn, :custid, :qd, :vu, :ta, :tx, :cc, :notes, :cb)"
        ), {"id": qid, "tid": tenant_id, "cid": company_id, "qn": qnum,
            "custid": customer_id, "qd": quote_date, "vu": kw.get("valid_until"),
            "ta": total, "tx": tax_total, "cc": kw.get("currency_code", "SAR"),
            "notes": kw.get("notes"), "cb": kw.get("created_by")})

        self._insert_lines("dbp_sales_quotation_lines", tenant_id, "quote_id", qid, lines)
        self.db.flush()
        return qid

    def convert_quotation_to_order(self, quote_id: str, tenant_id: str, company_id: str,
                                   created_by: str | None = None) -> dict[str, Any]:
        quote = self.db.execute(text(
            "SELECT id, status, customer_id, quote_date, total_amount, tax_amount, "
            "currency_code, notes FROM dbp_sales_quotations WHERE id = :qid AND tenant_id = :tid"
        ), {"qid": quote_id, "tid": tenant_id}).fetchone()
        if not quote:
            return {"success": False, "error": "Quotation not found"}
        if quote[1] == "converted":
            return {"success": False, "error": "Quotation already converted"}

        qlines = self.db.execute(text(
            "SELECT item_id, description, quantity, unit_price, tax_rate, tax_amount "
            "FROM dbp_sales_quotation_lines WHERE quote_id = :qid ORDER BY line_number"
        ), {"qid": quote_id}).fetchall()

        lines = [{"item_id": l[0], "description": l[1], "quantity": float(l[2]),
                  "unit_price": float(l[3]), "tax_rate": float(l[4]) if l[4] else 0,
                  "tax_amount": float(l[5]) if l[5] is not None else None}
                 for l in qlines]
        total, tax_total = self._calc_totals(lines)

        oid = self._insert_sales_order(tenant_id, company_id, quote[2], str(quote[3]),
                                       total, tax_total, quote[6], quote[7], created_by)
        if lines:
            self._insert_lines("dbp_sales_order_lines", tenant_id, "order_id", oid, lines)

        self.db.execute(text(
            "UPDATE dbp_sales_orders SET quotation_id = :qid WHERE id = :oid"
        ), {"qid": quote_id, "oid": oid})
        self.db.execute(text(
            "UPDATE dbp_sales_quotations SET status = 'converted' WHERE id = :qid"
        ), {"qid": quote_id})
        self.db.flush()
        return {"success": True, "order_id": oid}

    # ── SALES ORDERS ──

    def create_sales_order(self, tenant_id: str, company_id: str, customer_id: str,
                           order_date: str, lines: list[dict], **kw) -> str:
        total, tax_total = self._calc_totals(lines)
        oid = self._insert_sales_order(tenant_id, company_id, customer_id, order_date,
                                       total, tax_total,
                                       kw.get("currency_code", "SAR"),
                                       kw.get("notes"), kw.get("created_by"))
        if kw.get("quotation_id"):
            self.db.execute(text(
                "UPDATE dbp_sales_orders SET quotation_id = :qid WHERE id = :oid"
            ), {"qid": kw.get("quotation_id"), "oid": oid})
        self._insert_lines("dbp_sales_order_lines", tenant_id, "order_id", oid, lines)
        self.db.flush()
        return oid

    def get_sales_order(self, order_id: str, tenant_id: str | None = None) -> dict | None:
        params: dict[str, Any] = {"oid": order_id}
        tscope = ""
        if tenant_id:
            tscope = " AND o.tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT o.id, o.order_number, o.customer_id, c.name, o.quotation_id, "
            "o.order_date, o.status, o.total_amount, o.tax_amount, o.currency_code, o.notes "
            "FROM dbp_sales_orders o LEFT JOIN dbp_customers c ON o.customer_id = c.id "
            "WHERE o.id = :oid" + tscope
        ), params).fetchone()
        if not row:
            return None
        lines = self.db.execute(text(
            "SELECT l.id, l.line_number, l.item_id, l.description, l.quantity, "
            "l.unit_price, l.line_total, l.quantity_delivered, l.tax_rate, l.tax_amount "
            "FROM dbp_sales_order_lines l WHERE l.order_id = :oid ORDER BY l.line_number"
        ), {"oid": order_id}).fetchall()
        return {
            "id": row[0], "order_number": row[1], "customer_id": row[2],
            "customer_name": row[3], "quotation_id": row[4],
            "order_date": str(row[5]) if row[5] else None, "status": row[6],
            "total_amount": float(row[7]) if row[7] else 0,
            "tax_amount": float(row[8]) if row[8] else 0,
            "currency_code": row[9], "notes": row[10],
            "lines": [{"id": l[0], "line_number": l[1], "item_id": l[2],
                       "description": l[3], "quantity": float(l[4]),
                       "unit_price": float(l[5]), "line_total": float(l[6]),
                       "quantity_delivered": float(l[7]) if l[7] is not None else 0,
                       "tax_rate": float(l[8]) if l[8] is not None else 0,
                       "tax_amount": float(l[9]) if l[9] is not None else 0} for l in lines]
        }

    def list_sales_orders(self, company_id: str, status: str | None = None,
                          tenant_id: str | None = None) -> list[dict]:
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
            f"SELECT o.id, o.order_number, c.name, o.order_date, o.status, "
            f"o.total_amount, o.currency_code FROM dbp_sales_orders o "
            f"LEFT JOIN dbp_customers c ON o.customer_id = c.id "
            f"WHERE {where} ORDER BY o.order_date DESC"
        ), params).fetchall()
        return [{"id": r[0], "order_number": r[1], "customer_name": r[2],
                 "order_date": str(r[3]) if r[3] else None, "status": r[4],
                 "total_amount": float(r[5]) if r[5] else 0,
                 "currency_code": r[6]} for r in rows]

    # ── INVOICES ──

    def create_invoice(self, tenant_id: str, company_id: str, customer_id: str,
                       invoice_date: str, lines: list[dict], **kw) -> str:
        iid = str(uuid.uuid4())
        invnum = self._next_code(company_id, "INV")
        total, tax_total = self._calc_totals(lines)

        self.db.execute(text(
            "INSERT INTO dbp_sales_invoices (id, tenant_id, company_id, invoice_number, "
            "customer_id, order_id, invoice_date, due_date, total_amount, tax_amount, "
            "paid_amount, currency_code, notes, created_by) "
            "VALUES (:id, :tid, :cid, :in, :custid, :oid, :idate, :dd, :ta, :tx, 0, "
            ":cc, :notes, :cb)"
        ), {"id": iid, "tid": tenant_id, "cid": company_id, "in": invnum,
            "custid": customer_id, "oid": kw.get("order_id"), "idate": invoice_date,
            "dd": kw.get("due_date"), "ta": total, "tx": tax_total,
            "cc": kw.get("currency_code", "SAR"), "notes": kw.get("notes"),
            "cb": kw.get("created_by")})

        self._insert_lines("dbp_sales_invoice_lines", tenant_id, "invoice_id", iid, lines)
        self.db.flush()
        return iid

    def get_invoice(self, invoice_id: str, tenant_id: str | None = None) -> dict | None:
        params: dict[str, Any] = {"iid": invoice_id}
        tscope = ""
        if tenant_id:
            tscope = " AND i.tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT i.id, i.invoice_number, i.customer_id, c.name, i.order_id, "
            "i.invoice_date, i.due_date, i.status, i.total_amount, i.tax_amount, "
            "i.paid_amount, i.currency_code, i.notes "
            "FROM dbp_sales_invoices i LEFT JOIN dbp_customers c ON i.customer_id = c.id "
            "WHERE i.id = :iid" + tscope
        ), params).fetchone()
        if not row:
            return None
        lines = self.db.execute(text(
            "SELECT l.id, l.line_number, l.item_id, l.description, l.quantity, "
            "l.unit_price, l.line_total, l.tax_rate, l.tax_amount "
            "FROM dbp_sales_invoice_lines l WHERE l.invoice_id = :iid ORDER BY l.line_number"
        ), {"iid": invoice_id}).fetchall()
        return {
            "id": row[0], "invoice_number": row[1], "customer_id": row[2],
            "customer_name": row[3], "order_id": row[4],
            "invoice_date": str(row[5]) if row[5] else None,
            "due_date": str(row[6]) if row[6] else None, "status": row[7],
            "total_amount": float(row[8]) if row[8] else 0,
            "tax_amount": float(row[9]) if row[9] else 0,
            "paid_amount": float(row[10]) if row[10] is not None else 0,
            "currency_code": row[11], "notes": row[12],
            "lines": [{"id": l[0], "line_number": l[1], "item_id": l[2],
                       "description": l[3], "quantity": float(l[4]),
                       "unit_price": float(l[5]), "line_total": float(l[6]),
                       "tax_rate": float(l[7]) if l[7] is not None else 0,
                       "tax_amount": float(l[8]) if l[8] is not None else 0} for l in lines]
        }

    def list_invoices(self, company_id: str, status: str | None = None,
                      tenant_id: str | None = None) -> list[dict]:
        conditions = ["i.company_id = :cid"]
        params: dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("i.tenant_id = :tid")
            params["tid"] = tenant_id
        if status:
            conditions.append("i.status = :st")
            params["st"] = status
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT i.id, i.invoice_number, c.name, i.invoice_date, i.due_date, "
            f"i.status, i.total_amount, i.tax_amount, i.paid_amount, i.currency_code "
            f"FROM dbp_sales_invoices i LEFT JOIN dbp_customers c ON i.customer_id = c.id "
            f"WHERE {where} ORDER BY i.invoice_date DESC"
        ), params).fetchall()
        return [{"id": r[0], "invoice_number": r[1], "customer_name": r[2],
                 "invoice_date": str(r[3]) if r[3] else None,
                 "due_date": str(r[4]) if r[4] else None, "status": r[5],
                 "total_amount": float(r[6]) if r[6] else 0,
                 "tax_amount": float(r[7]) if r[7] else 0,
                 "paid_amount": float(r[8]) if r[8] is not None else 0,
                 "currency_code": r[9]} for r in rows]

    # ── PAYMENTS ──

    def record_payment(self, invoice_id: str, amount: float, payment_date: str,
                       tenant_id: str | None = None, **kw) -> dict[str, Any]:
        params: dict[str, Any] = {"iid": invoice_id}
        tscope = ""
        if tenant_id:
            tscope = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT total_amount, tax_amount, paid_amount, status "
            "FROM dbp_sales_invoices WHERE id = :iid" + tscope
        ), params).fetchone()
        if not row:
            return {"success": False, "error": "Invoice not found"}
        if row[3] == "cancelled":
            return {"success": False, "error": "Cannot record payment on a cancelled invoice"}
        if amount <= 0:
            return {"success": False, "error": "Payment amount must be positive"}

        total = float(row[0] or 0) + float(row[1] or 0)
        paid = float(row[2] or 0)
        balance = total - paid
        if round(amount, 4) > round(balance, 4):
            return {"success": False, "error": f"Payment {amount} exceeds remaining balance {balance}"}

        new_paid = paid + amount
        new_status = "paid" if round(new_paid, 4) >= round(total, 4) else "partial"
        self.db.execute(text(
            "UPDATE dbp_sales_invoices SET paid_amount = :pa, status = :st WHERE id = :iid"
        ), {"pa": new_paid, "st": new_status, "iid": invoice_id})
        self.db.flush()
        return {"success": True, "paid_amount": new_paid, "status": new_status}

    # ── HELPERS ──

    def _calc_totals(self, lines: list[dict]) -> tuple[float, float]:
        total = sum(float(l.get("quantity", 0)) * float(l.get("unit_price", 0)) for l in lines)
        tax_total = sum(
            float(l["tax_amount"]) if l.get("tax_amount")
            else float(l.get("quantity", 0)) * float(l.get("unit_price", 0))
                 * float(l.get("tax_rate", 0) or 0) / 100
            for l in lines)
        return total, tax_total

    def _insert_lines(self, table: str, tenant_id: str, fk_col: str, fk_id: str,
                      lines: list[dict]) -> None:
        has_delivered = table == "dbp_sales_order_lines"
        cols = (f"id, tenant_id, {fk_col}, line_number, item_id, description, quantity, "
                "unit_price, line_total, tax_rate, tax_amount")
        vals = (":id, :tid, :fkid, :ln, :iid, :desc, :qty, :up, :lt, :tr, :txa")
        if has_delivered:
            cols += ", quantity_delivered"
            vals += ", :qd"
        sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
        for i, line in enumerate(lines, 1):
            lid = str(uuid.uuid4())
            lt = float(line.get("quantity", 0)) * float(line.get("unit_price", 0))
            params: dict[str, Any] = {
                "id": lid, "tid": tenant_id, "fkid": fk_id, "ln": i,
                "iid": line.get("item_id"), "desc": line.get("description"),
                "qty": line.get("quantity", 0), "up": line.get("unit_price", 0),
                "lt": lt, "tr": line.get("tax_rate", 0),
                "txa": line.get("tax_amount") or lt * float(line.get("tax_rate", 0) or 0) / 100}
            if has_delivered:
                params["qd"] = line.get("quantity_delivered", 0)
            self.db.execute(text(sql), params)

    def _insert_sales_order(self, tenant_id: str, company_id: str, customer_id: str,
                            order_date: str, total: float, tax: float, currency: str,
                            notes: str | None, created_by: str | None) -> str:
        oid = str(uuid.uuid4())
        ocode = self._next_code(company_id, "SO")
        self.db.execute(text(
            "INSERT INTO dbp_sales_orders (id, tenant_id, company_id, order_number, "
            "customer_id, order_date, total_amount, tax_amount, currency_code, "
            "notes, created_by) "
            "VALUES (:id, :tid, :cid, :on, :custid, :od, :ta, :tx, :cc, :notes, :cb)"
        ), {"id": oid, "tid": tenant_id, "cid": company_id, "on": ocode,
            "custid": customer_id, "od": order_date, "ta": total, "tx": tax,
            "cc": currency, "notes": notes, "cb": created_by})
        return oid

    def _next_code(self, company_id: str, prefix: str) -> str:
        table_map = {
            "CUS": ("dbp_customers", "code"),
            "QT": ("dbp_sales_quotations", "quote_number"),
            "SO": ("dbp_sales_orders", "order_number"),
            "INV": ("dbp_sales_invoices", "invoice_number")}
        table, col = table_map[prefix]
        rows = self.db.execute(text(
            f"SELECT {col} FROM {table} WHERE company_id = :cid AND {col} LIKE :pre"
        ), {"cid": company_id, "pre": f"{prefix}-%"}).fetchall()
        num = 0
        for r in rows:
            try:
                num = max(num, int(str(r[0]).rsplit("-", 1)[1]))
            except (ValueError, IndexError):
                continue
        return f"{prefix}-{num + 1:06d}"
