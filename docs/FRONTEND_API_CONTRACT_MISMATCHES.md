# Frontend/Backend API Contract Mismatches — Status

Originally discovered while verifying `erp-system/frontend` against the live backend OpenAPI schema. Updated after the follow-up contract fix pass.

## Fixed in this pass

| Frontend call | Fix applied |
|---|---|
| `GET/POST /api/v1/customers` | Frontend `customersAPI` now uses the existing `/api/v1/sales/customers` contract. |
| `GET /api/v1/reports/*` | `main.py` mounts the existing reporting router under `/api/v1`, while preserving the legacy unversioned `/reports/*` routes for backward compatibility. |
| `suppliersAPI` | Repointed to `/api/v1/inventory/suppliers`. |
| `productsAPI` | Repointed to `/api/v1/inventory/products`. |
| `POST /api/v1/auth/refresh` | Confirmed no refresh-token backend exists. The frontend already handles a 401 by clearing the session and emitting `eos:auth-expired`; the backend feature remains open. |

## Still unresolved

1. **Refresh-token backend implementation.** A production-grade flow still needs issuance, secure client storage policy, rotation, reuse detection, revocation, and session invalidation.
2. **Orders/invoices generic API.** The backend exposes industry-specific order/invoice contracts. The frontend must either become industry-aware or consume a new generic tenant-template dispatch endpoint. It must not guess one industry's schema.
3. **Router duplication.** `sales.py`/`sales_api.py`, `inventory.py`/`inventory_api.py`, `accounting.py`/`accounting_api.py`, and `hr.py`/`hr_api.py` remain live and should be consolidated through an explicit deprecation/removal plan.

## Verification method

```bash
python -c "
import main
schema = main.app.openapi()
paths = set(schema['paths'].keys())
required = [
    '/api/v1/reports/profit-and-loss',
    '/api/v1/reports/sales',
    '/api/v1/reports/inventory',
    '/api/v1/sales/customers',
    '/api/v1/inventory/suppliers',
    '/api/v1/inventory/products',
]
missing = [p for p in required if p not in paths]
print('Missing:', missing or 'NONE')
"
```

The verification must also confirm that every versioned reporting endpoint retains the same authentication, permission, rate-limit, and tenant-context dependencies as the legacy route because the same `reporting_api.router` instance is mounted under both prefixes.
