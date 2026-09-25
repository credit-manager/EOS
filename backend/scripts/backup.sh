#!/bin/bash
# EOS Database Backup Script
# Run daily via cron: 0 2 * * * /path/to/scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/eos}"
DB_URL="${DATABASE_URL:-sqlite:///./eos_demo.db}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

if [[ "$DB_URL" == postgresql* ]]; then
    # PostgreSQL backup
    PGPASSWORD="${PGPASSWORD:-}" pg_dump -h localhost -U eos_user eos_db | gzip > "$BACKUP_DIR/eos_$DATE.sql.gz"
elif [[ "$DB_URL" == sqlite* ]]; then
    # SQLite backup
    DB_PATH="${DB_URL#sqlite:///}"
    cp "$DB_PATH" "$BACKUP_DIR/eos_$DATE.db"
    gzip "$BACKUP_DIR/eos_$DATE.db"
fi

# Cleanup old backups
find "$BACKUP_DIR" -name "eos_*" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: eos_$DATE"
