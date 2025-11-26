#!/usr/bin/env python3
"""
Paku IoT Collector Service
===========================
Subscribes to MQTT topics and stores validated measurements in Postgres.
"""

import os
import json
import signal
import sys
from typing import Dict, Any, Optional
import psycopg
import paho.mqtt.client as mqtt


# Environment configuration
PGHOST = os.getenv('PGHOST', 'postgres')
PGUSER = os.getenv('PGUSER', 'paku')
PGPASSWORD = os.getenv('PGPASSWORD', 'paku')
PGDATABASE = os.getenv('PGDATABASE', 'paku')
MQTT_HOST = os.getenv('MQTT_HOST', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))

# Global counter for observability
rejected_message_count = 0


def validate_message(payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
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


def insert_measurement(conn: psycopg.Connection, payload: Dict[str, Any]) -> None:
    """
    Insert validated measurement into Postgres.
    
    Args:
        conn: Postgres connection
        payload: Validated payload
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO measurements (
                sensor_id,
                ts,
                temperature_c,
                humidity_percent,
                pressure_hpa,
                battery_mv,
                acceleration_x_mg,
                acceleration_y_mg,
                acceleration_z_mg,
                acceleration_total_mg,
                tx_power_dbm,
                movement_counter,
                measurement_sequence,
                mac
            ) VALUES (
                %(sensor_id)s,
                COALESCE(%(timestamp)s::timestamptz, NOW()),
                %(temperature_c)s,
                %(humidity_percent)s,
                %(pressure_hpa)s,
                %(battery_mv)s,
                %(acceleration_x_mg)s,
                %(acceleration_y_mg)s,
                %(acceleration_z_mg)s,
                %(acceleration_total_mg)s,
                %(tx_power_dbm)s,
                %(movement_counter)s,
                %(measurement_sequence)s,
                %(mac)s
            )
        """, payload)


def on_connect(client: mqtt.Client, userdata: Any, flags: Any, rc: int, properties: Any = None) -> None:
    """MQTT connection callback."""
    print(f'Collector connected to MQTT broker (rc={rc})', flush=True)
    client.subscribe('paku/#', qos=0)


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    """MQTT message callback with validation."""
    global rejected_message_count
    
    conn = userdata['conn']
    payload_str = msg.payload.decode('utf-8', 'replace')
    
    # Parse JSON
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        rejected_message_count += 1
        print(f'[ERROR] Invalid JSON on topic {msg.topic}: {e}', flush=True)
        print(f'[ERROR] Payload: {payload_str}', flush=True)
        print(f'[INFO] Total rejected messages: {rejected_message_count}', flush=True)
        return
    
    # Validate against schema
    is_valid, error_msg = validate_message(payload)
    if not is_valid:
        rejected_message_count += 1
        print(f'[ERROR] Validation failed for topic {msg.topic}: {error_msg}', flush=True)
        print(f'[ERROR] Payload: {json.dumps(payload)}', flush=True)
        print(f'[INFO] Total rejected messages: {rejected_message_count}', flush=True)
        return
    
    # Insert into database
    try:
        insert_measurement(conn, payload)
        print(f'[INFO] Inserted measurement from {payload.get("sensor_id")} (topic: {msg.topic})', flush=True)
    except Exception as e:
        print(f'[ERROR] Database insertion failed: {e}', flush=True)
        print(f'[ERROR] Payload: {json.dumps(payload)}', flush=True)


def main():
    """Main entry point for the collector service."""
    print('Starting Paku IoT Collector...', flush=True)
    
    # Connect to Postgres
    try:
        conn = psycopg.connect(
            host=PGHOST,
            user=PGUSER,
            password=PGPASSWORD,
            dbname=PGDATABASE,
            autocommit=True
        )
        print(f'Connected to Postgres at {PGHOST}', flush=True)
    except Exception as e:
        print(f'[ERROR] Failed to connect to Postgres: {e}', flush=True)
        sys.exit(1)
    
    # Set up MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.user_data_set({'conn': conn})
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        print(f'Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}', flush=True)
    except Exception as e:
        print(f'[ERROR] Failed to connect to MQTT broker: {e}', flush=True)
        conn.close()
        sys.exit(1)
    
    # Handle shutdown gracefully
    def shutdown_handler(sig, frame):
        print('\nShutting down collector...', flush=True)
        print(f'Total rejected messages: {rejected_message_count}', flush=True)
        client.loop_stop()
        conn.close()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # Run forever
    print('Collector is running and listening for messages...', flush=True)
    client.loop_forever()


if __name__ == '__main__':
    main()
