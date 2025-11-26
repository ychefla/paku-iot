#!/usr/bin/env python3
"""
Paku IoT Collector Service
Subscribes to MQTT topics and writes sensor data to Postgres.
"""

import os
import sys
import json
import signal
import logging
from datetime import datetime

import paho.mqtt.client as mqtt
import psycopg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('collector')

# Configuration from environment variables
MQTT_HOST = os.getenv('MQTT_HOST', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'paku/ruuvi/van_inside')

PGHOST = os.getenv('PGHOST', 'postgres')
PGPORT = int(os.getenv('PGPORT', '5432'))
PGUSER = os.getenv('PGUSER', 'paku')
PGPASSWORD = os.getenv('PGPASSWORD', 'paku')
PGDATABASE = os.getenv('PGDATABASE', 'paku')

# Global connection object
db_conn = None
mqtt_client = None


def connect_to_database():
    """Establish connection to PostgreSQL database."""
    global db_conn
    try:
        logger.info(f"Connecting to PostgreSQL at {PGHOST}:{PGPORT}...")
        db_conn = psycopg.connect(
            host=PGHOST,
            port=PGPORT,
            user=PGUSER,
            password=PGPASSWORD,
            dbname=PGDATABASE,
            autocommit=True
        )
        logger.info("Successfully connected to PostgreSQL")
        return db_conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)


def insert_measurement(data):
    """
    Insert a measurement into the database.
    
    Args:
        data: Dictionary containing sensor data with fields:
              - sensor_id
              - temperature_c
              - humidity_percent
              - pressure_hpa
              - battery_mv
              - timestamp (optional)
    """
    try:
        # Extract fields from the payload
        sensor_id = data.get('sensor_id', 'unknown')
        temperature_c = data.get('temperature_c')
        humidity_percent = data.get('humidity_percent')
        pressure_hpa = data.get('pressure_hpa')
        battery_mv = data.get('battery_mv')
        
        # Use provided timestamp or current time
        timestamp = data.get('timestamp')
        if timestamp:
            # Parse ISO 8601 timestamp
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            ts = None  # Will use database default (now())
        
        # Insert into database
        with db_conn.cursor() as cur:
            if ts:
                cur.execute(
                    """
                    INSERT INTO measurements 
                    (sensor_id, ts, temperature_c, humidity_percent, pressure_hpa, battery_mv)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (sensor_id, ts, temperature_c, humidity_percent, pressure_hpa, battery_mv)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO measurements 
                    (sensor_id, temperature_c, humidity_percent, pressure_hpa, battery_mv)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (sensor_id, temperature_c, humidity_percent, pressure_hpa, battery_mv)
                )
        
        logger.info(
            f"Inserted measurement: sensor_id={sensor_id}, "
            f"temp={temperature_c}°C, humidity={humidity_percent}%, "
            f"pressure={pressure_hpa}hPa, battery={battery_mv}mV"
        )
        
    except Exception as e:
        logger.error(f"Failed to insert measurement: {e}")
        # Don't re-raise - we want to continue processing other messages


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when the client connects to the MQTT broker."""
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        logger.info(f"Subscribing to topic: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC, qos=0)
    else:
        logger.error(f"Failed to connect to MQTT broker, return code: {rc}")


def on_message(client, userdata, msg):
    """
    Callback when a message is received from the MQTT broker.
    
    Args:
        client: MQTT client instance
        userdata: User data
        msg: MQTT message with topic and payload
    """
    try:
        # Decode the payload
        payload_str = msg.payload.decode('utf-8')
        logger.debug(f"Received message on topic {msg.topic}: {payload_str}")
        
        # Parse JSON
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload on topic {msg.topic}: {e}")
            logger.debug(f"Malformed payload: {payload_str}")
            return  # Skip this message and continue
        
        # Insert into database
        insert_measurement(data)
        
    except Exception as e:
        logger.error(f"Error processing message from topic {msg.topic}: {e}")
        # Continue processing other messages


def on_disconnect(client, userdata, rc, properties=None):
    """Callback when the client disconnects from the MQTT broker."""
    if rc != 0:
        logger.warning(f"Unexpected disconnect from MQTT broker, return code: {rc}")


def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    
    if db_conn:
        db_conn.close()
    
    sys.exit(0)


def main():
    """Main entry point for the collector service."""
    global mqtt_client
    
    logger.info("Starting Paku IoT Collector Service")
    logger.info(f"MQTT: {MQTT_HOST}:{MQTT_PORT}, Topic: {MQTT_TOPIC}")
    logger.info(f"PostgreSQL: {PGHOST}:{PGPORT}/{PGDATABASE}")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # Connect to database
    connect_to_database()
    
    # Set up MQTT client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    
    # Connect to MQTT broker
    try:
        logger.info(f"Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}...")
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        sys.exit(1)
    
    # Start the MQTT loop (blocking)
    logger.info("Collector service is running. Press Ctrl+C to stop.")
    mqtt_client.loop_forever()


if __name__ == '__main__':
    main()
