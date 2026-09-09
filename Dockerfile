# EOS Dynamic Business Platform — Production Dockerfile
# Multi-stage build: React frontend + Python runtime

FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /frontend
COPY erp-system/frontend/package.json ./package.json
RUN npm install --no-audit --no-fund
COPY erp-system/frontend/ ./
RUN npm run build

FROM python:3.12-slim AS python-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r eos && useradd -r -g eos eos
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=python-builder /root/.local /home/eos/.local
COPY --chown=eos:eos . .
RUN rm -rf /app/erp-system/frontend/dist
COPY --from=frontend-builder --chown=eos:eos /frontend/dist /app/erp-system/frontend/dist
RUN chmod 0755 /app/docker/entrypoint.sh
USER eos
ENV PATH=/home/eos/.local/bin:$PATH

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
