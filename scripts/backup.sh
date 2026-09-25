#!/bin/bash
# EOS Database Backup Script
# Usage: ./scripts/backup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== 2TO EOS Backup ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

cd "$PROJECT_DIR"

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run Python backup script
python "$SCRIPT_DIR/../backend/scripts/backup.py"

echo "=== Backup complete ==="
