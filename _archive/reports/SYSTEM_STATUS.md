> **📜 HISTORICAL DOCUMENT**
>
> This document represents a snapshot from a specific point in time and may not reflect the current state of the system.
> For current documentation, see [README.md](../README.md) and [docs/](../docs/).

---

# Paku IoT System Status

**Last Updated:** 2025-12-07 15:50 UTC  
**Overall Status:** ✅ **FULLY OPERATIONAL**

## Service Health

All services running and healthy on server `static.107.192.27.37.clients.your-server.de`:

| Service | Container Name | Status | Uptime |
|---------|----------------|--------|--------|
| PostgreSQL | paku_postgres | ✅ Healthy | 3+ hours |
| Mosquitto MQTT | paku_mosquitto | ✅ Healthy | 3+ hours |
| Grafana | paku_grafana | ✅ Healthy | 3+ hours |
| Ruuvi Collector | paku_collector | ✅ Running | 3+ hours |
| EcoFlow Collector | paku_ecoflow_collector | ✅ Running | 3+ hours |

## Data Collection Status

### EcoFlow (Delta Pro)
- ✅ Connected to EcoFlow Open API MQTT broker
- ✅ Receiving real-time updates every ~10 seconds
- ✅ Successfully storing data in PostgreSQL
- 📊 **Current Status** (as of 15:49 UTC):
  - Battery: 88% SOC
  - Solar Input: 281W
  - AC Output: ~1W (idle)
  - Temperature: 14°C

**Recent Data Sample:**
```
id    | timestamp                     | soc | watts_in | watts_out | ac_out | pv_in
15335 | 2025-12-07 15:49:13.558342+00 | 88  | 1        | 1         | 1      | 281
```

### Ruuvi Sensors
- ✅ Two sensors active and reporting
- ✅ Updates every ~5 seconds
- ✅ Successfully storing data in PostgreSQL

**Active Sensors:**
1. **ruuvi_1_Reppu** (Location: 1_Reppu)
   - Temperature: 22.25°C
   - Humidity: 38.78%

2. **ruuvi_2_Paku** (Location: 2_Paku)
   - Temperature: 7.36°C
   - Humidity: 71.30%

## Grafana Dashboards

All 5 dashboards deployed and accessible at `http://localhost:3000`:

### 1. Ruuvi Overview (`paku-ruuvi`)
- **Panels:** 3
- **Purpose:** Temperature & humidity monitoring
- **Status:** ✅ Working - Data flowing from both sensors

### 2. EcoFlow Overview (`paku-ecoflow`)
- **Panels:** 12
- **Purpose:** Main EcoFlow dashboard
- **Features:** Battery level, power flow, solar input, port breakdown
- **Status:** ✅ Working - Real-time data from Delta Pro

### 3. EcoFlow Realtime (`ecoflow-realtime`)
- **Panels:** 7
- **Purpose:** Quick status monitoring
- **Features:** Battery %, Input/Output power, Time remaining
- **Status:** ✅ Working

### 4. EcoFlow Comprehensive (`paku-ecoflow-realtime`)
- **Panels:** 8
- **Purpose:** Temperature & voltage monitoring
- **Features:** Battery temp, voltage, comprehensive power metrics
- **Status:** ✅ Working

### 5. EcoFlow Exporter Style (`ecoflow-exporter-style`)
- **Panels:** 30
- **Purpose:** Most comprehensive monitoring
- **Features:** Inverter details, cell voltages, temperatures, cycles
- **Status:** ✅ Working

## Recent Fixes Applied

### Issue 1: EcoFlow watts_out_sum Calculation
**Fixed:** 2025-12-07 11:54 UTC (Commit: 68efaa9)

Changed calculation from using incomplete API field `pd.wattsOutSum` to component-based calculation:
```python
watts_out_sum = ac_out_watts + dc_out_watts + typec_out_watts + usb_out_watts
```

**Result:** Accurate power output readings matching official EcoFlow app.

### Issue 2: Dashboard Consolidation
**Fixed:** 2025-12-07 13:00 UTC

- Removed 4 redundant dashboards
- Fixed duplicate UID conflicts
- Updated all queries to use proper column names
- Added device selection variables where missing

### Issue 3: Unit Conversions
**Fixed:** 2025-12-07 12:00 UTC (Commit: f4617c0)

Applied proper unit conversions for all EcoFlow power values from the Open API, ensuring accurate Watt readings across all fields.

## Database Schema

### ecoflow_measurements
Primary columns for EcoFlow Delta Pro data:
- `device_sn` - Device serial number
- `ts` - Timestamp with timezone
- `soc_percent` - Battery state of charge (0-100)
- `remain_time_min` - Estimated runtime (minutes)
- `watts_in_sum` - Total input power (W)
- `watts_out_sum` - Total output power (W) - **calculated from components**
- `ac_out_watts` - AC outlet power (W)
- `dc_out_watts` - DC outlet power (W)
- `typec_out_watts` - USB-C power (W)
- `usb_out_watts` - USB-A power (W)
- `pv_in_watts` - Solar/PV input power (W)
- `bms_voltage_mv` - Battery voltage (millivolts)
- `bms_amp_ma` - Battery current (milliamps)
- `bms_temp_c` - Battery temperature (Celsius)
- `bms_cycles` - Battery charge cycles
- `bms_soh_percent` - Battery state of health (%)
- `raw_data` - Complete JSON response (JSONB)

### measurements
Table for Ruuvi and other sensor data:
- `device_id` - Sensor identifier
- `ts` - Timestamp with timezone
- `metrics` - JSONB with sensor readings:
  - `temperature_c` - Temperature in Celsius
  - `humidity_percent` - Relative humidity %
  - `pressure_hpa` - Air pressure in hPa
  - `battery_mv` - Battery voltage in mV

## API Integration

### EcoFlow Open API
- **Endpoint:** EU API (https://api-e.ecoflow.com)
- **Method:** MQTT over TLS
- **Authentication:** OAuth2 with access/secret keys
- **Data Source:** Real-time quota messages from device
- **Update Frequency:** ~10 seconds
- **API Documentation:** https://developer-eu.ecoflow.com/us/document/deltapro

### MQTT Topics Subscribed
- `/open/{app_key}/{device_sn}/quota` - Real-time device status updates

## Monitoring Recommendations

### For EcoFlow
1. Monitor the `watts_out_sum` vs component fields to ensure calculation accuracy
2. Check battery temperature during high load/charge cycles
3. Review SOC trends for battery health
4. Monitor solar input for system efficiency

### For Ruuvi
1. Set up alerts for temperature thresholds
2. Monitor humidity levels for environmental control
3. Track battery levels for maintenance scheduling

## Troubleshooting

### If EcoFlow data stops updating:
1. Check collector logs: `docker compose -f compose/stack.yaml logs -f ecoflow-collector`
2. Verify MQTT connection in logs
3. Restart collector: `docker compose -f compose/stack.yaml restart ecoflow-collector`
4. Check API credentials in environment variables

### If Ruuvi data stops updating:
1. Check collector logs: `docker compose -f compose/stack.yaml logs -f collector`
2. Verify MQTT broker connectivity
3. Check sensor battery levels
4. Restart collector: `docker compose -f compose/stack.yaml restart collector`

### If dashboards don't show data:
1. Verify time range selection in Grafana (e.g., "Last 15 minutes")
2. Check datasource connection in Grafana settings
3. Verify PostgreSQL is accepting connections
4. Run test query directly in PostgreSQL

## Access Information

- **Grafana URL:** http://localhost:3000 (or server IP:3000)
- **Default Credentials:** admin/admin (change on first login)
- **PostgreSQL:** localhost:5432 (internal to Docker network)
- **MQTT Broker:** localhost:1883 (internal to Docker network)

## Git Repository Status

- **Branch:** main
- **Latest Commit:** 60c63ba - "Update DASHBOARD_FIX_SUMMARY with latest fixes"
- **Working Tree:** Clean
- **Remote:** Up to date with origin/main

## System Requirements Met

✅ Real-time EcoFlow monitoring via Open API  
✅ Ruuvi sensor data collection  
✅ PostgreSQL time-series data storage  
✅ Grafana visualization dashboards  
✅ MQTT message broker for local sensors  
✅ Docker Compose orchestration  
✅ Automated dashboard provisioning  

## Next Steps (Optional Enhancements)

1. **Alerting:** Configure Grafana alerts for:
   - Low battery warnings (< 20%)
   - High temperature alerts (> 40°C)
   - Abnormal power consumption patterns

2. **Historical Analysis:**
   - Set up retention policies for old data
   - Create monthly summary reports
   - Track solar generation efficiency over time

3. **Additional Integrations:**
   - Add more Ruuvi sensors
   - Integrate other EcoFlow devices
   - Add weather data correlation

4. **Performance Optimization:**
   - Implement data aggregation for long-term storage
   - Add database indexes for common queries
   - Set up automated backup procedures

## Support Documentation

- **Main README:** `/workspaces/paku/paku-iot/README.md`
- **Dashboard Fix Summary:** `/workspaces/paku/paku-iot/DASHBOARD_FIX_SUMMARY.md`
- **EcoFlow Integration:** `/workspaces/paku/paku-iot/docs/ecoflow_integration.md`
- **API Documentation:** https://developer-eu.ecoflow.com/

---

**System is fully operational and ready for production use.** 🎉
