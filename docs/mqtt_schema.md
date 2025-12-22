# MQTT Topic Schema for Paku IoT

## Overview

This document defines the MQTT topic hierarchy and payload formats for the Paku IoT system. The design supports multiple installations (sites), diverse device types, and clear separation of concerns between data, control, status, and configuration.

---

## Topic Hierarchy

```
{site_id}/{system}/{device_id}/{topic_type}
```

### Topic Levels

1. **`{site_id}`** - Installation identifier (e.g., `paku`, `car`, `home`)
2. **`{system}`** - Functional system category (e.g., `sensors`, `heater`, `power`, `flow`)
3. **`{device_id}`** - Unique device identifier (e.g., `ruuvi_cabin`, `ecoflow`, `webasto`)
4. **`{topic_type}`** - Message purpose: `data`, `control`, `status`, `config`

---

## Topic Types

### `/data` - Telemetry Data

Real-time sensor measurements and device telemetry. Published by devices.

**QoS:** 0 (at most once)  
**Retained:** No

**Example Topics:**
```
paku/sensors/ruuvi_cabin/data
paku/heater/webasto/data
paku/power/ecoflow/data
```

**Payload Format:**
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

### `/control` - Device Commands

Commands sent to devices for control actions.

**QoS:** 1 (at least once)  
**Retained:** Yes (last command)

**Example Topics:**
```
paku/heater/webasto/control
paku/lighting/cabin/control
```

**Payload Format:**
```json
{
  "command": "set_temperature",
  "value": 22,
  "timestamp": "2025-12-01T20:00:00Z"
}
```

### `/status` - Device Health

Device connectivity and health status. Published by devices.

**QoS:** 1 (at least once)  
**Retained:** Yes (last status)

**Example Topics:**
```
paku/sensors/ruuvi_cabin/status
paku/power/ecoflow/status
```

**Payload Format:**
```json
{
  "online": true,
  "last_seen": "2025-12-01T20:00:00Z",
  "signal_strength_dbm": -65,
  "uptime_seconds": 3600,
  "firmware_version": "1.0.2"
}
```

### `/config` - Device Configuration

Device configuration settings.

**QoS:** 1 (at least once)  
**Retained:** Yes (current config)

**Example Topics:**
```
paku/sensors/ruuvi_cabin/config
paku/heater/webasto/config
```

**Payload Format:**
```json
{
  "reporting_interval_seconds": 60,
  "enabled": true,
  "location": "cabin"
}
```

### EDGE Device Configuration Topics

**EDGE devices** (ESP32 firmware) use split configuration topics to prevent publish/subscribe loops:

#### `/config/set` - Configuration Commands (Subscribe)

Commands sent from the server to configure the device. Published by the server/operator.

**QoS:** 1 (at least once)  
**Retained:** Yes (last configuration)

**Example Topic:**
```
paku/edge/ESP32-20E955A0/config/set
```

**Usage:**
```bash
# Set configuration on the broker
docker exec paku_mosquitto mosquitto_pub -h localhost \
  -t 'paku/edge/ESP32-20E955A0/config/set' -r \
  -m '{"sensors":{"flow":{"enabled":false}}}'
```

**Payload Format:**
```json
{
  "timing": {
    "collection_interval_s": 300,
    "transmission_interval_s": 600,
    "timezone": "EET-2EEST,M3.5.0/3,M10.5.0/4"
  },
  "sensors": {
    "flow": {
      "enabled": false
    }
  },
  "power": {
    "disconnect_after_transmit": true
  }
}
```

#### `/config/report` - Configuration Status (Publish)

Current configuration reported by the device. Published by the device.

**QoS:** 1 (at least once)  
**Retained:** No (use `/status` for retained state)

**Example Topic:**
```
paku/edge/ESP32-20E955A0/config/report
```

**Payload Format:** Same as `/config/set`

**Separation Rationale:**
- Device subscribes only to `/config/set` for incoming commands
- Device publishes only to `/config/report` for status reporting
- No circular loop: device never receives its own config publications

---

## System Categories

### sensors
Environmental sensors (temperature, humidity, pressure)
- Ruuvi tags: `paku/sensors/ruuvi_{location}/data`
- Moko sensors: `paku/sensors/moko_{location}/data`

### heater
Heating system components
- Diesel heater: `paku/heater/webasto/data`
- Heater controller: `paku/heater/controller/data`

### power
Power systems and batteries
- EcoFlow: `paku/power/ecoflow/data`
- Leisure battery: `paku/power/leisure_battery/data`
- Starter battery: `paku/power/starter_battery/data`

### flow
Flow measurement devices
- Coolant flow: `paku/flow/coolant/data`

### climate
HVAC and climate control
- Ventilation: `paku/climate/ventilation/data`

---

## Payload Field Standards

### Common Fields (all `/data` topics)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp in UTC (e.g., "2025-12-01T20:00:00Z") |
| `device_id` | string | Yes | Unique device identifier matching topic |
| `location` | string | No | Physical location description |
| `mac` | string | No | BLE MAC address (for wireless sensors only) |

### Sensor-Specific Fields

**Ruuvi/Moko sensors:**
```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "metrics": {
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
}
```

**Note:** The `mac` field contains the BLE MAC address for hardware identification and troubleshooting.

**Power systems:**
```json
{
  "metrics": {
    "voltage_v": 13.2,
    "current_a": 5.3,
    "power_w": 69.96,
    "state_of_charge_percent": 87,
    "remaining_capacity_wh": 2610
  }
}
```

**Heater:**
```json
{
  "metrics": {
    "temperature_in_c": 18.5,
    "temperature_out_c": 65.2,
    "power_w": 2000,
    "pump_speed_percent": 75,
    "status": "heating"
  }
}
```

**Flow:**
```json
{
  "metrics": {
    "flow_rate_lpm": 4.2,
    "total_volume_l": 156.8,
    "pulse_count": 15680
  }
}
```

---

## Subscription Patterns

### Common Use Cases

| Pattern | Description |
|---------|-------------|
| `paku/#` | All data from paku site |
| `paku/sensors/#` | All sensor data |
| `paku/sensors/+/data` | Only sensor telemetry (no control/status) |
| `paku/+/ruuvi_cabin/data` | Specific device across all systems |
| `+/sensors/#` | All sensors across all sites |
| `paku/heater/+/control` | All heater control topics |

---

## Database Storage

The collector service subscribes to `{site_id}/+/+/data` and stores telemetry in a normalized format:

**measurements table:**
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

CREATE INDEX idx_measurements_site_device_ts 
    ON measurements(site_id, device_id, ts DESC);
CREATE INDEX idx_measurements_system_ts 
    ON measurements(system, ts DESC);
```

---

## Migration from Old Schema

**Old format:** `paku/ruuvi/van_inside` with flat JSON  
**New format:** `paku/sensors/ruuvi_van_inside/data` with nested metrics

Both formats will be supported during migration period.
