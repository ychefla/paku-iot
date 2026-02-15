#!/bin/sh
# Daily pg_dump backup script — runs inside the postgres container.
# Keeps the last 7 daily backups, removing older ones.

set -e

BACKUP_DIR="/backups"
DB="${POSTGRES_DB:-paku}"
USER="${POSTGRES_USER:-paku}"
DATE=$(date +%Y-%m-%d_%H%M)
FILE="${BACKUP_DIR}/${DB}_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting pg_dump of '${DB}' at $(date -Iseconds)"
pg_dump -U "$USER" "$DB" | gzip > "$FILE"
echo "[backup] Wrote ${FILE} ($(du -h "$FILE" | cut -f1))"

# Prune backups older than 7 days
find "$BACKUP_DIR" -name "${DB}_*.sql.gz" -mtime +7 -delete
echo "[backup] Pruned backups older than 7 days"
