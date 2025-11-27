# Database Schema

This document describes the PostgreSQL database schema for the paku-iot backend.

## Overview

The database stores sensor measurements from Ruuvi devices. The schema is automatically initialized when the Postgres container starts for the first time via the `init.sql` script located in `stack/postgres/`.

## Tables

### measurements

Stores time-series sensor data from Ruuvi devices.

| Column               | Type               | Nullable | Description                                      |
|----------------------|--------------------|----------|--------------------------------------------------|
| id                   | BIGSERIAL          | No       | Primary key, auto-incrementing                   |
| sensor_id            | TEXT               | No       | Logical sensor identifier (e.g., "van_inside")   |
| ts                   | TIMESTAMPTZ        | No       | Measurement timestamp (defaults to NOW())        |
| temperature_c        | NUMERIC(5,2)       | No       | Temperature in degrees Celsius                   |
| humidity_percent     | NUMERIC(5,2)       | No       | Relative humidity as a percentage                |
| pressure_hpa         | NUMERIC(6,2)       | No       | Atmospheric pressure in hectopascals             |
| battery_mv           | INTEGER            | No       | Battery voltage in millivolts                    |
| acceleration_x_mg    | INTEGER            | Yes      | X-axis acceleration in milli-g                   |
| acceleration_y_mg    | INTEGER            | Yes      | Y-axis acceleration in milli-g                   |
| acceleration_z_mg    | INTEGER            | Yes      | Z-axis acceleration in milli-g                   |
| acceleration_total_mg| INTEGER            | Yes      | Total acceleration magnitude in milli-g          |
| tx_power_dbm         | INTEGER            | Yes      | Transmit power in dBm                            |
| movement_counter     | INTEGER            | Yes      | Movement counter value                           |
| measurement_sequence | INTEGER            | Yes      | Measurement sequence number                      |
| mac                  | TEXT               | Yes      | Device MAC address                               |

#### Indexes

- **Primary key:** `id`
- **idx_measurements_ts:** Index on `ts` for efficient time-range queries
- **idx_measurements_sensor_id:** Index on `sensor_id` for filtering by sensor
- **idx_measurements_sensor_ts:** Composite index on `(sensor_id, ts DESC)` for common queries

#### Example Query

```sql
-- Get the latest 10 measurements
SELECT * FROM measurements ORDER BY ts DESC LIMIT 10;

-- Get measurements for a specific sensor
SELECT * FROM measurements WHERE sensor_id = 'van_inside' ORDER BY ts DESC LIMIT 10;

-- Get measurements within a time range
SELECT * FROM measurements 
WHERE ts >= NOW() - INTERVAL '1 hour' 
ORDER BY ts DESC;
```

## Schema Initialization

The schema is created automatically when the Postgres container starts for the first time. The initialization script is located at:

```
stack/postgres/init.sql
```

This script is copied to `/docker-entrypoint-initdb.d/` in the container, where PostgreSQL automatically executes it during first-time initialization.

## Connection Details (Development)

Credentials for local development are configured via environment variables (see `.env.example`):

- **Host:** localhost (or `postgres` from within the Docker network)
- **Port:** 5432
- **Database:** Set via `POSTGRES_DB` environment variable
- **User:** Set via `POSTGRES_USER` environment variable
- **Password:** Set via `POSTGRES_PASSWORD` environment variable

⚠️ **Note:** Never commit real credentials. Use `.env` file (git-ignored) for local development and secrets management for production.

## Verifying Schema Creation

To verify the schema was created successfully:

1. Start the stack:
   ```bash
   docker compose -f compose/stack.yaml up -d
   ```

2. Connect to the database:
   ```bash
   docker exec -it paku_postgres psql -U paku -d paku
   ```

3. Check the table exists:
   ```sql
   \dt measurements
   ```

4. Verify you can query it:
   ```sql
   SELECT * FROM measurements LIMIT 1;
   ```

## Related Documentation

- [MQTT Schema](mqtt_schema.md) - Describes the message format ingested from MQTT
- [Requirements](requirements.md) - Overall system requirements and architecture
