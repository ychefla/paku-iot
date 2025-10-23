# paku-iot — Backend Requirements

## Purpose & Scope
The **paku-iot** repo hosts the backend that connects and manages paku devices (firmware = “edge/core”). It must:
- Accept telemetry + status from devices.
- Send commands + configuration to devices.
- Provide OTA firmware distribution.
- Persist data for dashboards/analysis.
- Expose simple APIs for apps and admin tools.
- Be easy to run locally (Docker) and on a small VM (Hetzner).

> Naming: we use **edge** when referring to the device/firmware (repo: `paku-core`). This backend is **paku-iot**.

---

## MVP Functional Requirements
1. **Ingest telemetry**
   - Protocol: MQTT.
   - Topics (proposal):
     - `paku/<deviceId>/telemetry` (JSON payload)
     - `paku/<deviceId>/state` (online/offline, rssi, fwVersion)
     - `paku/<deviceId>/event/<name>` (button, error, etc.)
2. **Downlink / control**
   - `paku/<deviceId>/cmd` (JSON commands; device ACK on `/state` or `/event/ack`).
3. **Device provisioning**
   - Create device ID + credentials.
   - Optional one-time claim code flow.
4. **OTA**
   - Host firmware files and a manifest:
     - `GET /ota/manifest.json` → list of `{model, version, url, sha256}`.
     - Firmware files served via HTTP(S).
5. **Storage**
   - Time-series telemetry.
   - Device registry (id, model, secrets, metadata).
6. **APIs**
   - `GET /health`
   - `GET /devices`, `GET /devices/<id>`
   - `POST /devices` (provision)
   - `GET /ota/manifest.json`
7. **Admin UI (optional for MVP)**
   - Minimal dashboard (device list, last seen, fw version).

---

## Non-Functional Requirements
- **Small footprint:** runs on a 1–2 vCPU VM, 1–2 GB RAM.
- **Portable dev env:** `docker compose up` works on macOS/Linux.
- **Observability:** logs for each service; simple metrics endpoint.
- **Backups:** DB snapshot script (cron/`scripts/backup.sh`).
- **Security:** no secrets in git; per-device MQTT creds; TLS ready.

---

## Proposed Minimal Stack
- **MQTT broker:** Eclipse Mosquitto.
- **Collector/Bridge:** small service that validates messages and writes to DB (language TBD; Node/Go/Python—keep simple).
- **DB:** 
  - Option A (simple): PostgreSQL (JSONB for telemetry).
  - Option B (timeseries): Postgres + Timescale or InfluxDB.
- **API:** lightweight HTTP service (can be same as Collector at first).
- **OTA:** static file server (nginx) + `manifest.json`.
- **Optional dashboards:** Grafana (if we go Postgres/Influx).

---

## Data Model (initial)
- **Device**
  - `id`, `model`, `createdAt`, `fwVersion`, `lastSeenAt`, `notes`
- **Credential**
  - per-device mqtt username/password or token
- **Measurement**
  - `deviceId`, `ts`, `payload` (JSON)
- **Event**
  - `deviceId`, `ts`, `type`, `payload` (JSON)

---

## MQTT Details (baseline)
- QoS: 1 for telemetry/events; 0 acceptable for state.
- Retain: `state` retained; telemetry/events not retained.
- Auth: unique username/password per device. ACL: device can publish only to its own topics; backend can publish to `/cmd`.

---

## OTA Flow (baseline)
1. CI (or manual) uploads `firmware.bin` and updates `manifest.json`.
2. Device periodically checks `GET /ota/manifest.json?model=<m>&current=<v>`.
3. If newer version found, device downloads from `url`.
4. (Future) Optional signature verification.

---

## Secrets & Config
- Commit **`example`** files only:
  - `.env.example` for compose environment.
  - `config.example.yml` for service defaults.
- Real secrets go to `.env` / `config.yml` (git-ignored).
- Use `trufflehog` locally before pushes.

---

## Directory Layout (target)
paku-iot/
compose/          # docker compose files (dev, prod)
services/
api/
collector/
ota/            # static files + manifest.json
config/
config.example.yml
docs/
scripts/
backup.sh

---

## Local Development (goal)
- Requirements: Docker, Docker Compose.
- Commands:
  - `docker compose -f compose/dev.yaml up -d`
  - Logs: `docker compose -f compose/dev.yaml logs -f`
  - Tear down: `docker compose -f compose/dev.yaml down -v`

---

## Deployment (Hetzner VM)
- Single-host docker deployment using `compose/prod.yaml`.
- Bind mounts for persistent volumes.
- Reverse proxy/TLS can be Caddy/Traefik (future).

---

## Acceptance Criteria (MVP)
- Device connects, authenticates, publishes telemetry.
- Telemetry persisted and queryable via API.
- `/health` returns 200 for all services.
- OTA manifest served; device downloads file.
- No secrets in repo (`trufflehog` clean).

---

## Next Steps
1. Add `compose/dev.yaml` skeleton.
2. Add `.env.example` with required variables.
3. Implement a minimal collector + API (single process is fine).
