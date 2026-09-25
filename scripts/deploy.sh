#!/bin/bash
# 2TO EOS — Production Deployment Script
# Run this on the production server

set -e

echo "============================================"
echo "  2TO EOS — Production Deployment"
echo "============================================"

# Check prerequisites
echo ""
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Docker is required. Install: https://docs.docker.com/get-docker/"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || COMPOSE_CMD="docker compose" || COMPOSE_CMD="docker-compose"
COMPOSE_CMD=${COMPOSE_CMD:-"docker compose"}

# Check .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Build and start
echo ""
echo "Building containers..."
$COMPOSE_CMD build

echo ""
echo "Starting services..."
$COMPOSE_CMD up -d postgres redis

echo ""
echo "Waiting for PostgreSQL..."
sleep 5

echo ""
echo "Running database migrations..."
$COMPOSE_CMD run --rm backend python -m alembic upgrade head

echo ""
echo "Seeding database..."
$COMPOSE_CMD run --rm backend python scripts/seed.py

echo ""
echo "Starting all services..."
$COMPOSE_CMD up -d

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "Services:"
echo "  Frontend:  http://localhost"
echo "  Backend:   http://localhost:8000"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:     localhost:6379"
echo ""
echo "Admin Login:"
echo "  Email:    admin@2to-eos.local"
echo "  Password: CHANGE_ME_IN_PRODUCTION"
echo ""
echo "Demo Login:"
echo "  Email:    demo@acme.com"
echo "  Password: demo12345"
