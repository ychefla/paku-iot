import paho.mqtt.client as mqtt
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import json

# Initialize InfluxDB Client with token

token='ejUrCrkAsSaFPW8O3-iUpJkCyfHGEPdcumIVW3C1c3hFoc88wkOqM4PDpDend_zHLScAnVfrZc8e7EqE7UV9_w=='
org='Paku'
url='http://influxdb2:8086'

influx_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

write_api = influx_client.write_api(write_options=SYNCHRONOUS)


# MQTT broker config
MQTT_BROKER_URL    = "mosquitto"
MQTT_PUBLISH_TOPIC = "test_topic"

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(MQTT_PUBLISH_TOPIC)

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    data = msg.payload.decode()

    # Check if data is valid JSON
    try:
        json_data = json.loads(data)

        # Handle both float and dict cases
        if isinstance(json_data, dict):
            value = float(json_data['value'])  # Extract value from JSON
        elif isinstance(json_data, float):
            value = json_data
        else:
            raise ValueError("Invalid data type")

    except (ValueError, KeyError, json.JSONDecodeError):
        print("Invalid data received")
        return

    # Process and store data in InfluxDB
    point = Point(MQTT_PUBLISH_TOPIC) \
        .tag("location", "test_location") \
        .field("value", value) \
        .time(time.time_ns(), WritePrecision.NS)

    write_api.write(bucket='core_data', org='Paku', record=point)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER_URL, 1883, 60)
mqtt_client.loop_forever()
