#!/bin/sh
# Runs idempotent migrations on first-time database initialisation.
# Existing databases get the same files from the deploy workflow.
set -e
for f in /migrations/*.sql; do
  [ -e "$f" ] || continue
  echo "Applying migration $f"
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
done
