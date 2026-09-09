"""
P36 AI-Powered Features Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_ai_models": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "model_type": "VARCHAR(50) NOT NULL",
        "target_entity": "VARCHAR(100) NOT NULL",
        "config": "JSONB",
        "status": "VARCHAR(20) DEFAULT 'ready'",
        "accuracy_score": "DECIMAL(5,4)",
        "trained_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_ai_predictions": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "model_id": "VARCHAR(36) REFERENCES dbp_ai_models(id) ON DELETE SET NULL",
        "entity_type": "VARCHAR(100)",
        "entity_id": "VARCHAR(36)",
        "prediction_type": "VARCHAR(50) NOT NULL",
        "predicted_value": "JSONB NOT NULL",
        "confidence": "DECIMAL(5,4)",
        "actual_value": "JSONB",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "expires_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_ai_recommendations": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "entity_type": "VARCHAR(100)",
        "entity_id": "VARCHAR(36)",
        "recommendation_type": "VARCHAR(50) NOT NULL",
        "title": "VARCHAR(255) NOT NULL",
        "description": "TEXT",
        "priority": "VARCHAR(10) DEFAULT 'medium'",
        "impact_score": "DECIMAL(5,4)",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "acknowledged_by": "VARCHAR(100)",
        "acknowledged_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_ai_anomalies": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "entity_type": "VARCHAR(100) NOT NULL",
        "entity_id": "VARCHAR(36)",
        "metric_name": "VARCHAR(100) NOT NULL",
        "expected_value": "DECIMAL(20,4)",
        "actual_value": "DECIMAL(20,4)",
        "deviation_pct": "DECIMAL(10,2)",
        "severity": "VARCHAR(10) DEFAULT 'medium'",
        "status": "VARCHAR(20) DEFAULT 'detected'",
        "resolved_by": "VARCHAR(100)",
        "resolved_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_ai_models": ["tenant_id, company_id"],
    "dbp_ai_predictions": ["tenant_id, company_id", "model_id"],
    "dbp_ai_recommendations": ["tenant_id, company_id"],
    "dbp_ai_anomalies": ["tenant_id, company_id"],
}

if __name__ == "__main__":
    print("Running P36 migration...")
    with engine.begin() as conn:
        for table, cols in TABLES.items():
            exists = conn.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='{table}')"
            )).scalar()
            if not exists:
                col_defs = ", ".join(f"{c} {t}" for c, t in cols.items())
                conn.execute(text(f"CREATE TABLE {table} ({col_defs})"))
                print(f"  [OK] {table}")
            else:
                existing = {r[0] for r in conn.execute(text(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"
                )).fetchall()}
                for col, typ in cols.items():
                    if col not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
                        print(f"  [OK] Added {col} to {table}")

        for table, cols in INDEXES.items():
            for col in cols:
                col_clean = col.replace(", ", "_")
                idx_name = f"idx_{table}_{col_clean}"
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"))
                except Exception:
                    pass

    print("P36 migration complete.")
