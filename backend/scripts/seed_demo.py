#!/usr/bin/env python3
"""Seed demo data for the 2TO EOS platform.

Usage:
    python -m backend.scripts.seed_demo
    python -m backend.scripts.seed_demo --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> Any:
    r = client.request(method, path, **kwargs)
    if r.status_code == 204:
        return None
    try:
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        detail = getattr(exc.response, "text", str(exc))
        print(f"  ⚠ {method.upper()} {path} → {exc.response.status_code}: {detail[:200]}")
        raise


def authenticate(client: httpx.Client, email: str, password: str, tenant: str) -> str:
    print(f"[auth] Registering/login as {email} ...")
    try:
        data = _json(client, "POST", "/auth/register", json={
            "email": email, "password": password, "tenant_name": tenant,
        })
        print(f"  ✓ Registered: user_id={data['user_id']}")
        return data["access_token"]
    except Exception:
        pass

    data = _json(client, "POST", "/auth/token", json={"email": email, "password": password})
    print(f"  ✓ Logged in as {email}")
    return data["access_token"]


def has_entity(headers: dict[str, str], client: httpx.Client, code: str) -> bool:
    items = _json(client, "GET", "/metadata/entities", headers=headers)
    return any(e["code"] == code for e in items)


def has_workflow(headers: dict[str, str], client: httpx.Client, code: str) -> bool:
    items = _json(client, "GET", "/workflows/definitions", headers=headers)
    return any(d["code"] == code for d in items)


def has_rule(headers: dict[str, str], client: httpx.Client, name: str) -> bool:
    data = _json(client, "GET", "/rules", headers=headers)
    return any(r["name"] == name for r in data.get("items", []))


def has_report(headers: dict[str, str], client: httpx.Client, code: str) -> bool:
    items = _json(client, "GET", "/analytics/reports", headers=headers)
    return any(r["code"] == code for r in items)


def seed_workflow(client: httpx.Client, headers: dict[str, str], wf_code: str) -> None:
    if has_workflow(headers, client, wf_code):
        print(f"  ⏭ workflow '{wf_code}' exists — skipping")
        return
    print(f"[workflow] Creating '{wf_code}' ...")
    _json(client, "POST", "/workflows/definitions", headers=headers, json={
        "code": wf_code,
        "name": "Purchase Request Approval",
        "states": ["draft", "submitted", "approved", "rejected"],
        "initial_state": "draft",
        "transitions": [
            {
                "from_state": "draft",
                "to_state": "submitted",
                "action": "submit",
                "roles": ["admin", "member"],
                "requires_approval": True,
                "conditions": [],
                "actions": [],
            },
            {
                "from_state": "submitted",
                "to_state": "approved",
                "action": "approve",
                "roles": ["admin"],
                "requires_approval": False,
                "conditions": [],
                "actions": [],
            },
            {
                "from_state": "submitted",
                "to_state": "rejected",
                "action": "reject",
                "roles": ["admin"],
                "requires_approval": False,
                "conditions": [],
                "actions": [],
            },
        ],
    })
    print("  ✓ workflow created")


def seed_entities(client: httpx.Client, headers: dict[str, str], wf_code: str) -> None:
    # ---- supplier entity (simple, no workflow) ----
    if not has_entity(headers, client, "supplier"):
        print("[metadata] Creating 'supplier' entity ...")
        _json(client, "POST", "/metadata/entities", headers=headers, json={
            "code": "supplier",
            "name": "Supplier",
            "fields": [
                {"code": "name", "type": "text", "label": "Supplier Name", "required": True},
                {"code": "country", "type": "text", "label": "Country", "required": False},
            ],
        })
        _json(client, "POST", "/metadata/entities/supplier/publish", headers=headers)
        print("  ✓ supplier created + published")

    # ---- purchase_request entity with workflow binding + relation ----
    if not has_entity(headers, client, "purchase_request"):
        print("[metadata] Creating 'purchase_request' entity ...")
        _json(client, "POST", "/metadata/entities", headers=headers, json={
            "code": "purchase_request",
            "name": "Purchase Request",
            "fields": [
                {"code": "title",       "type": "text",    "label": "Title",       "required": True},
                {"code": "amount",      "type": "decimal", "label": "Amount",      "required": True},
                {"code": "status",      "type": "text",    "label": "Status",      "required": False, "default": "draft"},
                {"code": "supplier_id", "type": "relation","label": "Supplier",    "required": False, "target_entity": "supplier"},
            ],
            "permissions": {
                "admin":  ["create", "read", "update", "delete"],
                "member": ["create", "read", "update", "delete"],
            },
            "workflow": {
                "code": wf_code,
                "reference_type": "purchase_request",
                "auto_start_on_create": True,
            },
        })
        _json(client, "POST", "/metadata/entities/purchase_request/publish", headers=headers)
        print("  ✓ purchase_request created + published")


def _filter_records(
    client: httpx.Client, headers: dict[str, str], entity: str, field: str, value: str
) -> list[dict[str, Any]]:
    data = _json(client, "GET", f"/entities/{entity}/records?limit=5", headers=headers, params={
        "filter_field": field, "filter_value": value,
    })
    return data if isinstance(data, list) else []


def seed_records(
    client: httpx.Client, headers: dict[str, str], supplier_ids: list[str]
) -> list[str]:
    print("[records] Creating purchase requests ...")
    created: list[str] = []
    samples = [
        ("Office supplies", 1200, 0),
        ("Server upgrade", 85000, 1),
        ("Software licenses", 15000, 2),
        ("Cloud subscription", 5200, 0),
        ("Office renovation", 125000, 1),
        ("Networking equipment", 9800, 2),
        ("Security audit", 34000, 0),
        ("Team offsite", 7500, 1),
    ]
    for title, amount, si in samples:
        existing = _filter_records(client, headers, "purchase_request", "title", title)
        if existing:
            continue
        body: dict[str, Any] = {"title": title, "amount": float(amount)}
        if supplier_ids:
            body["supplier_id"] = supplier_ids[si % len(supplier_ids)]
        rec = _json(client, "POST", "/entities/purchase_request/records", headers=headers, json={"data": body})
        created.append(rec["id"])
        print(f"  + {title} (amount={amount}) → {rec['id'][:8]}")
    print(f"  ✓ created {len(created)} records")
    return created


def seed_suppliers(client: httpx.Client, headers: dict[str, str]) -> list[str]:
    print("[records] Creating suppliers ...")
    ids: list[str] = []
    for name in ["Acme Supplies", "Global Tech", "BuildRight Co."]:
        existing = _filter_records(client, headers, "supplier", "name", name)
        if existing:
            ids.append(existing[0]["id"])
            continue
        rec = _json(client, "POST", "/entities/supplier/records", headers=headers, json={"data": {"name": name}})
        ids.append(rec["id"])
        print(f"  + {name} → {rec['id'][:8]}")
    print(f"  ✓ created/loaded {len(ids)} suppliers")
    return ids


def trigger_approvals(client: httpx.Client, headers: dict[str, str], count: int) -> int:
    print("[workflow] Triggering approval transitions ...")
    instances = _json(client, "GET", "/workflows/instances", headers=headers)
    if not isinstance(instances, list):
        instances = []

    submitted = 0
    for inst in instances:
        if submitted >= count:
            break
        if inst.get("current_state") != "draft":
            continue
        try:
            result = _json(client, "POST", f"/workflows/instances/{inst['id']}/transitions", headers=headers, json={
                "action": "submit",
            })
            submitted += 1
            status = result.get("status") if isinstance(result, dict) else "?"
            print(f"  + instance {inst['id'][:8]} → submitted (approval: {status})")
        except Exception:
            pass
    print(f"  ✓ triggered {submitted} approval(s)")
    return submitted


def seed_rule(client: httpx.Client, headers: dict[str, str]) -> None:
    if has_rule(headers, client, "purchase_requests_started"):
        print("  ⏭ rule 'purchase_requests_started' exists — skipping")
        return
    print("[rules] Creating 'purchase_requests_started' rule ...")
    _json(client, "POST", "/rules", headers=headers, json={
        "name": "purchase_requests_started",
        "description": "Notify manager when a new purchase request workflow is started",
        "event_type": "workflow.instance.started",
        "conditions": [
            {"field": "payload.reference_type", "op": "eq", "value": "purchase_request"},
        ],
        "actions": [
            {
                "type": "notify",
                "title": "New Purchase Request",
                "message": "A new purchase request workflow has been started.",
                "role": "manager",
            },
        ],
        "priority": 50,
        "enabled": True,
    })
    print("  ✓ rule created")


def seed_report(client: httpx.Client, headers: dict[str, str]) -> None:
    if has_report(headers, client, "requests_by_status"):
        print("  ⏭ report 'requests_by_status' exists — skipping")
        return
    print("[analytics] Creating 'requests_by_status' report ...")
    _json(client, "POST", "/analytics/reports", headers=headers, json={
        "code": "requests_by_status",
        "name": "Purchase Requests by Status",
        "entity_code": "purchase_request",
        "metric": "count",
        "field": None,
        "conditions": [],
        "group_by": "status",
    })
    print("  ✓ report created")


def trigger_rule_live(
    client: httpx.Client, headers: dict[str, str], supplier_ids: list[str]
) -> int:
    """Create + submit one request AFTER the rule exists so the rule fires live."""
    print("[rules] Firing rule live (create + submit a fresh request) ...")
    body: dict[str, Any] = {
        "title": "Quarterly audit review",
        "amount": 18500.0,
    }
    if supplier_ids:
        body["supplier_id"] = supplier_ids[0]
    rec = _json(client, "POST", "/entities/purchase_request/records", headers=headers, json={"data": body})
    submitted = 0
    try:
        insts = _json(client, "GET", "/workflows/instances", headers=headers)
        target = next((i for i in insts if i.get("reference_id") == rec["id"]), None)
        if target:
            _json(client, "POST", f"/workflows/instances/{target['id']}/transitions", headers=headers, json={
                "action": "submit",
            })
            submitted = 1
    except Exception:
        pass
    print(f"  ✓ fired → {submitted} new approval")
    return submitted


# ---------------------------------------------------------------------------
# ERP Demo Data
# ---------------------------------------------------------------------------

def seed_projects(client: httpx.Client, headers: dict[str, str]) -> list[str]:
    """Create demo construction projects"""
    print("[erp] Creating construction projects ...")
    ids: list[str] = []
    projects = [
        {"code": "PRJ-001", "name": "Dubai Marina Tower", "status": "active", "description": "50-story residential tower"},
        {"code": "PRJ-002", "name": "Abu Dhabi Office Complex", "status": "planning", "description": "Grade A office building"},
        {"code": "PRJ-003", "name": "Riyadh Mall Extension", "status": "active", "description": "Shopping mall expansion"},
    ]

    existing = _json(client, "GET", "/construction/projects", headers=headers, params={"limit": 100})
    existing_list = existing if isinstance(existing, list) else []

    for proj in projects:
        match = next((p for p in existing_list if p.get("code") == proj["code"]), None)
        if match:
            ids.append(match["id"])
            print(f"  ⏭ project '{proj['code']}' exists — loaded {match['id'][:8]}")
            continue

        rec = _json(client, "POST", "/construction/projects", headers=headers, json=proj)
        ids.append(rec["id"])
        print(f"  + {proj['code']}: {proj['name']} → {rec['id'][:8]}")

    print(f"  ✓ created/loaded {len(ids)} projects")
    return ids


def seed_contracts(
    client: httpx.Client, headers: dict[str, str], project_ids: list[str]
) -> list[str]:
    """Create demo contracts"""
    print("[erp] Creating contracts ...")
    ids: list[str] = []
    contracts = [
        {"contract_number": "CTR-001", "project_id": project_ids[0] if project_ids else None, "contract_type": "main", "title": "Main Construction Contract", "counterparty": "BuildRight Co.", "contract_value": 5000000, "status": "active"},
        {"contract_number": "CTR-002", "project_id": project_ids[0] if project_ids else None, "contract_type": "subcontract", "title": "MEP Subcontract", "counterparty": "Global Tech", "contract_value": 1200000, "status": "active"},
        {"contract_number": "CTR-003", "project_id": project_ids[1] if len(project_ids) > 1 else (project_ids[0] if project_ids else None), "contract_type": "main", "title": "Foundation Works", "counterparty": "Acme Supplies", "contract_value": 800000, "status": "draft"},
    ]

    existing = _json(client, "GET", "/construction/contracts", headers=headers, params={"limit": 100})
    existing_list = existing if isinstance(existing, list) else []

    for ctr in contracts:
        match = next((c for c in existing_list if c.get("contract_number") == ctr["contract_number"]), None)
        if match:
            ids.append(match["id"])
            print(f"  ⏭ contract '{ctr['contract_number']}' exists — loaded {match['id'][:8]}")
            continue

        if not ctr["project_id"]:
            print(f"  ⏭ contract '{ctr['contract_number']}' skipped — no project_id available")
            continue

        rec = _json(client, "POST", "/construction/contracts", headers=headers, json=ctr)
        ids.append(rec["id"])
        print(f"  + {ctr['contract_number']}: {ctr['title']} → {rec['id'][:8]}")

    print(f"  ✓ created/loaded {len(ids)} contracts")
    return ids


def seed_accounts(client: httpx.Client, headers: dict[str, str]) -> list[str]:
    """Create demo chart of accounts"""
    print("[erp] Creating chart of accounts ...")
    ids: list[str] = []
    accounts = [
        {"code": "1000", "name": "Cash", "account_type": "asset", "is_active": True},
        {"code": "1100", "name": "Accounts Receivable", "account_type": "asset", "is_active": True},
        {"code": "1200", "name": "Inventory", "account_type": "asset", "is_active": True},
        {"code": "2000", "name": "Accounts Payable", "account_type": "liability", "is_active": True},
        {"code": "2100", "name": "Loans Payable", "account_type": "liability", "is_active": True},
        {"code": "3000", "name": "Owner Equity", "account_type": "equity", "is_active": True},
        {"code": "4000", "name": "Construction Revenue", "account_type": "revenue", "is_active": True},
        {"code": "4100", "name": "Service Revenue", "account_type": "revenue", "is_active": True},
        {"code": "5000", "name": "Materials Expense", "account_type": "expense", "is_active": True},
        {"code": "5100", "name": "Labor Expense", "account_type": "expense", "is_active": True},
        {"code": "5200", "name": "Equipment Expense", "account_type": "expense", "is_active": True},
        {"code": "5300", "name": "Subcontractor Expense", "account_type": "expense", "is_active": True},
    ]

    existing = _json(client, "GET", "/financial/accounts", headers=headers, params={"limit": 100})
    existing_list = existing if isinstance(existing, list) else []

    for acc in accounts:
        match = next((a for a in existing_list if a.get("code") == acc["code"]), None)
        if match:
            ids.append(match["id"])
            print(f"  ⏭ account '{acc['code']}' exists — loaded {match['id'][:8]}")
            continue

        rec = _json(client, "POST", "/financial/accounts", headers=headers, json=acc)
        ids.append(rec["id"])
        print(f"  + {acc['code']}: {acc['name']} → {rec['id'][:8]}")

    print(f"  ✓ created/loaded {len(ids)} accounts")
    return ids


def seed_boqs(
    client: httpx.Client, headers: dict[str, str], contract_ids: list[str]
) -> list[str]:
    """Create demo Bills of Quantities"""
    print("[erp] Creating BOQs ...")
    ids: list[str] = []

    if not contract_ids:
        print("  ⏭ no contracts available — skipping BOQs")
        return ids

    boqs = [
        {"contract_id": contract_ids[0], "version": 1},
        {"contract_id": contract_ids[0], "version": 2},
        {"contract_id": contract_ids[1] if len(contract_ids) > 1 else contract_ids[0], "version": 1},
    ]

    existing = _json(client, "GET", "/construction/boqs", headers=headers, params={"limit": 100})
    existing_list = existing if isinstance(existing, list) else []

    for boq in boqs:
        match = next((
            b for b in existing_list
            if b.get("contract_id") == boq["contract_id"] and b.get("version") == boq["version"]
        ), None)
        if match:
            ids.append(match["id"])
            print(f"  ⏭ BOQ for contract {boq['contract_id'][:8]} v{boq['version']} exists — loaded {match['id'][:8]}")
            continue

        rec = _json(client, "POST", "/construction/boqs", headers=headers, json=boq)
        ids.append(rec["id"])
        print(f"  + BOQ v{boq['version']} for contract {boq['contract_id'][:8]} → {rec['id'][:8]}")

    print(f"  ✓ created/loaded {len(ids)} BOQs")
    return ids


def seed_claims(
    client: httpx.Client, headers: dict[str, str], contract_ids: list[str]
) -> list[str]:
    """Create demo progress claims"""
    print("[erp] Creating progress claims ...")
    ids: list[str] = []

    if not contract_ids:
        print("  ⏭ no contracts available — skipping claims")
        return ids

    claims = [
        {
            "contract_id": contract_ids[0],
            "claim_number": "CLM-001",
            "claim_date": "2026-09-01",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
        },
        {
            "contract_id": contract_ids[0],
            "claim_number": "CLM-002",
            "claim_date": "2026-09-15",
            "period_start": "2026-09-01",
            "period_end": "2026-09-15",
        },
    ]

    existing = _json(client, "GET", "/construction/claims", headers=headers, params={"limit": 100})
    existing_list = existing if isinstance(existing, list) else []

    for claim in claims:
        match = next((c for c in existing_list if c.get("claim_number") == claim["claim_number"]), None)
        if match:
            ids.append(match["id"])
            print(f"  ⏭ claim '{claim['claim_number']}' exists — loaded {match['id'][:8]}")
            continue

        rec = _json(client, "POST", "/construction/claims", headers=headers, json=claim)
        ids.append(rec["id"])
        print(f"  + {claim['claim_number']} → {rec['id'][:8]}")

    print(f"  ✓ created/loaded {len(ids)} claims")
    return ids


def seed_procurements(
    client: httpx.Client, headers: dict[str, str], project_ids: list[str]
) -> list[str]:
    """Create demo procurement requests"""
    print("[erp] Creating procurement requests ...")
    ids: list[str] = []

    pid = project_ids[0] if project_ids else None
    pid2 = project_ids[1] if len(project_ids) > 1 else pid
    pid3 = project_ids[2] if len(project_ids) > 2 else pid

    procurements = [
        {"project_id": pid, "requisition_number": "PR-001", "title": "Steel Reinforcement", "priority": "high"},
        {"project_id": pid, "requisition_number": "PR-002", "title": "Cement Supply", "priority": "medium"},
        {"project_id": pid2, "requisition_number": "PR-003", "title": "Electrical Cables", "priority": "urgent"},
        {"project_id": pid3, "requisition_number": "PR-004", "title": "Plumbing Fixtures", "priority": "low"},
    ]

    existing = _json(client, "GET", "/construction/procurements", headers=headers, params={"limit": 100})
    existing_list = existing if isinstance(existing, list) else []

    for proc in procurements:
        match = next((p for p in existing_list if p.get("requisition_number") == proc["requisition_number"]), None)
        if match:
            ids.append(match["id"])
            print(f"  ⏭ procurement '{proc['requisition_number']}' exists — loaded {match['id'][:8]}")
            continue

        if not proc["project_id"]:
            print(f"  ⏭ procurement '{proc['requisition_number']}' skipped — no project_id")
            continue

        rec = _json(client, "POST", "/construction/procurements", headers=headers, json=proc)
        ids.append(rec["id"])
        print(f"  + {proc['requisition_number']}: {proc['title']} → {rec['id'][:8]}")

    print(f"  ✓ created/loaded {len(ids)} procurements")
    return ids


def seed_financial_customers(
    client: httpx.Client, headers: dict[str, str]
) -> list[str]:
    """Create demo customers for AR"""
    print("[financial] Creating customers ...")
    ids: list[str] = []
    customers = [
        {"code": "CUST-001", "name": "Al Baraka Construction", "email": "finance@albaraka.com", "phone": "+971-4-555-0101", "payment_terms": "NET30", "currency": "USD", "credit_limit": 500000},
        {"code": "CUST-002", "name": "Gulf Properties LLC", "email": "ap@gulfprop.com", "phone": "+971-4-555-0202", "payment_terms": "NET45", "currency": "USD", "credit_limit": 750000},
        {"code": "CUST-003", "name": "Emirates Holdings", "email": "billing@emirates-holdings.com", "phone": "+971-4-555-0303", "payment_terms": "NET30", "currency": "USD", "credit_limit": 1000000},
        {"code": "CUST-004", "name": "Nile Development Corp", "email": "accounts@niledev.com", "phone": "+20-2-555-0404", "payment_terms": "NET60", "currency": "USD", "credit_limit": 300000},
        {"code": "CUST-005", "name": "Saudi Infrastructure Co", "email": "finance@saudi-infra.com", "phone": "+966-11-555-0505", "payment_terms": "NET30", "currency": "USD", "credit_limit": 800000},
    ]
    for c in customers:
        r = _json(client, "POST", "/financial/customers", headers=headers, json=c)
        ids.append(r["id"])
        print(f"  + {c['code']}: {c['name']} → {r['id'][:8]}")
    print(f"  ✓ created {len(ids)} customers")
    return ids


def seed_financial_suppliers(
    client: httpx.Client, headers: dict[str, str]
) -> list[str]:
    """Create demo suppliers for AP"""
    print("[financial] Creating financial suppliers ...")
    ids: list[str] = []
    suppliers = [
        {"code": "SUPP-001", "name": "Steel Masters International", "email": "billing@steelmasters.com", "phone": "+971-4-555-1001", "payment_terms": "NET30", "currency": "USD"},
        {"code": "SUPP-002", "name": "Gulf Concrete Supply", "email": "accounts@gulfconcrete.com", "phone": "+971-4-555-1002", "payment_terms": "NET15", "currency": "USD"},
        {"code": "SUPP-003", "name": "Emirates Electrical Co", "email": "finance@emirates-elec.com", "phone": "+971-4-555-1003", "payment_terms": "NET30", "currency": "USD"},
        {"code": "SUPP-004", "name": "Cairo Building Materials", "email": "billing@cairo-bm.com", "phone": "+20-2-555-1004", "payment_terms": "NET45", "currency": "USD"},
        {"code": "SUPP-005", "name": "Riyadh Heavy Equipment", "email": "ap@riyadh-equip.com", "phone": "+966-11-555-1005", "payment_terms": "NET30", "currency": "USD"},
    ]
    for s in suppliers:
        r = _json(client, "POST", "/financial/suppliers", headers=headers, json=s)
        ids.append(r["id"])
        print(f"  + {s['code']}: {s['name']} → {r['id'][:8]}")
    print(f"  ✓ created {len(ids)} suppliers")
    return ids


def seed_bank_accounts(
    client: httpx.Client, headers: dict[str, str], account_ids: list[str]
) -> list[str]:
    """Create demo bank accounts"""
    print("[financial] Creating bank accounts ...")
    ids: list[str] = []
    # Use asset accounts (1000=Cash, 1100=AR) as GL accounts
    cash_acct = account_ids[0] if account_ids else None
    ar_acct = account_ids[1] if len(account_ids) > 1 else cash_acct

    banks = [
        {"account_number": "1234567890", "account_name": "Main Operating Account", "bank_name": "Emirates NBD", "bank_code": "ABORAEAD", "account_type": "checking", "currency": "USD", "gl_account_id": cash_acct},
        {"account_number": "9876543210", "account_name": "Savings Account", "bank_name": "Abu Dhabi Commercial Bank", "bank_code": "ADCBAEAA", "account_type": "savings", "currency": "USD", "gl_account_id": cash_acct},
        {"account_number": "5555666677", "account_name": "Petty Cash", "bank_name": "Cash", "account_type": "cash", "currency": "USD", "gl_account_id": cash_acct},
    ]
    for b in banks:
        r = _json(client, "POST", "/financial/bank-accounts", headers=headers, json=b)
        ids.append(r["id"])
        print(f"  + {b['account_name']} ({b['bank_name']}) → {r['id'][:8]}")
    print(f"  ✓ created {len(ids)} bank accounts")
    return ids


def seed_invoices(
    client: httpx.Client, headers: dict[str, str], customer_ids: list[str]
) -> list[str]:
    """Create demo customer invoices"""
    print("[financial] Creating invoices ...")
    ids: list[str] = []
    from datetime import date, timedelta

    today = date.today()
    invoices_data = [
        {"customer_idx": 0, "days_issue": -45, "days_due": -15, "subtotal": 125000, "tax": 18750, "status": "overdue", "lines": [{"description": "Construction Phase 1 - Foundation", "quantity": 1, "unit_price": 125000, "tax_rate": 0.15}]},
        {"customer_idx": 0, "days_issue": -30, "days_due": 0, "subtotal": 85000, "tax": 12750, "status": "sent", "lines": [{"description": "Construction Phase 2 - Structure", "quantity": 1, "unit_price": 85000, "tax_rate": 0.15}]},
        {"customer_idx": 1, "days_issue": -60, "days_due": -30, "subtotal": 250000, "tax": 37500, "status": "paid", "lines": [{"description": "Office Complex - MEP Works", "quantity": 1, "unit_price": 250000, "tax_rate": 0.15}]},
        {"customer_idx": 1, "days_issue": -15, "days_due": 15, "subtotal": 67500, "tax": 10125, "status": "sent", "lines": [{"description": "Office Complex - Interior Finishing", "quantity": 1, "unit_price": 67500, "tax_rate": 0.15}]},
        {"customer_idx": 2, "days_issue": -20, "days_due": 10, "subtotal": 180000, "tax": 27000, "status": "sent", "lines": [{"description": "Mall Extension - Steel Works", "quantity": 1, "unit_price": 180000, "tax_rate": 0.15}]},
        {"customer_idx": 2, "days_issue": -90, "days_due": -60, "subtotal": 95000, "tax": 14250, "status": "paid", "lines": [{"description": "Mall Extension - Site Preparation", "quantity": 1, "unit_price": 95000, "tax_rate": 0.15}]},
        {"customer_idx": 3, "days_issue": -5, "days_due": 25, "subtotal": 42000, "tax": 6300, "status": "draft", "lines": [{"description": "Consulting Services - Q3", "quantity": 1, "unit_price": 42000, "tax_rate": 0.15}]},
        {"customer_idx": 4, "days_issue": -10, "days_due": 20, "subtotal": 320000, "tax": 48000, "status": "sent", "lines": [{"description": "Infrastructure - Road Works", "quantity": 1, "unit_price": 320000, "tax_rate": 0.15}]},
    ]
    for inv in invoices_data:
        cid = customer_ids[inv["customer_idx"] % len(customer_ids)]
        issue_date = (today + timedelta(days=inv["days_issue"])).isoformat()
        due_date = (today + timedelta(days=inv["days_due"])).isoformat()
        body = {
            "customer_id": cid,
            "issue_date": issue_date,
            "due_date": due_date,
            "currency": "USD",
            "lines": inv["lines"],
        }
        r = _json(client, "POST", "/financial/invoices", headers=headers, json=body)
        inv_id = r["id"]
        # Update status if not draft
        if inv["status"] != "draft":
            _json(client, "PATCH", f"/financial/invoices/{inv_id}/status", headers=headers, params={"status": inv["status"]})
        ids.append(inv_id)
        print(f"  + INV for customer {inv['customer_idx']+1}: ${inv['subtotal']:,} ({inv['status']}) → {inv_id[:8]}")
    print(f"  ✓ created {len(ids)} invoices")
    return ids


def seed_bills(
    client: httpx.Client, headers: dict[str, str], supplier_ids: list[str]
) -> list[str]:
    """Create demo supplier bills"""
    print("[financial] Creating bills ...")
    ids: list[str] = []
    from datetime import date, timedelta

    today = date.today()
    bills_data = [
        {"supplier_idx": 0, "days_issue": -40, "days_due": -10, "subtotal": 78000, "tax": 11700, "status": "overdue", "lines": [{"description": "Steel Reinforcement Bars", "quantity": 50, "unit_price": 1560, "tax_rate": 0.15}]},
        {"supplier_idx": 0, "days_issue": -20, "days_due": 10, "subtotal": 45000, "tax": 6750, "status": "received", "lines": [{"description": "Structural Steel Beams", "quantity": 30, "unit_price": 1500, "tax_rate": 0.15}]},
        {"supplier_idx": 1, "days_issue": -35, "days_due": -20, "subtotal": 32000, "tax": 4800, "status": "overdue", "lines": [{"description": "Ready Mix Concrete", "quantity": 200, "unit_price": 160, "tax_rate": 0.15}]},
        {"supplier_idx": 2, "days_issue": -25, "days_due": 5, "subtotal": 55000, "tax": 8250, "status": "received", "lines": [{"description": "Electrical Cables & Wiring", "quantity": 1, "unit_price": 55000, "tax_rate": 0.15}]},
        {"supplier_idx": 3, "days_issue": -50, "days_due": -20, "subtotal": 28000, "tax": 4200, "status": "paid", "lines": [{"description": "Building Materials - General", "quantity": 1, "unit_price": 28000, "tax_rate": 0.15}]},
        {"supplier_idx": 4, "days_issue": -10, "days_due": 20, "subtotal": 120000, "tax": 18000, "status": "draft", "lines": [{"description": "Heavy Equipment Rental - 3 months", "quantity": 3, "unit_price": 40000, "tax_rate": 0.15}]},
    ]
    for bill in bills_data:
        sid = supplier_ids[bill["supplier_idx"] % len(supplier_ids)]
        issue_date = (today + timedelta(days=bill["days_issue"])).isoformat()
        due_date = (today + timedelta(days=bill["days_due"])).isoformat()
        body = {
            "supplier_id": sid,
            "issue_date": issue_date,
            "due_date": due_date,
            "currency": "USD",
            "lines": bill["lines"],
        }
        r = _json(client, "POST", "/financial/bills", headers=headers, json=body)
        bill_id = r["id"]
        if bill["status"] != "draft":
            _json(client, "PATCH", f"/financial/bills/{bill_id}/status", headers=headers, params={"status": bill["status"]})
        ids.append(bill_id)
        print(f"  + BILL for supplier {bill['supplier_idx']+1}: ${bill['subtotal']:,} ({bill['status']}) → {bill_id[:8]}")
    print(f"  ✓ created {len(ids)} bills")
    return ids


def seed_payments(
    client: httpx.Client, headers: dict[str, str], customer_ids: list[str], supplier_ids: list[str]
) -> list[str]:
    """Create demo payments"""
    print("[financial] Creating payments ...")
    ids: list[str] = []
    from datetime import date, timedelta

    today = date.today()
    payments = [
        {"payment_type": "customer", "customer_idx": 2, "days_ago": 10, "amount": 250000, "method": "bank_transfer", "reference": "TRF-2026-001"},
        {"payment_type": "customer", "customer_idx": 2, "days_ago": 5, "amount": 95000, "method": "bank_transfer", "reference": "TRF-2026-002"},
        {"payment_type": "supplier", "supplier_idx": 3, "days_ago": 15, "amount": 28000, "method": "bank_transfer", "reference": "TRF-2026-003"},
    ]
    for p in payments:
        pid = customer_ids[p["customer_idx"]] if p["payment_type"] == "customer" else supplier_ids[p["supplier_idx"]]
        body = {
            "payment_type": p["payment_type"],
            "customer_id": customer_ids[p["customer_idx"]] if p["payment_type"] == "customer" else None,
            "supplier_id": supplier_ids[p["supplier_idx"]] if p["payment_type"] == "supplier" else None,
            "payment_date": (today - timedelta(days=p["days_ago"])).isoformat(),
            "currency": "USD",
            "amount": p["amount"],
            "payment_method": p["method"],
            "reference": p["reference"],
        }
        r = _json(client, "POST", "/financial/payments", headers=headers, json=body)
        ids.append(r["id"])
        print(f"  + {p['payment_type']} payment: ${p['amount']:,} ({p['reference']}) → {r['id'][:8]}")
    print(f"  ✓ created {len(ids)} payments")
    return ids


def seed_journal_entries(
    client: httpx.Client, headers: dict[str, str], account_ids: list[str]
) -> list[str]:
    """Create demo journal entries"""
    print("[financial] Creating journal entries ...")
    ids: list[str] = []
    from datetime import date, timedelta

    today = date.today()
    # Account indices: 0=Cash, 1=AR, 2=Inventory, 3=AP, 4=Loans, 5=Equity, 6=ConstrRev, 7=SvcRev, 8=MatExp, 9=LaborExp, 10=EquipExp, 11=SubExp

    entries = [
        {
            "date": (today - timedelta(days=60)).isoformat(),
            "description": "Initial capital injection",
            "reference": "JE-001",
            "lines": [
                {"account_idx": 0, "debit": 500000, "credit": 0},
                {"account_idx": 5, "debit": 0, "credit": 500000},
            ],
        },
        {
            "date": (today - timedelta(days=45)).isoformat(),
            "description": "Construction revenue - Phase 1",
            "reference": "JE-002",
            "lines": [
                {"account_idx": 1, "debit": 125000, "credit": 0},
                {"account_idx": 6, "debit": 0, "credit": 125000},
            ],
        },
        {
            "date": (today - timedelta(days=40)).isoformat(),
            "description": "Steel materials purchase",
            "reference": "JE-003",
            "lines": [
                {"account_idx": 8, "debit": 78000, "credit": 0},
                {"account_idx": 3, "debit": 0, "credit": 78000},
            ],
        },
        {
            "date": (today - timedelta(days=30)).isoformat(),
            "description": "Payment received - Office Complex",
            "reference": "JE-004",
            "lines": [
                {"account_idx": 0, "debit": 250000, "credit": 0},
                {"account_idx": 1, "debit": 0, "credit": 250000},
            ],
        },
        {
            "date": (today - timedelta(days=25)).isoformat(),
            "description": "Labor costs - September",
            "reference": "JE-005",
            "lines": [
                {"account_idx": 9, "debit": 95000, "credit": 0},
                {"account_idx": 0, "debit": 0, "credit": 95000},
            ],
        },
        {
            "date": (today - timedelta(days=20)).isoformat(),
            "description": "Concrete supply - overdue bill",
            "reference": "JE-006",
            "lines": [
                {"account_idx": 8, "debit": 32000, "credit": 0},
                {"account_idx": 3, "debit": 0, "credit": 32000},
            ],
        },
        {
            "date": (today - timedelta(days=15)).isoformat(),
            "description": "Payment to Cairo Building Materials",
            "reference": "JE-007",
            "lines": [
                {"account_idx": 3, "debit": 28000, "credit": 0},
                {"account_idx": 0, "debit": 0, "credit": 28000},
            ],
        },
        {
            "date": (today - timedelta(days=10)).isoformat(),
            "description": "Equipment rental expense",
            "reference": "JE-008",
            "lines": [
                {"account_idx": 10, "debit": 40000, "credit": 0},
                {"account_idx": 3, "debit": 0, "credit": 40000},
            ],
        },
        {
            "date": (today - timedelta(days=5)).isoformat(),
            "description": "Service revenue - consulting",
            "reference": "JE-009",
            "lines": [
                {"account_idx": 1, "debit": 42000, "credit": 0},
                {"account_idx": 7, "debit": 0, "credit": 42000},
            ],
        },
        {
            "date": today.isoformat(),
            "description": "Subcontractor payment",
            "reference": "JE-010",
            "lines": [
                {"account_idx": 11, "debit": 65000, "credit": 0},
                {"account_idx": 0, "debit": 0, "credit": 65000},
            ],
        },
    ]
    for e in entries:
        body = {
            "accounting_date": e["date"],
            "currency": "USD",
            "description": e["description"],
            "reference": e["reference"],
            "lines": [
                {"account_id": account_ids[l["account_idx"]], "debit": l["debit"], "credit": l["credit"]}
                for l in e["lines"]
            ],
        }
        r = _json(client, "POST", "/financial/journal-entries", headers=headers, json=body)
        je_id = r["id"]
        # Post the entry
        _json(client, "POST", f"/financial/journal-entries/{je_id}/post", headers=headers)
        ids.append(je_id)
        print(f"  + {e['reference']}: {e['description']} → posted {je_id[:8]}")
    print(f"  ✓ created + posted {len(ids)} journal entries")
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for 2TO EOS")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="demo@2to-eos.local")
    parser.add_argument("--password", default="Demo!2to-eos-2026")
    parser.add_argument("--tenant", default="Demo Organization")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    client = httpx.Client(base_url=f"{base}/api/v1", timeout=15)

    try:
        token = authenticate(client, args.email, args.password, args.tenant)
    except Exception as exc:
        print(f"AUTH FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    wf_code = "purchase_approval"

    print()
    seed_workflow(client, headers, wf_code)
    print()
    seed_entities(client, headers, wf_code)
    print()
    suppliers = seed_suppliers(client, headers)
    print()
    created_rr = seed_records(client, headers, suppliers)
    print()
    pending = trigger_approvals(client, headers, count=2)
    print()
    seed_rule(client, headers)
    print()
    seed_report(client, headers)
    print()
    live = trigger_rule_live(client, headers, suppliers)
    print()

    # ERP Demo Data
    print("=" * 60)
    print("  ERP DEMO DATA")
    print("=" * 60)
    print()
    project_ids = seed_projects(client, headers)
    print()
    contract_ids = seed_contracts(client, headers, project_ids)
    print()
    account_ids = seed_accounts(client, headers)
    print()
    bank_account_ids = seed_bank_accounts(client, headers, account_ids)
    print()
    customer_ids = seed_financial_customers(client, headers)
    print()
    financial_supplier_ids = seed_financial_suppliers(client, headers)
    print()
    journal_ids = seed_journal_entries(client, headers, account_ids)
    print()
    invoice_ids = seed_invoices(client, headers, customer_ids)
    print()
    bill_ids = seed_bills(client, headers, financial_supplier_ids)
    print()
    payment_ids = seed_payments(client, headers, customer_ids, financial_supplier_ids)
    print()
    boq_ids = seed_boqs(client, headers, contract_ids)
    print()
    claim_ids = seed_claims(client, headers, contract_ids)
    print()
    procurement_ids = seed_procurements(client, headers, project_ids)
    print()

    print("=" * 60)
    print("  DEMO SEED COMPLETE")
    print("  Entities:        supplier, purchase_request")
    print(f"  Records:         {len(suppliers)} suppliers, {len(created_rr) + live} purchase requests")
    print(f"  Approvals:       {pending + live} pending approval(s)")
    print("  Rule:            workflow.instance.started → notify manager (fired live)")
    print("  Report:          requests_by_status (count by status)")
    print(f"  Projects:        {len(project_ids)} construction projects")
    print(f"  Contracts:       {len(contract_ids)} contracts")
    print(f"  Accounts:        {len(account_ids)} chart of accounts")
    print(f"  Bank Accounts:   {len(bank_account_ids)} bank accounts")
    print(f"  Customers:       {len(customer_ids)} customers (AR)")
    print(f"  Suppliers:       {len(financial_supplier_ids)} suppliers (AP)")
    print(f"  Journal Entries: {len(journal_ids)} posted entries")
    print(f"  Invoices:        {len(invoice_ids)} customer invoices")
    print(f"  Bills:           {len(bill_ids)} supplier bills")
    print(f"  Payments:        {len(payment_ids)} payments")
    print(f"  BOQs:            {len(boq_ids)} bills of quantities")
    print(f"  Claims:          {len(claim_ids)} progress claims")
    print(f"  Procurements:    {len(procurement_ids)} procurement requests")
    print(f"  Login:           {args.email} / {args.password}")
    print("=" * 60)


if __name__ == "__main__":
    main()
