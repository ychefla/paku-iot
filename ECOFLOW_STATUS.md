# EcoFlow Integration Status

**Last Updated**: 2025-12-06 12:23 UTC

## Current Status: 🟡 DEPLOYED - AWAITING DATA

### Recent Changes (2025-12-06)
✅ Fixed MQTT topic subscription patterns
✅ Added comprehensive wildcard subscriptions  
✅ Improved logging for diagnostics
✅ Added check_ecoflow.sh troubleshooting script
✅ Pushed to main (auto-deployment triggered)

## Quick Status Check

On the server, run:
```bash
./scripts/check_ecoflow.sh
```

Or manually:
```bash
# 1. Check if collector is running
docker ps | grep ecoflow

# 2. View recent logs
docker logs --tail 50 paku_ecoflow_collector

# 3. Check for MQTT messages in logs
docker logs paku_ecoflow_collector | grep "Received MQTT message"

# 4. Query database for measurements
docker exec paku_postgres psql -U paku -d paku -c \
  "SELECT COUNT(*), MAX(ts) FROM ecoflow_measurements;"
```

## What Was Fixed

### Issue 1: Wrong MQTT Topic Patterns (FIXED ✓)
**Before**: Used simplified patterns that might not match EcoFlow's actual data stream
```python
topic = f"/app/device/property/{device_sn}"
```

**After**: Uses comprehensive wildcard patterns matching EcoFlow API docs
```python
# Primary - full wildcard for all device topics
topic1 = f"/app/{user_id}/{device_sn}/#"

# Secondary - simplified format
topic2 = f"/app/device/property/{device_sn}"

# Tertiary - quota information
topic3 = f"/open/{user_id}/{device_sn}/quota"
```

### Issue 2: User ID Extraction (FIXED ✓)
**Before**: Didn't properly extract user_id from certificateAccount

**After**: Extracts user_id correctly:
```python
cert_account = self.mqtt_credentials.get("certificateAccount", "")
if "/" in cert_account:
    user_id = cert_account.split("/")[0]
```

### Issue 3: Insufficient Logging (FIXED ✓)
**Before**: Limited visibility into what topics were subscribed to

**After**: Logs show:
- Certificate account value
- Extracted user_id
- Each subscription attempt
- Subscription results
- All incoming MQTT messages with topic and size

## Expected Log Output

After deployment, you should see:
```
[INFO] Starting EcoFlow Collector Service
[INFO] Connecting to Postgres at postgres:5432 db=paku
[INFO] Requesting MQTT credentials from EcoFlow API...
[INFO] Successfully obtained MQTT credentials
[INFO] MQTT info: host=mqtt-e.ecoflow.com port=8883
[INFO] Connecting to EcoFlow MQTT broker at mqtt-e.ecoflow.com:8883
[INFO] Connected to EcoFlow MQTT broker
[INFO] MQTT credentials info: certificateAccount=xxxxx/yyyyy
[INFO] Extracted user_id from certificateAccount: xxxxx
[INFO] Subscribing to device wildcard: /app/xxxxx/DCEBZ8ZE2110138/#
[INFO] Subscribe result for /app/xxxxx/DCEBZ8ZE2110138/#: (0, 1)
[INFO] Subscribing to simplified property: /app/device/property/DCEBZ8ZE2110138
[INFO] Subscribe result for /app/device/property/DCEBZ8ZE2110138: (0, 2)
[INFO] Subscribing to quota topic: /open/xxxxx/DCEBZ8ZE2110138/quota
[INFO] Subscribe result for /open/xxxxx/DCEBZ8ZE2110138/quota: (0, 3)
[INFO] Subscription confirmed: mid=1, codes=[...result codes...]
[INFO] Received MQTT message on topic: /app/.../thing/property/... (payload size: XXX bytes)
[INFO] Parsed data fields: {'device_sn': 'DCEBZ8ZE...', 'soc_percent': 85, ...}
[INFO] Inserted EcoFlow measurement for device=DCEBZ8ZE..., soc=85%
```

## Troubleshooting Steps

### If Container Not Running
```bash
# Start with ecoflow profile
cd /home/paku/paku-iot
docker compose -f compose/stack.prod.yaml --profile ecoflow up -d ecoflow-collector
```

### If Connected But No Data
1. **Check device is online**: Verify in EcoFlow app
2. **Check topics in logs**: Look for "Subscribing to..." messages
3. **Check for incoming messages**: Look for "Received MQTT message"
4. **Verify user_id extraction**: Check "Extracted user_id" log line
5. **Check certificateAccount format**: Should contain user_id

### If Logs Show Errors
- **401/403**: Check API credentials in .env
- **No connection**: Check network/firewall
- **Wrong topics**: Verify deviceSN matches your device
- **No messages**: Device may not be sending data (check if it's idle)

## Configuration Values

Current setup uses:
- **API Endpoint**: https://api-e.ecoflow.com (EU)
- **MQTT Broker**: mqtt-e.ecoflow.com:8883
- **Device SN**: DCEBZ8ZE2110138
- **Region**: Europe

## Next Steps

1. ⏳ Wait for GitHub Actions deployment to complete (~2-3 minutes)
2. 🔍 SSH to server and check logs: `ssh paku@server`
3. 📊 Check for data: Run check_ecoflow.sh script
4. 📈 View Grafana dashboard if data is flowing
5. 🐛 If issues persist, review troubleshooting steps above

## Known Limitations

- EcoFlow devices only send data when there's activity (charging/discharging)
- If device is idle (not charging/discharging), no updates will be sent
- Initial data might take a few minutes to appear after connecting

## References

- Full documentation: `docs/ecoflow_integration.md`
- API docs: https://developer-eu.ecoflow.com/us/document/introduction
- Troubleshooting script: `scripts/check_ecoflow.sh`
