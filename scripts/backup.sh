#!/bin/bash
# EOS Database Backup Script
# Runs daily via cron

set -e

# Load environment
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/eos_backup_${DATE}.sql.gz"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Starting backup at $(date)..."

# Dump database
docker-compose exec -T db pg_dump \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists | gzip > $BACKUP_FILE

# Verify backup
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file is empty or missing!"
    exit 1
fi

BACKUP_SIZE=$(du -h $BACKUP_FILE | cut -f1)
echo "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"

# Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -name "eos_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List remaining backups
echo "Remaining backups:"
ls -lh $BACKUP_DIR/eos_backup_*.sql.gz 2>/dev/null || echo "No backups found"

echo "Backup completed at $(date)"