-- Migration: Drop raw_data JSONB column from ecoflow_measurements
-- Prerequisites:
--   1. Grafana dashboards no longer reference raw_data (done)
--   2. Collector no longer writes to raw_data (done)
--   3. pg_dump backup taken before running this script
--
-- Estimated space savings: ~760 MB (raw JSONB → dedicated columns)
-- Run: psql -U paku -d paku -f drop_raw_data.sql

BEGIN;

-- Confirm no active queries use raw_data (safety check)
DO $$
BEGIN
    RAISE NOTICE 'Dropping raw_data JSONB column from ecoflow_measurements...';
    RAISE NOTICE 'Table size before: %', (
        SELECT pg_size_pretty(pg_total_relation_size('ecoflow_measurements'))
    );
END $$;

ALTER TABLE ecoflow_measurements DROP COLUMN IF EXISTS raw_data;

DO $$
BEGIN
    RAISE NOTICE 'Column dropped successfully.';
    RAISE NOTICE 'Run VACUUM FULL ecoflow_measurements to reclaim disk space.';
END $$;

COMMIT;
