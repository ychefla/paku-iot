FROM eclipse-mosquitto:2.0

# Copy configuration
COPY config/mosquitto.conf /mosquitto/config/mosquitto.conf

# Expose MQTT port
EXPOSE 1883

# Run Mosquitto
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
