#!/bin/bash
# Script to check EcoFlow collector status and troubleshoot issues

set -e

COMPOSE_FILE="compose/stack.prod.yaml"

echo "=== EcoFlow Collector Status Check ==="
echo ""

# Check if EcoFlow collector is running
echo "1. Container Status:"
if docker ps --format '{{.Names}}' | grep -q paku_ecoflow_collector; then
    echo "✓ EcoFlow collector is running"
    docker ps --filter name=paku_ecoflow_collector --format 'table {{.Names}}\t{{.Status}}\t{{.State}}'
else
    echo "✗ EcoFlow collector is NOT running"
    echo ""
    echo "To start it, ensure credentials are set and run:"
    echo "  cd /home/paku/paku-iot"
    echo "  docker compose -f $COMPOSE_FILE --profile ecoflow up -d ecoflow-collector"
    exit 1
fi

echo ""
echo "2. Recent Logs (last 30 lines):"
docker logs --tail 30 paku_ecoflow_collector

echo ""
echo "3. Database Status:"
docker exec paku_postgres psql -U paku -d paku -c "
SELECT 
    COUNT(*) as total_records,
    MIN(ts) as first_measurement,
    MAX(ts) as last_measurement,
    COUNT(DISTINCT device_sn) as unique_devices
FROM ecoflow_measurements;
" || echo "✗ Failed to query database"

echo ""
echo "4. Environment Variables (masked):"
docker exec paku_ecoflow_collector sh -c '
echo "ECOFLOW_ACCESS_KEY: ${ECOFLOW_ACCESS_KEY:0:10}***"
echo "ECOFLOW_SECRET_KEY: ${ECOFLOW_SECRET_KEY:0:10}***"
echo "ECOFLOW_DEVICE_SN: ${ECOFLOW_DEVICE_SN}"
echo "ECOFLOW_API_URL: ${ECOFLOW_API_URL}"
'

echo ""
echo "5. Recent measurements (if any):"
docker exec paku_postgres psql -U paku -d paku -c "
SELECT 
    ts,
    device_sn,
    soc_percent,
    watts_in_sum,
    watts_out_sum
FROM ecoflow_measurements
ORDER BY ts DESC
LIMIT 5;
" || echo "No measurements found"

echo ""
echo "=== Check Complete ==="
echo ""
echo "If no data is appearing:"
echo "  1. Check that credentials are correct in .env file"
echo "  2. Verify device_sn matches your EcoFlow device"
echo "  3. Ensure device is online and sending data"
echo "  4. Check logs for MQTT connection and subscription details"
echo "  5. Try restarting the collector: docker compose -f $COMPOSE_FILE restart ecoflow-collector"
