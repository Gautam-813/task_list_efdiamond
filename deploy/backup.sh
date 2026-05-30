#!/usr/bin/env bash
# Shared Task Management App — Backup Script
# Usage: ./backup.sh [output_directory]

set -euo pipefail

APP_DIR="/opt/task_app"
BACKUP_DIR="${1:-/opt/task_app/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"

mkdir -p "${BACKUP_PATH}"

echo "==> Backing up database..."

# Detect database type from .env
DB_URL=$(grep "^DATABASE_URL" "${APP_DIR}/.env" | cut -d= -f2-)

if echo "$DB_URL" | grep -q "sqlite"; then
    DB_FILE=$(echo "$DB_URL" | sed 's|sqlite:///||')
    DB_PATH="${APP_DIR}/${DB_FILE}"
    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "${BACKUP_PATH}/task_app.db"
        echo "    SQLite database backed up."
    fi
elif echo "$DB_URL" | grep -q "postgresql"; then
    DATABASE=$(echo "$DB_URL" | grep -oP '/\K[^?]+')
    pg_dump "${DB_URL}" > "${BACKUP_PATH}/task_app.sql"
    echo "    PostgreSQL dump created."
fi

echo "==> Backing up .env..."
if [ -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env" "${BACKUP_PATH}/.env"
fi

echo ""
echo "Backup complete: ${BACKUP_PATH}"
echo ""

# Rotate — keep the 7 most recent backups
ls -1dt "${BACKUP_DIR}/"*/ 2>/dev/null | tail -n +8 | while read -r old; do
    rm -rf "$old"
    echo "Removed old backup: $old"
done
