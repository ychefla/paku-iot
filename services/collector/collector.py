import os, json, signal, sys
import psycopg
import paho.mqtt.client as mqtt

PGHOST = os.getenv('PGHOST', 'postgres')
PGUSER = os.getenv('PGUSER', 'paku')
PGPASSWORD = os.getenv('PGPASSWORD', 'paku')
PGDATABASE = os.getenv('PGDATABASE', 'paku')
MQTT_HOST = os.getenv('MQTT_HOST', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))

conn = psycopg.connect(host=PGHOST, user=PGUSER, password=PGPASSWORD, dbname=PGDATABASE, autocommit=True)
with conn.cursor() as cur:
    cur.execute("""CREATE TABLE IF NOT EXISTS measurements (
        id BIGSERIAL PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL DEFAULT now(),
        topic TEXT NOT NULL,
        payload JSONB NOT NULL
    );""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts);""")

def on_connect(client, userdata, flags, rc, properties=None):
    print('collector connected rc=', rc, flush=True)
    client.subscribe('paku/#', qos=0)

def on_message(client, userdata, msg):
    payload_str = msg.payload.decode('utf-8', 'replace')
    try:
        data = json.loads(payload_str)
    except Exception:
        data = {'raw': payload_str}
    with conn.cursor() as cur:
        cur.execute('INSERT INTO measurements(topic, payload) VALUES (%s, %s)', (msg.topic, json.dumps(data)))
    print('inserted', msg.topic, data, flush=True)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)

def _stop(sig, frame):
    client.loop_stop()
    conn.close()
    sys.exit(0)

signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)
client.loop_forever()
