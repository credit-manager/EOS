#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required for database migrations" >&2
  exit 1
fi

echo "EOS: applying database migrations..."
alembic upgrade head
echo "EOS: database migrations complete."
