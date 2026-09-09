# EOS Dynamic Business Platform — Production Dockerfile
# Multi-stage build: React frontend + Python runtime

FROM node:24.20.0-bookworm-slim AS frontend-builder
WORKDIR /frontend
COPY erp-system/frontend/package.json erp-system/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY erp-system/frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS python-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN groupadd -r eos && useradd -r -g eos eos
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=python-builder /root/.local /home/eos/.local
COPY --chown=eos:eos . .
RUN rm -rf /app/erp-system/frontend/dist
COPY --from=frontend-builder --chown=eos:eos /frontend/dist /app/erp-system/frontend/dist
RUN chmod 0755 /app/docker/entrypoint.sh /app/docker/migrate-entrypoint.sh /app/docker/nginx-entrypoint.sh
USER eos
ENV PATH=/home/eos/.local/bin:$PATH
ENV WEB_CONCURRENCY=4

# Readiness verifies the application process and database connectivity before
# dependent production services (Nginx) are allowed to start.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8000/health/ready || exit 1
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
