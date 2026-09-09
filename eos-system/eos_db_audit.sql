-- EOS Database Audit

-- 1. Record counts
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS record_count
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY n_live_tup DESC;

-- 2. Foreign Keys
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table,
    ccu.column_name AS foreign_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
   AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;

-- 3. Tenants
SELECT *
FROM tenants
LIMIT 10;

-- 4. Industries
SELECT DISTINCT industry
FROM tenants
ORDER BY industry;

-- 5. Users / Roles / Permissions
SELECT
    (SELECT COUNT(*) FROM users) AS total_users,
    (SELECT COUNT(*) FROM roles) AS total_roles,
    (SELECT COUNT(*) FROM permissions) AS total_permissions;

-- 6. Sector-specific tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
       table_name LIKE 'pharmacy_%'
    OR table_name LIKE 'restaurant_%'
    OR table_name LIKE 'retail_%'
    OR table_name LIKE 'recipe%'
  )
ORDER BY table_name;
