"""
P27 Human Resources Engine
"""
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class HREngine:
    """Employees, Leave Requests, Attendance, Payroll Runs."""

    EMPLOYEE_FIELDS = ("first_name", "last_name", "email", "phone", "department_id",
                       "position", "hire_date", "termination_date", "employment_status",
                       "salary", "currency_code", "manager_id", "cost_center_id")

    def __init__(self, db: Session):
        self.db = db

    # ── EMPLOYEES ──

    def create_employee(self, tenant_id: str, company_id: str, first_name: str,
                        last_name: str, hire_date, **kw) -> str:
        eid = str(uuid.uuid4())
        code = self._next_code(company_id, "EMP")
        self.db.execute(text(
            "INSERT INTO dbp_employees (id, tenant_id, company_id, employee_code, "
            "first_name, last_name, email, phone, department_id, position, hire_date, "
            "employment_status, salary, currency_code, manager_id, cost_center_id) "
            "VALUES (:id, :tid, :cid, :code, :fn, :ln, :email, :phone, :dept, :pos, "
            ":hd, :status, :sal, :cur, :mgr, :cc)"
        ), {"id": eid, "tid": tenant_id, "cid": company_id, "code": code,
            "fn": first_name, "ln": last_name,
            "email": kw.get("email"), "phone": kw.get("phone"),
            "dept": kw.get("department_id"), "pos": kw.get("position"),
            "hd": hire_date, "status": kw.get("employment_status", "active"),
            "sal": kw.get("salary", 0),
            "cur": kw.get("currency_code") or "SAR",
            "mgr": kw.get("manager_id"), "cc": kw.get("cost_center_id")})
        self.db.flush()
        return eid

    def list_employees(self, company_id: str, tenant_id: str = None,
                       department_id: str = None) -> List[Dict]:
        conditions = ["company_id = :cid"]
        params: Dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        if department_id:
            conditions.append("department_id = :dept")
            params["dept"] = department_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, employee_code, first_name, last_name, department_id, position, "
            f"hire_date, employment_status, salary FROM dbp_employees "
            f"WHERE {where} ORDER BY employee_code"
        ), params).fetchall()
        return [{"id": r[0], "employee_code": r[1], "first_name": r[2], "last_name": r[3],
                 "department_id": r[4], "position": r[5],
                 "hire_date": r[6].isoformat() if r[6] else None,
                 "employment_status": r[7],
                 "salary": float(r[8]) if r[8] is not None else 0} for r in rows]

    def update_employee(self, employee_id: str, tenant_id: str = None, **kw) -> Dict[str, Any]:
        fields = {k: v for k, v in kw.items() if k in self.EMPLOYEE_FIELDS and v is not None}
        if not fields:
            return {"success": False, "error": "No valid fields to update"}
        params: Dict[str, Any] = {"eid": employee_id}
        tscope = ""
        if tenant_id:
            tscope = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        exists = self.db.execute(text(
            "SELECT id FROM dbp_employees WHERE id = :eid" + tscope
        ), params).fetchone()
        if not exists:
            return {"success": False, "error": "Employee not found"}
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        params.update(fields)
        self.db.execute(text(
            f"UPDATE dbp_employees SET {sets} WHERE id = :eid" + tscope
        ), params)
        self.db.flush()
        return {"success": True}

    # ── LEAVE REQUESTS ──

    def create_leave_request(self, tenant_id: str, employee_id: str, leave_type: str,
                             start_date, end_date, days: int, reason: str = None) -> str:
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_leave_requests (id, tenant_id, employee_id, leave_type, "
            "start_date, end_date, days, reason, status) "
            "VALUES (:id, :tid, :eid, :lt, :sd, :ed, :days, :reason, 'pending')"
        ), {"id": lid, "tid": tenant_id, "eid": employee_id, "lt": leave_type,
            "sd": start_date, "ed": end_date, "days": days, "reason": reason})
        self.db.flush()
        return lid

    def approve_leave_request(self, request_id: str, approved_by: str, tenant_id: str = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"rid": request_id}
        tscope = ""
        if tenant_id:
            tscope = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT status FROM dbp_leave_requests WHERE id = :rid" + tscope
        ), params).fetchone()
        if not row:
            return {"success": False, "error": "Leave request not found"}
        if row[0] != "pending":
            return {"success": False, "error": f"Cannot approve request in status '{row[0]}'"}
        self.db.execute(text(
            "UPDATE dbp_leave_requests SET status = 'approved', approved_by = :ab "
            "WHERE id = :rid" + tscope
        ), {"ab": approved_by, "rid": request_id, "tid": tenant_id})
        self.db.flush()
        return {"success": True, "request_id": request_id, "status": "approved"}

    def list_leave_requests(self, company_id: str, tenant_id: str = None,
                            status: str = None, employee_id: str = None) -> List[Dict]:
        conditions = ["e.company_id = :cid"]
        params: Dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("lr.tenant_id = :tid")
            params["tid"] = tenant_id
        if status:
            conditions.append("lr.status = :st")
            params["st"] = status
        if employee_id:
            conditions.append("lr.employee_id = :eid")
            params["eid"] = employee_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT lr.id, lr.employee_id, e.first_name, e.last_name, lr.leave_type, "
            f"lr.start_date, lr.end_date, lr.days, lr.reason, lr.status, lr.approved_by, "
            f"lr.created_at FROM dbp_leave_requests lr "
            f"JOIN dbp_employees e ON lr.employee_id = e.id "
            f"WHERE {where} ORDER BY lr.created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "employee_id": r[1],
                 "employee_name": f"{r[2]} {r[3]}",
                 "leave_type": r[4],
                 "start_date": r[5].isoformat() if r[5] else None,
                 "end_date": r[6].isoformat() if r[6] else None,
                 "days": r[7], "reason": r[8], "status": r[9],
                 "approved_by": r[10],
                 "created_at": r[11].isoformat() if r[11] else None} for r in rows]

    # ── ATTENDANCE ──

    def record_attendance(self, tenant_id: str, employee_id: str, work_date,
                          clock_in=None, clock_out=None, hours_worked: float = 0,
                          overtime_hours: float = 0) -> str:
        existing = self.db.execute(text(
            "SELECT id FROM dbp_attendance WHERE employee_id = :eid AND work_date = :wd"
        ), {"eid": employee_id, "wd": work_date}).fetchone()
        if existing:
            self.db.execute(text(
                "UPDATE dbp_attendance SET clock_in = :ci, clock_out = :co, "
                "hours_worked = :hw, overtime_hours = :ot WHERE id = :aid"
            ), {"ci": clock_in, "co": clock_out, "hw": hours_worked,
                "ot": overtime_hours, "aid": existing[0]})
            self.db.flush()
            return existing[0]
        aid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_attendance (id, tenant_id, employee_id, work_date, "
            "clock_in, clock_out, hours_worked, overtime_hours) "
            "VALUES (:id, :tid, :eid, :wd, :ci, :co, :hw, :ot)"
        ), {"id": aid, "tid": tenant_id, "eid": employee_id, "wd": work_date,
            "ci": clock_in, "co": clock_out, "hw": hours_worked, "ot": overtime_hours})
        self.db.flush()
        return aid

    def get_attendance(self, company_id: str, tenant_id: str = None,
                       employee_id: str = None, start_date=None,
                       end_date=None) -> List[Dict]:
        conditions = ["e.company_id = :cid"]
        params: Dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("a.tenant_id = :tid")
            params["tid"] = tenant_id
        if employee_id:
            conditions.append("a.employee_id = :eid")
            params["eid"] = employee_id
        if start_date:
            conditions.append("a.work_date >= :sd")
            params["sd"] = start_date
        if end_date:
            conditions.append("a.work_date <= :ed")
            params["ed"] = end_date
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT a.id, a.employee_id, e.first_name, e.last_name, a.work_date, "
            f"a.clock_in, a.clock_out, a.hours_worked, a.overtime_hours, a.status "
            f"FROM dbp_attendance a "
            f"JOIN dbp_employees e ON a.employee_id = e.id "
            f"WHERE {where} ORDER BY a.work_date DESC"
        ), params).fetchall()
        return [{"id": r[0], "employee_id": r[1],
                 "employee_name": f"{r[2]} {r[3]}",
                 "work_date": r[4].isoformat() if r[4] else None,
                 "clock_in": r[5].isoformat() if r[5] else None,
                 "clock_out": r[6].isoformat() if r[6] else None,
                 "hours_worked": float(r[7]) if r[7] is not None else 0,
                 "overtime_hours": float(r[8]) if r[8] is not None else 0,
                 "status": r[9]} for r in rows]

    # ── PAYROLL ──

    def create_payroll_run(self, tenant_id: str, company_id: str,
                           pay_period_start, pay_period_end) -> str:
        rid = str(uuid.uuid4())
        run_number = self._next_code(company_id, "PR")
        self.db.execute(text(
            "INSERT INTO dbp_payroll_runs (id, tenant_id, company_id, run_number, "
            "pay_period_start, pay_period_end, status) "
            "VALUES (:id, :tid, :cid, :rn, :ps, :pe, 'draft')"
        ), {"id": rid, "tid": tenant_id, "cid": company_id, "rn": run_number,
            "ps": pay_period_start, "pe": pay_period_end})
        self.db.flush()
        return rid

    def add_payroll_line(self, tenant_id: str, run_id: str, employee_id: str,
                         basic_salary: float, allowances: float = 0,
                         bonus: float = 0, deductions: float = 0,
                         tax: float = 0) -> str:
        run = self.db.execute(text(
            "SELECT id FROM dbp_payroll_runs WHERE id = :rid AND tenant_id = :tid"
        ), {"rid": run_id, "tid": tenant_id}).fetchone()
        if not run:
            raise ValueError("Payroll run not found")
        net_pay = float(basic_salary) + float(allowances) + float(bonus) \
            - float(deductions) - float(tax)
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_payroll_lines (id, tenant_id, run_id, employee_id, "
            "basic_salary, allowances, bonus, deductions, tax, net_pay) "
            "VALUES (:id, :tid, :rid, :eid, :bs, :al, :bo, :de, :tx, :np)"
        ), {"id": lid, "tid": tenant_id, "rid": run_id, "eid": employee_id,
            "bs": basic_salary, "al": allowances, "bo": bonus,
            "de": deductions, "tx": tax, "np": net_pay})
        gross = float(basic_salary) + float(allowances) + float(bonus)
        total_ded = float(deductions) + float(tax)
        self.db.execute(text(
            "UPDATE dbp_payroll_runs SET total_gross = total_gross + :g, "
            "total_deductions = total_deductions + :d, total_net = total_net + :n "
            "WHERE id = :rid"
        ), {"g": gross, "d": total_ded, "n": net_pay, "rid": run_id})
        self.db.flush()
        return lid

    def get_payroll_run(self, run_id: str, tenant_id: str = None) -> Optional[Dict]:
        params: Dict[str, Any] = {"rid": run_id}
        tscope = ""
        if tenant_id:
            tscope = " AND tenant_id = :tid"
            params["tid"] = tenant_id
        row = self.db.execute(text(
            "SELECT id, tenant_id, company_id, run_number, pay_period_start, "
            "pay_period_end, status, total_gross, total_deductions, total_net, "
            "processed_by, created_at FROM dbp_payroll_runs WHERE id = :rid" + tscope
        ), params).fetchone()
        if not row:
            return None
        lines = self.db.execute(text(
            "SELECT pl.id, pl.employee_id, e.first_name, e.last_name, "
            "pl.basic_salary, pl.allowances, pl.bonus, pl.deductions, pl.tax, pl.net_pay "
            "FROM dbp_payroll_lines pl "
            "LEFT JOIN dbp_employees e ON pl.employee_id = e.id "
            "WHERE pl.run_id = :rid ORDER BY pl.id"
        ), {"rid": run_id}).fetchall()
        return {"id": row[0], "tenant_id": row[1], "company_id": row[2],
                "run_number": row[3],
                "pay_period_start": row[4].isoformat() if row[4] else None,
                "pay_period_end": row[5].isoformat() if row[5] else None,
                "status": row[6],
                "total_gross": float(row[7]) if row[7] is not None else 0,
                "total_deductions": float(row[8]) if row[8] is not None else 0,
                "total_net": float(row[9]) if row[9] is not None else 0,
                "processed_by": row[10],
                "created_at": row[11].isoformat() if row[11] else None,
                "lines": [{"id": l[0], "employee_id": l[1],
                           "employee_name": f"{l[2]} {l[3]}" if l[2] else None,
                           "basic_salary": float(l[4]) if l[4] is not None else 0,
                           "allowances": float(l[5]) if l[5] is not None else 0,
                           "bonus": float(l[6]) if l[6] is not None else 0,
                           "deductions": float(l[7]) if l[7] is not None else 0,
                           "tax": float(l[8]) if l[8] is not None else 0,
                           "net_pay": float(l[9]) if l[9] is not None else 0} for l in lines]}

    def list_payroll_runs(self, company_id: str, tenant_id: str = None) -> List[Dict]:
        conditions = ["company_id = :cid"]
        params: Dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, run_number, pay_period_start, pay_period_end, status, "
            f"total_gross, total_deductions, total_net, created_at "
            f"FROM dbp_payroll_runs WHERE {where} ORDER BY created_at DESC"
        ), params).fetchall()
        return [{"id": r[0], "run_number": r[1],
                 "pay_period_start": r[2].isoformat() if r[2] else None,
                 "pay_period_end": r[3].isoformat() if r[3] else None,
                 "status": r[4],
                 "total_gross": float(r[5]) if r[5] is not None else 0,
                 "total_deductions": float(r[6]) if r[6] is not None else 0,
                 "total_net": float(r[7]) if r[7] is not None else 0,
                 "created_at": r[8].isoformat() if r[8] else None} for r in rows]

    # ── HELPERS ──

    def _next_code(self, company_id: str, prefix: str) -> str:
        table_map = {
            "EMP": ("dbp_employees", "employee_code"),
            "PR": ("dbp_payroll_runs", "run_number")}
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
