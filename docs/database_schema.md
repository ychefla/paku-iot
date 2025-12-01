# Database Schema

This document describes the PostgreSQL database schema for the paku-iot backend.

## Overview

The database stores time-series telemetry data from diverse IoT devices across multiple sites. The schema uses a flexible JSONB structure to accommodate different device types while maintaining efficient indexing and query performance.

The schema is automatically initialized when the Postgres container starts for the first time via the `init.sql` script located in `stack/postgres/`.

## Tables

### measurements

Stores time-series telemetry data from all IoT devices.

| Column      | Type        | Nullable | Description                                              |
|-------------|-------------|----------|----------------------------------------------------------|
| id          | BIGSERIAL   | No       | Primary key, auto-incrementing                           |
| site_id     | TEXT        | No       | Installation identifier (e.g., "paku", "car", "home")    |
| system      | TEXT        | No       | System category (e.g., "sensors", "heater", "power")     |
| device_id   | TEXT        | No       | Unique device identifier (e.g., "ruuvi_cabin")           |
| location    | TEXT        | Yes      | Physical location description (e.g., "cabin", "kitchen") |
| ts          | TIMESTAMPTZ | No       | Measurement timestamp (defaults to NOW())                |
| metrics     | JSONB       | No       | Device metrics as JSON object (flexible schema)          |
| created_at  | TIMESTAMPTZ | No       | Record creation timestamp (defaults to NOW())            |

#### Indexes

- **Primary key:** `id`
- **idx_measurements_ts:** B-tree index on `ts DESC` for time-range queries
- **idx_measurements_site_device_ts:** Composite index on `(site_id, device_id, ts DESC)` for device-specific time-series queries
- **idx_measurements_system_ts:** Composite index on `(system, ts DESC)` for system-level queries
- **idx_measurements_site_system:** Composite index on `(site_id, system)` for filtering by site and system
- **idx_measurements_metrics:** GIN index on `metrics` JSONB column for fast metric field queries

#### Metrics Field Structure

The `metrics` column stores device-specific measurements as a JSON object. Different device types have different metrics:

**Sensor devices (Ruuvi, Moko):**
```json
{
  "temperature_c": 21.5,
  "humidity_percent": 45.2,
  "pressure_hpa": 1013.25,
  "battery_mv": 2870,
  "acceleration_x_mg": -23,
  "acceleration_y_mg": 5,
  "acceleration_z_mg": 1015,
  "tx_power_dbm": 4,
  "movement_counter": 120
}
```

**Power systems:**
```json
{
  "voltage_v": 13.2,
  "current_a": 5.3,
  "power_w": 69.96,
  "state_of_charge_percent": 87,
  "remaining_capacity_wh": 2610
}
```

**Heater systems:**
```json
{
  "temperature_in_c": 18.5,
  "temperature_out_c": 65.2,
  "power_w": 2000,
  "pump_speed_percent": 75,
  "status": "heating"
}
```

**Flow meters:**
```json
{
  "flow_rate_lpm": 4.2,
  "total_volume_l": 156.8,
  "pulse_count": 15680
}
```

#### Example Queries

```sql
-- Get latest measurements from all devices at paku site
SELECT 
  device_id, 
  location, 
  ts, 
  metrics 
FROM measurements 
WHERE site_id = 'paku' 
ORDER BY ts DESC 
LIMIT 10;

-- Get temperature data from all sensor devices
SELECT 
  device_id,
  location,
  ts,
  metrics->>'temperature_c' as temperature_c
FROM measurements 
WHERE system = 'sensors'
  AND metrics ? 'temperature_c'
ORDER BY ts DESC 
LIMIT 100;

-- Get measurements for a specific device
SELECT * 
FROM measurements 
WHERE site_id = 'paku' 
  AND device_id = 'ruuvi_cabin' 
ORDER BY ts DESC 
LIMIT 10;

-- Get measurements within a time range for a specific system
SELECT * 
FROM measurements 
WHERE site_id = 'paku'
  AND system = 'power'
  AND ts >= NOW() - INTERVAL '1 hour' 
ORDER BY ts DESC;

-- Query specific metric across all sensor devices
SELECT 
  site_id,
  device_id,
  location,
  ts,
  (metrics->>'temperature_c')::numeric as temperature_c
FROM measurements
WHERE system = 'sensors'
  AND metrics ? 'temperature_c'
  AND ts >= NOW() - INTERVAL '24 hours'
ORDER BY ts DESC;

-- Average temperature by location over last hour
SELECT 
  location,
  AVG((metrics->>'temperature_c')::numeric) as avg_temp,
  COUNT(*) as reading_count
FROM measurements
WHERE system = 'sensors'
  AND metrics ? 'temperature_c'
  AND ts >= NOW() - INTERVAL '1 hour'
GROUP BY location
ORDER BY avg_temp DESC;
```

## Schema Initialization

The schema is created automatically when the Postgres container starts for the first time. The initialization script is located at:

```
stack/postgres/init.sql
```

This script is copied to `/docker-entrypoint-initdb.d/` in the container, where PostgreSQL automatically executes it during first-time initialization.

## Data Migration

If you have existing data in the old schema, you can migrate it with:

```sql
-- Backup existing data (if needed)
CREATE TABLE measurements_old AS SELECT * FROM measurements;

-- Drop old table and recreate with new schema
DROP TABLE measurements;
-- (Run init.sql or restart container)

-- Note: Migration script for old data would need to be created
-- based on your specific data mapping requirements
```

## Connection Details (Development)

Credentials for local development are configured via environment variables (see `compose/.env.example`):

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

4. Inspect the table structure:
   ```sql
   \d+ measurements
   ```

5. Verify you can query it:
   ```sql
   SELECT * FROM measurements LIMIT 1;
   ```

## Performance Considerations

- The GIN index on `metrics` enables fast queries on any metric field but has higher write cost
- Time-series queries are optimized with descending timestamp indexes
- Consider partitioning by `ts` if data volume exceeds millions of rows
- Use TimescaleDB extension for advanced time-series features (optional)

## Related Documentation

- [MQTT Schema](mqtt_schema.md) - Describes the message format ingested from MQTT
- [Requirements](requirements.md) - Overall system requirements and architecture
