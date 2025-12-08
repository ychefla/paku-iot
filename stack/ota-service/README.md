# OTA Service

REST API service for Over-The-Air (OTA) firmware updates for ESP devices.

## Features

- **Firmware Hosting**: Store and serve signed firmware artifacts
- **Version Management**: Track firmware releases with metadata and changelogs
- **Update Orchestration**: Control rollouts with targeting rules (all, canary, specific devices)
- **Status Tracking**: Monitor device update progress and results
- **Metrics & Monitoring**: Built-in metrics endpoint for observability

## Architecture

The OTA service provides two sets of APIs:

### Device-Facing APIs
- `GET /api/firmware/check` - Check for available updates
- `GET /api/firmware/download/{version}` - Download firmware binary
- `POST /api/device/{device_id}/update-status` - Report update status

### Admin/Management APIs
- `POST /api/admin/firmware/upload` - Upload new firmware release
- `GET /api/admin/firmware/releases` - List firmware releases
- `POST /api/admin/rollout/create` - Create rollout configuration
- `GET /api/admin/devices` - List registered devices
- `GET /api/admin/update-status` - Monitor update status

### Monitoring APIs
- `GET /health` - Health check
- `GET /metrics` - OTA metrics

## Configuration

Environment variables:

```bash
# Database (required)
PGHOST=postgres
PGPORT=5432
PGUSER=paku
PGPASSWORD=paku
PGDATABASE=paku

# Storage
FIRMWARE_STORAGE_PATH=/firmware

# Security (optional)
API_KEY=your-secret-api-key

# Server
PORT=8080
HOST=0.0.0.0
```

## Usage

### Device Update Flow

1. **Device checks for update**:
   ```
   GET /api/firmware/check?device_id=esp32_001&device_model=esp32&current_version=1.0.0
   ```

2. **Service checks rollout rules and returns update info**:
   ```json
   {
     "update_available": true,
     "current_version": "1.0.0",
     "latest_version": "1.1.0",
     "download_url": "/api/firmware/download/1.1.0",
     "file_size": 524288,
     "checksum_sha256": "abc123...",
     "release_notes": "Bug fixes and improvements"
   }
   ```

3. **Device downloads firmware**:
   ```
   GET /api/firmware/download/1.1.0
   ```

4. **Device reports progress**:
   ```
   POST /api/device/esp32_001/update-status
   {
     "device_id": "esp32_001",
     "firmware_version": "1.1.0",
     "status": "downloading",
     "progress_percent": 50
   }
   ```

5. **Device reports completion**:
   ```
   POST /api/device/esp32_001/update-status
   {
     "device_id": "esp32_001",
     "firmware_version": "1.1.0",
     "status": "success",
     "progress_percent": 100
   }
   ```

### Admin Workflows

#### Upload Firmware

```bash
curl -X POST "http://localhost:8080/api/admin/firmware/upload?version=1.1.0&device_model=esp32&is_signed=true" \
  -H "X-API-Key: your-api-key" \
  -F "file=@firmware.bin"
```

#### Create Rollout

**Full rollout to all devices:**
```bash
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "v1.1.0-production",
    "firmware_version": "1.1.0",
    "device_model": "esp32",
    "target_type": "all",
    "rollout_percentage": 100,
    "is_active": true
  }'
```

**Canary rollout to 10% of devices:**
```bash
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "v1.1.0-canary",
    "firmware_version": "1.1.0",
    "device_model": "esp32",
    "target_type": "canary",
    "rollout_percentage": 10,
    "is_active": true
  }'
```

**Specific devices:**
```bash
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "v1.1.0-test-devices",
    "firmware_version": "1.1.0",
    "device_model": "esp32",
    "target_type": "specific",
    "target_filter": {
      "device_ids": ["esp32_001", "esp32_002", "esp32_003"]
    },
    "is_active": true
  }'
```

#### Monitor Updates

```bash
# List all devices
curl "http://localhost:8080/api/admin/devices?limit=100"

# Get update status for specific device
curl "http://localhost:8080/api/admin/update-status?device_id=esp32_001"

# Get metrics
curl "http://localhost:8080/metrics"
```

## Rollout Strategies

### Target Types

1. **all**: All devices of specified model
2. **canary**: Percentage-based rollout using consistent hashing
3. **specific**: Explicit list of device IDs
4. **group**: Device group membership (requires metadata setup)

### Rollout Percentage

For `all` and `canary` target types, the `rollout_percentage` parameter controls what percentage of devices receive the update. The service uses consistent hashing to ensure:
- Same devices always fall in the same percentage bucket
- Gradual rollout increases are possible (e.g., 10% → 25% → 50% → 100%)
- Distribution is even across device population

## Security

### Authentication

Admin endpoints require API key authentication via `X-API-Key` header. Set the `API_KEY` environment variable to enable.

Device-facing endpoints are currently open but should be secured with:
- TLS/HTTPS in production
- Device authentication tokens
- Rate limiting

### Firmware Signing

The service supports signed firmware via the `is_signed` flag. Implement signature verification on the device side using:
- RSA or ECDSA signatures
- Public key embedded in device bootloader
- Signature verification before applying update

### Best Practices

1. **Always sign firmware** in production
2. **Use TLS/HTTPS** for all communications
3. **Implement mutual TLS** for device authentication
4. **Start with canary rollouts** for new firmware
5. **Monitor metrics** during rollouts
6. **Have rollback plan** ready

## Database Schema

The service uses these PostgreSQL tables:

- `firmware_releases`: Firmware metadata and versions
- `devices`: Device registry and current firmware tracking
- `device_update_status`: Update progress and results
- `rollout_configurations`: Rollout rules and targeting
- `ota_events`: Audit log of all OTA activities

See `stack/postgres/ota_schema.sql` for full schema.

## Monitoring

### Metrics Endpoint

`GET /metrics` returns:

```json
{
  "total_devices": 100,
  "devices_by_model": {
    "esp32": 80,
    "esp8266": 20
  },
  "recent_updates_24h": {
    "success": 45,
    "failed": 2,
    "downloading": 3
  },
  "active_rollouts": 2
}
```

### Grafana Dashboard

Create dashboards to monitor:
- Active device count by model
- Update success/failure rates
- Average update duration
- Firmware version distribution
- Rollout progress

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PGHOST=localhost
export PGUSER=paku
export PGPASSWORD=paku
export PGDATABASE=paku
export API_KEY=test-key

# Run service
python ota_service.py
```

### Testing

```bash
# Health check
curl http://localhost:8080/health

# Check update (no auth required)
curl "http://localhost:8080/api/firmware/check?device_id=test001&device_model=esp32&current_version=1.0.0"

# Upload firmware (requires API key)
curl -X POST "http://localhost:8080/api/admin/firmware/upload?version=1.0.0&device_model=esp32" \
  -H "X-API-Key: test-key" \
  -F "file=@test_firmware.bin"
```

## Integration with ESP Devices

See the companion `paku-core` repository for ESP32/ESP8266 OTA client implementation.

Basic ESP integration:

```cpp
#include <HTTPClient.h>
#include <Update.h>

void checkForUpdate() {
    HTTPClient http;
    String url = "http://ota-service:8080/api/firmware/check";
    url += "?device_id=" + getDeviceId();
    url += "&device_model=esp32";
    url += "&current_version=" + FIRMWARE_VERSION;
    
    http.begin(url);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, http.getString());
        
        if (doc["update_available"]) {
            String downloadUrl = doc["download_url"];
            performOTA(downloadUrl);
        }
    }
    http.end();
}
```

## Troubleshooting

### No updates offered to devices

1. Check rollout configuration is active
2. Verify device model matches firmware release
3. Check rollout targeting includes the device
4. Review logs: `docker logs paku_ota_service`

### Firmware download fails

1. Verify firmware file exists in storage path
2. Check file permissions
3. Verify file path in database matches actual location

### Database connection errors

1. Ensure PostgreSQL is running and accessible
2. Verify credentials in environment variables
3. Check network connectivity between containers
