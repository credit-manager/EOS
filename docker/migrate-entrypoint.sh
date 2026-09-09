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

echo "EOS: applying database migrations..."
alembic upgrade head
echo "EOS: database migrations complete."

echo "EOS: reconciling least-privilege runtime database role..."
python scripts/ensure_runtime_db_role.py
echo "EOS: runtime database role ready."
