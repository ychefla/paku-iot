#!/bin/sh
# entrypoint.sh — Mosquitto entrypoint that ensures certs + password file exist.
#
# Certs are stored in /mosquitto/certs (a Docker volume) so they persist
# across container rebuilds. Only generated on first run.
#
# Password file is always regenerated from environment variables so that
# credential changes take effect on restart without rebuilding.
set -e

CERT_DIR="/mosquitto/certs"
CN="${MQTT_CN:-paku-mqtt}"
DAYS=3650  # 10 years

# --- Generate TLS certs if they don't exist (or if forced) ---
# Set FORCE_REGEN_CERTS=1 to regenerate (e.g. after CN change).
# After regenerating, you must update MQTT_CA_CERT in the firmware secrets.h.
if [ "${FORCE_REGEN_CERTS:-0}" = "1" ] || [ ! -f "$CERT_DIR/ca.crt" ] || [ ! -f "$CERT_DIR/server.crt" ]; then
  echo "=== Generating TLS certificates (CN=$CN) ==="
  mkdir -p "$CERT_DIR"

  # CA
  openssl req -new -x509 -days "$DAYS" -nodes \
    -subj "/CN=paku-mqtt-ca" \
    -keyout "$CERT_DIR/ca.key" \
    -out "$CERT_DIR/ca.crt" 2>/dev/null

  # Server key + CSR
  openssl req -new -nodes \
    -subj "/CN=$CN" \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.csr" 2>/dev/null

  # Sign with CA (include SAN for hostname, Docker name, localhost)
  cat > "$CERT_DIR/san.cnf" <<EOF
[v3_req]
subjectAltName = DNS:$CN, DNS:mosquitto, DNS:localhost, IP:127.0.0.1
EOF

  openssl x509 -req -days "$DAYS" \
    -in "$CERT_DIR/server.csr" \
    -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial \
    -extfile "$CERT_DIR/san.cnf" -extensions v3_req \
    -out "$CERT_DIR/server.crt" 2>/dev/null

  # Clean up intermediates
  rm -f "$CERT_DIR/server.csr" "$CERT_DIR/san.cnf" "$CERT_DIR/ca.srl"

  echo "=== CA certificate (embed in firmware secrets.h) ==="
  cat "$CERT_DIR/ca.crt"
  echo "=== TLS certificates generated ==="
else
  echo "=== TLS certificates already exist, reusing ==="
  echo "CA valid until:"
  openssl x509 -noout -enddate -in "$CERT_DIR/ca.crt" 2>/dev/null || true
fi

# --- Always regenerate password file from env vars ---
MQTT_USER="${MQTT_USER:-edge}"
MQTT_PASSWORD="${MQTT_PASSWORD:-changeme}"
mosquitto_passwd -b -c /mosquitto/config/passwd "$MQTT_USER" "$MQTT_PASSWORD"
echo "=== MQTT password file updated for user: $MQTT_USER ==="

# --- Start Mosquitto ---
exec mosquitto -c /mosquitto/config/mosquitto.conf -v
