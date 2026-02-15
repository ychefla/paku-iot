#!/usr/bin/env python3
"""
Autoterm Heater Emulator — MQTT Publisher

Simulates an Autoterm Flow 5D hydronic heater connected to paku-core,
publishing telemetry to paku/heater/{device_id}/data and HA state to
paku/heater/{device_id}/state.

The emulator runs a simple state machine:
  Off → Starting → Running → (optional) ShuttingDown → Cooling → Off

Controlled via MQTT commands on paku/heater/{device_id}/cmd:
  {"cmd": "start", "power": 5}
  {"cmd": "stop"}
  {"cmd": "vent", "power": 3}
  {"cmd": "reset"}

Environment variables:
  MQTT_HOST              Broker hostname (default: mosquitto)
  MQTT_PORT              Broker port (default: 1883)
  DEVICE_ID              Device identifier (default: emu01)
  MAX_RUNTIME_SECONDS    Auto-shutdown after N seconds (default: 600)
  PUBLISH_INTERVAL       Seconds between publishes (default: 5)
"""

import json
import math
import os
import random
import time
from datetime import datetime, timezone
from enum import Enum

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion


class HeaterState(Enum):
    OFF = "Off"
    STARTING = "Starting"
    WARMING = "Warming"
    RUNNING = "Running"
    VENTILATION = "Ventilation"
    SHUTTING_DOWN = "ShuttingDown"
    COOLING = "Cooling"


class HeaterEmulator:
    """Simulates heater state machine with realistic thermal behavior."""

    def __init__(self):
        self.state = HeaterState.OFF
        self.coolant_temp = 20.0   # Ambient
        self.core_temp = 25.0
        self.flow_lpm = 3.5        # Healthy flow
        self.battery_v = 12.8
        self.error = "None"
        self.safety_ok = True
        self.state_start_time = time.time()
        self.power_level = 0

    def update(self, dt: float):
        """Advance the simulation by dt seconds."""
        elapsed = time.time() - self.state_start_time

        # Battery voltage jitter
        self.battery_v = 12.6 + random.gauss(0, 0.1)

        # Flow rate jitter
        if self.state in (HeaterState.OFF, HeaterState.COOLING):
            self.flow_lpm = max(0.0, 3.0 + random.gauss(0, 0.2))
        else:
            self.flow_lpm = max(0.5, 3.5 + random.gauss(0, 0.3))

        # State machine transitions
        if self.state == HeaterState.OFF:
            self.core_temp = max(25.0, self.core_temp - dt * 0.5)
            self.coolant_temp = max(20.0, self.coolant_temp - dt * 0.3)

        elif self.state == HeaterState.STARTING:
            self.core_temp += dt * 2.0
            if elapsed > 8:
                self._transition(HeaterState.WARMING)

        elif self.state == HeaterState.WARMING:
            self.core_temp += dt * 1.5
            self.coolant_temp += dt * 0.8
            if elapsed > 12:
                self._transition(HeaterState.RUNNING)

        elif self.state == HeaterState.RUNNING:
            # Steady state with slight oscillation
            target_core = 80 + self.power_level * 3
            target_coolant = 55 + self.power_level * 2
            self.core_temp += (target_core - self.core_temp) * 0.05
            self.coolant_temp += (target_coolant - self.coolant_temp) * 0.03
            # Add sinusoidal variation
            self.coolant_temp += math.sin(time.time() * 0.1) * 0.3

        elif self.state == HeaterState.VENTILATION:
            self.core_temp = max(30.0, self.core_temp - dt * 0.3)
            self.coolant_temp = max(20.0, self.coolant_temp - dt * 0.2)

        elif self.state == HeaterState.SHUTTING_DOWN:
            self.core_temp -= dt * 1.0
            self.coolant_temp -= dt * 0.3
            if elapsed > 6:
                self._transition(HeaterState.COOLING)

        elif self.state == HeaterState.COOLING:
            self.core_temp = max(30.0, self.core_temp - dt * 0.8)
            self.coolant_temp = max(20.0, self.coolant_temp - dt * 0.4)
            if elapsed > 10:
                self._transition(HeaterState.OFF)

    def start(self, power: int = 5):
        if self.state == HeaterState.OFF:
            self.power_level = max(0, min(9, power))
            self._transition(HeaterState.STARTING)
            print(f"[Heater] Starting (power {self.power_level})")

    def stop(self):
        if self.state in (HeaterState.STARTING, HeaterState.WARMING,
                          HeaterState.RUNNING, HeaterState.VENTILATION):
            self._transition(HeaterState.SHUTTING_DOWN)
            print("[Heater] Shutting down")

    def vent(self, power: int = 5):
        if self.state == HeaterState.OFF:
            self.power_level = max(0, min(9, power))
            self._transition(HeaterState.VENTILATION)
            print(f"[Heater] Ventilation mode (power {self.power_level})")

    def _transition(self, new_state: HeaterState):
        print(f"[Heater] {self.state.value} → {new_state.value}")
        self.state = new_state
        self.state_start_time = time.time()

    def is_running(self) -> bool:
        return self.state in (HeaterState.STARTING, HeaterState.WARMING,
                              HeaterState.RUNNING)

    def to_state_json(self, device_id: str) -> dict:
        """HA state topic payload (flat, matches value_templates)."""
        return {
            "state": self.state.value,
            "coolant_temp_c": round(self.coolant_temp, 1),
            "flow_lpm": round(self.flow_lpm, 1),
            "battery_v": round(self.battery_v, 1),
            "core_temp_c": round(self.core_temp, 0),
            "safety_ok": self.safety_ok,
            "uart_online": True,
            "error": self.error,
            "running": self.is_running(),
        }

    def to_data_json(self, device_id: str) -> dict:
        """paku-iot collector topic payload (matches +/+/+/data)."""
        return {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "device_id": f"heater_{device_id}",
            "location": "van",
            "metrics": {
                "coolant_temp_c": round(self.coolant_temp, 1),
                "flow_lpm": round(self.flow_lpm, 1),
                "battery_v": round(self.battery_v, 1),
                "core_temp_c": round(self.core_temp, 0),
                "heater_state": self.state.value,
                "safety_ok": 1 if self.safety_ok else 0,
                "uart_online": 1,
                "error": self.error,
            },
        }


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Failed to connect: {reason_code}")
        return
    print("Connected to MQTT broker")
    emu = userdata
    cmd_topic = f"paku/heater/{emu['device_id']}/cmd"
    client.subscribe(cmd_topic)
    print(f"Subscribed to {cmd_topic}")


def on_message(client, userdata, msg):
    emu = userdata
    heater = emu["heater"]
    try:
        payload = json.loads(msg.payload.decode())
        cmd = payload.get("cmd", "")
        if cmd == "start":
            power = payload.get("power", 5)
            heater.start(power)
        elif cmd == "stop":
            heater.stop()
        elif cmd == "vent":
            power = payload.get("power", 5)
            heater.vent(power)
        elif cmd == "reset":
            heater.safety_ok = True
            heater.error = "None"
            print("[Heater] Safety reset")
        else:
            print(f"Unknown command: {cmd}")
    except Exception as e:
        print(f"Error processing command: {e}")


def main():
    mqtt_host = os.getenv("MQTT_HOST", "mosquitto")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    device_id = os.getenv("DEVICE_ID", "emu01")
    max_runtime = int(os.getenv("MAX_RUNTIME_SECONDS", "600"))
    interval = int(os.getenv("PUBLISH_INTERVAL", "5"))

    heater = HeaterEmulator()
    userdata = {"heater": heater, "device_id": device_id}

    state_topic = f"paku/heater/{device_id}/state"
    data_topic = f"paku/heater/{device_id}/data"

    print(f"Starting Autoterm heater emulator...")
    print(f"MQTT: {mqtt_host}:{mqtt_port}")
    print(f"Device: {device_id}")
    print(f"Topics: {state_topic}, {data_topic}")
    print(f"Publish interval: {interval}s, max runtime: {max_runtime}s")

    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        userdata=userdata,
    )
    client.on_connect = on_connect
    client.on_message = on_message

    # Set credentials if provided
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)

    # Retry connection
    for attempt in range(1, 11):
        try:
            client.connect(mqtt_host, mqtt_port, 60)
            break
        except Exception as e:
            print(f"Connect attempt {attempt}/10 failed: {e}")
            if attempt < 10:
                time.sleep(5)
            else:
                print("Max retries reached. Exiting.")
                return

    client.loop_start()
    time.sleep(2)

    start_time = time.time()
    last_update = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= max_runtime:
                print(f"\nMax runtime {max_runtime}s reached. Exiting.")
                break

            # Update simulation
            now = time.time()
            dt = now - last_update
            last_update = now
            heater.update(dt)

            # Publish state (for HA)
            state_payload = json.dumps(heater.to_state_json(device_id))
            client.publish(state_topic, state_payload, qos=0)

            # Publish data (for paku-iot collector)
            data_payload = json.dumps(heater.to_data_json(device_id))
            client.publish(data_topic, data_payload, qos=0)

            print(f"[{heater.state.value:>12}] "
                  f"coolant={heater.coolant_temp:.1f}°C "
                  f"core={heater.core_temp:.0f}°C "
                  f"flow={heater.flow_lpm:.1f}L/m "
                  f"batt={heater.battery_v:.1f}V")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nShutting down emulator...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
