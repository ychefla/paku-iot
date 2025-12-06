-- Enhanced EcoFlow schema with comprehensive data fields
-- This adds additional columns to capture more detailed metrics

-- Add enhanced columns to ecoflow_measurements table
ALTER TABLE IF EXISTS ecoflow_measurements 
  ADD COLUMN IF NOT EXISTS bms_voltage_mv INTEGER,
  ADD COLUMN IF NOT EXISTS bms_amp_ma INTEGER,
  ADD COLUMN IF NOT EXISTS bms_temp_c INTEGER,
  ADD COLUMN IF NOT EXISTS bms_cycles INTEGER,
  ADD COLUMN IF NOT EXISTS bms_soh_percent INTEGER,
  ADD COLUMN IF NOT EXISTS inv_ac_in_volts_mv INTEGER,
  ADD COLUMN IF NOT EXISTS inv_ac_out_volts_mv INTEGER,
  ADD COLUMN IF NOT EXISTS inv_ac_freq_hz INTEGER,
  ADD COLUMN IF NOT EXISTS inv_temp_c INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_in_volts_mv INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_in_amps_ma INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_out_volts_mv INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_out_amps_ma INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_temp_c INTEGER,
  ADD COLUMN IF NOT EXISTS car_out_volts_mv INTEGER,
  ADD COLUMN IF NOT EXISTS car_out_amps_ma INTEGER,
  ADD COLUMN IF NOT EXISTS wifi_rssi INTEGER,
  ADD COLUMN IF NOT EXISTS data_staleness_sec INTEGER;

-- Create index for faster queries on timestamp and device
CREATE INDEX IF NOT EXISTS idx_ecoflow_ts_device ON ecoflow_measurements(device_sn, ts DESC);

-- Create a materialized view for latest values with staleness indicator
CREATE MATERIALIZED VIEW IF NOT EXISTS ecoflow_latest AS
SELECT DISTINCT ON (device_sn)
  device_sn,
  ts,
  soc_percent,
  remain_time_min,
  watts_in_sum,
  watts_out_sum,
  ac_out_watts,
  dc_out_watts,
  typec_out_watts,
  usb_out_watts,
  pv_in_watts,
  bms_voltage_mv,
  bms_amp_ma,
  bms_temp_c,
  bms_cycles,
  bms_soh_percent,
  inv_ac_in_volts_mv,
  inv_ac_out_volts_mv,
  inv_ac_freq_hz,
  inv_temp_c,
  mppt_in_volts_mv,
  mppt_in_amps_ma,
  mppt_out_volts_mv,
  mppt_out_amps_ma,
  mppt_temp_c,
  car_out_volts_mv,
  car_out_amps_ma,
  wifi_rssi,
  EXTRACT(EPOCH FROM (NOW() - ts))::INTEGER as staleness_sec,
  raw_data
FROM ecoflow_measurements
ORDER BY device_sn, ts DESC;

-- Create unique index for concurrent refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_ecoflow_latest_device ON ecoflow_latest(device_sn);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_ecoflow_latest()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY ecoflow_latest;
END;
$$ LANGUAGE plpgsql;

-- Add comment explaining the schema
COMMENT ON TABLE ecoflow_measurements IS 
'Stores EcoFlow power station telemetry data. Updated every few seconds via MQTT. 
raw_data contains complete JSON payload for all available fields.';

COMMENT ON COLUMN ecoflow_measurements.raw_data IS 
'Complete JSON payload from EcoFlow MQTT broker containing all available parameters.
Use jsonb_pretty(raw_data) to view formatted data.';

COMMENT ON MATERIALIZED VIEW ecoflow_latest IS
'Latest measurement for each device with staleness indicator.
Refresh periodically with: SELECT refresh_ecoflow_latest();';
