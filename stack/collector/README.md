# Paku IoT Collector Service

The Collector service subscribes to MQTT topics, validates incoming sensor data, and writes it to PostgreSQL.

## Overview

This service acts as a bridge between the MQTT broker (Mosquitto) and the PostgreSQL database. It:
- Subscribes to the configured MQTT topic (default: `paku/ruuvi/van_inside`)
- Validates and parses JSON payloads
- Extracts sensor measurements
- Inserts data into the `measurements` table
- Handles errors gracefully without crashing

## Configuration

All configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOST` | `mosquitto` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_TOPIC` | `paku/ruuvi/van_inside` | MQTT topic to subscribe to |
| `PGHOST` | `postgres` | PostgreSQL host |
| `PGPORT` | `5432` | PostgreSQL port |
| `PGUSER` | `paku` | PostgreSQL username |
| `PGPASSWORD` | `paku` | PostgreSQL password |
| `PGDATABASE` | `paku` | PostgreSQL database name |

## Supported Message Formats

The collector supports both the documented RuuviTag format and legacy formats for compatibility:

### Documented Format (mqtt_schema.md)
```json
{
  "sensor_id": "van_inside",
  "temperature_c": 21.5,
  "humidity_percent": 45.2,
  "pressure_hpa": 1003.2,
  "battery_mv": 2870,
  "timestamp": "2025-11-25T09:30:00Z"
}
```

### Legacy Format (for compatibility)
```json
{
  "tag": "sensor-1",
  "temperature": 21.5,
  "humidity": 45.2,
  "battery": 3.1,
  "ts": "2025-11-25T09:30:00Z"
}
```

The collector will automatically map legacy field names to the database schema.

## Error Handling

The collector is designed to be resilient:
- **Malformed JSON**: Logs error and continues processing
- **Invalid data**: Logs error and continues processing
- **Database errors**: Logs error and continues processing
- **MQTT disconnection**: Attempts to reconnect automatically

This ensures that a single bad message doesn't crash the entire service.

## Database Schema

The collector writes to the `measurements` table with the following columns:
- `id` - Auto-incrementing primary key
- `sensor_id` - Logical sensor identifier
- `ts` - Timestamp (defaults to current time if not provided)
- `temperature_c` - Temperature in Celsius
- `humidity_percent` - Relative humidity percentage
- `pressure_hpa` - Atmospheric pressure in hPa
- `battery_mv` - Battery voltage in millivolts

## Running

The service is typically run as part of the Docker Compose stack:

```bash
docker compose -f compose/stack.yaml up collector
```

For development, you can run it directly:

```bash
export MQTT_HOST=localhost
export PGHOST=localhost
python3 collector.py
```

## Logging

The collector logs all activities to stdout:
- Connection status
- Received messages (debug level)
- Inserted measurements
- Errors (with details)

View logs using:
```bash
docker logs -f paku_collector
```

## Acceptance Criteria

✅ Subscribes to `paku/ruuvi/van_inside` topic  
✅ Validates and parses JSON payloads  
✅ Maps fields to database columns  
✅ Inserts rows into PostgreSQL  
✅ Logs each processed message  
✅ Handles malformed messages gracefully (logs error, continues)  
✅ Uses environment variables for configuration  
✅ Supports both documented and legacy field formats  
✅ Uses python:3.12-alpine base image  
