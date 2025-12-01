# Ruuvi Emulator

Simple MQTT publisher that simulates RuuviTag sensor data for testing purposes.

## Overview

This container publishes JSON-formatted sensor data to an MQTT broker, simulating a real RuuviTag environmental sensor. It follows the schema documented in `docs/mqtt_schema.md`.

## Configuration

### Environment Variables

- `MQTT_HOST` - MQTT broker hostname (default: `mosquitto`)
- `MQTT_PORT` - MQTT broker port (default: `1883`)

### Topic

Messages are published to: `paku/ruuvi/van_inside`

## Behavior

- Publishes a new message every 5-10 seconds (randomized)
- Generates realistic sensor values:
  - Temperature: 18-25°C
  - Humidity: 35-55%
  - Pressure: 990-1020 hPa
  - Battery: 2800-3000 mV
  - Random acceleration and movement data
- Logs each published message to stdout for inspection
- Includes retry logic with 10 attempts to connect to MQTT broker
- Uses QoS 0 for message delivery

## Message Format

```json
{
  "sensor_id": "van_inside",
  "temperature_c": 21.5,
  "humidity_percent": 45.2,
  "pressure_hpa": 1003.2,
  "acceleration_x_mg": -23,
  "acceleration_y_mg": 5,
  "acceleration_z_mg": 1015,
  "acceleration_total_mg": 1016,
  "tx_power_dbm": 4,
  "movement_counter": 120,
  "measurement_sequence": 34123,
  "battery_mv": 2870,
  "mac": "AA:BB:CC:DD:EE:FF",
  "timestamp": "2025-11-25T09:30:00Z"
}
```

## Usage

### With Docker Compose

```bash
docker compose -f compose/stack.yaml up ruuvi-emulator
```

### View Logs

```bash
docker logs paku_ruuvi_emulator
```

### Subscribe to Messages

From the host or another container:

```bash
mosquitto_sub -h localhost -t "paku/ruuvi/#"
```

## Development

### Local Testing

Test the data generation logic:

```bash
cd stack/ruuvi-emulator
python3 emulator.py
```

Note: Requires `paho-mqtt` to be installed (`pip install paho-mqtt==2.1.0`)
