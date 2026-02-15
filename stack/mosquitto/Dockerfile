FROM eclipse-mosquitto:2.0

# Install openssl for TLS cert generation
RUN apk add --no-cache openssl

# Copy configuration and cert generation script
COPY mosquitto.conf /mosquitto/config/mosquitto.conf
COPY generate_certs.sh /usr/local/bin/generate_certs.sh
RUN chmod +x /usr/local/bin/generate_certs.sh

# Generate self-signed CA + server certificate for TLS listener
ARG MQTT_CN=paku-mqtt
RUN /usr/local/bin/generate_certs.sh "$MQTT_CN"

# Create password file from build args (used by TLS listener only)
ARG MQTT_USER=paku
ARG MQTT_PASSWORD=paku
RUN mosquitto_passwd -b -c /mosquitto/config/passwd "$MQTT_USER" "$MQTT_PASSWORD"

EXPOSE 1883 8883

# Run Mosquitto in the foreground with verbose logging
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf", "-v"]
