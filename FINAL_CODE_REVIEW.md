# EOS DBP — FINAL CODE REVIEW
## Date: 2026-08-28
## Status: REVIEW COMPLETE — 9 CRITICAL ISSUES FOUND

---

## Executive Summary

```
╔══════════════════════════════════════════════════════════════╗
║  EOS DBP — FINAL CODE REVIEW                               ║
╠══════════════════════════════════════════════════════════════╣
║  Files examined:    170+ Python files                       ║
║  Backend files:      89 core + 80 routers = 169             ║
║  Frontend files:       1 (placeholder only)                 ║
║  SQL/Migrations:       1 (alembic)                          ║
║  Tests:               26                                    ║
║  Docker/Config:       10+                                   ║
╠══════════════════════════════════════════════════════════════╣
║  🔴 Critical:    9                                         ║
║  🟠 High:       17                                         ║
║  🟡 Medium:     30                                         ║
║  🔵 Low:        18                                         ║
║  🟢 Good:       38+                                        ║
╠══════════════════════════════════════════════════════════════╣
║  VERDICT: NOT READY FOR PRODUCTION                         ║
║  9 critical issues must be fixed before first customer     ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Scores

```
Architecture:       6/10  — Dual stock tables, duplicated helpers
Security:           4/10  — SHA-256 passwords, cross-tenant leaks, WS unauth
Database:           5/10  — Float for money, race conditions, N+1 patterns
Backend:            5/10  — Missing error handling, manual sessions, sys.path hacks
Accounting:         3/10  — No tenant isolation, no GL updates, double-posting
Commerce:           4/10  — Dual stock tables, no PO receipt stock update
Industry ERPs:      6/10  — Good workflows but hardcoded VAT, broken services accept
Frontend:           1/10  — Single HTML placeholder, no ERP UI
Infrastructure:     7/10  — Good Docker/Nginx but backup script broken
Code Quality:       5/10  — __pycache__ in release, test files, dead code

FINAL SCORE:        4.6/10
```

---

## 🔴 CRITICAL Issues (9) — Must Fix Before Production

### C1. Cross-Tenant Data Leak in Accounting API
```
File:    routers/accounting_api.py (ALL endpoints)
Impact:  Any authenticated user can read/modify/delete ANY tenant's financial data
Cause:   No tenant_id filtering in any query
Fix:     Add AND tenant_id = :tid to every query
```

### C2. SHA-256 Password Hashing (Unsalted)
```
File:    core/portal_engine.py:40-41, _create_user.py:35
Impact:  Portal passwords trivially crackable with rainbow tables
Cause:   hashlib.sha256() without salt or iterations
Fix:     Use bcrypt/argon2/scrypt
```

### C3. WebSocket Accepts Unauthenticated Connections
```
File:    routers/ws_router.py:77-80
Impact:  Any anonymous user can connect and receive broadcast messages
Cause:   Falls through to anonymous on invalid/missing token
Fix:     Reject connection if auth fails, never allow anonymous
```

### C4. Journal Entries Can Be Double-Posted
```
File:    core/accounting_engine.py:116-158, routers/accounting_api.py:247-258
Impact:  Double-counts GL balances, corrupts financial statements
Cause:   Read-then-write without SELECT FOR UPDATE
Fix:     Use SELECT FOR UPDATE or UPDATE WHERE status='draft'
```

### C5. Accounting API Does NOT Update GL Balances
```
File:    routers/accounting_api.py:247-258
Impact:  All GL-derived reports (trial balance, P&L, balance sheet) are wrong
Cause:   API only sets status='posted', never updates dbp_accounts.current_balance
Fix:     Delegate to AccountingEngine.post_journal_entry()
```

### C6. Stock Transfers Read unit_cost From Wrong Table
```
File:    routers/trading_api.py:1042-1052
Impact:  Wrong inventory valuation after transfers, corrupted WAC
Cause:   Reads from dbp_trading_stock but operates on dbp_commerce_stock
Fix:     Read unit_cost from dbp_commerce_stock
```

### C7. Hardcoded Credentials in alembic.ini
```
File:    alembic.ini:89
Impact:  Database credentials exposed in plaintext
Cause:   postgresql://eos:0100@127.0.0.1:5432/eos_main hardcoded
Fix:     Read from environment variable
```

### C8. Hardcoded Secret Key in .env.production
```
File:    .env.production:14
Impact:  JWT signing key exposed if file leaks
Cause:   Real-looking secret value instead of placeholder
Fix:     Generate unique key per deployment
```

### C9. Services API: accept_quotation Broken (Undefined Variable)
```
File:    routers/services_api.py:315
Impact:  accept_quotation endpoint crashes at runtime (NameError)
Cause:   References q_id instead of quote_id
Fix:     Change q_id to quote_id
```

---

## 🟠 HIGH Issues (17) — Fix Before First Customer

| # | Finding | File |
|---|---------|------|
| H1 | Rate limiter in-memory, resets on restart, per-worker | core/rate_limit.py |
| H2 | require_permission allows None user (bypasses auth) | core/auth.py:117 |
| H3 | Test secret key fallback if env not set | core/auth.py:22-25 |
| H4 | Float for money in journal balancing | core/industry_security.py:142 |
| H5 | Float for money in commerce (all monetary values) | core/commerce_engine.py:57 |
| H6 | Float for money in accounting (debit/credit) | core/accounting_engine.py:95 |
| H7 | Race condition in sequence generation | core/industry_security.py:240 |
| H8 | Race condition in entry number generation | core/accounting_engine.py:254 |
| H9 | Refund without SELECT FOR UPDATE | core/payment_engine.py:90 |
| H10 | No refund amount validation (over-refunding) | core/payment_engine.py:97 |
| H11 | Hardcoded VAT 14% in retail (should be 15% or configurable) | routers/retail_api.py:226 |
| H12 | Hardcoded VAT 15% in restaurant, services (not configurable) | routers/restaurant_api.py:744 |
| H13 | Hardcoded labor rate $50/hr in services | routers/services_api.py:880 |
| H14 | Trading audit endpoint queries wrong table | routers/trading_api.py:1102 |
| H15 | Inconsistent stock tables (trading vs commerce) | routers/trading_api.py (multiple) |
| H16 | PO receipt does NOT update stock levels | routers/inventory_api.py:424 |
| H17 | create_journal_entry does NOT validate debits == credits | routers/accounting_api.py:213 |

---

## 🟡 MEDIUM Issues (30)

| # | Finding | File |
|---|---------|------|
| M1 | 6 routers bypass Depends(get_db), manual sessions | Multiple routers |
| M2 | sys.path.insert hacks in 10 router files | 10 router files |
| M3 | Bare except Exception in analytics_api | routers/analytics_api.py |
| M4 | No input validation in reporting_api date params | routers/reporting_api.py |
| M5 | N+1 in post_journal (loop of INSERTs) | core/industry_security.py:156 |
| M6 | N+1 in commerce_dashboard (6 sequential queries) | core/commerce_engine.py:629 |
| M7 | N+1 in auto_match (query per bank line) | core/reconciliation_engine.py:118 |
| M8 | N+1 in notification process_event | core/notification_engine.py:196 |
| M9 | _ensure_tables() DDL on every constructor (4 engines) | Multiple engines |
| M10 | Journal reversal does not update GL | routers/accounting_api.py:261 |
| M11 | No returns/void accounting workflow | Accounting layer |
| M12 | Multi-currency accounting not implemented | Accounting layer |
| M13 | No DELETE endpoints across all industry modules | All 6 routers |
| M14 | Construction API duplicates helper functions | routers/construction_api.py |
| M15 | Construction API returns inconsistent format | routers/construction_api.py |
| M16 | X-Forwarded-For header spoofable | core/rate_limit.py:50 |
| M17 | No pagination in customer portal queries | core/portal_engine.py:82 |
| M18 | Currency conversion uses float | core/currency_engine.py:105 |
| M19 | No currency rate history (old rates deleted) | core/currency_engine.py:68 |
| M20 | calculate_gain_loss missing tenant_id filter | core/currency_engine.py:130 |
| M21 | Price list has no line items | core/commerce_engine.py:591 |
| M22 | No warehouse update/delete | core/commerce_engine.py |
| M23 | Reserved stock quantity never used | core/commerce_engine.py |
| M24 | Stock adjustments use wrong table | routers/trading_api.py:1179 |
| M25 | inventory_api uses different tables from commerce | routers/inventory_api.py |
| M26 | __pycache__ directories in release (100+ files) | Release package |
| M27 | 26 test files in production release | tests/ directory |
| M28 | backup.sh: $DB_PASSWORD never set | scripts/backup.sh:19 |
| M29 | deploy.sh: alembic errors suppressed with || true | scripts/deploy.sh:59 |
| M30 | Grafana default password in docker-compose | docker-compose.yml:139 |

---

## 🔵 LOW Issues (18)

| # | Finding | File |
|---|---------|------|
| L1 | Audit table named dbp_construction_audit for all industries | core/industry_security.py |
| L2 | Manual field validation instead of Pydantic | routers/auth.py |
| L3 | .env.production has realistic-looking secret | .env.production |
| L4 | Entry numbers race condition (medium-low impact) | core/accounting_engine.py |
| L5 | inventory_report loads all items in Python | core/reporting_engine.py |
| L6 | Hardcoded 'default' warehouse | core/commerce_engine.py |
| L7 | _get_stock/_recalc_stock dead code | routers/trading_api.py:61 |
| L8 | Manufacturing validation sets defined but unused | routers/manufacturing_api.py |
| L9 | Hardcoded account codes across all modules | All industry routers |
| L10 | Hardcoded points formula in retail | routers/retail_api.py:234 |
| L11 | No .dockerignore file | Root directory |
| L12 | Python 3.14-slim base image (pre-release) | Dockerfile |
| L13 | Nginx ${DOMAIN} not expanded | nginx/conf.d/eos.conf |
| L14 | Monitoring ports exposed to host | docker-compose.yml |
| L15 | Backup alerts reference unexported metrics | monitoring/alert_rules.yml |
| L16 | Prometheus/Grafana ports exposed | docker-compose.yml |
| L17 | _role_matches prefix matching too broad | core/security.py:383 |
| L18 | Backup script no pg_dump error handling | scripts/backup.sh |

---

## 🟢 Good Practices Found

| # | Area | Finding |
|---|------|---------|
| 1 | Security | Parameterized SQL throughout (no value injection) |
| 2 | Security | JWT with expiry, tenant_id in token |
| 3 | Security | Security headers (CSP, HSTS, X-Frame-Options) |
| 4 | Security | Server header suppressed |
| 5 | Security | Brute force protection on 2FA |
| 6 | Security | Recovery codes hashed and single-use |
| 7 | Security | Sensitive data redaction in audit logs |
| 8 | Security | Rate limiting on auth endpoints |
| 9 | Security | CORS from env var |
| 10 | Security | Production startup validation blocks bad config |
| 11 | Database | SELECT FOR UPDATE on stock operations |
| 12 | Database | Tenant isolation on most queries |
| 13 | Database | Connection pool configured for production |
| 14 | Database | Alembic with type comparison enabled |
| 15 | Backend | HTTPException with proper status codes |
| 16 | Backend | Pydantic models for request validation |
| 17 | Backend | Credit limit checks |
| 18 | Backend | Order status lifecycle validation |
| 19 | Industry | Trading: Full sales/purchase workflow |
| 20 | Industry | Retail: Complete POS with loyalty |
| 21 | Industry | Restaurant: Most comprehensive (KDS, recipes, waste) |
| 22 | Industry | Manufacturing: BOM, routing, production orders |
| 23 | Industry | Services: CRM, projects, timesheets, invoicing |
| 24 | Industry | Construction: BOQ, procurement, equipment |
| 25 | Production | Docker multi-stage build, non-root user |
| 26 | Production | Docker Compose with health checks |
| 27 | Production | Nginx rate limiting, gzip, security headers |
| 28 | Production | Prometheus + Grafana + AlertManager |
| 29 | Production | Comprehensive alert rules |
| 30 | Production | Restore script with verification |
| 31 | Code | Bilingual error messages |
| 32 | Code | Request ID tracking |
| 33 | Code | Health check with Kubernetes probes |
| 34 | Code | Audit logging with correlation IDs |
| 35 | Accounting | Debit/credit validation |
| 36 | Accounting | Trial balance implementation |
| 37 | Commerce | Stock operations atomic |
| 38 | Commerce | Item validation on create |

---

## Priority Fix Order

```
PHASE 1 — CRITICAL (9 fixes) — Estimated: 2-3 days
├── C1: Add tenant_id to accounting_api (all queries)
├── C2: Replace SHA-256 with bcrypt in portal
├── C3: Reject unauthenticated WebSocket
├── C4: Add SELECT FOR UPDATE on journal posting
├── C5: Add GL balance updates in accounting_api
├── C6: Fix stock transfer unit_cost table
├── C7: Remove hardcoded credentials from alembic.ini
├── C8: Regenerate secret key in .env.production
└── C9: Fix q_id → quote_id in services_api

PHASE 2 — HIGH (17 fixes) — Estimated: 3-5 days
├── H1: Switch rate limiter to Redis or DB-backed
├── H2: Fix require_permission None user bypass
├── H3: Remove test secret key fallback
├── H4-H6: Replace float with Decimal for money
├── H7-H8: Fix sequence/number generation race conditions
├── H9-H10: Add FOR UPDATE + amount validation on refunds
├── H11-H13: Make VAT rate configurable per tenant
├── H14: Fix trading audit table reference
├── H15: Consolidate stock tables
├── H16: Add stock update on PO receipt
└── H17: Add debit/credit validation on creation

PHASE 3 — MEDIUM (30 fixes) — Estimated: 1-2 weeks
├── Session management fixes
├── Remove sys.path.insert hacks
├── Add error handling to all routers
├── Fix N+1 query patterns
├── Remove _ensure_tables() DDL
├── Add DELETE endpoints
├── Fix construction API consistency
├── Clean release package
└── Fix scripts

PHASE 4 — LOW (18 fixes) — Estimated: 3-5 days
├── Code cleanup
├── Docker improvements
├── Config improvements
└── Documentation
```

---

## Recommendation

```
╔══════════════════════════════════════════════════════════════╗
║  VERDICT: NOT READY FOR PRODUCTION                         ║
╠══════════════════════════════════════════════════════════════╣
║  The 599/599 test score masked critical issues:             ║
║  - Cross-tenant data leaks in accounting                   ║
║  - Weak password hashing                                   ║
║  - Unauthenticated WebSocket                               ║
║  - Race conditions in financial operations                 ║
║  - Wrong stock tables in transfers                         ║
║  - Broken services quotation acceptance                    ║
║                                                             ║
║  These issues would cause data corruption,                 ║
║  security breaches, and incorrect financial reports        ║
║  in production with real customers.                        ║
║                                                             ║
║  RECOMMENDATION: Fix all 9 CRITICAL issues,               ║
║  then all 17 HIGH issues, then re-test before deployment.  ║
╚══════════════════════════════════════════════════════════════╝
```
