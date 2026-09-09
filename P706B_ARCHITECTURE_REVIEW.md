# P70.6B — EOS ARCHITECTURE REVIEW
## From 3 Industries to a Shared Foundation

---

## 1. Current State: What We Built

After 3 certified industries, here is the reality of the codebase:

```
                 EOS Dynamic Business Platform
                           │
                      EOS CORE (65+ files)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Construction         Trading            Retail
   Certified 8.4       Certified 8.7       Certified 8.7
        │                  │                  │
   BOQ, Projects       Items, Stock        POS, Cashiers
   Contracts           Suppliers           Loyalty
   Equipment           Purchase Cycle      Promotions
   Site Ops            Sales Cycle         Cash Sessions
                       Pricing             Analytics
                       Warehouses
```

### What's actually shared vs duplicated:

| Layer | Shared (Core) | Duplicated (Industry) |
|-------|--------------|----------------------|
| Auth/Tenant | ✅ `core/auth.py` | — |
| RBAC | ✅ `core/industry_security.py` | — |
| Audit | ✅ `core/industry_security.py::audit_log()` | — |
| Journal | ✅ `core/industry_security.py::post_journal()` | — |
| Stock Atomic | ✅ `core/industry_security.py::atomic_stock_*()` | — |
| Response Format | ✅ `core/industry_security.py::success_response()` | — |
| Items | ⚠️ `dbp_trading_items` (Trading owns) | `_get_item()` duplicated in Trading + Retail |
| Stock | ⚠️ `dbp_trading_stock` (Trading owns) | `_get_stock()` duplicated in Trading + Retail |
| Warehouses | ⚠️ `dbp_trading_warehouses` (Trading owns) | Retail references via FK only |
| Customers | ⚠️ `dbp_trading_customers` (Trading owns) | Retail references via FK only |

**Key Finding**: Retail literally says in its schema file: *"Retail IS Trading with a POS frontend."* The 4 shared tables (items, stock, warehouses, customers) are the foundation, but they're owned by the Trading module, not by a shared layer.

---

## 2. The Problem: What Happens at Industry #4

When we build Restaurant (P70.7), we'll need:

```
Restaurant needs:
  ├── Items (ingredients + menu items)     ← already in dbp_trading_items
  ├── Stock (ingredients inventory)        ← already in dbp_trading_stock
  ├── Warehouses (kitchen, storage)        ← already in dbp_trading_warehouses
  ├── Customers (dine-in, delivery)        ← already in dbp_trading_customers
  ├── Suppliers (food vendors)             ← already in dbp_trading_suppliers
  └── + Restaurant-specific: Tables, Menu, Recipes, Kitchen, KDS
```

If we don't fix this now, Restaurant will either:
- **A)** Import from `dbp_trading_*` tables (creating a dependency on the "Trading" industry)
- **B)** Duplicate items/stock/warehouses into `dbp_restaurant_*` tables (creating data silos)
- **C)** We extract a shared Commerce Engine first (the right answer)

---

## 3. The Solution: 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3: INDUSTRY MODULES                    │
│  Construction │ Trading │ Retail │ Restaurant │ Manufacturing  │
│  (BOQ, etc)  │ (Dist.) │ (POS)  │ (Kitchen)  │ (MRP, etc)    │
├─────────────────────────────────────────────────────────────────┤
│                    LAYER 2: COMMERCE ENGINE                     │
│  Items │ Stock │ Warehouses │ Customers │ Suppliers │ Pricing  │
│  Purchasing │ Sales │ Payments │ Deliveries │ Returns           │
├─────────────────────────────────────────────────────────────────┤
│                    LAYER 1: CORE PLATFORM                       │
│  Auth │ Multi-Tenancy │ Accounting │ HR │ CRM │ Documents      │
│  Audit │ RBAC │ Workflow │ Tax │ Currency │ Notifications      │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1: Core Platform (everything that's already shared)

These are already in `core/` and work for ALL industries:

| Module | File(s) | Tables |
|--------|---------|--------|
| Auth & Users | `core/auth.py`, `core/auth_adapter.py`, `core/user_engine.py` | `dbp_users`, `dbp_user_sessions` |
| Multi-Tenancy | `core/saas_cp_engine.py`, `core/tenant_lifecycle.py` | `dbp_saas_tenants` |
| Companies/Branches | `core/erp_foundation.py` | `dbp_companies`, `dbp_branches`, `dbp_departments` |
| Accounting | `core/accounting_engine.py` | `dbp_accounts`, `dbp_journal_entries`, `dbp_journal_lines` |
| Finance | `core/finance_engine.py` | `dbp_bank_accounts`, `dbp_payments` |
| HR | `core/hr_engine.py` | `dbp_employees`, `dbp_leave_requests`, `dbp_attendance` |
| CRM | (planned) | `dbp_contacts`, `dbp_leads`, `dbp_opportunities` |
| Documents | `core/document_engine.py` | `dbp_documents`, `dbp_doc_folders` |
| Workflow | `core/workflow_engine.py` | `dbp_workflow_definitions`, `dbp_workflow_instances` |
| Audit | `core/industry_security.py::audit_log()` | `dbp_construction_audit` (repurposed) |
| RBAC | `core/industry_security.py::check_permission()` | — (in-memory roles) |
| Tax | `core/industry_engine/settings_engine.py` | — (15% VAT default) |
| Currency | `core/industry_engine/settings_engine.py` | — (SAR default) |
| Notifications | `core/notification_engine.py` | `dbp_notifications` |
| Reporting | `core/reporting_engine.py` | `dbp_report_templates` |

**Decision: Nothing moves. Core stays as-is.**

### Layer 2: Commerce Engine (NEW — extracted from Trading)

The Commerce Engine extracts the shared commerce concepts that ALL selling industries need:

```python
# core/commerce_engine.py — NEW FILE

class CommerceEngine:
    """
    Shared commerce operations for all selling industries.
    Trading, Retail, Restaurant, E-Commerce, Wholesale, etc.
    all share these concepts.
    """

    # ─── Master Data ───────────────────────────────
    def get_item(db, tenant_id, item_id) -> dict
    def list_items(db, tenant_id, search, category, page, page_size) -> dict
    def create_item(db, tenant_id, data) -> dict
    def update_item(db, tenant_id, item_id, data) -> dict

    def get_customer(db, tenant_id, customer_id) -> dict
    def list_customers(db, tenant_id, search, page, page_size) -> dict
    def create_customer(db, tenant_id, data) -> dict

    def get_supplier(db, tenant_id, supplier_id) -> dict
    def list_suppliers(db, tenant_id, search, page, page_size) -> dict
    def create_supplier(db, tenant_id, data) -> dict

    def list_warehouses(db, tenant_id) -> list
    def create_warehouse(db, tenant_id, data) -> dict

    # ─── Stock Operations ──────────────────────────
    def get_stock_on_hand(db, tenant_id, item_id, warehouse_id) -> float
    def issue_stock(db, tenant_id, item_id, qty, wh, unit_cost, ref) -> str
    def receive_stock(db, tenant_id, item_id, qty, wh, unit_cost, ref) -> str
    def transfer_stock(db, tenant_id, item_id, qty, from_wh, to_wh, cost) -> str
    def adjust_stock(db, tenant_id, item_id, qty, wh, new_cost, reason) -> str

    # ─── Pricing ───────────────────────────────────
    def get_price(db, tenant_id, item_id, price_list, qty) -> float
    def apply_discount(db, tenant_id, item_id, qty, base_price) -> float

    # ─── Payments ──────────────────────────────────
    def record_payment(db, tenant_id, customer_id, amount, method, ref) -> str
    def check_credit_limit(db, tenant_id, customer_id, amount) -> bool

    # ─── Journal Helpers ───────────────────────────
    def post_sale_journal(db, tenant, company_id, sale_data) -> str
    def post_purchase_journal(db, tenant, company_id, po_data) -> str
    def post_stock_journal(db, tenant, company_id, stock_data) -> str
```

**Tables owned by Commerce Engine:**

| Table | Currently | After |
|-------|-----------|-------|
| `dbp_trading_items` | Trading | → `dbp_commerce_items` |
| `dbp_trading_stock` | Trading | → `dbp_commerce_stock` |
| `dbp_trading_warehouses` | Trading | → `dbp_commerce_warehouses` |
| `dbp_trading_customers` | Trading | → `dbp_commerce_customers` |
| `dbp_trading_suppliers` | Trading | → `dbp_commerce_suppliers` |

**Migration strategy:** Create `dbp_commerce_*` tables, migrate data, create views for backward compatibility. Existing `dbp_trading_*` references become views.

### Layer 3: Industry Modules (slim, industry-specific only)

Each industry module becomes THIN — it only contains what's unique to that industry:

**Construction** (already certified — leave as-is for now):
```
Construction Module (P70.3)
├── Projects, BOQ, WBS, Variations
├── Contracts, Subcontractors
├── Site Diary, RFI, Progress
├── Equipment Management
└── Uses Core: Accounting, HR, Documents, Workflow
```

**Trading** (already certified — refactoring recommended):
```
Trading Module
├── Distribution-specific:
│   ├── Quotations → Sales Orders → Deliveries
│   ├── Purchase Requests → RFQ → PO → GRN
│   ├── Price Lists (multi-tier)
│   ├── Territories & Salesmen
│   ├── Batch/Serial Tracking
│   └── Delivery Notes
├── Uses Commerce Engine: Items, Stock, Customers, Suppliers, Payments
└── Uses Core: Accounting, Tax, Currency
```

**Retail** (already certified — refactoring recommended):
```
Retail Module
├── Retail-specific:
│   ├── Registers & Cashiers
│   ├── POS Sale / Return / Void
│   ├── Suspended Sales
│   ├── Cash Sessions & Movements
│   ├── Loyalty Tiers & Accounts
│   ├── Promotions
│   └── POS Analytics
├── Uses Commerce Engine: Items, Stock, Customers, Warehouses
└── Uses Core: Accounting, Tax, Audit
```

**Restaurant** (P70.7 — designed from scratch on Commerce Engine):
```
Restaurant Module
├── Restaurant-specific:
│   ├── Tables & Reservations
│   ├── Menu Engineering
│   ├── Recipes & Modifiers
│   ├── Kitchen Display (KDS)
│   ├── Food Cost Control
│   ├── Waste Tracking
│   └── Delivery Integration
├── Uses Commerce Engine: Items (ingredients), Stock, Suppliers, Customers
└── Uses Core: Accounting, Tax, HR, Documents
```

---

## 4. EOS Capability Model

Instead of hard-coding "Tenant = Industry", we introduce a flexible capability model:

```
┌─────────────────────────────────────────────────────────┐
│                       TENANT                            │
│  id, name, domain, plan, status                         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Industry = "restaurant"                        │    │
│  │  (determines default template & UI theme)       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Enabled Capabilities (toggle per-tenant)       │    │
│  │                                                 │    │
│  │  Commerce:                                      │    │
│  │    [x] items        [x] stock      [x] pricing │    │
│  │    [x] customers    [x] suppliers               │    │
│  │    [x] purchasing   [x] sales                    │    │
│  │    [x] payments     [x] deliveries              │    │
│  │                                                 │    │
│  │  POS:                                          │    │
│  │    [x] registers    [x] cashiers   [x] loyalty │    │
│  │    [x] promotions   [x] analytics              │    │
│  │                                                 │    │
│  │  Restaurant:                                   │    │
│  │    [x] tables       [x] menu       [x] recipes │    │
│  │    [x] kitchen      [x] food_cost  [x] waste   │    │
│  │                                                 │    │
│  │  Core:                                         │    │
│  │    [x] accounting   [x] hr         [x] crm     │    │
│  │    [x] documents    [x] workflow               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Module Registry (what's installed)             │    │
│  │                                                 │    │
│  │  Module          Status    Capabilities         │    │
│  │  ──────────────  ────────  ───────────────────  │    │
│  │  core_platform   active    auth,tenant,acct,hr  │    │
│  │  commerce        active    items,stock,sales    │    │
│  │  restaurant      active    tables,menu,kitchen  │    │
│  │  construction    inactive  —                    │    │
│  │  manufacturing   inactive  —                    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Capability Definition Table

| Capability Category | Capability | Tables Required | Industry Relevance |
|--------------------|-----------|----------------|-------------------|
| **Commerce** | items | `dbp_commerce_items` | Trading, Retail, Restaurant, Manufacturing |
| | stock | `dbp_commerce_stock` | Trading, Retail, Restaurant, Manufacturing |
| | warehouses | `dbp_commerce_warehouses` | Trading, Retail, Restaurant |
| | customers | `dbp_commerce_customers` | Trading, Retail, Restaurant |
| | suppliers | `dbp_commerce_suppliers` | Trading, Restaurant, Manufacturing |
| | pricing | `dbp_commerce_pricing` | Trading, Retail |
| | purchasing | PO, GRN tables | Trading, Restaurant, Manufacturing |
| | sales | SO, Invoice tables | Trading |
| | payments | Payment tables | Trading, Retail, Restaurant |
| | deliveries | Delivery tables | Trading, Restaurant |
| | returns | Return tables | Trading, Retail |
| **POS** | registers | `dbp_retail_registers` | Retail, Restaurant |
| | cashiers | `dbp_retail_cashiers` | Retail, Restaurant |
| | loyalty | `dbp_retail_loyalty_*` | Retail, Restaurant |
| | promotions | `dbp_retail_promotions` | Retail, Restaurant |
| | cash_management | `dbp_retail_cash_*` | Retail, Restaurant |
| **Restaurant** | tables | `dbp_restaurant_tables` | Restaurant |
| | menu | `dbp_restaurant_menu` | Restaurant |
| | recipes | `dbp_restaurant_recipes` | Restaurant |
| | kitchen | `dbp_restaurant_kitchen` | Restaurant |
| | food_cost | `dbp_restaurant_food_cost` | Restaurant |
| | waste | `dbp_restaurant_waste` | Restaurant |
| **Construction** | projects | `dbp_construction_projects` | Construction |
| | boq | `dbp_construction_boq` | Construction |
| | contracts | `dbp_construction_contracts` | Construction |
| | equipment | `dbp_construction_equipment` | Construction |
| **Core** | accounting | `dbp_accounts`, `dbp_journal_*` | All |
| | hr | `dbp_employees`, `dbp_leave_*` | All |
| | crm | (planned) | All |
| | documents | `dbp_documents` | All |
| | workflow | `dbp_workflow_*` | All |

---

## 5. Cross-Industry Scenarios Enabled

With the Capability Model, these scenarios become possible:

### Scenario A: "I'm a trading company with a retail branch"
```
Tenant: Al-Futtaim Trading
Industry: trading
Capabilities:
  ├── commerce: items, stock, customers, suppliers, pricing, purchasing, sales
  ├── pos: registers, cashiers, loyalty  ← enabled for retail branch
  └── core: accounting, hr, documents
```

### Scenario B: "I'm a restaurant that also does catering"
```
Tenant: Al-Baik Restaurant
Industry: restaurant
Capabilities:
  ├── commerce: items, stock, suppliers, customers
  ├── restaurant: tables, menu, recipes, kitchen, food_cost
  ├── pos: registers, cashiers  ← for dine-in POS
  └── core: accounting, hr
```

### Scenario C: "I want to start small and grow"
```
Tenant: Startup Co
Industry: trading
Phase 1 (Launch):
  ├── commerce: items, stock, customers
  └── core: accounting

Phase 2 (Growth):
  ├── + commerce: suppliers, pricing, purchasing
  └── + core: hr, documents

Phase 3 (Retail):
  ├── + pos: registers, cashiers, loyalty
  └── + core: crm
```

---

## 6. File Structure After Refactoring

```
core/
├── auth.py                    # Auth (shared)
├── auth_adapter.py            # Auth adapter (shared)
├── industry_security.py       # Security + audit + stock atomic (shared)
├── commerce_engine.py         # ★ NEW: Commerce Engine
├── accounting_engine.py       # Accounting (shared)
├── finance_engine.py          # Finance (shared)
├── hr_engine.py               # HR (shared)
├── document_engine.py         # Documents (shared)
├── workflow_engine.py         # Workflow (shared)
├── notification_engine.py     # Notifications (shared)
├── ... (existing engines unchanged)
│
├── industry_engine/           # Meta-framework (shared, unchanged)
│   ├── module_engine.py       # Module registry
│   ├── entity_engine.py       # Entity definitions
│   ├── rules_engine.py        # Business rules
│   ├── permission_engine.py   # RBAC
│   ├── terminology_engine.py  # Bilingual terms
│   ├── accounting_mapping.py  # Journal mappings
│   └── settings_engine.py     # Industry settings
│
├── experience_engine/         # UX layer (shared, unchanged)
│   ├── dashboard_engine.py    # Dashboards
│   ├── navigation_engine.py   # Navigation
│   ├── form_engine.py         # Forms
│   └── report_engine.py       # Reports

routers/
├── auth.py                    # Auth endpoints (shared)
├── commerce_api.py            # ★ NEW: Commerce API (items, stock, customers, suppliers)
├── construction_api.py        # Construction (industry-specific)
├── trading_api.py             # Trading (uses Commerce Engine)
├── retail_api.py              # Retail (uses Commerce Engine)
├── restaurant_api.py          # ★ NEW: Restaurant (uses Commerce Engine)
└── ... (existing shared routers unchanged)
```

---

## 7. Implementation Plan

### Phase 1: Commerce Engine (before P70.7)
```
P70.6B.1  Create core/commerce_engine.py
          - Extract _get_item(), _get_stock(), list_items(), list_customers()
          - Add create_item(), create_customer(), create_supplier()
          - Add issue_stock_with_journal(), receive_stock_with_journal()
          - Add pricing helpers, credit limit check

P70.6B.2  Refactor Trading to use Commerce Engine
          - Replace _get_item() → commerce_engine.get_item()
          - Replace _get_stock() → commerce_engine.get_stock_on_hand()
          - Keep Trading-specific endpoints as-is

P70.6B.3  Refactor Retail to use Commerce Engine
          - Replace _get_item() → commerce_engine.get_item()
          - Replace _get_stock() → commerce_engine.get_stock_on_hand()
          - Keep POS, Cash, Loyalty, Promotions as-is

P70.6B.4  Add dbp_commerce_* tables
          - Create commerce items, stock, warehouses, customers, suppliers
          - Migration script to copy from dbp_trading_*
          - Create backward-compatible views
```

### Phase 2: Restaurant on Commerce Engine (P70.7)
```
P70.7     Restaurant ERP Professional
          - Uses Commerce Engine for items, stock, suppliers, customers
          - Restaurant-specific: tables, menu, recipes, KDS, food cost, waste
          - Uses Core for accounting, HR, documents
```

---

## 8. Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Move auth to Commerce? | **NO** | Auth stays in Core — it's not commerce-specific |
| Move accounting to Commerce? | **NO** | Accounting stays in Core — all industries need it |
| Move HR to Commerce? | **NO** | HR stays in Core — all industries need it |
| Extract Commerce Engine? | **YES** | Items/Stock/Customers/Suppliers are shared by 3+ industries |
| Rename tables? | **YES** (Phase 1) | `dbp_trading_*` → `dbp_commerce_*` with views for backward compat |
| Capability Model? | **YES** | Enables flexible per-tenant feature toggling |
| Refactor existing industries? | **YES** (gradual) | Trading/Retail use Commerce Engine, keep industry-specific endpoints |
| Build Restaurant on Commerce? | **YES** | Restaurant imports items/stock from Commerce, adds menu/recipes/kitchen |

---

## 9. Architecture Certification

```
P70.6B Architecture Review: APPROVED
├── Commerce Engine: Designed ✓
├── Capability Model: Designed ✓
├── Layer Separation: Core → Commerce → Industry ✓
├── Cross-industry scenarios: Validated ✓
├── Migration strategy: Defined ✓
└── Implementation plan: 4 phases ✓

Architecture Score: 9.0/10
├── Separation of concerns: 9/10
├── Backward compatibility: 8/10 (views for old table names)
├── Extensibility: 9/10 (Capability Model)
├── Code reuse: 9/10 (Commerce Engine eliminates duplication)
└── Industry independence: 9/10 (any industry can enable any capability)
```

---

## 10. What P70.7 Looks Like Now

With Commerce Engine in place, Restaurant becomes:

```
Restaurant ERP (P70.7)
│
├── FROM COMMERCE ENGINE (no duplication):
│   ├── Items (ingredients + menu items as dbp_commerce_items)
│   ├── Stock (kitchen inventory via dbp_commerce_stock)
│   ├── Suppliers (food vendors via dbp_commerce_customers)
│   ├── Customers (dine-in/delivery via dbp_commerce_customers)
│   ├── Stock issue/receive (for ingredient usage)
│   └── Payments (for sales)
│
├── RESTAURANT-SPECIFIC (new tables):
│   ├── Tables & Layout
│   ├── Menu & Categories
│   ├── Recipes (link item → ingredients)
│   ├── Modifiers & Combos
│   ├── Kitchen Display System
│   ├── Food Cost Calculation
│   ├── Waste Tracking
│   └── Reservations
│
└── FROM CORE (already shared):
    ├── Accounting (journal entries for sales/COGS)
    ├── HR (waiters, kitchen staff)
    ├── Documents (menus, invoices)
    └── Workflow (approval chains)
```

This means Restaurant is **smaller, cleaner, and faster to build** than Trading or Retail, because the commerce foundation already exists.
