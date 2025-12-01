# MQTT Schema Migration - December 1, 2025

## Overview

This document describes the migration from the old flat MQTT topic structure to a new hierarchical schema that better supports multi-site deployments, multiple systems, and standardized data formats.

## Old Schema

**Topic Pattern:** `paku/ruuvi/{location}`

**Example Topics:**
```
paku/ruuvi/van_inside
paku/ruuvi/van_outside
```

**Payload:** Flat JSON with all fields at root level
```json
{
  "timestamp": "2025-12-01T20:00:00Z",
  "temperature_c": 21.5,
  "humidity_percent": 45.2,
  "pressure_hpa": 1013.25,
  "battery_mv": 2870,
  "mac": "AA:BB:CC:DD:EE:FF"
}
```

## New Schema

**Topic Pattern:** `{site_id}/{system}/{device_id}/{topic_type}`

**Example Topics:**
```
paku/sensors/ruuvi_cabin/data
paku/sensors/ruuvi_outside/data
paku/flow/coolant/data
paku/power/ecoflow/data
```

**Payload:** Structured JSON with nested metrics
```json
{
  "timestamp": "2025-12-01T20:00:00Z",
  "device_id": "ruuvi_cabin",
  "location": "cabin",
  "mac": "AA:BB:CC:DD:EE:FF",
  "metrics": {
    "temperature_c": 21.5,
    "humidity_percent": 45.2,
    "pressure_hpa": 1013.25,
    "battery_mv": 2870
  }
}
```

## Key Changes

### 1. Hierarchical Topics
- **Site ID:** Enables multiple installations (paku, car, home, etc.)
- **System:** Groups related devices (sensors, heater, power, flow)
- **Device ID:** Unique identifier with system prefix (ruuvi_cabin, ecoflow, webasto)
- **Topic Type:** Separates data, control, status, config

### 2. Structured Payloads
- Common fields: `timestamp`, `device_id`, `location`, `mac`
- Device-specific data in nested `metrics` object
- Consistent field naming across all devices

### 3. Database Schema
New normalized table structure:
```sql
CREATE TABLE measurements (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT NOT NULL,
    system TEXT NOT NULL,
    device_id TEXT NOT NULL,
    location TEXT,
    mac TEXT,
    ts TIMESTAMPTZ NOT NULL,
    metrics JSONB NOT NULL
);
```

Old flat structure had all sensor fields as separate columns.

### 4. MAC Address Field
- Added to MQTT payload for device identification
- Stored in database for troubleshooting
- Helps map device_id to physical hardware

## Migration Steps

### 1. Database Migration
Run migration script to alter table structure:
```bash
docker exec paku_postgres psql -U paku -d paku -f /migrations/001_to_new_schema.sql
```

### 2. Update paku-core
- New topic format: `paku/sensors/ruuvi_{location}/data`
- Include MAC address in payload
- Nest sensor readings in `metrics` object

### 3. Update paku-iot Collector
- Parse new topic hierarchy
- Extract site_id, system, device_id from topic
- Store metrics as JSONB

### 4. Update Grafana Dashboards
- Query new JSONB metrics structure
- Use new indexing for performance
- Filter by site_id, system, device_id

## Benefits

1. **Scalability:** Supports multiple sites and installations
2. **Organization:** Clear system categories
3. **Flexibility:** JSONB metrics adapt to any device type
4. **Performance:** Better indexes for time-series queries
5. **Standardization:** Consistent format across all devices
6. **Identification:** MAC addresses for hardware tracking

## Compatibility

During migration period, both old and new formats are supported by the collector. Once all publishers are updated to new format, old format support can be removed.

## See Also

- [MQTT Schema Documentation](mqtt_schema.md)
- [Database Schema](database_schema.md)
- [Migration Guide](../MIGRATION_GUIDE.md)
