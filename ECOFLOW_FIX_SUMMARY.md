# EcoFlow Collector Fix Summary

**Date**: December 2024  
**Issue**: HTTP 405 "Method Not Allowed" when connecting to EcoFlow API  
**Status**: ✅ Fixed

## Problem

The EcoFlow collector was failing with the following error:

```
[ERROR] Failed to get MQTT credentials: HTTP 405 - {"code":"405","message":"Method Not Allowed"}
RuntimeError: EcoFlow API error: 405
```

## Root Cause

The EcoFlow API changed its authentication method from:
- **Old**: POST request with headers (`accessKey` and `secretKey` in headers)
- **New**: GET request with HMAC-SHA256 signed query parameters

The collector was still using the old POST method, which EcoFlow no longer accepts.

## Solution

Updated the EcoFlow API integration to use the new authentication method:

### 1. Changed HTTP Method
- From: `POST` request with authentication headers
- To: `GET` request with signed query parameters

### 2. Added HMAC-SHA256 Signature
The new API requires a signature generated from:
- `accessKey`: Your API access key
- `nonce`: Random 16-character string
- `timestamp`: Current time in milliseconds
- `sign`: HMAC-SHA256 hash of the sorted parameters

### 3. Implementation Details

**Signature Generation Process**:
```python
# 1. Create parameters (without signature)
params = {
    "accessKey": access_key,
    "nonce": random_16_chars,
    "timestamp": current_time_ms
}

# 2. Sort alphabetically and concatenate
param_str = "accessKey=xxx&nonce=abc&timestamp=123"

# 3. Generate HMAC-SHA256 signature
sign = hmac.new(secret_key, param_str, hashlib.sha256).hexdigest()

# 4. Add signature to parameters
params["sign"] = sign

# 5. Make GET request with query parameters
response = requests.get(url, params=params)
```

## Files Changed

1. **`stack/ecoflow-collector/ecoflow_collector.py`**
   - Added imports: `hashlib`, `hmac`, `random`, `string`
   - Added `_generate_sign()` method to generate HMAC-SHA256 signatures
   - Changed `get_mqtt_credentials()` from POST to GET with signed parameters

2. **`stack/ecoflow-collector/test_config.py`**
   - Added imports: `hashlib`, `hmac`, `random`, `string`, `time`
   - Updated `test_api_connection()` to use new authentication method

3. **`docs/ecoflow_technical_notes.md`**
   - Updated API documentation to reflect new GET method
   - Added signature generation examples
   - Added note about API change timeline

4. **`stack/ecoflow-collector/README.md`**
   - Added warning about recent API changes
   - Clarified Docker Compose profile requirement

5. **`ECOFLOW_QUICKSTART.md`**
   - Emphasized the `--profile ecoflow` requirement
   - Added note that service won't start without the profile flag

## Additional Issue: Auto-Start

**Question**: "It requires specific commands to start up - not automatically started when main branch updates"

**Answer**: This is by design, not a bug. The EcoFlow collector uses a Docker Compose **profile** to make it optional:

```yaml
ecoflow-collector:
  # ... service config ...
  profiles:
    - ecoflow
```

### Why Use Profiles?

1. **Optional Feature**: Not all users have EcoFlow devices
2. **Requires Credentials**: Needs API keys from EcoFlow Developer Portal
3. **Security**: Prevents accidental exposure of credentials
4. **Resource Efficiency**: Only runs when explicitly needed

### How to Enable Auto-Start

To start the EcoFlow collector, you must use the profile flag:

```bash
# Start with EcoFlow collector
docker compose --profile ecoflow -f compose/stack.yaml up -d

# Or add to a startup script
echo "docker compose --profile ecoflow -f compose/stack.yaml up -d" > start.sh
```

If you want it to always start, you can:
1. Remove the `profiles:` section from `compose/stack.yaml` (not recommended)
2. Set `COMPOSE_PROFILES=ecoflow` in your `.env` file (better approach)
3. Create an alias or startup script that includes the flag (recommended)

## Testing

To verify the fix works:

```bash
# 1. Set your credentials in compose/.env
ECOFLOW_ACCESS_KEY=your_key
ECOFLOW_SECRET_KEY=your_secret

# 2. Test configuration
cd stack/ecoflow-collector
python test_config.py

# 3. Start the collector
docker compose --profile ecoflow -f compose/stack.yaml up -d ecoflow-collector

# 4. Check logs
docker logs -f paku_ecoflow_collector
```

Expected output:
```
[INFO] Starting EcoFlow Collector Service
[INFO] Requesting MQTT credentials from EcoFlow API...
[INFO] Successfully obtained MQTT credentials
[INFO] Connected to EcoFlow MQTT broker
```

## References

- [EcoFlow Developer Portal](https://developer.ecoflow.com/)
- [HMAC-SHA256 Documentation](https://en.wikipedia.org/wiki/HMAC)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)

## Migration Note

If you were using the old version and seeing 405 errors:
1. Pull the latest code with this fix
2. Rebuild the Docker image: `docker compose build ecoflow-collector`
3. Restart with the profile flag: `docker compose --profile ecoflow -f compose/stack.yaml up -d`

No configuration changes needed - your existing credentials will work with the new authentication method.
