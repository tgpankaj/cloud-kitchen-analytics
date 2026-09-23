#!/bin/bash
# ============================================
# Database Backup Script
# Usage: ./scripts/backup_db.sh
# ============================================

set -e

# Config
DB_NAME="${DB_NAME:-cloudkitchen}"
DB_USER="${DB_USER:-kitchen_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/cloudkitchen_${TIMESTAMP}.sql.gz"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🗄️  Database Backup${NC}"
echo "   Database: $DB_NAME"
echo "   Host:     $DB_HOST:$DB_PORT"
echo "   User:     $DB_USER"
echo ""

# Create backup dir
mkdir -p "$BACKUP_DIR"

# Check pg_dump
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}❌ pg_dump not found. Install PostgreSQL client tools.${NC}"
    exit 1
fi

# Get password
if [ -z "$PGPASSWORD" ]; then
    read -sp "🔑 Enter DB password: " PGPASSWORD
    echo ""
    export PGPASSWORD
fi

# Create backup
echo -e "${YELLOW}📦 Creating backup...${NC}"

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup created${NC}"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $SIZE"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Cleanup old backups (keep last 7)
echo ""
echo -e "${YELLOW}🧹 Cleaning old backups (keeping last 7)...${NC}"
cd "$BACKUP_DIR"
ls -t cloudkitchen_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -v
cd - > /dev/null

# List backups
echo ""
echo -e "${YELLOW}📁 Available backups:${NC}"
ls -lh "$BACKUP_DIR"/cloudkitchen_*.sql.gz 2>/dev/null | tail -5

echo ""
echo -e "${GREEN}✅ Backup complete!${NC}"

# Restore instructions
echo ""
echo -e "${YELLOW}To restore:${NC}"
echo "   gunzip -c $BACKUP_FILE | psql -h $DB_HOST -U $DB_USER $DB_NAME"