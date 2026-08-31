# P80.5D — FULL CODE REVIEW (5 DIMENSIONS) — COMPLETE

**Date:** 2026-08-29
**Target:** `D:\EOS\EOS-Release-1.0` (Release copy — master `D:\EOS\Eos final` never modified)
**Scope:** Full 5-dimension code review (Security, Accounting, Multi-tenant / Isolation, Architecture, APIs & Validation). All **Critical** findings fixed. High/Medium/Low findings **documented** for the next phase (per directive: fix Criticals first, document the rest with evidence).
**Source of issues:** Agent review findings across 5 dimensions (security, accounting, multi-tenant, architecture, APIs/validation agents) + verification against the actual Release source.

---

## Summary

| Suite | Result |
|-------|--------|
| Full Regression `tests/run_all.py` | **542/542 PASS** |
| Control Plane gate (owner vs tenant) | owner 200 / cross-tenant 403 |
| Cross-tenant scoping smoke tests (payment / finance / erp / accounting / sales / procurement / hr) | owner 200 / cross-tenant 404-or-empty |
| Payment money-safety smoke tests | missing-refund 404, negative/zero cash 400, happy-path 200 |

- **Critical = 0** (all fixed and verified)
- **High / Medium / Low = documented** (deferred, with evidence) — see Deferred section below

---

## Fixed Criticals (each verified via smoke tests + regression)

### C1 — Control Plane gated only by broad `admin`/`dynamic` role
- **Problem:** All 16 control-plane endpoints relied on `get_current_user` only; any authenticated `admin`-role tenant could call tenant provisioning / impersonation / global tenant listing.
- **Files:** `core/auth.py`, `routers/control_plane.py`
- **Fix:** Added `require_platform_owner` dependency — grants access when the caller has a `platform_owner` role OR is a designated platform-owner email from `EOS_PLATFORM_OWNER_EMAILS` (defaults to `admin@demo.com`). Added `_designated_platform_owners()` helper; added to `__all__`. All 16 control-plane endpoint signatures changed from `Depends(get_current_user)` to `Depends(require_platform_owner)`.
- **Verified:** PlatformOwner(demo admin)=200, `platform_owner` role=200, TenantAdmin(role admin)=403, NormalUser=403, unauth=401; impersonate OK for owner, 403 for plain tenant-admin.
- **Tests:** control-plane re-test passed; `tests/test_p77_commercial.py` (only control-plane-using test) still green.

### C2 — Login falls back to the test signing key in production
- **Problem:** `routers/auth.py:120-122` fell back to `TEST_SECRET_KEY` when `EOS_SECRET_KEY` was absent (or non-test mode), so production could mint tokens with a known dev key.
- **File:** `routers/auth.py`
- **Fix:** Production now raises `_err(500,"SERVER_CONFIG","EOS_SECRET_KEY is not configured")` when the key is missing in non-test mode; test mode uses `TEST_SECRET_KEY`.
- **Verified:** demo admin login still returns 200.

### C3 — `post_journal` did not update General Ledger balances
- **Problem:** `core/industry_security.py` `post_journal` (lines 157-192) did not update the `current_balance` of the GL accounts it posted.
- **File:** `core/industry_security.py`
- **Fix:** Added `current_balance = current_balance + :dr - :cr` update per journal line, keyed on `code + tenant_id` (journal lines store the account **code** in `account_id`).
- **Verified:** `accounting_engine.py` posting path already updated GL (lines 142-148); `industry_engine/__init__.py:122 post_journal` is a rule-based generator (returns data), not a poster — fix applied to the actual poster.

### C4 — Payment transactions not tenant-scoped (cross-tenant access / drain)
- **Problem:** `core/payment_engine.py` read/complete/fail/refund operations were keyed only on transaction id; a tenant could read/refund another tenant's transaction.
- **Files:** `core/payment_engine.py`, `routers/payment_api.py`
- **Fix:** Added `tenant_id` param + `AND tenant_id = :t` scoping to `get_transaction`, `complete_transaction`, `fail_transaction`, `refund_transaction`; refund sum scoped. No other callers.
- **Verified:** cross-tenant get → 404; owner get → 200.

### C5 — Finance module not tenant-scoped (incl. money movement)
- **Problem:** `core/finance_engine.py` / `routers/finance.py` reads and `approve_payment` (payment lookup + bank-balance UPDATE) were unscoped; create ops did not verify company ownership.
- **Files:** `core/finance_engine.py`, `routers/finance.py`
- **Fix:** Scoped reads (`get_bank_accounts`, `list_payments`, `get_budgets`, `get_budget_utilization`), `approve_payment` (payment lookup + bank balance scoped by tenant), create ops use `_verify_company_tenant` + bank-account ownership in `create_payment`/`create_budget`.
- **Verified:** owner 200; cross-tenant reads empty; cross-tenant approve blocked; foreign-company create → 403.

### C6 — ERP Foundation not tenant-scoped
- **Problem:** `core/erp_foundation.py` / `routers/erp_foundation.py` reads (`get_branches`, `get_departments`, `get_department_tree`, `get_fiscal_years`, `get_cost_centers`) and `update_company` / `close_fiscal_year` unscoped.
- **Files:** `core/erp_foundation.py`, `routers/erp_foundation.py`
- **Fix:** Scoped all listed reads; `update_company` now requires `user` + tenant; `close_fiscal_year` scoped; create ops add `_verify_company_tenant`.
- **Verified:** compile + regression green.

### C7 — Accounting engine/router not tenant-scoped
- **Problem:** `core/accounting_engine.py` / `routers/accounting.py` reads and mutations (accounts, journal entries, trial balance, `post_journal_entry`, `add_journal_line`) unscoped.
- **Files:** `core/accounting_engine.py`, `routers/accounting.py`
- **Fix:** Scoped all reads and `post_journal_entry` (header `FOR UPDATE` + GL update + mark-posted all `AND tenant_id`); `_verify_company_tenant` on create ops; `add_journal_line` takes `tenant_id` and verifies parent journal owner (404 otherwise). Updated all router endpoints to pass `user`/`tenant_id`.
- **Verified:** owner 200 (with data); cross-tenant 200 empty (no leak) for accounts / journal-entries / trial-balance.

### C8 — Sales module not tenant-scoped
- **Problem:** `core/sales_engine.py` / `routers/sales.py` `get_sales_order`, `get_invoice`, `record_payment`, `convert_quotation` unscoped.
- **Files:** `core/sales_engine.py`, `routers/sales.py`
- **Fix:** Scoped each (order/invoice/report `AND tenant_id`); `convert_quotation_to_order` quotation lookup scoped; router passes tenant.

### C9 — Payments money endpoints: error-as-success + negative/zero amounts (API review C1)
- **Problem:** `routers/payment_api.py` wrapped refund/complete/fail engine `{"error": ...}` results in `"status":"success"` HTTP 200; `complete`/`fail` on a nonexistent transaction returned 200; `process_cash`/`create_transaction`/`create_payment_link` accepted amount ≤ 0.
- **Files:** `core/payment_engine.py`, `routers/payment_api.py`
- **Fix:** `complete_transaction`/`fail_transaction` return `{"error":...}` when the row is missing; router maps to **404**. Router maps refund error dict to 404 (not found) / 400 (state violation). `create_transaction` and `create_payment_link` raise `ValueError` on amount ≤ 0; router catches → **400** (covers cash + bank transfer which delegate to `create_transaction`).
- **Verified:** complete/fail/refund of missing tx → 404; cash amount 0 / -5 → 400; create→complete→refund happy path → 200.

### C10 — Procurement & HR cross-tenant exposure (API review C2)
- **Problem:** `core/procurement_engine.py` (`list_suppliers`, `list_purchase_requests`, `list_purchase_orders`, `get_purchase_order`, `approve_purchase_request/order`, `receive_goods`) and `core/hr_engine.py` (`update_employee`, `approve_leave_request`, `add_payroll_line`, `get_payroll_run`) filtered only by company_id (no tenant).
- **Files:** `core/procurement_engine.py`, `routers/procurement.py`, `core/hr_engine.py`, `routers/hr.py`
- **Fix:** Added `tenant_id` to every WHERE clause (list/detail/approve/receive/update/get); threaded `user.get("tenant_id")` through the handlers.
- **Verified:** owner lists → 200 with data; cross-tenant lists → 200 empty (no leak).

---

## Deferred Findings (documented with evidence — next phase)

The following were reviewed and confirmed, but **not modified** per the directive (fix Criticals first, document the rest). Recommended for the next release phase.

### High

- **H1 — Missing-resource mutations return 400 instead of 404** (`routers/accounting.py:89`, `routers/sales.py:144`, `routers/finance.py:60`, `routers/procurement.py:61,96,110`). Suggest: engine returns a not-found sentinel → router raises 404; reserve 400 for state violations.
- **H2 — Generic `except Exception` swallows errors** (`routers/hr.py:37`, `routers/projects.py:42`, `routers/sales_api.py:214,285,235,306`). Leaks internal message as 400 and can fabricate empty/`[]` success on missing tables. Suggest: let exceptions propagate → structured 500 via the app error handler.
- **H3 — Wrong-typed JSON fields cause unhandled 500** (`body: dict` numerics: `sales.py:140`, `inventory.py:44-81`, `accounting.py:77`, `finance.py:44`, `accounting_api.py:230`, `procurement.py:73`). Suggest: Pydantic models / shared `validate_body` → FastAPI 422.
- **H4 — `create_purchase_request` accepts arbitrary/empty body** (`routers/procurement.py:51-55`, `core/procurement_engine.py:78-90`). Suggest: require/validate request_date, priority, non-empty body.
- **H5 — Duplicate account code → unhandled 500 in `/api/v1/accounting`** (`routers/accounting_api.py:86-106`). Suggest: pre-check duplicate `(tenant_id, company_id, code)` → 409; require ≥1 journal line (currently empty entries accepted, `accounting_api.py:224-259`).

### Medium

- **M1 — Response-schema inconsistency** across `/api/v1/dynamic/*` (`{"status","data"}`) vs `/api/v1/{accounting,sales}/*` (paginated / bare dict); `payment_api.py:101` returns plain-string 404 detail vs structured error envelope elsewhere. Suggest: standardize on one wrapper + error envelope.
- **M2 — Update/close of nonexistent resources reported as success/wrong code** (`erp_foundation.py:52-58` — no rowcount check → 200 "updated" for missing company; `close_fiscal_year` collapses 404/409). Suggest: check `rowcount`; split 404 vs 409.
- **M3 — `approve_api` minor status gaps** (duplicate chain → 400 should be 409 at `approve_api.py:50`; `get_chain_steps` returns 200 empty for missing chain at `:82-91`). Suggest: 409 / 404 existence check.
- **M4 — Reads on nonexistent company return 200 `[]` while writes raise 403** (`_verify_company_tenant` → 403 for a nonexistent company). Suggest: distinguish "not found" (404) from "belongs to another tenant" (403/404); apply existence check on reads for consistency.

### Low

- **L1 — Create endpoints return 200 instead of 201 / deletes return 200 instead of 204** (all dynamic POST create handlers; `accounting_api.py:138`, `sales_api.py:168`). Suggest: `status_code=201` / `204`.
- **L2 — Free-form input gaps allowing garbage but not crashing** (unchecked `account_type`/`parent_id`/`opening_balance`, `set_exchange_rate` no `rate>0`, `convert_amount` missing-field → wrong 404, free-form `movement_type`, `days` untyped, stub endpoints returning hardcoded 200). Suggest: Pydantic/whitelist enums/numeric coercion; mark stubs 501.
- **L3 — `payment_api` un-bounded inputs** (`limit: int = 50` no `Query(ge/le)`, `RefundRequest.amount` no `gt=0`, `TransactionCreate.amount` allows negatives). Suggest: add bound/validation constraints.

---

## Verification

- All modified files byte-compile (`python -m py_compile`).
- Server restarted on Release copy; `/health` → 200.
- Cross-tenant smoke tests for payment / finance / erp_foundation / accounting / sales / procurement / hr and money-safety passed (owner 200 / cross-tenant 404-or-empty / invalid money 400).
- Full regression: **542/542 PASS** (run twice — before and after the C1/C2 payment/procurement/HR fixes).
- Control Plane re-test: owner 200, cross-tenant 403, unauth 401.

## Files Modified (Release copy only)

- `core/auth.py` — `require_platform_owner` + `_designated_platform_owners` (C1)
- `routers/control_plane.py` — 16 endpoints gated (C1)
- `routers/auth.py` — production key-fallback removed (C2)
- `core/industry_security.py` — GL balance update in `post_journal` (C3)
- `core/payment_engine.py`, `routers/payment_api.py` — tenant scoping (C4) + money-safety/error codes (C9)
- `core/finance_engine.py`, `routers/finance.py` — tenant scoping + `_verify_company_tenant` (C5)
- `core/erp_foundation.py`, `routers/erp_foundation.py` — tenant scoping (C6)
- `core/accounting_engine.py`, `routers/accounting.py` — tenant scoping (C7)
- `core/sales_engine.py`, `routers/sales.py` — tenant scoping (C8)
- `core/procurement_engine.py`, `routers/procurement.py` — tenant scoping (C10)
- `core/hr_engine.py`, `routers/hr.py` — tenant scoping (C10)

## Status

**P80.5D COMPLETE — Critical 0, Full Regression 542/542. High/Medium/Low findings documented for next phase.**

Next: Local Production Simulation → Release 1.1 Final → Cloud deployment.
