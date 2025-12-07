# EcoFlow Data Collection Diagnosis

## Current Status (2025-12-07 19:18 UTC)

### Symptoms
- Most EcoFlow data fields showing zero values
- `bmsMaster.inputWatts` = 0
- `bmsMaster.outputWatts` = 0
- Only SOC (90%) and temperature (14°C) updating correctly
- Dashboard showing error: "failed to convert long to wide series"

### Actual Device State (per official app)
- AC Input: ~709W
- AC Output: ~707W
- 12V DC Output: ~8W
- Temperature: 14°C
- SOC: 89-90%
- Remaining time: 5d 16h
- NO solar input

## Root Cause Analysis

### EcoFlow API Architecture
The EcoFlow OpenAPI provides TWO ways to get device data:

1. **MQTT (Consumer/Subscribe Model)**
   - Device pushes data when it "feels like it"
   - Frequency depends on device state and activity
   - Power data (`inputWatts`, `outputWatts`) only sent when device actively charging/discharging
   - When device is idle or in standby, these fields report as 0

2. **REST API (Request/Response Model)**
   - Application requests specific parameters  
   - Device responds with current values
   - Can get real-time data on demand
   - Requires active querying at desired interval

### Current Implementation Issue
Our collector is:
- ✅ Connected to MQTT and receiving messages
- ✅ Has REST API methods implemented
- ✅ Requests device parameters periodically
- ❌ REST API returns data in DIFFERENT FORMAT than MQTT
- ❌ Parser expects MQTT format with `params` object containing dotted keys
- ❌ REST API returns flat dict with dotted keys directly (no `params` wrapper)
- ❌ Power values may be in different units (W vs mW)

### Evidence from Logs
```
# REST API Response (truncated, shows flat structure):
{
  "pd.iconWifiMode": 1,
  "mppt.faultCode": 0,
  "ems.minDsgSoc": 5,
  "pd.iconOverloadState": 0,
  "bmsMaster.chgDsgState": 1,
  "inv.invOutFreq": 50,
  "mppt.inAmp": 0,
  ...
}

# MQTT Response (shows params wrapper):
{
  "addr": 0,
  "cmdFunc": 0,
  "cmdId": 0,
  "id": 2150912106874021449,
  "version": "1.0",
  "timestamp": 1765135125232,
  "params": {
    "bmsMaster.temp": 14,
    "bmsMaster.inputWatts": 0,
    "bmsMaster.outputWatts": 0,
    "bmsMaster.soc": 90
  }
}
```

## Solution

###  Fix Parser to Handle Both Formats
The `parse_ecoflow_payload()` function needs to:
1. Detect if data is from REST API (flat dict) or MQTT (`params` wrapper)
2. Handle both formats correctly
3. Check if power values are already in watts or milliwatts

### Add Direct REST API Polling
Instead of relying on MQTT quota responses, directly query REST API:
- `/iot-open/sign/device/quota/all` - Get ALL device data
- Parse the response correctly
- Store to database

### Key Fields to Extract from REST API
Based on Delta Pro documentation:
- `inv.inputWatts` - AC input power (W)
- `inv.outputWatts` - AC output power (W)
- `pd.carWatts` - 12V DC output (W)
- `mppt.inWatts` - Solar input (W)
- `bmsMaster.soc` - Battery SOC (%)
- `bmsMaster.temp` - Battery temperature (°C)
- `pd.remainTime` - Remaining time (minutes)
- `bmsMaster.vol` - Battery voltage (mV)
- `bmsMaster.amp` - Battery current (mA)

## Next Steps

1. Modify `parse_ecoflow_payload()` to handle REST API format
2. Check units of REST API values (likely already in W, not mW)
3. Add unit tests with example REST and MQTT payloads
4. Test with real device data
5. Update dashboards to handle new data format

