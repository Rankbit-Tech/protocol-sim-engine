# MQTT Protocol Guide

**Complete guide to MQTT IoT device simulation with embedded broker**

Version: 0.2.0
Status: Production Ready
Last Updated: February 2, 2026

---

## Overview

The MQTT implementation provides realistic IoT device simulation with a **built-in MQTT broker**. No external broker setup is required - just enable MQTT in your configuration and the simulator handles everything.

### Key Features

- **Embedded MQTT Broker** - Built-in amqtt broker, no external dependencies
- **Multiple Device Types** - Environmental sensors, energy meters, asset trackers
- **Realistic Data** - Industrial-grade data patterns with noise and variation
- **Configurable QoS** - Support for QoS levels 0, 1, and 2
- **Custom Topics** - Flexible topic hierarchy configuration
- **Gateway Pattern** - Reliable single-client architecture for all devices

---

## Quick Start

### 1. Enable MQTT in Configuration

```yaml
# config.yml
industrial_protocols:
  mqtt:
    enabled: true
    use_embedded_broker: true  # No external broker needed!
    broker_port: 1883
    devices:
      temperature_sensors:
        count: 5
        device_template: "iot_environmental_sensor"
        base_topic: "factory/sensors"
        publish_interval: 5.0
        qos: 1
```

### 2. Run the Simulator

```bash
docker run -d \
  --name iot-sim \
  -p 8080:8080 \
  -p 1883:1883 \
  -v $(pwd)/config.yml:/config/factory.yml \
  developeryashsolanki/protocol-sim-engine:latest
```

### 3. Subscribe to Messages

```bash
# Using mosquitto_sub
mosquitto_sub -h localhost -t "factory/#" -v

# Output:
# factory/sensors/mqtt_temperature_sensors_000/status {"device_id": "...", "status": "online"}
# factory/sensors/mqtt_temperature_sensors_000/data {"temperature": 22.5, "humidity": 45.2, ...}
```

---

## Device Types

### Environmental Sensor

Simulates indoor environmental monitoring devices.

```yaml
device_template: "iot_environmental_sensor"
base_topic: "factory/environment"
publish_interval: 5.0
qos: 1
data_config:
  temperature_range: [18, 35]
  humidity_range: [30, 80]
```

**Published Data:**

```json
{
  "device_id": "mqtt_environmental_sensors_000",
  "device_type": "environmental_sensor",
  "timestamp": 1770027936.29,
  "data": {
    "temperature": 22.5,
    "humidity": 45.2,
    "air_quality_index": 65,
    "co2_ppm": 710,
    "tvoc_ppb": 154,
    "pressure_hpa": 1013.25
  }
}
```

**Data Fields:**

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| temperature | float | °C | Ambient temperature |
| humidity | float | % | Relative humidity |
| air_quality_index | int | - | AQI (0-500) |
| co2_ppm | int | ppm | CO2 concentration |
| tvoc_ppb | int | ppb | Total VOCs |
| pressure_hpa | float | hPa | Atmospheric pressure |

---

### Smart Energy Meter

Simulates industrial power monitoring devices.

```yaml
device_template: "smart_meter"
base_topic: "factory/energy"
publish_interval: 10.0
qos: 1
data_config:
  voltage_range: [220, 240]
  current_range: [0, 100]
  power_factor_range: [0.85, 0.99]
```

**Published Data:**

```json
{
  "device_id": "mqtt_energy_meters_000",
  "device_type": "energy_meter",
  "timestamp": 1770027936.29,
  "data": {
    "voltage_v": 231.4,
    "current_a": 32.1,
    "power_kw": 6.52,
    "power_factor": 0.88,
    "frequency_hz": 49.99,
    "energy_kwh": 10000.0,
    "phase": "L1"
  }
}
```

**Data Fields:**

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| voltage_v | float | V | Line voltage |
| current_a | float | A | Current draw |
| power_kw | float | kW | Active power |
| power_factor | float | - | Power factor (0-1) |
| frequency_hz | float | Hz | Grid frequency |
| energy_kwh | float | kWh | Total energy consumed |
| phase | string | - | Phase identifier |

---

### Asset Tracker

Simulates indoor asset tracking beacons.

```yaml
device_template: "asset_tracker"
base_topic: "factory/assets"
publish_interval: 30.0
qos: 0
data_config:
  zone_ids: ["zone_a", "zone_b", "zone_c", "warehouse"]
  battery_drain_rate: 0.001
```

**Published Data:**

```json
{
  "device_id": "mqtt_asset_trackers_000",
  "device_type": "asset_tracker",
  "timestamp": 1770027936.29,
  "data": {
    "zone_id": "zone_a",
    "battery_level": 87.5,
    "rssi": -65,
    "last_seen": 1770027936.29
  }
}
```

---

## Topic Structure

Messages are published to a hierarchical topic structure:

```
{base_topic}/{device_id}/status   - Online/offline status (retained)
{base_topic}/{device_id}/data     - Telemetry data
{base_topic}/{device_id}/alerts   - Alert messages (if any)
```

### Examples

With `base_topic: "factory/sensors"`:

```
factory/sensors/mqtt_environmental_sensors_000/status
factory/sensors/mqtt_environmental_sensors_000/data
factory/sensors/mqtt_environmental_sensors_001/status
factory/sensors/mqtt_environmental_sensors_001/data
```

### Status Messages

Status messages are published with `retain=true` so new subscribers immediately know device state:

```json
{"device_id": "mqtt_environmental_sensors_000", "status": "online", "timestamp": 1770027936.29}
```

---

## Configuration Reference

### MQTT Protocol Settings

```yaml
industrial_protocols:
  mqtt:
    enabled: true                    # Enable MQTT protocol
    use_embedded_broker: true        # Use built-in broker (recommended)
    broker_host: "localhost"         # Broker hostname
    broker_port: 1883                # Broker port
    client_id_prefix: "sim_"         # Client ID prefix
    devices:
      # ... device configurations
```

### Device Configuration

```yaml
devices:
  my_sensors:
    count: 10                        # Number of devices to create
    device_template: "iot_environmental_sensor"  # Device type
    base_topic: "factory/sensors"    # Topic prefix
    publish_interval: 5.0            # Seconds between publishes
    qos: 1                           # MQTT QoS level (0, 1, 2)
    retain: false                    # Retain data messages
    data_config:                     # Device-specific parameters
      temperature_range: [18, 35]
      humidity_range: [30, 80]
```

### Using External Broker

To use an external broker (e.g., Mosquitto, HiveMQ):

```yaml
industrial_protocols:
  mqtt:
    enabled: true
    use_embedded_broker: false       # Disable embedded broker
    broker_host: "my-broker.example.com"
    broker_port: 1883
```

---

## API Endpoints

### Broker Status

```bash
GET /mqtt/broker
```

Response:
```json
{
  "broker_host": "localhost",
  "broker_port": 1883,
  "embedded": true,
  "status": "connected",
  "gateway_client_id": "mqtt_gateway"
}
```

### List Topics

```bash
GET /mqtt/topics
```

Response:
```json
{
  "topic_count": 10,
  "devices": [
    {
      "device_id": "mqtt_environmental_sensors_000",
      "topics": {
        "data": "factory/sensors/mqtt_environmental_sensors_000/data",
        "status": "factory/sensors/mqtt_environmental_sensors_000/status"
      }
    }
  ]
}
```

### Device Messages

```bash
GET /mqtt/devices/{device_id}/messages?limit=10
```

Response:
```json
{
  "device_id": "mqtt_environmental_sensors_000",
  "message_count": 50,
  "messages": [
    {"timestamp": 1770027936.29, "data": {...}},
    {"timestamp": 1770027931.29, "data": {...}}
  ]
}
```

---

## Architecture

### Gateway Pattern

The MQTT implementation uses a **gateway pattern** where a single MQTT client publishes messages for all devices. This provides:

- **Reliability** - Single connection to manage
- **Efficiency** - Reduced broker load
- **Simplicity** - No per-device connection management

```
┌─────────────────────────────────────────────────────┐
│                 MQTTDeviceManager                   │
│  ┌─────────────────────────────────────────────┐   │
│  │           Shared MQTT Client                │   │
│  │         (gateway pattern)                   │   │
│  └─────────────────────────────────────────────┘   │
│       │           │           │           │        │
│  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐  │
│  │Device 1 │ │Device 2 │ │Device 3 │ │Device N │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  MQTT Broker    │
              │  (embedded or   │
              │   external)     │
              └─────────────────┘
```

### Embedded Broker

When `use_embedded_broker: true`, the simulator starts an amqtt broker:

- Binds to `0.0.0.0:1883`
- Allows anonymous connections
- Supports QoS 0, 1, 2
- Graceful shutdown on stop

---

## Testing

### Subscribe to All Topics

```bash
# All factory topics
mosquitto_sub -h localhost -t "factory/#" -v

# Only sensor data
mosquitto_sub -h localhost -t "factory/sensors/+/data" -v

# Only status messages
mosquitto_sub -h localhost -t "factory/+/+/status" -v
```

### Python Client Example

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    print(f"{msg.topic}: {data['data']}")

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("factory/#")
client.loop_forever()
```

### Verify via API

```bash
# Check broker status
curl http://localhost:8080/mqtt/broker

# List all topics
curl http://localhost:8080/mqtt/topics

# Get device data
curl http://localhost:8080/devices/mqtt_environmental_sensors_000/data
```

---

## Troubleshooting

### Broker Connection Failed

**Symptom:** `MQTT gateway connection timeout`

**Solutions:**
1. If using embedded broker, ensure no other process is using port 1883
2. If using external broker, verify `broker_host` and `broker_port` are correct
3. Check broker is running: `nc -z localhost 1883`

### No Messages Published

**Symptom:** Subscriptions show no messages

**Solutions:**
1. Check device `publish_interval` - messages may be infrequent
2. Verify topic subscription matches `base_topic` in config
3. Check `/mqtt/broker` endpoint shows `status: connected`

### Embedded Broker Not Starting

**Symptom:** `amqtt not installed` warning

**Solutions:**
1. Ensure using the official Docker image (includes amqtt)
2. If building from source, run `poetry install`
3. Set `use_embedded_broker: false` and use external broker

---

## Best Practices

### Topic Design

- Use hierarchical topics: `{location}/{type}/{device_id}/{message_type}`
- Keep topics concise but descriptive
- Use wildcards (`+`, `#`) for flexible subscriptions

### QoS Selection

| QoS | Use Case | Overhead |
|-----|----------|----------|
| 0 | Non-critical telemetry | Lowest |
| 1 | Standard monitoring | Medium |
| 2 | Critical alerts | Highest |

### Publish Intervals

| Device Type | Recommended Interval |
|-------------|---------------------|
| Environmental sensors | 5-30 seconds |
| Energy meters | 10-60 seconds |
| Asset trackers | 30-300 seconds |

---

## External Resources

- [MQTT Specification](https://mqtt.org/mqtt-specification/)
- [Paho MQTT Python](https://pypi.org/project/paho-mqtt/)
- [amqtt Documentation](https://github.com/Yakifo/amqtt)
- [MQTT Best Practices](https://www.hivemq.com/mqtt-essentials/)

---

**Status: Production Ready** ✅

**Last Updated: February 2, 2026**
