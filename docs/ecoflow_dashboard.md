# EcoFlow Grafana Dashboard Guide

## Overview

The EcoFlow Power Station Overview dashboard provides comprehensive monitoring and visualization of your EcoFlow device data in real-time.

## Dashboard Features

### Automatic Provisioning

The dashboard is automatically loaded when you start Grafana. No manual import required!

**Location**: `stack/grafana/dashboards/ecoflow_overview.json`

### Access

1. Start the stack with EcoFlow profile:
   ```bash
   docker compose --profile ecoflow -f compose/stack.yaml up -d
   ```

2. Access Grafana: http://localhost:3000

3. Navigate to: **Dashboards → EcoFlow Power Station Overview**

## Dashboard Layout

### Row 1: Current Status (4 Stat Panels)

**Battery Level** - Large stat with color gradient
- Shows current state of charge (%)
- Color coding:
  - 🔴 Red: 0-20% (Critical)
  - 🟠 Orange: 20-50% (Low)
  - 🟡 Yellow: 50-80% (Medium)
  - 🟢 Green: 80-100% (Good)
- Includes sparkline graph showing recent trend

**Power Output** - Current load in watts
- Shows total power consumption
- Color thresholds:
  - Green: 0-1000W (Light load)
  - Yellow: 1000-2000W (Medium load)
  - Orange: 2000-3000W (Heavy load)
  - Red: >3000W (Very heavy load)

**Power Input** - Current charging power
- Shows total input power in watts
- Green when charging (>0W)
- Red when not charging (0W)

**Remaining Time** - Estimated runtime
- Shows minutes until empty (at current load)
- Color coding:
  - Red: <30 minutes
  - Orange: 30-60 minutes
  - Yellow: 60-120 minutes
  - Green: >120 minutes

### Row 2: Power Trends (2 Time Series Charts)

**Battery State of Charge** - Historical battery level
- Time series chart showing battery % over time
- Same color thresholds as battery stat
- Default: Last 6 hours
- Auto-refresh: 30 seconds

**Power Flow (Input/Output)** - Charging vs Load
- Dual-series chart showing:
  - 🟢 Green line: Power Input (charging)
  - 🔴 Red line: Power Output (load)
- Shows when device is charging vs discharging
- Helps identify usage patterns

### Row 3: Detailed Analysis (2 Time Series Charts)

**Solar (PV) Input** - Solar charging power
- 🟡 Yellow line showing solar input over time
- Track solar generation throughout the day
- Useful for optimizing solar panel placement
- Shows weather impact on charging

**Output Ports Breakdown** - Where power goes
- Multi-series chart showing power usage by port:
  - AC outlets (e.g., laptops, appliances)
  - DC outlets (e.g., car chargers)
  - USB-C ports (e.g., phones, tablets)
  - USB-A ports (e.g., accessories)
- Helps identify which devices consume most power

### Row 4: Summary and Details (3 Panels)

**Current Power Output Gauge** - Visual power indicator
- Semi-circular gauge (speedometer style)
- Scale: 0-3600W (3.6kW max for Delta Pro)
- Color zones:
  - Green: 0-2000W
  - Yellow: 2000-3000W
  - Red: 3000-3600W

**Energy Statistics (Last Hour)** - Quick stats
- Three key metrics:
  - Average Output: Mean power consumption
  - Peak Output: Maximum power draw
  - Average Input: Mean charging rate
- Helps understand recent usage patterns

**Recent Measurements Table** - Latest data
- Shows last 10 measurements
- Columns:
  - Time (timestamp)
  - Battery % (color-coded)
  - Input (W)
  - Output (W)
  - Remain (minutes)
- Battery % column has color background
- Sortable by clicking column headers

### Row 5: Advanced Analysis (1 Full-Width Chart)

**Net Power Flow** - Charging vs Discharging
- Shows net power: Input - Output
- Positive values (green): Charging (battery gaining power)
- Negative values (red/orange): Discharging (battery losing power)
- Zero (yellow): Balanced (input = output)
- Gradient fill for visual impact
- Helps visualize energy flow at a glance

## Device Selection

**Multi-Device Support**

If you have multiple EcoFlow devices:
1. Click the "Device" dropdown at the top of the dashboard
2. Select the device serial number you want to monitor
3. All panels update automatically

The dropdown is populated from your database:
```sql
SELECT DISTINCT device_sn FROM ecoflow_measurements
```

## Dashboard Settings

### Time Range
- Default: Last 6 hours
- Adjustable via time picker (top-right)
- Common ranges:
  - Last 6 hours (default)
  - Last 12 hours
  - Last 24 hours
  - Last 7 days
  - Custom range

### Auto-Refresh
- Default: 30 seconds
- Configurable via refresh dropdown
- Options: 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h

### Panel Interactions
- **Hover**: See exact values and timestamps
- **Click legend**: Toggle series on/off
- **Zoom**: Click and drag on chart
- **Reset zoom**: Double-click chart
- **Expand**: Click panel title → View
- **Edit**: Click panel title → Edit (for customization)

## Use Cases

### Daily Monitoring
Track battery level throughout the day to understand:
- When battery charges from solar
- Peak usage times
- How long battery lasts on typical load

### Solar Optimization
Use the Solar Input panel to:
- Verify panels are working
- Track generation throughout day
- Identify optimal panel angles
- Monitor weather impact

### Load Management
Use Output Ports Breakdown to:
- Identify power-hungry devices
- Balance loads across ports
- Optimize device usage
- Plan power budget

### Energy Planning
Use Net Power Flow to:
- See when you're charging vs discharging
- Identify net positive/negative periods
- Plan device usage around charging times
- Optimize solar utilization

### Troubleshooting
Use Recent Measurements table to:
- Verify data is flowing
- Check timestamp freshness
- Spot anomalies quickly
- Debug collector issues

## Customization

### Adding Panels

To add a new panel:
1. Click "Add panel" (dashboard settings)
2. Select "Add a new panel"
3. Choose visualization type
4. Configure data source (PostgreSQL - paku-pg)
5. Write SQL query against `ecoflow_measurements`

Example query for custom metric:
```sql
SELECT
  ts AS "time",
  (watts_out_sum * 1.0 / NULLIF(soc_percent, 0)) AS "Power per %"
FROM ecoflow_measurements
WHERE
  device_sn = '$device_sn'
  AND $__timeFilter(ts)
ORDER BY ts
```

### Modifying Thresholds

To adjust color thresholds:
1. Click panel title → Edit
2. Go to "Field" tab (right sidebar)
3. Scroll to "Thresholds"
4. Click "+" to add threshold
5. Adjust values and colors
6. Save dashboard

### Alerts (Future Enhancement)

You can add alerts to notify when:
- Battery drops below 20%
- Power output exceeds 3000W
- No data received for 5 minutes
- Remaining time < 30 minutes

See Grafana alerting documentation for setup.

## SQL Query Examples

### All panels use these data patterns:

**Latest value:**
```sql
SELECT column_name
FROM ecoflow_measurements
WHERE device_sn = '$device_sn'
ORDER BY ts DESC
LIMIT 1
```

**Time series:**
```sql
SELECT
  ts AS "time",
  column_name AS "Display Name"
FROM ecoflow_measurements
WHERE
  device_sn = '$device_sn'
  AND $__timeFilter(ts)
ORDER BY ts
```

**Aggregations:**
```sql
SELECT
  AVG(column_name) AS "Average",
  MAX(column_name) AS "Maximum"
FROM ecoflow_measurements
WHERE
  device_sn = '$device_sn'
  AND ts >= NOW() - INTERVAL '1 hour'
```

## Troubleshooting

### Dashboard Not Visible
- Verify Grafana is running: `docker ps | grep grafana`
- Check logs: `docker logs paku_grafana`
- Dashboard file present: `ls stack/grafana/dashboards/ecoflow_overview.json`

### No Data Showing
- Verify collector is running: `docker ps | grep ecoflow`
- Check collector logs: `docker logs paku_ecoflow_collector`
- Verify data in database:
  ```bash
  docker exec -it paku_postgres psql -U paku -d paku
  SELECT COUNT(*) FROM ecoflow_measurements;
  ```

### "No Device" in Dropdown
- No data collected yet (wait 1-2 minutes)
- Collector not configured with credentials
- Check collector logs for errors

### Panels Show "N/A"
- Selected device has no recent data
- Check time range (may be too far in past)
- Verify device serial number is correct

### Queries Taking Long Time
- Large time range selected
- Database needs indexing (should be automatic)
- Check PostgreSQL logs: `docker logs paku_postgres`

## Dashboard Metrics Reference

| Metric | Column | Unit | Description |
|--------|--------|------|-------------|
| Battery Level | `soc_percent` | % | State of charge (0-100%) |
| Power Output | `watts_out_sum` | W | Total power consumption |
| Power Input | `watts_in_sum` | W | Total charging power |
| Remaining Time | `remain_time_min` | minutes | Estimated runtime |
| AC Output | `ac_out_watts` | W | AC outlets power |
| DC Output | `dc_out_watts` | W | DC outlets power |
| USB-C | `typec_out_watts` | W | USB-C ports power |
| USB-A | `usb_out_watts` | W | USB-A ports power |
| Solar Input | `pv_in_watts` | W | PV/solar charging |

## Best Practices

1. **Regular Monitoring**: Check dashboard daily to understand patterns
2. **Time Range**: Use 6-24 hours for daily monitoring, 7 days for trends
3. **Screenshots**: Take screenshots of interesting patterns for reference
4. **Baselines**: Note typical values for comparison
5. **Alerts**: Set up alerts for critical thresholds (when supported)

## Advanced Features

### JSON Queries

All panels can query the `raw_data` JSONB column:
```sql
SELECT
  ts AS "time",
  raw_data->>'params'->>'bmsMaster'->>'temp' AS "Battery Temp"
FROM ecoflow_measurements
WHERE device_sn = '$device_sn'
  AND $__timeFilter(ts)
ORDER BY ts
```

### Variables

Add more dashboard variables:
- Site location
- Time aggregation (1m, 5m, 15m)
- Metric to display

### Export Data

Use Grafana's export features:
- Export to CSV (panel menu → Inspect → Data → Download CSV)
- Export dashboard JSON (dashboard settings → JSON Model)
- Screenshot panels (panel menu → Share → Direct link)

## Related Documentation

- [EcoFlow Integration Guide](ecoflow_integration.md)
- [Database Schema](database_schema.md)
- [Grafana Official Docs](https://grafana.com/docs/)

## Support

For dashboard issues:
- Check Grafana logs: `docker logs paku_grafana`
- Verify PostgreSQL connection in Grafana UI
- Test queries in PostgreSQL directly first
- Refer to panel configuration in JSON file

## Future Enhancements

Planned dashboard improvements:
- Weather data integration (temperature, cloud cover)
- Cost calculations (electricity rates)
- Historical comparisons (today vs yesterday)
- Predictive analytics (ML-based runtime estimates)
- Mobile-optimized view
- Pre-configured alerts
- Export/import of custom panels
