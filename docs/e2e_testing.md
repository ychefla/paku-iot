# End-to-End Testing

This document describes how to run the end-to-end (E2E) tests for the Paku IoT stack.

## Prerequisites

- Docker and Docker Compose installed
- Ports 1883 (MQTT), 3000 (Grafana), and 5432 (Postgres) available

## Quick Start

### Automated Test

Run the automated E2E test script:

```bash
cd /path/to/paku-iot
./tests/e2e_test.sh
```

This script will:
1. Start the entire stack using `docker compose -f compose/stack.yaml up --build`
2. Wait for all services to be healthy
3. Publish a test MQTT message
4. Verify the message appears in Postgres
5. Verify Grafana dashboard is accessible and can query data
6. Clean up after completion

### Manual Testing

If you prefer to test manually, follow these steps:

#### 1. Start the Stack

```bash
cd /path/to/paku-iot
docker compose -f compose/stack.yaml up --build
```

Wait for all services to start (you should see log messages from all services).

#### 2. Verify Services

Check that all services are healthy:

```bash
docker compose -f compose/stack.yaml ps
```

All services should show as "healthy" or "running".

#### 3. Publish a Test Message

Using `mosquitto_pub` (requires mosquitto-clients package):

```bash
mosquitto_pub -h localhost -p 1883 -t "paku/ruuvi/test_sensor" -m '{
  "sensor_id": "test_sensor",
  "temperature_c": 22.5,
  "humidity_percent": 55.0,
  "pressure_hpa": 1013.25,
  "battery_mv": 2900,
  "timestamp": "2025-01-01T12:00:00Z"
}'
```

Or using the mosquitto container:

```bash
docker exec -it paku_mosquitto mosquitto_pub -t "paku/ruuvi/test_sensor" -m '{"sensor_id":"test_sensor","temperature_c":22.5,"humidity_percent":55.0,"pressure_hpa":1013.25,"battery_mv":2900}'
```

#### 4. Verify Postgres Data

Check that the measurement was inserted:

```bash
docker exec paku_postgres psql -U paku -d paku -c "SELECT * FROM measurements ORDER BY ts DESC LIMIT 5;"
```

You should see your test message in the results.

#### 5. Verify Grafana Dashboard

1. Open Grafana in your browser: http://localhost:3000
2. Navigate to Dashboards → Paku → Paku Overview
3. Verify that:
   - The dashboard loads without errors
   - Temperature, Humidity, Pressure, and Battery charts are displayed
   - The "Latest Measurements" table shows your test data

#### 6. Stop the Stack

```bash
docker compose -f compose/stack.yaml down
```

To remove all data volumes as well:

```bash
docker compose -f compose/stack.yaml down --volumes
```

## Test Acceptance Criteria

The E2E test is considered successful when:

1. ✅ The stack starts successfully using `docker compose -f compose/stack.yaml up --build`
2. ✅ All services become healthy within a reasonable timeout (2 minutes)
3. ✅ An MQTT message published to `paku/ruuvi/<sensor_id>` is captured by the collector
4. ✅ The message is inserted into the Postgres `measurements` table
5. ✅ Grafana is accessible and the Paku Overview dashboard displays data

## Troubleshooting

### Services not starting

Check the logs for each service:

```bash
docker compose -f compose/stack.yaml logs mosquitto
docker compose -f compose/stack.yaml logs postgres
docker compose -f compose/stack.yaml logs collector
docker compose -f compose/stack.yaml logs grafana
```

### Messages not appearing in Postgres

1. Verify the collector is connected to MQTT:
   ```bash
   docker logs paku_collector | grep "connected"
   ```

2. Check for message parsing errors:
   ```bash
   docker logs paku_collector | grep -i "error\|warning"
   ```

3. Verify MQTT broker is receiving messages:
   ```bash
   docker exec -it paku_mosquitto mosquitto_sub -t "paku/#" -v
   ```

### Grafana dashboard not showing data

1. Verify Postgres datasource connection:
   - Go to Grafana → Connections → Data sources → Paku Postgres
   - Click "Test" to verify the connection

2. Check the time range:
   - Make sure the dashboard time range includes the time when data was inserted
   - Try setting to "Last 1 hour" or "Last 5 minutes"

3. Verify data exists in Postgres:
   ```bash
   docker exec paku_postgres psql -U paku -d paku -c "SELECT * FROM measurements ORDER BY ts DESC LIMIT 5;"
   ```
