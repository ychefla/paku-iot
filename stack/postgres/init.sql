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

-- EcoFlow power station measurements table
CREATE TABLE IF NOT EXISTS ecoflow_measurements (
    id BIGSERIAL PRIMARY KEY,
    device_sn TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    soc_percent INTEGER,
    remain_time_min INTEGER,
    watts_in_sum INTEGER,
    watts_out_sum INTEGER,
    ac_out_watts INTEGER,
    dc_out_watts INTEGER,
    typec_out_watts INTEGER,
    usb_out_watts INTEGER,
    pv_in_watts INTEGER,
    raw_data JSONB
);

-- Create indexes for EcoFlow measurements
CREATE INDEX IF NOT EXISTS idx_ecoflow_measurements_ts ON ecoflow_measurements(ts);
CREATE INDEX IF NOT EXISTS idx_ecoflow_measurements_device_sn ON ecoflow_measurements(device_sn);
CREATE INDEX IF NOT EXISTS idx_ecoflow_measurements_device_ts ON ecoflow_measurements(device_sn, ts DESC);
