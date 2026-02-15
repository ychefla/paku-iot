#!/bin/bash
# extract_mqtt_ca.sh — Extract the MQTT CA certificate from the Mosquitto Docker image
# and format it as a C string for embedding in secrets.h
#
# Usage:
#   ./scripts/extract_mqtt_ca.sh
#   ./scripts/extract_mqtt_ca.sh paku_mosquitto   # custom container/image name

set -e

IMAGE="${1:-paku_mosquitto}"

echo "Extracting CA cert from $IMAGE..."
CA_PEM=$(docker run --rm "$IMAGE" cat /mosquitto/certs/ca.crt 2>/dev/null || \
         docker cp "$IMAGE":/mosquitto/certs/ca.crt /dev/stdout 2>/dev/null)

if [ -z "$CA_PEM" ]; then
    echo "ERROR: Could not extract CA cert. Is the image/container running?" >&2
    exit 1
fi

echo ""
echo "// Paste this into your secrets.h (MQTT TLS CA certificate)"
echo "#define MQTT_CA_CERT \\"
echo "$CA_PEM" | while IFS= read -r line; do
    echo "\"${line}\\n\" \\"
done | sed '$ s/ \\$//'
echo ""
echo "// Then set MQTT_PORT to 8883 and fill in MQTT_USER / MQTT_PASSWORD"
