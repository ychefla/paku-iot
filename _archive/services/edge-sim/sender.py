import os, time, json, random, signal, sys, datetime
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv('MQTT_HOST','mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT','1883'))
TOPIC = 'paku/devkit-1/sens/ruuvi'

run = True
def _stop(*_): 
    global run
    run = False
signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

while run:
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    msg = {
        "tag":"faux-ruuvi-1",
        "ts": now,
        "temperature": round(random.uniform(20.0, 25.0), 2),
        "humidity": round(random.uniform(45.0, 55.0), 1),
        "battery": round(random.uniform(3.0, 3.2), 2),
        "rssi": random.randint(-80, -60)
    }
    client.publish(TOPIC, json.dumps(msg), qos=0, retain=False)
    print("published:", msg, flush=True)
    time.sleep(5)

client.loop_stop()
client.disconnect()
