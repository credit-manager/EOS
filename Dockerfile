# EOS Dynamic Business Platform — Production Dockerfile
# Multi-stage build with a minimal Alpine runtime and a non-root service user.

FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-alpine AS builder
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev postgresql-dev
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-alpine
WORKDIR /app
RUN addgroup -S eos && adduser -S -G eos eos
RUN apk add --no-cache libpq
COPY --from=builder /root/.local /home/eos/.local
COPY --chown=eos:eos . .
RUN rm -rf /app/eos-system/frontend/dist
COPY --from=frontend-builder --chown=eos:eos /app/frontend/dist /app/eos-system/frontend/dist
USER eos
ENV PATH=/home/eos/.local/bin:$PATH

# /health is the load-balancer/Kubernetes-compatible liveness endpoint.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"
EXPOSE 8000
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-"]
