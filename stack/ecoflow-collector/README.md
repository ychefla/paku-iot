# EcoFlow Collector Service

This service connects to the EcoFlow Cloud API to collect real-time data from EcoFlow power stations (e.g., Delta Pro) and stores it in the paku-iot PostgreSQL database.

## ⚠️ Recent Changes (December 2024)

**EcoFlow API Authentication Updated**: The EcoFlow API changed from header-based POST authentication to query parameter-based GET authentication with HMAC-SHA256 signatures. The collector has been updated to support the new authentication method.

If you encounter "HTTP 405 Method Not Allowed" errors, ensure you're using the latest version of this collector.

## Overview

The EcoFlow collector:
1. Authenticates with the EcoFlow Developer API using HMAC-SHA256 signed requests
2. Polls the EcoFlow REST API at regular intervals (default: 30 seconds)
3. Fetches device quota (status) information via GET requests
4. Parses power station telemetry data
5. Stores measurements in the `ecoflow_measurements` table

**Data Collection Method**: REST API polling (configurable interval via `REST_API_INTERVAL` environment variable)

## Prerequisites

### 1. EcoFlow Developer Account

You need to register as a developer with EcoFlow to obtain API credentials:

1. Go to [EcoFlow Developer Portal](https://developer.ecoflow.com/)
2. Sign up for a developer account
3. Create an application to get your credentials:
   - `access_key` (also called Access Key)
   - `secret_key` (also called Secret Key)

### 2. Device Serial Number

Find your EcoFlow device serial number:
- Check the device label
- Look in the EcoFlow mobile app (Device Settings → About)
- Format: Usually starts with device code (e.g., `R331ZEB...` for Delta Pro)

## Configuration

Set the following environment variables in your `compose/.env` file:

```bash
# EcoFlow Developer API Credentials
ECOFLOW_ACCESS_KEY=your_access_key_here
ECOFLOW_SECRET_KEY=your_secret_key_here

# Optional: Specific device serial number to monitor
# If not set, will collect data from all devices on your account
ECOFLOW_DEVICE_SN=R331ZEB4ZEA1234567
```

## Data Collected

The collector captures key metrics from your EcoFlow power station:

| Metric | Description | Unit |
|--------|-------------|------|
| `soc_percent` | State of Charge (battery level) | % |
| `remain_time_min` | Estimated remaining runtime | minutes |
| `watts_in_sum` | Total power input (charging) | watts |
| `watts_out_sum` | Total power output (load) | watts |
| `ac_out_watts` | AC output power | watts |
| `dc_out_watts` | DC output power | watts |
| `typec_out_watts` | USB-C output power | watts |
| `usb_out_watts` | USB-A output power | watts |
| `pv_in_watts` | Solar (PV) input power | watts |
| `raw_data` | Full JSON payload (for debugging) | JSONB |

## Database Schema

Data is stored in the `ecoflow_measurements` table:

```sql
CREATE TABLE ecoflow_measurements (
    id BIGSERIAL PRIMARY KEY,
    device_sn TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    soc_percent INTEGER,
    remain_time_min INTEGER,
    watts_in_sum INTEGER,
    watts_out_sum INTEGER,
    ac_out_watts INTEGER,
    dc_out_watts INTEGER,
    typec_out_watts INTEGER,
    usb_out_watts INTEGER,
    pv_in_watts INTEGER,
    raw_data JSONB
);
```

## Usage

### With Docker Compose

**Important**: The EcoFlow collector uses a Docker Compose profile and requires the `--profile ecoflow` flag:

```bash
# Start with the ecoflow profile enabled
docker compose --profile ecoflow -f compose/stack.yaml up -d ecoflow-collector

# Or start the full stack with ecoflow profile
docker compose --profile ecoflow -f compose/stack.yaml up -d
```

**Without the profile flag, the service will not start.** This is by design to keep the EcoFlow collector optional.

### Standalone Docker

```bash
cd stack/ecoflow-collector
docker build -t paku-ecoflow-collector .
docker run -e ECOFLOW_ACCESS_KEY="..." \
           -e ECOFLOW_SECRET_KEY="..." \
           -e PGHOST="postgres" \
           -e PGUSER="paku" \
           -e PGPASSWORD="paku" \
           -e PGDATABASE="paku" \
           paku-ecoflow-collector
```

## Troubleshooting

### Authentication Errors

If you see authentication errors:
- Verify your `ECOFLOW_ACCESS_KEY` and `ECOFLOW_SECRET_KEY` are correct
- Check that your developer account is active
- Ensure your application hasn't been revoked in the developer portal

### No Data Received

If connected but not receiving data:
- Verify your device is online and connected to EcoFlow cloud
- Check the device serial number is correct
- Look at MQTT topic subscriptions in logs
- Try removing `ECOFLOW_DEVICE_SN` to subscribe to all devices

### Connection Issues

If MQTT connection fails:
- Check your internet connectivity
- Verify firewall rules allow outbound port 8883 (MQTT over TLS)
- Check EcoFlow API status

### Viewing Logs

```bash
docker logs paku_ecoflow_collector
```

## Visualization

To visualize EcoFlow data in Grafana:

1. Access Grafana at `http://localhost:3000`
2. Create a new dashboard
3. Add panels with queries like:

```sql
-- Battery State of Charge over time
SELECT ts, soc_percent 
FROM ecoflow_measurements 
WHERE device_sn = 'YOUR_DEVICE_SN'
ORDER BY ts DESC
LIMIT 1000;

-- Power flow (in/out)
SELECT ts, watts_in_sum, watts_out_sum 
FROM ecoflow_measurements 
WHERE device_sn = 'YOUR_DEVICE_SN'
ORDER BY ts DESC
LIMIT 1000;
```

## Security Notes

- Never commit your `.env` file with API credentials
- API credentials provide access to control your devices - keep them secure
- Consider using read-only API keys if available
- Rotate credentials periodically
- MQTT credentials are temporary and auto-renewed by the service

## Supported Devices

This collector is designed for EcoFlow devices that support the official API:
- Delta Pro
- Delta Max
- Delta 2
- Delta 2 Max
- Delta 2 Pro
- River series (with API support)
- PowerStream

The exact fields available may vary by device model. The `raw_data` JSONB field captures the complete payload for reference.

## References

- [EcoFlow Developer Portal](https://developer.ecoflow.com/)
- [EcoFlow API Documentation](https://developer.ecoflow.com/us/document/introduction)
- [paho-mqtt Python Client](https://github.com/eclipse/paho.mqtt.python)
