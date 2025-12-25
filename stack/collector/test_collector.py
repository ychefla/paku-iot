#!/usr/bin/env python3
"""
Unit tests for Collector Service

Tests core functionality including topic parsing, payload validation,
and database insertion logic.
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from collector import (
    parse_topic,
    validate_payload,
    insert_measurement,
    load_config,
    CollectorApp
)


# ---------------------------------------------------------------------
# Topic Parsing Tests
# ---------------------------------------------------------------------

def test_parse_topic_valid():
    """Test parsing valid topic structure."""
    result = parse_topic("van/ruuvi/sensor1/data")
    assert result == ("van", "ruuvi", "sensor1", "data")


def test_parse_topic_valid_different_values():
    """Test parsing with different valid values."""
    result = parse_topic("home/ecoflow/battery1/data")
    assert result == ("home", "ecoflow", "battery1", "data")


def test_parse_topic_invalid_too_few_levels():
    """Test parsing topic with too few levels."""
    result = parse_topic("van/ruuvi")
    assert result is None


def test_parse_topic_invalid_too_many_levels():
    """Test parsing topic with too many levels."""
    result = parse_topic("van/ruuvi/sensor1/data/extra")
    assert result is None


def test_parse_topic_non_data():
    """Test parsing non-data topics (should be ignored)."""
    result = parse_topic("van/ruuvi/sensor1/status")
    assert result is None


def test_parse_topic_command():
    """Test parsing command topics (should be ignored)."""
    result = parse_topic("van/ruuvi/sensor1/command")
    assert result is None


def test_parse_topic_empty():
    """Test parsing empty topic."""
    result = parse_topic("")
    assert result is None


# ---------------------------------------------------------------------
# Payload Validation Tests
# ---------------------------------------------------------------------

def test_validate_payload_valid():
    """Test validation with complete valid payload."""
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "location": "cabin",
        "mac": "AA:BB:CC:DD:EE:FF",
        "metrics": {
            "temperature_c": 22.5,
            "humidity_percent": 45.0
        }
    }
    assert validate_payload(payload) == True


def test_validate_payload_minimal_valid():
    """Test validation with minimal valid payload (required fields only)."""
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": {"temperature_c": 22.5}
    }
    assert validate_payload(payload) == True


def test_validate_payload_missing_timestamp():
    """Test validation with missing timestamp."""
    payload = {
        "device_id": "sensor1",
        "metrics": {"temperature_c": 22.5}
    }
    assert validate_payload(payload) == False


def test_validate_payload_missing_device_id():
    """Test validation with missing device_id."""
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "metrics": {"temperature_c": 22.5}
    }
    assert validate_payload(payload) == False


def test_validate_payload_missing_metrics():
    """Test validation with missing metrics."""
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1"
    }
    assert validate_payload(payload) == False


def test_validate_payload_metrics_not_dict():
    """Test validation with metrics field not being a dictionary."""
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": "not a dict"
    }
    assert validate_payload(payload) == False


def test_validate_payload_metrics_empty():
    """Test validation with empty metrics dictionary."""
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": {}
    }
    assert validate_payload(payload) == False


def test_validate_payload_metrics_list():
    """Test validation with metrics as list instead of dict."""
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": ["temperature", 22.5]
    }
    assert validate_payload(payload) == False


# ---------------------------------------------------------------------
# Database Insertion Tests
# ---------------------------------------------------------------------

@patch('collector.psycopg.Connection')
def test_insert_measurement_complete(mock_conn):
    """Test database insertion with complete payload."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "location": "cabin",
        "mac": "AA:BB:CC:DD:EE:FF",
        "metrics": {
            "temperature_c": 22.5,
            "humidity_percent": 45.0
        }
    }
    
    insert_measurement(mock_conn, "van", "ruuvi", "sensor1", payload)
    
    # Verify execute was called
    assert mock_cursor.execute.called
    call_args = mock_cursor.execute.call_args
    
    # Verify SQL contains INSERT
    assert "INSERT INTO measurements" in call_args[0][0]
    
    # Verify parameters
    params = call_args[0][1]
    assert params["site_id"] == "van"
    assert params["system"] == "ruuvi"
    assert params["device_id"] == "sensor1"
    assert params["location"] == "cabin"
    assert params["mac"] == "AA:BB:CC:DD:EE:FF"
    assert params["timestamp"] == "2025-12-13T10:00:00Z"
    
    # Verify metrics is JSON string
    metrics = json.loads(params["metrics"])
    assert metrics["temperature_c"] == 22.5
    assert metrics["humidity_percent"] == 45.0


@patch('collector.psycopg.Connection')
def test_insert_measurement_minimal(mock_conn):
    """Test database insertion with minimal payload."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": {"temperature_c": 22.5}
    }
    
    insert_measurement(mock_conn, "van", "ruuvi", "sensor1", payload)
    
    assert mock_cursor.execute.called
    call_args = mock_cursor.execute.call_args
    params = call_args[0][1]
    
    # Optional fields should be None
    assert params["location"] is None
    assert params["mac"] is None


@patch('collector.psycopg.Connection')
def test_insert_measurement_no_location(mock_conn):
    """Test database insertion without location."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "mac": "AA:BB:CC:DD:EE:FF",
        "metrics": {"temperature_c": 22.5}
    }
    
    insert_measurement(mock_conn, "van", "ruuvi", "sensor1", payload)
    
    assert mock_cursor.execute.called
    call_args = mock_cursor.execute.call_args
    params = call_args[0][1]
    assert params["location"] is None
    assert params["mac"] == "AA:BB:CC:DD:EE:FF"


# ---------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------

def test_load_config_with_defaults():
    """Test configuration loading with default values."""
    with patch.dict('os.environ', {
        'PGUSER': 'test_user',
        'PGPASSWORD': 'test_pass',
        'PGDATABASE': 'test_db'
    }, clear=True):
        config = load_config()
        
        # Check defaults
        assert config["mqtt_host"] == "mosquitto"
        assert config["mqtt_port"] == 1883
        assert config["mqtt_topic_pattern"] == "+/+/+/data"
        assert config["pg_host"] == "postgres"
        assert config["pg_port"] == 5432
        
        # Check provided values
        assert config["pg_user"] == "test_user"
        assert config["pg_password"] == "test_pass"
        assert config["pg_database"] == "test_db"


def test_load_config_with_custom_values():
    """Test configuration loading with custom environment variables."""
    with patch.dict('os.environ', {
        'MQTT_HOST': 'custom-mqtt',
        'MQTT_PORT': '8883',
        'MQTT_TOPIC_PATTERN': 'custom/+/+/data',
        'PGHOST': 'custom-pg',
        'PGPORT': '5433',
        'PGUSER': 'custom_user',
        'PGPASSWORD': 'custom_pass',
        'PGDATABASE': 'custom_db'
    }, clear=True):
        config = load_config()
        
        assert config["mqtt_host"] == "custom-mqtt"
        assert config["mqtt_port"] == 8883
        assert config["mqtt_topic_pattern"] == "custom/+/+/data"
        assert config["pg_host"] == "custom-pg"
        assert config["pg_port"] == 5433
        assert config["pg_user"] == "custom_user"
        assert config["pg_password"] == "custom_pass"
        assert config["pg_database"] == "custom_db"


def test_load_config_missing_required():
    """Test configuration loading fails with missing required variables."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing environment variable"):
            load_config()


# ---------------------------------------------------------------------
# MQTT Callback Tests
# ---------------------------------------------------------------------

@patch('collector.connect_to_database')
@patch('collector.mqtt.Client')
def test_collector_on_connect_success(mock_client_class, mock_db):
    """Test MQTT connection callback on success."""
    mock_conn = Mock()
    mock_db.return_value = mock_conn
    
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    config = {
        "mqtt_host": "test-mqtt",
        "mqtt_port": 1883,
        "mqtt_topic_pattern": "+/+/+/data",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test"
    }
    
    app = CollectorApp(config)
    
    # Simulate successful connection
    mock_reason_code = Mock()
    mock_reason_code.is_failure = False
    
    app.on_connect(app.client, None, None, mock_reason_code, None)
    
    # Verify subscribe was called
    app.client.subscribe.assert_called_once_with("+/+/+/data")


@patch('collector.connect_to_database')
@patch('collector.mqtt.Client')
def test_collector_on_connect_failure(mock_client_class, mock_db):
    """Test MQTT connection callback on failure."""
    mock_conn = Mock()
    mock_db.return_value = mock_conn
    
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    config = {
        "mqtt_host": "test-mqtt",
        "mqtt_port": 1883,
        "mqtt_topic_pattern": "+/+/+/data",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test"
    }
    
    app = CollectorApp(config)
    
    # Simulate failed connection
    mock_reason_code = Mock()
    mock_reason_code.is_failure = True
    
    app.on_connect(app.client, None, None, mock_reason_code, None)
    
    # Verify subscribe was NOT called
    app.client.subscribe.assert_not_called()


@patch('collector.connect_to_database')
@patch('collector.mqtt.Client')
@patch('collector.insert_measurement')
def test_collector_on_message_valid(mock_insert, mock_client_class, mock_db):
    """Test MQTT message callback with valid message."""
    mock_conn = Mock()
    mock_db.return_value = mock_conn
    
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    config = {
        "mqtt_host": "test-mqtt",
        "mqtt_port": 1883,
        "mqtt_topic_pattern": "+/+/+/data",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test"
    }
    
    app = CollectorApp(config)
    app.conn = mock_conn
    
    # Create mock MQTT message
    mock_msg = Mock()
    mock_msg.topic = "van/ruuvi/sensor1/data"
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": {"temperature_c": 22.5}
    }
    mock_msg.payload = json.dumps(payload).encode('utf-8')
    
    app.on_message(app.client, None, mock_msg)
    
    # Verify insert was called
    mock_insert.assert_called_once()
    call_args = mock_insert.call_args[0]
    assert call_args[0] == mock_conn
    assert call_args[1] == "van"
    assert call_args[2] == "ruuvi"
    assert call_args[3] == "sensor1"


@patch('collector.connect_to_database')
@patch('collector.mqtt.Client')
@patch('collector.insert_measurement')
def test_collector_on_message_invalid_json(mock_insert, mock_client_class, mock_db):
    """Test MQTT message callback with invalid JSON."""
    mock_conn = Mock()
    mock_db.return_value = mock_conn
    
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    config = {
        "mqtt_host": "test-mqtt",
        "mqtt_port": 1883,
        "mqtt_topic_pattern": "+/+/+/data",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test"
    }
    
    app = CollectorApp(config)
    app.conn = mock_conn
    
    # Create mock MQTT message with invalid JSON
    mock_msg = Mock()
    mock_msg.topic = "van/ruuvi/sensor1/data"
    mock_msg.payload = b"not valid json {"
    
    app.on_message(app.client, None, mock_msg)
    
    # Verify insert was NOT called
    mock_insert.assert_not_called()


@patch('collector.connect_to_database')
@patch('collector.mqtt.Client')
@patch('collector.insert_measurement')
def test_collector_on_message_invalid_topic(mock_insert, mock_client_class, mock_db):
    """Test MQTT message callback with invalid topic structure."""
    mock_conn = Mock()
    mock_db.return_value = mock_conn
    
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    config = {
        "mqtt_host": "test-mqtt",
        "mqtt_port": 1883,
        "mqtt_topic_pattern": "+/+/+/data",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test"
    }
    
    app = CollectorApp(config)
    app.conn = mock_conn
    
    # Create mock MQTT message with invalid topic
    mock_msg = Mock()
    mock_msg.topic = "invalid/topic"
    payload = {
        "timestamp": "2025-12-13T10:00:00Z",
        "device_id": "sensor1",
        "metrics": {"temperature_c": 22.5}
    }
    mock_msg.payload = json.dumps(payload).encode('utf-8')
    
    app.on_message(app.client, None, mock_msg)
    
    # Verify insert was NOT called
    mock_insert.assert_not_called()


@patch('collector.connect_to_database')
@patch('collector.mqtt.Client')
@patch('collector.insert_measurement')
def test_collector_on_message_invalid_payload(mock_insert, mock_client_class, mock_db):
    """Test MQTT message callback with invalid payload."""
    mock_conn = Mock()
    mock_db.return_value = mock_conn
    
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    config = {
        "mqtt_host": "test-mqtt",
        "mqtt_port": 1883,
        "mqtt_topic_pattern": "+/+/+/data",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test"
    }
    
    app = CollectorApp(config)
    app.conn = mock_conn
    
    # Create mock MQTT message with invalid payload (missing required fields)
    mock_msg = Mock()
    mock_msg.topic = "van/ruuvi/sensor1/data"
    payload = {
        "device_id": "sensor1"
        # Missing timestamp and metrics
    }
    mock_msg.payload = json.dumps(payload).encode('utf-8')
    
    app.on_message(app.client, None, mock_msg)
    
    # Verify insert was NOT called
    mock_insert.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
