FROM eclipse-mosquitto:2.0

# Copy configuration file
COPY mosquitto.conf /mosquitto/config/mosquitto.conf

# Create password file from build args
ARG MQTT_USER=paku
ARG MQTT_PASSWORD=paku
RUN mosquitto_passwd -b -c /mosquitto/config/passwd "$MQTT_USER" "$MQTT_PASSWORD"

EXPOSE 1883

# Run Mosquitto in the foreground with verbose logging
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf", "-v"]
