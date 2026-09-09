from database import engine, Base, SessionLocal
from sqlalchemy import text
from models import DBPEntity, DBPField

print("🔄 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created!")

print("🔄 Seeding data...")
db = SessionLocal()

try:
    db.execute(text("""
        INSERT INTO dbp_entities
        (code, name_en, name_ar, faculty, table_mapping, is_system)
        VALUES
        ('account', 'Account', 'حساب', 'finance', 'tenants', true)
        ON CONFLICT (code) DO NOTHING
    """))
    db.commit()

    result = db.execute(
        text("SELECT id FROM dbp_entities WHERE code = 'account'")
    ).fetchone()

    if result:
        eid = result[0]

        db.execute(text("""
            INSERT INTO dbp_fields
            (entity_id, code, label_en, label_ar, field_type, is_required, ui_config)
            VALUES
            (:eid, 'code', 'Code', 'الكود', 'string', true,
             '{"component": "input", "order": 1}'),
            (:eid, 'name', 'Name', 'الاسم', 'string', true,
             '{"component": "input", "order": 2}'),
            (:eid, 'account_type', 'Type', 'النوع', 'enum', true,
             '{"component": "select", "order": 3}')
            ON CONFLICT (entity_id, code) DO NOTHING
        """), {"eid": eid})

        db.execute(text("""
            UPDATE dbp_fields
            SET enum_values = '["asset", "liability", "equity"]'::jsonb
            WHERE code = 'account_type'
              AND entity_id = :eid
        """), {"eid": eid})

        db.commit()
        print("✅ Data seeded successfully!")
    else:
        print("⚠️ Entity not found after insert")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()

finally:
    db.close()
