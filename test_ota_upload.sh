#!/bin/bash
# Test OTA firmware upload locally

set -e

# Configuration
OTA_URL="${OTA_SERVICE_URL:-http://37.27.192.107:8080}"
API_KEY="${OTA_API_KEY}"
FIRMWARE_PATH="$1"

if [ -z "$FIRMWARE_PATH" ]; then
    echo "Usage: $0 <firmware_file.bin>"
    exit 1
fi

if [ ! -f "$FIRMWARE_PATH" ]; then
    echo "Error: Firmware file not found: $FIRMWARE_PATH"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "Error: OTA_API_KEY environment variable not set"
    exit 1
fi

# Build version string
VERSION="test-$(date +%Y%m%d-%H%M%S)"
DEVICE_MODEL="lilygo-t-display-s3"
RELEASE_NOTES="Manual test upload"

echo "Testing firmware upload..."
echo "URL: $OTA_URL/api/admin/firmware/upload"
echo "Version: $VERSION"
echo "Device: $DEVICE_MODEL"
echo "File: $FIRMWARE_PATH"
echo "Size: $(stat -f%z "$FIRMWARE_PATH") bytes"
echo ""

# Test 1: Basic curl with verbose output
echo "=== Test 1: Verbose curl ==="
curl -v \
  -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Expect:" \
  -F "file=@$FIRMWARE_PATH" \
  "$OTA_URL/api/admin/firmware/upload?version=$VERSION&device_model=$DEVICE_MODEL&is_signed=false&release_notes=$(printf '%s' "$RELEASE_NOTES" | jq -sRr @uri)"

echo ""
echo ""

# Test 2: Check if we can at least reach the server
echo "=== Test 2: Health check ==="
curl -v "$OTA_URL/api/device/health" || echo "Health endpoint not available"

echo ""
echo "Done!"
