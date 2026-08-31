#!/bin/bash
# EOS Database Restore Script
# Tests backup integrity by restoring to a test database

set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/restore.sh <backup-file>"
    echo "Example: ./scripts/restore.sh /backups/eos_backup_20240115_020000.sql.gz"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Load environment
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

TEST_DB="eos_restore_test_$(date +%s)"

echo "Creating test database: $TEST_DB"
docker-compose exec -T db psql -U $POSTGRES_USER -d postgres -c "CREATE DATABASE $TEST_DB;"

echo "Restoring from $BACKUP_FILE..."
zcat $BACKUP_FILE | docker-compose exec -T db psql -U $POSTGRES_USER -d $TEST_DB

echo "Verifying restore..."
TABLE_COUNT=$(docker-compose exec -T db psql -U $POSTGRES_USER -d $TEST_DB -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo "Tables restored: $TABLE_COUNT"

# Check critical tables
for table in dbp_users dbp_companies dbp_commerce_items dbp_trading_sales_orders dbp_retail_pos_sales dbp_restaurant_orders dbp_mfg_orders; do
    COUNT=$(docker-compose exec -T db psql -U $POSTGRES_USER -d $TEST_DB -t -c "SELECT count(*) FROM $table;")
    echo "  $table: $COUNT rows"
done

echo "Cleaning up test database..."
docker-compose exec -T db psql -U $POSTGRES_USER -d postgres -c "DROP DATABASE $TEST_DB;"

echo "Restore test PASSED!"