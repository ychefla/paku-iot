# EcoFlow Dashboard and API Analysis Report

**Generated:** 2025-12-11  
**Dashboard Analyzed:** EcoFlow (Exporter Style)  
**Purpose:** Analyze parameters shown on dashboard vs. available from EcoFlow API

## Executive Summary

The "EcoFlow (Exporter Style)" dashboard contains 30 panels displaying various power station metrics. Analysis reveals:

- **Dashboard Parameters:** 31 unique fields queried
- **API Supported Parameters:** 18 confirmed fields actively collected
- **Status:** Many dashboard parameters use incorrect API paths (bms.* vs bmsMaster.*)
- **Issue:** Dashboard queries fields not returned by EcoFlow REST API, resulting in zero values

## Part 1: Dashboard Parameters vs API Support

This table lists all parameters displayed on the "EcoFlow (Exporter Style)" dashboard and their API support status.

| Panel # | Panel Title | Parameter Queried | API Support | Status | Notes |
|---------|-------------|-------------------|-------------|--------|-------|
| 0 | Online Status | timestamp check | ✅ Supported | Working | Checks recent data |
| 1 | Inverter IN Watts | `watts_in_sum` | ✅ Supported | Working | From `pd.wattsInSum` |
| 2 | Inverter IN Volts | `inv.acInVol`, `inv.invInVol` | ❌ Not Available | Zero | Not in REST API response |
| 3 | Inverter IN Current | `inv.acInAmp`, `inv.invInAmp` | ❌ Not Available | Zero | Not in REST API response |
| 4 | Charging Remaining Time | `remain_time_min`, `watts_in_sum` | ✅ Supported | Working | From `pd.remainTime` |
| 5 | Full Capacity | `bms.fullCap`, `bms_bmsStatus.fullCap` | ❌ Not Available | Zero | Not in REST API response |
| 6 | BMS Current | `bms.amp`, `bms_bmsStatus.amp` | ❌ Not Available | Zero | Not in REST API response |
| 7 | Battery Volts | `bms.vol`, `bms_bmsStatus.vol` | ❌ Not Available | Zero | Not in REST API response |
| 8 | MIN Cell Volts | `bms.minCellVol`, `bms_bmsStatus.minCellVol` | ❌ Not Available | Zero | Not in REST API response |
| 9 | MAX Cell Volts | `bms.maxCellVol`, `bms_bmsStatus.maxCellVol` | ❌ Not Available | Zero | Not in REST API response |
| 10 | Battery Level (SOC) | `soc_percent` | ✅ Supported | Working | From `bmsMaster.soc` |
| 11 | Inverter OUT Watts | `watts_out_sum` | ✅ Supported | Working | From `pd.wattsOutSum` |
| 12 | Inverter OUT Volts | `inv.invOutVol` | ❌ Not Available | Zero | Not in REST API response |
| 13 | Inverter OUT Current | `inv.invOutAmp` | ❌ Not Available | Zero | Not in REST API response |
| 14 | Discharging Remaining Time | `remain_time_min`, `watts_out_sum` | ✅ Supported | Working | From `pd.remainTime` |
| 15 | Remain Capacity | `bms.remainCap`, `bms_bmsStatus.remainCap` | ❌ Not Available | Zero | Not in REST API response |
| 16 | Battery Cycles | `bms.cycles`, `bms_bmsStatus.cycles` | ❌ Not Available | Zero | Not in REST API response |
| 17 | Inverter Temp | `inv.outTemp` | ✅ Supported | Working | From `inv.outTemp` |
| 18 | MIN Cell Temp | `bms.minCellTemp`, `bms_bmsStatus.minCellTemp` | ⚠️ Path Issue | May work | Should use `bmsMaster.minCellTemp` |
| 19 | MAX Cell Temp | `bms.maxCellTemp`, `bms_bmsStatus.maxCellTemp` | ⚠️ Path Issue | May work | Should use `bmsMaster.maxCellTemp` |
| 20 | Charge/Discharge Status | `bms.amp`, `bms_bmsStatus.amp` | ❌ Not Available | Zero | Not in REST API response |
| 21 | Battery Level | `soc_percent` | ✅ Supported | Working | From `bmsMaster.soc` |
| 22 | I/O Watts | `watts_in_sum`, `watts_out_sum` | ✅ Supported | Working | From `pd.*` fields |
| 23 | Remaining Time | `remain_time_min` | ✅ Supported | Working | From `pd.remainTime` |
| 24 | I/O Volts | `inv.invOutVol`, `inv.acInVol` | ❌ Not Available | Zero | Not in REST API response |
| 25 | Temperature | `inv.outTemp`, `bms.temp`, etc. | ✅/⚠️ Mixed | Partial | `inv.outTemp` works, bms paths may need correction |
| 26 | Current | `bms.amp`, `inv.invOutAmp`, `inv.acInAmp` | ❌ Not Available | Zero | Not in REST API response |
| 27 | USB Output | USB/TypeC fields | ✅ Supported | Working | From `pd.usb*` and `pd.typec*` |
| 28 | Battery Volts | `bms.vol`, `bms.minCellVol`, etc. | ❌ Not Available | Zero | Not in REST API response |
| 29 | Solar Power | Solar fields | ✅ Supported | Working | From `mppt.inWatts` |

### Summary Statistics

- **Total Parameters:** 31 unique fields
- **✅ Fully Supported:** 11 fields (35%)
- **⚠️ Path Issues:** 3 fields (10%) - may work with path correction
- **❌ Not Available:** 17 fields (55%)

### Why Some Parameters Show Zero

The EcoFlow REST API (`/iot-open/sign/device/quota/all`) returns a **limited subset** of data compared to the MQTT stream. Many voltage, current, and detailed battery metrics are:

1. **Not included in REST API response** - The REST API focuses on high-level metrics
2. **Only available via MQTT** - Would require MQTT integration to access
3. **Using incorrect paths** - Some queries use `bms.*` when API returns `bmsMaster.*`

## Part 2: Available API Parameters

This table lists all parameters confirmed to be available from the EcoFlow REST API (based on current collector implementation).

| Category | Parameter | API Field Name | Unit | Data Type | Visualization Suggestion |
|----------|-----------|----------------|------|-----------|-------------------------|
| **Battery** | State of Charge | `bmsMaster.soc` | % | integer | Gauge (0-100%), Time Series |
| **Battery** | Temperature | `bmsMaster.temp` | °C | integer/10 | Gauge, Time Series with thresholds |
| **Power Input** | Total Input Power | `pd.wattsInSum` | W | integer | Gauge, Time Series |
| **Power Output** | Total Output Power | `pd.wattsOutSum` | W | integer | Gauge, Time Series |
| **Power Output** | AC Output | `inv.outputWatts` | W | integer | Gauge, Time Series |
| **Power Input** | AC Input | `inv.inputWatts` | W | integer | Gauge, Time Series |
| **Solar** | Solar Input | `mppt.inWatts` | W | integer | Gauge, Time Series, Daily totals |
| **Solar** | MPPT Output | `mppt.outWatts` | W | integer | Time Series |
| **Solar** | MPPT Temperature | `mppt.mpptTemp` | °C | integer/10 | Gauge, Time Series |
| **Power Output** | 12V Car Port | `pd.carWatts` | W | integer | Gauge, Time Series |
| **Power Output** | USB Port 1 | `pd.usb1Watts` | W | integer | Stacked Bar Chart with other USB |
| **Power Output** | USB Port 2 | `pd.usb2Watts` | W | integer | Stacked Bar Chart with other USB |
| **Power Output** | QC USB Port 1 | `pd.qcUsb1Watts` | W | integer | Stacked Bar Chart with other USB |
| **Power Output** | QC USB Port 2 | `pd.qcUsb2Watts` | W | integer | Stacked Bar Chart with other USB |
| **Power Output** | USB-C Port 1 | `pd.typec1Watts` | W | integer | Stacked Bar Chart with other USB |
| **Power Output** | USB-C Port 2 | `pd.typec2Watts` | W | integer | Stacked Bar Chart with other USB |
| **Temperature** | Inverter Temperature | `inv.outTemp` | °C | integer/10 | Gauge with thresholds, Time Series |
| **Time** | Remaining Runtime | `pd.remainTime` | minutes | integer | Gauge (as hours), Time Series |

### Calculated/Derived Metrics

These metrics are calculated from the above parameters:

| Metric | Calculation | Visualization |
|--------|-------------|---------------|
| **DC Output Total** | `carWatts + usb1 + usb2 + qcusb1 + qcusb2` | Gauge, Stacked Area |
| **USB Total Output** | `usb1 + usb2 + qcusb1 + qcusb2` | Gauge, Time Series |
| **USB-C Total Output** | `typec1 + typec2` | Gauge, Time Series |
| **Net Power** | `watts_in_sum - watts_out_sum` | Time Series (pos=charging, neg=discharging) |
| **Charging Status** | `watts_in_sum > 0` | Binary indicator/LED |
| **Discharging Status** | `watts_out_sum > 0` | Binary indicator/LED |
| **Runtime (hours)** | `remain_time_min / 60` | Gauge, formatted as "Xh Ym" |

## Part 3: Recommended Visualizations by Parameter

### High-Priority Dashboard Panels

Based on usefulness and data availability, recommended panels are:

#### Current Status (Stat Panels)
1. **Battery Level** - Large gauge (0-100%), color thresholds
2. **Current Input Power** - Gauge, shows charging watts
3. **Current Output Power** - Gauge, shows consumption
4. **Remaining Time** - Formatted as hours and minutes
5. **Charging Status** - Green/Red LED indicator

#### Historical Trends (Time Series)
6. **Power In/Out Over Time** - Dual line chart
7. **Battery Level History** - Line chart showing SOC over time
8. **Solar Production** - Area chart (when applicable)
9. **Temperature Trends** - Multi-line (Battery, Inverter, MPPT)
10. **Net Power Flow** - Pos/neg area chart

#### Detailed Breakdowns (Bar/Stacked)
11. **Output Distribution** - Stacked bar: AC, DC, USB, USB-C
12. **USB Ports Breakdown** - Individual USB port usage

### Panel Configuration Recommendations

#### For Current Values (Gauge/Stat Panels)
- **Type:** Gauge for values with max (battery, power), Stat for others
- **Thresholds:** 
  - Battery: Green >50%, Yellow 20-50%, Red <20%
  - Temperature: Green <40°C, Yellow 40-60°C, Red >60°C
  - Power: Green when expected values
- **Unit:** Auto-format with proper unit (W, %, °C, h)
- **Decimals:** 0 for power/battery, 1 for temperature

#### For Time Series (Historical Charts)
- **Type:** Time series (line or area)
- **Time Range:** Default last 24 hours, user-selectable
- **Legend:** Show on bottom or right, current values visible
- **Axes:** Y-axis starts at 0 for absolute values, auto for deltas
- **Points:** Only show on hover unless sparse data

#### For Distributions (Stacked/Bar)
- **Type:** Bar gauge or stacked area
- **Colors:** Consistent color per metric type
- **Tooltip:** Show all values in stack

## Part 4: REST API vs MQTT Data Comparison

### REST API (`/iot-open/sign/device/quota/all`)
**Pros:**
- Simple to implement
- No persistent connection needed
- Lower bandwidth
- Good for basic monitoring

**Cons:**
- Limited data fields (18 vs 200+ in MQTT)
- No voltage/current details
- No detailed battery cell data
- Polling only (30s minimum interval)

**Available Data:**
- High-level power metrics (in/out watts)
- Battery SOC and temperature
- Basic temperatures
- Output port watts
- Runtime estimate

### MQTT Stream (historical implementation)
**Pros:**
- 200+ detailed parameters
- Real-time updates (push-based)
- Full battery cell data (voltages, temps per cell)
- Detailed electrical measurements (V, A, W)
- System states and errors

**Cons:**
- Complex implementation
- Requires persistent connection
- Higher bandwidth usage
- More processing overhead

**Additional Data (not in REST API):**
- Individual cell voltages
- Individual cell temperatures
- Detailed current measurements
- Voltage details (input/output)
- Battery capacity details (full, remaining)
- Cycle count
- Detailed system states

## Part 5: Recommendations

### Immediate Actions

1. **Fix Exporter Style Dashboard**
   - Remove or mark as "N/A" panels querying unsupported fields
   - Correct `bms.*` paths to `bmsMaster.*` where applicable
   - Focus dashboard on available REST API data

2. **Create "EcoFlow API Data" Dashboard**
   - Show only the 18 confirmed API-supported parameters
   - Use recommended visualizations from Part 3
   - Include both current and historical views
   - Clear, user-friendly labels

3. **Document API Limitations**
   - Create user documentation explaining REST API vs MQTT differences
   - Set expectations about available data
   - Provide guidance on when MQTT might be needed

### Long-Term Considerations

1. **MQTT Integration (Optional)**
   - If detailed voltage/current/cell data is needed
   - Requires more complex implementation
   - Provides 10x more data points
   - Consider cost/benefit of complexity

2. **Dashboard Consolidation**
   - Current: 4 EcoFlow dashboards with overlapping info
   - Proposed: 2 dashboards - "Overview" (simple) + "Detailed" (advanced)
   - Reduces maintenance burden
   - Clearer user experience

3. **API Monitoring**
   - Track API response changes
   - Alert if expected fields missing
   - Version compatibility tracking

## Appendix: Complete Field Mapping

### REST API Response Structure

```json
{
  "bmsMaster.soc": 89,              // Battery State of Charge (%)
  "bmsMaster.temp": 235,             // Battery temp in tenths of °C (235 = 23.5°C)
  "pd.wattsInSum": 0,                // Total input power (W)
  "pd.wattsOutSum": 24,              // Total output power (W)
  "pd.remainTime": 7350,             // Remaining time (minutes)
  "pd.carWatts": 0,                  // 12V car port output (W)
  "pd.usb1Watts": 0,                 // USB port 1 output (W)
  "pd.usb2Watts": 0,                 // USB port 2 output (W)
  "pd.qcUsb1Watts": 0,               // QC USB port 1 output (W)
  "pd.qcUsb2Watts": 0,               // QC USB port 2 output (W)
  "pd.typec1Watts": 1,               // USB-C port 1 output (W)
  "pd.typec2Watts": 0,               // USB-C port 2 output (W)
  "inv.inputWatts": 0,               // AC input power (W)
  "inv.outputWatts": 24,             // AC output power (W)
  "inv.outTemp": 243,                // Inverter temp in tenths of °C (243 = 24.3°C)
  "mppt.inWatts": 0,                 // Solar input power (W)
  "mppt.outWatts": 0,                // MPPT output to battery (W)
  "mppt.mpptTemp": 228               // MPPT temp in tenths of °C (228 = 22.8°C)
}
```

**Note:** Temperature values are stored in tenths of degrees Celsius and must be divided by 10 to get actual temperature. For example, `bmsMaster.temp: 235` means 23.5°C.

### Database Storage

- **Table:** `ecoflow_measurements`
- **Extracted columns:** `soc_percent`, `remain_time_min`, `watts_in_sum`, `watts_out_sum`, etc.
- **Raw data:** Complete API response stored in `raw_data` JSONB column
- **Query pattern:** `(raw_data->>'field.name')::numeric` or `/10.0` for temperatures

---

**Report End**

For questions or updates, see:
- `stack/ecoflow-collector/ecoflow_collector.py` - Current collector implementation
- `docs/ecoflow_integration.md` - Integration guide
- `stack/postgres/init.sql` - Database schema
