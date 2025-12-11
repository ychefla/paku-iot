# Grafana Dashboard Updates Summary

**Date:** 2025-12-11  
**Purpose:** Comprehensive update to Grafana dashboards for better temperature monitoring and EcoFlow data visualization

## Changes Made

### 1. Temperature and Humidity Overview Dashboard (formerly "Ruuvi Overview")

**File:** `stack/grafana/dashboards/ruuvi_overview.json`  
**UID:** `paku-ruuvi`  
**Changes:**
- ✅ Renamed from "Ruuvi Overview" to "Temperature and Humidity Overview"
- ✅ Added 4 EcoFlow temperature data sources to Temperature panel:
  - Inverter Temperature (`raw_data->'inv'->>'outTemp'`)
  - BMS Temperature (`raw_data->'bms'->>'temp'`)
  - Maximum Cell Temperature (`raw_data->'bms'->>'maxCellTemp'`)
  - Minimum Cell Temperature (`raw_data->'bms'->>'minCellTemp'`)
- ✅ Created policy document (`docs/dashboard_temperature_policy.md`) to ensure all future temperature sources are added

**Impact:** Users now see all temperature data from both Ruuvi sensors and EcoFlow power station in one unified view.

### 2. EcoFlow API Data Dashboard (NEW)

**File:** `stack/grafana/dashboards/ecoflow_api_data.json`  
**UID:** `ecoflow-api-data`  
**Type:** New dashboard created from scratch  
**Panels:** 22 panels organized in 7 rows

**Layout:**
- **Row 1:** Battery status (Level, Time, Battery Temp, Inverter Temp) - 4 gauges
- **Row 2:** Power flow (Input, Output, Solar, AC In/Out) - 5 stats
- **Row 3:** DC/USB outputs (Car, USB-C 1&2, USB 1&2, QC USB 1) - 6 stats
- **Row 4:** Battery level and runtime history - 2 time series
- **Row 5:** Power flow charts (Input/Output, Net Power) - 2 time series
- **Row 6:** Solar and AC charts - 2 time series
- **Row 7:** System temperatures - 1 time series

**Purpose:** Shows ONLY REST API supported parameters (identified in analysis report). No zero-value panels.

### 3. EcoFlow Unified Dashboard (NEW)

**File:** `stack/grafana/dashboards/ecoflow_unified.json`  
**UID:** `ecoflow-unified`  
**Type:** New consolidated dashboard  
**Panels:** 15 panels organized in 6 rows

**Layout:**
- **Row 1:** At-a-glance status - 4 large gauges (Battery, Input, Output, Battery Temp)
- **Row 2:** Secondary stats - 6 stats (Runtime, Solar, AC In/Out, Inverter Temp, MPPT Temp)
- **Row 3:** Battery Level & Runtime History - 1 combined time series
- **Row 4:** Power Flow (Input, Output, Net) - 1 combined time series
- **Row 5:** Power Sources & Outputs breakdown - 2 time series (Solar/AC Input, AC/DC/USB Output)
- **Row 6:** System Temperatures - 1 time series

**Purpose:** 
- Combines best features from multiple existing dashboards
- Provides easy view of BOTH current status AND historical data
- Clean, focused layout without redundant panels
- Can replace existing dashboards in the future

### 4. Analysis Report (NEW)

**File:** `ECOFLOW_DASHBOARD_API_ANALYSIS.md`

**Contents:**
- Comprehensive analysis of "EcoFlow (Exporter Style)" dashboard
- Table showing which parameters work vs. show zero
- Explanation of why some parameters show zero (REST API vs MQTT differences)
- Complete list of available REST API parameters (18 confirmed)
- Recommended visualizations for each parameter
- Comparison of REST API vs MQTT data availability

**Key Finding:** 55% of parameters in Exporter Style dashboard show zero because they query fields not available in the REST API response.

## Dashboard Comparison

| Dashboard | File | Panels | Status | Purpose |
|-----------|------|--------|--------|---------|
| Temperature and Humidity Overview | `ruuvi_overview.json` | 5 | ✅ Updated | All temperature/humidity sensors |
| EcoFlow Power Station Overview | `ecoflow_overview.json` | 12 | 📌 Keep | Original overview |
| EcoFlow - Real-Time Overview | `ecoflow_comprehensive.json` | 8 | 📌 Keep | Simple real-time view |
| EcoFlow Real-Time | `ecoflow_realtime.json` | 7 | 📌 Keep | Minimal real-time |
| EcoFlow (Exporter Style) | `ecoflow_exporter_style.json` | 30 | ⚠️ Has issues | Many zero-value panels |
| **EcoFlow API Data** | `ecoflow_api_data.json` | 22 | ✨ New | All API-supported data |
| **EcoFlow Unified Dashboard** | `ecoflow_unified.json` | 15 | ✨ New | Best of all dashboards |

## Recommendations for Future

### Immediate Use
1. **Use "EcoFlow Unified Dashboard"** as the primary dashboard - it provides the best balance of current and historical data
2. **Use "EcoFlow API Data"** when you need detailed view of specific parameters
3. **Use "Temperature and Humidity Overview"** for all temperature monitoring

### Long-Term Cleanup (Optional)
Consider deprecating/removing redundant dashboards:
- Keep: Unified, API Data, Temperature and Humidity Overview
- Consider removing: Overview, Comprehensive, Realtime, Exporter Style (after user testing confirms Unified meets all needs)

## Documentation Created

1. **`docs/dashboard_temperature_policy.md`**
   - Policy requiring ALL temperature sources be added to Temperature and Humidity Overview
   - Step-by-step guide for adding new temperature sources
   - Query templates and best practices
   - Validation checklist

2. **`ECOFLOW_DASHBOARD_API_ANALYSIS.md`**
   - Complete analysis of Exporter Style dashboard issues
   - REST API vs MQTT comparison
   - Available parameters documentation
   - Visualization recommendations

## Technical Notes

### Temperature Data Access
EcoFlow temperatures are stored in `raw_data` JSONB column and must be divided by 10:
```sql
(raw_data->>'bmsMaster.temp')::numeric / 10.0  -- Battery temp in °C
(raw_data->>'inv.outTemp')::numeric / 10.0      -- Inverter temp in °C
(raw_data->>'mppt.mpptTemp')::numeric / 10.0    -- MPPT temp in °C
```

### Device Selection
All new dashboards include `$device_sn` template variable:
```sql
SELECT DISTINCT device_sn FROM ecoflow_measurements WHERE device_sn != '' ORDER BY device_sn
```

### Data Availability
- REST API provides 18 core parameters
- Parameters like voltage, current, cell details require MQTT (not currently implemented)
- All new dashboards use only REST API supported fields

## Testing Recommendations

1. **Verify Dashboard Loading**
   - Access Grafana and confirm all dashboards appear
   - Check that device selection dropdown works
   - Verify time range selector functions

2. **Validate Data Display**
   - Confirm temperature data appears from both Ruuvi and EcoFlow
   - Verify power metrics show realistic values
   - Check that historical charts display data

3. **User Acceptance**
   - Get user feedback on Unified Dashboard layout
   - Confirm it meets needs for "easy view of both current situation AND historical information"
   - Verify all important metrics are visible

## Migration Path

If users want to fully migrate to the new dashboards:

1. **Phase 1 (Current):** New dashboards available alongside existing ones
2. **Phase 2:** User testing and feedback on Unified Dashboard
3. **Phase 3:** Make Unified Dashboard the default/home dashboard
4. **Phase 4:** (Optional) Archive/remove redundant older dashboards

---

**Summary:** Successfully created comprehensive dashboard solution that addresses all requirements:
- ✅ All temperatures in one place with policy for future additions
- ✅ Analysis report identifying API limitations
- ✅ New dashboard with only API-supported parameters
- ✅ Unified dashboard combining best features with current + historical views
