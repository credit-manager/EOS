# EOS Dynamic Business Platform — Production Dockerfile
# Multi-stage build for smaller production image

FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Keep production Python aligned with the CI/test matrix.
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r eos && useradd -r -g eos eos
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /home/eos/.local
COPY --chown=eos:eos . .
RUN rm -rf /app/eos-system/frontend/dist
COPY --from=frontend-builder --chown=eos:eos /app/frontend/dist /app/eos-system/frontend/dist
USER eos
ENV PATH=/home/eos/.local/bin:$PATH

# /health is the load-balancer/Kubernetes-compatible liveness endpoint.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
EXPOSE 8000
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-"]
