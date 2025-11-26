# Database Schema

This document describes the PostgreSQL database schema for the paku-iot backend.

## Overview

The database stores sensor measurements from Ruuvi devices. The schema is automatically initialized when the Postgres container starts for the first time via the `init.sql` script located in `stack/postgres/`.

## Tables

### measurements

Stores time-series sensor data from Ruuvi devices.

| Column             | Type               | Nullable | Description                                      |
|--------------------|--------------------|----------|--------------------------------------------------|
| id                 | SERIAL             | No       | Primary key, auto-incrementing                   |
| sensor_id          | TEXT               | No       | Logical sensor identifier (e.g., "van_inside")   |
| ts                 | TIMESTAMPTZ        | No       | Measurement timestamp with timezone              |
| temperature_c      | DOUBLE PRECISION   | Yes      | Temperature in degrees Celsius                   |
| humidity_percent   | DOUBLE PRECISION   | Yes      | Relative humidity as a percentage                |
| pressure_hpa       | DOUBLE PRECISION   | Yes      | Atmospheric pressure in hectopascals             |
| battery_mv         | INTEGER            | Yes      | Battery voltage in millivolts                    |
| created_at         | TIMESTAMPTZ        | No       | Record creation timestamp (defaults to now)      |

#### Indexes

- **Primary key:** `id`
- **idx_measurements_ts:** Index on `ts DESC` for efficient time-range queries
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

Default credentials for local development (defined in `stack/postgres/Dockerfile`):

- **Host:** localhost (or `paku_postgres` from within the Docker network)
- **Port:** 5432
- **Database:** paku
- **User:** paku
- **Password:** paku

⚠️ **Note:** These are development-only credentials. Production deployments should use secure credentials stored in environment variables or secrets management.

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
