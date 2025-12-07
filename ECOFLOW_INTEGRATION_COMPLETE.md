# EcoFlow Integration Complete

## Summary

Successfully implemented dual-mode EcoFlow data collection using both MQTT and REST API:

### Implementation Details

**1. MQTT Integration (Real-time)**
- Connects to EcoFlow OpenAPI MQTT broker
- Receives real-time updates when device is active
- Subscrates to `/open/{userId}/{deviceSN}/quota` topic
- Updates every 1-2 seconds when device is transmitting

**2. REST API Integration (Polling)**
- Polls EcoFlow REST API endpoint: `/iot-open/sign/device/quota/all`
- Fetches complete device state every 60 seconds (configurable)
- Provides data continuity when MQTT is quiet
- Can be enabled/disabled via `ECOFLOW_REST_API_ENABLED` env var

### Current Status ✅

**Data Collection:**
- ✅ MQTT receiving data successfully
- ✅ REST API polling working (every 60s)
- ✅ Data being stored to PostgreSQL
- ✅ SOC, temperature, power values flowing

**Database:**
- ✅ Table: `ecoflow_measurements`
- ✅ 70+ fields for comprehensive device monitoring
- ✅ Indexes on timestamp, device_sn for efficient queries

**Recent Data (as of 2025-12-07 17:07):**
```
SOC: 89%
Temperature: 14°C
PV Input: 281W (solar)
Power In: 1W
Power Out: 0-1W
```

### Configuration

Environment variables in compose file:
```yaml
ECOFLOW_ACCESS_KEY - OpenAPI access key
ECOFLOW_SECRET_KEY - OpenAPI secret key  
ECOFLOW_DEVICE_SN - Device serial number
ECOFLOW_API_URL - API endpoint (https://api.ecoflow.com for US, https://api-e.ecoflow.com for EU)
ECOFLOW_REST_API_ENABLED - Enable/disable REST polling (default: true)
ECOFLOW_REST_API_INTERVAL - Polling interval in seconds (default: 60)
```

### Architecture

```
EcoFlow Device (Delta Pro)
    ├─> MQTT Broker (real-time) ──> Collector Service
    └─> REST API (polling 60s) ──> Collector Service
                                        ↓
                                   PostgreSQL
                                        ↓
                                    Grafana Dashboards
```

### Data Flow

1. **MQTT Path**: Device → EcoFlow Cloud MQTT → paku_ecoflow_collector → PostgreSQL
2. **REST Path**: Device → EcoFlow Cloud API → paku_ecoflow_collector (polls every 60s) → PostgreSQL

### Grafana Dashboards

The system provides data to Grafana for visualization:
- Real-time power flow
- Battery SOC over time
- Input/output power graphs
- Temperature monitoring
- Solar (PV) input tracking

### Files Modified

1. `stack/ecoflow-collector/ecoflow_collector.py` - Main collector service
   - Added EcoFlowAPI class with REST API methods
   - Integrated MQTT and REST polling
   - Enhanced data parsing for all available fields

### Next Steps

To verify dashboards are working:
1. Open Grafana at http://your-server-ip:3000
2. Check EcoFlow dashboard
3. Verify data is displaying correctly
4. Check for graph errors

### Troubleshooting

**If no data appears:**
- Check collector logs: `docker logs paku_ecoflow_collector`
- Verify API credentials in compose file
- Check database for recent records: 
  ```sql
  SELECT * FROM ecoflow_measurements 
  WHERE ts > now() - interval '10 minutes' 
  ORDER BY ts DESC LIMIT 10;
  ```

**To adjust polling frequency:**
- Set `ECOFLOW_REST_API_INTERVAL=30` for 30-second polling
- Restart collector: `docker restart paku_ecoflow_collector`

**To disable REST API (use MQTT only):**
- Set `ECOFLOW_REST_API_ENABLED=false`
- Restart collector

### Known Limitations

1. OpenAPI provides less frequent updates than Consumer API
2. Some advanced metrics may not be available via OpenAPI
3. Polling interval should not be too aggressive to avoid rate limits

### Git Commits

- `7ff8b7c` - Add REST API polling alongside MQTT
- `7aab834` - Fix REST API initialization and add configurable interval

### Documentation References

- OpenAPI General Info: https://developer-eu.ecoflow.com/us/document/introduction
- Delta Pro Data Structure: https://developer-eu.ecoflow.com/us/document/deltapro
- OpenAPI Device Quota: https://developer-eu.ecoflow.com/us/document/generalInfo
