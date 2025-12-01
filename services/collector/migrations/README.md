# Database Migrations

## 001_update_schema_for_new_topics.sql

Migrates the measurements table from the old schema to the new schema that supports the hierarchical topic structure.

**Changes:**
- Migrates from: `sensor_id` + fixed columns for Ruuvi data
- Migrates to: `site_id`, `system`, `device_id`, `location` + flexible `metrics` JSONB column

**Applied:** 2025-12-01

**To apply manually:**
```bash
docker exec -i paku_postgres psql -U paku -d paku < 001_update_schema_for_new_topics.sql
```

**Note:** This migration was already applied to the production database.
