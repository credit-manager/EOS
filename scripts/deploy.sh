#!/bin/bash
# EOS DBP - Production Deployment Script
# Run this on the VPS after uploading EOS-Release-1.0

set -e

echo "=== EOS DBP Deployment ==="
echo "Time: $(date)"

# Configuration
APP_DIR="/home/eos/eos-dbp"
DB_NAME="eos_main"
DB_USER="eos"

# Step 1: Setup application directory
echo "[1/8] Setting up application directory..."
mkdir -p $APP_DIR
cp -r . $APP_DIR/
cd $APP_DIR

# Step 2: Create environment file
echo "[2/8] Creating environment file..."
if [ ! -f .env ]; then
    cat > .env << EOF
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
CORS_ORIGINS=https://app.yourdomain.com
ALLOWED_HOSTS=api.yourdomain.com,localhost
EOF
    echo "Created .env file"
else
    echo ".env already exists"
fi

# Step 3: Install dependencies
echo "[3/8] Installing dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Step 4: Setup PostgreSQL
echo "[4/8] Setting up PostgreSQL..."
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" || true
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" || true

# Step 5: Restore database
echo "[5/8] Restoring database..."
if [ -f backups/eos_production_backup.sql ]; then
    PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME < backups/eos_production_backup.sql
    echo "Database restored"
else
    echo "No backup found, skipping restore"
fi

# Step 6: Run migrations
echo "[6/8] Running migrations..."
alembic upgrade head || true

# Step 7: Build Docker image
echo "[7/8] Building Docker image..."
docker build -t eos-dbp .

# Step 8: Start services
echo "[8/8] Starting services..."
docker-compose up -d

echo "=== Deployment Complete ==="
echo "API: http://localhost:8000"
echo "Health: http://localhost:8000/health"
