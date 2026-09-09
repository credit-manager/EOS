-- تهيئة قاعدة بيانات ERP
-- يتم تشغيل هذا الملف تلقائياً عند بدء PostgreSQL لأول مرة

-- إنشاء الامتدادات
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- إنشاء دالة لتحديث timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ملاحظة: الجداول سيتم إنشاؤها بواسطة Alembic migrations
-- هذا الملف للتهيئة الأولية فقط

-- إدراج بيانات تجريبية (اختياري)
-- INSERT INTO users (email, username, hashed_password, is_active, is_superuser)
-- VALUES ('admin@erp.com', 'admin', '$2b$12$...', true, true);

COMMENT ON DATABASE erp_db IS 'قاعدة بيانات نظام ERP المتكامل';
