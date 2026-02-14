#!/bin/bash
# ------------------------------------------------------------
# Docker Cleanup Script
#
# Removes dangling images, build cache, and orphaned volumes
# to prevent disk exhaustion on the production server.
#
# Install as a weekly cron job:
#   crontab -e
#   0 4 * * 0 /home/paku/paku-iot/scripts/docker-cleanup.sh >> /var/log/docker-cleanup.log 2>&1
# ------------------------------------------------------------

set -euo pipefail

echo "=== Docker cleanup started: $(date -Iseconds) ==="

echo "--- Pruning build cache ---"
docker builder prune -af --keep-storage=1GB 2>/dev/null || true

echo "--- Pruning dangling images ---"
docker image prune -f 2>/dev/null || true

echo "--- Pruning orphaned volumes ---"
docker volume prune -f 2>/dev/null || true

echo "--- Disk usage after cleanup ---"
df -h / | tail -1
docker system df

echo "=== Docker cleanup finished: $(date -Iseconds) ==="
