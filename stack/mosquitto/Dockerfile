FROM eclipse-mosquitto:2.0

# Install openssl for TLS cert generation (done at runtime)
RUN apk add --no-cache openssl

# Copy configuration and entrypoint
COPY mosquitto.conf /mosquitto/config/mosquitto.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 1883 8883

# Entrypoint generates certs (if missing) + password file, then starts Mosquitto
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
