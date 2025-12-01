-- Migration: Update measurements table to support new topic hierarchy
-- From: sensor_id + old schema
-- To: site_id, system, device_id, location + flexible metrics

BEGIN;

-- Create new measurements table with updated schema
CREATE TABLE measurements_new (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT NOT NULL,
    system TEXT NOT NULL,
    device_id TEXT NOT NULL,
    location TEXT,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metrics JSONB NOT NULL
);

-- Create indexes for efficient querying
CREATE INDEX idx_measurements_new_site_system_device ON measurements_new(site_id, system, device_id);
CREATE INDEX idx_measurements_new_ts ON measurements_new(ts);
CREATE INDEX idx_measurements_new_site_system_device_ts ON measurements_new(site_id, system, device_id, ts DESC);
CREATE INDEX idx_measurements_new_metrics ON measurements_new USING GIN(metrics);

-- Migrate old data (map old sensor_id to new structure)
-- Old format was just sensor_id (like "ruuvi_cafe01")
-- New format: site_id=paku, system=sensors, device_id=sensor_id
INSERT INTO measurements_new (site_id, system, device_id, location, ts, metrics)
SELECT 
    'paku' as site_id,
    'sensors' as system,
    sensor_id as device_id,
    NULL as location,
    ts,
    jsonb_strip_nulls(jsonb_build_object(
        'temperature_c', temperature_c,
        'humidity_percent', humidity_percent,
        'pressure_hpa', pressure_hpa,
        'battery_mv', battery_mv,
        'acceleration_x_mg', acceleration_x_mg,
        'acceleration_y_mg', acceleration_y_mg,
        'acceleration_z_mg', acceleration_z_mg,
        'acceleration_total_mg', acceleration_total_mg,
        'tx_power_dbm', tx_power_dbm,
        'movement_counter', movement_counter,
        'measurement_sequence', measurement_sequence,
        'mac', mac
    )) as metrics
FROM measurements
ORDER BY ts;

-- Drop old table and rename new one
DROP TABLE measurements;
ALTER TABLE measurements_new RENAME TO measurements;

COMMIT;
