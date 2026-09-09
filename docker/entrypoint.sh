#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required before starting EOS" >&2
  exit 1
fi

# Production images must never serve application traffic against an unmigrated
# database. Alembic is idempotent at the current head.
echo "EOS: applying database migrations..."
alembic upgrade head
echo "EOS: database migrations complete."

# Keep the runtime process as PID 1 for correct signal handling and graceful shutdown.
exec gunicorn main:app \
  --workers "${GUNICORN_WORKERS:-4}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --keep-alive "${GUNICORN_KEEP_ALIVE:-5}" \
  --access-logfile - \
  --error-logfile -
