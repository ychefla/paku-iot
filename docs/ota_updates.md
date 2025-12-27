# OTA (Over-The-Air) Updates for ESP Devices

This document describes the OTA update system for ESP devices in the Paku IoT platform.

## Overview

The OTA update system enables secure, automated firmware updates for ESP32/ESP8266 devices deployed in the field. It provides:

- **Firmware Hosting**: Centralized storage and serving of signed firmware artifacts
- **Version Management**: Track releases, compatibility, and changelogs
- **Rollout Orchestration**: Control which devices receive updates and when
- **Status Monitoring**: Track update progress and success rates
- **Rollback Support**: Ability to halt or reverse problematic rollouts

## Architecture

```
┌──────────────┐
│ ESP Devices  │
│              │
│ 1. Check for │──────┐
│    updates   │      │
│              │      │
│ 2. Download  │      │
│    firmware  │      │
│              │      │
│ 3. Report    │      │
│    status    │      │
└──────────────┘      │
                      │
                      │ HTTPS
                      │
                      ▼
              ┌───────────────┐
              │  OTA Service  │
              │   (FastAPI)   │
              │               │
              │ - Check API   │
              │ - Download    │
              │ - Status      │
              └───────┬───────┘
                      │
                      │
                      ▼
              ┌───────────────┐
              │  PostgreSQL   │
              │               │
              │ - Releases    │
              │ - Devices     │
              │ - Rollouts    │
              │ - Status      │
              └───────────────┘
                      │
                      │
                      ▼
              ┌───────────────┐
              │    Grafana    │
              │  (Dashboard)  │
              │               │
              │ - Metrics     │
              │ - Monitoring  │
              └───────────────┘
```

## Getting Started

### 1. Start the OTA Service

The OTA service is included in the main Docker Compose stack:

```bash
cd compose
docker compose -f stack.yaml up -d
```

The service will be available at:
- Device API: `http://localhost:8080/api/firmware/*`
- Admin API: `http://localhost:8080/api/admin/*`
- Metrics: `http://localhost:8080/metrics`
- Health: `http://localhost:8080/health`

### 2. Upload Firmware

Upload a new firmware release using the admin API:

```bash
curl -X POST "http://localhost:8080/api/admin/firmware/upload?version=1.0.0&device_model=esp32&is_signed=true&release_notes=Initial+release" \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "file=@path/to/firmware.bin"
```

### 3. Create a Rollout

Create a rollout configuration to control which devices receive the update:

**Test rollout to specific devices:**
```bash
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "name": "v1.0.0-test",
    "firmware_version": "1.0.0",
    "device_model": "esp32",
    "target_type": "specific",
    "target_filter": {"device_ids": ["esp32_001", "esp32_002"]},
    "is_active": true
  }'
```

**Canary rollout to 10% of devices:**
```bash
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "name": "v1.0.0-canary",
    "firmware_version": "1.0.0",
    "device_model": "esp32",
    "target_type": "canary",
    "rollout_percentage": 10,
    "is_active": true
  }'
```

**Full production rollout:**
```bash
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "name": "v1.0.0-production",
    "firmware_version": "1.0.0",
    "device_model": "esp32",
    "target_type": "all",
    "rollout_percentage": 100,
    "is_active": true
  }'
```

### 4. Monitor Updates

Check update status through the admin API:

```bash
# List all devices
curl "http://localhost:8080/api/admin/devices"

# Get update status
curl "http://localhost:8080/api/admin/update-status?limit=50"

# Get metrics
curl "http://localhost:8080/metrics"
```

### 5. Manage Device Groups (Optional)

Device groups enable targeting updates to specific sets of devices based on their metadata (e.g., location, function, environment). Groups are stored in the device's metadata JSONB field in the database.

**Setting device groups:**

Devices are automatically registered when they check for updates. To assign groups to a device, update its metadata in the database:

```sql
-- Assign groups to a device
UPDATE devices 
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{groups}',
    '["location:warehouse", "function:sensor", "env:production"]'::jsonb
)
WHERE device_id = 'esp32_001';

-- Query devices by group
SELECT device_id, device_model, metadata->'groups' as groups
FROM devices
WHERE metadata->'groups' ? 'location:warehouse';
```

**Creating a group-based rollout:**

```bash
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "name": "v1.0.0-warehouse-sensors",
    "firmware_version": "1.0.0",
    "device_model": "esp32",
    "target_type": "group",
    "target_filter": {"groups": ["location:warehouse", "function:sensor"]},
    "rollout_percentage": 100,
    "is_active": true
  }'
```

**How group targeting works:**
- A device matches if it belongs to **ANY** of the specified groups (OR logic)
- Example: `target_filter: {"groups": ["location:warehouse", "function:sensor"]}` matches devices with either group
- The `rollout_percentage` applies to devices that match the group criteria
- Devices without metadata or groups are excluded from group-based rollouts

## Device Integration

### ESP32/ESP8266 Client Code

Devices should periodically check for updates and report their status. Example Arduino/ESP-IDF code:

```cpp
#include <HTTPClient.h>
#include <Update.h>
#include <ArduinoJson.h>

const char* OTA_SERVER = "http://ota-service:8080";
const char* DEVICE_ID = "esp32_001";
const char* DEVICE_MODEL = "esp32";
const char* CURRENT_VERSION = "1.0.0";

void checkForOTAUpdate() {
    HTTPClient http;
    
    // Build check URL
    String url = String(OTA_SERVER) + "/api/firmware/check";
    url += "?device_id=" + String(DEVICE_ID);
    url += "&device_model=" + String(DEVICE_MODEL);
    url += "&current_version=" + String(CURRENT_VERSION);
    
    Serial.println("Checking for OTA updates...");
    http.begin(url);
    
    int httpCode = http.GET();
    if (httpCode != 200) {
        Serial.printf("Check failed: %d\n", httpCode);
        http.end();
        return;
    }
    
    // Parse response
    DynamicJsonDocument doc(2048);
    DeserializationError error = deserializeJson(doc, http.getString());
    http.end();
    
    if (error) {
        Serial.println("JSON parse error");
        return;
    }
    
    // Check if update available
    if (!doc["update_available"].as<bool>()) {
        Serial.println("No update available");
        return;
    }
    
    // Get update info
    String newVersion = doc["latest_version"].as<String>();
    String downloadUrl = doc["download_url"].as<String>();
    String checksum = doc["checksum_sha256"].as<String>();
    
    Serial.printf("Update available: %s -> %s\n", CURRENT_VERSION, newVersion.c_str());
    
    // Perform OTA update
    performOTA(downloadUrl, checksum, newVersion);
}

void performOTA(String downloadUrl, String checksum, String version) {
    HTTPClient http;
    
    // Report downloading status
    reportStatus(version, "downloading", 0);
    
    String url = String(OTA_SERVER) + downloadUrl;
    http.begin(url);
    
    int httpCode = http.GET();
    if (httpCode != 200) {
        Serial.printf("Download failed: %d\n", httpCode);
        reportStatus(version, "failed", 0);
        http.end();
        return;
    }
    
    int contentLength = http.getSize();
    
    // Start OTA update
    if (!Update.begin(contentLength)) {
        Serial.println("Not enough space");
        reportStatus(version, "failed", 0);
        http.end();
        return;
    }
    
    // Download and write firmware
    WiFiClient* client = http.getStreamPtr();
    size_t written = 0;
    uint8_t buffer[128];
    
    while (http.connected() && (written < contentLength)) {
        size_t available = client->available();
        if (available) {
            int bytesRead = client->readBytes(buffer, min(available, sizeof(buffer)));
            Update.write(buffer, bytesRead);
            written += bytesRead;
            
            // Report progress every 10%
            int progress = (written * 100) / contentLength;
            static int lastProgress = 0;
            if (progress >= lastProgress + 10) {
                reportStatus(version, "downloading", progress);
                lastProgress = progress;
            }
        }
        delay(1);
    }
    
    http.end();
    
    if (written != contentLength) {
        Serial.println("Download incomplete");
        reportStatus(version, "failed", 0);
        return;
    }
    
    // Finalize and verify
    reportStatus(version, "installing", 100);
    
    if (!Update.end(true)) {
        Serial.printf("Update error: %s\n", Update.errorString());
        reportStatus(version, "failed", 100);
        return;
    }
    
    // Success - report and reboot
    reportStatus(version, "success", 100);
    Serial.println("Update successful, rebooting...");
    delay(1000);
    ESP.restart();
}

void reportStatus(String version, String status, int progress) {
    HTTPClient http;
    
    String url = String(OTA_SERVER) + "/api/device/" + String(DEVICE_ID) + "/update-status";
    
    DynamicJsonDocument doc(512);
    doc["device_id"] = DEVICE_ID;
    doc["firmware_version"] = version;
    doc["status"] = status;
    doc["progress_percent"] = progress;
    
    String jsonStr;
    serializeJson(doc, jsonStr);
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    
    int httpCode = http.POST(jsonStr);
    if (httpCode != 200) {
        Serial.printf("Status report failed: %d\n", httpCode);
    }
    
    http.end();
}

void setup() {
    Serial.begin(115200);
    
    // WiFi setup
    WiFi.begin("SSID", "password");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
    }
    
    // Check for updates on startup
    checkForOTAUpdate();
}

void loop() {
    // Check for updates periodically (e.g., every hour)
    static unsigned long lastCheck = 0;
    if (millis() - lastCheck > 3600000) {
        checkForOTAUpdate();
        lastCheck = millis();
    }
    
    // Your application code here
    delay(100);
}
```

## Rollout Strategies

### 1. Test Rollout (Specific Devices)

Best for: Initial testing with known test devices

```json
{
  "target_type": "specific",
  "target_filter": {
    "device_ids": ["esp32_test1", "esp32_test2"]
  }
}
```

### 2. Canary Rollout (Percentage-Based)

Best for: Gradual rollout with risk mitigation

```json
{
  "target_type": "canary",
  "rollout_percentage": 10
}
```

Start with 10%, monitor for issues, then increase to 25%, 50%, 100%.

### 3. Full Production Rollout

Best for: Well-tested updates ready for all devices

```json
{
  "target_type": "all",
  "rollout_percentage": 100
}
```

### 4. Group-Based Rollout

Best for: Targeting devices by location or function

```json
{
  "target_type": "group",
  "target_filter": {
    "groups": ["location:warehouse", "function:sensor"]
  },
  "rollout_percentage": 100
}
```

**Example use cases:**
- Deploy updates to all sensors in a specific location: `{"groups": ["location:warehouse"]}`
- Target devices by environment: `{"groups": ["env:production"]}`
- Update specific device functions: `{"groups": ["function:gateway", "function:sensor"]}`
- Combine criteria: `{"groups": ["location:warehouse", "env:production"]}`

**Phased group rollout:**
Start with a small percentage of the group, then increase:
```bash
# Phase 1: 25% of warehouse sensors
curl -X POST "http://localhost:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{
    "name": "v1.2.0-warehouse-phase1",
    "firmware_version": "1.2.0",
    "device_model": "esp32",
    "target_type": "group",
    "target_filter": {"groups": ["location:warehouse"]},
    "rollout_percentage": 25,
    "is_active": true
  }'

# Phase 2: Increase to 100% after monitoring Phase 1
curl -X PATCH "http://localhost:8080/api/admin/rollout/v1.2.0-warehouse-phase1" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-here" \
  -d '{"rollout_percentage": 100}'
```

## Security Best Practices

### 1. Firmware Signing

**Always sign firmware binaries** in production:

```bash
# Generate signing key (one-time)
openssl genrsa -out firmware_signing_key.pem 2048
openssl rsa -in firmware_signing_key.pem -pubout -out firmware_public_key.pem

# Sign firmware
openssl dgst -sha256 -sign firmware_signing_key.pem -out firmware.sig firmware.bin

# Embed public key in device bootloader for verification
```

Device verification code:
```cpp
bool verifyFirmwareSignature(uint8_t* firmware, size_t size, uint8_t* signature) {
    // Verify signature using embedded public key
    // Only apply update if signature is valid
    return mbedtls_rsa_pkcs1_verify(...) == 0;
}
```

### 2. TLS/HTTPS

Use HTTPS for all OTA communications in production:

```cpp
WiFiClientSecure client;
client.setCACert(root_ca);  // Pin server certificate
```

### 3. Device Authentication

Implement device authentication using:
- Device-specific API tokens
- Mutual TLS (mTLS) with client certificates
- HMAC-based authentication

### 4. Rollback Protection

Implement rollback protection to prevent downgrade attacks:

```cpp
// Store minimum firmware version in protected flash
const uint32_t MIN_FIRMWARE_VERSION = 1000;  // v1.0.0

bool validateNewFirmware(uint32_t newVersion) {
    return newVersion >= MIN_FIRMWARE_VERSION;
}
```

### 5. Rate Limiting

Protect the OTA service with rate limiting:
- Per-device request limits
- Global bandwidth limits
- Exponential backoff on failures

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Update Success Rate**: Percentage of successful updates
2. **Update Duration**: Time to complete updates
3. **Failure Rate**: Failed update attempts
4. **Device Distribution**: Firmware versions in fleet
5. **Rollout Progress**: Percentage of devices updated

### Grafana Dashboard

Create a Grafana dashboard with panels for:

```sql
-- Total devices by firmware version
SELECT 
    current_firmware_version,
    COUNT(*) as device_count
FROM devices
GROUP BY current_firmware_version
ORDER BY device_count DESC;

-- Update success rate (last 24h)
SELECT 
    status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM device_update_status
WHERE reported_at > NOW() - INTERVAL '24 hours'
    AND status IN ('success', 'failed')
GROUP BY status;

-- Recent update activity
SELECT 
    DATE_TRUNC('hour', reported_at) as hour,
    status,
    COUNT(*) as count
FROM device_update_status
WHERE reported_at > NOW() - INTERVAL '7 days'
GROUP BY hour, status
ORDER BY hour DESC;

-- Devices needing updates
SELECT 
    d.device_id,
    d.device_model,
    d.current_firmware_version,
    fr.version as latest_version,
    d.last_seen
FROM devices d
JOIN firmware_releases fr ON d.device_model = fr.device_model
WHERE d.current_firmware_version != fr.version
    AND fr.created_at = (
        SELECT MAX(created_at) 
        FROM firmware_releases 
        WHERE device_model = d.device_model
    )
ORDER BY d.last_seen DESC;
```

### Alert Conditions

Set up alerts for:
- Update failure rate > 5%
- Device offline > 24 hours after update
- Rollout stuck (no progress for X hours)
- Storage space low for firmware artifacts

## CI/CD Integration

### Automated Firmware Build & Upload

Example GitHub Actions workflow:

```yaml
name: Build and Release Firmware

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build firmware
        run: |
          platformio run --environment esp32
          
      - name: Sign firmware
        run: |
          openssl dgst -sha256 -sign ${{ secrets.SIGNING_KEY }} \
            -out firmware.sig .pio/build/esp32/firmware.bin
      
      - name: Upload to OTA service
        env:
          OTA_API_KEY: ${{ secrets.OTA_API_KEY }}
          VERSION: ${{ github.ref_name }}
        run: |
          curl -X POST \
            "https://ota.paku-iot.example.com/api/admin/firmware/upload?version=${VERSION}&device_model=esp32&is_signed=true" \
            -H "X-API-Key: ${OTA_API_KEY}" \
            -F "file=@.pio/build/esp32/firmware.bin"
```

## Troubleshooting

### Device Not Receiving Updates

**Check:**
1. Is there an active rollout for the device model?
2. Does the device meet targeting criteria?
3. Is the device's current version different from latest?
4. Check device logs for API errors

**Debug:**
```bash
# Check if device is registered
curl "http://localhost:8080/api/admin/devices?limit=1000" | jq '.devices[] | select(.device_id=="esp32_001")'

# Check rollout configuration
curl "http://localhost:8080/api/admin/firmware/releases?device_model=esp32"

# Check if update would be offered
curl "http://localhost:8080/api/firmware/check?device_id=esp32_001&device_model=esp32&current_version=1.0.0"
```

### Update Failures

**Common causes:**
1. Insufficient flash space on device
2. Network interruption during download
3. Corrupted firmware binary
4. Signature verification failure

**Debug:**
```bash
# Check update status for device
curl "http://localhost:8080/api/admin/update-status?device_id=esp32_001"

# Check OTA service logs
docker logs paku_ota_service

# Check database for errors
docker exec -it paku_postgres psql -U paku -d paku -c \
  "SELECT * FROM device_update_status WHERE device_id='esp32_001' ORDER BY reported_at DESC LIMIT 5;"
```

### High Failure Rate

**Actions:**
1. Pause rollout immediately (set `is_active=false`)
2. Analyze error messages from failed devices
3. Test firmware on affected device models
4. Consider rolling back to previous version

## API Reference

### Device APIs

#### Check for Updates
```
GET /api/firmware/check
Query params: device_id, device_model, current_version
Response: FirmwareCheckResponse
```

#### Download Firmware
```
GET /api/firmware/download/{version}
Response: Binary firmware file with checksum header
```

#### Report Status
```
POST /api/device/{device_id}/update-status
Body: UpdateStatus (status, progress, error)
Response: Success confirmation
```

### Admin APIs

#### Upload Firmware
```
POST /api/admin/firmware/upload
Headers: X-API-Key
Query: version, device_model, min_version, changelog, release_notes, is_signed
Body: Multipart file upload
Response: Upload confirmation with checksum
```

#### List Releases
```
GET /api/admin/firmware/releases
Query: device_model (optional), limit
Response: List of firmware releases
```

#### Create Rollout
```
POST /api/admin/rollout/create
Headers: X-API-Key
Body: RolloutConfig
Response: Creation confirmation
```

#### List Devices
```
GET /api/admin/devices
Query: device_model (optional), limit
Response: List of registered devices
```

#### Get Update Status
```
GET /api/admin/update-status
Query: device_id (optional), firmware_version (optional), limit
Response: List of update status records
```

### Monitoring APIs

#### Health Check
```
GET /health
Response: Service health status
```

#### Metrics
```
GET /metrics
Response: OTA metrics and statistics
```

## Related Documentation

- [Stack README](../README.md) - Main project documentation
- [OTA Service README](../stack/ota-service/README.md) - Service-specific details
- [Database Schema](database_schema.md) - Complete schema documentation
- [Deployment Guide](deployment.md) - Production deployment

## Support

For issues or questions:
1. Check logs: `docker logs paku_ota_service`
2. Review metrics: `curl http://localhost:8080/metrics`
3. Check database state: Connect to PostgreSQL and query OTA tables
4. Open GitHub issue with relevant logs and configuration
