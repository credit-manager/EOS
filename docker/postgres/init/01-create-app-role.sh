#!/bin/sh
set -eu

: "${EOS_DB_APP_USER:?EOS_DB_APP_USER is required}"
: "${EOS_DB_APP_PASSWORD:?EOS_DB_APP_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_user="$EOS_DB_APP_USER" \
  --set=app_password="$EOS_DB_APP_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')\gexec

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user')\gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_user')\gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I', current_user, :'app_user')\gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %I', current_user, :'app_user')\gexec
SQL
