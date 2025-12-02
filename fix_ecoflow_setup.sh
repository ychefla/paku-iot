#!/bin/bash
# Fix EcoFlow setup on production server
# This script:
# 1. Creates the ecoflow_measurements table if it doesn't exist
# 2. Checks if ecoflow collector is running
# 3. Starts it with the ecoflow profile if not running

set -e

echo "=== EcoFlow Setup Fix Script ==="
echo ""

# Check if we're in the right directory
if [ ! -f "compose/stack.prod.yaml" ]; then
    echo "Error: Please run this script from /home/paku/paku-iot directory"
    exit 1
fi

# Step 1: Create ecoflow_measurements table
echo "Step 1: Creating ecoflow_measurements table..."
docker exec paku_postgres psql -U paku -d paku << 'PGSQL'
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

CREATE INDEX IF NOT EXISTS idx_ecoflow_measurements_ts ON ecoflow_measurements(ts);
CREATE INDEX IF NOT EXISTS idx_ecoflow_measurements_device_sn ON ecoflow_measurements(device_sn);
CREATE INDEX IF NOT EXISTS idx_ecoflow_measurements_device_ts ON ecoflow_measurements(device_sn, ts DESC);

COMMENT ON TABLE ecoflow_measurements IS 'EcoFlow power station telemetry data';
COMMENT ON COLUMN ecoflow_measurements.device_sn IS 'EcoFlow device serial number';
COMMENT ON COLUMN ecoflow_measurements.ts IS 'Measurement timestamp';
COMMENT ON COLUMN ecoflow_measurements.soc_percent IS 'State of charge (battery percentage)';
COMMENT ON COLUMN ecoflow_measurements.remain_time_min IS 'Estimated remaining runtime in minutes';
COMMENT ON COLUMN ecoflow_measurements.watts_in_sum IS 'Total input power in watts';
COMMENT ON COLUMN ecoflow_measurements.watts_out_sum IS 'Total output power in watts';
COMMENT ON COLUMN ecoflow_measurements.raw_data IS 'Full JSON payload from EcoFlow device';
PGSQL

echo "✓ Table created successfully"
echo ""

# Step 2: Check if EcoFlow credentials are set
echo "Step 2: Checking EcoFlow credentials..."
if grep -q "ECOFLOW_ACCESS_KEY=.\+" compose/.env && grep -q "ECOFLOW_SECRET_KEY=.\+" compose/.env; then
    echo "✓ EcoFlow credentials found in .env"
    
    # Step 3: Check if ecoflow collector is running
    echo ""
    echo "Step 3: Checking EcoFlow collector status..."
    if docker ps | grep -q paku_ecoflow_collector; then
        echo "✓ EcoFlow collector is running"
        echo ""
        echo "Checking recent logs:"
        docker logs --tail 10 paku_ecoflow_collector
    else
        echo "✗ EcoFlow collector is NOT running"
        echo ""
        echo "Step 4: Starting EcoFlow collector..."
        docker compose --profile ecoflow -f compose/stack.prod.yaml up -d ecoflow-collector
        echo ""
        echo "Waiting for collector to start..."
        sleep 5
        echo ""
        echo "Checking logs:"
        docker logs --tail 20 paku_ecoflow_collector
    fi
else
    echo "✗ EcoFlow credentials not found in .env"
    echo ""
    echo "Please set these in compose/.env:"
    echo "  ECOFLOW_ACCESS_KEY=your_access_key"
    echo "  ECOFLOW_SECRET_KEY=your_secret_key"
    echo "  ECOFLOW_DEVICE_SN=your_device_sn (optional)"
    exit 1
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To verify data collection:"
echo "  docker exec paku_postgres psql -U paku -d paku -c 'SELECT COUNT(*) FROM ecoflow_measurements;'"
echo ""
echo "To check collector logs:"
echo "  docker logs -f paku_ecoflow_collector"
