> **📜 HISTORICAL DOCUMENT**
>
> This document represents a snapshot from a specific point in time and may not reflect the current state of the system.
> For current documentation, see [README.md](../README.md) and [docs/](../docs/).

---

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

_Updated 2026-08-05 to reflect current state._

### Active Dashboards — yhteenveto

| Dashboard | File | UID | Paneelit | Tarkoitus |
|-----------|------|-----|----------|-----------|
| Temperature and Humidity Overview | `ruuvi_overview.json` | `paku-ruuvi` | 5 | Ruuvi-anturit + EcoFlow lämpötilat |
| **EcoFlow — Täydellinen** | `ecoflow_full.json` | `ecoflow-full` | 26 | Kaikki EcoFlow data + historia |
| **EcoFlow — Yleiskatsaus** | `ecoflow_overview_v2.json` | `ecoflow-overview-v2` | 14 | Tärkeimmät mittarit, 6 h näkymä |
| Edge Devices Overview | `edge_devices.json` | `edge-devices` | 13 | ESP32-laitteet: tila, FW, RSSI |
| Hydronic Heater Overview | `heater_overview.json` | `paku-heater` | 8 | Vedenlämmitin |
| OTA Update Monitoring | `ota_monitoring.json` | `ota-monitoring` | 7 | OTA-päivitysten seuranta |

---

### Tarkka metriikat per dashboard

#### Temperature and Humidity Overview (`ruuvi_overview.json`)

| Paneeli | Tyyppi | Mittaussuureet |
|---------|--------|----------------|
| Temperature (°C) | time series | `temperature_c` per laite+sijainti (Ruuvi) |
| Humidity (%) | time series | `humidity_percent` per laite+sijainti (Ruuvi) |
| Dew Point (°C) | time series | laskettu: Magnus-kaava (Ruuvi temp + kosteus) |
| Absolute Humidity (g/m³) | time series | laskettu: g/m³ (Ruuvi temp + kosteus) |
| EcoFlow Temperatures (°C) | time series | `inv_out_temp`, `bms_temp`, `bms_max_cell_temp`, `bms_min_cell_temp` |

---

#### EcoFlow — Täydellinen (`ecoflow_full.json`)

| Paneeli | Tyyppi | Mittaussuureet |
|---------|--------|----------------|
| Online | stat | `online` |
| Akku | stat | `soc_percent` (%) |
| Sisään | stat | `watts_in_sum` (W) |
| Ulos | stat | `watts_out_sum` (W) |
| Netto | stat | `watts_in_sum - watts_out_sum` (W) |
| Solar | stat | `mppt_in_watts` (W) |
| AC Sisään | stat | `ac_in_watts` (W) |
| Jäljellä | stat | `remain_time` (h) |
| Akku °C | stat | `bms_temp` (°C) |
| Akkutaso & Aika jäljellä | time series | `soc_percent`, `remain_time` |
| Tehovirta: Sisään / Ulos / Netto | time series | `watts_in_sum`, `watts_out_sum`, netto |
| Tehon lähteet: Solar & AC | time series | `mppt_in_watts`, `ac_in_watts` |
| Lähdöt: AC & DC | time series | `ac_out_watts`, `dc_out_watts`, `typec_out_watts`, `usb_out_watts` |
| Lämpötilat | time series | `bms_temp`, `inv_out_temp`, `mppt_temp`, `bms_min_cell_temp`, `bms_max_cell_temp` |
| Jännitteet | time series | `ac_in_vol`, `inv_out_vol`, `bms_vol` |
| Virta | time series | `ac_in_amp`, `inv_out_amp`, `bms_amp` |
| Akkujännitteet | time series | `bms_vol`, `bms_min_cell_vol`, `bms_max_cell_vol` |
| USB Lähdöt | time series | `usb_out_watts`, `typec_out_watts` |
| Lataussyklit | stat | `bms_cycles` |
| Kapasiteetti | stat | `bms_design_cap` (Wh) |
| Jäljellä kap. | stat | `bms_remain_cap` (Wh) |
| BMS Virta | stat | `bms_amp` (A) |
| Cell Min °C | stat | `bms_min_cell_temp` (°C) |
| Cell Max °C | stat | `bms_max_cell_temp` (°C) |
| Cell Min V | stat | `bms_min_cell_vol` (V) |
| Cell Max V | stat | `bms_max_cell_vol` (V) |

---

#### EcoFlow — Yleiskatsaus (`ecoflow_overview_v2.json`)

| Paneeli | Tyyppi | Mittaussuureet |
|---------|--------|----------------|
| Online | stat | `online` |
| Akku | stat | `soc_percent` (%) |
| Sisään | stat | `watts_in_sum` (W) |
| Ulos | stat | `watts_out_sum` (W) |
| Solar | stat | `mppt_in_watts` (W) |
| Jäljellä | stat | `remain_time` (h) |
| Akku °C | stat | `bms_temp` (°C) |
| Invertteri °C | stat | `inv_out_temp` (°C) |
| Netto | stat | `watts_in_sum - watts_out_sum` (W) |
| Akkutaso (%) | time series | `soc_percent` |
| Tehovirta | time series | `watts_in_sum`, `watts_out_sum`, netto |
| Tehon lähteet | time series | `mppt_in_watts`, `ac_in_watts` |
| Lähdöt | time series | `ac_out_watts`, `dc_out_watts`, `typec_out_watts`, `usb_out_watts` |
| Lämpötilat | time series | `bms_temp`, `inv_out_temp`, `mppt_temp` |

---

#### Edge Devices Overview (`edge_devices.json`)

| Paneeli | Tyyppi | Mittaussuureet |
|---------|--------|----------------|
| Total / Online / Up-to-Date Devices | stat | laitteiden lukumäärä |
| Latest Firmware | stat | uusin firmware-versio |
| Status Updates (Last Hour) | stat | viestimäärä tunnissa |
| Device Status Overview | table | device_id, model, current_fw, latest_fw, status, last_seen, last_status, WiFi (dBm), uptime, state, update_status, registered |
| Status Update Rate | time series | viestejä / 5 min per laite |
| WiFi Signal Strength | time series | `signal_strength_dbm` (dBm) per laite |
| Recent Status Updates | table | ts, device, state, WiFi (dBm), uptime, fw_version, heater_status, active_scenario |
| Device Update History | table | started_at, device, target_version, status, duration, error_message |
| Device Uptime Trends | time series | `uptime_seconds / 3600` (h) per laite |
| Current Device States | stat | state + active_scenario per laite |
| Device Uptime | stat | uptime-aika muotoiltuna per laite |

---

#### Hydronic Heater Overview (`heater_overview.json`)

| Paneeli | Tyyppi | Mittaussuureet |
|---------|--------|----------------|
| Heater State | stat | `heater_state` (Off/Starting/Warming/Running/ShuttingDown/Cooling) |
| Safety | stat | `safety_ok` |
| Battery | stat | `battery_v` (V) |
| Coolant Temperature | gauge | `coolant_temp_c` (°C) |
| Flow Rate | gauge | `flow_lpm` (L/min) |
| Coolant Temperature History | time series | `coolant_temp_c`, `core_temp` |
| Battery Voltage & Flow Rate | time series | `battery_v`, `flow_lpm` |
| Heater State History | state-timeline | `heater_state` |

---

#### OTA Update Monitoring (`ota_monitoring.json`)

| Paneeli | Tyyppi | Mittaussuureet |
|---------|--------|----------------|
| Total Devices | stat | laitteiden lukumäärä |
| Latest Firmware | stat | uusin versio |
| Devices Up-to-Date | stat | ajan tasalla olevien laitteiden määrä |
| Active Updates | stat | käynnissä olevat päivitykset |
| Device Status & Update Progress | table | device_id, model, current_version, update_progress, target_version, online, last_seen, last_update, status |
| Recent Updates (Last 20) | table | started_at, device_id, model, from_version, to_version, status, duration |

---

### EcoFlow-mittareiden vertailu: Täydellinen vs Yleiskatsaus

| Mittari | Täydellinen | Yleiskatsaus |
|---------|:-----------:|:------------:|
| online | stat | stat |
| soc_percent | stat + ts | stat + ts |
| watts_in_sum | stat + ts | stat + ts |
| watts_out_sum | stat + ts | stat + ts |
| netto (in−out) | stat + ts | stat + ts |
| mppt_in_watts (Solar) | stat + ts | stat + ts |
| ac_in_watts | stat + ts | ts |
| remain_time | stat + ts | stat |
| bms_temp | stat + ts | stat + ts |
| inv_out_temp | ts | stat |
| mppt_temp | ts | ts |
| bms_min/max_cell_temp | ts + stat | — |
| ac_in_vol / inv_out_vol / bms_vol | ts | — |
| ac_in_amp / inv_out_amp / bms_amp | ts + stat | — |
| bms_min/max_cell_vol | ts + stat | — |
| usb_out_watts / typec_out_watts | ts + ts (USB) | ts |
| ac_out_watts / dc_out_watts | ts | ts |
| bms_cycles | stat | — |
| bms_design_cap / remain_cap | stat | — |

---

### Legacy / Redundant EcoFlow Dashboards (poistoehdokkaat)

| Dashboard | File | Paneelit | Huomio |
|-----------|------|----------|--------|
| EcoFlow Power Station Overview | `ecoflow_overview.json` | 12 | Korvattu uusilla |
| EcoFlow - Real-Time Overview | `ecoflow_comprehensive.json` | 8 | Korvattu uusilla |
| EcoFlow Real-Time | `ecoflow_realtime.json` | 7 | Korvattu uusilla |
| EcoFlow (Exporter Style) | `ecoflow_exporter_style.json` | 30 | 55 % nollapaneeleita, korvattu |
| EcoFlow API Data | `ecoflow_api_data.json` | 22 | Korvattu uusilla |
| EcoFlow Unified Dashboard | `ecoflow_unified.json` | 15 | Korvattu uusilla |

## Recommendations for Future

### Immediate Use
1. **EcoFlow — Täydellinen** (`ecoflow_full.json`) — ensisijainen EcoFlow-dashboard, kaikki historia
2. **EcoFlow — Yleiskatsaus** (`ecoflow_overview_v2.json`) — nopea tilannekuva
3. **Temperature and Humidity Overview** — kaikki lämpötila/kosteus-seuranta

### Long-Term Cleanup
Poista 6 legacy-dashboardia `stack/grafana/dashboards/`:
- `ecoflow_overview.json`
- `ecoflow_comprehensive.json`
- `ecoflow_realtime.json`
- `ecoflow_exporter_style.json`
- `ecoflow_api_data.json`
- `ecoflow_unified.json`

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
