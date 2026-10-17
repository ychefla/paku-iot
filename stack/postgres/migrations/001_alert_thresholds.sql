-- Alert thresholds and per-sensor status for Grafana alerting.
-- Idempotent: safe to run on every deploy (see deploy.yaml / 99-migrations.sh).

-- Thresholds per site ('*' = site default) with optional per-device overrides.
-- NULL means "inherit" for device rows and "disabled" for site defaults.
-- Grafana alert rules read these via alert_sensor_status, so thresholds can be
-- tuned (later from Home Assistant) without touching the rules.
CREATE TABLE IF NOT EXISTS alert_thresholds (
    site_id TEXT NOT NULL,
    device_id TEXT NOT NULL DEFAULT '*',
    temp_min_c DOUBLE PRECISION,
    humidity_max_percent DOUBLE PRECISION,
    battery_min_v DOUBLE PRECISION,
    nodata_minutes INTEGER,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (site_id, device_id)
);

COMMENT ON TABLE alert_thresholds IS 'Alert limits per site (device_id = ''*'') with optional per-device overrides';
COMMENT ON COLUMN alert_thresholds.temp_min_c IS 'Alert when 60 min average temperature is below this';
COMMENT ON COLUMN alert_thresholds.humidity_max_percent IS 'Alert when 60 min average relative humidity is above this';
COMMENT ON COLUMN alert_thresholds.battery_min_v IS 'Alert when 24 h average sensor battery voltage is below this';
COMMENT ON COLUMN alert_thresholds.nodata_minutes IS 'Alert when a sensor has not reported for this many minutes';

-- Defaults. ON CONFLICT DO NOTHING keeps values tuned later.
INSERT INTO alert_thresholds (site_id, device_id, temp_min_c, humidity_max_percent, battery_min_v, nodata_minutes)
VALUES
    ('honkaranta', '*', 5, 80, 2.5, 120),
    ('paku',       '*', 0, 90, 2.5, 360)
ON CONFLICT (site_id, device_id) DO NOTHING;

-- Latest readings + effective thresholds for every sensor seen in 14 days.
-- Ruuvi firmware reports battery in volts under "battery_mv"; values above
-- 100 are treated as real millivolts.
CREATE OR REPLACE VIEW alert_sensor_status AS
WITH recent AS (
    SELECT
        site_id,
        device_id,
        max(ts) AS last_seen,
        -- 60 min windows: some tags report only every ~20 min, and a
        -- shorter window would make alerts flap resolved/firing.
        avg((metrics->>'temperature_c')::float8)
            FILTER (WHERE ts > now() - interval '60 minutes') AS temp_c,
        avg((metrics->>'humidity_percent')::float8)
            FILTER (WHERE ts > now() - interval '60 minutes') AS humidity_percent,
        avg(CASE WHEN (metrics->>'battery_mv')::float8 > 100
                 THEN (metrics->>'battery_mv')::float8 / 1000
                 ELSE (metrics->>'battery_mv')::float8 END)
            FILTER (WHERE ts > now() - interval '24 hours') AS battery_v
    FROM measurements
    WHERE system = 'sensors'
      AND ts > now() - interval '14 days'
    GROUP BY site_id, device_id
)
SELECT
    r.site_id,
    r.device_id,
    r.last_seen,
    extract(epoch FROM now() - r.last_seen) / 60 AS minutes_since_seen,
    r.temp_c,
    r.humidity_percent,
    r.battery_v,
    coalesce(d.temp_min_c, s.temp_min_c) AS temp_min_c,
    coalesce(d.humidity_max_percent, s.humidity_max_percent) AS humidity_max_percent,
    coalesce(d.battery_min_v, s.battery_min_v) AS battery_min_v,
    coalesce(d.nodata_minutes, s.nodata_minutes) AS nodata_minutes
FROM recent r
LEFT JOIN alert_thresholds s ON s.site_id = r.site_id AND s.device_id = '*'
LEFT JOIN alert_thresholds d ON d.site_id = r.site_id AND d.device_id = r.device_id;
