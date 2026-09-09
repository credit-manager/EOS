import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://eos:0100@127.0.0.1:5432/eos_main"

def main():
    print("=" * 60)
    print("🚀 بدء إعداد قاعدة بيانات EOS DBP")
    print("=" * 60)
    
    try:
        engine = create_engine(DATABASE_URL)
        print("✅ تم الاتصال بقاعدة البيانات بنجاح")
    except Exception as e:
        print(f"❌ فشل الاتصال: {e}")
        return
    
    with engine.connect() as conn:
        # 1. جدول الكيانات
        print("\n📝 إنشاء جدول dbp_entities...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_entities (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                tenant_id VARCHAR(36),
                code VARCHAR(100) NOT NULL UNIQUE,
                name_en VARCHAR(255) NOT NULL,
                name_ar VARCHAR(255),
                faculty VARCHAR(50) NOT NULL,
                table_mapping VARCHAR(100),
                is_system BOOLEAN DEFAULT false,
                is_active BOOLEAN DEFAULT true,
                metadata_schema JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("✅ تم إنشاء dbp_entities")
        
        # 2. جدول الحقول
        print("\n📝 إنشاء جدول dbp_fields...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_fields (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                entity_id VARCHAR(36) REFERENCES dbp_entities(id) ON DELETE CASCADE,
                code VARCHAR(100) NOT NULL,
                label_en VARCHAR(255),
                label_ar VARCHAR(255),
                field_type VARCHAR(50) NOT NULL,
                is_required BOOLEAN DEFAULT false,
                ui_config JSONB DEFAULT '{}'::jsonb,
                enum_values JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_id, code)
            )
        """))
        conn.commit()
        print("✅ تم إنشاء dbp_fields")
        
        # 3. إدخال بيانات تجريبية
        print("\n🌱 إدخال بيانات تجريبية (كيان الحسابات)...")
        conn.execute(text("""
            INSERT INTO dbp_entities (code, name_en, name_ar, faculty, table_mapping, is_system)
            VALUES ('account', 'Account', 'حساب', 'finance', 'tenants', true)
            ON CONFLICT (code) DO NOTHING
        """))
        conn.commit()
        
        # 4. جلب ID الكيان
        result = conn.execute(text("SELECT id FROM dbp_entities WHERE code = 'account'")).fetchone()
        if result:
            eid = result[0]
            conn.execute(text("""
                INSERT INTO dbp_fields (entity_id, code, label_en, label_ar, field_type, is_required, ui_config)
                VALUES 
                    (:eid, 'code', 'Code', 'الكود', 'string', true, '{"order": 1}'),
                    (:eid, 'name', 'Name', 'الاسم', 'string', true, '{"order": 2}'),
                    (:eid, 'account_type', 'Type', 'النوع', 'enum', true, '{"order": 3}')
                ON CONFLICT (entity_id, code) DO NOTHING
            """), {"eid": eid})
            
            conn.execute(text("""
                UPDATE dbp_fields 
                SET enum_values = '["asset", "liability", "equity"]'::jsonb 
                WHERE code = 'account_type' AND entity_id = :eid
            """), {"eid": eid})
            conn.commit()
            print("✅ تم إدخال البيانات التجريبية")
        
        # 5. التحقق النهائي
        count = conn.execute(text("SELECT COUNT(*) FROM dbp_entities")).scalar()
        fields_count = conn.execute(text("SELECT COUNT(*) FROM dbp_fields")).scalar()
        
        print("\n" + "=" * 60)
        print("🎉 تم إعداد قاعدة البيانات بنجاح!")
        print(f"   - عدد الكيانات: {count}")
        print(f"   - عدد الحقول: {fields_count}")
        print("=" * 60)

if __name__ == "__main__":
    main()