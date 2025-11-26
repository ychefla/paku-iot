# paku-iot — Backend Requirements (Current Plan)

## Purpose & Scope
The **paku-iot** repo hosts the backend stack for the Paku project. In the **current phase**, the scope is intentionally small and focused:

- Ingest environmental telemetry (temperature, humidity, etc.) from a single van environment.
- Persist measurements in a simple Postgres schema.
- Visualize data in Grafana dashboards.
- Run everything locally using a single Docker Compose stack.

Future phases (not part of the current sprint) may add:
- Multiple devices and a proper device registry.
- Commands / configuration downlink to devices.
- OTA firmware distribution.
- Remote deployment on a small VM.

> Naming: we use **edge** for the device/firmware side (repo: `paku-core`). This backend is **paku-iot**.

---

## MVP Functional Requirements (current phase)

1. **Ingest telemetry via MQTT**
   - MQTT broker: Mosquitto (running in the unified stack).
   - Primary topic (current focus):
     - `paku/ruuvi/van_inside`
   - Payload: RuuviTag-style JSON as documented in `docs/mqtt_schema.md`.

2. **Store measurements in Postgres**
   - Simple `measurements` table, including at least:
     - `id` (primary key)
     - `sensor_id`
     - timestamp
     - temperature, humidity, pressure, battery
   - Schema created automatically when Postgres container starts (init script or similar).

3. **Collector service (MQTT → Postgres)**
   - Subscribes to the Ruuvi topic.
   - Validates incoming JSON against the documented schema.
   - Inserts valid measurements into Postgres.
   - Logs and skips malformed messages without crashing.

4. **Basic dashboards in Grafana**
   - Visualize at least:
     - Temperature over time.
     - Humidity over time.
     - Table view of the last N measurements.
   - Dashboards should persist across container restarts via named volumes.

5. **Minimal observability for this stack**
   - Container logs for all services (broker, collector, Postgres, Grafana).
   - Simple end-to-end test: one MQTT message results in one DB row.

---

## Future Functional Requirements (not in current sprint)

These are explicitly **future** items. They influence some design choices but are not to be implemented now:

1. **Generalized device topics and registry**
   - Topics like `paku/<deviceId>/telemetry`, `paku/<deviceId>/state`, `paku/<deviceId>/event/<name>`.
   - Device registry (id, model, secrets, metadata).

2. **Downlink / control**
   - `paku/<deviceId>/cmd` (JSON commands).
   - Device ACK via `/state` or `/event/ack`.

3. **OTA firmware distribution**
   - Host firmware files + manifest (e.g. `GET /ota/manifest.json`).
   - Firmware download over HTTP(S) or similar.

4. **HTTP APIs and admin tools**
   - Basic APIs for devices and measurements.
   - Lightweight admin UI.

These should remain parked until the single-van telemetry pipeline is stable and useful.

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
  - `.env.example` for compose environment variables.
- Real secrets go to `.env` (git-ignored).
- The `.env.example` file should document:
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

## Deployment (future)

Future goal (not current sprint):
- Run the same stack (or a slightly adapted version) on a small VM (e.g. Hetzner).
- Use a similar compose file, with additional hardening (MQTT auth/TLS, backups, ingress).

Details for remote deployment will be specified once the local stack is stable and useful.

---

## Acceptance Criteria (for current MVP)

- Ruuvitag-style emulator publishes JSON to the agreed MQTT topic.
- Collector consumes messages, validates payloads and writes rows into Postgres.
- Grafana dashboard shows live and historical measurements from Postgres.
- The unified stack can be started and stopped with a single compose command.
- No secrets are committed to git; `.env.example` exists and is usable as a template.