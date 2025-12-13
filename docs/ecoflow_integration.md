# EcoFlow Integration Guide

This guide explains how to integrate EcoFlow power stations (like Delta Pro) with paku-iot to automatically collect and visualize power station data.

## Overview

The EcoFlow integration enables automatic collection of real-time data from EcoFlow power stations over the internet. This is achieved by:

1. **Authentication**: Using EcoFlow Developer API credentials
2. **MQTT Connection**: Subscribing to EcoFlow's cloud MQTT broker
3. **Data Collection**: Receiving real-time power station telemetry
4. **Storage**: Persisting data to PostgreSQL
5. **Visualization**: Creating Grafana dashboards

## Architecture

```
EcoFlow Device → EcoFlow Cloud → REST API → EcoFlow Collector → PostgreSQL → Grafana
     (WiFi)         (Internet)   (HTTPS)      (Container)        (paku DB)
```

The EcoFlow collector service runs as a separate Docker container that:
- Authenticates with the EcoFlow Developer API using HMAC-SHA256 signatures
- Polls the REST API at configurable intervals (default: 30 seconds)
- Fetches device quota/status data via HTTPS GET requests
- Parses and stores measurements in the database

## Prerequisites

### 1. EcoFlow Device Setup

Ensure your EcoFlow device is:
- Connected to WiFi
- Linked to your EcoFlow mobile app account
- Online and accessible via the EcoFlow app

Supported devices:
- Delta Pro
- Delta Max
- Delta 2 Series (Delta 2, Delta 2 Max, Delta 2 Pro)
- River Series (with cloud API support)
- PowerStream

### 2. EcoFlow Developer Account

**Step 1**: Register as a developer

1. Visit [EcoFlow Developer Portal](https://developer.ecoflow.com/)
2. Click "Sign Up" or "Register"
3. Complete the registration form
4. Verify your email address

**Step 2**: Create an application

1. Log in to the developer portal
2. Navigate to "Applications" or "My Apps"
3. Click "Create Application"
4. Fill in application details:
   - **Name**: e.g., "Paku IoT Integration"
   - **Description**: Brief description of your use case
   - **Type**: Select appropriate type (usually "Personal" or "Testing")
5. Submit the application

**Step 3**: Obtain API credentials

Once your application is approved (usually instant for personal use):

1. Go to your application details
2. Copy your credentials:
   - **Access Key** (also called `accessKey` or `access_key`)
   - **Secret Key** (also called `secretKey` or `secret_key`)

**Important**: Keep these credentials secure - they provide access to your devices.

### 3. Find Your Device Serial Number

You'll need your device's serial number (optional but recommended for filtering):

**Method 1: EcoFlow App**
1. Open the EcoFlow app
2. Select your device
3. Go to Settings → About
4. Copy the Serial Number (format: `R331ZEB...` for Delta Pro)

**Method 2: Physical Label**
- Check the device label (usually on the back or bottom)
- Look for "S/N:" followed by alphanumeric code

## Installation

### Step 1: Configure Environment Variables

Edit your `compose/.env` file and add EcoFlow credentials:

```bash
# EcoFlow Developer API Credentials
ECOFLOW_ACCESS_KEY=your_access_key_from_developer_portal
ECOFLOW_SECRET_KEY=your_secret_key_from_developer_portal

# Optional: Specific device serial number
# If omitted, collector will receive data from all devices on your account
ECOFLOW_DEVICE_SN=R331ZEB4ZEA1234567
```

Example with real credentials (yours will differ):
```bash
ECOFLOW_ACCESS_KEY=ak_us_1a2b3c4d5e6f7g8h
ECOFLOW_SECRET_KEY=sk_us_9i8h7g6f5e4d3c2b1a
ECOFLOW_DEVICE_SN=R331ZEB4ZEA0012345
```

### Step 2: Start the EcoFlow Collector

The EcoFlow collector uses Docker Compose profiles to make it optional:

**Option A: Start only EcoFlow collector**
```bash
docker compose --profile ecoflow -f compose/stack.yaml up ecoflow-collector
```

**Option B: Start full stack with EcoFlow**
```bash
docker compose --profile ecoflow -f compose/stack.yaml up
```

**Option C: Start full stack without EcoFlow**
```bash
# Regular stack without EcoFlow (default)
docker compose -f compose/stack.yaml up
```

### Step 3: Verify Connection

Check the logs to ensure successful connection:

```bash
docker logs paku_ecoflow_collector
```

Expected output:
```
2025-12-01 10:30:00 [INFO] paku-ecoflow-collector - Starting EcoFlow Collector Service
2025-12-01 10:30:00 [INFO] paku-ecoflow-collector - Connecting to Postgres at postgres:5432 db=paku
2025-12-01 10:30:01 [INFO] paku-ecoflow-collector - Requesting MQTT credentials from EcoFlow API...
2025-12-01 10:30:02 [INFO] paku-ecoflow-collector - Successfully obtained MQTT credentials
2025-12-01 10:30:02 [INFO] paku-ecoflow-collector - Connecting to EcoFlow MQTT broker at mqtt.ecoflow.com:8883
2025-12-01 10:30:03 [INFO] paku-ecoflow-collector - Connected to EcoFlow MQTT broker
2025-12-01 10:30:03 [INFO] paku-ecoflow-collector - Subscribing to device-specific topic: /app/+/R331ZEB4ZEA0012345/+
2025-12-01 10:30:15 [INFO] paku-ecoflow-collector - Inserted EcoFlow measurement for device=R331ZEB4ZEA0012345, soc=85%
```

## Data Schema

### Database Table: `ecoflow_measurements`

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGSERIAL | Primary key |
| `device_sn` | TEXT | Device serial number |
| `ts` | TIMESTAMPTZ | Measurement timestamp |
| `soc_percent` | INTEGER | State of charge (battery %) |
| `remain_time_min` | INTEGER | Estimated runtime (minutes) |
| `watts_in_sum` | INTEGER | Total input power (watts) |
| `watts_out_sum` | INTEGER | Total output power (watts) |
| `ac_out_watts` | INTEGER | AC output (watts) |
| `dc_out_watts` | INTEGER | DC output (watts) |
| `typec_out_watts` | INTEGER | USB-C output (watts) |
| `usb_out_watts` | INTEGER | USB-A output (watts) |
| `pv_in_watts` | INTEGER | Solar input (watts) |
| `raw_data` | JSONB | Complete JSON payload |

### Query Examples

**Latest measurement for a device:**
```sql
SELECT * FROM ecoflow_measurements 
WHERE device_sn = 'R331ZEB4ZEA0012345'
ORDER BY ts DESC 
LIMIT 1;
```

**Battery level over time (last 24 hours):**
```sql
SELECT ts, soc_percent 
FROM ecoflow_measurements 
WHERE device_sn = 'R331ZEB4ZEA0012345'
  AND ts >= NOW() - INTERVAL '24 hours'
ORDER BY ts;
```

**Power flow analysis:**
```sql
SELECT 
    ts,
    watts_in_sum as charging_watts,
    watts_out_sum as load_watts,
    watts_in_sum - watts_out_sum as net_watts
FROM ecoflow_measurements 
WHERE device_sn = 'R331ZEB4ZEA0012345'
  AND ts >= NOW() - INTERVAL '1 hour'
ORDER BY ts;
```

## Grafana Dashboards

### Creating a Dashboard

1. **Access Grafana**: http://localhost:3000
2. **Login**: Use credentials from `compose/.env`
3. **Create Dashboard**: Click "+" → "New Dashboard"
4. **Add Panel**: Click "Add visualization"

### Example Panels

**Panel 1: Battery State of Charge**
```sql
SELECT 
    ts as time,
    soc_percent as "Battery %"
FROM ecoflow_measurements
WHERE 
    device_sn = 'R331ZEB4ZEA0012345'
    AND $__timeFilter(ts)
ORDER BY ts
```
- Visualization: Time series
- Y-axis: Percentage (0-100)

**Panel 2: Power Flow**
```sql
SELECT 
    ts as time,
    watts_in_sum as "Input (W)",
    watts_out_sum as "Output (W)"
FROM ecoflow_measurements
WHERE 
    device_sn = 'R331ZEB4ZEA0012345'
    AND $__timeFilter(ts)
ORDER BY ts
```
- Visualization: Time series
- Y-axis: Watts

**Panel 3: Current Status (Stat Panel)**
```sql
SELECT 
    soc_percent as "Battery",
    watts_out_sum as "Load",
    watts_in_sum as "Input"
FROM ecoflow_measurements
WHERE device_sn = 'R331ZEB4ZEA0012345'
ORDER BY ts DESC
LIMIT 1
```
- Visualization: Stat
- Show: Current value only

**Panel 4: Solar Input**
```sql
SELECT 
    ts as time,
    pv_in_watts as "Solar (W)"
FROM ecoflow_measurements
WHERE 
    device_sn = 'R331ZEB4ZEA0012345'
    AND $__timeFilter(ts)
ORDER BY ts
```

## Troubleshooting

### Problem: Authentication Errors

**Symptoms**: Logs show "Failed to get MQTT credentials" or 401/403 errors

**Solutions**:
1. Verify credentials are correct in `compose/.env`
2. Check for extra spaces or newlines in credentials
3. Ensure your developer account is active
4. Try regenerating credentials in developer portal

### Problem: No Data Received

**Symptoms**: Connected successfully but no measurements in database

**Solutions**:
1. Verify device is online in EcoFlow app
2. Check device serial number is correct
3. Try removing `ECOFLOW_DEVICE_SN` to subscribe to all devices
4. Check MQTT topic in logs - it should match device format
5. Enable debug logging: Add `LOG_LEVEL=DEBUG` to environment

### Problem: Connection Timeouts

**Symptoms**: Cannot connect to MQTT broker

**Solutions**:
1. Check internet connectivity
2. Verify firewall allows outbound port 8883
3. Try different network (mobile hotspot for testing)
4. Check EcoFlow service status

### Problem: Missing Fields

**Symptoms**: Some metrics show NULL in database

**Solutions**:
1. Not all devices support all fields
2. Check `raw_data` column to see actual payload structure
3. Field names may vary by device model
4. Some fields only populate when active (e.g., solar input when sun present)

### Viewing Raw Data

To debug data format issues:

```sql
SELECT 
    device_sn,
    ts,
    raw_data 
FROM ecoflow_measurements 
ORDER BY ts DESC 
LIMIT 5;
```

This shows the complete JSON payload received from EcoFlow.

## Security Best Practices

### Credentials Management

1. **Never commit credentials**: `.env` is git-ignored by default
2. **Use strong passwords**: For database and Grafana
3. **Rotate credentials**: Periodically regenerate API keys
4. **Read-only access**: Use read-only API keys if available
5. **Network isolation**: Consider firewall rules for production

### API Limits

- EcoFlow API has rate limits (typically generous for personal use)
- MQTT credentials expire after some time (auto-renewed by collector)
- Avoid running multiple collectors with same credentials simultaneously

## Advanced Configuration

### Multiple Devices

To monitor multiple EcoFlow devices:

**Option 1**: Omit device serial number
```bash
# In .env, comment out or remove:
# ECOFLOW_DEVICE_SN=
```
This subscribes to all devices on your account.

**Option 2**: Run multiple collectors
```bash
# Not recommended - increases complexity
# Instead, use Option 1
```

### Custom Collection Intervals

EcoFlow pushes data at its own intervals (typically every few seconds to minutes). The collector receives data as pushed by EcoFlow.

### Data Retention

Configure PostgreSQL retention policies:

```sql
-- Delete measurements older than 90 days
DELETE FROM ecoflow_measurements 
WHERE ts < NOW() - INTERVAL '90 days';
```

Consider setting up automated cleanup or using TimescaleDB for time-series optimization.

## Integration with Home Automation

### Home Assistant

You can query the paku-iot database from Home Assistant:

```yaml
sensor:
  - platform: sql
    db_url: postgresql://paku:paku@localhost:5432/paku
    queries:
      - name: "EcoFlow Battery"
        query: >
          SELECT soc_percent FROM ecoflow_measurements 
          WHERE device_sn = 'YOUR_SN' 
          ORDER BY ts DESC LIMIT 1
        column: 'soc_percent'
        unit_of_measurement: '%'
```

### Node-RED

Use Node-RED PostgreSQL nodes to query and automate based on power station data.

### REST API

Consider adding a REST API layer (future enhancement) to expose data via HTTP endpoints.

## Performance Considerations

- **Database Size**: Each measurement is ~200 bytes + raw JSON
- **Typical Rate**: 1-10 measurements per minute per device
- **Daily Growth**: ~1-10 MB per device per day
- **Indexing**: Properly indexed for time-series queries

## References

- [EcoFlow Developer Portal](https://developer.ecoflow.com/)
- [EcoFlow API Documentation](https://developer.ecoflow.com/us/document/introduction)
- [paho-mqtt Documentation](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)

## Support

For issues specific to:
- **paku-iot integration**: Open an issue on GitHub
- **EcoFlow API**: Contact EcoFlow developer support
- **Device connectivity**: Contact EcoFlow customer support

## Future Enhancements

Planned improvements:
- [ ] Historical data backfill via REST API
- [ ] Downlink commands (remote control)
- [ ] Alert notifications (low battery, high load)
- [ ] REST API for external access
- [ ] Pre-built Grafana dashboards
- [ ] Multi-site support
- [ ] Data export capabilities
