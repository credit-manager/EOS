"""Manual smoke test for the ETA invoice endpoint.

This script is a standalone diagnostic and is not part of the automated test suite.
"""

import argparse
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test the ETA invoice endpoint")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/api/v1")
    parser.add_argument("--email", default="eta-smoke@test.com")
    parser.add_argument("--password", default="EtaTest!@#")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with httpx.Client(timeout=20.0) as client:
        register = client.post(
            f"{args.base_url}/auth/register",
            json={
                "email": args.email,
                "password": args.password,
                "company_name": "ETA Smoke Test",
                "company_name_ar": "اختبار ETA",
                "industry": "tech",
            },
        )
        print(f"Register: {register.status_code}")
        if register.status_code not in {200, 201, 409}:
            print(f"  Error: {register.text[:200]}")
            return 1

        registration_data: dict[str, Any] = register.json() if register.content else {}
        tenant_id = registration_data.get("tenant_id")

        login = client.post(
            f"{args.base_url}/auth/login",
            json={
                "email": args.email,
                "password": args.password,
                **({"tenant_id": tenant_id} if tenant_id else {}),
            },
        )
        print(f"Login: {login.status_code}")
        if login.status_code != 200:
            print(f"  Error: {login.text[:200]}")
            return 1

        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            f"{args.base_url}/eta/1/eta-invoices",
            json={
                "invoice_number": "EI-20260820-000001",
                "issue_date": "2026-08-20",
                "due_date": "2026-09-20",
                "supplier_id": "supplier-001",
                "buyer_id": "customer-001",
                "supplier_name_ar": "شركة الغذاء",
                "buyer_name_ar": "شركة التوزيع",
                "items": [
                    {
                        "description": "منتج غذائي",
                        "quantity": 100,
                        "unit_price": 50.00,
                        "total_price": 5000.00,
                    }
                ],
                "currency": "EGP",
            },
            headers=headers,
        )

    print(f"ETA Invoice: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  invoice_number: {data.get('invoice_number')}")
        print(f"  tax_amount: {data.get('tax_amount')}")
        print(f"  total_amount: {data.get('total_amount')}")
        print(f"  eta_status: {data.get('eta_status')}")
        return 0

    print(f"  Error: {response.text[:200]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
