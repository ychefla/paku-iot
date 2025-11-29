"""
Paku Collector Service

Subscribes to MQTT messages from the Ruuvi emulator and writes
validated measurements into the Postgres `measurements` table.

Environment variables (set via docker compose):

    MQTT_HOST
    MQTT_PORT
    MQTT_TOPIC

    PGHOST
    PGPORT
    PGUSER
    PGPASSWORD
    PGDATABASE
"""

import json
import logging
import os
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
        "mqtt_topic": get_env("MQTT_TOPIC", "paku/ruuvi/van_inside"),
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


def insert_measurement(conn: psycopg.Connection, payload: Dict[str, Any]) -> None:
    """
    Insert one measurement row into the database.

    Expects payload to follow docs/mqtt_schema.md, i.e. at least:
      sensor_id, temperature_c, humidity_percent, pressure_hpa, battery_mv
    plus optional accel/tx/movement fields.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
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
            )
            VALUES (
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
            """,
            payload,
        )


# ---------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------
REQUIRED_FIELDS = [
    "sensor_id",
    "temperature_c",
    "humidity_percent",
    "pressure_hpa",
    "battery_mv",
]


def validate_payload(data: Dict[str, Any]) -> bool:
    """Very simple schema validation against expected Ruuvi fields."""
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        logger.warning("Payload missing required fields %s: %s", missing, data)
        return False

    # Type checks for main numeric fields (best-effort)
    numeric_fields = [
        "temperature_c",
        "humidity_percent",
        "pressure_hpa",
        "battery_mv",
        "acceleration_x_mg",
        "acceleration_y_mg",
        "acceleration_z_mg",
        "acceleration_total_mg",
        "tx_power_dbm",
        "movement_counter",
        "measurement_sequence",
    ]
    for field in numeric_fields:
        if field in data and data[field] is not None:
            try:
                float(data[field])
            except (TypeError, ValueError):
                logger.warning("Invalid numeric field %s=%r in payload %s", field, data[field], data)
                return False

    return True


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
            self.cfg["mqtt_topic"],
        )
        self.client.connect(self.cfg["mqtt_host"], self.cfg["mqtt_port"], keepalive=60)
        self.client.loop_forever()

    # MQTT callbacks ---------------------------------------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("Failed to connect to MQTT broker: %s", reason_code)
        else:
            logger.info("Connected to MQTT broker, subscribing to %s", self.cfg["mqtt_topic"])
            client.subscribe(self.cfg["mqtt_topic"])

    def on_disconnect(self, client, userdata, reason_code, properties):
        logger.warning("Disconnected from MQTT broker, reason_code=%s", reason_code)

    def on_message(self, client, userdata, msg):
        payload_raw = msg.payload.decode("utf-8", errors="replace")
        logger.debug("Received MQTT message on %s: %s", msg.topic, payload_raw)

        try:
            data = json.loads(payload_raw)
        except json.JSONDecodeError:
            logger.warning("Failed to decode JSON payload: %s", payload_raw)
            return

        if not isinstance(data, dict):
            logger.warning("Expected JSON object, got: %r", data)
            return

        if not validate_payload(data):
            # Already logged inside validate_payload
            return

        if self.conn is None:
            logger.error("No DB connection available; dropping message")
            return

        try:
            insert_measurement(self.conn, data)
            logger.info("Inserted measurement for sensor_id=%s", data.get("sensor_id"))
        except Exception as exc:
            logger.exception("Failed to insert measurement: %s", exc)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def main() -> None:
    cfg = load_config()
    app = CollectorApp(cfg)
    app.start()


if __name__ == "__main__":
    main()
