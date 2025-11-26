version: "3.9"

# ------------------------------------------------------------
# PAKU IoT – UNIFIED STACK
#
# This compose file starts the full lightweight environment:
#   ruuvi-emulator → mosquitto → collector → postgres → grafana
#
# Each service has its own directory under stack/.
# In this phase the goal is to run a clean end-to-end pipeline.
# ------------------------------------------------------------

services:
  # ------------------------------------------------------------
  # MOSQUITTO MQTT BROKER
  # Receives messages from the Ruuvi emulator.
  # The collector service subscribes here.
  # ------------------------------------------------------------
  mosquitto:
    build:
      context: ../stack/mosquitto
    container_name: paku_mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "1883"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ------------------------------------------------------------
  # POSTGRES – PERSISTENT STORAGE
  # Stores all sensor data.
  # The paku_pgdata volume ensures data persists across restarts.
  # ------------------------------------------------------------
  postgres:
    build:
      context: ../stack/postgres
    container_name: paku_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - paku_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ------------------------------------------------------------
  # GRAFANA
  # Visualization layer that reads from Postgres.
  # The paku_grafana volume stores dashboards and Grafana state.
  # ------------------------------------------------------------
  grafana:
    image: grafana/grafana:11.3.0
    container_name: paku_grafana
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      GF_SECURITY_ADMIN_USER: ${GF_SECURITY_ADMIN_USER}
      GF_SECURITY_ADMIN_PASSWORD: ${GF_SECURITY_ADMIN_PASSWORD}
    ports:
      - "3000:3000"
    volumes:
      - paku_grafana:/var/lib/grafana

  # ------------------------------------------------------------
  # RUUVITAG EMULATOR
  # Sends fake sensor data to MQTT for testing.
  # ------------------------------------------------------------
  ruuvi-emulator:
    build:
      context: ../stack/ruuvi-emulator
    container_name: paku_ruuvi_emulator
    restart: unless-stopped
    depends_on:
      mosquitto:
        condition: service_healthy
    environment:
      MQTT_HOST: mosquitto
      MQTT_PORT: 1883

  # ------------------------------------------------------------
  # COLLECTOR
  # Reads MQTT messages from Mosquitto and writes them to Postgres.
  # Subscribes to paku/ruuvi/van_inside and inserts data into the
  # measurements table.
  # ------------------------------------------------------------
  collector:
    build:
      context: ../stack/collector
    container_name: paku_collector
    restart: unless-stopped
    depends_on:
      mosquitto:
        condition: service_healthy
      postgres:
        condition: service_healthy
    environment:
      MQTT_HOST: mosquitto
      MQTT_PORT: 1883
      MQTT_TOPIC: paku/ruuvi/van_inside
      PGHOST: postgres
      PGPORT: 5432
      PGUSER: ${POSTGRES_USER}
      PGPASSWORD: ${POSTGRES_PASSWORD}
      PGDATABASE: ${POSTGRES_DB}

# ------------------------------------------------------------
# VOLUMES
# Centralized definitions for all persistent data directories.
# ------------------------------------------------------------
volumes:
  paku_pgdata:
  paku_grafana:

FROM python:3.12-alpine

# Install system dependencies required by psycopg[binary]
RUN apk add --no-cache gcc musl-dev libpq-dev

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy collector source code
COPY collector.py .

# Default command: run the collector
CMD ["python", "collector.py"]

# Paku Collector Service

The collector is a small Python service that:

- subscribes to MQTT messages from the Ruuvi emulator
- validates and parses the JSON payload
- inserts measurements into the Postgres database

## Runtime flow

1. Connect to Postgres using environment variables:
   - `PGHOST`
   - `PGPORT`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGDATABASE`

2. Connect to Mosquitto using:
   - `MQTT_HOST`
   - `MQTT_PORT`
   - `MQTT_TOPIC`

3. Subscribe to `MQTT_TOPIC` (currently `paku/ruuvi/van_inside`).

4. For each message:
   - decode JSON
   - validate against the schema defined in `docs/mqtt_schema.md`
   - insert a row into the `measurements` table
   - log errors but do not crash on malformed messages

## Environment

The collector is run as part of the unified stack defined in `compose/stack.yaml`.

The base image and dependencies are defined in `stack/collector/Dockerfile`.
