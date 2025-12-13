# Migration Guide: New MQTT Topic Hierarchy

## Overview

This document describes the migration from the old flat MQTT topic structure to a new hierarchical system that supports multiple sites, systems, and device types.

## What Changed

### Topic Structure

**Old:** `paku/ruuvi/van_inside` or `paku/devices/{device_id}/telemetry/{type}/{location}`  
**New:** `{site_id}/{system}/{device_id}/data`

Examples:
- `paku/sensors/ruuvi_cabin/data` - Ruuvi sensor in cabin
- `paku/flow/coolant/data` - Coolant flow meter
- `paku/power/ecoflow/data` - EcoFlow battery
- `paku/heater/webasto/data` - Diesel heater

### Payload Structure

**Old** (flat JSON):
```json
{
  "sensor_id": "van_inside",
  "temperature_c": 21.5,
  "humidity_percent": 45.2,
  "pressure_hpa": 1013.25,
  "battery_mv": 2870,
  "timestamp": "2025-12-01T20:00:00Z"
}
```

**New** (nested with metrics):
```json
{
  "timestamp": "2025-12-01T20:00:00Z",
  "device_id": "ruuvi_cabin",
  "location": "cabin",
  "metrics": {
    "temperature_c": 21.5,
    "humidity_percent": 45.2,
    "pressure_hpa": 1013.25,
    "battery_mv": 2870
  }
}
```

### Database Schema

**Old:**
- Flat columns for each metric
- `sensor_id` as identifier

**New:**
- `site_id`, `system`, `device_id` for hierarchical identification
- `metrics` JSONB column for flexible metric storage
- `location` as optional metadata

## Migration Steps

### 1. Update Database ✅ DONE

The database schema has been updated:
- New table structure with `site_id`, `system`, `device_id`
- JSONB `metrics` column
- Improved indexes for time-series queries

To apply (will drop existing data):
```bash
docker compose -f compose/stack.yaml down -v
docker compose -f compose/stack.yaml up -d
```

### 2. Update Collector ✅ DONE

The collector now:
- Subscribes to `+/+/+/data` (all sites/systems/devices)
- Parses topic to extract site_id, system, device_id
- Validates new payload structure
- Stores metrics in JSONB column

### 3. Update paku-core ⏸️ PENDING

See `paku-core/MQTT_UPDATE.md` for detailed code changes required.

**Note**: This step requires updates to the separate paku-core firmware repository. The backend (paku-iot) supports both old and new formats during the transition period.

Key changes needed in paku-core:
- Consolidate metrics per device into single message
- Use new topic pattern: `paku/{system}/{device_id}/data`
- Include all metrics in `metrics` object

### 4. Update Grafana Dashboards ✅ COMPLETED

Dashboards have been updated to use the new schema.

Example query updates:
```sql
-- Old query
SELECT ts, temperature_c 
FROM measurements 
WHERE sensor_id = 'van_inside'

-- New query
SELECT 
  ts, 
  (metrics->>'temperature_c')::numeric as temperature_c
FROM measurements 
WHERE site_id = 'paku'
  AND device_id = 'ruuvi_cabin'
```

## Benefits

1. **Scalability**: Support multiple installations (vans, cars, homes)
2. **Flexibility**: JSONB metrics support any device type
3. **Organization**: Clear hierarchy for topic subscription
4. **Performance**: Better indexes for common query patterns
5. **Grafana**: Easier filtering and visualization

## Backwards Compatibility

Currently NO backwards compatibility. All components must be updated together.

Future enhancement could add support for both formats during transition period.

## Testing

After migration:
1. Verify MQTT topics in MQTT Explorer
2. Check database inserts: `SELECT * FROM measurements ORDER BY ts DESC LIMIT 10;`
3. Test Grafana queries with new schema
4. Verify all device types are reporting correctly

## Rollback Plan

If issues occur:
1. Stop all services
2. Restore from backup (if data important)
3. Revert to previous git commits
4. Redeploy old version

## Support

- Documentation: `/docs/mqtt_schema.md`, `/docs/database_schema.md`
- Issues: Create GitHub issue with logs
- Contact: System maintainer
