# paku-iot

Backend stack for the Paku project — environmental telemetry ingestion, storage, and visualization.

## Overview

This repository contains the unified Docker Compose stack for the Paku IoT backend:
- **MQTT Broker** (Mosquitto) — message ingestion
- **RuuviTag Emulator** — test data generation
- **Collector** — MQTT to Postgres data pipeline
- **PostgreSQL** — persistent data storage
- **Grafana** — data visualization

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ychefla/paku-iot.git
   cd paku-iot
   ```

2. **Configure environment variables:**
   
   Copy the example environment file and customize it:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and update the values as needed. The `.env.example` file contains:
   - Database credentials (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
   - MQTT broker settings (MQTT_HOST, MQTT_PORT)
   - Grafana admin password (GF_SECURITY_ADMIN_PASSWORD)
   
   **Important:** Never commit the `.env` file — it contains secrets and is git-ignored.

3. **Start the stack:**
   ```bash
   docker compose -f compose/stack.yaml up --build
   ```

4. **Access the services:**
   - Grafana: http://localhost:3000 (default credentials: admin / [value from .env])
   - PostgreSQL: localhost:5432
   - MQTT Broker: localhost:1883

5. **Stop the stack:**
   ```bash
   docker compose -f compose/stack.yaml down
   ```

## Documentation

- [Requirements](docs/requirements.md) — functional and technical requirements
- [MQTT Schema](docs/mqtt_schema.md) — message format and topics

## Security & Secrets

- **Never commit secrets** to version control
- Use `.env` for local secrets (already git-ignored)
- Use `.env.example` as a template showing required variables
- Change default passwords before deploying to production

## Development

For development and contribution guidelines, see the detailed documentation in the `docs/` directory.

## Project Structure

```
paku-iot/
├── compose/
│   └── stack.yaml          # Unified Docker Compose configuration
├── stack/
│   ├── mosquitto/          # MQTT broker
│   ├── ruuvi-emulator/     # Test data emulator
│   ├── collector/          # Data pipeline service
│   ├── postgres/           # Database
│   └── grafana/            # Visualization
├── docs/
│   ├── requirements.md
│   └── mqtt_schema.md
├── .env.example            # Environment variables template
└── README.md               # This file
```

## License

[Add license information here]
