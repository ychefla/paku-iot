-- Edge Devices Configuration and Status Tables
-- Supports MQTT topics: {site_id}/edge/{device_id}/status and {site_id}/edge/{device_id}/config

-- Table for edge device configurations
CREATE TABLE IF NOT EXISTS edge_device_configs (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    config JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(site_id, device_id)
);

-- Table for edge device status updates
CREATE TABLE IF NOT EXISTS edge_device_status (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    status JSONB NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for edge device tables
CREATE INDEX IF NOT EXISTS idx_edge_configs_site_device ON edge_device_configs(site_id, device_id);
CREATE INDEX IF NOT EXISTS idx_edge_status_site_device_ts ON edge_device_status(site_id, device_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_edge_status_ts ON edge_device_status(ts DESC);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_edge_configs_config ON edge_device_configs USING GIN (config);
CREATE INDEX IF NOT EXISTS idx_edge_status_status ON edge_device_status USING GIN (status);

-- Comments for documentation
COMMENT ON TABLE edge_device_configs IS 'Edge device configuration storage (latest config per device)';
COMMENT ON COLUMN edge_device_configs.site_id IS 'Installation identifier';
COMMENT ON COLUMN edge_device_configs.device_id IS 'Edge device identifier (e.g., ESP32-BLE, ESP8266-WIRED)';
COMMENT ON COLUMN edge_device_configs.config IS 'Device configuration as JSON (timing, sensors, power settings)';
COMMENT ON COLUMN edge_device_configs.updated_at IS 'Last configuration update timestamp';

COMMENT ON TABLE edge_device_status IS 'Edge device status updates (time-series)';
COMMENT ON COLUMN edge_device_status.site_id IS 'Installation identifier';
COMMENT ON COLUMN edge_device_status.device_id IS 'Edge device identifier';
COMMENT ON COLUMN edge_device_status.status IS 'Device status as JSON (state, uptime, wifi, mqtt, etc.)';
COMMENT ON COLUMN edge_device_status.ts IS 'Status timestamp from device';
COMMENT ON COLUMN edge_device_status.created_at IS 'Record creation timestamp in database';
