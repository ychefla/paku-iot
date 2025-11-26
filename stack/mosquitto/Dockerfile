FROM alpine:3.19

# Install Mosquitto MQTT broker
RUN apk add --no-cache mosquitto

# Minimal config for local development:
# - listen on port 1883 on all interfaces
# - allow anonymous connections (OK for local dev only)
RUN mkdir -p /mosquitto/config /mosquitto/data /mosquitto/log && \
    printf "listener 1883 0.0.0.0\nallow_anonymous true\n" > /mosquitto/config/mosquitto.conf

EXPOSE 1883

# Run Mosquitto in the foreground with verbose logging
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf", "-v"]
