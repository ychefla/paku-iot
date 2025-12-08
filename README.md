# Paku IoT Backend

Backend stack for the Paku project - environmental telemetry ingestion, storage, and visualization.

## Overview

The **paku-iot** repository hosts the backend infrastructure for collecting, storing, and visualizing sensor data from IoT devices. The current implementation focuses on a minimal viable product (MVP) that handles telemetry from a single van environment.

### Key Features

- **MQTT Telemetry Ingestion**: Receives environmental sensor data via MQTT
- **EcoFlow Integration**: Automatic data collection from EcoFlow power stations (Delta Pro, etc.)
- **OTA Updates**: Over-the-air firmware update orchestration for ESP devices
- **Persistent Storage**: Stores measurements in PostgreSQL
- **Data Visualization**: Real-time dashboards in Grafana
- **Docker-based Stack**: Complete environment runs via Docker Compose

## Quick Start

### Prerequisites

- Docker (version 20.10 or later)
- Docker Compose (version 2.0 or later)
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
   cp compose/.env.example compose/.env
   ```
   
   Edit `compose/.env` and update the values as needed. The `compose/.env.example` file contains:
   - Database credentials (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
   - MQTT broker settings (MQTT_HOST, MQTT_PORT)
   - Grafana admin password (GF_SECURITY_ADMIN_PASSWORD)
   
   **Important:** Never commit the `compose/.env` file — it contains secrets and is git-ignored.

3. **Start the Stack:**
   ```bash
   docker compose -f compose/stack.yaml up --build
   ```

4. **Access the Services:**
   - **Grafana**: http://localhost:3000 (default credentials: admin / [value from compose/.env])
   - **PostgreSQL**: localhost:5432
   - **MQTT Broker**: localhost:1883
   - **OTA Service**: http://localhost:8080 (API documentation: http://localhost:8080/docs)

5. **Stop the Stack:**
   ```bash
   docker compose -f compose/stack.yaml down
   ```

## EcoFlow Integration (Optional)

To enable automatic data collection from EcoFlow power stations (Delta Pro, Delta Max, etc.):

1. **Get API Credentials:**
   - Register at [EcoFlow Developer Portal](https://developer.ecoflow.com/)
   - Create an application to get your `access_key` and `secret_key`

2. **Configure:**
   ```bash
   # Add to compose/.env
   ECOFLOW_ACCESS_KEY=your_access_key_here
   ECOFLOW_SECRET_KEY=your_secret_key_here
   ECOFLOW_DEVICE_SN=your_device_serial_number  # Optional
   ```

3. **Start with EcoFlow:**
   ```bash
   docker compose --profile ecoflow -f compose/stack.yaml up
   ```

4. **View Data:**
   - Check logs: `docker logs paku_ecoflow_collector`
   - Query database: `SELECT * FROM ecoflow_measurements ORDER BY ts DESC LIMIT 10;`
   - Create Grafana dashboards for battery level, power flow, solar input, etc.

For complete setup instructions, troubleshooting, and Grafana examples, see [EcoFlow Integration Guide](docs/ecoflow_integration.md).

## OTA Updates for ESP Devices

The platform includes a complete OTA (Over-The-Air) update system for ESP32/ESP8266 devices:

### Features

- **Firmware Hosting**: Secure storage and serving of signed firmware binaries
- **Version Management**: Track releases, compatibility requirements, and changelogs
- **Rollout Orchestration**: Control which devices receive updates (all, canary, specific devices)
- **Status Monitoring**: Real-time tracking of update progress and success rates
- **Rollback Support**: Ability to halt or reverse problematic rollouts

### Quick Start

1. **Upload firmware** (requires API key):
   ```bash
   curl -X POST "http://localhost:8080/api/admin/firmware/upload?version=1.0.0&device_model=esp32&is_signed=true" \
     -H "X-API-Key: your-api-key" \
     -F "file=@firmware.bin"
   ```

2. **Create a rollout**:
   ```bash
   curl -X POST "http://localhost:8080/api/admin/rollout/create" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-api-key" \
     -d '{
       "name": "v1.0.0-production",
       "firmware_version": "1.0.0",
       "device_model": "esp32",
       "target_type": "all",
       "rollout_percentage": 100,
       "is_active": true
     }'
   ```

3. **Monitor updates**:
   - API: `http://localhost:8080/metrics`
   - Grafana: OTA Monitoring dashboard
   - Logs: `docker logs paku_ota_service`

### Automated OTA Updates via GitHub Actions

The repository includes a GitHub Actions workflow for automated ESP firmware updates:

**Manual Workflow Trigger**: Navigate to Actions → "OTA Update ESP Devices" → Run workflow

**Features**:
- Builds firmware from `paku-core` main branch automatically
- Supports multiple rollout strategies (test, canary, full)
- Generates deployment summaries with firmware checksums
- No manual steps required - just execute the workflow

**Setup Requirements**:
- Configure `OTA_SERVICE_URL` and `OTA_API_KEY` secrets in GitHub
- Optionally set `PAKU_CORE_REPO` for private repositories

For complete workflow documentation and usage guide, see [OTA Workflow Guide](docs/ota_workflow_guide.md).

For API documentation, device integration examples, and best practices, see [OTA Updates Guide](docs/ota_updates.md).

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

The stack consists of core Docker containers for data collection and management:

1. **Ruuvi Emulator**: Publishes simulated sensor data to MQTT
2. **Mosquitto**: MQTT broker for message routing
3. **Collector**: Consumes MQTT messages and writes to database
4. **PostgreSQL**: Time-series data storage with OTA tables
5. **Grafana**: Data visualization and dashboards
6. **EcoFlow Collector** (optional): Collects data from EcoFlow power stations
7. **OTA Service**: REST API for firmware update orchestration

```
Ruuvi Emulator → Mosquitto (MQTT) → Collector → PostgreSQL → Grafana
                                                      ↑
EcoFlow Device → EcoFlow Cloud API → EcoFlow Collector
                                                      ↑
ESP Devices → OTA Service (REST API) → PostgreSQL → OTA Monitoring Dashboard
```

## Data Model

The current schema includes a `measurements` table with:

- `id` - Primary key
- `sensor_id` - Logical sensor identifier (e.g., "van_inside")
- `ts` - Timestamp with timezone
- `temperature_c` - Temperature in Celsius
- `humidity_percent` - Relative humidity percentage
- `pressure_hpa` - Atmospheric pressure in hPa
- `battery_mv` - Battery voltage in millivolts

## Deployment

The stack can be deployed to a Hetzner Cloud VM for production use.

### Quick Production Deployment

1. Set up a Hetzner Cloud VM (CX11 or CX21 recommended)
2. Configure GitHub Secrets for automated deployment:
   - `HETZNER_HOST` - Server IP address
   - `HETZNER_SSH_KEY` - SSH private key for deployment
   - `POSTGRES_PASSWORD` - Strong database password
   - `GF_SECURITY_ADMIN_PASSWORD` - Strong Grafana admin password
3. Push to `main` branch to trigger automatic deployment

For detailed instructions, see [docs/deployment.md](docs/deployment.md).

### Manual Production Deployment

```bash
# On the server
git clone https://github.com/ychefla/paku-iot.git
cd paku-iot
cp compose/.env.example compose/.env
# Edit compose/.env with production passwords
docker compose -f compose/stack.prod.yaml up -d
```

## Documentation

- [Requirements](docs/requirements.md) - Detailed functional and non-functional requirements
- [Deployment Guide](docs/deployment.md) - Hetzner deployment instructions
- [E2E Test Guide](docs/e2e_test.md) - Complete testing documentation
- [MQTT Schema](docs/mqtt_schema.md) - Message format and topic structure
- [Database Schema](docs/database_schema.md) - Database structure and design
- [EcoFlow Integration](docs/ecoflow_integration.md) - Complete guide for EcoFlow power station integration
- [OTA Updates](docs/ota_updates.md) - Over-the-air firmware update system for ESP devices
- [OTA Workflow Guide](docs/ota_workflow_guide.md) - GitHub Actions workflow for automated ESP firmware updates

## Development

### Project Structure

```
paku-iot/
├── compose/
│   ├── stack.yaml          # Docker Compose configuration
│   ├── .env.example        # Environment variables template
│   └── .env                # Local environment variables (git-ignored)
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

Environment variables are loaded from `compose/.env` (git-ignored). See `compose/.env.example` for template.

Default database credentials (development only):
- Database: `paku`
- User: `paku`
- Password: `paku`

**Security Note**: The default credentials are for local development only. In production environments, use strong passwords and proper secrets management.

### Security & Secrets

- **Never commit secrets** to version control
- Use `compose/.env` for local secrets (already git-ignored)
- Use `compose/.env.example` as a template showing required variables
- Change default passwords before deploying to production

### Logs

View logs for specific services:

```bash
docker logs paku_ruuvi_emulator
docker logs paku_collector
docker logs paku_postgres
docker logs paku_mosquitto
docker logs paku_grafana
docker logs paku_ecoflow_collector
docker logs paku_ota_service
```

## Future Enhancements

Planned for future sprints:
- Multi-device support with enhanced device registry
- Downlink commands and configuration
- CDN integration for firmware distribution
- Admin UI for OTA management
- Advanced rollout strategies (A/B testing, gradual percentage increase)

See [docs/requirements.md](docs/requirements.md) for detailed roadmap.

## License

[License information to be added]

## Contributing

[Contributing guidelines to be added]
