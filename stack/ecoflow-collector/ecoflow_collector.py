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
        # Default to US API endpoint - use https://api-e.ecoflow.com for EU
        "ecoflow_api_url": os.getenv("ECOFLOW_API_URL", "https://api.ecoflow.com"),
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
    
    Uses INSERT ... ON CONFLICT to update existing recent measurement with new data,
    aggregating values from multiple MQTT messages into a single row.
    
    Expected fields from EcoFlow MQTT payload (Delta Pro):
    - soc (state of charge %)
    - remainTime (minutes)
    - wattsInSum (total input watts)
    - wattsOutSum (total output watts)
    - Various port-specific power readings
    """
    # Only insert if we have at least one meaningful value
    has_data = any([
        data.get(k) is not None 
        for k in ['soc_percent', 'remain_time_min', 'watts_in_sum', 'watts_out_sum',
                  'ac_out_watts', 'dc_out_watts', 'typec_out_watts', 'usb_out_watts', 'pv_in_watts']
    ])
    
    if not has_data:
        logger.debug("Skipping insert - no meaningful data in payload")
        return
    
    with conn.cursor() as cur:
        # First, check if there's a recent measurement (within last 10 seconds) to update
        cur.execute(
            """
            SELECT id FROM ecoflow_measurements
            WHERE device_sn = %(device_sn)s
              AND ts >= NOW() - INTERVAL '10 seconds'
            ORDER BY ts DESC
            LIMIT 1
            """,
            {"device_sn": data["device_sn"]}
        )
        recent_row = cur.fetchone()
        
        if recent_row:
            # Update existing row with new non-null values
            update_fields = []
            update_params = {"id": recent_row[0]}
            
            for field in ['soc_percent', 'remain_time_min', 'watts_in_sum', 'watts_out_sum',
                          'ac_out_watts', 'dc_out_watts', 'typec_out_watts', 'usb_out_watts', 'pv_in_watts']:
                if data.get(field) is not None:
                    update_fields.append(f"{field} = COALESCE(%({field})s, {field})")
                    update_params[field] = data[field]
            
            # Always append to raw_data
            if data.get('raw_data'):
                update_fields.append("raw_data = raw_data || %(raw_data)s::jsonb")
                update_params['raw_data'] = data['raw_data']
            
            if update_fields:
                query = f"""
                UPDATE ecoflow_measurements
                SET {', '.join(update_fields)}, ts = NOW()
                WHERE id = %(id)s
                """
                cur.execute(query, update_params)
                logger.debug("Updated recent measurement id=%s", recent_row[0])
        else:
            # Insert new row
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
            logger.debug("Inserted new measurement")


def parse_ecoflow_payload(raw_payload: Dict[str, Any], device_sn: str = "") -> Dict[str, Any]:
    """
    Parse EcoFlow MQTT payload into our database schema.
    
    EcoFlow sends complex nested structures with dotted field names.
    Example: {"params": {"bmsMaster.soc": 89, "bmsMaster.inputWatts": 0, ...}}
    """
    # EcoFlow typically nests data in a "params" or "data" field
    params = raw_payload.get("params", {})
    
    # Helper to sum multiple USB/TypeC ports
    def sum_ports(keys):
        total = 0
        for key in keys:
            val = params.get(key)
            if val is not None:
                total += val
        return total if total > 0 else None
    
    # Extract values from dotted field names (e.g., "bmsMaster.soc")
    # and also support legacy flat structures
    parsed = {
        "device_sn": device_sn or raw_payload.get("sn", "unknown"),
        "soc_percent": (
            params.get("bmsMaster.soc") or 
            params.get("pd.soc") or
            params.get("soc") or 
            params.get("bmsMaster", {}).get("soc")
        ),
        "remain_time_min": (
            params.get("pd.remainTime") or
            params.get("bmsMaster.remainTime") or
            params.get("ems.chgRemainTime") or
            params.get("remainTime")
        ),
        "watts_in_sum": (
            params.get("pd.wattsInSum") or
            params.get("pd.chgPowerAc") or
            params.get("bmsMaster.inputWatts") or
            params.get("inv.inputWatts") or
            params.get("wattsInSum") or 
            params.get("inv", {}).get("inputWatts")
        ),
        "watts_out_sum": (
            params.get("pd.wattsOutSum") or
            params.get("pd.dsgPowerAc") or
            params.get("bmsMaster.outputWatts") or
            params.get("inv.outputWatts") or
            params.get("wattsOutSum") or 
            params.get("inv", {}).get("outputWatts")
        ),
        "ac_out_watts": (
            params.get("inv.outputWatts") or
            params.get("inv.acOutWatts") or
            params.get("inv.outWatts") or
            params.get("invOutWatts")
        ),
        "dc_out_watts": (
            params.get("mppt.carOutWatts") or
            params.get("mppt.outWatts") or
            params.get("pd.dcOutWatts") or
            params.get("dcOutWatts")
        ),
        "typec_out_watts": sum_ports(["pd.typec1Watts", "pd.typec2Watts"]) or params.get("typecOutWatts"),
        "usb_out_watts": sum_ports([
            "pd.usb1Watts", "pd.usb2Watts", 
            "pd.qcUsb1Watts", "pd.qcUsb2Watts"
        ]) or params.get("usbOutWatts"),
        "pv_in_watts": (
            params.get("mppt.inWatts") or
            params.get("mppt.pv1InputWatts") or
            params.get("pvInWatts") or 
            params.get("pv", {}).get("inputWatts")
        ),
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
    
    def _ensure_db_connection(self):
        """Ensure database connection is alive, reconnect if needed."""
        try:
            if self.conn is None or self.conn.closed:
                logger.warning("Database connection is closed, reconnecting...")
                self.conn = connect_to_database(self.cfg)
                return
            
            # Test the connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception as exc:
            logger.warning("Database connection test failed: %s, reconnecting...", exc)
            try:
                if self.conn:
                    self.conn.close()
            except:
                pass
            self.conn = connect_to_database(self.cfg)
    
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
            logger.info("MQTT credentials info: certificateAccount=%s", self.mqtt_credentials.get("certificateAccount", "N/A"))
            
            # Subscribe to device topic(s)
            # EcoFlow topic format varies by region and API version
            # Based on the documentation, try multiple patterns to catch messages
            
            # Extract user ID from certificateAccount (format is often "userId/randomString")
            cert_account = self.mqtt_credentials.get("certificateAccount", "")
            if "/" in cert_account:
                user_id = cert_account.split("/")[0]
                logger.info("Extracted user_id from certificateAccount: %s", user_id)
            else:
                user_id = cert_account
                logger.info("Using full certificateAccount as user_id: %s", user_id)
            
            # Subscribe to multiple topic patterns to ensure we catch messages
            topics = []
            
            if self.device_sn:
                # Standard OpenAPI topics for device properties and quotas
                topics.extend([
                    f"/app/{user_id}/{self.device_sn}/#",  # All device messages
                    f"/app/device/property/{self.device_sn}",  # Simplified property format
                    f"/open/{user_id}/{self.device_sn}/quota",  # Quota updates
                ])
            
            # Also subscribe to global wildcard to debug what topics are actually used
            topics.append("#")  # ALL topics - for debugging
            
            logger.info("Subscribing to %d topic patterns", len(topics))
            for topic in topics:
                result = client.subscribe(topic, qos=0)
                logger.info("Subscribed to topic: %s (result: %s)", topic, result)
    
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
        
        # Ensure database connection is alive
        try:
            self._ensure_db_connection()
        except Exception as exc:
            logger.error("Failed to ensure DB connection: %s; dropping message", exc)
            return
        
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
