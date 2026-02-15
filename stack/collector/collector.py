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
        "mqtt_user": os.getenv("MQTT_USER"),
        "mqtt_password": os.getenv("MQTT_PASSWORD"),
        "mqtt_topic_patterns": [
            "+/+/+/data",    # Sensor data measurements
            "+/edge/+/status",  # Edge device status
            "+/edge/+/config",  # Edge device configuration
            "+/edge/+/ota/+",   # OTA status/progress/result
        ],
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


def insert_edge_status(
    conn: psycopg.Connection,
    site_id: str,
    device_id: str,
    payload: Dict[str, Any]
) -> None:
    """
    Insert edge device status into the database.
    
    Expected payload structure:
    {
        "timestamp": "2025-12-13T10:00:00Z",
        "state": "COLLECT",
        "uptime_s": 12345,
        "wifi": {...},
        "mqtt": {...},
        "device_id": "ESP32-27C136B8",
        "firmware_version": "1.3.0",
        "device_model": "lilygo-t-display-s3",
        ...
    }
    """
    with conn.cursor() as cur:
        # Register or update device in OTA devices table if device info is present
        device_model = payload.get("device_model")
        firmware_version = payload.get("firmware_version")
        
        if device_model:
            cur.execute(
                """
                INSERT INTO devices (device_id, device_model, current_firmware_version, last_seen)
                VALUES (%(device_id)s, %(device_model)s, %(firmware_version)s, NOW())
                ON CONFLICT (device_id) 
                DO UPDATE SET 
                    device_model = EXCLUDED.device_model,
                    current_firmware_version = EXCLUDED.current_firmware_version,
                    last_seen = NOW()
                """,
                {
                    "device_id": device_id,
                    "device_model": device_model,
                    "firmware_version": firmware_version,
                },
            )
        
        # Insert status record
        cur.execute(
            """
            INSERT INTO edge_device_status (
                site_id,
                device_id,
                status,
                ts
            )
            VALUES (
                %(site_id)s,
                %(device_id)s,
                %(status)s::jsonb,
                COALESCE(%(timestamp)s::timestamptz, NOW())
            )
            """,
            {
                "site_id": site_id,
                "device_id": device_id,
                "status": json.dumps(payload),
                "timestamp": payload.get("timestamp"),
            },
        )


def upsert_edge_config(
    conn: psycopg.Connection,
    site_id: str,
    device_id: str,
    payload: Dict[str, Any]
) -> None:
    """
    Upsert edge device configuration into the database.
    
    Expected payload structure:
    {
        "timing": {...},
        "sensors": {...},
        "power": {...},
        ...
    }
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO edge_device_configs (
                site_id,
                device_id,
                config,
                updated_at
            )
            VALUES (
                %(site_id)s,
                %(device_id)s,
                %(config)s::jsonb,
                NOW()
            )
            ON CONFLICT (site_id, device_id)
            DO UPDATE SET
                config = %(config)s::jsonb,
                updated_at = NOW()
            """,
            {
                "site_id": site_id,
                "device_id": device_id,
                "config": json.dumps(payload),
            },
        )


# ---------------------------------------------------------------------
# OTA message handling
# ---------------------------------------------------------------------
def handle_ota_message(
    conn: psycopg.Connection,
    device_id: str,
    ota_type: str,
    payload: Dict[str, Any],
) -> None:
    """
    Process OTA MQTT messages (status / progress / result) and write
    into device_update_status + ota_events tables.

    ota_type is one of: "status", "progress", "result"
    """
    firmware_version = payload.get("target_version", payload.get("version", "unknown"))

    with conn.cursor() as cur:
        if ota_type == "status":
            # OTA command acknowledged – create initial tracking row
            cur.execute(
                """
                INSERT INTO device_update_status
                    (device_id, firmware_version, status, started_at, reported_at)
                VALUES (%(device_id)s, %(fw)s, 'pending', NOW(), NOW())
                """,
                {"device_id": device_id, "fw": firmware_version},
            )
            cur.execute(
                """
                INSERT INTO ota_events
                    (event_type, device_id, firmware_version, event_data)
                VALUES ('update_started', %(device_id)s, %(fw)s, %(data)s::jsonb)
                """,
                {
                    "device_id": device_id,
                    "fw": firmware_version,
                    "data": json.dumps(payload),
                },
            )

        elif ota_type == "progress":
            # Update the latest tracking row with progress
            status = "downloading"
            state = payload.get("state", "").lower()
            if state == "installing":
                status = "installing"
            elif state == "verifying":
                status = "downloaded"

            cur.execute(
                """
                UPDATE device_update_status
                SET status = %(status)s,
                    progress_percent = %(pct)s,
                    reported_at = NOW()
                WHERE id = (
                    SELECT id FROM device_update_status
                    WHERE device_id = %(device_id)s
                    ORDER BY reported_at DESC
                    LIMIT 1
                )
                """,
                {
                    "device_id": device_id,
                    "status": status,
                    "pct": payload.get("percent", 0),
                },
            )

        elif ota_type == "result":
            success = payload.get("success", False)
            final_status = "success" if success else "failed"
            error_msg = None if success else payload.get("message")

            cur.execute(
                """
                UPDATE device_update_status
                SET status = %(status)s,
                    progress_percent = CASE WHEN %(success)s THEN 100 ELSE progress_percent END,
                    error_message = %(err)s,
                    completed_at = NOW(),
                    reported_at = NOW()
                WHERE id = (
                    SELECT id FROM device_update_status
                    WHERE device_id = %(device_id)s
                    ORDER BY reported_at DESC
                    LIMIT 1
                )
                """,
                {
                    "device_id": device_id,
                    "status": final_status,
                    "success": success,
                    "err": error_msg,
                },
            )

            event_type = "update_completed" if success else "update_failed"
            cur.execute(
                """
                INSERT INTO ota_events
                    (event_type, device_id, firmware_version, event_data)
                VALUES (%(evt)s, %(device_id)s, %(fw)s, %(data)s::jsonb)
                """,
                {
                    "evt": event_type,
                    "device_id": device_id,
                    "fw": firmware_version,
                    "data": json.dumps(payload),
                },
            )


# ---------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------
def validate_payload(data: Dict[str, Any]) -> bool:
    """
    Validate payload structure for new schema.
    
    Required: device_id, metrics
    Optional: timestamp, location
    """
    required_fields = ["device_id", "metrics"]
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
    Parse topic structure:
      4-segment: {site_id}/{system}/{device_id}/{topic_type}
      5-segment: {site_id}/edge/{device_id}/ota/{ota_type}
    
    Returns: (site_id, system, device_id, topic_type) or None if invalid
    
    Supported topic_types:
    - data: sensor measurements
    - status: edge device status updates  
    - config: edge device configuration
    - ota_status, ota_progress, ota_result: OTA update messages
    """
    parts = topic.split("/")

    # 5-segment OTA topics: {site_id}/edge/{device_id}/ota/{ota_type}
    if len(parts) == 5 and parts[1] == "edge" and parts[3] == "ota":
        site_id, system, device_id, _, ota_type = parts
        if ota_type in ["status", "progress", "result"]:
            return (site_id, system, device_id, f"ota_{ota_type}")
        logger.debug("Ignoring unknown OTA sub-topic '%s': %s", ota_type, topic)
        return None

    # 4-segment standard topics
    if len(parts) != 4:
        logger.warning("Invalid topic structure (expected 4 or 5 levels): %s", topic)
        return None
    
    site_id, system, device_id, topic_type = parts
    
    # Support data, status, and config topics
    if topic_type not in ["data", "status", "config"]:
        logger.debug("Ignoring unsupported topic type '%s': %s", topic_type, topic)
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

        # Set MQTT credentials if provided
        mqtt_user = self.cfg.get("mqtt_user")
        mqtt_password = self.cfg.get("mqtt_password")
        if mqtt_user and mqtt_password:
            self.client.username_pw_set(mqtt_user, mqtt_password)
            logger.info("MQTT authentication enabled (user=%s)", mqtt_user)

        logger.info(
            "Connecting to MQTT at %s:%s, subscribing to: %s",
            self.cfg["mqtt_host"],
            self.cfg["mqtt_port"],
            ", ".join(self.cfg["mqtt_topic_patterns"]),
        )
        self.client.connect(self.cfg["mqtt_host"], self.cfg["mqtt_port"], keepalive=60)
        self.client.loop_forever()

    # MQTT callbacks ---------------------------------------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("Failed to connect to MQTT broker: %s", reason_code)
        else:
            logger.info("Connected to MQTT broker")
            for pattern in self.cfg["mqtt_topic_patterns"]:
                client.subscribe(pattern)
                logger.info("Subscribed to: %s", pattern)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        logger.warning("Disconnected from MQTT broker, reason_code=%s", reason_code)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload_raw = msg.payload.decode("utf-8", errors="replace")
        logger.debug("Received MQTT message on %s: %s", topic, payload_raw)

        # Parse topic to extract site_id, system, device_id, topic_type
        parsed = parse_topic(topic)
        if not parsed:
            logger.debug("Ignoring unsupported topic: %s", topic)
            return
        
        site_id, system, device_id, topic_type = parsed

        try:
            data = json.loads(payload_raw)
        except json.JSONDecodeError:
            logger.warning("Failed to decode JSON payload on %s: %s", topic, payload_raw)
            return

        if not isinstance(data, dict):
            logger.warning("Expected JSON object on %s, got: %r", topic, data)
            return

        if self.conn is None:
            logger.error("No DB connection available; dropping message from %s", topic)
            return

        try:
            if topic_type == "data":
                # Handle sensor data measurements
                if not validate_payload(data):
                    return
                
                insert_measurement(self.conn, site_id, system, device_id, data)
                logger.info(
                    "Inserted measurement: %s/%s/%s location=%s",
                    site_id,
                    system,
                    device_id,
                    data.get("location", "N/A")
                )
                
            elif topic_type == "status" and system == "edge":
                # Handle edge device status updates
                insert_edge_status(self.conn, site_id, device_id, data)
                logger.info(
                    "Inserted edge status: %s/edge/%s state=%s",
                    site_id,
                    device_id,
                    data.get("state", "N/A")
                )
                
            elif topic_type == "config" and system == "edge":
                # Handle edge device configuration updates
                upsert_edge_config(self.conn, site_id, device_id, data)
                logger.info(
                    "Updated edge config: %s/edge/%s",
                    site_id,
                    device_id
                )

            elif topic_type.startswith("ota_") and system == "edge":
                # Handle OTA status/progress/result messages
                ota_type = topic_type[4:]  # strip "ota_" prefix
                handle_ota_message(self.conn, device_id, ota_type, data)
                logger.info(
                    "OTA %s from %s/edge/%s",
                    ota_type,
                    site_id,
                    device_id,
                )
            else:
                logger.debug("Unhandled topic type: %s (system=%s)", topic_type, system)
                
        except Exception as exc:
            logger.exception("Failed to process message from %s: %s", topic, exc)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def main() -> None:
    cfg = load_config()
    app = CollectorApp(cfg)
    app.start()


if __name__ == "__main__":
    main()
