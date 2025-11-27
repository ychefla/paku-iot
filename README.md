<<<<<<< HEAD
# paku-iot

Backend stack for the Paku project — environmental telemetry ingestion, storage, and visualization.

## Overview

This repository contains the unified Docker Compose stack for the Paku IoT backend:
- **MQTT Broker** (Mosquitto) — message ingestion
- **RuuviTag Emulator** — test data generation
- **Collector** — MQTT to Postgres data pipeline
- **PostgreSQL** — persistent data storage
- **Grafana** — data visualization
=======
# Paku IoT Backend

Backend stack for the Paku project - environmental telemetry ingestion, storage, and visualization.

## Overview

The **paku-iot** repository hosts the backend infrastructure for collecting, storing, and visualizing sensor data from IoT devices. The current implementation focuses on a minimal viable product (MVP) that handles telemetry from a single van environment.

### Key Features

- **MQTT Telemetry Ingestion**: Receives environmental sensor data via MQTT
- **Persistent Storage**: Stores measurements in PostgreSQL
- **Data Visualization**: Real-time dashboards in Grafana
- **Docker-based Stack**: Complete environment runs via Docker Compose
>>>>>>> copilot/create-e2e-test-scenario

## Quick Start

### Prerequisites

<<<<<<< HEAD
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
=======
- Docker (version 20.10 or later)
- Docker Compose (version 2.0 or later)

### Start the Stack

```bash
docker compose -f compose/stack.yaml up --build -d
```

### Access Services

- **Grafana**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **MQTT Broker**: localhost:1883

### Stop the Stack

```bash
docker compose -f compose/stack.yaml down
```

## Testing

### End-to-End Test

Run the automated E2E test to verify the complete data pipeline:

```bash
./tests/e2e_test.sh
```

This test:
- Starts the full stack
- Verifies MQTT message publication
- Confirms data persistence in PostgreSQL
- Validates the complete pipeline functionality

For detailed testing documentation, see [docs/e2e_test.md](docs/e2e_test.md).

## Architecture

The stack consists of five Docker containers:

1. **Ruuvi Emulator**: Publishes simulated sensor data to MQTT
2. **Mosquitto**: MQTT broker for message routing
3. **Collector**: Consumes MQTT messages and writes to database
4. **PostgreSQL**: Time-series data storage
5. **Grafana**: Data visualization and dashboards

```
Ruuvi Emulator → Mosquitto (MQTT) → Collector → PostgreSQL → Grafana
```

## Documentation

- [Requirements](docs/requirements.md) - Detailed functional and non-functional requirements
- [E2E Test Guide](docs/e2e_test.md) - Complete testing documentation
- [MQTT Schema](docs/mqtt_schema.md) - Message format and topic structure

## Data Model

The current schema includes a `measurements` table with:

- `id` - Primary key
- `sensor_id` - Logical sensor identifier (e.g., "van_inside")
- `ts` - Timestamp with timezone
- `temperature_c` - Temperature in Celsius
- `humidity_percent` - Relative humidity percentage
- `pressure_hpa` - Atmospheric pressure in hPa
- `battery_mv` - Battery voltage in millivolts

## Development

### Project Structure
>>>>>>> copilot/create-e2e-test-scenario

```
paku-iot/
├── compose/
<<<<<<< HEAD
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
=======
│   └── stack.yaml          # Docker Compose configuration
├── stack/
│   ├── mosquitto/          # MQTT broker
│   ├── ruuvi-emulator/     # Sensor emulator
│   ├── collector/          # Data collector service
│   ├── postgres/           # Database with init scripts
│   └── grafana/            # Visualization
├── docs/                   # Documentation
└── tests/                  # Test scripts
```

### Configuration

Environment variables are loaded from `.env` (git-ignored). See `.env.example` for template.

Default database credentials (development only):
- Database: `paku`
- User: `paku`
- Password: `paku`

**Security Note**: The default credentials are for local development only. In production environments, use strong passwords and consider using `.pgpass` files or connection URIs instead of command-line password arguments.

### Logs

View logs for specific services:

```bash
docker logs paku_ruuvi_emulator
docker logs paku_collector
docker logs paku_postgres
docker logs paku_mosquitto
docker logs paku_grafana
```

## Future Enhancements

Planned for future sprints:
- Multi-device support with device registry
- Downlink commands and configuration
- OTA firmware distribution
- HTTP APIs and admin UI
- Remote deployment capabilities

See [docs/requirements.md](docs/requirements.md) for detailed roadmap.

## License

[License information to be added]

## Contributing

[Contributing guidelines to be added]
>>>>>>> copilot/create-e2e-test-scenario
