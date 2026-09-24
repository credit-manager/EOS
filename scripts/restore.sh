#!/bin/bash
# EOS Database Restore Script
# Usage: ./scripts/restore.sh <backup_file>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la "$PROJECT_DIR/backups/" 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"
echo "=== 2TO EOS Restore ==="
echo "Restoring from: $BACKUP_FILE"

cd "$PROJECT_DIR"

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_URL="${DATABASE_URL:-sqlite:///./eos_demo.db}"

if [[ "$DB_URL" == postgresql* ]]; then
    echo "Restoring PostgreSQL database..."
    gunzip -c "$BACKUP_FILE" | psql "${DB_URL}"
elif [[ "$DB_URL" == sqlite* ]]; then
    DB_PATH=$(echo "$DB_URL" | sed 's|sqlite:///||')
    echo "Restoring SQLite database to: $DB_PATH"
    gunzip -c "$BACKUP_FILE" > "$DB_PATH"
fi

echo "=== Restore complete ==="
