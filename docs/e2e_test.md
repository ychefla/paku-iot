# Paku IoT End-to-End Test

## Overview

This document describes the end-to-end (E2E) test for the Paku IoT stack. The test verifies the complete data pipeline from MQTT message publication to database persistence.

**Purpose**: Validate that a message published to the MQTT broker by the Ruuvi emulator is correctly processed by the collector service and persisted as a row in the Postgres measurements table.

## Test Scope

The E2E test covers:

1. ✓ Starting the full Docker Compose stack
2. ✓ Waiting for all services to be ready
3. ✓ Verifying the database schema is initialized
4. ✓ Confirming at least one MQTT message is published
5. ✓ Validating at least one row exists in the measurements table
6. ✓ Cleaning up the test environment

## Prerequisites

### Required Tools

- **Docker**: Container runtime (version 20.10 or later)
- **Docker Compose**: Container orchestration (version 2.0 or later)
- **psql**: PostgreSQL client for database verification

### Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose postgresql-client
```

**macOS:**
```bash
brew install docker docker-compose postgresql
```

**Verify installations:**
```bash
docker --version
docker compose version
psql --version
```

## Automated Test

### Running the Test Script

The automated test script is located at `tests/e2e_test.sh`. It performs all verification steps automatically.

**Run from the repository root:**
```bash
./tests/e2e_test.sh
```

### Expected Output

A successful test run produces output similar to:

```
==========================================
Paku IoT End-to-End Test
==========================================

Step 1: Checking prerequisites...
✓ Docker is installed
✓ Docker Compose is installed
✓ psql is installed

Step 2: Starting the Docker Compose stack...
✓ Stack started successfully

Step 3: Waiting for services to be ready...
ℹ Waiting for Postgres to accept connections...
✓ Postgres is ready

Step 4: Checking database schema...
✓ measurements table exists

Step 5: Waiting for MQTT messages to be published and processed...
ℹ Checking if ruuvi-emulator is publishing messages...
ℹ Checking if collector is processing messages...
ℹ Waiting for at least one row in measurements table...
✓ Found 1 row(s) in measurements table

Step 6: Verifying data content...
✓ Successfully retrieved sample data:
 id | sensor_id  |           ts           | temperature_c | humidity_percent
----+------------+------------------------+---------------+------------------
  1 | van_inside | 2025-11-26 12:30:00+00 |          21.5 |             45.2

==========================================
End-to-End Test Summary
==========================================
✓ All tests passed!

Test results:
  - Stack started: ✓
  - Postgres ready: ✓
  - measurements table exists: ✓
  - At least one row inserted: ✓ (1 row(s) found)
  - Data retrieval working: ✓

ℹ The full MQTT → Postgres pipeline is working correctly.
==========================================
```

### Test Configuration

The test script uses the following default configuration:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `COMPOSE_FILE` | `compose/stack.yaml` | Docker Compose file location |
| `MQTT_TOPIC` | `paku/ruuvi/van_inside` | MQTT topic for Ruuvi data |
| `DB_HOST` | `localhost` | Postgres host |
| `DB_PORT` | `5432` | Postgres port |
| `DB_NAME` | `paku` | Database name |
| `DB_USER` | `paku` | Database user |
| `DB_PASSWORD` | `paku` | Database password |
| `TIMEOUT_SECONDS` | `60` | Maximum wait time for operations |
| `CHECK_INTERVAL` | `5` | Interval between status checks |

These can be modified in the script if your setup differs.

## Manual Test Procedure

If you prefer to run the test manually or need to debug issues, follow these steps:

### Step 1: Start the Stack

```bash
cd /path/to/paku-iot
docker compose -f compose/stack.yaml up --build -d
```

**Expected result**: All containers start successfully:
- `paku_mosquitto` (MQTT broker)
- `paku_ruuvi_emulator` (Sensor emulator)
- `paku_collector` (MQTT → Postgres bridge)
- `paku_postgres` (Database)
- `paku_grafana` (Visualization)

### Step 2: Verify Postgres is Running

```bash
docker ps | grep paku_postgres
```

**Expected result**: Container is running and healthy.

### Step 3: Check Database Schema

```bash
PGPASSWORD=paku psql -h localhost -p 5432 -U paku -d paku -c "\dt"
```

**Expected result**: The `measurements` table is listed.

### Step 4: Verify MQTT Messages

Check the emulator logs to confirm it's publishing messages:

```bash
docker logs paku_ruuvi_emulator
```

**Expected result**: Log entries showing MQTT publish operations.

### Step 5: Check Collector Processing

Verify the collector is consuming messages:

```bash
docker logs paku_collector
```

**Expected result**: Log entries showing message processing and database inserts.

### Step 6: Query the Database

Check for rows in the measurements table:

```bash
PGPASSWORD=paku psql -h localhost -p 5432 -U paku -d paku -c "SELECT COUNT(*) FROM measurements;"
```

**Expected result**: At least 1 row.

Retrieve sample data:

```bash
PGPASSWORD=paku psql -h localhost -p 5432 -U paku -d paku -c "SELECT * FROM measurements LIMIT 1;"
```

**Expected result**: A row with sensor data including `sensor_id`, `temperature_c`, `humidity_percent`, etc.

### Step 7: Stop the Stack

```bash
docker compose -f compose/stack.yaml down -v
```

**Note**: The `-v` flag removes volumes, ensuring a clean state for the next test.

## Troubleshooting

### Issue: "Postgres did not become ready in time"

**Possible causes**:
- Postgres container failed to start
- Port 5432 is already in use
- Insufficient system resources

**Solutions**:
1. Check Postgres logs: `docker logs paku_postgres`
2. Verify port availability: `netstat -an | grep 5432`
3. Ensure Docker has sufficient memory (at least 2GB recommended)

### Issue: "measurements table does not exist"

**Possible causes**:
- Database initialization script not executed
- Schema migration failed

**Solutions**:
1. Check Postgres logs for initialization errors
2. Verify the init script exists in `stack/postgres/`
3. Rebuild the Postgres container: `docker compose -f compose/stack.yaml build postgres`

### Issue: "No rows found in measurements table"

**Possible causes**:
- Ruuvi emulator not publishing messages
- Collector service not running or failing
- MQTT broker connection issues

**Solutions**:
1. Check emulator logs: `docker logs paku_ruuvi_emulator`
2. Check collector logs: `docker logs paku_collector`
3. Check mosquitto logs: `docker logs paku_mosquitto`
4. Verify network connectivity between containers

### Issue: "psql: command not found"

**Solution**: Install the PostgreSQL client:
- Ubuntu/Debian: `sudo apt-get install postgresql-client`
- macOS: `brew install postgresql`

## Definition of Done (Sprint 2)

This E2E test serves as the "definition of done" for Sprint 2. The sprint is considered complete when:

- [ ] The automated test script (`tests/e2e_test.sh`) runs successfully
- [ ] At least one MQTT message is published by the emulator
- [ ] At least one row exists in the measurements table
- [ ] All data fields are correctly populated (sensor_id, temperature, humidity, etc.)
- [ ] The test can be repeated reliably
- [ ] Documentation is clear and complete

## Running in CI/CD

The E2E test can be integrated into CI/CD pipelines. Example GitHub Actions workflow snippet:

```yaml
- name: Run E2E Test
  run: ./tests/e2e_test.sh
```

**Note**: The test script has execute permissions set in the repository (`chmod +x`), so no additional permission changes are needed in CI.

## Test Maintenance

### Updating the Test

When modifying the stack (e.g., changing database schema, MQTT topics, or service names), update:

1. The test script (`tests/e2e_test.sh`)
2. This documentation (`docs/e2e_test.md`)
3. Any configuration values in both files

### Adding New Test Cases

Future enhancements may include:

- Testing multiple MQTT messages
- Validating specific field values
- Testing error handling (invalid messages)
- Performance testing (message throughput)
- Testing Grafana dashboard availability

## References

- [Requirements Document](requirements.md) - Functional and non-functional requirements
- [MQTT Schema](mqtt_schema.md) - Message format specification
- [Docker Compose Stack](../compose/stack.yaml) - Stack configuration

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review container logs for error messages
3. Consult the requirements and schema documentation
4. Open an issue on the project repository
