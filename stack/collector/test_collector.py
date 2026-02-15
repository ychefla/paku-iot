#!/usr/bin/env python3
"""
Unit tests for the paku collector service.

Tests cover:
  - Topic parsing (parse_topic)
  - Payload validation (validate_payload)

Run:  python -m pytest test_collector.py -v
"""

import pytest
import sys
import os

# Allow import of collector module from same directory
sys.path.insert(0, os.path.dirname(__file__))
from collector import parse_topic, validate_payload


# =====================================================================
# parse_topic
# =====================================================================

class TestParseTopic:
    """Tests for MQTT topic parsing."""

    def test_data_topic(self):
        result = parse_topic("paku/ruuvi/van_inside/data")
        assert result == ("paku", "ruuvi", "van_inside", "data")

    def test_status_topic(self):
        result = parse_topic("paku/edge/ESP32-ABC123/status")
        assert result == ("paku", "edge", "ESP32-ABC123", "status")

    def test_config_topic(self):
        result = parse_topic("paku/edge/ESP32-ABC123/config")
        assert result == ("paku", "edge", "ESP32-ABC123", "config")

    def test_ota_status_topic(self):
        result = parse_topic("paku/edge/ESP32-ABC123/ota/status")
        assert result == ("paku", "edge", "ESP32-ABC123", "ota_status")

    def test_ota_progress_topic(self):
        result = parse_topic("paku/edge/ESP32-ABC123/ota/progress")
        assert result == ("paku", "edge", "ESP32-ABC123", "ota_progress")

    def test_ota_result_topic(self):
        result = parse_topic("paku/edge/ESP32-ABC123/ota/result")
        assert result == ("paku", "edge", "ESP32-ABC123", "ota_result")

    def test_unknown_topic_type_returns_none(self):
        assert parse_topic("paku/ruuvi/van_inside/unknown") is None

    def test_too_few_segments_returns_none(self):
        assert parse_topic("paku/ruuvi") is None

    def test_too_many_segments_non_ota_returns_none(self):
        assert parse_topic("paku/ruuvi/van_inside/data/extra") is None

    def test_empty_string_returns_none(self):
        assert parse_topic("") is None

    def test_unknown_ota_subtype_returns_none(self):
        assert parse_topic("paku/edge/ESP32-ABC123/ota/unknown") is None

    def test_ota_wrong_system_returns_none(self):
        # OTA 5-segment but system is not "edge"
        assert parse_topic("paku/ruuvi/sensor1/ota/status") is None

    def test_heater_data_topic(self):
        result = parse_topic("paku/heater/emu01/data")
        assert result == ("paku", "heater", "emu01", "data")


# =====================================================================
# validate_payload
# =====================================================================

class TestValidatePayload:
    """Tests for sensor data payload validation."""

    def test_valid_payload(self):
        payload = {
            "device_id": "ruuvi_cabin",
            "metrics": {"temperature_c": 21.5, "humidity_percent": 45.2},
        }
        assert validate_payload(payload) is True

    def test_missing_device_id(self):
        payload = {"metrics": {"temperature_c": 21.5}}
        assert validate_payload(payload) is False

    def test_missing_metrics(self):
        payload = {"device_id": "ruuvi_cabin"}
        assert validate_payload(payload) is False

    def test_metrics_not_dict(self):
        payload = {"device_id": "ruuvi_cabin", "metrics": "not_a_dict"}
        assert validate_payload(payload) is False

    def test_metrics_empty(self):
        payload = {"device_id": "ruuvi_cabin", "metrics": {}}
        assert validate_payload(payload) is False

    def test_extra_fields_are_ok(self):
        payload = {
            "device_id": "ruuvi_cabin",
            "metrics": {"temperature_c": 21.5},
            "timestamp": "2025-12-01T20:00:00Z",
            "location": "cabin",
            "mac": "AA:BB:CC:DD:EE:FF",
        }
        assert validate_payload(payload) is True

    def test_empty_payload(self):
        assert validate_payload({}) is False

    def test_single_metric(self):
        payload = {"device_id": "sensor1", "metrics": {"battery_mv": 2870}}
        assert validate_payload(payload) is True


# =====================================================================
# Entry point
# =====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
