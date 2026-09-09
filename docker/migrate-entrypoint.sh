#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required for database migrations" >&2
  exit 1
fi

if [ -z "${EOS_DB_RUNTIME_USER:-}" ] || [ -z "${EOS_DB_RUNTIME_PASSWORD:-}" ]; then
  echo "EOS_DB_RUNTIME_USER and EOS_DB_RUNTIME_PASSWORD are required" >&2
  exit 1
fi

if [ -z "${EOS_DB_EXPORTER_USER:-}" ] || [ -z "${EOS_DB_EXPORTER_PASSWORD:-}" ]; then
  echo "EOS_DB_EXPORTER_USER and EOS_DB_EXPORTER_PASSWORD are required" >&2
  exit 1
fi

echo "EOS: reconciling least-privilege runtime and monitoring roles before migrations..."
python scripts/ensure_runtime_db_role.py

echo "EOS: applying database migrations..."
alembic upgrade head
echo "EOS: database migrations complete."

echo "EOS: enforcing database role security invariants..."
python scripts/enforce_runtime_db_role_security.py
echo "EOS: database roles secured."