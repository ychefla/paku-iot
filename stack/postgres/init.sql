-- ============================================================
-- PAKU IoT - Postgres Schema Initialization
-- ============================================================
-- This script is automatically executed when the Postgres
-- container starts for the first time (via docker-entrypoint-initdb.d).
-- ============================================================

-- Create the measurements table to store Ruuvi sensor data
CREATE TABLE IF NOT EXISTS measurements (
    id SERIAL PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    temperature_c DOUBLE PRECISION,
    humidity_percent DOUBLE PRECISION,
    pressure_hpa DOUBLE PRECISION,
    battery_mv INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create an index on ts for efficient time-range queries
CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts DESC);

-- Create an index on sensor_id for efficient sensor filtering
CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id ON measurements(sensor_id);

-- Create a composite index for common queries (sensor + time)
CREATE INDEX IF NOT EXISTS idx_measurements_sensor_ts ON measurements(sensor_id, ts DESC);
