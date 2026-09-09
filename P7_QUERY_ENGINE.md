# P7 — Dynamic Query Engine

**Status:** COMPLETE
**Date:** 2026-08-24
**Version:** 1.0.0

---

## 1. Implementation Summary

### New Files

| File | Purpose |
|------|---------|
| `core/query_parser.py` | Filter/sort parser with security validation |
| `test_query.py` | 26 comprehensive tests |

### Modified Files

| File | Changes |
|------|---------|
| `routers/dynamic_crud.py` | Added filters, sort params to GET /records |

---

## 2. Query Contract

### GET `/api/v1/dynamic/entities/{entity_code}/records`

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `filters` | string | — | Comma-separated filter expressions |
| `sort` | string | — | Sort expression (prefix `-` for DESC) |
| `limit` | integer | 100 | Records per page (1-500) |
| `offset` | integer | 0 | Records to skip |

### Filter Format

```
field:operator:value
```

**Examples:**
```
status:eq:active
price:gte:100
name:like:ahmed
created_at:gte:2026-01-01
code:in:P001|P002|P003
deleted_at:is_null
```

### Sort Format

```
sort=-created_at,name
```

- Prefix `-` = DESC
- No prefix = ASC

---

## 3. Operators

| Operator | SQL | Value Required |
|----------|-----|----------------|
| `eq` | `= :param` | Yes |
| `neq` | `!= :param` | Yes |
| `gt` | `> :param` | Yes |
| `gte` | `>= :param` | Yes |
| `lt` | `< :param` | Yes |
| `lte` | `<= :param` | Yes |
| `like` | `ILIKE :param` | Yes |
| `in` | `IN :param` | Yes (pipe-separated) |
| `is_null` | `IS NULL` | No |
| `is_not_null` | `IS NOT NULL` | No |

---

## 4. Security Chain

```
Request
   ↓
Parse filters/sort
   ↓
Column Allowlist (real_columns from PostgreSQL)
   ↓
Operator Allowlist (10 operators only)
   ↓
Value Type Validation
   ↓
Tenant Scope (from JWT, not user input)
   ↓
Parameterized SQL (no raw input)
   ↓
Response
```

### Security Rules

| Rule | Implementation |
|------|----------------|
| No raw SQL | All queries parameterized |
| Column validation | Must exist in real_columns |
| Operator validation | Must be in allowlist |
| Tenant isolation | JWT tenant always applied |
| SQL injection | Parameterized queries prevent it |
| Limit enforcement | MAX_LIMIT = 500 |

---

## 5. Response Format

```json
{
  "status": "success",
  "data": [...],
  "count": 10,
  "tenant_applied": true,
  "effective_tenant": "tenant_a",
  "pagination": {
    "total": 150,
    "limit": 10,
    "offset": 0,
    "has_next": true
  }
}
```

---

## 6. Test Results

### Functional Tests (13)

```
Basic list:          PASS
Filter eq:           PASS
Filter gte:          PASS
Filter in:           PASS
Filter is_null:      PASS
Sort ascending:      PASS
Sort descending:     PASS
Invalid column:      PASS (400)
Invalid operator:    PASS (400)
Pagination:          PASS
Limit enforcement:   PASS
Tenant isolation:    PASS
SQL injection:       PASS
```

### Regression Tests

```
RBAC:         17/17 ✅
Audit:         8/8  ✅
Cross-Tenant: 12/12 ✅
P7 Query:     26/26 ✅
─────────────────────
TOTAL:        63/63 ✅
```

---

## 7. API Examples

### Filter by status
```
GET /entities/products/records?filters=status:eq:active
```

### Filter by price range
```
GET /entities/products/records?filters=price:gte:100,price:lte:500
```

### Sort by price descending
```
GET /entities/products/records?sort=-price
```

### Search by name
```
GET /entities/products/records?filters=name:like:ahmed
```

### Paginate
```
GET /entities/products/records?limit=50&offset=100
```

### Combined
```
GET /entities/products/records?filters=status:eq:active,price:gte:100&sort=-created_at&limit=20
```

---

## Next: P8 Bulk / Import / Export
