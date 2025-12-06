"""
EcoFlow Collector Service

Connects to EcoFlow Cloud API to obtain MQTT credentials,
then subscribes to EcoFlow MQTT broker to receive real-time
power station data and writes it to the Postgres database.

Environment variables (set via docker compose):

    ECOFLOW_ACCESS_KEY - EcoFlow Developer API access key
    ECOFLOW_SECRET_KEY - EcoFlow Developer API secret key
    ECOFLOW_DEVICE_SN - Device serial number (optional, for filtering)

    PGHOST
    PGPORT
    PGUSER
    PGPASSWORD
    PGDATABASE
"""

import hashlib
import hmac
import json
import logging
import os
import random
import ssl
import string
import sys
import time
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import psycopg
import requests


# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("paku-ecoflow-collector")


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
        "ecoflow_access_key": get_env("ECOFLOW_ACCESS_KEY"),
        "ecoflow_secret_key": get_env("ECOFLOW_SECRET_KEY"),
        "ecoflow_device_sn": os.getenv("ECOFLOW_DEVICE_SN", ""),
        "ecoflow_api_url": os.getenv("ECOFLOW_API_URL", "https://api-e.ecoflow.com"),
        "pg_host": get_env("PGHOST", "postgres"),
        "pg_port": int(os.getenv("PGPORT", "5432")),
        "pg_user": get_env("PGUSER"),
        "pg_password": get_env("PGPASSWORD"),
        "pg_database": get_env("PGDATABASE"),
    }


# ---------------------------------------------------------------------
# EcoFlow API integration
# ---------------------------------------------------------------------
class EcoFlowAPI:
    """Helper class to interact with EcoFlow Developer API."""
    
    def __init__(self, access_key: str, secret_key: str, base_url: Optional[str] = None):
        self.access_key = access_key
        self.secret_key = secret_key
        # Support regional endpoints: US (default), EU, or custom
        self.base_url = base_url or "https://api.ecoflow.com"
    
    def _generate_sign(self, params: Dict[str, str]) -> str:
        """
        Generate HMAC-SHA256 signature for EcoFlow API request.
        
        The signature is computed from a sorted, concatenated string of parameters.
        """
        # Sort parameters by key
        sorted_params = sorted(params.items())
        # Concatenate as key=value pairs
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        # Create HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def get_mqtt_credentials(self) -> Dict[str, Any]:
        """
        Request MQTT credentials from EcoFlow API.
        
        Returns dict with: url, port, username, password, protocol, clientId
        """
        # Generate request parameters
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        timestamp = str(int(time.time() * 1000))  # milliseconds
        
        # Build parameters for signature
        params = {
            "accessKey": self.access_key,
            "nonce": nonce,
            "timestamp": timestamp
        }
        
        # Generate signature
        sign = self._generate_sign(params)
        
        # Make GET request with parameters as headers (required by EU API)
        url = f"{self.base_url}/iot-open/sign/certification"
        headers = {
            "accessKey": self.access_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign
        }
        
        logger.info("Requesting MQTT credentials from EcoFlow API...")
        logger.debug("API endpoint: %s", url)
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error("Failed to get MQTT credentials: HTTP %s - %s", 
                        response.status_code, response.text)
            raise RuntimeError(f"EcoFlow API error: {response.status_code}")
        
        data = response.json()
        
        if data.get("code") != "0":
            logger.error("EcoFlow API returned error: %s", data)
            raise RuntimeError(f"EcoFlow API error: {data.get('message', 'Unknown error')}")
        
        mqtt_data = data.get("data", {})
        logger.info("Successfully obtained MQTT credentials")
        logger.debug("MQTT info: host=%s port=%s", mqtt_data.get("url"), mqtt_data.get("port"))
        
        return mqtt_data


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


def insert_ecoflow_measurement(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """
    Insert EcoFlow power station measurement into the database.
    
    Expected fields from EcoFlow MQTT payload (Delta Pro):
    - soc (state of charge %)
    - remainTime (minutes)
    - wattsInSum (total input watts)
    - wattsOutSum (total output watts)
    - Various port-specific power readings
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ecoflow_measurements (
                device_sn,
                ts,
                soc_percent,
                remain_time_min,
                watts_in_sum,
                watts_out_sum,
                ac_out_watts,
                dc_out_watts,
                typec_out_watts,
                usb_out_watts,
                pv_in_watts,
                raw_data
            )
            VALUES (
                %(device_sn)s,
                NOW(),
                %(soc_percent)s,
                %(remain_time_min)s,
                %(watts_in_sum)s,
                %(watts_out_sum)s,
                %(ac_out_watts)s,
                %(dc_out_watts)s,
                %(typec_out_watts)s,
                %(usb_out_watts)s,
                %(pv_in_watts)s,
                %(raw_data)s
            )
            """,
            data,
        )


def parse_ecoflow_payload(raw_payload: Dict[str, Any], device_sn: str = "") -> Dict[str, Any]:
    """
    Parse EcoFlow MQTT payload into our database schema.
    
    EcoFlow sends complex nested structures. We extract key metrics.
    """
    # EcoFlow typically nests data in a "params" or "data" field
    params = raw_payload.get("params", {})
    
    # Common field mappings (may vary by device model)
    parsed = {
        "device_sn": device_sn or raw_payload.get("sn", "unknown"),
        "soc_percent": params.get("soc") or params.get("bmsMaster", {}).get("soc"),
        "remain_time_min": params.get("remainTime"),
        "watts_in_sum": params.get("wattsInSum") or params.get("inv", {}).get("inputWatts"),
        "watts_out_sum": params.get("wattsOutSum") or params.get("inv", {}).get("outputWatts"),
        "ac_out_watts": params.get("invOutWatts"),
        "dc_out_watts": params.get("dcOutWatts"),
        "typec_out_watts": params.get("typecOutWatts"),
        "usb_out_watts": params.get("usbOutWatts"),
        "pv_in_watts": params.get("pvInWatts") or params.get("pv", {}).get("inputWatts"),
        "raw_data": json.dumps(raw_payload),  # Store full payload for reference
    }
    
    return parsed


# ---------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------
class EcoFlowCollectorApp:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self.conn: Optional[psycopg.Connection] = None
        self.mqtt_credentials: Optional[Dict[str, Any]] = None
        self.client: Optional[mqtt.Client] = None
        self.device_sn = cfg.get("ecoflow_device_sn", "")
    
    def start(self) -> None:
        # Connect to database
        self.conn = connect_to_database(self.cfg)
        
        # Get MQTT credentials from EcoFlow API
        # Use configured API URL (defaults to EU endpoint)
        api_url = self.cfg.get("ecoflow_api_url", "https://api-e.ecoflow.com")
        api = EcoFlowAPI(
            self.cfg["ecoflow_access_key"],
            self.cfg["ecoflow_secret_key"],
            api_url
        )
        self.mqtt_credentials = api.get_mqtt_credentials()
        
        # Setup MQTT client
        client_id = self.mqtt_credentials.get("clientId", "paku-ecoflow-collector")
        self.client = mqtt.Client(
            client_id=client_id,
            callback_api_version=CallbackAPIVersion.VERSION2
        )
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        
        # Setup TLS with proper certificate verification
        self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        
        # Setup credentials (certificateAccount and certificatePassword from API)
        username = self.mqtt_credentials.get("certificateAccount") or self.mqtt_credentials.get("username")
        password = self.mqtt_credentials.get("certificatePassword") or self.mqtt_credentials.get("password")
        self.client.username_pw_set(username, password)
        
        # Connect
        host = self.mqtt_credentials.get("url", "mqtt.ecoflow.com")
        port = int(self.mqtt_credentials.get("port", 8883))
        
        logger.info("Connecting to EcoFlow MQTT broker at %s:%s", host, port)
        self.client.connect(host, port, keepalive=60)
        self.client.loop_forever()
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("Failed to connect to EcoFlow MQTT broker: %s", reason_code)
        else:
            logger.info("Connected to EcoFlow MQTT broker")
            
            # Subscribe to device topic(s)
            # EcoFlow topic format: /app/{appKey}/{deviceSn}/thing/property/+
            # The appKey is the user ID from MQTT credentials
            app_key = self.mqtt_credentials.get("certificateAccount", "").split("/")[0] if "/" in self.mqtt_credentials.get("certificateAccount", "") else self.mqtt_credentials.get("certificateAccount", "")
            
            if self.device_sn:
                # Subscribe to specific device property updates
                topic1 = f"/app/{app_key}/{self.device_sn}/thing/property/+"
                logger.info("Subscribing to device property topic: %s", topic1)
                result1 = client.subscribe(topic1, qos=1)
                logger.info("Subscribe result: %s", result1)
                
                # Also try the simpler format
                topic2 = f"/app/device/property/{self.device_sn}"
                logger.info("Also subscribing to: %s", topic2)
                result2 = client.subscribe(topic2, qos=1)
                logger.info("Subscribe result: %s", result2)
                
                # Subscribe to wildcard to see all topics
                topic3 = "#"
                logger.info("Also subscribing to wildcard: %s", topic3)
                result3 = client.subscribe(topic3, qos=1)
                logger.info("Subscribe result: %s", result3)
            else:
                # Subscribe to all devices for this user
                topic = f"/app/{app_key}/+/thing/property/+"
                logger.info("Subscribing to all devices: %s", topic)
                client.subscribe(topic, qos=1)
    
    def on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        logger.info("Subscription confirmed: mid=%s, codes=%s", mid, reason_code_list)
    
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        logger.warning("Disconnected from EcoFlow MQTT broker, reason_code=%s", reason_code)
    
    def on_message(self, client, userdata, msg):
        payload_raw = msg.payload.decode("utf-8", errors="replace")
        logger.info("Received MQTT message on topic: %s (payload size: %d bytes)", msg.topic, len(payload_raw))
        logger.debug("Payload preview: %s", payload_raw[:200])
        
        try:
            data = json.loads(payload_raw)
        except json.JSONDecodeError:
            logger.warning("Failed to decode JSON payload: %s", payload_raw[:100])
            return
        
        if not isinstance(data, dict):
            logger.warning("Expected JSON object, got: %r", type(data))
            return
        
        # Parse topic to extract device serial number if not configured
        device_sn = self.device_sn
        if not device_sn:
            # Try to extract from topic: /app/{user_id}/{device_sn}/...
            parts = msg.topic.split("/")
            logger.debug("Topic parts: %s", parts)
            if len(parts) > 3:
                device_sn = parts[3]
                logger.info("Extracted device SN from topic: %s", device_sn)
        
        if self.conn is None:
            logger.error("No DB connection available; dropping message")
            return
        
        try:
            parsed_data = parse_ecoflow_payload(data, device_sn)
            logger.info("Parsed data fields: %s", {k: v for k, v in parsed_data.items() if k != 'raw_data'})
            insert_ecoflow_measurement(self.conn, parsed_data)
            logger.info(
                "Inserted EcoFlow measurement for device=%s, soc=%s%%",
                device_sn,
                parsed_data.get("soc_percent")
            )
        except Exception as exc:
            logger.exception("Failed to insert EcoFlow measurement: %s", exc)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def main() -> None:
    logger.info("Starting EcoFlow Collector Service")
    
    try:
        cfg = load_config()
        app = EcoFlowCollectorApp(cfg)
        app.start()
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
