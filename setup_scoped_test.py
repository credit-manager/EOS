"""
Create SCOPED test table for Cross-Tenant verification.

This script:
1. Creates a table with tenant_id column (SCOPED)
2. Registers it as a DBP entity
3. Seeds test data for two tenants
"""

from database import SessionLocal, engine
from sqlalchemy import text
from models import DBPEntity, DBPField
import uuid


def setup_scoped_test():
    db = SessionLocal()

    try:
        # 1. Create SCOPED test table
        print("Creating test_products table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS test_products (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36) NOT NULL,
                code VARCHAR(50) NOT NULL,
                name VARCHAR(255) NOT NULL,
                price NUMERIC(10,2) DEFAULT 0,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # Add unique constraint on (tenant_id, code)
        db.execute(text("""
            DO $$ BEGIN
                ALTER TABLE test_products
                ADD CONSTRAINT uq_test_products_tenant_code
                UNIQUE (tenant_id, code);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$
        """))

        db.commit()
        print("  OK")

        # 2. Register as DBP entity
        print("Registering entity...")

        existing = db.query(DBPEntity).filter(
            DBPEntity.code == "test_product"
        ).first()

        if not existing:
            entity_id = str(uuid.uuid4())
            entity = DBPEntity(
                id=entity_id,
                code="test_product",
                name_en="Test Product",
                name_ar="منتج تجريبي",
                faculty="inventory",
                table_mapping="test_products",
                is_system=False,
            )
            db.add(entity)

            # Add fields
            fields = [
                DBPField(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    code="code",
                    label_en="Code",
                    label_ar="الكود",
                    field_type="string",
                    is_required=True,
                    ui_config={"order": 1},
                ),
                DBPField(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    code="name",
                    label_en="Name",
                    label_ar="الاسم",
                    field_type="string",
                    is_required=True,
                    ui_config={"order": 2},
                ),
                DBPField(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    code="price",
                    label_en="Price",
                    label_ar="السعر",
                    field_type="number",
                    is_required=False,
                    ui_config={"order": 3},
                ),
            ]

            for f in fields:
                db.add(f)

            db.commit()
            print("  OK (new entity)")
        else:
            print("  OK (existing)")

        # 3. Seed test data for two tenants
        print("Seeding test data...")

        # Clear existing test data
        db.execute(text("DELETE FROM test_products"))
        db.commit()

        tenant_a = "tenant_a"
        tenant_b = "tenant_b"

        records = [
            {"tenant_id": tenant_a, "code": "P001", "name": "Product A1", "price": 100},
            {"tenant_id": tenant_a, "code": "P002", "name": "Product A2", "price": 200},
            {"tenant_id": tenant_b, "code": "P001", "name": "Product B1", "price": 150},
            {"tenant_id": tenant_b, "code": "P003", "name": "Product B3", "price": 300},
        ]

        for rec in records:
            db.execute(text("""
                INSERT INTO test_products (id, tenant_id, code, name, price)
                VALUES (:id, :tenant_id, :code, :name, :price)
            """), {
                "id": str(uuid.uuid4()),
                "tenant_id": rec["tenant_id"],
                "code": rec["code"],
                "name": rec["name"],
                "price": rec["price"],
            })

        db.commit()
        print("  OK (4 records)")

        # 4. Verify
        result = db.execute(text(
            "SELECT tenant_id, code, name FROM test_products ORDER BY tenant_id, code"
        ))
        print("\nTest data:")
        for row in result:
            print(f"  {row[0]:10s} | {row[1]:5s} | {row[2]}")

    finally:
        db.close()


if __name__ == "__main__":
    setup_scoped_test()
