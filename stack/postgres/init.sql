-- Paku IoT Database Schema
-- Create measurements table for storing sensor data

CREATE TABLE IF NOT EXISTS measurements (
    id BIGSERIAL PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    temperature_c NUMERIC(5, 2) NOT NULL,
    humidity_percent NUMERIC(5, 2) NOT NULL,
    pressure_hpa NUMERIC(6, 2) NOT NULL,
    battery_mv INTEGER NOT NULL,
    acceleration_x_mg INTEGER,
    acceleration_y_mg INTEGER,
    acceleration_z_mg INTEGER,
    acceleration_total_mg INTEGER,
    tx_power_dbm INTEGER,
    movement_counter INTEGER,
    measurement_sequence INTEGER,
    mac TEXT
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts);
CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id ON measurements(sensor_id);
CREATE INDEX IF NOT EXISTS idx_measurements_sensor_ts ON measurements(sensor_id, ts DESC);
