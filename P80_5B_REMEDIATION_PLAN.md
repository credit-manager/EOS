# P80.5B — Critical Remediation Plan (9/9)
## Date: 2026-08-28
## Status: PLAN — Awaiting Approval

---

## Scope

```
9 CRITICAL fixes
Files to modify: 8 files
New files: 0
Estimated time: 2-3 hours of code changes
Testing after: Full regression (599 tests) + 9 new critical tests
```

---

## C1. Accounting API — Add tenant_id to ALL queries

**File:** `routers/accounting_api.py`
**Problem:** No tenant_id filtering. Any user can read/modify/delete any tenant's financial data.
**Impact:** Cross-tenant financial data exposure.

### Changes Required

```
Every endpoint that queries dbp_accounts or dbp_journal_entries
must add: WHERE ... AND tenant_id = :tid

Extract tenant_id from user token: tid = user.get("tenant_id")

Affected endpoints (ALL):
- list_accounts (line ~30)
- get_account (line ~66)
- create_account (line ~82)
- update_account (line ~104)
- delete_account (line ~120)
- list_journal_entries (line ~134)
- get_journal_entry (line ~181)
- create_journal_entry (line ~213)
- post_journal_entry (line ~247)
- reverse_journal_entry (line ~261)
- trial_balance (line ~273)
- income_statement
- balance_sheet
- cash_flow
- profit_and_loss
```

### Pattern

```python
# BEFORE:
db.execute(text("SELECT * FROM dbp_accounts WHERE id = :id"), {"id": account_id})

# AFTER:
tid = user.get("tenant_id")
db.execute(text("SELECT * FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"),
           {"id": account_id, "tid": tid})
```

### Test

```python
def test_c1_tenant_isolation():
    """Verify accounting data is isolated per tenant"""
    # Login as tenant A user
    # Create account, journal entry
    # Login as tenant B user
    # Try to read tenant A's accounts → should return empty
    # Try to read tenant A's journal entries → should return empty
    # Try to update tenant A's account → should fail (404)
```

---

## C2. Portal — Replace SHA-256 with bcrypt

**File:** `core/portal_engine.py:40-41`
**Problem:** `hashlib.sha256(password.encode()).hexdigest()` — unsalted, trivially crackable.
**Impact:** Portal passwords weak against rainbow table attacks.

### Changes Required

```python
# BEFORE:
def _hash_password(self, password):
    return hashlib.sha256(password.encode()).hexdigest()

# AFTER:
import hashlib, secrets, os

def _hash_password(self, password):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${h.hex()}"

def _verify_password(self, password, stored):
    if '$' not in stored:
        return hashlib.sha256(password.encode()).hexdigest() == stored  # legacy compat
    salt, h = stored.split('$', 1)
    new_h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return secrets.compare_digest(new_h.hex(), h)
```

### Test

```python
def test_c2_portal_password_hashing():
    """Verify portal uses strong password hashing"""
    # Create portal user
    # Check stored password is NOT plain SHA-256
    # Verify password verification works
    # Verify wrong password fails
```

---

## C3. WebSocket — Reject unauthenticated connections

**File:** `routers/ws_router.py:77-80`
**Problem:** Falls through to anonymous on invalid/missing token.
**Impact:** Any anonymous user can connect and receive broadcast messages.

### Changes Required

```python
# BEFORE:
if not token or not payload:
    user_id = f"anonymous_{uuid.uuid4().hex[:8]}"
    tenant_id = "default"

# AFTER:
if not token or not payload:
    await websocket.close(code=4001, reason="Authentication required")
    return

# Also add tenant isolation to broadcast:
def broadcast(self, message, tenant_id=None):
    for ws, info in self.connections.items():
        if tenant_id and info.get("tenant_id") != tenant_id:
            continue
        # send message
```

### Test

```python
def test_c3_websocket_auth():
    """Verify WebSocket rejects unauthenticated connections"""
    # Connect without token → should get 4001 close
    # Connect with invalid token → should get 4001 close
    # Connect with valid token → should connect
    # Tenant A broadcasts → Tenant B should NOT receive
```

---

## C4. Journal Posting — Prevent double-posting

**File:** `core/accounting_engine.py:116-158`
**Problem:** Read-then-write without locking. Two concurrent requests can both post the same entry.
**Impact:** Double-counts GL balances, corrupts financial statements.

### Changes Required

```python
# BEFORE:
entry = db.execute(text("SELECT id, status FROM dbp_journal_entries WHERE id = :id"), {"id": entry_id}).fetchone()
if entry[1] == "posted":
    raise ValueError("Already posted")
# ... update ...

# AFTER:
entry = db.execute(text(
    "SELECT id, status FROM dbp_journal_entries WHERE id = :id FOR UPDATE"
), {"id": entry_id}).fetchone()
if entry[1] == "posted":
    raise ValueError("Already posted")
# ... update in same transaction ...
```

### Test

```python
def test_c4_no_double_posting():
    """Verify journal entries cannot be double-posted"""
    # Create journal entry
    # Post it
    # Try to post again → should fail
    # Verify GL balances are correct (not doubled)
```

---

## C5. Accounting API — Update GL balances on posting

**File:** `routers/accounting_api.py:247-258`
**Problem:** API only sets status='posted', never updates dbp_accounts.current_balance.
**Impact:** All GL-derived reports (trial balance, P&L, balance sheet) are wrong.

### Changes Required

```python
# AFTER setting status='posted', add:
lines = db.execute(text(
    "SELECT * FROM dbp_journal_lines WHERE journal_entry_id = :jid"
), {"jid": entry_id}).fetchall()

for line in lines:
    db.execute(text(
        "UPDATE dbp_accounts SET current_balance = current_balance + :dr - :cr WHERE id = :aid AND tenant_id = :tid"
    ), {"dr": line.debit, "cr": line.credit, "aid": line.account_id, "tid": tid})
```

### Test

```python
def test_c5_gl_balances_updated():
    """Verify GL balances update when journal entry is posted"""
    # Create account
    # Create journal entry (debit account A, credit account B)
    # Post entry
    # Verify account A current_balance increased
    # Verify account B current_balance decreased
```

---

## C6. Stock Transfer — Fix unit_cost source table

**File:** `routers/trading_api.py:1042-1052`
**Problem:** Reads unit_cost from dbp_trading_stock but operates on dbp_commerce_stock.
**Impact:** Wrong inventory valuation after transfers.

### Changes Required

```python
# BEFORE:
stock_row = db.execute(text(
    "SELECT unit_cost FROM dbp_trading_stock WHERE tenant_id=:t AND item_id=:iid AND warehouse_id=:w"
), ...)

# AFTER:
stock_row = db.execute(text(
    "SELECT unit_cost FROM dbp_commerce_stock WHERE tenant_id=:t AND item_id=:iid AND warehouse_id=:w"
), ...)
```

### Test

```python
def test_c6_stock_transfer_cost():
    """Verify stock transfer uses correct unit_cost"""
    # Receive item at warehouse A (cost = 100)
    # Transfer to warehouse B
    # Verify warehouse B unit_cost = 100
```

---

## C7. Alembic — Remove hardcoded credentials

**File:** `alembic.ini:89`
**Problem:** `sqlalchemy.url = postgresql://eos:0100@127.0.0.1:5432/eos_main`
**Impact:** Database credentials exposed in plaintext.

### Changes Required

```ini
# BEFORE:
sqlalchemy.url = postgresql://eos:0100@127.0.0.1:5432/eos_main

# AFTER:
sqlalchemy.url = %(DATABASE_URL)s
```

Also update `alembic/env.py` to read from environment:

```python
import os
config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL", ""))
```

### Test

```python
def test_c7_no_hardcoded_creds():
    """Verify no hardcoded credentials in config files"""
    # Check alembic.ini has no plaintext password
    # Check .env files are in .gitignore
```

---

## C8. Secrets — Remove real secret from .env.production

**File:** `.env.production:14`
**Problem:** Real-looking secret key committed to release.
**Impact:** JWT signing key exposed if file leaks.

### Changes Required

```env
# BEFORE:
EOS_SECRET_KEY=V9hlS_-LWVt-NsDOtn_m_XiWtMsTyuYkxsL0UmUcum6xnOIcEIe5hWXjbn5SW8PGAg7XmUDThuqnMaiOHYrtCQ

# AFTER:
EOS_SECRET_KEY=CHANGE_ME_GENERATE_ON_DEPLOYMENT
```

### Test

```python
def test_c8_no_real_secrets():
    """Verify no real secrets in config files"""
    # Check .env.production has only placeholders
```

---

## C9. Services API — Fix accept_quotation

**File:** `routers/services_api.py:315`
**Problem:** References `q_id` instead of `quote_id` — NameError at runtime.
**Impact:** accept_quotation endpoint is completely broken.

### Changes Required

```python
# BEFORE:
desc = f"Contract from {q_id[:8]}"

# AFTER:
desc = f"Contract from {quote_id[:8]}"
```

### Test

```python
def test_c9_services_accept_quotation():
    """Verify accept_quotation works without errors"""
    # Create lead, opportunity, quotation
    # Accept quotation
    # Verify contract created
```

---

## Execution Order

```
Step 1: C9 (simplest — variable name fix)
Step 2: C8 (secret placeholder)
Step 3: C7 (alembic config)
Step 4: C6 (stock transfer table)
Step 5: C2 (portal password hashing)
Step 6: C3 (WebSocket auth)
Step 7: C1 (accounting tenant_id)
Step 8: C4 (journal double-posting)
Step 9: C5 (GL balance updates)

After each: Run affected tests
After all: Run full regression (599 tests)
Then: Run 9 new critical tests
```

---

## Verification Checklist

```
After all 9 Critical fixes:

□ Accounting API queries all have tenant_id
□ Portal passwords hashed with PBKDF2 (not SHA-256)
□ WebSocket rejects unauthenticated connections
□ WebSocket broadcasts are tenant-isolated
□ Journal entries cannot be double-posted
□ GL balances update when entries are posted
□ Stock transfers read unit_cost from correct table
□ alembic.ini has no hardcoded credentials
□ .env.production has placeholder secrets only
□ services_api accept_quotation works
□ All 599 existing tests pass
□ 9 new critical tests pass
```
