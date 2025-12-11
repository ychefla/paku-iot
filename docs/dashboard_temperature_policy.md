# Dashboard Temperature Policy

## Overview

This document defines the policy for temperature data visualization in Paku-IoT dashboards to ensure consistency and completeness.

## Temperature and Humidity Overview Dashboard

**Dashboard Name:** Temperature and Humidity Overview  
**Dashboard UID:** `paku-ruuvi`  
**File:** `stack/grafana/dashboards/ruuvi_overview.json`

### Policy: All Temperature Sources Must Be Included

**Requirement:** The "Temperature and Humidity Overview" dashboard MUST display temperature data from ALL available sources in the system.

### Current Temperature Sources

#### 1. Ruuvi Sensors (Environmental Sensors)
- **Table:** `measurements`
- **Query Path:** `metrics->>'temperature_c'`
- **Description:** Environmental temperature sensors (Ruuvi tags)
- **Unit:** Celsius (°C)

#### 2. EcoFlow Power Station
The EcoFlow system provides multiple temperature measurements that MUST all be included:

##### a. Inverter Temperature
- **Table:** `ecoflow_measurements`
- **Query Path:** `(raw_data->'inv'->>'outTemp')::numeric / 10.0`
- **Description:** Inverter output temperature
- **Unit:** Celsius (°C)

##### b. Battery Management System (BMS) Temperature
- **Table:** `ecoflow_measurements`
- **Query Paths:** 
  - Primary: `(raw_data->'bms'->>'temp')::numeric / 10.0`
  - Fallback: `(raw_data->'bms_bmsStatus'->>'temp')::numeric / 10.0`
- **Description:** Battery management system temperature
- **Unit:** Celsius (°C)

##### c. Maximum Cell Temperature
- **Table:** `ecoflow_measurements`
- **Query Paths:**
  - Primary: `(raw_data->'bms'->>'maxCellTemp')::numeric / 10.0`
  - Fallback: `(raw_data->'bms_bmsStatus'->>'maxCellTemp')::numeric / 10.0`
- **Description:** Hottest battery cell temperature
- **Unit:** Celsius (°C)

##### d. Minimum Cell Temperature
- **Table:** `ecoflow_measurements`
- **Query Paths:**
  - Primary: `(raw_data->'bms'->>'minCellTemp')::numeric / 10.0`
  - Fallback: `(raw_data->'bms_bmsStatus'->>'minCellTemp')::numeric / 10.0`
- **Description:** Coldest battery cell temperature
- **Unit:** Celsius (°C)

### Adding New Temperature Sources

When new devices or systems with temperature sensors are added to Paku-IoT, they MUST be added to the Temperature and Humidity Overview dashboard according to the following process:

1. **Identify Temperature Fields**
   - Determine the database table
   - Identify the column or JSONB path where temperature is stored
   - Verify the unit (convert to Celsius if needed)
   - Check if scaling is needed (e.g., divide by 10)

2. **Update Dashboard**
   - Add a new query target to the "Temperature (°C)" panel
   - Use descriptive metric name (e.g., "Device Type - Sensor Name")
   - Include appropriate NULL checks
   - Use COALESCE for fallback values if applicable
   - Apply time filtering: `$__timeFilter(ts)`
   - Order by timestamp: `ORDER BY ts ASC`

3. **Query Template**
   ```sql
   SELECT
     ts AS "time",
     [temperature_expression] AS value,
     '[Device Type - Sensor Name]' AS metric
   FROM [table_name]
   WHERE
     $__timeFilter(ts)
     AND [temperature_field] IS NOT NULL
   ORDER BY ts ASC
   ```

4. **Update Documentation**
   - Add the new temperature source to this document
   - Document the query path and any transformations
   - Include in the "Current Temperature Sources" section above

5. **Testing**
   - Verify the query returns data in Grafana
   - Check that the metric appears in the Temperature panel
   - Ensure historical data is displayed correctly
   - Validate units are correct (Celsius)

### Best Practices

1. **Metric Naming Convention**
   - Format: `[System/Device Type] [Specific Sensor]`
   - Examples: "EcoFlow BMS", "Ruuvi Living Room", "Heater Inlet"

2. **NULL Handling**
   - Always include NULL checks in WHERE clause
   - Use COALESCE with fallback paths when multiple locations exist
   - Default to 0 only for gauges, not for time series

3. **Time Filtering**
   - Always use `$__timeFilter(ts)` for time series queries
   - Always order by `ts ASC` for proper time series rendering

4. **Unit Consistency**
   - All temperatures MUST be displayed in Celsius (°C)
   - Apply conversions in the query if source uses different units
   - Apply scaling factors if needed (e.g., divide by 10 for EcoFlow)

### Validation Checklist

When adding or reviewing temperature sources:

- [ ] All available temperature sensors are included
- [ ] Query paths are correct for the database schema
- [ ] Metric names are descriptive and follow naming convention
- [ ] Unit conversions are applied correctly
- [ ] NULL checks prevent errors
- [ ] Time filtering is applied
- [ ] Data displays correctly in the dashboard
- [ ] This documentation is updated

## Related Dashboards

While the Temperature and Humidity Overview dashboard is the primary location for temperature monitoring, individual device dashboards may also display temperature:

- **EcoFlow Dashboards:** May show device-specific temperatures
- **Device-Specific Dashboards:** May focus on single device temperatures

However, the Temperature and Humidity Overview dashboard MUST remain the comprehensive source showing ALL temperatures across the system.

## Maintenance

This policy should be reviewed and updated whenever:
- New devices with temperature sensors are added
- Database schema changes affect temperature storage
- New temperature data sources become available
- Dashboard structure is modified

---

**Last Updated:** 2025-12-11  
**Policy Version:** 1.0
