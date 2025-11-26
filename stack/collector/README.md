# Paku IoT Collector Service

## Overview

The collector service subscribes to MQTT topics and stores validated sensor measurements in PostgreSQL. It implements structured validation against the RuuviTag schema to ensure data quality and service reliability.

## Features

- **Schema Validation**: Validates incoming MQTT messages against the documented RuuviTag schema (see `docs/mqtt_schema.md`)
- **Required Fields**: Validates presence of sensor_id, temperature_c, humidity_percent, pressure_hpa, and battery_mv
- **Type Checking**: Ensures field types match expectations (strings, numbers, integers)
- **Graceful Error Handling**: Logs validation errors with payload details but does not crash the service
- **Observability**: Tracks and reports count of rejected messages

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| sensor_id | string | Logical sensor identifier |
| temperature_c | int/float | Temperature in Celsius |
| humidity_percent | int/float | Humidity percentage |
| pressure_hpa | int/float | Atmospheric pressure in hPa |
| battery_mv | int | Battery voltage in millivolts |

## Optional Fields

The collector also accepts and stores additional RuuviTag fields:
- acceleration_x_mg, acceleration_y_mg, acceleration_z_mg
- acceleration_total_mg
- tx_power_dbm
- movement_counter
- measurement_sequence
- mac
- timestamp

## Configuration

The service is configured via environment variables:

- `MQTT_HOST`: MQTT broker hostname (default: mosquitto)
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `PGHOST`: PostgreSQL hostname (default: postgres)
- `PGUSER`: PostgreSQL username (default: paku)
- `PGPASSWORD`: PostgreSQL password (default: paku)
- `PGDATABASE`: PostgreSQL database name (default: paku)

## Error Handling

When a message fails validation:
1. A detailed error message is logged including the validation failure reason
2. The complete payload is logged for debugging
3. The rejected message counter is incremented
4. The message is skipped (not inserted into the database)
5. The service continues running normally

## Testing

Run the validation tests:

```bash
python3 test_validation.py
```

The test suite includes:
- Valid message acceptance
- Missing required field detection
- Type validation for all required fields
- Support for both integer and float numeric types

## Database Schema

The collector inserts validated measurements into the `measurements` table:

```sql
CREATE TABLE measurements (
    id BIGSERIAL PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    temperature_c NUMERIC(5, 2) NOT NULL,
    humidity_percent NUMERIC(5, 2) NOT NULL,
    pressure_hpa NUMERIC(6, 2) NOT NULL,
    battery_mv INTEGER NOT NULL,
    -- Optional fields...
);
```

## Logging

The collector provides structured logging:
- `[INFO]`: Successful message insertion
- `[ERROR]`: Validation failures, JSON parse errors, database errors
- On shutdown: Total count of rejected messages

## Example Valid Message

```json
{
  "sensor_id": "van_inside",
  "temperature_c": 21.5,
  "humidity_percent": 45.2,
  "pressure_hpa": 1003.2,
  "battery_mv": 2870,
  "mac": "AA:BB:CC:DD:EE:FF",
  "timestamp": "2025-11-25T09:30:00Z"
}
```

## Example Error Scenarios

### Missing Required Field
```
[ERROR] Validation failed for topic paku/ruuvi/van_inside: Missing required field: sensor_id
[ERROR] Payload: {"temperature_c": 21.5, ...}
[INFO] Total rejected messages: 1
```

### Type Mismatch
```
[ERROR] Validation failed for topic paku/ruuvi/van_inside: Field 'temperature_c' has incorrect type: expected int or float, got str
[ERROR] Payload: {"sensor_id": "van_inside", "temperature_c": "21.5", ...}
[INFO] Total rejected messages: 2
```

### Invalid JSON
```
[ERROR] Invalid JSON on topic paku/ruuvi/van_inside: Expecting value: line 1 column 1 (char 0)
[ERROR] Payload: {invalid json}
[INFO] Total rejected messages: 3
```

## Dependencies

- `paho-mqtt==2.1.0`: MQTT client library
- `psycopg[binary]==3.2.3`: PostgreSQL adapter for Python
