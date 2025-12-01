# EcoFlow Integration - Technical Notes

## Implementation Overview

This document provides technical details about the EcoFlow Delta Pro integration implementation for developers and contributors.

## Architecture Decisions

### Why MQTT over REST API Polling?

We chose the MQTT approach for the following reasons:

1. **Real-time Updates**: MQTT provides push-based updates as soon as device state changes
2. **Efficiency**: Lower bandwidth and latency compared to polling
3. **Consistency**: Follows the same pattern as the existing Ruuvi collector
4. **Battery-friendly**: Device doesn't need to serve HTTP requests
5. **EcoFlow Native**: EcoFlow devices natively publish to MQTT broker

### Why Store Raw JSON?

The `raw_data` JSONB column stores the complete payload because:

1. **Future-proofing**: Device models have different available fields
2. **Debugging**: Full context available for troubleshooting
3. **Schema Evolution**: Can add new fields without schema migration
4. **Device Variations**: Different models report different metrics
5. **Flexibility**: Custom queries on raw data using PostgreSQL JSONB operators

## Data Flow

```
1. Service Startup
   ├── Load environment variables (API keys)
   ├── Connect to PostgreSQL
   └── Initialize EcoFlow API client

2. MQTT Authentication
   ├── Request temporary MQTT credentials from EcoFlow API
   │   └── POST to https://api.ecoflow.com/iot-open/sign/certification
   ├── Receive MQTT connection details (host, port, username, password)
   └── Credentials are valid for several hours (auto-renewed if needed)

3. MQTT Connection
   ├── Connect to mqtt.ecoflow.com:8883 (MQTT over TLS)
   ├── Authenticate with temporary credentials
   └── Subscribe to device topic(s)

4. Message Processing
   ├── Receive MQTT message (JSON payload)
   ├── Parse device serial number from topic or payload
   ├── Extract key metrics from nested JSON structure
   ├── Insert into ecoflow_measurements table
   └── Log success/failure
```

## API Endpoints Used

### EcoFlow API

**Endpoint**: `GET https://api.ecoflow.com/iot-open/sign/certification`

**Authentication**: HMAC-SHA256 signature

**Query Parameters**:
- `accessKey`: Your EcoFlow Developer API access key
- `nonce`: Random 16-character string
- `timestamp`: Current time in milliseconds (Unix epoch * 1000)
- `sign`: HMAC-SHA256 signature of sorted parameters

**Signature Generation**:
```python
# 1. Create parameter dict (without sign)
params = {
    "accessKey": "<your_access_key>",
    "nonce": "<random_16_chars>",
    "timestamp": "<current_time_ms>"
}

# 2. Sort parameters alphabetically and concatenate
param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
# Example: "accessKey=ak_xxx&nonce=abc123&timestamp=1733097600000"

# 3. Generate HMAC-SHA256 signature using secret key
import hmac
import hashlib
sign = hmac.new(
    secret_key.encode('utf-8'),
    param_str.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# 4. Add signature to parameters
params["sign"] = sign
```

**Example Request**:
```
GET https://api.ecoflow.com/iot-open/sign/certification?accessKey=ak_us_xxx&nonce=abc123def456&timestamp=1733097600000&sign=sha256_hash_here
```

**Response** (success):
```json
{
  "code": "0",
  "message": "Success",
  "data": {
    "url": "mqtt.ecoflow.com",
    "port": 8883,
    "protocol": "mqtts",
    "username": "temp_user_xxxxx",
    "password": "temp_pass_xxxxx",
    "clientId": "unique_client_id"
  }
}
```

**Note**: The EcoFlow API changed from POST to GET with signature-based authentication in late 2024/early 2025. The old POST method with header-based auth is no longer supported (returns HTTP 405).

## MQTT Topics

EcoFlow uses multiple topic patterns depending on the API version and device:

### Topic Patterns

1. **App API topics**: `/app/{user_id}/{device_sn}/thing/property/set`
2. **Open API topics**: `/open/{user_id}/{device_sn}/quota`
3. **Status updates**: `/app/device/property/{device_sn}`

Our implementation subscribes to: `/app/+/{device_sn}/+` (wildcard for flexibility)

### Message Format

```json
{
  "sn": "R331ZEB4ZEA0012345",
  "params": {
    "soc": 85,
    "remainTime": 407,
    "wattsInSum": 120,
    "wattsOutSum": 300,
    "invOutWatts": 280,
    "dcOutWatts": 20,
    "typecOutWatts": 18,
    "usbOutWatts": 2,
    "pvInWatts": 100,
    "bmsMaster": {
      "soc": 85,
      "vol": 54000,
      "amp": 2200,
      "temp": 25
    },
    "inv": {
      "inputWatts": 120,
      "outputWatts": 300,
      "cfgAcOutVol": 230
    },
    "mppt": {
      "inWatts": 100,
      "outVol": 54000
    }
  }
}
```

## Field Mappings

### Delta Pro Fields

| Database Column | JSON Path | Fallback | Description |
|----------------|-----------|----------|-------------|
| `device_sn` | `sn` | Topic parsing | Device serial number |
| `soc_percent` | `params.soc` | `params.bmsMaster.soc` | Battery state of charge |
| `remain_time_min` | `params.remainTime` | - | Estimated runtime |
| `watts_in_sum` | `params.wattsInSum` | `params.inv.inputWatts` | Total input power |
| `watts_out_sum` | `params.wattsOutSum` | `params.inv.outputWatts` | Total output power |
| `ac_out_watts` | `params.invOutWatts` | - | AC outlet power |
| `dc_out_watts` | `params.dcOutWatts` | - | DC outlet power |
| `typec_out_watts` | `params.typecOutWatts` | - | USB-C power |
| `usb_out_watts` | `params.usbOutWatts` | - | USB-A power |
| `pv_in_watts` | `params.pvInWatts` | `params.pv.inputWatts` | Solar input |

**Note**: Different device models may use different field names or structures.

## Database Schema Details

### Table: ecoflow_measurements

**Primary Key**: `id` (BIGSERIAL, auto-incrementing)

**Indexes**:
1. `idx_ecoflow_measurements_ts` - Time-based queries
2. `idx_ecoflow_measurements_device_sn` - Device filtering
3. `idx_ecoflow_measurements_device_ts` - Combined device + time queries

**Data Types**:
- All power values: `INTEGER` (watts)
- Battery level: `INTEGER` (percentage, 0-100)
- Timestamps: `TIMESTAMPTZ` (with timezone)
- Raw data: `JSONB` (indexed for fast queries)

### Storage Considerations

**Typical row size**: ~200 bytes + JSON size (~1-5 KB)
**Daily storage** (1 reading/min): ~2-7 MB per device
**Monthly storage**: ~60-210 MB per device
**Yearly storage**: ~0.7-2.5 GB per device

## Security Considerations

### Credentials Storage

- API keys stored in `.env` file (git-ignored)
- Never logged or exposed in error messages
- MQTT passwords are temporary and auto-expire
- TLS encryption for all API and MQTT traffic

### Network Security

- Outbound HTTPS (443) to api.ecoflow.com
- Outbound MQTTS (8883) to mqtt.ecoflow.com
- Both use TLS 1.2+ with certificate verification
- No inbound connections required

### Database Security

- Use strong PostgreSQL passwords
- Connection from Docker network only
- Prepared statements (no SQL injection risk)
- JSONB data is sanitized by PostgreSQL

## Error Handling

### Retry Logic

The collector handles various failure modes:

1. **API Authentication Failure**: Logs error and exits (manual fix required)
2. **MQTT Connection Failure**: Paho client auto-reconnects
3. **Network Interruption**: Reconnects when network restored
4. **Database Connection Loss**: Errors logged, messages dropped
5. **Invalid Payload**: Logged and skipped, doesn't crash

### Logging Levels

- `INFO`: Normal operations, connection status, insertions
- `WARNING`: Invalid payloads, disconnections
- `ERROR`: Authentication failures, database errors
- `DEBUG`: Full message payloads, detailed parsing

## Performance

### Resource Usage

**CPU**: ~1-2% idle, <5% when processing messages
**Memory**: ~50-100 MB
**Network**: ~1-10 KB/minute per device
**Database**: ~100-500 rows/hour per device

### Optimization

- Connection pooling: Single persistent DB connection
- Batch insertions: Could be added for high-frequency updates
- Index strategy: Optimized for time-series queries
- JSONB storage: Compressed and indexed

## Testing

### Unit Testing

Currently manual testing via `test_config.py`. Future enhancements:

```python
# Example unit tests to add
def test_parse_ecoflow_payload():
    """Test payload parsing with various device models."""
    
def test_mqtt_connection_retry():
    """Test reconnection logic."""
    
def test_database_insertion():
    """Test database insert with mock data."""
```

### Integration Testing

To test the full flow:

1. Set up test EcoFlow account with demo device
2. Configure collector with test credentials
3. Verify data appears in database
4. Check Grafana dashboards

### Manual Testing Checklist

- [ ] Environment variables validation
- [ ] API authentication
- [ ] MQTT connection
- [ ] Message reception
- [ ] Database insertion
- [ ] Grafana visualization
- [ ] Error recovery (network disconnect)
- [ ] Multiple devices
- [ ] Different device models

## Extending the Integration

### Adding New Device Models

1. Capture raw payload from `raw_data` column
2. Identify new fields in payload
3. Add field mappings to `parse_ecoflow_payload()`
4. Consider adding new columns if fields are standard

### Adding Downlink Commands

EcoFlow API supports sending commands to devices:

```python
# Example: Turn on AC output
def send_command(device_sn, command):
    topic = f"/app/{user_id}/{device_sn}/thing/property/set"
    payload = {"sn": device_sn, "cmd": command}
    client.publish(topic, json.dumps(payload))
```

**Note**: Requires additional API permissions and testing.

### Historical Data Import

To backfill historical data:

1. Use EcoFlow REST API's historical endpoints
2. Query data by time range
3. Transform to match database schema
4. Insert with original timestamps

## Troubleshooting Development Issues

### "No matching distribution" (pip install)

This is often a network/SSL issue in build environment. Try:
- Build with `--network=host`
- Use a pip mirror
- Check firewall/proxy settings

### "Certificate verification failed"

For development only:
```python
# Temporary workaround (not for production)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### "Table does not exist"

Ensure `init.sql` has been run:
```bash
docker exec -it paku_postgres psql -U paku -d paku -f /docker-entrypoint-initdb.d/init.sql
```

## Future Enhancements

### Planned Features

1. **Alert System**: Notifications for low battery, high load
2. **REST API**: HTTP endpoint to query device status
3. **Historical Analysis**: Energy usage reports, trends
4. **Multi-site**: Support for multiple locations
5. **Device Registry**: Database of known devices
6. **Configuration UI**: Web interface for setup
7. **Webhook Support**: Push data to external services
8. **Data Export**: CSV/JSON export for analysis

### Performance Improvements

1. **Batch Inserts**: Buffer messages, insert in batches
2. **Time-series DB**: Migrate to TimescaleDB for better performance
3. **Caching**: Redis for frequently accessed data
4. **Compression**: Archive old data with compression

## References

### EcoFlow API Documentation

- [Developer Portal](https://developer.ecoflow.com/)
- [API Documentation](https://developer.ecoflow.com/us/document/introduction)
- [MQTT Integration Guide](https://developer.ecoflow.com/us/document/mqttIntroduction)

### Dependencies

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) - MQTT client
- [psycopg](https://www.psycopg.org/psycopg3/) - PostgreSQL adapter
- [requests](https://requests.readthedocs.io/) - HTTP library

### Similar Projects

- [Home Assistant EcoFlow Integration](https://github.com/tolwi/hassio-ecoflow-cloud)
- [Node-RED EcoFlow Nodes](https://flows.nodered.org/node/@rotflorg/node-red-contrib-ecoflow-powerstream)
- [ioBroker EcoFlow Adapter](https://github.com/foxthefox/ioBroker.ecoflow-mqtt)

## Contributing

When contributing to the EcoFlow integration:

1. **Test thoroughly**: Multiple device models if possible
2. **Update docs**: Keep documentation in sync with code
3. **Preserve compatibility**: Don't break existing installations
4. **Security first**: Never expose credentials or create vulnerabilities
5. **Follow patterns**: Match existing collector architecture

## Contact

For questions or issues specific to this integration:
- Open an issue on GitHub
- Tag with `ecoflow` label
- Include device model and error logs
