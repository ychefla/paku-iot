"""
EcoFlow Collector Service - REST API Only

Fetches data from EcoFlow REST API and stores to PostgreSQL.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("paku-ecoflow-collector")


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
        "ecoflow_api_url": os.getenv("ECOFLOW_API_URL") or "https://api-e.ecoflow.com",
        "pg_host": get_env("PGHOST", "postgres"),
        "pg_port": int(os.getenv("PGPORT", "5432")),
        "pg_user": get_env("PGUSER"),
        "pg_password": get_env("PGPASSWORD"),
        "pg_database": get_env("PGDATABASE"),
        "rest_api_interval": int(os.getenv("REST_API_INTERVAL", "30")),
    }


class EcoFlowAPI:
    def __init__(self, access_key: str, secret_key: str, base_url: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip('/')
    
    def _generate_sign(self, params: Dict[str, str]) -> str:
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_api_request(self, endpoint: str, method: str = "GET", body: Optional[Dict] = None) -> Dict[str, Any]:
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
        endpoint = f"/iot-open/sign/device/quota/all?sn={device_sn}"
        return self._make_api_request(endpoint, method="GET")


def insert_ecoflow_measurement(conn: psycopg.Connection, device_sn: str, data: Dict[str, Any]) -> None:
    """
    Insert EcoFlow measurement into database.
    
    EcoFlow API returns flat field names with dots. Key fields:
    - pd.wattsInSum: Total input power
    - pd.wattsOutSum: Total output power
    - inv.inputWatts: AC input
    - inv.outputWatts: AC output
    - mppt.inWatts: Solar input
    - mppt.outWatts: MPPT output (to battery)
    - pd.carWatts: 12V car output
    - bmsMaster.soc: Battery SOC %
    - pd.remainTime: Remaining time in minutes
    """
    
    # Battery info
    soc = data.get('bmsMaster.soc', 0)
    remain_time = data.get('pd.remainTime', 0)  # in minutes
    
    # Use EcoFlow's summary fields first, fall back to individual components
    watts_in_sum = data.get('pd.wattsInSum', 0)
    watts_out_sum = data.get('pd.wattsOutSum', 0)
    
    # Individual components
    ac_in_watts = data.get('inv.inputWatts', 0)
    ac_out_watts = data.get('inv.outputWatts', 0)
    pv_in_watts = data.get('mppt.inWatts', 0)
    mppt_out_watts = data.get('mppt.outWatts', 0)
    car_watts = data.get('pd.carWatts', 0)
    
    # USB/TypeC outputs
    usb1 = data.get('pd.usb1Watts', 0)
    usb2 = data.get('pd.usb2Watts', 0)
    qcusb1 = data.get('pd.qcUsb1Watts', 0)
    qcusb2 = data.get('pd.qcUsb2Watts', 0)
    typec1 = data.get('pd.typec1Watts', 0)
    typec2 = data.get('pd.typec2Watts', 0)
    
    # Calculate component sums
    dc_out_watts = car_watts + usb1 + usb2 + qcusb1 + qcusb2
    typec_out_watts = typec1 + typec2
    usb_out_watts = usb1 + usb2 + qcusb1 + qcusb2
    
    # Temperature & power/voltage/BMS – extracted to dedicated columns so
    # Grafana can query via index rather than scanning raw_data JSONB
    inv_temp = data.get('inv.outTemp')
    mppt_temp = data.get('mppt.mpptTemp')
    bms_temp = data.get('bmsMaster.temp')
    bms_max_cell_temp = data.get('bmsMaster.maxCellTemp')
    bms_min_cell_temp = data.get('bmsMaster.minCellTemp')

    # Power / voltage / BMS fields
    inv_input_watts = data.get('inv.inputWatts')
    inv_ac_in_vol   = data.get('inv.acInVol')
    inv_out_vol     = data.get('inv.invOutVol')
    inv_ac_in_amp   = data.get('inv.acInAmp')
    inv_out_amp     = data.get('inv.invOutAmp')
    bms_amp         = data.get('bmsMaster.amp')
    bms_vol         = data.get('bmsMaster.vol')
    bms_min_cell_vol = data.get('bmsMaster.minCellVol')
    bms_max_cell_vol = data.get('bmsMaster.maxCellVol')
    bms_remain_cap  = data.get('bmsMaster.remainCap')
    bms_full_cap    = data.get('bmsMaster.fullCap')
    bms_cycles      = data.get('bmsMaster.cycles')

    sql = """
        INSERT INTO ecoflow_measurements (
            device_sn, ts,
            soc_percent, remain_time_min,
            watts_in_sum, watts_out_sum,
            ac_out_watts, dc_out_watts, typec_out_watts, usb_out_watts,
            pv_in_watts, car_watts,
            usb1_watts, usb2_watts, qcusb1_watts, qcusb2_watts,
            typec1_watts, typec2_watts,
            inv_out_temp, bms_temp, bms_max_cell_temp, bms_min_cell_temp, mppt_temp,
            inv_input_watts, inv_ac_in_vol, inv_out_vol, inv_ac_in_amp, inv_out_amp,
            bms_amp, bms_vol, bms_min_cell_vol, bms_max_cell_vol,
            bms_remain_cap, bms_full_cap, bms_cycles,
            raw_data
        ) VALUES (
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s
        )
    """

    with conn.cursor() as cur:
        cur.execute(sql, (
            device_sn, datetime.now(),
            soc, remain_time,
            watts_in_sum, watts_out_sum,
            ac_out_watts, dc_out_watts, typec_out_watts, usb_out_watts,
            pv_in_watts, car_watts,
            usb1, usb2, qcusb1, qcusb2,
            typec1, typec2,
            inv_temp, bms_temp, bms_max_cell_temp, bms_min_cell_temp, mppt_temp,
            inv_input_watts, inv_ac_in_vol, inv_out_vol, inv_ac_in_amp, inv_out_amp,
            bms_amp, bms_vol, bms_min_cell_vol, bms_max_cell_vol,
            bms_remain_cap, bms_full_cap, bms_cycles,
            json.dumps(data)
        ))
        conn.commit()


class EcoFlowCollectorApp:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device_sn = config["ecoflow_device_sn"]
        self.rest_api_interval = config["rest_api_interval"]
        
        self.api = EcoFlowAPI(
            access_key=config["ecoflow_access_key"],
            secret_key=config["ecoflow_secret_key"],
            base_url=config["ecoflow_api_url"]
        )
        
        self.conn: Optional[psycopg.Connection] = None
        self._init_db_connection()
    
    def _init_db_connection(self):
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
        try:
            if self.conn and not self.conn.closed:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return
        except Exception:
            logger.warning("Database connection lost, reconnecting...")
        
        self._init_db_connection()
    
    def fetch_and_store_data(self):
        try:
            logger.info("Fetching device data for SN: %s", self.device_sn)
            
            quota_data = self.api.get_device_quota_all(self.device_sn)
            
            if not quota_data:
                logger.warning("No data received from API")
                return
            
            self._ensure_db_connection()
            
            insert_ecoflow_measurement(self.conn, self.device_sn, quota_data)
            
            # Log key metrics using summary fields
            soc = quota_data.get('bmsMaster.soc', 0)
            watts_in = quota_data.get('pd.wattsInSum', 0)
            watts_out = quota_data.get('pd.wattsOutSum', 0)
            solar = quota_data.get('mppt.inWatts', 0)
            temp = quota_data.get('bmsMaster.temp', 0)
            
            logger.info(
                "Stored: SOC=%d%%, IN=%dW, OUT=%dW, SOLAR=%dW, TEMP=%d°C",
                soc, watts_in, watts_out, solar, temp
            )
            
        except Exception as e:
            logger.error("Failed to fetch/store data: %s", e, exc_info=True)
    
    def run(self):
        logger.info("Starting EcoFlow collector (REST API mode)")
        logger.info("Polling interval: %d seconds", self.rest_api_interval)
        
        while True:
            try:
                self.fetch_and_store_data()
            except Exception as e:
                logger.error("Error in main loop: %s", e)
            
            time.sleep(self.rest_api_interval)


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
