FROM eclipse-mosquitto:2.0

# Enable anonymous connections for development
# Listen on all interfaces for Docker networking
RUN echo "listener 1883 0.0.0.0" > /mosquitto/config/mosquitto.conf && \
    echo "allow_anonymous true" >> /mosquitto/config/mosquitto.conf && \
    echo "persistence false" >> /mosquitto/config/mosquitto.conf

EXPOSE 1883

# Run Mosquitto in the foreground with verbose logging
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf", "-v"]
