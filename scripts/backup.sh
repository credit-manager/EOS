#!/bin/bash
# EOS DBP - Production Backup Script
# Run this on the production server

BACKUP_DIR="/home/eos/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="eos_main"
DB_USER="eos"
DB_HOST="localhost"

echo "=== EOS DBP Backup ==="
echo "Time: $(date)"

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

# Database backup
echo "Backing up database..."
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/eos_db_$DATE.sql.gz

# Verify backup
if [ -f "$BACKUP_DIR/eos_db_$DATE.sql.gz" ]; then
    SIZE=$(du -h "$BACKUP_DIR/eos_db_$DATE.sql.gz" | cut -f1)
    echo "Backup successful: eos_db_$DATE.sql.gz ($SIZE)"
else
    echo "ERROR: Backup failed!"
    exit 1
fi

# Cleanup old backups (keep last 30 days)
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "eos_db_*.sql.gz" -mtime +30 -delete

echo "=== Backup Complete ==="
