#!/bin/bash
# End-to-end test for Paku IoT stack
# Verifies the full path from MQTT message to Postgres row
#
# Usage:
#   ./tests/e2e_test.sh
#
# Requirements:
#   - Docker and Docker Compose installed
#   - psql client (for Postgres verification)
#   - curl (for Grafana API verification)

set -e

# Configuration
COMPOSE_FILE="compose/stack.yaml"
MQTT_TOPIC="paku/ruuvi/van_inside"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="paku"
DB_USER="paku"
DB_PASSWORD="paku"
TIMEOUT_SECONDS=60
CHECK_INTERVAL=5

# Grafana configuration
GRAFANA_HOST="localhost"
GRAFANA_PORT="3000"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="admin"
GRAFANA_DASHBOARD_UID="paku-ruuvi"

# Container names (must match compose/stack.yaml)
CONTAINER_EMULATOR="paku_ruuvi_emulator"
CONTAINER_COLLECTOR="paku_collector"
CONTAINER_MOSQUITTO="paku_mosquitto"
CONTAINER_POSTGRES="paku_postgres"
CONTAINER_GRAFANA="paku_grafana"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Paku IoT End-to-End Test"
echo "=========================================="
echo ""

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Step 1: Checking prerequisites..."
if ! command_exists docker; then
    print_error "Docker is not installed"
    exit 1
fi
print_success "Docker is installed"

if ! docker compose version >/dev/null 2>&1; then
    print_error "Docker Compose is not installed"
    echo "Install Docker Compose v2+ with your Docker installation"
    exit 1
fi
print_success "Docker Compose is installed"

if ! command_exists psql; then
    print_error "psql is not installed (required for database verification)"
    echo "Install it with: sudo apt-get install postgresql-client (Ubuntu/Debian)"
    echo "             or: brew install postgresql (macOS)"
    exit 1
fi
print_success "psql is installed"

if ! command_exists curl; then
    print_error "curl is not installed (required for Grafana API verification)"
    echo "Install it with: sudo apt-get install curl (Ubuntu/Debian)"
    echo "             or: brew install curl (macOS)"
    exit 1
fi
print_success "curl is installed"
echo ""

# Change to repository root
cd "$(dirname "$0")/.."

# Function to stop the stack
stop_stack() {
    docker compose -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
}

# Clean up function
cleanup() {
    echo ""
    print_info "Cleaning up..."
    stop_stack
    print_success "Cleanup completed"
}

# Register cleanup on exit
trap cleanup EXIT

# Step 2: Start the stack
echo "Step 2: Starting the Docker Compose stack..."
stop_stack
docker compose -f "$COMPOSE_FILE" up --build -d

if [ $? -ne 0 ]; then
    print_error "Failed to start the stack"
    exit 1
fi
print_success "Stack started successfully"
echo ""

# Step 3: Wait for services to be ready
echo "Step 3: Waiting for services to be ready..."
print_info "Waiting for Postgres to accept connections..."
elapsed=0
while [ $elapsed -lt $TIMEOUT_SECONDS ]; do
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" >/dev/null 2>&1; then
        print_success "Postgres is ready"
        break
    fi
    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
    print_info "Still waiting... (${elapsed}s/${TIMEOUT_SECONDS}s)"
done

if [ $elapsed -ge $TIMEOUT_SECONDS ]; then
    print_error "Postgres did not become ready in time"
    exit 1
fi
echo ""

# Step 4: Check if measurements table exists
echo "Step 4: Checking database schema..."
TABLE_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc \
    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'measurements');")

if [ "$TABLE_EXISTS" = "t" ]; then
    print_success "measurements table exists"
else
    print_error "measurements table does not exist"
    print_info "Expected schema should be created during Postgres initialization"
    exit 1
fi
echo ""

# Step 5: Wait for MQTT messages to be processed
echo "Step 5: Waiting for MQTT messages to be published and processed..."
print_info "Checking if ruuvi-emulator is publishing messages..."
print_info "Checking if collector is processing messages..."
print_info "Waiting for at least one row in measurements table..."

elapsed=0
row_count=0
while [ $elapsed -lt $TIMEOUT_SECONDS ]; do
    row_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc \
        "SELECT COUNT(*) FROM measurements;")
    
    if [ "$row_count" -gt 0 ]; then
        print_success "Found $row_count row(s) in measurements table"
        break
    fi
    
    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
    print_info "Still waiting... (${elapsed}s/${TIMEOUT_SECONDS}s) - Current row count: $row_count"
done

if [ "$row_count" -eq 0 ]; then
    print_error "No rows found in measurements table after ${TIMEOUT_SECONDS}s"
    print_info "Checking container logs for debugging..."
    echo ""
    echo "=== Ruuvi Emulator Logs ==="
    docker logs "$CONTAINER_EMULATOR" 2>&1 | tail -20
    echo ""
    echo "=== Collector Logs ==="
    docker logs "$CONTAINER_COLLECTOR" 2>&1 | tail -20
    echo ""
    echo "=== Mosquitto Logs ==="
    docker logs "$CONTAINER_MOSQUITTO" 2>&1 | tail -20
    exit 1
fi
echo ""

# Step 6: Verify data content
echo "Step 6: Verifying data content..."
SAMPLE_ROW=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c \
    "SELECT id, sensor_id, ts, temperature_c, humidity_percent FROM measurements LIMIT 1;" 2>&1)

if [ $? -eq 0 ]; then
    print_success "Successfully retrieved sample data:"
    echo "$SAMPLE_ROW"
else
    print_error "Failed to retrieve sample data"
    exit 1
fi
echo ""

# Step 7: Verify Grafana dashboard
echo "Step 7: Verifying Grafana dashboard..."
GRAFANA_URL="http://${GRAFANA_HOST}:${GRAFANA_PORT}"

# Wait for Grafana to be ready
print_info "Waiting for Grafana to be ready..."
elapsed=0
while [ $elapsed -lt $TIMEOUT_SECONDS ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${GRAFANA_URL}/api/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Grafana is ready"
        break
    fi
    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
    print_info "Still waiting... (${elapsed}s/${TIMEOUT_SECONDS}s)"
done

if [ $elapsed -ge $TIMEOUT_SECONDS ]; then
    print_error "Grafana did not become ready in time"
    docker logs "$CONTAINER_GRAFANA" 2>&1 | tail -20
    exit 1
fi

# Verify dashboard exists
print_info "Verifying dashboard '${GRAFANA_DASHBOARD_UID}' exists..."
DASHBOARD_RESPONSE=$(curl -s --fail -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
    "${GRAFANA_URL}/api/dashboards/uid/${GRAFANA_DASHBOARD_UID}" 2>&1)
CURL_EXIT=$?

if [ $CURL_EXIT -ne 0 ]; then
    print_error "Failed to connect to Grafana API"
    echo "Response: $DASHBOARD_RESPONSE"
    exit 1
fi

if echo "$DASHBOARD_RESPONSE" | grep -q '"title"'; then
    DASHBOARD_TITLE=$(echo "$DASHBOARD_RESPONSE" | grep -o '"title":"[^"]*"' | head -1 | cut -d'"' -f4)
    print_success "Dashboard '${DASHBOARD_TITLE}' exists"
else
    print_error "Dashboard '${GRAFANA_DASHBOARD_UID}' not found"
    echo "Response: $DASHBOARD_RESPONSE"
    exit 1
fi

# Verify Grafana can query measurement data via datasource
print_info "Verifying Grafana can query measurement data..."
QUERY_RESPONSE=$(curl -s --fail -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
    -H "Content-Type: application/json" \
    -X POST "${GRAFANA_URL}/api/ds/query" \
    -d '{
        "queries": [
            {
                "refId": "A",
                "datasource": {"uid": "paku-pg", "type": "postgres"},
                "rawSql": "SELECT COUNT(*) as count FROM measurements",
                "format": "table"
            }
        ],
        "from": "now-1h",
        "to": "now"
    }' 2>&1)
CURL_EXIT=$?

if [ $CURL_EXIT -ne 0 ]; then
    print_error "Failed to query Grafana datasource API"
    echo "Response: $QUERY_RESPONSE"
    exit 1
fi

# Parse count from JSON response - look for value in the values array
if echo "$QUERY_RESPONSE" | grep -q '"values"'; then
    # Extract count value from JSON - values array contains [[count]]
    QUERY_COUNT=$(echo "$QUERY_RESPONSE" | grep -o '\[\[*[0-9]\+\]*\]' | grep -o '[0-9]\+' | head -1)
    if [ -n "$QUERY_COUNT" ] && [ "$QUERY_COUNT" -gt 0 ]; then
        print_success "Grafana successfully queried $QUERY_COUNT measurement(s) from database"
    else
        print_error "Grafana query returned no measurements"
        echo "Response: $QUERY_RESPONSE"
        exit 1
    fi
else
    print_error "Grafana failed to query measurement data"
    echo "Response: $QUERY_RESPONSE"
    exit 1
fi
echo ""

# Step 8: Final summary
echo "=========================================="
echo "End-to-End Test Summary"
echo "=========================================="
print_success "All tests passed!"
echo ""
echo "Test results:"
echo "  - Stack started: ✓"
echo "  - Postgres ready: ✓"
echo "  - measurements table exists: ✓"
echo "  - At least one row inserted: ✓ ($row_count row(s) found)"
echo "  - Data retrieval working: ✓"
echo "  - Grafana dashboard accessible: ✓"
echo "  - Grafana data query working: ✓"
echo ""
print_info "The full MQTT → Postgres → Grafana pipeline is working correctly."
echo "=========================================="

exit 0
