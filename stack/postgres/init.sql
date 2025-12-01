-- Paku IoT Database Schema
-- Updated schema supporting the hierarchical topic structure
-- {site_id}/{system}/{device_id}/data

CREATE TABLE IF NOT EXISTS measurements (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT NOT NULL,
    system TEXT NOT NULL,
    device_id TEXT NOT NULL,
    location TEXT,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_site_device_ts ON measurements(site_id, device_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_system_ts ON measurements(system, ts DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_site_system ON measurements(site_id, system);

-- GIN index for JSONB metrics column to enable fast queries on metric fields
CREATE INDEX IF NOT EXISTS idx_measurements_metrics ON measurements USING GIN (metrics);

-- Comments for documentation
COMMENT ON TABLE measurements IS 'Time-series telemetry data from all devices across sites';
COMMENT ON COLUMN measurements.site_id IS 'Installation identifier (e.g., paku, car, home)';
COMMENT ON COLUMN measurements.system IS 'Functional system category (e.g., sensors, heater, power)';
COMMENT ON COLUMN measurements.device_id IS 'Unique device identifier within the system';
COMMENT ON COLUMN measurements.location IS 'Physical location description (optional)';
COMMENT ON COLUMN measurements.ts IS 'Measurement timestamp from device or ingestion time';
COMMENT ON COLUMN measurements.metrics IS 'Device metrics as JSON object (flexible schema per device type)';
COMMENT ON COLUMN measurements.created_at IS 'Record creation timestamp in database';
