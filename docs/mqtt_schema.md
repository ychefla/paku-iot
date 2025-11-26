Topic: `paku/ruuvi/van_inside`

Example JSON payload (full RuuviTag-style data):

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

## Storage

The collector service persists the following fields to the `measurements` table in Postgres:
- `sensor_id`
- `temperature_c`
- `humidity_percent`
- `pressure_hpa`
- `battery_mv`
- `ts` (mapped from `timestamp`)

For complete database schema details, see [database_schema.md](database_schema.md).