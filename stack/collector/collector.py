import os
import json
import signal
import sys
import time
import psycopg
import paho.mqtt.client as mqtt

PGHOST = os.getenv('PGHOST', 'postgres')
PGUSER = os.getenv('PGUSER', 'paku')
PGPASSWORD = os.getenv('PGPASSWORD', 'paku')
PGDATABASE = os.getenv('PGDATABASE', 'paku')
MQTT_HOST = os.getenv('MQTT_HOST', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))


def wait_for_postgres(max_retries=30, delay=2):
    """Wait for Postgres to be available."""
    for i in range(max_retries):
        try:
            conn = psycopg.connect(
                host=PGHOST,
                user=PGUSER,
                password=PGPASSWORD,
                dbname=PGDATABASE,
                autocommit=True
            )
            print(f'Connected to Postgres after {i + 1} attempts', flush=True)
            return conn
        except psycopg.OperationalError as e:
            print(f'Waiting for Postgres... attempt {i + 1}/{max_retries}', flush=True)
            time.sleep(delay)
    raise RuntimeError('Could not connect to Postgres')


def wait_for_mqtt(max_retries=30, delay=2):
    """Wait for MQTT broker to be available."""
    for i in range(max_retries):
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.disconnect()
            print(f'MQTT broker available after {i + 1} attempts', flush=True)
            return True
        except Exception as e:
            print(f'Waiting for MQTT broker... attempt {i + 1}/{max_retries}', flush=True)
            time.sleep(delay)
    raise RuntimeError('Could not connect to MQTT broker')


# Wait for dependencies
conn = wait_for_postgres()
wait_for_mqtt()

# Create measurements table
with conn.cursor() as cur:
    cur.execute("""CREATE TABLE IF NOT EXISTS measurements (
        id BIGSERIAL PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL DEFAULT now(),
        sensor_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        temperature_c NUMERIC,
        humidity_percent NUMERIC,
        pressure_hpa NUMERIC,
        battery_mv INTEGER,
        payload JSONB NOT NULL
    );""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts);""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id ON measurements(sensor_id);""")
    print('Database schema ready', flush=True)


def on_connect(client, userdata, flags, rc, properties=None):
    print(f'Collector connected to MQTT broker (rc={rc})', flush=True)
    client.subscribe('paku/#', qos=0)
    print('Subscribed to paku/#', flush=True)


def on_message(client, userdata, msg):
    payload_str = msg.payload.decode('utf-8', 'replace')
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        data = {'raw': payload_str}
        print(f'Warning: Could not parse JSON payload from {msg.topic}', flush=True)

    # Extract fields from the payload
    sensor_id = data.get('sensor_id', 'unknown')
    temperature_c = data.get('temperature_c')
    humidity_percent = data.get('humidity_percent')
    pressure_hpa = data.get('pressure_hpa')
    battery_mv = data.get('battery_mv')

    with conn.cursor() as cur:
        cur.execute(
            '''INSERT INTO measurements(sensor_id, topic, temperature_c, humidity_percent, pressure_hpa, battery_mv, payload)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (sensor_id, msg.topic, temperature_c, humidity_percent, pressure_hpa, battery_mv, json.dumps(data))
        )
    print(f'Inserted measurement from {msg.topic}: sensor_id={sensor_id}', flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)


def _stop(sig, frame):
    print('Shutting down collector...', flush=True)
    client.loop_stop()
    conn.close()
    sys.exit(0)


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

print('Collector running...', flush=True)
client.loop_forever()
