FROM eclipse-mosquitto:2.0

# Copy custom configuration if needed
# For now, use default configuration which allows anonymous connections
# and listens on port 1883

# Enable anonymous connections for development
RUN echo "listener 1883" > /mosquitto/config/mosquitto.conf && \
    echo "allow_anonymous true" >> /mosquitto/config/mosquitto.conf && \
    echo "persistence false" >> /mosquitto/config/mosquitto.conf
