# Paku Collector Service

The collector is a lightweight Python service responsible for:

- subscribing to MQTT messages produced by the Ruuvi emulator  
- validating and parsing the JSON payloads  
- inserting measurements into the Postgres `measurements` table  

It runs automatically as part of the unified Paku IoT stack.

---

## Data Flow

```
Ruuvi Emulator → Mosquitto (MQTT) → Collector → Postgres → Grafana
```

---

## Environment Variables

These are injected via `compose/stack.yaml`:

### MQTT
- `MQTT_HOST`  
- `MQTT_PORT`  
- `MQTT_TOPIC`

### Postgres
- `PGHOST`  
- `PGPORT`  
- `PGUSER`  
- `PGPASSWORD`  
- `PGDATABASE`

---

## Runtime Logic

1. Connect to Postgres using psycopg.  
2. Connect to Mosquitto using Paho MQTT and subscribe to `MQTT_TOPIC`.  
3. For each incoming message:
   - decode UTF‑8 payload  
   - parse JSON  
   - validate fields based on `docs/mqtt_schema.md`  
   - insert full measurement row into Postgres  
4. Log errors but keep the collector running.

---

## Source Code

Collector implementation:  
`stack/collector/collector.py`

Docker image definition:  
`stack/collector/Dockerfile`

---
