# EOS Dynamic Business Platform — Production Dockerfile
# Multi-stage build: React frontend + Python runtime

# ═══════════════════════════════════════════════
# Stage 1: Build canonical EOS React frontend
# ═══════════════════════════════════════════════
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /frontend
COPY erp-system/frontend/package.json ./package.json
RUN npm install --no-audit --no-fund
COPY erp-system/frontend/ ./
RUN npm run build

# ═══════════════════════════════════════════════
# Stage 2: Build Python dependencies
# ═══════════════════════════════════════════════
FROM python:3.14-slim AS python-builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ═══════════════════════════════════════════════
# Stage 3: Production runtime
# ═══════════════════════════════════════════════
FROM python:3.14-slim

WORKDIR /app

RUN groupadd -r eos && useradd -r -g eos eos

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /root/.local /home/eos/.local
COPY --chown=eos:eos . .

# The canonical React source is erp-system/frontend and main.py serves the
# build output from the same canonical path.
RUN rm -rf /app/erp-system/frontend/dist
COPY --from=frontend-builder --chown=eos:eos /frontend/dist /app/erp-system/frontend/dist

USER eos
ENV PATH=/home/eos/.local/bin:$PATH

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
