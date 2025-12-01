"""
Paku Collector Service

Subscribes to MQTT messages from IoT devices and writes validated measurements
into the Postgres `measurements` table using the new hierarchical schema.

Supports topic pattern: {site_id}/{system}/{device_id}/data

Environment variables (set via docker compose):

    MQTT_HOST
    MQTT_PORT
    MQTT_TOPIC_PATTERN (default: +/+/+/data)

    PGHOST
    PGPORT
    PGUSER
    PGPASSWORD
    PGDATABASE
"""

import json
import logging
import os
import re
import sys
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import psycopg


# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("paku-collector")


# ---------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------
def get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        logger.error("Required environment variable %s is not set", name)
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def load_config() -> Dict[str, Any]:
    return {
        "mqtt_host": get_env("MQTT_HOST", "mosquitto"),
        "mqtt_port": int(os.getenv("MQTT_PORT", "1883")),
        "mqtt_topic_pattern": get_env("MQTT_TOPIC_PATTERN", "+/+/+/data"),
        "pg_host": get_env("PGHOST", "postgres"),
        "pg_port": int(os.getenv("PGPORT", "5432")),
        "pg_user": get_env("PGUSER"),
        "pg_password": get_env("PGPASSWORD"),
        "pg_database": get_env("PGDATABASE"),
    }


# ---------------------------------------------------------------------
# Database handling
# ---------------------------------------------------------------------
def connect_to_database(cfg: Dict[str, Any]) -> psycopg.Connection:
    logger.info(
        "Connecting to Postgres at %s:%s db=%s",
        cfg["pg_host"],
        cfg["pg_port"],
        cfg["pg_database"],
    )
    conn = psycopg.connect(
        host=cfg["pg_host"],
        port=cfg["pg_port"],
        user=cfg["pg_user"],
        password=cfg["pg_password"],
        dbname=cfg["pg_database"],
        autocommit=True,
    )
    return conn


def insert_measurement(
    conn: psycopg.Connection,
    site_id: str,
    system: str,
    device_id: str,
    payload: Dict[str, Any]
) -> None:
    """
    Insert one measurement row into the database using new schema.
    
    Expected payload structure:
    {
        "timestamp": "2025-12-01T20:00:00Z",
        "device_id": "ruuvi_cabin",
        "location": "cabin",
        "mac": "AA:BB:CC:DD:EE:FF",
        "metrics": {
            "temperature_c": 21.5,
            "humidity_percent": 45.2,
            ...
        }
    }
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO measurements (
                site_id,
                system,
                device_id,
                location,
                mac,
                ts,
                metrics
            )
            VALUES (
                %(site_id)s,
                %(system)s,
                %(device_id)s,
                %(location)s,
                %(mac)s,
                COALESCE(%(timestamp)s::timestamptz, NOW()),
                %(metrics)s::jsonb
            )
            """,
            {
                "site_id": site_id,
                "system": system,
                "device_id": device_id,
                "location": payload.get("location"),
                "mac": payload.get("mac"),
                "timestamp": payload.get("timestamp"),
                "metrics": json.dumps(payload.get("metrics", {})),
            },
        )


# ---------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------
def validate_payload(data: Dict[str, Any]) -> bool:
    """
    Validate payload structure for new schema.
    
    Required: timestamp, device_id, metrics
    Optional: location
    """
    required_fields = ["timestamp", "device_id", "metrics"]
    missing = [f for f in required_fields if f not in data]
    
    if missing:
        logger.warning("Payload missing required fields %s: %s", missing, data)
        return False
    
    if not isinstance(data["metrics"], dict):
        logger.warning("metrics field must be a dict, got: %s", type(data["metrics"]))
        return False
    
    if not data["metrics"]:
        logger.warning("metrics field is empty: %s", data)
        return False
    
    return True


def parse_topic(topic: str) -> Optional[tuple[str, str, str, str]]:
    """
    Parse topic structure: {site_id}/{system}/{device_id}/{topic_type}
    
    Returns: (site_id, system, device_id, topic_type) or None if invalid
    """
    parts = topic.split("/")
    if len(parts) != 4:
        logger.warning("Invalid topic structure (expected 4 levels): %s", topic)
        return None
    
    site_id, system, device_id, topic_type = parts
    
    if topic_type != "data":
        # Only process /data topics
        return None
    
    return (site_id, system, device_id, topic_type)


# ---------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------
class CollectorApp:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self.conn: Optional[psycopg.Connection] = None
        self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def start(self) -> None:
        # Connect to DB once at startup
        self.conn = connect_to_database(self.cfg)

        logger.info(
            "Connecting to MQTT at %s:%s, subscribing to %s",
            self.cfg["mqtt_host"],
            self.cfg["mqtt_port"],
            self.cfg["mqtt_topic_pattern"],
        )
        self.client.connect(self.cfg["mqtt_host"], self.cfg["mqtt_port"], keepalive=60)
        self.client.loop_forever()

    # MQTT callbacks ---------------------------------------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("Failed to connect to MQTT broker: %s", reason_code)
        else:
            logger.info("Connected to MQTT broker, subscribing to %s", self.cfg["mqtt_topic_pattern"])
            client.subscribe(self.cfg["mqtt_topic_pattern"])

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        logger.warning("Disconnected from MQTT broker, reason_code=%s", reason_code)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload_raw = msg.payload.decode("utf-8", errors="replace")
        logger.debug("Received MQTT message on %s: %s", topic, payload_raw)

        # Parse topic to extract site_id, system, device_id
        parsed = parse_topic(topic)
        if not parsed:
            logger.debug("Ignoring non-data topic: %s", topic)
            return
        
        site_id, system, device_id, _ = parsed

        try:
            data = json.loads(payload_raw)
        except json.JSONDecodeError:
            logger.warning("Failed to decode JSON payload on %s: %s", topic, payload_raw)
            return

        if not isinstance(data, dict):
            logger.warning("Expected JSON object on %s, got: %r", topic, data)
            return

        if not validate_payload(data):
            # Already logged inside validate_payload
            return

        if self.conn is None:
            logger.error("No DB connection available; dropping message from %s", topic)
            return

        try:
            insert_measurement(self.conn, site_id, system, device_id, data)
            logger.info(
                "Inserted measurement: %s/%s/%s location=%s",
                site_id,
                system,
                device_id,
                data.get("location", "N/A")
            )
        except Exception as exc:
            logger.exception("Failed to insert measurement from %s: %s", topic, exc)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def main() -> None:
    cfg = load_config()
    app = CollectorApp(cfg)
    app.start()


if __name__ == "__main__":
    main()
