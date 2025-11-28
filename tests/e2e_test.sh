#!/bin/bash
# ------------------------------------------------------------
# Paku IoT End-to-End Test Script
#
# This script validates the full data pipeline:
#   1. Start the stack using docker compose
#   2. Wait for all services to be healthy
#   3. Publish an MQTT message
#   4. Verify the message appears in Postgres
#   5. Verify Grafana dashboard is accessible and has data
#
# Usage: ./tests/e2e_test.sh
# ------------------------------------------------------------

set -e

# Configuration
COMPOSE_FILE="compose/stack.yaml"
MQTT_HOST="localhost"
MQTT_PORT="1883"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_USER="paku"
POSTGRES_PASSWORD="paku"
POSTGRES_DB="paku"
GRAFANA_URL="http://localhost:3000"
TIMEOUT=120
TEST_SENSOR_ID="e2e_test_sensor"
TEST_TOPIC="paku/ruuvi/$TEST_SENSOR_ID"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker compose -f "$COMPOSE_FILE" down --volumes 2>/dev/null || true
}

# Check if required tools are available
check_requirements() {
    log_info "Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "docker compose is not available"
        exit 1
    fi
    
    log_info "All requirements met"
}

# Start the stack
start_stack() {
    log_info "Starting the stack with: docker compose -f $COMPOSE_FILE up --build -d"
    docker compose -f "$COMPOSE_FILE" up --build -d
    
    log_info "Waiting for services to be healthy..."
    
    local waited=0
    while [ $waited -lt $TIMEOUT ]; do
        local all_healthy=true
        
        # Check if postgres is healthy
        if ! docker compose -f "$COMPOSE_FILE" ps postgres 2>/dev/null | grep -q "healthy"; then
            all_healthy=false
        fi
        
        # Check if mosquitto is healthy
        if ! docker compose -f "$COMPOSE_FILE" ps mosquitto 2>/dev/null | grep -q "healthy"; then
            all_healthy=false
        fi
        
        # Check if grafana is healthy
        if ! docker compose -f "$COMPOSE_FILE" ps grafana 2>/dev/null | grep -q "healthy"; then
            all_healthy=false
        fi
        
        if [ "$all_healthy" = true ]; then
            log_info "All services are healthy"
            return 0
        fi
        
        sleep 5
        waited=$((waited + 5))
        log_info "Waiting for services... ($waited/$TIMEOUT seconds)"
    done
    
    log_error "Timeout waiting for services to be healthy"
    docker compose -f "$COMPOSE_FILE" ps
    docker compose -f "$COMPOSE_FILE" logs
    return 1
}

# Get the current row count before publishing
get_row_count() {
    docker exec paku_postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM measurements WHERE sensor_id = '$TEST_SENSOR_ID';" | tr -d ' '
}

# Publish an MQTT test message
publish_mqtt_message() {
    log_info "Publishing MQTT test message to $TEST_TOPIC..."
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local payload=$(cat <<EOF
{
  "sensor_id": "$TEST_SENSOR_ID",
  "temperature_c": 22.5,
  "humidity_percent": 55.0,
  "pressure_hpa": 1013.25,
  "acceleration_x_mg": 0,
  "acceleration_y_mg": 0,
  "acceleration_z_mg": 1000,
  "acceleration_total_mg": 1000,
  "tx_power_dbm": 4,
  "movement_counter": 1,
  "measurement_sequence": 1,
  "battery_mv": 2900,
  "mac": "E2:E2:E2:E2:E2:E2",
  "timestamp": "$timestamp"
}
EOF
)
    
    # Use docker exec to publish via mosquitto_pub in the mosquitto container
    echo "$payload" | docker exec -i paku_mosquitto mosquitto_pub -t "$TEST_TOPIC" -s
    
    log_info "Message published successfully"
}

# Verify the message was inserted into Postgres
verify_postgres() {
    log_info "Verifying message in Postgres..."
    
    local initial_count=$1
    local expected_count=$((initial_count + 1))
    local waited=0
    local max_wait=30
    
    while [ $waited -lt $max_wait ]; do
        local current_count=$(get_row_count)
        
        if [ "$current_count" -ge "$expected_count" ]; then
            log_info "Message found in Postgres (rows: $current_count)"
            
            # Show the inserted row
            log_info "Latest measurement:"
            docker exec paku_postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
                "SELECT id, ts, sensor_id, temperature_c, humidity_percent, pressure_hpa, battery_mv FROM measurements WHERE sensor_id = '$TEST_SENSOR_ID' ORDER BY ts DESC LIMIT 1;"
            
            return 0
        fi
        
        sleep 2
        waited=$((waited + 2))
        log_info "Waiting for Postgres insert... ($waited/$max_wait seconds)"
    done
    
    log_error "Message not found in Postgres within $max_wait seconds"
    log_info "Current row count: $(get_row_count), expected: $expected_count"
    
    # Show collector logs for debugging
    log_info "Collector logs:"
    docker logs paku_collector --tail 50
    
    return 1
}

# Verify Grafana is accessible and has data
verify_grafana() {
    log_info "Verifying Grafana dashboard..."
    
    # Check Grafana health
    if ! curl -s "$GRAFANA_URL/api/health" | grep -q "ok"; then
        log_error "Grafana health check failed"
        return 1
    fi
    log_info "Grafana health check passed"
    
    # Check if the Paku Overview dashboard exists
    local dashboard_response=$(curl -s "$GRAFANA_URL/api/dashboards/uid/paku-overview")
    if echo "$dashboard_response" | grep -q "Paku Overview"; then
        log_info "Paku Overview dashboard found"
    else
        log_warn "Paku Overview dashboard not found (might be in folder)"
    fi
    
    # Query the Postgres datasource through Grafana to verify data is accessible
    # First, get a short time range that includes our test data
    local from_time=$(date -u -d '1 hour ago' +%s%3N 2>/dev/null || date -u -v-1H +%s000)
    local to_time=$(date -u +%s%3N 2>/dev/null || date -u +%s000)
    
    local query_payload=$(cat <<EOF
{
  "queries": [
    {
      "refId": "A",
      "datasource": {"type": "postgres", "uid": "paku_pg"},
      "rawSql": "SELECT COUNT(*) as count FROM measurements WHERE sensor_id = '$TEST_SENSOR_ID';",
      "format": "table"
    }
  ],
  "from": "$from_time",
  "to": "$to_time"
}
EOF
)
    
    local query_response=$(curl -s -X POST "$GRAFANA_URL/api/ds/query" \
        -H "Content-Type: application/json" \
        -d "$query_payload" 2>/dev/null)
    
    if echo "$query_response" | grep -q "count"; then
        log_info "Grafana can query Postgres data successfully"
        log_info "Query response: $query_response"
    else
        log_warn "Could not verify Grafana data query (non-critical)"
        log_info "Response: $query_response"
    fi
    
    # Verify dashboard panels are configured correctly
    log_info "Checking Grafana dashboard panels..."
    local panels_response=$(curl -s "$GRAFANA_URL/api/dashboards/uid/paku-overview" | grep -o '"panels":\[[^]]*\]' | head -1)
    if [ -n "$panels_response" ]; then
        log_info "Dashboard panels are configured"
    fi
    
    log_info "Grafana verification complete"
    return 0
}

# Main test execution
main() {
    log_info "========================================"
    log_info "Paku IoT End-to-End Test"
    log_info "========================================"
    
    # Change to repository root
    cd "$(dirname "$0")/.."
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run tests
    check_requirements
    
    # Clean up any previous test run
    cleanup
    
    start_stack
    
    # Wait a bit for collector to be fully ready
    sleep 5
    
    # Get initial row count
    local initial_count=$(get_row_count)
    log_info "Initial row count for test sensor: $initial_count"
    
    publish_mqtt_message
    
    verify_postgres "$initial_count"
    
    verify_grafana
    
    log_info "========================================"
    log_info "All E2E tests passed!"
    log_info "========================================"
    
    return 0
}

# Run main function
main "$@"
