# OTA Updates

Backend-side reference for the OTA firmware update system.
For the edge/device perspective, see [paku-core ota-integration.md](https://github.com/ychefla/paku-core/blob/main/docs/edge/ota-integration.md).

## Architecture

```
GitHub Actions                OTA Service (FastAPI)         ESP32 Device
     │                              │                           │
     ├─ Build firmware              │                           │
     ├─ Upload binary ─────────────►│                           │
     ├─ Create rollout ────────────►│                           │
     │                              │  Publish MQTT cmd/ota ───►│
     │                              │                           ├─ Download FW (HTTP)
     │                              │  ◄── ota/status ──────────┤
     │                              │  ◄── ota/progress ────────┤
     │                              │  ◄── ota/result ──────────┤
     │                              │        │                  │
     │                              │   Collector writes to DB  │
     │                              │        ▼                  │
     │                              │   PostgreSQL / Grafana    │
```

## OTA Service

Runs as part of the Docker Compose stack on port **8080**.

### Admin API

All admin endpoints require `X-API-Key` header.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/firmware/upload` | POST | Upload firmware binary (multipart) |
| `/api/admin/rollout/create` | POST | Create rollout configuration |
| `/api/admin/firmware/releases` | GET | List firmware releases |
| `/api/admin/devices` | GET | List registered devices |
| `/api/admin/update-status` | GET | Get update status records |
| `/health` | GET | Health check |
| `/metrics` | GET | OTA metrics |

### Upload Firmware

```bash
curl -X POST \
  "http://server:8080/api/admin/firmware/upload?version=1.2.0&device_model=esp32&is_signed=false" \
  -H "X-API-Key: $OTA_API_KEY" \
  -F "file=@firmware.bin"
```

### Create Rollout

```bash
# Test rollout — specific devices
curl -X POST "http://server:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OTA_API_KEY" \
  -d '{"name":"v1.2.0-test","firmware_version":"1.2.0","device_model":"esp32","target_type":"specific","target_filter":{"device_ids":["esp32_001"]},"is_active":true}'

# Canary rollout — 10 %
curl -X POST "http://server:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OTA_API_KEY" \
  -d '{"name":"v1.2.0-canary","firmware_version":"1.2.0","device_model":"esp32","target_type":"canary","rollout_percentage":10,"is_active":true}'

# Full production
curl -X POST "http://server:8080/api/admin/rollout/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OTA_API_KEY" \
  -d '{"name":"v1.2.0-prod","firmware_version":"1.2.0","device_model":"esp32","target_type":"all","rollout_percentage":100,"is_active":true}'
```

### Deactivate Rollout

```bash
curl -X POST "http://server:8080/api/admin/rollout/{rollout_id}/deactivate" \
  -H "X-API-Key: $OTA_API_KEY"
```

## GitHub Actions Workflow

The workflow `ota-update-esp.yaml` automates build → upload → rollout.

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `OTA_SERVICE_URL` | OTA service URL (e.g. `http://server:8080`) |
| `OTA_API_KEY` | API key matching server config |
| `PAKU_CORE_REPO` | (optional) `owner/repo` if different org |
| `PAKU_CORE_TOKEN` | (optional) PAT if paku-core is private |

See [SECRETS_REFERENCE.md](../.github/SECRETS_REFERENCE.md) for full secrets list.

### Workflow Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| Rollout Strategy | `test`, `canary-10`, `canary-25`, `canary-50`, `full` | How to deploy |
| Device Model | `esp32`, `esp32-s3`, etc. | Must match `platformio.ini` env |
| Test Devices | comma-separated IDs | Required for `test` strategy |
| Release Notes | free text | Stored in firmware metadata |

### Version Numbering

Auto-generated: `{commit_hash_7}-{YYYYMMDD-HHMMSS}` (e.g. `a1b2c3d-20251208-153045`).
For semantic versioning, tag commits in paku-core: `git tag v1.2.0`.

### Progressive Canary Rollout

1. Run workflow with `canary-10` → monitor 24–48 h
2. Run with `canary-25` → monitor
3. Run with `canary-50` → monitor
4. Run with `full`

## Monitoring

### Grafana SQL Queries

```sql
-- Devices by firmware version
SELECT current_firmware_version, COUNT(*) as count
FROM devices
GROUP BY current_firmware_version ORDER BY count DESC;

-- Update success rate (last 24 h)
SELECT status, COUNT(*) as count
FROM device_update_status
WHERE reported_at > NOW() - INTERVAL '24 hours'
  AND status IN ('success', 'failed')
GROUP BY status;

-- Recent activity
SELECT DATE_TRUNC('hour', reported_at) as hour, status, COUNT(*)
FROM device_update_status
WHERE reported_at > NOW() - INTERVAL '7 days'
GROUP BY hour, status ORDER BY hour DESC;
```

### Alert Conditions

- Update failure rate > 5 %
- Device offline > 24 h after update
- Rollout stuck (no progress for X hours)

## Troubleshooting

| Problem | Check |
|---------|-------|
| Build fails | `platformio.ini` env matches `device_model`; code compiles locally |
| Upload fails | `OTA_SERVICE_URL` reachable; `OTA_API_KEY` matches; port 8080 open |
| Rollout created, devices not updating | Devices online; correct model; OTA-capable firmware |
| High failure rate | Pause rollout; check device logs; test firmware on dev device |

Debug commands:
```bash
# OTA service health
curl http://server:8080/health

# OTA service logs
docker logs paku_ota_service

# Device update history
docker exec paku_postgres psql -U paku -d paku -c \
  "SELECT * FROM device_update_status WHERE device_id='esp32_001' ORDER BY reported_at DESC LIMIT 5;"
```

## Related

- [OTA Service README](../stack/ota-service/README.md)
- [Database Schema](database_schema.md) — OTA tables
- [Secrets Reference](../.github/SECRETS_REFERENCE.md)
- [Deployment Guide](deployment.md)
