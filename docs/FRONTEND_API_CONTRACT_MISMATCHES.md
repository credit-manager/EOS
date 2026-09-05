# Frontend/Backend API Contract Mismatches — Requires Decision

Discovered while verifying `erp-system/frontend` (the design-system-declared
canonical frontend) against the live backend OpenAPI schema. The frontend
was never actually exercised against the real backend before this check —
these are confirmed by comparing `erp-system/frontend/src/services/api.ts`
against `main.app.openapi()['paths']`.

## Confirmed mismatches

| Frontend calls | Backend reality | Status |
|---|---|---|
| `POST /api/v1/auth/refresh` | **Does not exist anywhere in the backend.** No refresh-token issuance/rotation logic exists in `routers/auth.py` or `core/auth*.py` at all. | Missing feature, not a naming issue. |
| `GET/POST /api/v1/customers` | Real paths are `/api/v1/sales/customers` **and** `/api/v1/dynamic/companies/{cid}/customers` (two competing implementations — see the known `sales.py`/`sales_api.py` duplication). | Naming + duplication issue. |
| `GET /api/v1/reports/profit-and-loss` | Real paths: `/api/v1/accounting/reports/profit-and-loss` **and** a separate unversioned `/reports/profit-and-loss`. | Naming + versioning inconsistency. |
| `GET /api/v1/reports/sales` | No exact match; closest are `/api/v1/sales/leads`, `/api/v1/dynamic/sales-orders`. | Needs a defined canonical endpoint. |
| `GET /api/v1/reports/inventory` | Real paths under `/api/v1/inventory/*` (`products`, `warehouses`, `stock/movements`), no single `/reports/inventory` aggregate. | Needs a defined canonical endpoint. |

## Why this was not fixed blindly in this pass

Guessing which backend path is "correct" for `/customers` or
`/reports/profit-and-loss` would mean silently picking a winner between
the duplicated router implementations (`sales.py` vs `sales_api.py`, and
similar) — an architectural decision that has been explicitly deferred to
the product owner in prior reviews. Rewiring the frontend to point at the
wrong one would just move the bug, not fix it.

## Required decision before this frontend can go live

1. Resolve the router duplication (`sales`/`sales_api`, etc.) so there is
   exactly one canonical `/customers`-equivalent path.
2. Decide on and implement a real refresh-token flow (issuance, storage,
   rotation, revocation) — `erp-system/frontend/src/services/api.ts`
   already has correct client-side handling for it; only the backend
   endpoint is missing.
3. Standardize report endpoints under one versioned prefix
   (`/api/v1/reports/*` recommended) and update all report routers to
   match, instead of the current mix of `/api/v1/accounting/reports/*`,
   `/reports/*`, and `/api/v1/analytics/*`.

## Verification method (for re-checking after fixes)

```bash
python -c "
import main
schema = main.app.openapi()
paths = set(schema['paths'].keys())
required = ['/api/v1/auth/refresh', '/api/v1/customers',
            '/api/v1/reports/profit-and-loss', '/api/v1/reports/sales',
            '/api/v1/reports/inventory']
missing = [p for p in required if p not in paths]
print('Missing:', missing or 'NONE')
"
