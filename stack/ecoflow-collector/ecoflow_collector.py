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
    """Helper class to interact with EcoFlow Developer API (both MQTT auth and REST API)."""
    
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
    
    def _make_api_request(self, endpoint: str, method: str = "GET", body: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make an authenticated request to EcoFlow REST API.
        
        Args:
            endpoint: API endpoint path (e.g., "/iot-open/sign/device/quota")
            method: HTTP method (GET or POST)
            body: Optional request body for POST requests
            
        Returns:
            Response data dictionary
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
        
        # Build headers
        headers = {
            "accessKey": self.access_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        logger.debug("REST API request: %s %s", method, url)
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body or {}, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code != 200:
                logger.error("API request failed: HTTP %s - %s", response.status_code, response.text)
                return {"code": str(response.status_code), "message": response.text}
            
            data = response.json()
            
            if data.get("code") != "0":
                logger.warning("API returned error code: %s, message: %s", 
                             data.get("code"), data.get("message"))
            
            return data
            
        except requests.RequestException as e:
            logger.error("API request exception: %s", e)
            return {"code": "-1", "message": str(e)}
    
    def get_mqtt_credentials(self) -> Dict[str, Any]:
        """
        Request MQTT credentials from EcoFlow API.
        
        Returns dict with: url, port, username, password, protocol, clientId
        """
        data = self._make_api_request("/iot-open/sign/certification", "GET")
        
        if data.get("code") != "0":
            logger.error("Failed to get MQTT credentials: %s", data)
            raise RuntimeError(f"EcoFlow API error: {data.get('message', 'Unknown error')}")
        
        mqtt_data = data.get("data", {})
        logger.info("Successfully obtained MQTT credentials")
        logger.debug("MQTT info: host=%s port=%s", mqtt_data.get("url"), mqtt_data.get("port"))
        
        return mqtt_data
    
    def get_device_quota(self, device_sn: str) -> Optional[Dict[str, Any]]:
        """
        Get device quota (current status) via REST API.
        
        According to OpenAPI docs, this returns real-time device data including:
        - Battery SOC, voltage, current, temperature
        - Input/output power
        - Inverter status
        - MPPT (solar) status
        - And more...
        
        Args:
            device_sn: Device serial number
            
        Returns:
            Device quota data or None on error
        """
        endpoint = f"/iot-open/sign/device/quota?sn={device_sn}"
        data = self._make_api_request(endpoint, "GET")
        
        if data.get("code") == "0":
            logger.info("Successfully fetched device quota for %s", device_sn)
            return data.get("data", {})
        else:
            logger.warning("Failed to get device quota: %s", data.get("message"))
            return None
    
    def get_device_quota_all(self, device_sn: str) -> Optional[Dict[str, Any]]:
        """
        Get all device quota data via REST API.
        
        This endpoint retrieves comprehensive device status.
        
        Args:
            device_sn: Device serial number
            
        Returns:
            Complete device data or None on error
        """
        endpoint = f"/iot-open/sign/device/quota/all?sn={device_sn}"
        data = self._make_api_request(endpoint, "GET")
        
        if data.get("code") == "0":
            logger.info("Successfully fetched all device quota for %s", device_sn)
            return data.get("data", {})
        else:
            logger.warning("Failed to get all device quota: %s", data.get("message"))
            return None


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
    
    Enhanced to handle all available fields from comprehensive parsing.
    Uses INSERT ... ON CONFLICT to update existing recent measurement with new data,
    aggregating values from multiple MQTT messages into a single row.
    """
    # Define all possible fields
    all_fields = [
        'soc_percent', 'remain_time_min', 'watts_in_sum', 'watts_out_sum',
        'ac_out_watts', 'dc_out_watts', 'typec_out_watts', 'usb_out_watts', 'pv_in_watts',
        'bms_voltage_mv', 'bms_amp_ma', 'bms_temp_c', 'bms_cycles', 'bms_soh_percent',
        'inv_ac_in_volts_mv', 'inv_ac_out_volts_mv', 'inv_ac_freq_hz', 'inv_temp_c',
        'mppt_in_volts_mv', 'mppt_in_amps_ma', 'mppt_out_volts_mv', 'mppt_out_amps_ma',
        'mppt_temp_c', 'car_out_volts_mv', 'car_out_amps_ma', 'wifi_rssi'
    ]
    
    # Only insert if we have at least one meaningful value
    has_data = any([data.get(k) is not None for k in all_fields])
    
    if not has_data:
        logger.debug("Skipping insert - no meaningful data in payload")
        return
    
    with conn.cursor() as cur:
        # Check if there's a recent measurement (within last 10 seconds) to update
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
            
            for field in all_fields:
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
                SET {', '.join(update_fields)}
                WHERE id = %(id)s
                """
                cur.execute(query, update_params)
                logger.debug("Updated recent measurement id=%s with %d fields", recent_row[0], len(update_fields))
        else:
            # Prepare insert with only non-null fields
            insert_fields = ['device_sn', 'ts'] + [f for f in all_fields if data.get(f) is not None]
            if data.get('raw_data'):
                insert_fields.append('raw_data')
            
            placeholders = ['%(device_sn)s', 'NOW()'] + [f'%({f})s' for f in all_fields if data.get(f) is not None]
            if data.get('raw_data'):
                placeholders.append('%(raw_data)s')
            
            query = f"""
                INSERT INTO ecoflow_measurements (
                    {', '.join(insert_fields)}
                )
                VALUES (
                    {', '.join(placeholders)}
                )
            """
            cur.execute(query, data)
            logger.debug("Inserted new measurement with %d fields", len(insert_fields))


def parse_ecoflow_payload(raw_payload: Dict[str, Any], device_sn: str = "") -> Dict[str, Any]:
    """
    Parse EcoFlow MQTT payload into our database schema.
    
    EcoFlow sends complex nested structures with dotted field names.
    Example: {"params": {"bmsMaster.soc": 89, "bmsMaster.inputWatts": 0, ...}}
    
    Enhanced to extract more comprehensive data from raw_data.
    """
    # EcoFlow typically nests data in a "params" or "data" field
    params = raw_payload.get("params", {})
    
    # Helper to safely get numeric values with optional unit conversion
    def get_val(key, default=None, divide_by=1):
        val = params.get(key, default)
        # Filter out obviously invalid values
        if val is not None and isinstance(val, (int, float)):
            # Some fields use 65535 or similar large numbers as "not available"
            if val > 100000000:  # 100M is clearly invalid
                return None
            if divide_by > 1:
                val = val / divide_by
        return val
    
    # Helper to sum multiple USB/TypeC ports
    def sum_ports(keys, divide_by=1):
        total = 0
        for key in keys:
            val = get_val(key, 0, divide_by=divide_by)
            if val is not None:
                total += val
        return total if total > 0 else None
    
    # Extract values from dotted field names (e.g., "bmsMaster.soc")
    # Primary data sources - prefer pd (power distribution) and bmsMaster values
    
    # Calculate power values first with unit conversions
    watts_in_sum_val = (
        get_val("pd.wattsInSum", divide_by=1000) or
        get_val("inv.inputWatts", divide_by=1000) or
        get_val("mppt.inWatts", divide_by=1000) or
        get_val("bmsMaster.inputWatts", divide_by=1000) or
        get_val("wattsInSum", divide_by=1000)
    )
    
    # Individual output components
    ac_out = (
        get_val("inv.outputWatts", divide_by=1000) or
        get_val("inv.invOutWatts", divide_by=1000) or
        get_val("pd.dsgPowerAc", divide_by=1000)
    )
    dc_out = (
        get_val("mppt.carOutWatts", divide_by=1000) or
        get_val("mppt.outWatts", divide_by=1000) or
        get_val("pd.dsgPowerDc", divide_by=1000)
    )
    typec_out = sum_ports(["pd.typec1Watts", "pd.typec2Watts"], divide_by=1000)
    usb_out = sum_ports([
        "pd.usb1Watts", "pd.usb2Watts", 
        "pd.qcUsb1Watts", "pd.qcUsb2Watts"
    ], divide_by=1000)
    
    # Calculate total output from components, or use provided total
    # Note: pd.wattsOutSum often doesn't include AC output, so calculate from components
    watts_out_from_components = sum(filter(None, [ac_out, dc_out, typec_out, usb_out])) or None
    watts_out_sum_val = (
        watts_out_from_components or
        get_val("pd.wattsOutSum", divide_by=1000) or
        get_val("inv.outputWatts", divide_by=1000) or
        get_val("bmsMaster.outputWatts", divide_by=1000) or
        get_val("wattsOutSum", divide_by=1000)
    )
    
    parsed = {
        "device_sn": device_sn or raw_payload.get("sn", "unknown"),
        "soc_percent": (
            get_val("pd.soc") or 
            get_val("bmsMaster.soc") or 
            get_val("ems.lcdShowSoc") or
            get_val("soc")
        ),
        "remain_time_min": (
            get_val("pd.remainTime") or
            get_val("bmsMaster.remainTime") or
            get_val("ems.chgRemainTime") or
            get_val("ems.dsgRemainTime") or
            get_val("remainTime")
        ),
        "watts_in_sum": watts_in_sum_val,
        "watts_out_sum": watts_out_sum_val,
        "ac_out_watts": ac_out,
        "dc_out_watts": dc_out,
        "typec_out_watts": typec_out,
        "usb_out_watts": usb_out,
        "pv_in_watts": (
            get_val("mppt.inWatts", divide_by=1000) or
            get_val("mppt.pv1InputWatts", divide_by=1000) or
            get_val("pd.chgSunPower", divide_by=1000) or
            get_val("pvInWatts", divide_by=1000) or 
            (params.get("pv", {}).get("inputWatts", 0) / 1000 if params.get("pv", {}).get("inputWatts") else None)
        ),
        # BMS (Battery Management System) data
        "bms_voltage_mv": get_val("bmsMaster.vol"),
        "bms_amp_ma": get_val("bmsMaster.amp"),
        "bms_temp_c": get_val("bmsMaster.temp"),
        "bms_cycles": get_val("bmsMaster.cycles"),
        "bms_soh_percent": get_val("bmsMaster.soh"),
        # Inverter data
        "inv_ac_in_volts_mv": get_val("inv.acInVol"),
        "inv_ac_out_volts_mv": get_val("inv.invOutVol") or get_val("inv.acOutVol"),
        "inv_ac_freq_hz": get_val("inv.acInFreq") or get_val("inv.invOutFreq"),
        "inv_temp_c": get_val("inv.outTemp") or get_val("inv.dcInTemp"),
        # MPPT (Solar controller) data
        "mppt_in_volts_mv": get_val("mppt.inVol"),
        "mppt_in_amps_ma": get_val("mppt.inAmp"),
        "mppt_out_volts_mv": get_val("mppt.outVol"),
        "mppt_out_amps_ma": get_val("mppt.outAmp"),
        "mppt_temp_c": get_val("mppt.mpptTemp"),
        # Car/DC output
        "car_out_volts_mv": get_val("mppt.carOutVol"),
        "car_out_amps_ma": get_val("mppt.carOutAmp"),
        # WiFi signal strength
        "wifi_rssi": get_val("pd.wifiRssi"),
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
        self.api: Optional[EcoFlowAPI] = None
        self.rest_api_enabled = os.getenv("ECOFLOW_REST_API_ENABLED", "true").lower() == "true"
        self.rest_api_interval = int(os.getenv("ECOFLOW_REST_API_INTERVAL", "60"))  # seconds
    
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
        self.api = EcoFlowAPI(
            self.cfg["ecoflow_access_key"],
            self.cfg["ecoflow_secret_key"],
            api_url
        )
        self.mqtt_credentials = self.api.get_mqtt_credentials()
        
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
            
            # Start periodic data request thread
            import threading
            request_thread = threading.Thread(target=self._periodic_data_request, daemon=True)
            request_thread.start()
            logger.info("Started periodic data request thread")
            
            # Make initial data request
            self._request_device_data()
            
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

    def _request_device_data(self):
        """Publish command to request device data from EcoFlow device."""
        if not self.client or not self.device_sn:
            return
        
        # Request all device data - according to OpenAPI docs  
        # Publish to /app/{user_id}/{device_sn}/thing/property/get
        user_id = self.mqtt_credentials.get('certificateAccount')
        topic = f'/app/{user_id}/{self.device_sn}/thing/property/get'
        
        # Empty payload requests all properties
        payload = {}
        
        try:
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("Requested device data on topic: %s", topic)
            else:
                logger.warning("Failed to publish data request: %s", result.rc)
        except Exception as e:
            logger.warning("Error requesting device data: %s", e)
    
    def _periodic_data_request(self):
        """Background thread to periodically request device data via MQTT and REST API."""
        import time
        import threading
        
        while True:
            try:
                # Request via MQTT
                self._request_device_data()
                
                # Also fetch via REST API as fallback/supplement (if enabled)
                if self.rest_api_enabled:
                    threading.Thread(target=self._fetch_rest_data, daemon=True).start()
                
            except Exception as e:
                logger.error("Data request error: %s", e)
            time.sleep(self.rest_api_interval)  # Use configured interval
    
    def _fetch_rest_data(self):
        """Fetch device data via REST API and store to database."""
        if not self.device_sn:
            logger.debug("No device SN configured, skipping REST API fetch")
            return
        
        try:
            # Fetch device quota (all data)
            logger.info("Fetching device quota via REST API for device: %s", self.device_sn)
            quota_data = self.api.get_device_quota_all(self.device_sn)
            
            if not quota_data:
                logger.warning("No quota data received from REST API")
                return
            
            logger.debug("REST API quota data: %s", json.dumps(quota_data, indent=2)[:500])
            
            # Ensure database connection
            self._ensure_db_connection()
            if self.conn is None:
                logger.error("No DB connection available for REST data")
                return
            
            # Parse and store the data
            parsed_data = parse_ecoflow_payload(quota_data, self.device_sn)
            parsed_data['source'] = 'rest_api'  # Mark source
            
            insert_ecoflow_measurement(self.conn, parsed_data)
            logger.info(
                "Inserted EcoFlow measurement from REST API: device=%s, soc=%s%%",
                self.device_sn,
                parsed_data.get("soc_percent")
            )
            
        except Exception as e:
            logger.error("Failed to fetch/store REST API data: %s", e, exc_info=True)


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
