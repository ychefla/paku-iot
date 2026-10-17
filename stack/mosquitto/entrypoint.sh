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

# Ensure cert files are readable by mosquitto
chown -R mosquitto:mosquitto "$CERT_DIR"

# --- Always regenerate password + ACL files from env vars ---
# MQTT_USER is the paku site user (van devices + HA bridge): paku/# and
# homeassistant/#. MQTT_SITE_USERS adds one user per additional site, e.g.
#   MQTT_SITE_USERS="honkaranta:secret1,koti:secret2"
# Each site user may only touch {site}/#. ACL applies to the TLS listener
# (8883) only; the internal plain listener (1883) is not published.
MQTT_USER="${MQTT_USER:-edge}"
MQTT_PASSWORD="${MQTT_PASSWORD:-changeme}"
PASSWD_FILE=/mosquitto/config/passwd
ACL_FILE=/mosquitto/config/acl

mosquitto_passwd -b -c "$PASSWD_FILE" "$MQTT_USER" "$MQTT_PASSWORD"
cat > "$ACL_FILE" <<EOF
user $MQTT_USER
topic readwrite paku/#
topic readwrite homeassistant/#
EOF

if [ -n "${MQTT_SITE_USERS:-}" ]; then
  echo "$MQTT_SITE_USERS" | tr ',' '\n' | while IFS=: read -r site pass; do
    [ -z "$site" ] && continue
    if [ -z "$pass" ] || [ "$site" = "paku" ] || [ "$site" = "$MQTT_USER" ]; then
      echo "!!! Skipping invalid MQTT_SITE_USERS entry for site '$site'"
      continue
    fi
    mosquitto_passwd -b "$PASSWD_FILE" "$site" "$pass"
    printf '\nuser %s\ntopic readwrite %s/#\n' "$site" "$site" >> "$ACL_FILE"
    echo "=== MQTT site user added: $site ($site/#) ==="
  done
fi

chown mosquitto:mosquitto "$PASSWD_FILE" "$ACL_FILE"
chmod 600 "$PASSWD_FILE" "$ACL_FILE"
echo "=== MQTT password + ACL files updated (base user: $MQTT_USER) ==="

# --- Start Mosquitto ---
exec mosquitto -c /mosquitto/config/mosquitto.conf -v
