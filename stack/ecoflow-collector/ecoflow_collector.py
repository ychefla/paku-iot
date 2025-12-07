"""
EcoFlow Collector Service

Primarily uses EcoFlow REST API to fetch device data.
MQTT support is minimal and can be enhanced in the future.

Environment variables (set via docker compose):

    ECOFLOW_ACCESS_KEY - EcoFlow Developer API access key
    ECOFLOW_SECRET_KEY - EcoFlow Developer API secret key
    ECOFLOW_DEVICE_SN - Device serial number

    PGHOST
    PGPORT
    PGUSER
    PGPASSWORD
    PGDATABASE
    
    REST_API_INTERVAL - Polling interval in seconds (default: 30)
"""

import hashlib
import hmac
import json
import logging
import os
import random
import string
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

import psycopg
import requests


# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
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
        "ecoflow_device_sn": get_env("ECOFLOW_DEVICE_SN"),
        # Use EU API endpoint
        "ecoflow_api_url": os.getenv("ECOFLOW_API_URL", "https://api-e.ecoflow.com"),
        "pg_host": get_env("PGHOST", "postgres"),
        "pg_port": int(os.getenv("PGPORT", "5432")),
        "pg_user": get_env("PGUSER"),
        "pg_password": get_env("PGPASSWORD"),
        "pg_database": get_env("PGDATABASE"),
        "rest_api_interval": int(os.getenv("REST_API_INTERVAL", "30")),
    }


# ---------------------------------------------------------------------
# EcoFlow API integration
# ---------------------------------------------------------------------
class EcoFlowAPI:
    """Helper class to interact with EcoFlow Developer REST API."""
    
    def __init__(self, access_key: str, secret_key: str, base_url: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip('/')
    
    def _generate_sign(self, params: Dict[str, str]) -> str:
        """Generate HMAC-SHA256 signature for EcoFlow API request."""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_api_request(self, endpoint: str, method: str = "GET", body: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an authenticated request to EcoFlow REST API."""
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        timestamp = str(int(time.time() * 1000))
        
        params = {
            "accessKey": self.access_key,
            "nonce": nonce,
            "timestamp": timestamp
        }
        
        sign = self._generate_sign(params)
        
        headers = {
            "accessKey": self.access_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body or {}, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != "0":
                logger.warning("API returned error code: %s, message: %s", data.get("code"), data.get("message"))
                return {}
            
            return data.get("data", {})
            
        except requests.exceptions.RequestException as e:
            logger.error("API request failed: %s", e)
            return {}
    
    def get_device_quota_all(self, device_sn: str) -> Dict[str, Any]:
        """Fetch all device quota data."""
        endpoint = f"/iot-open/sign/device/quota/all?sn={device_sn}"
        return self._make_api_request(endpoint, method="GET")


# ---------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------
def insert_ecoflow_measurement(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert EcoFlow measurement into the database."""
    
    # Extract key fields from the data
    timestamp = data.get('timestamp') or datetime.now()
    device_sn = data.get('device_sn', '')
    
    # Extract power values - these are the most critical
    ac_input_watts = data.get('inv', {}).get('inputWatts', 0)
    ac_output_watts = data.get('inv', {}).get('outputWatts', 0)
    solar_input_watts = data.get('mppt', {}).get('inWatts', 0)
    dc_12v_watts = data.get('pd', {}).get('carWatts', 0)
    
    # Battery info
    soc_percent = data.get('bmsMaster', {}).get('soc', 0)
    battery_voltage = data.get('bmsMaster', {}).get('vol', 0) / 1000.0 if data.get('bmsMaster', {}).get('vol') else 0
    battery_current = data.get('bmsMaster', {}).get('amp', 0) / 1000.0 if data.get('bmsMaster', {}).get('amp') else 0
    battery_temp = data.get('bmsMaster', {}).get('temp', 0) / 10.0 if data.get('bmsMaster', {}).get('temp') else 0
    
    # AC info
    ac_in_voltage = data.get('inv', {}).get('acInVol', 0) / 1000.0 if data.get('inv', {}).get('acInVol') else 0
    ac_out_voltage = data.get('inv', {}).get('acOutVol', 0) / 1000.0 if data.get('inv', {}).get('acOutVol') else 0
    inverter_temp = data.get('inv', {}).get('invOutTemp', 0) / 10.0 if data.get('inv', {}).get('invOutTemp') else 0
    
    # Time remaining (in minutes)
    remain_time_minutes = data.get('pd', {}).get('remainTime', 0)
    
    sql = """
        INSERT INTO ecoflow_measurements (
            timestamp, device_sn,
            ac_input_watts, ac_output_watts, solar_input_watts, dc_12v_watts,
            soc_percent, battery_voltage, battery_current, battery_temp,
            ac_in_voltage, ac_out_voltage, inverter_temp,
            remain_time_minutes,
            raw_data
        ) VALUES (
            %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s,
            %s
        )
    """
    
    with conn.cursor() as cur:
        cur.execute(sql, (
            timestamp, device_sn,
            ac_input_watts, ac_output_watts, solar_input_watts, dc_12v_watts,
            soc_percent, battery_voltage, battery_current, battery_temp,
            ac_in_voltage, ac_out_voltage, inverter_temp,
            remain_time_minutes,
            json.dumps(data)
        ))
        conn.commit()


# ---------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------
class EcoFlowCollectorApp:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device_sn = config["ecoflow_device_sn"]
        self.rest_api_interval = config["rest_api_interval"]
        
        # Initialize API client
        self.api = EcoFlowAPI(
            access_key=config["ecoflow_access_key"],
            secret_key=config["ecoflow_secret_key"],
            base_url=config["ecoflow_api_url"]
        )
        
        # Database connection
        self.conn: Optional[psycopg.Connection] = None
        self._init_db_connection()
    
    def _init_db_connection(self):
        """Initialize database connection."""
        try:
            self.conn = psycopg.connect(
                host=self.config["pg_host"],
                port=self.config["pg_port"],
                user=self.config["pg_user"],
                password=self.config["pg_password"],
                dbname=self.config["pg_database"],
                autocommit=False,
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error("Failed to connect to database: %s", e)
            raise
    
    def _ensure_db_connection(self):
        """Ensure database connection is alive, reconnect if needed."""
        try:
            if self.conn and not self.conn.closed:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return
        except Exception:
            logger.warning("Database connection lost, reconnecting...")
        
        self._init_db_connection()
    
    def fetch_and_store_data(self):
        """Fetch data from REST API and store to database."""
        try:
            logger.info("Fetching device data for SN: %s", self.device_sn)
            
            # Fetch all quota data
            quota_data = self.api.get_device_quota_all(self.device_sn)
            
            if not quota_data:
                logger.warning("No data received from API")
                return
            
            # Log received data structure
            logger.debug("Received data keys: %s", list(quota_data.keys()))
            
            # Add metadata
            quota_data['timestamp'] = datetime.now()
            quota_data['device_sn'] = self.device_sn
            
            # Ensure database connection
            self._ensure_db_connection()
            
            # Store to database
            insert_ecoflow_measurement(self.conn, quota_data)
            
            # Log key metrics
            soc = quota_data.get('bmsMaster', {}).get('soc', 0)
            ac_in = quota_data.get('inv', {}).get('inputWatts', 0)
            ac_out = quota_data.get('inv', {}).get('outputWatts', 0)
            solar = quota_data.get('mppt', {}).get('inWatts', 0)
            dc_12v = quota_data.get('pd', {}).get('carWatts', 0)
            
            logger.info(
                "Stored measurement: SOC=%d%%, AC_IN=%dW, AC_OUT=%dW, SOLAR=%dW, 12V=%dW",
                soc, ac_in, ac_out, solar, dc_12v
            )
            
        except Exception as e:
            logger.error("Failed to fetch/store data: %s", e, exc_info=True)
    
    def run(self):
        """Main run loop."""
        logger.info("Starting EcoFlow collector (REST API mode)")
        logger.info("Polling interval: %d seconds", self.rest_api_interval)
        
        while True:
            try:
                self.fetch_and_store_data()
            except Exception as e:
                logger.error("Error in main loop: %s", e)
            
            time.sleep(self.rest_api_interval)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def main() -> None:
    logger.info("Starting EcoFlow Collector Service")
    
    try:
        cfg = load_config()
        app = EcoFlowCollectorApp(cfg)
        app.run()
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
