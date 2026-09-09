"""
Multi-Tenancy Isolation Test â€” New Tables
Verifies that Tenant B cannot access Tenant A's data across all new endpoints.
"""
import asyncio
import httpx
import uuid

BASE = "http://localhost:8001/api/v1"


async def test_isolation():
    async with httpx.AsyncClient(follow_redirects=True) as c:
        uid_a = uuid.uuid4().hex[:6]
        uid_b = uuid.uuid4().hex[:6]

        # â”€â”€ Register + Login Tenant A â”€â”€
        r = await c.post(f"{BASE}/auth/register", json={
            "email": f"tenantA-{uid_a}@example.com", "password": "Admin123!",
            "company_name": f"TenantA {uid_a}", "company_name_ar": "A",
            "industry": "tech"})
        tid_a = r.json()["tenant_id"]
        r = await c.post(f"{BASE}/auth/login", json={
            "email": f"tenantA-{uid_a}@example.com", "password": "Admin123!",
            "tenant_id": tid_a})
        h_a = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # â”€â”€ Register + Login Tenant B â”€â”€
        r = await c.post(f"{BASE}/auth/register", json={
            "email": f"tenantB-{uid_b}@example.com", "password": "Admin123!",
            "company_name": f"TenantB {uid_b}", "company_name_ar": "B",
            "industry": "tech"})
        tid_b = r.json()["tenant_id"]
        r = await c.post(f"{BASE}/auth/login", json={
            "email": f"tenantB-{uid_b}@example.com", "password": "Admin123!",
            "tenant_id": tid_b})
        h_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

        results = []

        # â”€â”€ Test 1: Sales Invoices â”€â”€
        print("\n=== SALES INVOICES ===")
        # Tenant A creates invoice
        r = await c.post(f"{BASE}/{tid_a}/sales/customers", json={
            "name": "Cust A", "type": "individual"}, headers=h_a)
        cust_a = r.json()["id"]
        r = await c.post(f"{BASE}/{tid_a}/sales/sales-invoices", json={
            "customer_id": cust_a, "invoice_date": "2025-07-01",
            "lines": [{"description": "Svc", "quantity": 1, "unit_price": "500", "total": "500"}]},
            headers=h_a)
        inv_a_id = r.json()["id"]
        print(f"  Tenant A created invoice: {inv_a_id[:8]}...")

        # Tenant B tries to read Tenant A's invoice directly
        r = await c.get(f"{BASE}/{tid_b}/sales/sales-invoices/{inv_a_id}", headers=h_b)
        passed = r.status_code in (404, 403)
        results.append({"test": "Invoice cross-tenant GET", "status": r.status_code, "passed": passed})
        print(f"  Tenant B GET /sales-invoices/{inv_a_id[:8]}: {r.status_code} [{'PASS' if passed else 'FAIL'}]")

        # Tenant B lists invoices (should see 0)
        r = await c.get(f"{BASE}/{tid_b}/sales/sales-invoices", headers=h_b)
        count = r.json().get("total", len(r.json().get("invoices", [])))
        passed = count == 0
        results.append({"test": "Invoice cross-tenant LIST", "count": count, "passed": passed})
        print(f"  Tenant B LIST invoices: count={count} [{'PASS' if passed else 'FAIL'}]")

        # â”€â”€ Test 2: Supplier Invoices â”€â”€
        print("\n=== SUPPLIER INVOICES ===")
        import asyncpg
        conn = await asyncpg.connect('postgres://eos:0100@127.0.0.1:5432/eos_main')
        sup_a = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO suppliers (id, tenant_id, name, code, is_active) VALUES ($1, $2, $3, $4, $5)",
            sup_a, tid_a, "Supplier A", f"SA-{uid_a}", True)
        sup_b = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO suppliers (id, tenant_id, name, code, is_active) VALUES ($1, $2, $3, $4, $5)",
            sup_b, tid_b, "Supplier B", f"SB-{uid_b}", True)
        await conn.close()

        r = await c.post(f"{BASE}/{tid_a}/sales/supplier-invoices", json={
            "supplier_id": sup_a, "invoice_number": f"SINV-A-{uid_a}",
            "invoice_date": "2025-07-01",
            "lines": [{"description": "Mat", "quantity": 1, "unit_price": "300", "total": "300"}]},
            headers=h_a)
        sinv_a_id = r.json()["id"]
        print(f"  Tenant A created supplier invoice: {sinv_a_id[:8]}...")

        r = await c.get(f"{BASE}/{tid_b}/sales/supplier-invoices", headers=h_b)
        count = r.json().get("total", len(r.json().get("invoices", [])))
        passed = count == 0
        results.append({"test": "Supplier Invoice cross-tenant LIST", "count": count, "passed": passed})
        print(f"  Tenant B LIST supplier invoices: count={count} [{'PASS' if passed else 'FAIL'}]")

        # â”€â”€ Test 3: Fiscal Years â”€â”€
        print("\n=== FISCAL YEARS ===")
        r = await c.post(f"{BASE}/{tid_a}/infrastructure/fiscal-years", json={
            "name": f"FY-A-{uid_a}", "start_date": "2025-01-01", "end_date": "2025-12-31",
            "is_current": True}, headers=h_a)
        fy_a_id = r.json()["id"]
        print(f"  Tenant A created FY: {fy_a_id[:8]}...")

        r = await c.get(f"{BASE}/{tid_b}/infrastructure/fiscal-years", headers=h_b)
        count = len(r.json())
        passed = count == 0
        results.append({"test": "Fiscal Year cross-tenant LIST", "count": count, "passed": passed})
        print(f"  Tenant B LIST fiscal years: count={count} [{'PASS' if passed else 'FAIL'}]")

        # â”€â”€ Test 4: Bank Reconciliation â”€â”€
        print("\n=== BANK RECONCILIATION ===")
        # Create bank GL account for Tenant A
        r = await c.post(f"{BASE}/{tid_a}/accounting/accounts", json={
            "code": f"1{uid_a[:4]}", "name": "Bank A", "name_ar": "Ø¨Ù†Ùƒ",
            "account_type": "asset", "normal_balance": "debit"}, headers=h_a)
        bank_gl_a = r.json()["id"]

        conn = await asyncpg.connect('postgres://eos:0100@127.0.0.1:5432/eos_main')
        bank_acc_a = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO bank_accounts (id, tenant_id, account_id, bank_name, account_number, currency, current_balance, is_active) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            bank_acc_a, tid_a, bank_gl_a, "Bank A", "11111", "EGP", 100000, True)
        await conn.close()

        r = await c.post(f"{BASE}/{tid_a}/accounting/bank-reconciliations", json={
            "bank_account_id": bank_acc_a, "statement_date": "2025-07-01",
            "statement_balance": "100000", "book_balance": "100000"}, headers=h_a)
        recon_a_id = r.json()["id"]
        print(f"  Tenant A created reconciliation: {recon_a_id[:8]}...")

        r = await c.get(f"{BASE}/{tid_b}/accounting/bank-reconciliations", headers=h_b)
        count = r.json().get("total", len(r.json().get("reconciliations", [])))
        passed = count == 0
        results.append({"test": "Reconciliation cross-tenant LIST", "count": count, "passed": passed})
        print(f"  Tenant B LIST reconciliations: count={count} [{'PASS' if passed else 'FAIL'}]")

        # â”€â”€ Test 5: Account Statements â”€â”€
        print("\n=== ACCOUNT STATEMENTS ===")
        r = await c.post(f"{BASE}/{tid_a}/accounting/account-statements", json={
            "account_id": bank_gl_a, "period_id": fy_a_id,
            "opening_balance": "50000", "closing_balance": "60000",
            "total_debit": "20000", "total_credit": "10000"}, headers=h_a)
        stmt_a_id = r.json()["id"]
        print(f"  Tenant A created statement: {stmt_a_id[:8]}...")

        r = await c.get(f"{BASE}/{tid_b}/accounting/account-statements", headers=h_b)
        count = r.json().get("total", len(r.json().get("statements", [])))
        passed = count == 0
        results.append({"test": "Statement cross-tenant LIST", "count": count, "passed": passed})
        print(f"  Tenant B LIST statements: count={count} [{'PASS' if passed else 'FAIL'}]")

        # â”€â”€ Test 6: Exchange Rates â”€â”€
        print("\n=== EXCHANGE RATES ===")
        r = await c.get(f"{BASE}/{tid_a}/infrastructure/currencies", headers=h_a)
        cur_a = r.json()[0]["id"] if r.json() else None
        if cur_a:
            r = await c.post(f"{BASE}/{tid_a}/infrastructure/exchange-rates", json={
                "currency_id": cur_a, "rate": "50.5", "effective_date": "2025-01-01"}, headers=h_a)
            print(f"  Tenant A created exchange rate")

        r = await c.get(f"{BASE}/{tid_b}/infrastructure/exchange-rates", headers=h_b)
        count = len(r.json())
        passed = count == 0
        results.append({"test": "Exchange Rate cross-tenant LIST", "count": count, "passed": passed})
        print(f"  Tenant B LIST exchange rates: count={count} [{'PASS' if passed else 'FAIL'}]")

        # â”€â”€ SUMMARY â”€â”€
        print("\n" + "=" * 60)
        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        failed = total - passed_count
        print(f"MULTI-TENANCY ISOLATION: {passed_count}/{total} passed")
        if failed:
            print("FAILED:")
            for r in results:
                if not r["passed"]:
                    print(f"  - {r['test']}: {r}")
        else:
            print("ALL ISOLATION TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(test_isolation())
