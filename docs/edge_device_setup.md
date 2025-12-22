# EDGE Device Setup Guide

This document describes how to configure and manage EDGE devices (ESP32 firmware) in the Paku IoT system.

## Overview

EDGE devices are ESP32-based sensors that:
- Collect environmental data (temperature, humidity, pressure)
- Scan for BLE sensors (RuuviTag, MoKo)
- Communicate via MQTT with the backend
- Support remote configuration and OTA updates

## MQTT Topics

EDGE devices use a dedicated topic namespace separate from sensor data topics.

### Topic Structure

```
paku/edge/{device_id}/...
```

Where `{device_id}` is typically the MAC address (e.g., `ESP32-20E955A0`).

### Configuration Topics

EDGE devices use **split configuration topics** to prevent publish/subscribe loops:

#### Subscribe: `/config/set`

The device subscribes to this topic to receive configuration commands from the server.

**Topic:** `paku/edge/{device_id}/config/set`  
**QoS:** 1 (at least once)  
**Retained:** Yes (so devices receive config on reconnect)  
**Direction:** Server → Device

#### Publish: `/config/report`

The device publishes its current configuration to this topic after applying changes.

**Topic:** `paku/edge/{device_id}/config/report`  
**QoS:** 1 (at least once)  
**Retained:** No  
**Direction:** Device → Server

### Other EDGE Topics

- **Status**: `paku/edge/{device_id}/status` - Device online/offline, uptime, firmware version
- **Telemetry**: `paku/edge/{device_id}/telemetry` - ESP32 internal metrics (heap, WiFi signal)
- **OTA**: `paku/edge/{device_id}/ota` - OTA update commands

## Configuration Format

### Complete Configuration Object

```json
{
  "timing": {
    "collection_interval_s": 300,
    "transmission_interval_s": 600,
    "network_connection_timeout_s": 30,
    "disconnect_delay_s": 2,
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

### Timezone Configuration

The `timezone` field uses POSIX TZ format which supports automatic DST transitions:

**Format:** `STD offset [DST [offset],start[/time],end[/time]]`

**Common Examples:**

| Location | Timezone String |
|----------|----------------|
| Finland | `EET-2EEST,M3.5.0/3,M10.5.0/4` |
| UTC | `UTC0` |
| US Pacific | `PST8PDT,M3.2.0,M11.1.0` |
| US Eastern | `EST5EDT,M3.2.0,M11.1.0` |
| Central Europe | `CET-1CEST,M3.5.0,M10.5.0/3` |

**Components:**
- `EET-2` = Eastern European Time, UTC+2
- `EEST` = Eastern European Summer Time, UTC+3
- `M3.5.0/3` = Last Sunday (5th occurrence of Sunday, day 0) in March at 03:00
- `M10.5.0/4` = Last Sunday in October at 04:00

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timing.collection_interval_s` | int | 300 | How often to collect sensor data (seconds) |
| `timing.transmission_interval_s` | int | 600 | How often to transmit data via MQTT (seconds) |
| `timing.network_connection_timeout_s` | int | 30 | Maximum time to wait for network connection |
| `timing.disconnect_delay_s` | int | 2 | Delay before disconnecting WiFi after transmit |
| `timing.timezone` | string | `EET-2EEST,M3.5.0/3,M10.5.0/4` | POSIX timezone string |
| `sensors.flow.enabled` | bool | false | Enable flow sensor (set to false if not connected) |
| `power.disconnect_after_transmit` | bool | true | Disconnect WiFi after MQTT transmission to save power |

## Configuring a Device

### Method 1: Using mosquitto_pub (Docker)

From the server where the Mosquitto broker is running:

```bash
# Connect to the container
docker exec -it paku_mosquitto sh

# Publish configuration (retained)
mosquitto_pub -h localhost \
  -t 'paku/edge/ESP32-20E955A0/config/set' \
  -r \
  -m '{
    "timing": {
      "timezone": "EET-2EEST,M3.5.0/3,M10.5.0/4"
    },
    "sensors": {
      "flow": {
        "enabled": false
      }
    }
  }'
```

**Important:** Use the `-r` flag to retain the message. Devices retrieve this on connection.

### Method 2: Using mosquitto_pub (External)

If connecting from outside the server:

```bash
mosquitto_pub -h your-server-hostname \
  -p 1883 \
  -t 'paku/edge/ESP32-20E955A0/config/set' \
  -r \
  -m '{"sensors":{"flow":{"enabled":false}}}'
```

### Method 3: Using an MQTT Client Library

Python example:

```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect("your-server-hostname", 1883)

config = {
    "timing": {
        "timezone": "EET-2EEST,M3.5.0/3,M10.5.0/4"
    }
}

client.publish(
    "paku/edge/ESP32-20E955A0/config/set",
    json.dumps(config),
    qos=1,
    retain=True
)
```

## Verifying Configuration

### Check Current Retained Configuration

```bash
docker exec paku_mosquitto mosquitto_sub \
  -h localhost \
  -t 'paku/edge/+/config/set' \
  -v \
  -C 1
```

This will show the current retained configuration for all devices.

### Monitor Configuration Reports

Watch for devices reporting their configuration:

```bash
docker exec paku_mosquitto mosquitto_sub \
  -h localhost \
  -t 'paku/edge/+/config/report' \
  -v
```

### Check Device Logs

If you have serial access to the device, monitor the output for:

```
Processing retained messages...
Received configuration command from config/set topic
Config change: sensors.flow.enabled true -> false
Configuration updated and saved
```

## Troubleshooting

### Device Not Receiving Configuration

1. **Check retained message exists:**
   ```bash
   docker exec paku_mosquitto mosquitto_sub \
     -h localhost \
     -t 'paku/edge/ESP32-20E955A0/config/set' \
     -C 1
   ```

2. **Verify device subscribes correctly** - Check device serial logs for:
   ```
   Subscribed to paku/edge/ESP32-20E955A0/config/set
   ```

3. **Ensure MQTT buffer is large enough** - Device firmware should have buffer size ≥ 1024 bytes

4. **Check network connectivity** - Verify device connects to MQTT broker

### Configuration Not Persisting

Configuration is stored in ESP32 Non-Volatile Storage (NVS). It should persist across:
- Device reboots
- Power cycles

Configuration does **NOT** persist across:
- Full NVS erasure
- Factory reset

To reset to defaults, erase NVS:
```bash
pio run -t erase
```

### Wrong Timezone

1. **Verify timezone string format** using an online POSIX TZ validator
2. **Check device serial output** for timezone parsing errors
3. **Confirm time synchronization** - Device should show NTP sync on serial console

## Initial Device Setup

When setting up a new EDGE device:

1. **Flash firmware** (see paku-core documentation)

2. **Configure WiFi** (in `secrets.h` before flashing)

3. **Set initial configuration** via MQTT:
   ```bash
   mosquitto_pub -h your-server \
     -t 'paku/edge/ESP32-XXXXXX/config/set' \
     -r \
     -m '{
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
     }'
   ```

4. **Power on device** - It will connect, receive retained config, and start operating

## Best Practices

1. **Always use retained messages** (`-r` flag) for configuration
2. **Use partial configuration updates** - Only specify fields you want to change
3. **Monitor config/report topic** to verify changes applied
4. **Set timezone appropriately** for your device location
5. **Disable unused sensors** (like flow) to reduce processing overhead
6. **Test configuration changes** on one device before deploying to all

## See Also

- [MQTT Schema Documentation](mqtt_schema.md) - Complete MQTT topic reference
- [OTA Updates Guide](ota_updates.md) - Firmware update procedures
- [paku-core Documentation](https://github.com/ychefla/paku-core/tree/main/docs) - EDGE device firmware details
