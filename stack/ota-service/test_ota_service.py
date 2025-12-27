"""
Unit tests for OTA Service

Tests API endpoints and core functionality.
"""

import json
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Set required environment variables before importing ota_service
os.environ['PGUSER'] = 'test'
os.environ['PGPASSWORD'] = 'test'
os.environ['PGDATABASE'] = 'test'


def test_percentage_match():
    """Test percentage-based device selection using consistent hashing."""
    from ota_service import _percentage_match
    
    # 100% should always match
    assert _percentage_match("device1", 100) == True
    assert _percentage_match("device2", 100) == True
    
    # 0% should never match
    assert _percentage_match("device1", 0) == False
    assert _percentage_match("device2", 0) == False
    
    # Same device should always get same result for same percentage
    result1 = _percentage_match("device123", 50)
    result2 = _percentage_match("device123", 50)
    assert result1 == result2
    
    # Distribution should be roughly even for many devices
    matches = sum(_percentage_match(f"device{i}", 50) for i in range(1000))
    assert 400 < matches < 600  # Should be around 500, allow 20% variance


def test_check_device_eligibility_all():
    """Test eligibility check for 'all' target type."""
    from ota_service import _check_device_eligibility
    
    # All devices with 100%
    assert _check_device_eligibility("device1", "all", None, 100) == True
    
    # All devices with 50% - should use percentage match
    result = _check_device_eligibility("device123", "all", None, 50)
    assert isinstance(result, bool)


def test_check_device_eligibility_specific():
    """Test eligibility check for 'specific' target type."""
    from ota_service import _check_device_eligibility
    
    target_filter = json.dumps({"device_ids": ["device1", "device2", "device3"]})
    
    # Device in list should match
    assert _check_device_eligibility("device1", "specific", target_filter, 100) == True
    assert _check_device_eligibility("device2", "specific", target_filter, 100) == True
    
    # Device not in list should not match
    assert _check_device_eligibility("device4", "specific", target_filter, 100) == False
    assert _check_device_eligibility("device999", "specific", target_filter, 100) == False


def test_check_device_eligibility_canary():
    """Test eligibility check for 'canary' target type."""
    from ota_service import _check_device_eligibility
    
    # Canary should use percentage match
    result = _check_device_eligibility("device123", "canary", None, 10)
    assert isinstance(result, bool)
    
    # Should be consistent
    result1 = _check_device_eligibility("device456", "canary", None, 25)
    result2 = _check_device_eligibility("device456", "canary", None, 25)
    assert result1 == result2


def test_check_device_eligibility_group():
    """Test eligibility check for 'group' target type."""
    from ota_service import _check_device_eligibility
    
    target_filter = json.dumps({"groups": ["location:warehouse", "function:sensor"]})
    
    # Mock database connection and cursor
    with patch('ota_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        
        # Test 1: Device in target group should match (with 100% rollout)
        mock_cursor.fetchone.return_value = ({"groups": ["location:warehouse", "env:production"]},)
        result = _check_device_eligibility("device1", "group", target_filter, 100)
        assert result is True
        
        # Test 2: Device in different target group should also match
        mock_cursor.fetchone.return_value = ({"groups": ["function:sensor", "env:testing"]},)
        result = _check_device_eligibility("device2", "group", target_filter, 100)
        assert result is True
        
        # Test 3: Device not in any target group should not match
        mock_cursor.fetchone.return_value = ({"groups": ["location:office", "env:development"]},)
        result = _check_device_eligibility("device3", "group", target_filter, 100)
        assert result is False
        
        # Test 4: Device with no groups should not match
        mock_cursor.fetchone.return_value = ({"groups": []},)
        result = _check_device_eligibility("device4", "group", target_filter, 100)
        assert result is False
        
        # Test 5: Device with no metadata should not match
        mock_cursor.fetchone.return_value = (None,)
        result = _check_device_eligibility("device5", "group", target_filter, 100)
        assert result is False
        
        # Test 6: Device not found should not match
        mock_cursor.fetchone.return_value = None
        result = _check_device_eligibility("device6", "group", target_filter, 100)
        assert result is False
        
        # Test 7: Empty target filter should return False
        result = _check_device_eligibility("device7", "group", json.dumps({"groups": []}), 100)
        assert result is False
        
        # Test 8: No target filter should return False
        result = _check_device_eligibility("device8", "group", None, 100)
        assert result is False
        
        # Test 9: Percentage rollout should apply to eligible devices
        mock_cursor.fetchone.return_value = ({"groups": ["location:warehouse"]},)
        # With 0% rollout, even eligible devices should not get update
        result = _check_device_eligibility("device9", "group", target_filter, 0)
        assert result is False
        
        # Test 10: Consistency check - same device should get same result
        mock_cursor.fetchone.return_value = ({"groups": ["location:warehouse"]},)
        result1 = _check_device_eligibility("device10", "group", target_filter, 50)
        mock_cursor.fetchone.return_value = ({"groups": ["location:warehouse"]},)
        result2 = _check_device_eligibility("device10", "group", target_filter, 50)
        assert result1 == result2


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    from ota_service import app
    from fastapi.testclient import TestClient
    
    with patch('ota_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_db.return_value = mock_conn
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test metrics endpoint."""
    from ota_service import app
    from fastapi.testclient import TestClient
    
    with patch('ota_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_cursor = MagicMock()
        
        # Mock cursor context manager
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Mock query results - fetchone is called twice (total devices and active rollouts)
        mock_cursor.fetchone.side_effect = [
            (100,),  # total devices
            (2,),    # active rollouts
        ]
        # Mock fetchall results
        mock_cursor.fetchall.side_effect = [
            [("esp32", 80), ("esp8266", 20)],  # devices by model
            [("success", 45), ("failed", 2)],  # recent updates
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        client = TestClient(app)
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_devices" in data
        assert "devices_by_model" in data
        assert "recent_updates_24h" in data
        assert "active_rollouts" in data


@pytest.mark.asyncio
async def test_firmware_check_no_update():
    """Test firmware check when no update available."""
    from ota_service import app
    from fastapi.testclient import TestClient
    
    with patch('ota_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_cursor = MagicMock()
        
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Mock: device registration succeeds, latest version matches current
        mock_cursor.fetchone.return_value = ("1.0.0", "/path/to/firmware.bin", 524288, "abc123", "Release notes")
        
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        client = TestClient(app)
        response = client.get(
            "/api/firmware/check",
            params={
                "device_id": "test_device",
                "device_model": "esp32",
                "current_version": "1.0.0"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["update_available"] == False
        assert data["current_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_firmware_check_with_update():
    """Test firmware check when update is available."""
    from ota_service import app
    from fastapi.testclient import TestClient
    
    with patch('ota_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_cursor = MagicMock()
        
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Mock: new version available and active rollout exists
        mock_cursor.fetchone.side_effect = [
            ("1.1.0", "/path/to/firmware.bin", 524288, "abc123", "Bug fixes"),  # latest firmware
            (1, "all", None, 100),  # active rollout
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        client = TestClient(app)
        response = client.get(
            "/api/firmware/check",
            params={
                "device_id": "test_device",
                "device_model": "esp32",
                "current_version": "1.0.0"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["update_available"] == True
        assert data["current_version"] == "1.0.0"
        assert data["latest_version"] == "1.1.0"
        assert "download_url" in data


@pytest.mark.asyncio
async def test_report_update_status():
    """Test device update status reporting."""
    from ota_service import app
    from fastapi.testclient import TestClient
    
    with patch('ota_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_cursor = MagicMock()
        
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        client = TestClient(app)
        response = client.post(
            "/api/device/test_device/update-status",
            json={
                "device_id": "test_device",
                "firmware_version": "1.1.0",
                "status": "success",
                "progress_percent": 100
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_devices():
    """Test listing devices."""
    from ota_service import app
    from fastapi.testclient import TestClient
    
    with patch('ota_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_cursor = MagicMock()
        
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Mock device list
        from datetime import datetime
        now = datetime.now()
        mock_cursor.fetchall.return_value = [
            ("device1", "esp32", "1.0.0", now, now),
            ("device2", "esp32", "1.1.0", now, now),
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        client = TestClient(app)
        response = client.get("/api/admin/devices?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert len(data["devices"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
