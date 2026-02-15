#!/usr/bin/env python3
"""
Ruuvi Tag Emulator - MQTT Publisher
Simulates RuuviTag sensor data and publishes to Mosquitto.
"""

import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion


def generate_sensor_data():
    """Generate realistic RuuviTag sensor data."""
    return {
        "sensor_id": "van_inside",
        "temperature_c": round(random.uniform(18.0, 25.0), 1),
        "humidity_percent": round(random.uniform(35.0, 55.0), 1),
        "pressure_hpa": round(random.uniform(990.0, 1020.0), 1),
        "acceleration_x_mg": random.randint(-50, 50),
        "acceleration_y_mg": random.randint(-50, 50),
        "acceleration_z_mg": random.randint(980, 1050),
        "acceleration_total_mg": random.randint(980, 1060),
        "tx_power_dbm": 4,
        "movement_counter": random.randint(0, 255),
        "measurement_sequence": random.randint(0, 65535),
        "battery_mv": random.randint(2800, 3000),
        "mac": "AA:BB:CC:DD:EE:FF",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }


def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when client connects to broker."""
    if reason_code.is_failure:
        print(f"Failed to connect to MQTT broker: {reason_code}")
    else:
        print("Connected to MQTT broker successfully")


def on_publish(client, userdata, mid, reason_code, properties):
    """Callback when message is published."""
    # Message published successfully (optional callback)
    pass


def main():
    # Get MQTT configuration from environment variables
    mqtt_host = os.getenv("MQTT_HOST", "mosquitto")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    topic = "paku/ruuvi/van_inside"
    max_runtime_seconds = int(os.getenv("MAX_RUNTIME_SECONDS", "300"))  # Default 5 minutes
    
    print(f"Starting Ruuvi emulator...")
    print(f"MQTT Broker: {mqtt_host}:{mqtt_port}")
    print(f"Topic: {topic}")
    print(f"Max runtime: {max_runtime_seconds} seconds")
    
    # Create MQTT client
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_publish = on_publish

    # Set credentials if provided
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)

    # Connect to broker with retry logic
    max_retries = 10
    retry_count = 0
    while retry_count < max_retries:
        try:
            client.connect(mqtt_host, mqtt_port, 60)
            break
        except Exception as e:
            retry_count += 1
            print(f"Failed to connect to broker (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                print("Max retries reached. Exiting.")
                return
    
    # Start the network loop in a background thread
    client.loop_start()
    
    # Give the client time to connect
    time.sleep(2)
    
    # Main publishing loop with runtime limit
    start_time = time.time()
    try:
        while True:
            # Check if max runtime has been reached
            elapsed_time = time.time() - start_time
            if elapsed_time >= max_runtime_seconds:
                print(f"\nMax runtime of {max_runtime_seconds} seconds reached. Shutting down...")
                break
            
            # Generate and publish sensor data
            data = generate_sensor_data()
            payload = json.dumps(data, indent=2)
            
            result = client.publish(topic, payload, qos=0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Published: {payload}")
            else:
                print(f"Failed to publish message: {result.rc}")
            
            # Wait 5-10 seconds before next publish
            wait_time = random.uniform(5, 10)
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\nShutting down emulator...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
