# Frontend/Backend API Contract — Status

The canonical React frontend is now aligned with the versioned backend contracts for authentication, CRM customers, inventory suppliers/products, and reporting.

## Fixed

| Frontend contract | Backend contract |
|---|---|
| Authentication | `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me` |
| Customers | `/api/v1/sales/customers` |
| Suppliers | `/api/v1/inventory/suppliers` |
| Products | `/api/v1/inventory/products` |
| Reports | `/api/v1/reports/*` with the legacy `/reports/*` routes retained for compatibility |

Refresh sessions use opaque, hashed, rotating tokens with a 30-day lifetime. Reuse of a rotated/revoked token revokes its entire token family. Password changes, password resets, role changes, and account deactivation revoke existing refresh sessions.

## Remaining architecture work

1. **Generic orders/invoices:** the platform still exposes industry-specific order/invoice contracts. The generic frontend facade remains intentionally fail-closed rather than guessing a schema.
2. **Router consolidation:** `sales.py`/`sales_api.py`, `inventory.py`/`inventory_api.py`, `accounting.py`/`accounting_api.py`, and `hr.py`/`hr_api.py` still require a controlled deprecation/consolidation pass.

## Verification

```bash
python -c "
import main
schema = main.app.openapi()
paths = set(schema['paths'].keys())
required = [
    '/api/v1/auth/login',
    '/api/v1/auth/refresh',
    '/api/v1/auth/logout',
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
