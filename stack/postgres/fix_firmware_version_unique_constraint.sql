-- Migrate firmware_releases unique constraint from version-only to (version, device_model).
-- Allows the same semver to be uploaded for different device models.
ALTER TABLE firmware_releases DROP CONSTRAINT IF EXISTS firmware_releases_version_key;
CREATE UNIQUE INDEX IF NOT EXISTS firmware_releases_version_model_key ON firmware_releases(version, device_model);
