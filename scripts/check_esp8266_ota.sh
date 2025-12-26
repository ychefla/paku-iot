#!/bin/bash
# Quick diagnostic script for ESP8266 OTA issues

set -e

OTA_URL="${OTA_URL:-http://37.27.192.107:8080}"
OTA_API_KEY="${OTA_API_KEY:-your_api_key}"
DEVICE_MODEL="esp8266-wired-sensors"

echo "=== ESP8266 OTA Diagnostics ==="
echo ""

echo "1. Checking OTA service for ESP8266 devices..."
curl -s -H "X-API-Key: ${OTA_API_KEY}" \
  "${OTA_URL}/api/admin/devices?device_model=${DEVICE_MODEL}&limit=10" \
  | jq '.'

echo ""
echo "2. Devices found:"
curl -s -H "X-API-Key: ${OTA_API_KEY}" \
  "${OTA_URL}/api/admin/devices?device_model=${DEVICE_MODEL}&limit=10" \
  | jq -r '.devices[]? | "\(.device_id) - Last seen: \(.last_seen)"'

echo ""
echo "3. To manually send OTA to a specific ESP8266:"
echo "   DEVICE_ID=\"ESP8266-XXXXXXXX\""
echo "   mosquitto_pub -h 37.27.192.107 -p 1883 \\"
echo "     -t \"paku/devices/\${DEVICE_ID}/cmd/ota\" \\"
echo "     -m '{\"url\":\"YOUR_FIRMWARE_URL\",\"checksum\":\"YOUR_SHA256\",\"version\":\"YOUR_VERSION\"}'"

echo ""
echo "4. Monitor ESP8266 OTA responses:"
echo "   mosquitto_sub -h 37.27.192.107 -p 1883 -v \\"
echo "     -t 'paku/devices/ESP8266-+/ota/#'"
