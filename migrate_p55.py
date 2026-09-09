"""
P55 Migration — Marketplace
Tables: dbp_marketplace_items, dbp_tenant_installations
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

TABLES = {
    "dbp_marketplace_items": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("item_code", "VARCHAR(50) NOT NULL UNIQUE"),
        ("item_type", "VARCHAR(30) NOT NULL"),
        ("name_en", "VARCHAR(200) NOT NULL"),
        ("name_ar", "VARCHAR(200)"),
        ("description", "TEXT"),
        ("publisher", "VARCHAR(100) DEFAULT 'EOS Official'"),
        ("version", "VARCHAR(20) DEFAULT '1.0.0'"),
        ("is_featured", "BOOLEAN DEFAULT false"),
        ("is_free", "BOOLEAN DEFAULT true"),
        ("price_monthly", "NUMERIC(10,2) DEFAULT 0"),
        ("payload", "JSONB NOT NULL DEFAULT '{}'"),
        ("sort_order", "INTEGER DEFAULT 0"),
        ("is_published", "BOOLEAN DEFAULT true"),
        ("created_at", "TIMESTAMP DEFAULT NOW()"),
    ],
    "dbp_tenant_installations": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        ("item_code", "VARCHAR(50) NOT NULL"),
        ("status", "VARCHAR(20) NOT NULL DEFAULT 'installed'"),
        ("applied_payload", "JSONB NOT NULL DEFAULT '{}'"),
        ("installed_by", "VARCHAR(100)"),
        ("installed_at", "TIMESTAMP DEFAULT NOW()"),
        ("removed_at", "TIMESTAMP"),
    ],
}

INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_mkt_type ON dbp_marketplace_items(item_type)",
    "CREATE INDEX IF NOT EXISTS idx_inst_tenant ON dbp_tenant_installations(tenant_id)",
]

AR = lambda s: json.dumps(s, ensure_ascii=False)

ITEMS = [
    # ── Industry Packs ──
    {"id": "mkt-pack-construction", "code": "pack_construction", "type": "industry_pack",
     "en": "Construction Pack", "ar": "\u062d\u0632\u0645\u0629 \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a",
     "desc": "Full construction ERP: projects, procurement, inventory, payroll-ready HR",
     "featured": True,
     "payload": {"modules": ["accounting", "finance", "procurement", "inventory",
                              "projects", "hr", "sales", "documents", "workflow"],
                  "kpis": ["Active Projects", "Open POs", "Stock Value"]}},
    {"id": "mkt-pack-retail", "code": "pack_retail", "type": "industry_pack",
     "en": "Retail Pack", "ar": "\u062d\u0632\u0645\u0629 \u0627\u0644\u062a\u062c\u0632\u0626\u0629",
     "desc": "POS-ready retail: inventory, sales, multi-branch",
     "featured": True,
     "payload": {"modules": ["accounting", "finance", "inventory", "sales", "hr"]}},
    {"id": "mkt-pack-restaurant", "code": "pack_restaurant", "type": "industry_pack",
     "en": "Restaurant Pack", "ar": "\u062d\u0632\u0645\u0629 \u0627\u0644\u0645\u0637\u0627\u0639\u0645",
     "desc": "Food cost control, recipes, shifts",
     "payload": {"modules": ["accounting", "finance", "inventory", "sales", "hr"]}},
    {"id": "mkt-pack-manufacturing", "code": "pack_manufacturing", "type": "industry_pack",
     "en": "Manufacturing Pack", "desc": "Production orders, BOM, fixed assets",
     "payload": {"modules": ["accounting", "finance", "procurement", "inventory",
                              "projects", "hr", "fixed_assets"]}},
    {"id": "mkt-pack-trading", "code": "pack_trading", "type": "industry_pack",
     "en": "Trading Pack", "ar": "\u062d\u0632\u0645\u0629 \u0627\u0644\u062a\u062c\u0627\u0631\u0629",
     "desc": "Import/export distribution with full procurement chain",
     "payload": {"modules": ["accounting", "finance", "procurement", "inventory", "sales", "hr"]}},
    {"id": "mkt-pack-services", "code": "pack_services", "type": "industry_pack",
     "en": "Professional Services Pack", "desc": "Projects, time-based billing, proposals",
     "payload": {"modules": ["accounting", "finance", "projects", "hr", "sales", "workflow"]}},
    # ── Add-ons ──
    {"id": "mkt-addon-payroll", "code": "addon_payroll_plus", "type": "addon",
     "en": "Payroll Plus", "ar": "\u0628\u0631\u0646\u0627\u0645\u062c \u0627\u0644\u0631\u0648\u0627\u062a\u0628 \u0628\u0644\u0648\u0633",
     "desc": "Advanced payroll: GOSI, allowances, end-of-service",
     "featured": True, "free": False, "price": 49.00,
     "payload": {"modules": ["hr"], "entities": [
         {"entity_code": "payroll_adjustments", "name_en": "Payroll Adjustments",
          "fields": [{"code": "employee_name", "field_type": "string", "is_required": True},
                      {"code": "amount", "field_type": "number"},
                      {"code": "kind", "field_type": "enum",
                       "enum_values": ["bonus", "deduction", "allowance"]}]}]}},
    {"id": "mkt-addon-crm", "code": "addon_crm_lite", "type": "addon",
     "en": "CRM Lite", "desc": "Leads and opportunities pipeline",
     "free": False, "price": 29.00,
     "payload": {"modules": ["sales"], "entities": [
         {"entity_code": "crm_leads", "name_en": "CRM Leads",
          "fields": [{"code": "lead_name", "field_type": "string", "is_required": True},
                      {"code": "stage", "field_type": "enum",
                       "enum_values": ["new", "contacted", "qualified", "won", "lost"]},
                      {"code": "est_value", "field_type": "number"}]}]}},
    {"id": "mkt-addon-advanced-inv", "code": "addon_advanced_inventory", "type": "addon",
     "en": "Advanced Inventory", "desc": "Barcode & batch tracking flags",
     "payload": {"modules": ["inventory"], "settings": {"barcode_enabled": True, "batch_tracking": True}}},
    {"id": "mkt-addon-extra-reports", "code": "addon_extra_reports", "type": "addon",
     "en": "Extra Reports Bundle", "desc": "12 additional financial & operational reports",
     "payload": {"modules": ["bi"], "reports": ["aged_receivables", "cash_flow_13w", "stock_aging"]}},
]


def migrate():
    with engine.begin() as conn:
        for tbl, cols in TABLES.items():
            col_sql = ", ".join(f"{c[0]} {c[1]}" for c in cols)
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {tbl} ({col_sql})"))
            print(f"  [OK] {tbl}")
        for idx in INDICES:
            conn.execute(text(idx))
        for it in ITEMS:
            exists = conn.execute(text("SELECT id FROM dbp_marketplace_items WHERE item_code=:c"),
                                   {"c": it["code"]}).fetchone()
            if exists:
                continue
            conn.execute(text(
                "INSERT INTO dbp_marketplace_items "
                "(id, item_code, item_type, name_en, name_ar, description, is_featured, "
                "is_free, price_monthly, payload, sort_order) "
                "VALUES (:id, :c, :t, :en, :ar, :d, :feat, :free, :price, CAST(:pl AS JSONB), :so)"
            ), {"id": it["id"], "c": it["code"], "t": it["type"], "en": it["en"],
                "ar": it.get("ar"), "d": it.get("desc"), "feat": it.get("featured", False),
                "free": it.get("free", True), "price": it.get("price", 0),
                "pl": json.dumps(it.get("payload", {})), "so": len(ITEMS)})
        print(f"  [OK] Seeded {len(ITEMS)} marketplace items")


if __name__ == "__main__":
    print("=" * 60)
    print("  P55 MIGRATION — Marketplace")
    print("=" * 60)
    migrate()
    print("  DONE")
