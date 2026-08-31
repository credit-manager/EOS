# EOS Dynamic Business Platform — Production Dockerfile
# Multi-stage build for smaller production image

# ═══════════════════════════════════════════════
# Stage 1: Build dependencies
# ═══════════════════════════════════════════════
FROM python:3.14-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ═══════════════════════════════════════════════
# Stage 2: Production runtime
# ═══════════════════════════════════════════════
FROM python:3.14-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r eos && useradd -r -g eos eos

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /home/eos/.local

# Copy application code
COPY --chown=eos:eos . .

# Switch to non-root user
USER eos

# Add local packages to PATH
ENV PATH=/home/eos/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run with gunicorn for production
CMD ["gunicorn", "main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]