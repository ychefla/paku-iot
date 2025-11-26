# Testing the Collector Service

## Manual Testing with the Full Stack

Once the stack is running with `docker compose -f compose/stack.yaml up --build`, you can test the collector by publishing MQTT messages.

### Prerequisites
- Docker and Docker Compose installed
- MQTT client (mosquitto_pub) or Python with paho-mqtt

### Method 1: Using mosquitto_pub

Install mosquitto-clients if not already available:
```bash
# On Ubuntu/Debian
sudo apt-get install mosquitto-clients

# On macOS
brew install mosquitto
```

Publish a test message:
```bash
mosquitto_pub -h localhost -p 1883 -t paku/ruuvi/van_inside -m '{
  "sensor_id": "van_inside",
  "temperature_c": 22.5,
  "humidity_percent": 48.0,
  "pressure_hpa": 1013.2,
  "battery_mv": 2950,
  "timestamp": "2025-11-26T12:00:00Z"
}'
```

### Method 2: Using Python

Create a test publisher script:
```python
#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883, 60)

message = {
    "sensor_id": "van_inside",
    "temperature_c": 22.5,
    "humidity_percent": 48.0,
    "pressure_hpa": 1013.2,
    "battery_mv": 2950,
    "timestamp": "2025-11-26T12:00:00Z"
}

client.publish("paku/ruuvi/van_inside", json.dumps(message))
print("Published test message")
time.sleep(1)
client.disconnect()
```

## Verifying Data Insertion

### Check Collector Logs
```bash
docker logs -f paku_collector
```

You should see log messages like:
```
INFO - Connected to MQTT broker at mosquitto:1883
INFO - Subscribing to topic: paku/ruuvi/van_inside
INFO - Inserted measurement: sensor_id=van_inside, temp=22.5°C, humidity=48.0%, pressure=1013.2hPa, battery=2950mV
```

### Query the Database

Connect to PostgreSQL:
```bash
docker exec -it paku_postgres psql -U paku -d paku
```

Check the measurements:
```sql
-- Count total measurements
SELECT count(*) FROM measurements;

-- View recent measurements
SELECT * FROM measurements ORDER BY ts DESC LIMIT 10;

-- View measurements with formatted timestamp
SELECT 
    id,
    sensor_id,
    ts,
    temperature_c,
    humidity_percent,
    pressure_hpa,
    battery_mv
FROM measurements 
ORDER BY ts DESC 
LIMIT 5;
```

Expected output:
```
 id | sensor_id  |           ts              | temperature_c | humidity_percent | pressure_hpa | battery_mv 
----+------------+---------------------------+---------------+------------------+--------------+------------
  1 | van_inside | 2025-11-26 12:00:00+00:00 |          22.5 |             48.0 |       1013.2 |       2950
```

## Testing Error Handling

### Test 1: Malformed JSON
```bash
mosquitto_pub -h localhost -p 1883 -t paku/ruuvi/van_inside -m '{"invalid_json":'
```

Expected behavior:
- Collector logs an error about invalid JSON
- Collector continues running (doesn't crash)
- No row inserted into database

### Test 2: Missing Required Fields
```bash
mosquitto_pub -h localhost -p 1883 -t paku/ruuvi/van_inside -m '{}'
```

Expected behavior:
- Collector accepts the message
- Inserts row with NULL values for missing fields
- sensor_id defaults to "unknown"

### Test 3: Legacy Format
```bash
mosquitto_pub -h localhost -p 1883 -t paku/ruuvi/van_inside -m '{
  "tag": "test-sensor",
  "temperature": 20.0,
  "humidity": 50.0,
  "battery": 3.2,
  "ts": "2025-11-26T12:00:00Z"
}'
```

Expected behavior:
- Collector maps legacy fields to database schema
- `tag` → `sensor_id`
- `temperature` → `temperature_c`
- `humidity` → `humidity_percent`
- `battery` (3.2V) → `battery_mv` (3200mV)
- `ts` → `ts`

## Acceptance Criteria Validation

✅ **With emulator running, `SELECT count(*) FROM measurements;` increases over time**
   - Once a ruuvi-emulator is implemented and running, query the database periodically
   - The count should steadily increase

✅ **Collector does not crash on a single malformed message**
   - Tested by publishing invalid JSON
   - Collector logs error and continues processing subsequent messages

✅ **All inserts use the same schema established in S2-3**
   - Schema defined in `stack/postgres/init.sql`
   - All fields map to documented columns: sensor_id, ts, temperature_c, humidity_percent, pressure_hpa, battery_mv

## Performance Testing

For load testing:
```bash
# Publish 100 messages rapidly
for i in {1..100}; do
  mosquitto_pub -h localhost -p 1883 -t paku/ruuvi/van_inside -m "{
    \"sensor_id\": \"van_inside\",
    \"temperature_c\": $((20 + RANDOM % 10)),
    \"humidity_percent\": $((40 + RANDOM % 20)),
    \"pressure_hpa\": 1013.2,
    \"battery_mv\": 2900,
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }"
done

# Verify all were inserted
docker exec -it paku_postgres psql -U paku -d paku -c "SELECT count(*) FROM measurements;"
```

## Troubleshooting

### Collector won't connect to MQTT
- Check mosquitto is running: `docker ps | grep mosquitto`
- Check mosquitto logs: `docker logs paku_mosquitto`
- Verify port 1883 is exposed

### Collector won't connect to PostgreSQL
- Check postgres is running: `docker ps | grep postgres`
- Check postgres logs: `docker logs paku_postgres`
- Verify database was created (check for init.sql execution in logs)

### No data appearing in database
- Check collector logs for errors
- Try publishing a message manually
- Verify the topic name matches exactly (case-sensitive)
- Check that JSON is valid
