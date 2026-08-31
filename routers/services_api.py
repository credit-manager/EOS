"""
P70.9.2 Services ERP Professional — API
=========================================
40+ endpoints: CRM, Leads, Opportunities, Quotations, Contracts,
Projects, Tasks, Milestones, Skills, Allocations, Timesheets,
Expenses, Invoices, Profitability, Dashboard.
Cross-platform: CRM → Core CRM, Accounting → Core Accounting.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

from database import SessionLocal, get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import (
    now, uid, get_company_id, check_permission,
    audit_log, post_journal,
    success_response, list_response, error_response,
    get_tenant_config,
)

router = APIRouter(prefix="/services", tags=["Services ERP"])


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _next_code(db, tenant_id, table, prefix):
    row = db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id=:t"), {"t": tenant_id}).fetchone()
    n = (row[0] or 0) + 1
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{n:04d}"


# ═══════════════════════════════════════════════════
# CRM: CLIENTS
# ═══════════════════════════════════════════════════

class ClientCreate(BaseModel):
    client_code: str
    name: str
    name_ar: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    credit_limit: float = Field(default=0, ge=0)
    source: Optional[str] = None
    notes: Optional[str] = None

@router.post("/clients")
def create_client(body: ClientCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_svc_clients WHERE tenant_id=:t AND client_code=:c"),
                          {"t": t, "c": body.client_code}).fetchone()
    if existing:
        raise HTTPException(400, detail="Client code already exists")
    cid = uid()
    db.execute(text("INSERT INTO dbp_svc_clients "
                    "(id,tenant_id,client_code,name,name_ar,industry,website,phone,email,address,contact_person,credit_limit,source,notes,created_by) "
                    "VALUES (:id,:t,:cc,:n,:na,:i,:w,:p,:e,:a,:cp,:cl,:s,:nt,:cb)"),
               {"id": cid, "t": t, "cc": body.client_code, "n": body.name, "na": body.name_ar,
                "i": body.industry, "w": body.website, "p": body.phone, "e": body.email,
                "a": body.address, "cp": body.contact_person, "cl": body.credit_limit,
                "s": body.source, "nt": body.notes, "cb": user["id"]})
    audit_log(db, t, user["id"], "create", "svc_client", cid, new_values={"client_code": body.client_code})
    db.commit()
    return success_response("Client created", {"id": cid, "client_code": body.client_code})

@router.get("/clients")
def list_clients(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,client_code,name,industry,status,credit_limit,source "
                           "FROM dbp_svc_clients WHERE tenant_id=:t ORDER BY client_code"), {"t": t}).fetchall()
    data = [{"id": r[0], "client_code": r[1], "name": r[2], "industry": r[3],
             "status": r[4], "credit_limit": float(r[5] or 0), "source": r[6]} for r in rows]
    return list_response(data, len(data))

@router.get("/clients/{client_id}")
def get_client(client_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    c = db.execute(text("SELECT * FROM dbp_svc_clients WHERE id=:id AND tenant_id=:t"),
                   {"id": client_id, "t": t}).fetchone()
    if not c:
        raise HTTPException(404, detail="Client not found")
    return success_response("Client found", {
        "id": c[0], "client_code": c[2], "name": c[3], "name_ar": c[4],
        "industry": c[5], "website": c[6], "phone": c[7], "email": c[8],
        "address": c[9], "contact_person": c[10], "credit_limit": float(c[11] or 0),
        "status": c[12], "source": c[13], "notes": c[14],
    })


# ═══════════════════════════════════════════════════
# CRM: LEADS
# ═══════════════════════════════════════════════════

class LeadCreate(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    estimated_value: float = Field(default=0, ge=0)
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

@router.post("/leads")
def create_lead(body: LeadCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    lead_num = _next_code(db, t, "dbp_svc_leads", "LD")
    lid = uid()
    db.execute(text("INSERT INTO dbp_svc_leads "
                    "(id,tenant_id,lead_number,company_name,contact_name,email,phone,source,estimated_value,assigned_to,notes) "
                    "VALUES (:id,:t,:ln,:cn,:ct,:e,:p,:s,:ev,:at,:n)"),
               {"id": lid, "t": t, "ln": lead_num, "cn": body.company_name,
                "ct": body.contact_name, "e": body.email, "p": body.phone,
                "s": body.source, "ev": body.estimated_value, "at": body.assigned_to, "n": body.notes})
    audit_log(db, t, user["id"], "create", "svc_lead", lid, new_values={"lead_number": lead_num})
    db.commit()
    return success_response("Lead created", {"id": lid, "lead_number": lead_num})

@router.get("/leads")
def list_leads(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT id,lead_number,company_name,contact_name,status,priority,estimated_value,source "
                           f"FROM dbp_svc_leads {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "lead_number": r[1], "company_name": r[2], "contact_name": r[3],
             "status": r[4], "priority": r[5], "estimated_value": float(r[6] or 0), "source": r[7]}
            for r in rows]
    return list_response(data, len(data))

@router.put("/leads/{lead_id}/convert")
def convert_lead(lead_id: str, client_name: Optional[str] = None,
                 user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    lead = db.execute(text("SELECT id,company_name,contact_name,email,phone,estimated_value "
                           "FROM dbp_svc_leads WHERE id=:id AND tenant_id=:t"),
                      {"id": lead_id, "t": t}).fetchone()
    if not lead:
        raise HTTPException(404, detail="Lead not found")
    client_code = f"CLI-{datetime.now().strftime('%Y%m%d')}-{uid()[:6].upper()}"
    cid = uid()
    db.execute(text("INSERT INTO dbp_svc_clients "
                    "(id,tenant_id,client_code,name,phone,email,source,created_by) "
                    "VALUES (:id,:t,:cc,:n,:p,:e,:s,:cb)"),
               {"id": cid, "t": t, "cc": client_code, "n": client_name or lead[1],
                "p": lead[4], "e": lead[3], "s": "lead_conversion", "cb": user["id"]})
    db.execute(text("UPDATE dbp_svc_leads SET status='converted', updated_at=NOW() WHERE id=:id"), {"id": lead_id})
    audit_log(db, t, user["id"], "convert", "svc_lead", lead_id,
              new_values={"client_id": cid, "client_code": client_code})
    db.commit()
    return success_response("Lead converted to client", {"client_id": cid, "client_code": client_code})


# ═══════════════════════════════════════════════════
# CRM: OPPORTUNITIES
# ═══════════════════════════════════════════════════

class OpportunityCreate(BaseModel):
    client_id: Optional[str] = None
    lead_id: Optional[str] = None
    name: str
    stage: str = "qualification"
    probability: float = Field(default=50, ge=0, le=100)
    expected_value: float = Field(default=0, ge=0)
    close_date: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

@router.post("/opportunities")
def create_opportunity(body: OpportunityCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    opp_num = _next_code(db, t, "dbp_svc_opportunities", "OPP")
    oid = uid()
    db.execute(text("INSERT INTO dbp_svc_opportunities "
                    "(id,tenant_id,opp_number,client_id,lead_id,name,stage,probability,expected_value,close_date,assigned_to,notes) "
                    "VALUES (:id,:t,:on,:cid,:lid,:n,:st,:pr,:ev,:cd,:at,:nt)"),
               {"id": oid, "t": t, "on": opp_num, "cid": body.client_id, "lid": body.lead_id,
                "n": body.name, "st": body.stage, "pr": body.probability, "ev": body.expected_value,
                "cd": body.close_date, "at": body.assigned_to, "nt": body.notes})
    audit_log(db, t, user["id"], "create", "svc_opportunity", oid, new_values={"opp_number": opp_num})
    db.commit()
    return success_response("Opportunity created", {"id": oid, "opp_number": opp_num})

@router.get("/opportunities")
def list_opportunities(stage: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if stage:
        where += " AND stage=:s"
        params["s"] = stage
    rows = db.execute(text(f"SELECT id,opp_number,name,stage,probability,expected_value,close_date "
                           f"FROM dbp_svc_opportunities {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "opp_number": r[1], "name": r[2], "stage": r[3],
             "probability": float(r[4]), "expected_value": float(r[5] or 0),
             "close_date": str(r[6]) if r[6] else None} for r in rows]
    return list_response(data, len(data))

@router.put("/opportunities/{opp_id}/stage")
def update_opportunity_stage(opp_id: str, stage: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    valid_stages = {"qualification", "proposal", "negotiation", "closed_won", "closed_lost"}
    if stage not in valid_stages:
        raise HTTPException(400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    old = db.execute(text("SELECT stage FROM dbp_svc_opportunities WHERE id=:id AND tenant_id=:t"),
                     {"id": opp_id, "t": t}).fetchone()
    if not old:
        raise HTTPException(404, detail="Opportunity not found")
    db.execute(text("UPDATE dbp_svc_opportunities SET stage=:s, updated_at=NOW() WHERE id=:id"),
               {"s": stage, "id": opp_id})
    audit_log(db, t, user["id"], "update_stage", "svc_opportunity", opp_id,
              old_values={"stage": old[0]}, new_values={"stage": stage})
    db.commit()
    return success_response("Stage updated", {"stage": stage})


# ═══════════════════════════════════════════════════
# QUOTATIONS
# ═══════════════════════════════════════════════════

class QuoteLineCreate(BaseModel):
    description: str
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)
    discount_pct: float = Field(default=0, ge=0, le=100)

class QuoteCreate(BaseModel):
    client_id: str
    opportunity_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    valid_until: Optional[str] = None
    notes: Optional[str] = None
    lines: List[QuoteLineCreate] = []

@router.post("/quotations")
def create_quotation(body: QuoteCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    qnum = _next_code(db, t, "dbp_svc_quotations", "QT")
    qid = uid()
    total = 0
    for ln in body.lines:
        line_total = ln.quantity * ln.unit_price * (1 - ln.discount_pct / 100)
        total += line_total
    tax = total * 0.15
    grand = total + tax
    db.execute(text("INSERT INTO dbp_svc_quotations "
                    "(id,tenant_id,quote_number,client_id,opportunity_id,title,description,total,tax,grand_total,status,valid_until,notes,created_by) "
                    "VALUES (:id,:t,:qn,:cid,:oid,:ti,:d,:tt,:tx,:gt,'draft',:vu,:n,:cb)"),
               {"id": qid, "t": t, "qn": qnum, "cid": body.client_id, "oid": body.opportunity_id,
                "ti": body.title, "d": body.description, "tt": total, "tx": tax, "gt": grand,
                "vu": body.valid_until, "n": body.notes, "cb": user["id"]})
    for i, ln in enumerate(body.lines):
        lid = uid()
        lt = ln.quantity * ln.unit_price * (1 - ln.discount_pct / 100)
        db.execute(text("INSERT INTO dbp_svc_quote_lines (id,tenant_id,quote_id,description,quantity,unit_price,discount_pct,total,sort_order) "
                        "VALUES (:id,:t,:qi,:d,:q,:up,:dd,:lt,:so)"),
                   {"id": lid, "t": t, "qi": qid, "d": ln.description, "q": ln.quantity,
                    "up": ln.unit_price, "dd": ln.discount_pct, "lt": lt, "so": i})
    audit_log(db, t, user["id"], "create", "svc_quotation", qid, new_values={"quote_number": qnum, "total": grand})
    db.commit()
    return success_response("Quotation created", {"id": qid, "quote_number": qnum, "grand_total": grand})

@router.get("/quotations")
def list_quotations(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT id,quote_number,client_id,title,grand_total,status,valid_until "
                           f"FROM dbp_svc_quotations {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "quote_number": r[1], "client_id": r[2], "title": r[3],
             "grand_total": float(r[4] or 0), "status": r[5],
             "valid_until": str(r[6]) if r[6] else None} for r in rows]
    return list_response(data, len(data))

@router.put("/quotations/{quote_id}/accept")
def accept_quotation(quote_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    q = db.execute(text("SELECT id,status,client_id,grand_total FROM dbp_svc_quotations WHERE id=:id AND tenant_id=:t"),
                   {"id": quote_id, "t": t}).fetchone()
    if not q:
        raise HTTPException(404, detail="Quotation not found")
    if q[1] not in ('draft', 'sent'):
        raise HTTPException(400, detail="Only draft/sent quotations can be accepted")
    db.execute(text("UPDATE dbp_svc_quotations SET status='accepted', updated_at=NOW() WHERE id=:id"), {"id": quote_id})
    contract_code = _next_code(db, t, "dbp_svc_contracts", "CTR")
    contr_id = uid()
    db.execute(text("INSERT INTO dbp_svc_contracts "
                    "(id,tenant_id,contract_number,client_id,title,contract_type,value,status,created_by) "
                    "VALUES (:id,:t,:cc,:cid,:ti,'fixed_price',:v,'active',:cb)"),
               {"id": contr_id, "t": t, "cc": contract_code, "cid": q[2],
                "ti": f"Contract from {quote_id[:8]}", "v": q[3], "cb": user["id"]})
    audit_log(db, t, user["id"], "accept", "svc_quotation", quote_id,
              new_values={"status": "accepted", "contract_id": contr_id})
    db.commit()
    return success_response("Quotation accepted, contract created",
                            {"contract_id": contr_id, "contract_number": contract_code})


# ═══════════════════════════════════════════════════
# CONTRACTS
# ═══════════════════════════════════════════════════

class ContractCreate(BaseModel):
    client_id: str
    title: str
    contract_type: str = "fixed_price"
    value: float = Field(default=0, ge=0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    billing_cycle: str = "monthly"
    auto_renew: bool = False
    notes: Optional[str] = None

@router.post("/contracts")
def create_contract(body: ContractCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    cnum = _next_code(db, t, "dbp_svc_contracts", "CTR")
    cid = uid()
    db.execute(text("INSERT INTO dbp_svc_contracts "
                    "(id,tenant_id,contract_number,client_id,title,contract_type,value,start_date,end_date,billing_cycle,auto_renew,status,notes,created_by) "
                    "VALUES (:id,:t,:cn,:cli,:ti,:ct,:v,:sd,:ed,:bc,:ar,'draft',:n,:cb)"),
               {"id": cid, "t": t, "cn": cnum, "cli": body.client_id, "ti": body.title,
                "ct": body.contract_type, "v": body.value, "sd": body.start_date,
                "ed": body.end_date, "bc": body.billing_cycle, "ar": body.auto_renew,
                "n": body.notes, "cb": user["id"]})
    audit_log(db, t, user["id"], "create", "svc_contract", cid, new_values={"contract_number": cnum})
    db.commit()
    return success_response("Contract created", {"id": cid, "contract_number": cnum})

@router.get("/contracts")
def list_contracts(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT id,contract_number,client_id,title,contract_type,value,status,start_date,end_date "
                           f"FROM dbp_svc_contracts {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "contract_number": r[1], "client_id": r[2], "title": r[3],
             "contract_type": r[4], "value": float(r[5] or 0), "status": r[6],
             "start_date": str(r[7]) if r[7] else None, "end_date": str(r[8]) if r[8] else None}
            for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# PROJECTS
# ═══════════════════════════════════════════════════

class ProjectCreate(BaseModel):
    name: str
    client_id: Optional[str] = None
    contract_id: Optional[str] = None
    project_type: str = "time_material"
    budget: float = Field(default=0, ge=0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    manager_id: Optional[str] = None
    description: Optional[str] = None

@router.post("/projects")
def create_project(body: ProjectCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    pcode = _next_code(db, t, "dbp_svc_projects", "PRJ")
    pid = uid()
    db.execute(text("INSERT INTO dbp_svc_projects "
                    "(id,tenant_id,project_code,name,client_id,contract_id,project_type,budget,status,priority,start_date,end_date,manager_id,description,created_by) "
                    "VALUES (:id,:t,:pc,:n,:ci,:cti,:pt,:b,'planning',5,:sd,:ed,:mi,:d,:cb)"),
               {"id": pid, "t": t, "pc": pcode, "n": body.name, "ci": body.client_id,
                "cti": body.contract_id, "pt": body.project_type, "b": body.budget,
                "sd": body.start_date, "ed": body.end_date, "mi": body.manager_id,
                "d": body.description, "cb": user["id"]})
    audit_log(db, t, user["id"], "create", "svc_project", pid, new_values={"project_code": pcode})
    db.commit()
    return success_response("Project created", {"id": pid, "project_code": pcode})

@router.get("/projects")
def list_projects(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT p.id,p.project_code,p.name,p.client_id,p.project_type,p.budget,p.spent,"
                           f"p.status,p.priority,p.start_date,p.end_date,p.manager_id "
                           f"FROM dbp_svc_projects p {where} ORDER BY p.created_at DESC"), params).fetchall()
    data = [{"id": r[0], "project_code": r[1], "name": r[2], "client_id": r[3],
             "project_type": r[4], "budget": float(r[5] or 0), "spent": float(r[6] or 0),
             "status": r[7], "priority": r[8],
             "start_date": str(r[9]) if r[9] else None, "end_date": str(r[10]) if r[10] else None,
             "manager_id": r[11]} for r in rows]
    return list_response(data, len(data))

@router.put("/projects/{project_id}/status")
def update_project_status(project_id: str, status: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    valid = {"planning", "active", "on_hold", "completed", "cancelled"}
    if status not in valid:
        raise HTTPException(400, detail=f"Invalid status. Must be one of: {valid}")
    old = db.execute(text("SELECT status FROM dbp_svc_projects WHERE id=:id AND tenant_id=:t"),
                     {"id": project_id, "t": t}).fetchone()
    if not old:
        raise HTTPException(404, detail="Project not found")
    db.execute(text("UPDATE dbp_svc_projects SET status=:s, updated_at=NOW() WHERE id=:id"), {"s": status, "id": project_id})
    audit_log(db, t, user["id"], "update_status", "svc_project", project_id,
              old_values={"status": old[0]}, new_values={"status": status})
    db.commit()
    return success_response("Project status updated", {"status": status})


# ═══════════════════════════════════════════════════
# PROJECT TASKS
# ═══════════════════════════════════════════════════

class TaskCreate(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    task_type: str = "task"
    assigned_to: Optional[str] = None
    estimated_hours: float = Field(default=0, ge=0)
    start_date: Optional[str] = None
    due_date: Optional[str] = None

@router.post("/tasks")
def create_task(body: TaskCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    tid = uid()
    row = db.execute(text("SELECT COUNT(*) FROM dbp_svc_project_tasks WHERE project_id=:pid"),
                     {"pid": body.project_id}).fetchone()
    sort_order = (row[0] or 0) + 1
    db.execute(text("INSERT INTO dbp_svc_project_tasks "
                    "(id,tenant_id,project_id,name,description,task_type,assigned_to,estimated_hours,start_date,due_date,sort_order) "
                    "VALUES (:id,:t,:pid,:n,:d,:tt,:at,:eh,:sd,:dd,:so)"),
               {"id": tid, "t": t, "pid": body.project_id, "n": body.name, "d": body.description,
                "tt": body.task_type, "at": body.assigned_to, "eh": body.estimated_hours,
                "sd": body.start_date, "dd": body.due_date, "so": sort_order})
    audit_log(db, t, user["id"], "create", "svc_task", tid, new_values={"name": body.name})
    db.commit()
    return success_response("Task created", {"id": tid})

@router.get("/tasks/{project_id}")
def list_tasks(project_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,task_type,status,priority,assigned_to,estimated_hours,actual_hours,due_date "
                           "FROM dbp_svc_project_tasks WHERE project_id=:pid ORDER BY sort_order"),
                      {"pid": project_id}).fetchall()
    data = [{"id": r[0], "name": r[1], "task_type": r[2], "status": r[3], "priority": r[4],
             "assigned_to": r[5], "estimated_hours": float(r[6] or 0),
             "actual_hours": float(r[7] or 0), "due_date": str(r[8]) if r[8] else None}
            for r in rows]
    return list_response(data, len(data))

@router.put("/tasks/{task_id}/status")
def update_task_status(task_id: str, status: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    valid = {"todo", "in_progress", "review", "done", "blocked"}
    if status not in valid:
        raise HTTPException(400, detail=f"Invalid status. Must be one of: {valid}")
    old = db.execute(text("SELECT status FROM dbp_svc_project_tasks WHERE id=:id AND tenant_id=:t"),
                     {"id": task_id, "t": t}).fetchone()
    if not old:
        raise HTTPException(404, detail="Task not found")
    db.execute(text("UPDATE dbp_svc_project_tasks SET status=:s, updated_at=NOW() WHERE id=:id"), {"s": status, "id": task_id})
    audit_log(db, t, user["id"], "update_status", "svc_task", task_id,
              old_values={"status": old[0]}, new_values={"status": status})
    db.commit()
    return success_response("Task status updated", {"status": status})


# ═══════════════════════════════════════════════════
# MILESTONES
# ═══════════════════════════════════════════════════

class MilestoneCreate(BaseModel):
    project_id: str
    name: str
    due_date: Optional[str] = None
    amount: float = Field(default=0, ge=0)

@router.post("/milestones")
def create_milestone(body: MilestoneCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    mid = uid()
    db.execute(text("INSERT INTO dbp_svc_milestones (id,tenant_id,project_id,name,due_date,amount) "
                    "VALUES (:id,:t,:pid,:n,:dd,:a)"),
               {"id": mid, "t": t, "pid": body.project_id, "n": body.name,
                "dd": body.due_date, "a": body.amount})
    audit_log(db, t, user["id"], "create", "svc_milestone", mid, new_values={"name": body.name})
    db.commit()
    return success_response("Milestone created", {"id": mid})

@router.get("/milestones/{project_id}")
def list_milestones(project_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,due_date,amount,status,completed_at "
                           "FROM dbp_svc_milestones WHERE project_id=:pid ORDER BY due_date"),
                      {"pid": project_id}).fetchall()
    data = [{"id": r[0], "name": r[1], "due_date": str(r[2]) if r[2] else None,
             "amount": float(r[3] or 0), "status": r[4],
             "completed_at": str(r[5]) if r[5] else None} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# SKILLS
# ═══════════════════════════════════════════════════

@router.post("/skills")
def create_skill(name: str, category: Optional[str] = None,
                 user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    sid = uid()
    db.execute(text("INSERT INTO dbp_svc_skills (id,tenant_id,name,category) VALUES (:id,:t,:n,:c)"),
               {"id": sid, "t": t, "n": name, "c": category})
    audit_log(db, t, user["id"], "create", "svc_skill", sid, new_values={"name": name})
    db.commit()
    return success_response("Skill created", {"id": sid})

@router.get("/skills")
def list_skills(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,category FROM dbp_svc_skills WHERE tenant_id=:t ORDER BY name"), {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "category": r[2]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# RESOURCE ALLOCATIONS
# ═══════════════════════════════════════════════════

class AllocationCreate(BaseModel):
    employee_id: str
    project_id: str
    allocation_pct: float = Field(default=100, gt=0, le=100)
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@router.post("/allocations")
def create_allocation(body: AllocationCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    aid = uid()
    db.execute(text("INSERT INTO dbp_svc_resource_allocations "
                    "(id,tenant_id,employee_id,project_id,allocation_pct,start_date,end_date) "
                    "VALUES (:id,:t,:eid,:pid,:ap,:sd,:ed)"),
               {"id": aid, "t": t, "eid": body.employee_id, "pid": body.project_id,
                "ap": body.allocation_pct, "sd": body.start_date, "ed": body.end_date})
    audit_log(db, t, user["id"], "create", "svc_allocation", aid)
    db.commit()
    return success_response("Allocation created", {"id": aid})

@router.get("/allocations")
def list_allocations(project_id: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if project_id:
        where += " AND project_id=:pid"
        params["pid"] = project_id
    rows = db.execute(text(f"SELECT id,employee_id,project_id,allocation_pct,start_date,end_date,status "
                           f"FROM dbp_svc_resource_allocations {where}"), params).fetchall()
    data = [{"id": r[0], "employee_id": r[1], "project_id": r[2],
             "allocation_pct": float(r[3]), "start_date": str(r[4]) if r[4] else None,
             "end_date": str(r[5]) if r[5] else None, "status": r[6]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# TIMESHEETS
# ═══════════════════════════════════════════════════

class TimesheetLineCreate(BaseModel):
    project_id: str
    task_id: Optional[str] = None
    work_date: str
    hours: float = Field(gt=0)
    billable: bool = True
    description: Optional[str] = None

class TimesheetCreate(BaseModel):
    employee_id: str
    week_start: str
    week_end: str
    lines: List[TimesheetLineCreate] = []

@router.post("/timesheets")
def create_timesheet(body: TimesheetCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    ts_num = _next_code(db, t, "dbp_svc_timesheets", "TS")
    tsid = uid()
    total_h = sum(l.hours for l in body.lines)
    billable_h = sum(l.hours for l in body.lines if l.billable)
    db.execute(text("INSERT INTO dbp_svc_timesheets "
                    "(id,tenant_id,timesheet_number,employee_id,week_start,week_end,total_hours,billable_hours,status) "
                    "VALUES (:id,:t,:tn,:eid,:ws,:we,:th,:bh,'draft')"),
               {"id": tsid, "t": t, "tn": ts_num, "eid": body.employee_id,
                "ws": body.week_start, "we": body.week_end, "th": total_h, "bh": billable_h})
    for i, ln in enumerate(body.lines):
        lid = uid()
        db.execute(text("INSERT INTO dbp_svc_timesheet_lines "
                        "(id,tenant_id,timesheet_id,project_id,task_id,work_date,hours,billable,description) "
                        "VALUES (:id,:t,:tsid,:pid,:tid,:wd,:h,:b,:d)"),
                   {"id": lid, "t": t, "tsid": tsid, "pid": ln.project_id, "tid": ln.task_id,
                    "wd": ln.work_date, "h": ln.hours, "b": ln.billable, "d": ln.description})
    audit_log(db, t, user["id"], "create", "svc_timesheet", tsid,
              new_values={"timesheet_number": ts_num, "total_hours": total_h})
    db.commit()
    return success_response("Timesheet created", {"id": tsid, "timesheet_number": ts_num, "total_hours": total_h})

@router.get("/timesheets")
def list_timesheets(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT id,timesheet_number,employee_id,week_start,week_end,total_hours,billable_hours,status "
                           f"FROM dbp_svc_timesheets {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "timesheet_number": r[1], "employee_id": r[2],
             "week_start": str(r[3]) if r[3] else None, "week_end": str(r[4]) if r[4] else None,
             "total_hours": float(r[5] or 0), "billable_hours": float(r[6] or 0), "status": r[7]}
            for r in rows]
    return list_response(data, len(data))

@router.put("/timesheets/{ts_id}/submit")
def submit_timesheet(ts_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    ts = db.execute(text("SELECT status FROM dbp_svc_timesheets WHERE id=:id AND tenant_id=:t"),
                    {"id": ts_id, "t": t}).fetchone()
    if not ts:
        raise HTTPException(404, detail="Timesheet not found")
    if ts[0] != 'draft':
        raise HTTPException(400, detail="Only draft timesheets can be submitted")
    db.execute(text("UPDATE dbp_svc_timesheets SET status='submitted', submitted_at=NOW() WHERE id=:id"), {"id": ts_id})
    audit_log(db, t, user["id"], "submit", "svc_timesheet", ts_id, new_values={"status": "submitted"})
    db.commit()
    return success_response("Timesheet submitted", {"id": ts_id})

@router.put("/timesheets/{ts_id}/approve")
def approve_timesheet(ts_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    ts = db.execute(text("SELECT status FROM dbp_svc_timesheets WHERE id=:id AND tenant_id=:t"),
                    {"id": ts_id, "t": t}).fetchone()
    if not ts:
        raise HTTPException(404, detail="Timesheet not found")
    if ts[0] != 'submitted':
        raise HTTPException(400, detail="Only submitted timesheets can be approved")
    db.execute(text("UPDATE dbp_svc_timesheets SET status='approved', approved_by=:ab, approved_at=NOW() WHERE id=:id"),
               {"ab": user["id"], "id": ts_id})
    audit_log(db, t, user["id"], "approve", "svc_timesheet", ts_id, new_values={"status": "approved"})
    db.commit()
    return success_response("Timesheet approved", {"id": ts_id})


# ═══════════════════════════════════════════════════
# EXPENSES
# ═══════════════════════════════════════════════════

class ExpenseCreate(BaseModel):
    employee_id: str
    project_id: Optional[str] = None
    category: str
    amount: float = Field(gt=0)
    expense_date: str
    description: Optional[str] = None
    receipt_ref: Optional[str] = None

@router.post("/expenses")
def create_expense(body: ExpenseCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    valid_cats = {"travel", "meals", "office", "software", "hardware", "other"}
    if body.category not in valid_cats:
        raise HTTPException(400, detail=f"Invalid category. Must be one of: {valid_cats}")
    exp_num = _next_code(db, t, "dbp_svc_expenses", "EXP")
    eid = uid()
    db.execute(text("INSERT INTO dbp_svc_expenses "
                    "(id,tenant_id,expense_number,employee_id,project_id,category,amount,expense_date,description,receipt_ref) "
                    "VALUES (:id,:t,:en,:eid,:pid,:cat,:a,:ed,:d,:rr)"),
               {"id": eid, "t": t, "en": exp_num, "eid": body.employee_id, "pid": body.project_id,
                "cat": body.category, "a": body.amount, "ed": body.expense_date,
                "d": body.description, "rr": body.receipt_ref})
    audit_log(db, t, user["id"], "create", "svc_expense", eid,
              new_values={"expense_number": exp_num, "amount": body.amount})
    db.commit()
    return success_response("Expense created", {"id": eid, "expense_number": exp_num})

@router.get("/expenses")
def list_expenses(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT id,expense_number,employee_id,project_id,category,amount,expense_date,status "
                           f"FROM dbp_svc_expenses {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "expense_number": r[1], "employee_id": r[2], "project_id": r[3],
             "category": r[4], "amount": float(r[5] or 0), "expense_date": str(r[6]) if r[6] else None,
             "status": r[7]} for r in rows]
    return list_response(data, len(data))

@router.put("/expenses/{exp_id}/approve")
def approve_expense(exp_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    exp = db.execute(text("SELECT status FROM dbp_svc_expenses WHERE id=:id AND tenant_id=:t"),
                     {"id": exp_id, "t": t}).fetchone()
    if not exp:
        raise HTTPException(404, detail="Expense not found")
    if exp[0] not in ('draft', 'submitted'):
        raise HTTPException(400, detail="Only draft/submitted expenses can be approved")
    db.execute(text("UPDATE dbp_svc_expenses SET status='approved', approved_by=:ab, approved_at=NOW() WHERE id=:id"),
               {"ab": user["id"], "id": exp_id})
    audit_log(db, t, user["id"], "approve", "svc_expense", exp_id, new_values={"status": "approved"})
    db.commit()
    return success_response("Expense approved", {"id": exp_id})


# ═══════════════════════════════════════════════════
# SERVICE INVOICES
# ═══════════════════════════════════════════════════

class InvoiceLineCreate(BaseModel):
    description: str
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)
    timesheet_line_id: Optional[str] = None
    expense_id: Optional[str] = None

class InvoiceCreate(BaseModel):
    client_id: str
    project_id: Optional[str] = None
    contract_id: Optional[str] = None
    invoice_type: str = "time_material"
    due_date: Optional[str] = None
    notes: Optional[str] = None
    lines: List[InvoiceLineCreate] = []

@router.post("/invoices")
def create_invoice(body: InvoiceCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    inv_num = _next_code(db, t, "dbp_svc_invoices", "SINV")
    inv_id = uid()
    subtotal = sum(l.quantity * l.unit_price for l in body.lines)
    tax = subtotal * 0.15
    total = subtotal + tax
    db.execute(text("INSERT INTO dbp_svc_invoices "
                    "(id,tenant_id,invoice_number,client_id,project_id,contract_id,invoice_type,subtotal,tax,total,balance,status,due_date,notes,created_by) "
                    "VALUES (:id,:t,:in,:cid,:pid,:cti,:it,:st,:tx,:t2,:b2,'draft',:dd,:n,:cb)"),
               {"id": inv_id, "t": t, "in": inv_num, "cid": body.client_id, "pid": body.project_id,
                "cti": body.contract_id, "it": body.invoice_type, "st": subtotal, "tx": tax,
                "t2": total, "b2": total, "dd": body.due_date, "n": body.notes, "cb": user["id"]})
    for i, ln in enumerate(body.lines):
        lid = uid()
        lt = ln.quantity * ln.unit_price
        db.execute(text("INSERT INTO dbp_svc_invoice_lines "
                        "(id,tenant_id,invoice_id,description,quantity,unit_price,total,timesheet_line_id,expense_id,sort_order) "
                        "VALUES (:id,:t,:ii,:d,:q,:up,:tl,:tsl,:ei,:so)"),
                   {"id": lid, "t": t, "ii": inv_id, "d": ln.description, "q": ln.quantity,
                    "up": ln.unit_price, "tl": lt, "tsl": ln.timesheet_line_id,
                    "ei": ln.expense_id, "so": i})
    audit_log(db, t, user["id"], "create", "svc_invoice", inv_id,
              new_values={"invoice_number": inv_num, "total": total})
    db.commit()
    return success_response("Invoice created", {"id": inv_id, "invoice_number": inv_num, "total": total})

@router.get("/invoices")
def list_invoices(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT id,invoice_number,client_id,project_id,invoice_type,total,paid_amount,balance,status,due_date "
                           f"FROM dbp_svc_invoices {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "invoice_number": r[1], "client_id": r[2], "project_id": r[3],
             "invoice_type": r[4], "total": float(r[5] or 0), "paid_amount": float(r[6] or 0),
             "balance": float(r[7] or 0), "status": r[8],
             "due_date": str(r[9]) if r[9] else None} for r in rows]
    return list_response(data, len(data))

@router.put("/invoices/{inv_id}/send")
def send_invoice(inv_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    inv = db.execute(text("SELECT status FROM dbp_svc_invoices WHERE id=:id AND tenant_id=:t"),
                     {"id": inv_id, "t": t}).fetchone()
    if not inv:
        raise HTTPException(404, detail="Invoice not found")
    if inv[0] != 'draft':
        raise HTTPException(400, detail="Only draft invoices can be sent")
    db.execute(text("UPDATE dbp_svc_invoices SET status='sent', updated_at=NOW() WHERE id=:id"), {"id": inv_id})
    audit_log(db, t, user["id"], "send", "svc_invoice", inv_id, new_values={"status": "sent"})
    db.commit()
    return success_response("Invoice sent", {"id": inv_id})

@router.put("/invoices/{inv_id}/pay")
def pay_invoice(inv_id: str, amount: float = Query(gt=0),
                user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    inv = db.execute(text("SELECT id,total,paid_amount,balance,status FROM dbp_svc_invoices WHERE id=:id AND tenant_id=:t"),
                     {"id": inv_id, "t": t}).fetchone()
    if not inv:
        raise HTTPException(404, detail="Invoice not found")
    if inv[4] not in ('sent', 'overdue'):
        raise HTTPException(400, detail="Only sent/overdue invoices can be paid")
    new_paid = float(inv[2] or 0) + amount
    new_balance = float(inv[1] or 0) - new_paid
    new_status = 'paid' if new_balance <= 0 else 'sent'
    db.execute(text("UPDATE dbp_svc_invoices SET paid_amount=:pa, balance=:b, status=:s, paid_date=NOW(), updated_at=NOW() WHERE id=:id"),
               {"pa": new_paid, "b": max(0, new_balance), "s": new_status, "id": inv_id})
    company_id = get_company_id(db, t)
    post_journal(db, t, company_id, "svc_invoice_payment", f"Payment {inv_id[:8]}",
                 [{"account_code": "1000", "description": "Cash", "debit": amount},
                  {"account_code": "4000", "description": "Service Revenue", "credit": amount}])
    audit_log(db, t, user["id"], "pay", "svc_invoice", inv_id,
              new_values={"amount": amount, "new_status": new_status})
    db.commit()
    return success_response("Payment recorded", {"paid": amount, "status": new_status})


# ═══════════════════════════════════════════════════
# PROFITABILITY
# ═══════════════════════════════════════════════════

@router.get("/profitability/{project_id}")
def get_profitability(project_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    proj = db.execute(text("SELECT id,budget,spent FROM dbp_svc_projects WHERE id=:pid AND tenant_id=:t"),
                      {"pid": project_id, "t": t}).fetchone()
    if not proj:
        raise HTTPException(404, detail="Project not found")

    inv_row = db.execute(text("SELECT COALESCE(SUM(total),0) FROM dbp_svc_invoices WHERE project_id=:pid AND status IN ('sent','paid')"),
                         {"pid": project_id}).fetchone()
    revenue = float(inv_row[0] or 0)

    # Fixed H13: labor rate is now configurable per tenant (default 50).
    labor_rate = float(get_tenant_config(db, t, "labor_rate", 50.0))
    labor = db.execute(text("SELECT COALESCE(SUM(sl.hours * :rate),0) FROM dbp_svc_timesheet_lines sl "
                            "JOIN dbp_svc_timesheets ts ON sl.timesheet_id=ts.id "
                            "WHERE sl.project_id=:pid AND ts.status='approved'"),
                       {"pid": project_id, "rate": labor_rate}).fetchone()
    labor_cost = float(labor[0] or 0)

    exp = db.execute(text("SELECT COALESCE(SUM(amount),0) FROM dbp_svc_expenses WHERE project_id=:pid AND status='approved'"),
                     {"pid": project_id}).fetchone()
    expense_cost = float(exp[0] or 0)

    total_cost = labor_cost + expense_cost
    profit = revenue - total_cost
    margin = (profit / revenue * 100) if revenue > 0 else 0

    pid = uid()
    db.execute(text("DELETE FROM dbp_svc_profitability WHERE project_id=:pid"), {"pid": project_id})
    db.execute(text("INSERT INTO dbp_svc_profitability "
                    "(id,tenant_id,project_id,revenue,labor_cost,expense_cost,profit,margin_pct) "
                    "VALUES (:id,:t,:pid,:rev,:lc,:ec,:p,:m)"),
               {"id": pid, "t": t, "pid": project_id, "rev": revenue, "lc": labor_cost,
                "ec": expense_cost, "p": profit, "m": margin})
    db.commit()
    return success_response("Profitability calculated", {
        "project_id": project_id, "revenue": revenue, "labor_cost": labor_cost,
        "expense_cost": expense_cost, "total_cost": total_cost,
        "profit": profit, "margin_pct": round(margin, 1),
    })


# ═══════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════

@router.get("/dashboard")
def services_dashboard(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]

    clients = db.execute(text("SELECT COUNT(*) FROM dbp_svc_clients WHERE tenant_id=:t AND status='active'"), {"t": t}).fetchone()[0] or 0
    leads_new = db.execute(text("SELECT COUNT(*) FROM dbp_svc_leads WHERE tenant_id=:t AND status='new'"), {"t": t}).fetchone()[0] or 0
    leads_total = db.execute(text("SELECT COUNT(*) FROM dbp_svc_leads WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    opps = db.execute(text("SELECT COUNT(*) FROM dbp_svc_opportunities WHERE tenant_id=:t AND stage NOT IN ('closed_won','closed_lost')"), {"t": t}).fetchone()[0] or 0
    opps_value = db.execute(text("SELECT COALESCE(SUM(expected_value),0) FROM dbp_svc_opportunities WHERE tenant_id=:t AND stage NOT IN ('closed_won','closed_lost')"), {"t": t}).fetchone()[0] or 0

    projects_active = db.execute(text("SELECT COUNT(*) FROM dbp_svc_projects WHERE tenant_id=:t AND status='active'"), {"t": t}).fetchone()[0] or 0
    projects_budget = db.execute(text("SELECT COALESCE(SUM(budget),0) FROM dbp_svc_projects WHERE tenant_id=:t AND status='active'"), {"t": t}).fetchone()[0] or 0

    ts_pending = db.execute(text("SELECT COUNT(*) FROM dbp_svc_timesheets WHERE tenant_id=:t AND status='submitted'"), {"t": t}).fetchone()[0] or 0
    exp_pending = db.execute(text("SELECT COUNT(*) FROM dbp_svc_expenses WHERE tenant_id=:t AND status='submitted'"), {"t": t}).fetchone()[0] or 0

    inv_sent = db.execute(text("SELECT COUNT(*) FROM dbp_svc_invoices WHERE tenant_id=:t AND status='sent'"), {"t": t}).fetchone()[0] or 0
    inv_overdue = db.execute(text("SELECT COUNT(*) FROM dbp_svc_invoices WHERE tenant_id=:t AND status='overdue'"), {"t": t}).fetchone()[0] or 0
    inv_total = db.execute(text("SELECT COALESCE(SUM(balance),0) FROM dbp_svc_invoices WHERE tenant_id=:t AND status IN ('sent','overdue')"), {"t": t}).fetchone()[0] or 0

    contracts = db.execute(text("SELECT COUNT(*) FROM dbp_svc_contracts WHERE tenant_id=:t AND status='active'"), {"t": t}).fetchone()[0] or 0

    return success_response("Services dashboard", {
        "crm": {"active_clients": clients, "new_leads": leads_new, "total_leads": leads_total, "open_opps": opps, "pipeline_value": float(opps_value)},
        "projects": {"active": projects_active, "total_budget": float(projects_budget)},
        "approvals": {"timesheets": ts_pending, "expenses": exp_pending},
        "invoicing": {"sent": inv_sent, "overdue": inv_overdue, "outstanding": float(inv_total)},
        "contracts": {"active": contracts},
    })
