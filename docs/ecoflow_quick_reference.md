# EcoFlow Integration Quick Reference

## Setup Commands

```bash
# 1. Add credentials to compose/.env
ECOFLOW_ACCESS_KEY=your_access_key
ECOFLOW_SECRET_KEY=your_secret_key
ECOFLOW_DEVICE_SN=R331ZEB4ZEA0012345

# 2. Start with EcoFlow profile
docker compose --profile ecoflow -f compose/stack.yaml up -d

# 3. Check logs
docker logs -f paku_ecoflow_collector

# 4. Access Grafana
open http://localhost:3000
```

## Quick SQL Queries

```sql
-- Check data is flowing
SELECT COUNT(*) FROM ecoflow_measurements;

-- Latest reading
SELECT * FROM ecoflow_measurements 
ORDER BY ts DESC LIMIT 1;

-- Last hour average
SELECT 
  AVG(soc_percent) as avg_battery,
  AVG(watts_out_sum) as avg_output
FROM ecoflow_measurements
WHERE ts >= NOW() - INTERVAL '1 hour';

-- Device list
SELECT DISTINCT device_sn FROM ecoflow_measurements;
```

## Dashboard Panels

| Panel | What It Shows | Color Coding |
|-------|---------------|--------------|
| Battery Level | Current SoC % | Red<20%, Orange<50%, Yellow<80%, Green>80% |
| Power Output | Load in watts | Green<1kW, Yellow<2kW, Orange<3kW, Red>3kW |
| Power Input | Charging watts | Green if >0W, Red if 0W |
| Remaining Time | Minutes left | Red<30m, Orange<60m, Yellow<120m, Green>120m |
| Battery SoC | Historical % | Same as Battery Level |
| Power Flow | Input vs Output | Green=Input, Red=Output |
| Solar Input | PV generation | Yellow line |
| Ports Breakdown | AC/DC/USB usage | Multi-color lines |
| Power Gauge | Visual meter | Green→Yellow→Red zones |
| Energy Stats | Hour averages | No color coding |
| Recent Table | Last 10 rows | Battery % colored |
| Net Flow | Charge/discharge | Green=charging, Red=draining |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No data in dashboard | Check collector logs, verify credentials |
| Authentication failed | Check API keys in .env, verify no spaces |
| Device not in dropdown | Wait 2 minutes for first data, check device_sn |
| Panels show "N/A" | Select correct time range, check device has data |
| Collector won't start | Verify .env credentials set, check Docker logs |
| Dashboard not visible | Restart Grafana, check provisioning logs |

## Key Files

| File | Purpose |
|------|---------|
| `stack/ecoflow-collector/ecoflow_collector.py` | Collector service |
| `stack/postgres/init.sql` | Database schema |
| `stack/grafana/dashboards/ecoflow_overview.json` | Dashboard |
| `compose/.env` | Credentials (git-ignored) |
| `docs/ecoflow_integration.md` | Full setup guide |
| `docs/ecoflow_dashboard.md` | Dashboard guide |

## Important URLs

- **Grafana**: http://localhost:3000
- **EcoFlow Developer Portal**: https://developer.ecoflow.com/
- **Dashboard**: Dashboards → EcoFlow Power Station Overview

## Common Tasks

### Check Collector Status
```bash
docker ps | grep ecoflow
docker logs paku_ecoflow_collector --tail 50
```

### Query Database
```bash
docker exec -it paku_postgres psql -U paku -d paku
\dt ecoflow_measurements
SELECT * FROM ecoflow_measurements ORDER BY ts DESC LIMIT 5;
\q
```

### Restart Services
```bash
# Restart just EcoFlow collector
docker compose --profile ecoflow -f compose/stack.yaml restart ecoflow-collector

# Restart all
docker compose --profile ecoflow -f compose/stack.yaml restart
```

### View Dashboard JSON
```bash
cat stack/grafana/dashboards/ecoflow_overview.json | jq .
```

## Dashboard Access

1. **Login**: http://localhost:3000 (admin / admin)
2. **Navigate**: Dashboards → EcoFlow Power Station Overview
3. **Select Device**: Dropdown at top if multiple devices
4. **Adjust Time**: Time picker (top-right corner)
5. **Refresh**: Manual refresh button or auto-refresh

## Metrics Collected

| Metric | Column | Unit | Description |
|--------|--------|------|-------------|
| Battery | `soc_percent` | % | State of charge |
| Runtime | `remain_time_min` | min | Estimated remaining time |
| Input | `watts_in_sum` | W | Total charging power |
| Output | `watts_out_sum` | W | Total load power |
| AC | `ac_out_watts` | W | AC outlets |
| DC | `dc_out_watts` | W | DC outlets |
| USB-C | `typec_out_watts` | W | USB-C ports |
| USB-A | `usb_out_watts` | W | USB-A ports |
| Solar | `pv_in_watts` | W | Solar input |
| Raw | `raw_data` | JSON | Complete payload |

## Color Codes

### Battery Level
- 🔴 0-20%: Critical
- 🟠 20-50%: Low
- 🟡 50-80%: Medium
- 🟢 80-100%: Good

### Power Output
- 🟢 0-1000W: Light load
- 🟡 1000-2000W: Medium load
- 🟠 2000-3000W: Heavy load
- 🔴 3000W+: Very heavy load

### Net Power Flow
- 🔴 Negative: Discharging
- 🟡 Zero: Balanced
- 🟢 Positive: Charging

## Environment Variables

```bash
# Required
ECOFLOW_ACCESS_KEY=ak_us_xxxxx
ECOFLOW_SECRET_KEY=sk_us_xxxxx

# Optional
ECOFLOW_DEVICE_SN=R331ZEB4ZEA0012345

# Database (already set)
POSTGRES_USER=paku
POSTGRES_PASSWORD=paku
POSTGRES_DB=paku
```

## Docker Compose Profile

The EcoFlow collector uses Docker Compose profiles:

```bash
# Start without EcoFlow
docker compose -f compose/stack.yaml up

# Start with EcoFlow
docker compose --profile ecoflow -f compose/stack.yaml up

# Start only EcoFlow (with dependencies)
docker compose --profile ecoflow -f compose/stack.yaml up ecoflow-collector
```

## Default Values

- **Refresh Rate**: 30 seconds
- **Time Range**: 6 hours
- **Dashboard UID**: paku-ecoflow
- **Data Source**: paku-pg (PostgreSQL)
- **Container Name**: paku_ecoflow_collector
- **Database Table**: ecoflow_measurements

## API Credentials

Get from https://developer.ecoflow.com/:
1. Sign up / Login
2. Create application
3. Copy Access Key
4. Copy Secret Key
5. Add to compose/.env

## Supported Devices

- ✅ Delta Pro
- ✅ Delta Max
- ✅ Delta 2 Series
- ✅ River Series
- ✅ PowerStream
- ✅ Any device with official API support

## Dashboard Features

- ✅ Auto-refresh (30s)
- ✅ Multi-device support
- ✅ Time range selector
- ✅ Interactive charts
- ✅ Color-coded thresholds
- ✅ Hover tooltips
- ✅ Legend toggle
- ✅ Zoom/pan
- ✅ Export to CSV
- ✅ Full-screen panels

## Getting Help

| Issue Type | Resource |
|------------|----------|
| Setup | ECOFLOW_QUICKSTART.md |
| Configuration | docs/ecoflow_integration.md |
| Dashboard | docs/ecoflow_dashboard.md |
| Technical | docs/ecoflow_technical_notes.md |
| Database | docs/database_schema.md |
| API Issues | https://developer.ecoflow.com/ |

## Version Info

- Grafana Schema Version: 39
- Dashboard Version: 1
- Python: 3.11+
- PostgreSQL: 16+
- paho-mqtt: 2.1.0
- psycopg: 3.2.3

## Quick Tips

💡 **Tip 1**: Use 24-hour time range to see full day patterns  
💡 **Tip 2**: Solar panel shows when battery charges from sun  
💡 **Tip 3**: Net flow chart shows if you're gaining or losing power  
💡 **Tip 4**: Recent table is best for debugging  
💡 **Tip 5**: Set auto-refresh to 10s for real-time monitoring  
💡 **Tip 6**: Use device dropdown if you have multiple units  
💡 **Tip 7**: Export panel data to CSV for analysis  
💡 **Tip 8**: Screenshot panels for sharing/reporting  
💡 **Tip 9**: Hover over charts for exact values  
💡 **Tip 10**: Double-click charts to reset zoom  

## Status Indicators

| Indicator | Meaning |
|-----------|---------|
| 🟢 Green | Good / Charging / Normal |
| 🟡 Yellow | Medium / Balanced / Warning |
| 🟠 Orange | High / Low / Caution |
| 🔴 Red | Critical / Empty / Alert |

## Last Updated

This quick reference was last updated with commit b1ce9b9.
For the most current information, see the full documentation in `docs/`.
