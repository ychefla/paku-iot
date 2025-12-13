#!/usr/bin/env python3
"""
Unit tests for EcoFlow Collector Service

Tests API client, data transformation, and database insertion logic.
"""

import hashlib
import hmac
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from ecoflow_collector import (
    EcoFlowAPI,
    insert_ecoflow_measurement,
    load_config,
    EcoFlowCollectorApp
)


# ---------------------------------------------------------------------
# EcoFlowAPI Tests
# ---------------------------------------------------------------------

def test_api_initialization():
    """Test EcoFlowAPI initialization."""
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    assert api.access_key == "test_key"
    assert api.secret_key == "test_secret"
    assert api.base_url == "https://api.test.com"


def test_api_base_url_strip_trailing_slash():
    """Test that base URL trailing slash is removed."""
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com/")
    assert api.base_url == "https://api.test.com"


def test_generate_sign():
    """Test HMAC signature generation."""
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    params = {
        "accessKey": "test_key",
        "nonce": "abc123",
        "timestamp": "1234567890"
    }
    sign = api._generate_sign(params)
    
    # Verify it's a hex string of correct length (SHA256 = 64 chars)
    assert isinstance(sign, str)
    assert len(sign) == 64
    assert all(c in '0123456789abcdef' for c in sign)


def test_generate_sign_consistent():
    """Test that signature generation is deterministic."""
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    params = {
        "accessKey": "test_key",
        "nonce": "abc123",
        "timestamp": "1234567890"
    }
    
    sign1 = api._generate_sign(params)
    sign2 = api._generate_sign(params)
    
    assert sign1 == sign2


def test_generate_sign_different_params():
    """Test that different parameters produce different signatures."""
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    
    params1 = {
        "accessKey": "test_key",
        "nonce": "abc123",
        "timestamp": "1234567890"
    }
    
    params2 = {
        "accessKey": "test_key",
        "nonce": "def456",
        "timestamp": "1234567890"
    }
    
    sign1 = api._generate_sign(params1)
    sign2 = api._generate_sign(params2)
    
    assert sign1 != sign2


def test_generate_sign_sorted_params():
    """Test that parameter order doesn't affect signature."""
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    
    # Different order, same values
    params1 = {
        "accessKey": "test_key",
        "nonce": "abc123",
        "timestamp": "1234567890"
    }
    
    params2 = {
        "timestamp": "1234567890",
        "nonce": "abc123",
        "accessKey": "test_key"
    }
    
    sign1 = api._generate_sign(params1)
    sign2 = api._generate_sign(params2)
    
    assert sign1 == sign2


@patch('ecoflow_collector.requests.get')
def test_make_api_request_get_success(mock_get):
    """Test successful GET API request."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": "0",
        "message": "Success",
        "data": {"bmsMaster.soc": 85}
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    result = api._make_api_request("/test/endpoint", method="GET")
    
    assert result == {"bmsMaster.soc": 85}
    assert mock_get.called


@patch('ecoflow_collector.requests.post')
def test_make_api_request_post_success(mock_post):
    """Test successful POST API request."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": "0",
        "message": "Success",
        "data": {"status": "ok"}
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    result = api._make_api_request("/test/endpoint", method="POST", body={"test": "data"})
    
    assert result == {"status": "ok"}
    assert mock_post.called


@patch('ecoflow_collector.requests.get')
def test_make_api_request_api_error(mock_get):
    """Test API request with error code from API."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": "1001",
        "message": "Invalid access key",
        "data": None
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    result = api._make_api_request("/test/endpoint", method="GET")
    
    assert result == {}


@patch('ecoflow_collector.requests.get')
def test_make_api_request_http_error(mock_get):
    """Test API request with HTTP error."""
    import requests
    mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")
    
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    result = api._make_api_request("/test/endpoint", method="GET")
    
    assert result == {}


@patch('ecoflow_collector.requests.get')
def test_make_api_request_timeout(mock_get):
    """Test API request timeout."""
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
    
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    result = api._make_api_request("/test/endpoint", method="GET")
    
    assert result == {}


@patch('ecoflow_collector.requests.get')
def test_get_device_quota_all(mock_get):
    """Test get_device_quota_all method."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": "0",
        "message": "Success",
        "data": {
            "bmsMaster.soc": 85,
            "pd.wattsInSum": 100,
            "pd.wattsOutSum": 50
        }
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    api = EcoFlowAPI("test_key", "test_secret", "https://api.test.com")
    result = api.get_device_quota_all("TEST123")
    
    assert result["bmsMaster.soc"] == 85
    assert result["pd.wattsInSum"] == 100
    assert result["pd.wattsOutSum"] == 50
    
    # Verify the URL was constructed correctly
    call_args = mock_get.call_args
    assert "/iot-open/sign/device/quota/all?sn=TEST123" in call_args[0][0]


# ---------------------------------------------------------------------
# Database Insertion Tests
# ---------------------------------------------------------------------

@patch('ecoflow_collector.psycopg.Connection')
def test_insert_ecoflow_measurement_complete(mock_conn):
    """Test EcoFlow data insertion with complete data."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.commit = Mock()
    
    data = {
        "bmsMaster.soc": 85,
        "pd.remainTime": 407,
        "pd.wattsInSum": 100,
        "pd.wattsOutSum": 50,
        "inv.outputWatts": 45,
        "pd.carWatts": 5,
        "pd.usb1Watts": 0,
        "pd.usb2Watts": 0,
        "pd.qcUsb1Watts": 0,
        "pd.qcUsb2Watts": 0,
        "pd.typec1Watts": 0,
        "pd.typec2Watts": 0,
        "mppt.inWatts": 100
    }
    
    insert_ecoflow_measurement(mock_conn, "TEST123", data)
    
    # Verify execute was called
    assert mock_cursor.execute.called
    call_args = mock_cursor.execute.call_args
    
    # Verify SQL contains INSERT
    assert "INSERT INTO ecoflow_measurements" in call_args[0][0]
    
    # Verify parameters
    params = call_args[0][1]
    assert params[0] == "TEST123"  # device_sn
    assert isinstance(params[1], datetime)  # ts
    assert params[2] == 85  # soc_percent
    assert params[3] == 407  # remain_time_min
    assert params[4] == 100  # watts_in_sum
    assert params[5] == 50  # watts_out_sum
    
    # Verify commit was called
    mock_conn.commit.assert_called_once()


@patch('ecoflow_collector.psycopg.Connection')
def test_insert_ecoflow_measurement_minimal(mock_conn):
    """Test EcoFlow data insertion with minimal data (defaults to 0)."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.commit = Mock()
    
    data = {}  # Empty data should use defaults
    
    insert_ecoflow_measurement(mock_conn, "TEST123", data)
    
    assert mock_cursor.execute.called
    call_args = mock_cursor.execute.call_args
    params = call_args[0][1]
    
    # Verify defaults
    assert params[2] == 0  # soc_percent
    assert params[3] == 0  # remain_time_min
    assert params[4] == 0  # watts_in_sum
    assert params[5] == 0  # watts_out_sum


@patch('ecoflow_collector.psycopg.Connection')
def test_insert_ecoflow_measurement_raw_data(mock_conn):
    """Test that raw_data is stored as JSON."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.commit = Mock()
    
    data = {
        "bmsMaster.soc": 85,
        "custom.field": "test_value"
    }
    
    insert_ecoflow_measurement(mock_conn, "TEST123", data)
    
    call_args = mock_cursor.execute.call_args
    params = call_args[0][1]
    
    # Last parameter should be raw_data JSON
    raw_data_json = params[-1]
    raw_data = json.loads(raw_data_json)
    assert raw_data["bmsMaster.soc"] == 85
    assert raw_data["custom.field"] == "test_value"


@patch('ecoflow_collector.psycopg.Connection')
def test_insert_ecoflow_measurement_usb_calculations(mock_conn):
    """Test USB output power calculations."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.commit = Mock()
    
    data = {
        "pd.usb1Watts": 5,
        "pd.usb2Watts": 3,
        "pd.qcUsb1Watts": 10,
        "pd.qcUsb2Watts": 7,
        "pd.typec1Watts": 15,
        "pd.typec2Watts": 12
    }
    
    insert_ecoflow_measurement(mock_conn, "TEST123", data)
    
    call_args = mock_cursor.execute.call_args
    params = call_args[0][1]
    
    # dc_out_watts should be car + all USB
    # With car=0, dc_out_watts = 5+3+10+7 = 25
    assert params[7] == 25  # dc_out_watts
    
    # typec_out_watts should be typec1 + typec2 = 15+12 = 27
    assert params[8] == 27  # typec_out_watts
    
    # usb_out_watts should be usb1+usb2+qcusb1+qcusb2 = 5+3+10+7 = 25
    assert params[9] == 25  # usb_out_watts


# ---------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------

def test_load_config_with_defaults():
    """Test configuration loading with default values."""
    with patch.dict('os.environ', {
        'ECOFLOW_ACCESS_KEY': 'test_key',
        'ECOFLOW_SECRET_KEY': 'test_secret',
        'ECOFLOW_DEVICE_SN': 'TEST123',
        'PGUSER': 'test_user',
        'PGPASSWORD': 'test_pass',
        'PGDATABASE': 'test_db'
    }, clear=True):
        config = load_config()
        
        assert config["ecoflow_access_key"] == "test_key"
        assert config["ecoflow_secret_key"] == "test_secret"
        assert config["ecoflow_device_sn"] == "TEST123"
        assert config["ecoflow_api_url"] == "https://api-e.ecoflow.com"
        assert config["pg_host"] == "postgres"
        assert config["pg_port"] == 5432
        assert config["rest_api_interval"] == 30


def test_load_config_with_custom_values():
    """Test configuration loading with custom environment variables."""
    with patch.dict('os.environ', {
        'ECOFLOW_ACCESS_KEY': 'custom_key',
        'ECOFLOW_SECRET_KEY': 'custom_secret',
        'ECOFLOW_DEVICE_SN': 'CUSTOM123',
        'ECOFLOW_API_URL': 'https://custom-api.com',
        'PGHOST': 'custom-pg',
        'PGPORT': '5433',
        'PGUSER': 'custom_user',
        'PGPASSWORD': 'custom_pass',
        'PGDATABASE': 'custom_db',
        'REST_API_INTERVAL': '60'
    }, clear=True):
        config = load_config()
        
        assert config["ecoflow_api_url"] == "https://custom-api.com"
        assert config["pg_host"] == "custom-pg"
        assert config["pg_port"] == 5433
        assert config["rest_api_interval"] == 60


def test_load_config_missing_required():
    """Test configuration loading fails with missing required variables."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing environment variable"):
            load_config()


# ---------------------------------------------------------------------
# EcoFlowCollectorApp Tests
# ---------------------------------------------------------------------

@patch('ecoflow_collector.psycopg.connect')
@patch('ecoflow_collector.EcoFlowAPI')
def test_collector_app_initialization(mock_api_class, mock_connect):
    """Test EcoFlowCollectorApp initialization."""
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    
    config = {
        "ecoflow_access_key": "test_key",
        "ecoflow_secret_key": "test_secret",
        "ecoflow_device_sn": "TEST123",
        "ecoflow_api_url": "https://api.test.com",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test",
        "rest_api_interval": 30
    }
    
    app = EcoFlowCollectorApp(config)
    
    assert app.device_sn == "TEST123"
    assert app.rest_api_interval == 30
    assert mock_api_class.called
    assert mock_connect.called


@patch('ecoflow_collector.psycopg.connect')
@patch('ecoflow_collector.EcoFlowAPI')
def test_collector_app_db_connection_error(mock_api_class, mock_connect):
    """Test EcoFlowCollectorApp handles DB connection error."""
    mock_connect.side_effect = Exception("Connection failed")
    
    config = {
        "ecoflow_access_key": "test_key",
        "ecoflow_secret_key": "test_secret",
        "ecoflow_device_sn": "TEST123",
        "ecoflow_api_url": "https://api.test.com",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test",
        "rest_api_interval": 30
    }
    
    with pytest.raises(Exception, match="Connection failed"):
        EcoFlowCollectorApp(config)


@patch('ecoflow_collector.psycopg.connect')
@patch('ecoflow_collector.EcoFlowAPI')
@patch('ecoflow_collector.insert_ecoflow_measurement')
def test_collector_fetch_and_store_data_success(mock_insert, mock_api_class, mock_connect):
    """Test successful data fetch and storage."""
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.execute = Mock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    mock_api = Mock()
    mock_api.get_device_quota_all.return_value = {
        "bmsMaster.soc": 85,
        "pd.wattsInSum": 100,
        "pd.wattsOutSum": 50,
        "mppt.inWatts": 100,
        "bmsMaster.temp": 25
    }
    mock_api_class.return_value = mock_api
    
    config = {
        "ecoflow_access_key": "test_key",
        "ecoflow_secret_key": "test_secret",
        "ecoflow_device_sn": "TEST123",
        "ecoflow_api_url": "https://api.test.com",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test",
        "rest_api_interval": 30
    }
    
    app = EcoFlowCollectorApp(config)
    app.fetch_and_store_data()
    
    # Verify API was called
    mock_api.get_device_quota_all.assert_called_once_with("TEST123")
    
    # Verify insert was called
    mock_insert.assert_called_once()


@patch('ecoflow_collector.psycopg.connect')
@patch('ecoflow_collector.EcoFlowAPI')
@patch('ecoflow_collector.insert_ecoflow_measurement')
def test_collector_fetch_and_store_data_no_data(mock_insert, mock_api_class, mock_connect):
    """Test fetch_and_store_data when API returns no data."""
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    mock_api = Mock()
    mock_api.get_device_quota_all.return_value = {}  # Empty data
    mock_api_class.return_value = mock_api
    
    config = {
        "ecoflow_access_key": "test_key",
        "ecoflow_secret_key": "test_secret",
        "ecoflow_device_sn": "TEST123",
        "ecoflow_api_url": "https://api.test.com",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test",
        "rest_api_interval": 30
    }
    
    app = EcoFlowCollectorApp(config)
    app.fetch_and_store_data()
    
    # Verify insert was NOT called
    mock_insert.assert_not_called()


@patch('ecoflow_collector.psycopg.connect')
@patch('ecoflow_collector.EcoFlowAPI')
def test_collector_ensure_db_connection_reconnects(mock_api_class, mock_connect):
    """Test that _ensure_db_connection reconnects when connection is lost."""
    # First connection succeeds, second connection also succeeds
    mock_conn1 = MagicMock()
    mock_conn1.closed = True  # Simulate closed connection
    
    mock_conn2 = MagicMock()
    mock_conn2.closed = False
    mock_cursor = MagicMock()
    mock_conn2.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_connect.side_effect = [mock_conn1, mock_conn2]
    
    config = {
        "ecoflow_access_key": "test_key",
        "ecoflow_secret_key": "test_secret",
        "ecoflow_device_sn": "TEST123",
        "ecoflow_api_url": "https://api.test.com",
        "pg_host": "test-pg",
        "pg_port": 5432,
        "pg_user": "test",
        "pg_password": "test",
        "pg_database": "test",
        "rest_api_interval": 30
    }
    
    app = EcoFlowCollectorApp(config)
    
    # Force reconnection
    app._ensure_db_connection()
    
    # Verify connect was called twice (initial + reconnect)
    assert mock_connect.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
