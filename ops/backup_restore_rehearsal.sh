#!/usr/bin/env bash
set -euo pipefail

: "${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL is required}"
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required}"

WORK_DIR="${WORK_DIR:-$(mktemp -d)}"
BACKUP_FILE="${WORK_DIR}/eos_v2_rehearsal.dump"
trap 'rm -rf "${WORK_DIR}"' EXIT

started_at=$(date +%s)

echo "[1/5] Creating PostgreSQL custom-format backup"
pg_dump --format=custom --no-owner --no-acl "${SOURCE_DATABASE_URL}" --file "${BACKUP_FILE}"

echo "[2/5] Restoring into isolated PostgreSQL database"
pg_restore --clean --if-exists --no-owner --no-acl --dbname "${RESTORE_DATABASE_URL}" "${BACKUP_FILE}"

echo "[3/5] Verifying migration state"
version=$(psql "${RESTORE_DATABASE_URL}" -Atc 'SELECT version_num FROM alembic_version LIMIT 1')
test -n "${version}"
echo "migration_head=${version}"

echo "[4/5] Verifying schema integrity"
psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='eos_v2_accounts';
SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='eos_v2_journal_entries';
SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='eos_v2_journal_lines';
SELECT 1 FROM pg_constraint WHERE conname='fk_eos_v2_lines_tenant_account';
SELECT 1 FROM pg_constraint WHERE conname='fk_eos_v2_lines_tenant_entry';
SQL

echo "[5/5] Verifying row counts and foreign-key integrity"
orphan_lines=$(psql "${RESTORE_DATABASE_URL}" -Atc "SELECT COUNT(*) FROM eos_v2_journal_lines l LEFT JOIN eos_v2_journal_entries e ON e.id=l.journal_entry_id AND e.tenant_id=l.tenant_id WHERE e.id IS NULL")
test "${orphan_lines}" = "0"
psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -c 'SELECT ''eos_v2_accounts'' AS table_name, COUNT(*) AS rows FROM eos_v2_accounts;'
psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -c 'SELECT ''eos_v2_journal_entries'' AS table_name, COUNT(*) AS rows FROM eos_v2_journal_entries;'
psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -c 'SELECT ''eos_v2_journal_lines'' AS table_name, COUNT(*) AS rows FROM eos_v2_journal_lines;'
echo "orphan_lines=${orphan_lines}"

finished_at=$(date +%s)
echo "RESTORE_REHEARSAL_RESULT duration_seconds=$((finished_at-started_at)) status=passed"
