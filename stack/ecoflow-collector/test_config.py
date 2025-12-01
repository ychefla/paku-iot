#!/usr/bin/env python3
"""
Simple test script to verify EcoFlow collector configuration.

Tests:
1. Environment variables are set
2. Can connect to EcoFlow API
3. Can obtain MQTT credentials
4. Can parse sample EcoFlow payload

Usage:
    python test_config.py
"""

import hashlib
import hmac
import json
import os
import random
import string
import sys
import time

try:
    import requests
except ImportError:
    print("Error: requests library not found. Run: pip install requests")
    sys.exit(1)


def test_env_vars():
    """Check if required environment variables are set."""
    print("1. Checking environment variables...")
    
    required = ["ECOFLOW_ACCESS_KEY", "ECOFLOW_SECRET_KEY"]
    missing = []
    
    for var in required:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"   ❌ {var}: NOT SET")
        else:
            # Show first/last 4 chars for security
            masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            print(f"   ✓ {var}: {masked}")
    
    device_sn = os.getenv("ECOFLOW_DEVICE_SN")
    if device_sn:
        print(f"   ✓ ECOFLOW_DEVICE_SN: {device_sn}")
    else:
        print(f"   ⚠ ECOFLOW_DEVICE_SN: Not set (will collect from all devices)")
    
    if missing:
        print(f"\n❌ Missing required variables: {', '.join(missing)}")
        print("Set them in your shell or .env file:")
        print("  export ECOFLOW_ACCESS_KEY='your_key'")
        print("  export ECOFLOW_SECRET_KEY='your_secret'")
        return False
    
    print("✓ All required environment variables are set\n")
    return True


def test_api_connection():
    """Test connection to EcoFlow API and obtain MQTT credentials."""
    print("2. Testing EcoFlow API connection...")
    
    access_key = os.getenv("ECOFLOW_ACCESS_KEY")
    secret_key = os.getenv("ECOFLOW_SECRET_KEY")
    
    url = "https://api.ecoflow.com/iot-open/sign/certification"
    
    # Generate request parameters with signature
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    timestamp = str(int(time.time() * 1000))  # milliseconds
    
    # Build parameters for signature
    params = {
        "accessKey": access_key,
        "nonce": nonce,
        "timestamp": timestamp
    }
    
    # Generate HMAC-SHA256 signature
    sorted_params = sorted(params.items())
    param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
    sign = hmac.new(
        secret_key.encode('utf-8'),
        param_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    params["sign"] = sign
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
            return False
        
        data = response.json()
        
        if data.get("code") != "0":
            print(f"   ❌ API Error: {data.get('message', 'Unknown error')}")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return False
        
        mqtt_data = data.get("data", {})
        print(f"   ✓ Successfully obtained MQTT credentials")
        print(f"   MQTT Host: {mqtt_data.get('url')}")
        print(f"   MQTT Port: {mqtt_data.get('port')}")
        print(f"   Protocol: {mqtt_data.get('protocol')}")
        print(f"   Client ID: {mqtt_data.get('clientId')}")
        print("✓ API connection successful\n")
        return True
        
    except requests.exceptions.Timeout:
        print("   ❌ Connection timeout - check your internet connection")
        return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def test_payload_parsing():
    """Test parsing of sample EcoFlow payload."""
    print("3. Testing payload parsing...")
    
    # Sample EcoFlow Delta Pro payload structure
    sample_payload = {
        "sn": "R331ZEB4ZEA0012345",
        "params": {
            "soc": 85,
            "remainTime": 407,
            "wattsInSum": 120,
            "wattsOutSum": 300,
            "invOutWatts": 280,
            "dcOutWatts": 20,
            "typecOutWatts": 18,
            "usbOutWatts": 2,
            "pvInWatts": 100,
            "bmsMaster": {
                "soc": 85,
                "vol": 54000,
                "amp": 2200
            },
            "inv": {
                "inputWatts": 120,
                "outputWatts": 300,
                "cfgAcOutVol": 230
            }
        }
    }
    
    try:
        params = sample_payload.get("params", {})
        
        parsed = {
            "device_sn": sample_payload.get("sn", "unknown"),
            "soc_percent": params.get("soc") or params.get("bmsMaster", {}).get("soc"),
            "remain_time_min": params.get("remainTime"),
            "watts_in_sum": params.get("wattsInSum") or params.get("inv", {}).get("inputWatts"),
            "watts_out_sum": params.get("wattsOutSum") or params.get("inv", {}).get("outputWatts"),
            "ac_out_watts": params.get("invOutWatts"),
            "dc_out_watts": params.get("dcOutWatts"),
            "typec_out_watts": params.get("typecOutWatts"),
            "usb_out_watts": params.get("usbOutWatts"),
            "pv_in_watts": params.get("pvInWatts"),
        }
        
        print("   Sample payload parsed successfully:")
        print(f"   Device: {parsed['device_sn']}")
        print(f"   Battery: {parsed['soc_percent']}%")
        print(f"   Input: {parsed['watts_in_sum']}W")
        print(f"   Output: {parsed['watts_out_sum']}W")
        print(f"   Solar: {parsed['pv_in_watts']}W")
        print("✓ Payload parsing works correctly\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Parsing error: {e}")
        return False


def main():
    print("=" * 60)
    print("EcoFlow Collector Configuration Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Environment Variables", test_env_vars()))
    results.append(("API Connection", test_api_connection()))
    results.append(("Payload Parsing", test_payload_parsing()))
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All tests passed! Your EcoFlow collector is configured correctly.")
        print()
        print("Next steps:")
        print("1. Start the collector:")
        print("   docker compose --profile ecoflow -f compose/stack.yaml up ecoflow-collector")
        print()
        print("2. Check logs:")
        print("   docker logs -f paku_ecoflow_collector")
        print()
        print("3. Query data:")
        print("   docker exec -it paku_postgres psql -U paku -d paku")
        print("   SELECT * FROM ecoflow_measurements ORDER BY ts DESC LIMIT 10;")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above before running the collector.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
