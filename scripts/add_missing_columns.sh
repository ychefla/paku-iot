#!/bin/bash

# Script to add missing columns to ecoflow_measurements table
# Run this on the server where Docker is running

set -e

echo "Adding missing columns to ecoflow_measurements table..."

# Apply the migration
docker exec -i paku_postgres psql -U paku -d paku <<'EOF'
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
EOF

echo ""
echo "Migration complete! Column count shown above."
echo ""
echo "Restarting ecoflow collector to clear any cached errors..."
docker restart paku_ecoflow_collector

echo ""
echo "Done! Check the logs with: docker logs -f paku_ecoflow_collector"
