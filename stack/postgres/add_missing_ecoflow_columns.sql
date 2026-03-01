-- Add missing columns to ecoflow_measurements table
-- These columns are referenced in the collector but missing from the schema

-- USB output columns (individual ports)
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS usb1_watts INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS usb2_watts INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS qcusb1_watts INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS qcusb2_watts INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS typec1_watts INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS typec2_watts INTEGER;

-- Type-C temperature sensors
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS typec1_temp INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS typec2_temp INTEGER;

-- EMS (Energy Management System) configuration
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS ems_min_dsg_soc INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS ems_max_charge_soc INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS ems_min_open_oil_eb_soc INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS ems_max_close_oil_eb_soc INTEGER;

-- Inverter configuration
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_cfg_ac_enabled INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_cfg_standby_min INTEGER;

-- MPPT car charger status and configuration
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS mppt_car_state INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS mppt_cfg_dc_chg_current INTEGER;

-- Panel display settings
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_beep_state INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_lcd_off_sec INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_lcd_brightness INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_standby_mode INTEGER;

-- Temperature sensors (previously only stored in raw_data JSONB)
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_out_temp NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_temp NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_max_cell_temp NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_min_cell_temp NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS mppt_temp NUMERIC;

-- Power/energy fields (previously only stored in raw_data JSONB flat dot-keys)
-- inv.inputWatts - AC input power (ac_out_watts already covers inv.outputWatts)
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_input_watts NUMERIC;
-- inv voltage/current fields (keys: inv.acInVol, inv.invOutVol, inv.acInAmp, inv.invOutAmp)
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_ac_in_vol NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_out_vol NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_ac_in_amp NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS inv_out_amp NUMERIC;
-- BMS fields (keys: bmsMaster.amp, bmsMaster.vol, etc.)
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_amp NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_vol NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_min_cell_vol NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_max_cell_vol NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_remain_cap NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_full_cap NUMERIC;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS bms_cycles INTEGER;

-- WiFi signal strength
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS wifi_rssi INTEGER;

-- Device information
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_model VARCHAR(50);
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_sys_ver VARCHAR(50);
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_wifi_ver VARCHAR(50);

-- Usage time tracking (in seconds)
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_car_used_time INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_inv_used_time INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_mppt_used_time INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_usb_used_time INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_typec_used_time INTEGER;
ALTER TABLE ecoflow_measurements ADD COLUMN IF NOT EXISTS pd_dc_in_used_time INTEGER;

-- Create indexes for commonly queried fields
CREATE INDEX IF NOT EXISTS idx_ecoflow_ems_settings ON ecoflow_measurements(ems_min_dsg_soc, ems_max_charge_soc);
CREATE INDEX IF NOT EXISTS idx_ecoflow_inv_config ON ecoflow_measurements(inv_cfg_ac_enabled);
CREATE INDEX IF NOT EXISTS idx_ecoflow_mppt_car ON ecoflow_measurements(mppt_car_state);

-- Verify columns were added
SELECT COUNT(*) as column_count 
FROM information_schema.columns 
WHERE table_name = 'ecoflow_measurements';
