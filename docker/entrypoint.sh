#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required before starting EOS" >&2
  exit 1
fi

# Database migrations run in the dedicated migration service before API traffic is enabled.
# Keeping DDL out of the long-running application process allows the API to use a
# least-privilege database role and avoids concurrent migration races between replicas.

# Keep the runtime process as PID 1 for correct signal handling and graceful shutdown.
exec gunicorn main:app \
  --workers "${GUNICORN_WORKERS:-4}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --keep-alive "${GUNICORN_KEEP_ALIVE:-5}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --max-requests "${GUNICORN_MAX_REQUESTS:-1000}" \
  --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
  --access-logfile - \
  --error-logfile -
