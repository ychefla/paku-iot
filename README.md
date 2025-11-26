# Paku IoT Backend

Backend stack for the Paku project - environmental telemetry ingestion, storage, and visualization.

## Overview

The **paku-iot** repository hosts the backend infrastructure for collecting, storing, and visualizing sensor data from IoT devices. The current implementation focuses on a minimal viable product (MVP) that handles telemetry from a single van environment.

### Key Features

- **MQTT Telemetry Ingestion**: Receives environmental sensor data via MQTT
- **Persistent Storage**: Stores measurements in PostgreSQL
- **Data Visualization**: Real-time dashboards in Grafana
- **Docker-based Stack**: Complete environment runs via Docker Compose

## Quick Start

### Prerequisites

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

```
paku-iot/
├── compose/
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
