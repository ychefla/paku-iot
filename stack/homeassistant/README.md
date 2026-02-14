# Home Assistant Integration for Paku IoT

Configuration files for integrating Home Assistant with the paku ecosystem.

## Architecture

```
ESP32 (paku-core) ──► Local Mosquitto (HA) ◄══bridge══► Cloud Mosquitto
                           ▲                                  ▲
                      Home Assistant                    Collector → Postgres → Grafana
```

A local Mosquitto broker on the HA device bridges to the cloud broker.  
Everything works locally when the internet is down.

## Setup Steps

### 1. Install Mosquitto Add-on in HA

1. Open HA → **Settings → Add-ons → Add-on Store**
2. Search **"Mosquitto broker"** → Install → Start
3. Enable **Start on boot** and **Watchdog**

### 2. Install File Editor Add-on

1. Add-on Store → Search **"File editor"** → Install → Start
2. Enable **Show in sidebar**

### 3. Configure the MQTT Bridge

1. Open **File Editor** from the sidebar
2. Navigate to `/share/mosquitto/`  (create the folder if it doesn't exist)
3. Create `bridge.conf` with the contents of [`mosquitto_bridge.conf`](mosquitto_bridge.conf)
4. Restart the Mosquitto add-on

### 4. Add MQTT Integration

1. **Settings → Devices & Services → Add Integration → MQTT**
2. Broker: `core-mosquitto` (or `localhost`)
3. Port: `1883`
4. Leave username/password blank (unless you configured auth)

### 5. Install Sensor Configuration

1. In File Editor, navigate to `/config/`
2. Create a `packages/` directory if it doesn't exist
3. Copy [`paku.yaml`](paku.yaml) into `/config/packages/paku.yaml`
4. Edit `paku.yaml` — replace placeholder device IDs with your actual values
5. Ensure `/config/configuration.yaml` has:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
6. Restart Home Assistant

### 6. Point ESP32 Devices at Local Broker

In `secrets.h` on each ESP32:
```cpp
#define MQTT_SERVER "192.168.x.x"  // IP of your HA / RPi
#define MQTT_PORT 1883
```

## What You Get

### Auto-discovered (no config needed)
- Heater switch (on/off)
- Coolant temperature, core temperature
- Flow rate, battery voltage
- Safety OK, UART link status

### From paku.yaml config
- RuuviTag temperature, humidity, pressure, battery (per location)
- DS18B20 wired temperature
- Edge device online status, WiFi signal, uptime, firmware version

## Files

| File | Purpose | Install Location |
|------|---------|-----------------|
| `mosquitto_bridge.conf` | MQTT bridge to cloud | `/share/mosquitto/bridge.conf` |
| `paku.yaml` | HA MQTT sensor config | `/config/packages/paku.yaml` |
