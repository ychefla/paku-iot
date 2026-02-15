#!/bin/sh
# generate_certs.sh — Create a self-signed CA + server certificate for Mosquitto TLS.
# Called during Docker build. Certs are baked into the image.
#
# Usage: ./generate_certs.sh <common_name>
#   common_name: hostname/IP that devices connect to (e.g. paku.example.com)

set -e

CN="${1:-paku-mqtt}"
CERT_DIR="/mosquitto/certs"
DAYS=3650  # 10 years

mkdir -p "$CERT_DIR"

# --- CA ---
openssl req -new -x509 -days "$DAYS" -nodes \
  -subj "/CN=paku-mqtt-ca" \
  -keyout "$CERT_DIR/ca.key" \
  -out "$CERT_DIR/ca.crt" 2>/dev/null

# --- Server key + CSR ---
openssl req -new -nodes \
  -subj "/CN=$CN" \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.csr" 2>/dev/null

# --- Sign with CA (include SAN for IP and DNS) ---
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

# Output the CA cert so it can be embedded in firmware
echo "=== CA certificate (embed in firmware) ==="
cat "$CERT_DIR/ca.crt"
echo "=== Done ==="
