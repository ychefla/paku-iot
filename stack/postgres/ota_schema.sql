-- OTA (Over-The-Air) Update Schema
-- Supports firmware hosting, rollout orchestration, and device update tracking

-- Firmware releases table
-- Stores metadata for firmware artifacts
CREATE TABLE IF NOT EXISTS firmware_releases (
    id BIGSERIAL PRIMARY KEY,
    version TEXT NOT NULL UNIQUE,
    device_model TEXT NOT NULL,
    min_version TEXT,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    changelog TEXT,
    release_notes TEXT,
    is_signed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT,
    metadata JSONB
);

-- Index for querying latest firmware by model
CREATE INDEX IF NOT EXISTS idx_firmware_releases_model_version ON firmware_releases(device_model, version DESC);
CREATE INDEX IF NOT EXISTS idx_firmware_releases_created ON firmware_releases(created_at DESC);

COMMENT ON TABLE firmware_releases IS 'Firmware artifact metadata and version information';
COMMENT ON COLUMN firmware_releases.version IS 'Semantic version (e.g., 1.2.3)';
COMMENT ON COLUMN firmware_releases.device_model IS 'Target device model identifier';
COMMENT ON COLUMN firmware_releases.min_version IS 'Minimum firmware version required for upgrade';
COMMENT ON COLUMN firmware_releases.file_path IS 'Path to firmware binary on server';
COMMENT ON COLUMN firmware_releases.checksum_sha256 IS 'SHA256 checksum for integrity verification';
COMMENT ON COLUMN firmware_releases.is_signed IS 'Whether firmware is cryptographically signed';

-- Device registry for OTA tracking
CREATE TABLE IF NOT EXISTS devices (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL UNIQUE,
    device_model TEXT NOT NULL,
    current_firmware_version TEXT,
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_model ON devices(device_model);

COMMENT ON TABLE devices IS 'Device registry for OTA update tracking';
COMMENT ON COLUMN devices.device_id IS 'Unique device identifier (e.g., MAC address, serial number)';

-- Device update status tracking
CREATE TABLE IF NOT EXISTS device_update_status (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    firmware_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'downloading', 'downloaded', 'installing', 'success', 'failed', 'rolled_back')),
    error_message TEXT,
    progress_percent INTEGER CHECK (progress_percent >= 0 AND progress_percent <= 100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    CONSTRAINT fk_device FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_device_update_status_device ON device_update_status(device_id, reported_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_update_status_status ON device_update_status(status);
CREATE INDEX IF NOT EXISTS idx_device_update_status_version ON device_update_status(firmware_version);

COMMENT ON TABLE device_update_status IS 'Device firmware update status and progress tracking';
COMMENT ON COLUMN device_update_status.status IS 'Current update status';
COMMENT ON COLUMN device_update_status.progress_percent IS 'Update progress (0-100)';

-- Rollout configurations
-- Controls which devices receive which firmware versions
CREATE TABLE IF NOT EXISTS rollout_configurations (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    firmware_version TEXT NOT NULL,
    device_model TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('all', 'group', 'canary', 'specific')),
    target_filter JSONB,
    rollout_percentage INTEGER CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT,
    metadata JSONB,
    CONSTRAINT fk_firmware FOREIGN KEY (firmware_version) REFERENCES firmware_releases(version) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rollout_configurations_active ON rollout_configurations(is_active);
CREATE INDEX IF NOT EXISTS idx_rollout_configurations_model ON rollout_configurations(device_model);

COMMENT ON TABLE rollout_configurations IS 'Firmware rollout orchestration and targeting rules';
COMMENT ON COLUMN rollout_configurations.target_type IS 'Rollout targeting strategy';
COMMENT ON COLUMN rollout_configurations.target_filter IS 'JSON filter for device selection (device IDs, groups, etc.)';
COMMENT ON COLUMN rollout_configurations.rollout_percentage IS 'Percentage of target devices to update (for canary/phased rollouts)';

-- Update events log
-- Audit trail for all OTA-related events
CREATE TABLE IF NOT EXISTS ota_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (event_type IN ('firmware_uploaded', 'rollout_created', 'rollout_updated', 'update_started', 'update_completed', 'update_failed', 'rollback_initiated')),
    device_id TEXT,
    firmware_version TEXT,
    rollout_id BIGINT,
    event_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_ota_events_type ON ota_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ota_events_device ON ota_events(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ota_events_version ON ota_events(firmware_version, created_at DESC);

COMMENT ON TABLE ota_events IS 'Audit log for OTA update events and activities';
