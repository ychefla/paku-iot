-- Initialize the measurements table for Paku IoT
-- This script is executed when the Postgres container starts for the first time

CREATE TABLE IF NOT EXISTS measurements (
    id BIGSERIAL PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    temperature_c NUMERIC,
    humidity_percent NUMERIC,
    pressure_hpa NUMERIC,
    battery_mv INTEGER
);

-- Create index on timestamp for efficient time-based queries
CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts);

-- Create index on sensor_id for efficient filtering
CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id ON measurements(sensor_id);
