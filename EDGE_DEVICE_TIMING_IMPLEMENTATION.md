# Edge Device Timing and Configuration Implementation

## Overview
Decoupled sensor collection timing from edge device connection timing to optimize power consumption and synchronize operations efficiently.

## Implementation Summary

### Phase 1: Edge Device Timing Configuration (COMPLETED)
**Changes to ESP devices (paku-core):**

1. **New Configuration Structure**
   - Added `EdgeDeviceConfig` struct with timing, sensor, and power settings
   - Timing parameters:
     - `wake_interval_s`: How often the device wakes up (default: 60s)
     - `connection_duration_max_s`: Maximum time to stay connected (default: 30s)
     - `wifi_connect_timeout_s`: WiFi connection timeout (default: 10s)
     - `mqtt_connect_timeout_s`: MQTT connection timeout (default: 5s)
   
   - Sensor configurations:
     - BLE: scan_duration_s, scan_active flag
     - Wired: sample_count, sample_interval_ms
     - Flow: measurement_duration_s
   
   - Power settings:
     - deep_sleep_enabled
     - light_sleep_during_wait
     - battery_monitor_enabled

2. **MQTT Topics for Edge Devices**
   - Status: `{site_id}/edge/{device_id}/status` (published by device)
   - Config: `{site_id}/edge/{device_id}/config` (published by device, subscribed for updates)
   
   Status payload includes:
   - timestamp, state, uptime_s, firmware_version
   - wifi: rssi, ip
   - mqtt: connected, reconnect_count
   - system: free_heap, min_free_heap
   - sensors: last collection timestamp per sensor type

3. **Device ID Format**
   - Changed from "paku-{chip_id}" to "{board_type}-{chip_id}"
   - Examples: "ESP32-12345678", "ESP8266-WIRED-20E955A0"
   - Allows easier identification of device capabilities

4. **State Machine Enhancement**
   - States: INIT, COLLECT, CONNECT_NETWORK, TRANSMIT, DISCONNECT, SLEEP
   - Timing-aware transitions based on configuration
   - Efficient synchronization of sensor readings before network operations

### Phase 2: Data Collection Timing (COMPLETED)
**Changes to sensor collection:**

1. **Decoupled Sensor Timing**
   - Each sensor type has independent timing configuration
   - BLE: scan duration configurable
   - Wired: sample count and interval configurable
   - Flow: measurement duration configurable
   
2. **Efficient Data Buffering**
   - Sensors collect data independently
   - Data buffered in memory
   - Transmitted in batches when network connected
   - Maximum buffer size: 100 readings

3. **Synchronized Operations**
   - Device wakes up at configured intervals
   - Collects from all enabled sensors in parallel
   - Connects to network only when buffer threshold reached or timeout
   - Minimizes wake time by synchronizing operations

### Phase 3: Backend Support (COMPLETED)
**Changes to paku-iot backend:**

1. **Database Schema**
   - Created `edge_device_configs` table for device configurations
   - Created `edge_device_status` table for status time-series data
   - Indexes for efficient queries on site_id and device_id

2. **Collector Service Enhancement**
   - Now subscribes to three topic patterns:
     - `+/+/+/data` (sensor measurements)
     - `+/edge/+/status` (edge device status)
     - `+/edge/+/config` (edge device configuration)
   
   - Handles different topic types appropriately:
     - data: validates and inserts into measurements table
     - status: inserts into edge_device_status table
     - config: upserts into edge_device_configs table

3. **Topic Structure Validation**
   - All topics follow: `{site_id}/{system}/{device_id}/{topic_type}`
   - Edge devices use system="edge"
   - Ensures consistent data organization

## Current System Behavior

### ESP32-BLE (paku-96036100)
- Wakes every 10 seconds
- Scans for BLE devices
- Stays connected up to 30 seconds
- Reports status every cycle
- Publishes configuration on connect

### ESP8266-WIRED (paku-20E955A0)
- Continuously powered (not sleeping)
- Collects wired sensor data
- Reports status periodically
- Configuration in progress (not yet published)

## Verified Functionality
✅ Edge device status being captured in database
✅ Edge device configuration being captured in database  
✅ Sensor data collection continues normally
✅ MQTT topic structure follows documentation
✅ Collector handles all three topic types

## Database Tables

### edge_device_configs
Stores latest configuration for each edge device:
- site_id, device_id (unique)
- config (JSONB): timing, sensors, power settings
- updated_at

### edge_device_status
Time-series status updates:
- site_id, device_id
- status (JSONB): state, uptime, wifi, mqtt, system, sensors
- ts (timestamp from device)
- created_at

## Next Steps (Future Enhancements)

1. **Configuration Management UI**
   - Web interface to view and update device configurations
   - Send config updates via MQTT to devices
   
2. **Alerting and Monitoring**
   - Alert when devices offline too long
   - Monitor battery levels
   - Track connection quality

3. **Optimization**
   - Analyze timing patterns
   - Suggest optimal wake intervals
   - Power consumption analytics

4. **ESP8266 Configuration**
   - Complete config publishing for ESP8266-WIRED device
   - Ensure all devices report consistently

## Files Modified

### paku-core (ESP firmware)
- `src/main.cpp`: Added config structures, MQTT topics, state machine enhancements
- Device-specific files for ESP32 and ESP8266 variants

### paku-iot (Backend)
- `stack/postgres/edge_devices_schema.sql`: New database tables
- `stack/collector/collector.py`: Enhanced to handle status/config topics
- `compose/stack.prod.yaml`: (No changes needed - collector auto-subscribes)

## Deployment

All changes have been deployed to production:
- Database schema applied
- Collector rebuilt and restarted
- ESP devices updated and running

## Testing

Verified on production system:
- Edge device status updates flowing to database
- Edge device configurations being captured
- Sensor data collection unaffected
- All MQTT topics properly routed

---

**Date:** 2025-12-13
**Status:** Phase 3 Complete - All systems operational
