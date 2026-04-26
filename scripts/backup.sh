#!/usr/bin/env bash
# Nadini — Database Backup Script
# Usage: bash scripts/backup.sh
# Cron:  0 2 * * * cd /path/to/nadini && bash scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETAIN_DAYS="${RETAIN_DAYS:-7}"
CONTAINER="${DB_CONTAINER:-nadini-postgres-1}"
DB_NAME="${DB_NAME:-nadini}"
DB_USER="${DB_USER:-admin}"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting backup of $DB_NAME at $TIMESTAMP"

# Dump database
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom \
    > "$BACKUP_DIR/nadini_${TIMESTAMP}.dump"

# Compress
gzip "$BACKUP_DIR/nadini_${TIMESTAMP}.dump"

FILESIZE=$(ls -lh "$BACKUP_DIR/nadini_${TIMESTAMP}.dump.gz" | awk '{print $5}')
echo "[backup] Created: nadini_${TIMESTAMP}.dump.gz ($FILESIZE)"

# Cleanup old backups
find "$BACKUP_DIR" -name "nadini_*.dump.gz" -mtime +$RETAIN_DAYS -delete
REMAINING=$(ls -1 "$BACKUP_DIR"/nadini_*.dump.gz 2>/dev/null | wc -l)
echo "[backup] Cleaned backups older than $RETAIN_DAYS days. $REMAINING backups remaining."

echo "[backup] Done."
