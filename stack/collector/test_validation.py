#!/usr/bin/env python3
"""
Simple unit test for message validation logic.
This test can be run without external dependencies.
"""

import sys
import json

# Import the validation function (mock version for testing without paho-mqtt)
def validate_message(payload):
    """
    Validate MQTT message against the RuuviTag schema.
    
    Args:
        payload: Parsed JSON payload
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = {
        'sensor_id': str,
        'temperature_c': (int, float),
        'humidity_percent': (int, float),
        'pressure_hpa': (int, float),
        'battery_mv': int,
    }
    
    # Check for missing required fields
    for field, expected_type in required_fields.items():
        if field not in payload:
            return False, f"Missing required field: {field}"
        
        # Validate type
        if not isinstance(payload[field], expected_type):
            actual_type = type(payload[field]).__name__
            if isinstance(expected_type, tuple):
                expected_names = ' or '.join(t.__name__ for t in expected_type)
            else:
                expected_names = expected_type.__name__
            return False, f"Field '{field}' has incorrect type: expected {expected_names}, got {actual_type}"
    
    return True, None


def test_valid_message():
    """Test with a valid RuuviTag message."""
    payload = {
        "sensor_id": "van_inside",
        "temperature_c": 21.5,
        "humidity_percent": 45.2,
        "pressure_hpa": 1003.2,
        "acceleration_x_mg": -23,
        "acceleration_y_mg": 5,
        "acceleration_z_mg": 1015,
        "acceleration_total_mg": 1016,
        "tx_power_dbm": 4,
        "movement_counter": 120,
        "measurement_sequence": 34123,
        "battery_mv": 2870,
        "mac": "AA:BB:CC:DD:EE:FF",
        "timestamp": "2025-11-25T09:30:00Z"
    }
    is_valid, error = validate_message(payload)
    assert is_valid, f"Expected valid message, got error: {error}"
    print("✓ Valid message test passed")


def test_missing_sensor_id():
    """Test with missing sensor_id."""
    payload = {
        "temperature_c": 21.5,
        "humidity_percent": 45.2,
        "pressure_hpa": 1003.2,
        "battery_mv": 2870
    }
    is_valid, error = validate_message(payload)
    assert not is_valid, "Expected invalid message"
    assert "sensor_id" in error, f"Expected 'sensor_id' in error message, got: {error}"
    print(f"✓ Missing sensor_id test passed (error: {error})")


def test_missing_temperature():
    """Test with missing temperature_c."""
    payload = {
        "sensor_id": "van_inside",
        "humidity_percent": 45.2,
        "pressure_hpa": 1003.2,
        "battery_mv": 2870
    }
    is_valid, error = validate_message(payload)
    assert not is_valid, "Expected invalid message"
    assert "temperature_c" in error, f"Expected 'temperature_c' in error message, got: {error}"
    print(f"✓ Missing temperature test passed (error: {error})")


def test_wrong_type_sensor_id():
    """Test with wrong type for sensor_id."""
    payload = {
        "sensor_id": 12345,  # Should be string
        "temperature_c": 21.5,
        "humidity_percent": 45.2,
        "pressure_hpa": 1003.2,
        "battery_mv": 2870
    }
    is_valid, error = validate_message(payload)
    assert not is_valid, "Expected invalid message"
    assert "sensor_id" in error and "type" in error, f"Expected type error for sensor_id, got: {error}"
    print(f"✓ Wrong type sensor_id test passed (error: {error})")


def test_wrong_type_temperature():
    """Test with wrong type for temperature_c."""
    payload = {
        "sensor_id": "van_inside",
        "temperature_c": "21.5",  # Should be number
        "humidity_percent": 45.2,
        "pressure_hpa": 1003.2,
        "battery_mv": 2870
    }
    is_valid, error = validate_message(payload)
    assert not is_valid, "Expected invalid message"
    assert "temperature_c" in error and "type" in error, f"Expected type error for temperature_c, got: {error}"
    print(f"✓ Wrong type temperature test passed (error: {error})")


def test_integer_temperature():
    """Test with integer temperature (should be valid)."""
    payload = {
        "sensor_id": "van_inside",
        "temperature_c": 21,  # Integer should be accepted
        "humidity_percent": 45.2,
        "pressure_hpa": 1003.2,
        "battery_mv": 2870
    }
    is_valid, error = validate_message(payload)
    assert is_valid, f"Expected valid message with integer temperature, got error: {error}"
    print("✓ Integer temperature test passed")


def test_wrong_type_battery():
    """Test with wrong type for battery_mv."""
    payload = {
        "sensor_id": "van_inside",
        "temperature_c": 21.5,
        "humidity_percent": 45.2,
        "pressure_hpa": 1003.2,
        "battery_mv": 2870.5  # Should be int
    }
    is_valid, error = validate_message(payload)
    assert not is_valid, "Expected invalid message"
    assert "battery_mv" in error and "type" in error, f"Expected type error for battery_mv, got: {error}"
    print(f"✓ Wrong type battery test passed (error: {error})")


def run_all_tests():
    """Run all validation tests."""
    print("\n=== Running Validation Tests ===\n")
    
    tests = [
        test_valid_message,
        test_missing_sensor_id,
        test_missing_temperature,
        test_wrong_type_sensor_id,
        test_wrong_type_temperature,
        test_integer_temperature,
        test_wrong_type_battery
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print(f"\n=== Results: {len(tests) - failed}/{len(tests)} tests passed ===\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
