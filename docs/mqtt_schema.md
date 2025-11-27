# MQTT Schema for RuuviTag-style Telemetry

## Topic

**Topic name:** `paku/ruuvi/van_inside`

This topic is used for publishing telemetry data from a RuuviTag sensor inside the van environment.

---

## Payload Schema

The payload is a JSON object containing RuuviTag-style sensor measurements. All fields are required unless specified otherwise.

### Field Definitions

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `sensor_id` | string | - | Logical identifier for the sensor (e.g., "van_inside") |
| `temperature_c` | float | °C | Temperature in degrees Celsius |
| `humidity_percent` | float | % | Relative humidity as a percentage (0-100) |
| `pressure_hpa` | float | hPa | Atmospheric pressure in hectopascals |
| `acceleration_x_mg` | integer | mg | Acceleration on X-axis in milligravity (1 mg = 0.001 g) |
| `acceleration_y_mg` | integer | mg | Acceleration on Y-axis in milligravity |
| `acceleration_z_mg` | integer | mg | Acceleration on Z-axis in milligravity |
| `acceleration_total_mg` | integer | mg | Total acceleration magnitude in milligravity |
| `tx_power_dbm` | integer | dBm | Radio transmission power in decibels-milliwatt |
| `movement_counter` | integer | - | Cumulative count of detected movements |
| `measurement_sequence` | integer | - | Sequential measurement number (increments with each reading) |
| `battery_mv` | integer | mV | Battery voltage in millivolts |
| `mac` | string | - | MAC address of the sensor (format: AA:BB:CC:DD:EE:FF) |
| `timestamp` | string | - | Timestamp in ISO 8601 format (e.g., "2025-11-25T09:30:00Z") |

---

## Example Payload

Below is a complete example of a valid JSON payload:

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

---

## Notes

- The schema is designed to be compatible with RuuviTag sensor data format.
- All numeric values should use appropriate precision for their respective sensors.
- The `timestamp` field should be in UTC timezone (indicated by "Z" suffix).
- The `sensor_id` field provides logical identification independent of the MAC address.
- The `acceleration_total_mg` typically represents the vector magnitude: √(x² + y² + z²).

---

## Storage

The collector service persists the following fields to the `measurements` table in Postgres:
- `sensor_id`
- `temperature_c`
- `humidity_percent`
- `pressure_hpa`
- `battery_mv`
- `ts` (mapped from `timestamp`)

For complete database schema details, see [database_schema.md](database_schema.md).
