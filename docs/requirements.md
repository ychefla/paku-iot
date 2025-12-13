# paku-iot — Backend Requirements (Current Plan)

## Purpose & Scope
The **paku-iot** repo hosts the backend stack for the Paku project. The implementation includes:

- Ingest environmental telemetry (temperature, humidity, etc.) from IoT devices
- Persist measurements in PostgreSQL with flexible JSONB schema
- Visualize data in Grafana dashboards
- EcoFlow power station integration via REST API
- Over-the-air (OTA) firmware updates for ESP devices
- Docker Compose orchestration for all services
- Automated deployment via GitHub Actions

> Naming: we use **edge** for the device/firmware side (repo: `paku-core`). This backend is **paku-iot**.

---

## Implemented Functional Requirements

1. **Ingest telemetry via MQTT**
   - MQTT broker: Mosquitto (running in the unified stack)
   - Hierarchical topic structure: `{site_id}/{system}/{device_id}/data`
   - Legacy support: `paku/ruuvi/van_inside`
   - Payload: JSON with flexible JSONB metrics field as documented in `docs/mqtt_schema.md`

2. **Store measurements in PostgreSQL**
   - `measurements` table with JSONB metrics column
   - `ecoflow_measurements` table for EcoFlow power stations
   - OTA-related tables: firmware_releases, devices, device_update_status, rollout_configurations, ota_events
   - Schema created automatically when Postgres container starts

3. **Collector service (MQTT → Postgres)**
   - Subscribes to hierarchical topic patterns
   - Validates incoming JSON against the documented schema
   - Inserts valid measurements into Postgres
   - Logs and skips malformed messages without crashing

4. **EcoFlow Integration**
   - REST API polling of EcoFlow Cloud API
   - Automatic data collection from Delta Pro and other supported models
   - Real-time power station metrics (battery, solar input, power output, etc.)
   - Separate collector service with configurable polling interval

5. **OTA Firmware Updates**
   - REST API for ESP device firmware management
   - Firmware upload and versioning
   - Multiple rollout strategies (all, canary, specific devices, groups)
   - Update progress tracking and status monitoring
   - GitHub Actions workflow for automated firmware deployment
   - Consistent hashing for canary rollouts

6. **Grafana Dashboards**
   - Auto-provisioned dashboards for Ruuvi sensors
   - Comprehensive EcoFlow monitoring dashboards
   - Real-time visualization of all metrics
   - Dashboards persist across container restarts via named volumes

7. **Production Deployment**
   - Docker Compose orchestration for all services
   - Automated deployment via GitHub Actions
   - Environment-based configuration management
   - Support for Hetzner Cloud and other hosting providers

---

## Future Functional Requirements

These are items for potential future enhancement:

1. **Enhanced device registry**
   - Advanced device grouping and metadata
   - Fine-grained access control per device

2. **Downlink / control**
   - `paku/<deviceId>/cmd` (JSON commands)
   - Device ACK via `/state` or `/event/ack`

3. **HTTP APIs for telemetry**
   - REST API for querying measurements
   - Lightweight admin UI for system management

4. **Advanced OTA features**
   - CDN integration for firmware distribution
   - A/B testing capabilities
   - Automatic rollback on failure detection

---

## Non-Functional Requirements

- **Small footprint:**
  - Should run comfortably on a small dev machine and a small VM (1–2 vCPU, 1–2 GB RAM) if needed.

- **Simple local setup:**
  - `docker compose -f compose/stack.yaml up --build` should start the full stack.
  - No separate dev/prod compose layers in the current phase.

- **Observability:**
  - Logs available for all containers.
  - Ability to manually inspect data in Postgres.

- **Security baseline:**
  - No real secrets in git.
  - Environment variables loaded from `.env` (local only).
  - MQTT broker is open and simple for local dev; hardening (auth/TLS) is documented separately as future work in `AI_COLLAB.md`.

---

## Minimal Stack (current implementation)

- **MQTT broker:** Mosquitto (plain, local dev configuration).
- **Emulator:** Ruuvi emulator that publishes RuuviTag-style JSON.
- **Collector:** Python-based service consuming MQTT and inserting into Postgres.
- **DB:** PostgreSQL with a simple `measurements` table.
- **Dashboard:** Grafana, reading from Postgres.

All of these run via a **single Docker Compose stack** in `compose/stack.yaml`.

---

## Data Model (initial)

- **Measurement**
  - `id` — integer primary key.
  - `sensor_id` — logical sensor identifier (e.g. `van_inside`).
  - `ts` — timestamp with timezone (measurement time).
  - `temperature_c` — numeric.
  - `humidity_percent` — numeric.
  - `pressure_hpa` — numeric.
  - `battery_mv` — integer.
  - Optionally: raw payload or extra fields as needed.

Future models (device, events, etc.) can be added later once needed.

---

## MQTT Details (current)

- Broker: Mosquitto instance running in the unified stack.
- Main topic:
  - `paku/ruuvi/van_inside` (single Ruuvi sensor inside the van).
- Payload:
  - RuuviTag-style JSON as described in `docs/mqtt_schema.md`.
- QoS/retain:
  - QoS 0 or 1 acceptable; no strict requirement in current phase.
  - No retained telemetry needed at this stage.

Future multi-device topic structure (e.g. `paku/<deviceId>/...`) is out of scope for now.

---

## Secrets & Config

- Commit **example** files only:
  - `compose/.env.example` for compose environment variables.
- Real secrets go to `.env` (git-ignored).
- The `compose/.env.example` file should document:
  - DB credentials (user, password, database).
  - MQTT host/port if needed.
- Follow the general secrets guidance in `AI_COLLAB.md` (no real secrets in chat or git).

---

## Directory Layout (current target)

```text
paku-iot/
  compose/
    stack.yaml          # Single unified docker-compose stack
  stack/
    mosquitto/          # MQTT broker container
    ruuvi-emulator/     # Ruuvi emulator container
    collector/          # Collector (MQTT → Postgres)
    postgres/           # Postgres container + init scripts
    grafana/            # Grafana container and provisioning
  docs/
    requirements.md     # This file
    mqtt_schema.md      # Ruuvi payload + topic schema
  _archive/
    legacy_compose/     # Old dev/prod compose structure (kept for reference)
    services/           # Old service implementations (kept for reference)
```

This layout reflects the simplified, unified stack. Older `services/` and multi-file compose setups are archived and should not be extended.

---

## Local Development

Requirements:
- Docker and Docker Compose installed on the host.
- Devcontainer is optional but recommended for editing and tooling.

Typical workflow:

```bash
cd /Users/jossu/GIT/paku/paku-iot

# Start stack (host terminal, not inside devcontainer)
docker compose -f compose/stack.yaml up --build

# Stop stack
docker compose -f compose/stack.yaml down
```

Logs can be viewed using `docker logs` for each service or via a terminal that shows compose output.

---

## Deployment

The stack supports deployment to Hetzner Cloud VMs:

- Production compose file: `compose/stack.prod.yaml`
- Automated deployment via GitHub Actions (see `.github/workflows/deploy.yaml`)
- Detailed instructions in `docs/deployment.md`

The production stack includes:
- Resource limits for all containers
- Always restart policy
- JSON-file logging with rotation
- Health checks for all services
- PostgreSQL only exposed on localhost

Future hardening (not in current sprint):
- MQTT authentication and TLS
- Automated backups
- HTTPS via reverse proxy

---

## Acceptance Criteria (for current MVP)

- Ruuvitag-style emulator publishes JSON to the agreed MQTT topic.
- Collector consumes messages, validates payloads and writes rows into Postgres.
- Grafana dashboard shows live and historical measurements from Postgres.
- The unified stack can be started and stopped with a single compose command.
- No secrets are committed to git; `compose/.env.example` exists and is usable as a template.