# EOS ERP Generation E2E Contract

## Scenario A — Tourism

Tenant `tourism-a` may generate entities such as `customer`, `booking`, `hotel`, `tour`, and `supplier`.

## Scenario B — Construction

Tenant `construction-b` may independently generate `customer`, `project`, `contract`, `boq`, and `supplier`.

The same entity code is valid in different tenants. The uniqueness boundary is `(tenant_id, code)`.

## Runtime invariant

Every tenant-owned generated physical table contains `tenant_id` and every runtime query must constrain tenant-owned records by the authenticated tenant.

## Generation pipeline

```text
Business description
        ↓
AI Composer
        ↓
Industry + modules + entities + workflows
        ↓
Validation
        ↓
Builder draft
        ↓
Transactional publish
        ↓
Tenant-scoped metadata + physical schema
        ↓
Dynamic CRUD
        ↓
ERP runtime
```

The E2E test suite currently verifies the tenant-scoping contracts. A live database generation test should be run against a disposable PostgreSQL database before production deployment.
