-- Comprehensive EcoFlow schema update
-- Adds ALL available fields from Delta Pro parsing

BEGIN;

-- Add all missing columns to support comprehensive data collection
ALTER TABLE IF EXISTS ecoflow_measurements 
  -- Individual USB port details
  ADD COLUMN IF NOT EXISTS usb1_watts INTEGER,
  ADD COLUMN IF NOT EXISTS usb2_watts INTEGER,
  ADD COLUMN IF NOT EXISTS qcusb1_watts INTEGER,
  ADD COLUMN IF NOT EXISTS qcusb2_watts INTEGER,
  ADD COLUMN IF NOT EXISTS typec1_watts INTEGER,
  ADD COLUMN IF NOT EXISTS typec2_watts INTEGER,
  ADD COLUMN IF NOT EXISTS typec1_temp INTEGER,
  ADD COLUMN IF NOT EXISTS typec2_temp INTEGER,
  
  -- Detailed input sources
  ADD COLUMN IF NOT EXISTS chg_sun_power INTEGER,
  ADD COLUMN IF NOT EXISTS chg_power_ac INTEGER,
  ADD COLUMN IF NOT EXISTS chg_power_dc INTEGER,
  ADD COLUMN IF NOT EXISTS car_watts INTEGER,
  
  -- Extended BMS data
  ADD COLUMN IF NOT EXISTS bms_min_cell_temp_c INTEGER,
  ADD COLUMN IF NOT EXISTS bms_max_cell_temp_c INTEGER,
  ADD COLUMN IF NOT EXISTS bms_min_mos_temp_c INTEGER,
  ADD COLUMN IF NOT EXISTS bms_max_mos_temp_c INTEGER,
  ADD COLUMN IF NOT EXISTS bms_real_soh INTEGER,
  ADD COLUMN IF NOT EXISTS bms_remain_cap INTEGER,
  ADD COLUMN IF NOT EXISTS bms_full_cap INTEGER,
  ADD COLUMN IF NOT EXISTS bms_design_cap INTEGER,
  ADD COLUMN IF NOT EXISTS bms_min_cell_vol_mv INTEGER,
  ADD COLUMN IF NOT EXISTS bms_max_cell_vol_mv INTEGER,
  ADD COLUMN IF NOT EXISTS bms_max_vol_diff_mv INTEGER,
  
  -- EMS (Energy Management System) settings
  ADD COLUMN IF NOT EXISTS ems_min_dsg_soc INTEGER,
  ADD COLUMN IF NOT EXISTS ems_max_charge_soc INTEGER,
  ADD COLUMN IF NOT EXISTS ems_min_open_oil_eb_soc INTEGER,
  ADD COLUMN IF NOT EXISTS ems_max_close_oil_eb_soc INTEGER,
  
  -- Extended Inverter data
  ADD COLUMN IF NOT EXISTS inv_cfg_ac_enabled INTEGER,
  ADD COLUMN IF NOT EXISTS inv_cfg_standby_min INTEGER,
  
  -- Extended MPPT data
  ADD COLUMN IF NOT EXISTS mppt_car_out_volts_mv INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_car_out_amps_ma INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_car_state INTEGER,
  ADD COLUMN IF NOT EXISTS mppt_cfg_dc_chg_current INTEGER,
  
  -- PD (Power Distribution) settings
  ADD COLUMN IF NOT EXISTS pd_beep_state INTEGER,
  ADD COLUMN IF NOT EXISTS pd_lcd_off_sec INTEGER,
  ADD COLUMN IF NOT EXISTS pd_lcd_brightness INTEGER,
  ADD COLUMN IF NOT EXISTS pd_standby_mode INTEGER,
  ADD COLUMN IF NOT EXISTS pd_model TEXT,
  ADD COLUMN IF NOT EXISTS pd_sys_ver TEXT,
  ADD COLUMN IF NOT EXISTS pd_wifi_ver TEXT,
  
  -- Usage time counters (in seconds)
  ADD COLUMN IF NOT EXISTS pd_car_used_time INTEGER,
  ADD COLUMN IF NOT EXISTS pd_inv_used_time INTEGER,
  ADD COLUMN IF NOT EXISTS pd_mppt_used_time INTEGER,
  ADD COLUMN IF NOT EXISTS pd_usb_used_time INTEGER,
  ADD COLUMN IF NOT EXISTS pd_typec_used_time INTEGER,
  ADD COLUMN IF NOT EXISTS pd_dc_in_used_time INTEGER;

-- Add indexes for commonly queried fields
CREATE INDEX IF NOT EXISTS idx_ecoflow_soc ON ecoflow_measurements(device_sn, soc_percent) WHERE soc_percent IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ecoflow_power ON ecoflow_measurements(device_sn, watts_out_sum) WHERE watts_out_sum IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ecoflow_temp ON ecoflow_measurements(device_sn, bms_temp_c) WHERE bms_temp_c IS NOT NULL;

-- Drop and recreate materialized view with all new fields
DROP MATERIALIZED VIEW IF EXISTS ecoflow_latest CASCADE;

CREATE MATERIALIZED VIEW ecoflow_latest AS
SELECT DISTINCT ON (device_sn)
  device_sn,
  ts,
  EXTRACT(EPOCH FROM (NOW() - ts))::INTEGER as staleness_sec,
  -- Core metrics
  soc_percent,
  remain_time_min,
  watts_in_sum,
  watts_out_sum,
  -- Output channels
  ac_out_watts,
  dc_out_watts,
  typec_out_watts,
  usb_out_watts,
  -- Individual ports
  usb1_watts,
  usb2_watts,
  qcusb1_watts,
  qcusb2_watts,
  typec1_watts,
  typec2_watts,
  typec1_temp,
  typec2_temp,
  -- Input sources
  pv_in_watts,
  chg_sun_power,
  chg_power_ac,
  chg_power_dc,
  car_watts,
  -- BMS data
  bms_voltage_mv,
  bms_amp_ma,
  bms_temp_c,
  bms_min_cell_temp_c,
  bms_max_cell_temp_c,
  bms_min_mos_temp_c,
  bms_max_mos_temp_c,
  bms_cycles,
  bms_soh_percent,
  bms_real_soh,
  bms_remain_cap,
  bms_full_cap,
  bms_design_cap,
  bms_min_cell_vol_mv,
  bms_max_cell_vol_mv,
  bms_max_vol_diff_mv,
  -- EMS settings
  ems_min_dsg_soc,
  ems_max_charge_soc,
  ems_min_open_oil_eb_soc,
  ems_max_close_oil_eb_soc,
  -- Inverter data
  inv_ac_in_volts_mv,
  inv_ac_out_volts_mv,
  inv_ac_freq_hz,
  inv_temp_c,
  inv_cfg_ac_enabled,
  inv_cfg_standby_min,
  -- MPPT data
  mppt_in_volts_mv,
  mppt_in_amps_ma,
  mppt_out_volts_mv,
  mppt_out_amps_ma,
  mppt_temp_c,
  mppt_car_out_volts_mv,
  mppt_car_out_amps_ma,
  mppt_car_state,
  mppt_cfg_dc_chg_current,
  -- PD settings
  pd_beep_state,
  pd_lcd_off_sec,
  pd_lcd_brightness,
  pd_standby_mode,
  wifi_rssi,
  pd_model,
  pd_sys_ver,
  pd_wifi_ver,
  -- Usage counters
  pd_car_used_time,
  pd_inv_used_time,
  pd_mppt_used_time,
  pd_usb_used_time,
  pd_typec_used_time,
  pd_dc_in_used_time,
  -- Raw data
  raw_data
FROM ecoflow_measurements
ORDER BY device_sn, ts DESC;

CREATE UNIQUE INDEX idx_ecoflow_latest_device ON ecoflow_latest(device_sn);

COMMIT;

-- Display schema info
SELECT 'Schema updated successfully. Total columns: ' || COUNT(*) 
FROM information_schema.columns 
WHERE table_name = 'ecoflow_measurements';
