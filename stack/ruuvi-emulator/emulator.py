import json
import os
import random
import time
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv('MQTT_HOST', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
PUBLISH_INTERVAL = float(os.getenv('PUBLISH_INTERVAL', '10'))  # seconds
SENSOR_ID = os.getenv('SENSOR_ID', 'van_inside')
TOPIC = f'paku/ruuvi/{SENSOR_ID}'


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


def generate_ruuvi_payload():
    """Generate a RuuviTag-style payload with random values."""
    return {
        "sensor_id": SENSOR_ID,
        "temperature_c": round(random.uniform(18.0, 28.0), 1),
        "humidity_percent": round(random.uniform(30.0, 70.0), 1),
        "pressure_hpa": round(random.uniform(990.0, 1020.0), 1),
        "acceleration_x_mg": random.randint(-100, 100),
        "acceleration_y_mg": random.randint(-100, 100),
        "acceleration_z_mg": random.randint(900, 1100),
        "acceleration_total_mg": random.randint(900, 1100),
        "tx_power_dbm": 4,
        "movement_counter": random.randint(0, 255),
        "measurement_sequence": random.randint(0, 65535),
        "battery_mv": random.randint(2500, 3000),
        "mac": "AA:BB:CC:DD:EE:FF",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


def on_connect(client, userdata, flags, rc, properties=None):
    print(f'Emulator connected to MQTT broker (rc={rc})', flush=True)


def on_disconnect(client, userdata, rc, properties=None, reasoncode=None):
    print(f'Emulator disconnected from MQTT broker (rc={rc})', flush=True)


def main():
    wait_for_mqtt()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    print(f'Ruuvi emulator started. Publishing to {TOPIC} every {PUBLISH_INTERVAL}s', flush=True)

    try:
        while True:
            payload = generate_ruuvi_payload()
            message = json.dumps(payload)
            result = client.publish(TOPIC, message, qos=0)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f'Published: {message}', flush=True)
            else:
                print(f'Failed to publish message (rc={result.rc})', flush=True)
            time.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        print('Shutting down emulator...', flush=True)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == '__main__':
    main()
