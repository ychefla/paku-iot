FROM eclipse-mosquitto:2.0

# Copy configuration file
COPY mosquitto.conf /mosquitto/config/mosquitto.conf

EXPOSE 1883

# Run Mosquitto in the foreground with verbose logging
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf", "-v"]
