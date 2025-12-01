# EcoFlow Quick Start Guide

Get your EcoFlow power station data into paku-iot in 5 minutes!

## Prerequisites

✅ EcoFlow power station (Delta Pro, Delta Max, Delta 2, River, etc.)  
✅ Device connected to WiFi and linked to EcoFlow app  
✅ paku-iot stack already set up

## Step 1: Get API Credentials (2 minutes)

1. Go to [EcoFlow Developer Portal](https://developer.ecoflow.com/)
2. Sign up / Log in
3. Create a new application
4. Copy your **Access Key** and **Secret Key**

## Step 2: Configure (1 minute)

Edit `compose/.env`:

```bash
# Add these lines:
ECOFLOW_ACCESS_KEY=your_access_key_here
ECOFLOW_SECRET_KEY=your_secret_key_here
ECOFLOW_DEVICE_SN=your_device_serial_number  # Optional
```

## Step 3: Start the Collector (1 minute)

```bash
# Start the full stack with EcoFlow collector
docker compose --profile ecoflow -f compose/stack.yaml up -d

# Or just the collector if stack is already running
docker compose --profile ecoflow -f compose/stack.yaml up -d ecoflow-collector
```

## Step 4: Verify (1 minute)

Check logs:
```bash
docker logs -f paku_ecoflow_collector
```

You should see:
```
[INFO] Connected to EcoFlow MQTT broker
[INFO] Inserted EcoFlow measurement for device=R331ZEB..., soc=85%
```

Query data:
```bash
docker exec -it paku_postgres psql -U paku -d paku
```

```sql
SELECT device_sn, soc_percent, watts_out_sum, ts 
FROM ecoflow_measurements 
ORDER BY ts DESC LIMIT 5;
```

## Step 5: Visualize in Grafana

1. Open http://localhost:3000
2. Create a new dashboard
3. Add a panel with this query:

```sql
SELECT 
    ts as time,
    soc_percent as "Battery %"
FROM ecoflow_measurements
WHERE $__timeFilter(ts)
ORDER BY ts
```

4. Set visualization to "Time series"

## That's it! 🎉

Your EcoFlow data is now flowing into paku-iot.

## Troubleshooting

**No data appearing?**
- Check device is online in EcoFlow app
- Verify credentials in `.env` are correct
- Check logs for errors: `docker logs paku_ecoflow_collector`

**Authentication failed?**
- Ensure Access Key and Secret Key are correct
- Check for extra spaces or quotes in `.env`
- Verify developer account is active

**Need help?**
- See full guide: [docs/ecoflow_integration.md](docs/ecoflow_integration.md)
- Check technical details: [docs/ecoflow_technical_notes.md](docs/ecoflow_technical_notes.md)

## What Data is Collected?

- Battery level (%)
- Power input/output (watts)
- Solar input (watts)
- Estimated runtime
- USB/AC/DC port usage
- Full device state (JSON)

## Next Steps

- Create more Grafana dashboards
- Set up alerts for low battery
- Export data for analysis
- Add multiple devices

For complete documentation, see [docs/ecoflow_integration.md](docs/ecoflow_integration.md)
