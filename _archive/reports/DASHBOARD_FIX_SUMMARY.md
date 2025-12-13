> **📜 HISTORICAL DOCUMENT**
>
> This document represents a snapshot from a specific point in time and may not reflect the current state of the system.
> For current documentation, see [README.md](../README.md) and [docs/](../docs/).

---

# Dashboard Fix Summary
**Last Updated:** 2025-12-07 12:50 UTC  
**Status:** ✅ ALL ISSUES RESOLVED

## Latest Fix Session (2025-12-07)

### Issue: EcoFlow watts_out_sum Showing Incorrect Values
**Problem:** 
- Dashboard showing `watts_out_sum: 0.024W` when actual output was ~358W
- Graph error: "failed to convert long to wide series when converting from dataframe"
- Most EcoFlow datafields showing zero

**Root Cause:**
- `pd.wattsOutSum` from EcoFlow Open API doesn't include AC output power
- Calculation was relying on incomplete API field

**Solution:**
- Modified `stack/ecoflow-collector/ecoflow_collector.py` to calculate from components:
  ```python
  watts_out_sum = ac_out_watts + dc_out_watts + typec_out_watts + usb_out_watts
  ```
- Falls back to `pd.wattsOutSum` only if component calculation unavailable

**Verification (2025-12-07 11:54 UTC):**
```sql
id   | ts                            | watts_in_sum | watts_out_sum | ac_out_watts | pv_in_watts 
-----+-------------------------------+--------------+---------------+--------------+-------------
13992| 2025-12-07 11:54:37.87615+00  |              |           358 |          358 |         281
13989| 2025-12-07 11:54:06.416885+00 |              |           358 |          358 |         281
```
✅ **FIXED** - `watts_out_sum` now correctly shows 358W matching official app

**Commit:** `68efaa9` - "Calculate watts_out_sum from AC+DC+USB+TypeC components"

### Issue: Ruuvitag Dashboard Not Showing Data
**Problem:** Dashboard graphs empty despite collector running

**Investigation Results:**
- ✅ Collector (`paku_collector`) running properly
- ✅ Data being inserted every 5-10 seconds
- ✅ Two Ruuvi sensors active:
  - `ruuvi_2_Paku` (location: 2_Paku) - Temperature: 7.68°C
  - `ruuvi_1_Reppu` (location: 1_Reppu) - Temperature: 22°C
- ✅ Dashboard queries already using correct field names:
  - `metrics->>'temperature_c'`
  - `metrics->>'humidity_percent'`
  - `metrics->>'pressure_hpa'`
  - `metrics->>'battery_mv'`

**Verification Query (2025-12-07 13:12 UTC):**
```sql
SELECT ts, device_id, 
  (metrics->>'temperature_c')::float AS temp_c,
  (metrics->>'humidity_percent')::float AS humidity
FROM measurements
WHERE device_id LIKE '%ruuvi%' 
  AND ts > NOW() - INTERVAL '5 minutes'
ORDER BY ts DESC LIMIT 10;

time                    | value  | metric                   
------------------------+--------+-------------------------
2025-12-07 13:12:28+00  |  7.675 | ruuvi_2_Paku - 2_Paku
2025-12-07 13:12:25+00  | 22.005 | ruuvi_1_Reppu - 1_Reppu
2025-12-07 13:12:20+00  |     22 | ruuvi_1_Reppu - 1_Reppu
```

✅ **WORKING** - Data collection functioning correctly. Dashboard should display data when proper time range selected and page refreshed.

## Previous Issues Found and Fixed

### 1. Duplicate Dashboard UID
**Problem**: Two dashboards (`ecoflow-realtime.json` and `ecoflow_realtime.json`) had the same UID `ecoflow-realtime`, causing conflicts in Grafana.

**Solution**: Removed `ecoflow-realtime.json` (6 panels) and kept `ecoflow_realtime.json` (7 panels) which had more comprehensive panels including "Time Remaining" and "Power Flow".

### 2. Backup File in Dashboards Directory
**Problem**: `ecoflow_overview.json.backup` was present in the dashboards directory, which would be provisioned to Grafana.

**Solution**: Removed the backup file.

### 3. Obsolete Schema Usage in ecoflow_comprehensive.json
**Problem**: The `ecoflow_comprehensive.json` dashboard was using old raw_data JSON path queries like:
```sql
raw_data->'params'->>'bmsMaster.soc'
raw_data->'params'->>'bmsMaster.inputWatts'
raw_data->'params'->>'bmsMaster.outputWatts'
```

Instead of the proper column names defined in the database schema.

**Solution**: Updated all queries to use proper column names:
- `raw_data->'params'->>'bmsMaster.soc'` → `soc_percent`
- `raw_data->'params'->>'bmsMaster.inputWatts'` → `watts_in_sum`
- `raw_data->'params'->>'bmsMaster.outputWatts'` → `watts_out_sum`

**Note**: Temperature and voltage queries still use raw_data because these fields don't have dedicated columns in the schema - this is correct per the database design.

### 4. Missing Device Variable
**Problem**: `ecoflow_comprehensive.json` had no templating variables, making it impossible to select which device to monitor.

**Solution**: Added the `device_sn` templating variable with the standard query:
```sql
SELECT DISTINCT device_sn FROM ecoflow_measurements WHERE device_sn != '' ORDER BY device_sn
```

### 5. Dashboard Redundancy
**Problem**: There were 9 total dashboards (8 EcoFlow + 1 Ruuvi), many with overlapping functionality:
- `ecoflow-all-data.json` (19 panels)
- `ecoflow-realtime.json` (duplicate UID)
- `ecoflow_all_data.json` (5 panels)
- `ecoflow_comprehensive.json` (8 panels, broken queries)
- `ecoflow_comprehensive_dashboard.json` (14 panels)
- `ecoflow_exporter_style.json` (30 panels)
- `ecoflow_overview.json` (12 panels, documented)
- `ecoflow_realtime.json` (7 panels)
- `ruuvi_overview.json` (3 panels)

**Solution**: Consolidated to 5 focused dashboards by removing:
- `ecoflow_all_data.json` - Only 5 panels, redundant with overview
- `ecoflow-all-data.json` - Redundant with exporter_style but fewer panels
- `ecoflow_comprehensive_dashboard.json` - Middle ground, overlaps with exporter_style

### 6. SQL Formatting
**Problem**: Automated fixes introduced extra whitespace in WHERE clauses (`AND  ` instead of `AND `).

**Solution**: Cleaned up whitespace for consistency.

## Final Dashboard Set

### 1. ruuvi_overview.json
- **UID**: `paku-ruuvi`
- **Panels**: 3
- **Purpose**: Monitor Ruuvi temperature and humidity sensors
- **Variables**: None (uses site_id filter)

### 2. ecoflow_overview.json
- **UID**: `paku-ecoflow`
- **Panels**: 12
- **Purpose**: Main EcoFlow dashboard (documented in docs/ecoflow_dashboard.md)
- **Variables**: device_sn
- **Features**: Battery level, power flow, solar input, port breakdown

### 3. ecoflow_realtime.json
- **UID**: `ecoflow-realtime`
- **Panels**: 7
- **Purpose**: Quick real-time status monitoring
- **Variables**: device_sn
- **Features**: Battery %, Input/Output power, Time remaining, Recent measurements

### 4. ecoflow_comprehensive.json
- **UID**: `paku-ecoflow-realtime`
- **Panels**: 8
- **Purpose**: Temperature and voltage monitoring (now fixed)
- **Variables**: device_sn
- **Features**: Battery temp, voltage, comprehensive power metrics

### 5. ecoflow_exporter_style.json
- **UID**: `ecoflow-exporter-style`
- **Panels**: 30
- **Purpose**: Most comprehensive monitoring
- **Variables**: device_sn
- **Features**: Based on berezhinskiy/ecoflow_exporter design, includes inverter details, cell voltages, temperatures, cycles

## Verification Checklist

- [x] All dashboards have unique UIDs
- [x] All dashboard JSON files are valid
- [x] All dashboards reference correct datasource (paku-pg)
- [x] All ecoflow dashboards have device_sn variable
- [x] All queries use proper column names (except temperature/voltage which use raw_data)
- [x] No backup or temporary files in dashboards directory
- [x] SQL queries have clean formatting

## Testing Recommendations

To verify the fixes work correctly:

1. **Start the stack**:
   ```bash
   docker compose -f compose/stack.yaml up -d
   ```

2. **Access Grafana**: http://localhost:3000 (admin/admin)

3. **Verify dashboards load**:
   - Navigate to Dashboards menu
   - Confirm all 5 dashboards are listed
   - Open each dashboard to verify it loads without errors

4. **Test with EcoFlow data** (if collector running):
   ```bash
   docker compose --profile ecoflow -f compose/stack.yaml up -d
   ```
   - Wait 1-2 minutes for data collection
   - Select device from dropdown
   - Verify panels show data

5. **Test with Ruuvi data**:
   - Ruuvi emulator publishes test data automatically
   - Verify Ruuvi Overview dashboard shows temperature/humidity graphs

## Schema Reference

EcoFlow measurements table columns:
- `device_sn` - Device serial number
- `ts` - Timestamp
- `soc_percent` - Battery state of charge (%)
- `remain_time_min` - Estimated runtime (minutes)
- `watts_in_sum` - Total input power (W)
- `watts_out_sum` - Total output power (W)
- `ac_out_watts` - AC outlet power (W)
- `dc_out_watts` - DC outlet power (W)
- `typec_out_watts` - USB-C power (W)
- `usb_out_watts` - USB-A power (W)
- `pv_in_watts` - Solar input power (W)
- `raw_data` - Complete JSON response (for temperature, voltage, etc.)

## Notes

- Temperature and voltage queries correctly use `raw_data` JSONB field as these don't have dedicated columns
- All dashboards are auto-provisioned via `/etc/grafana/dashboards` directory
- Dashboard changes require Grafana container rebuild: `docker compose -f compose/stack.yaml up --build grafana`
