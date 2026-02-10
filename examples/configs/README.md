# Configuration Examples

Ready-to-use configuration files for common industrial scenarios.

## 🚀 Quick Start

### Simple Factory (3 Devices)

```bash
docker run --rm \
  -v $(pwd)/simple_factory.yml:/config/factory.yml \
  -p 15000-15002:15000-15002 \
  -p 8080:8080 \
  universal-simulation-engine:latest
```

**Devices:** 1 temperature sensor, 1 pressure transmitter, 1 motor drive

### Large Factory (60 Devices)

```bash
docker run --rm \
  -v $(pwd)/large_factory.yml:/config/factory.yml \
  -p 15000-15050:15000-15050 \
  -p 4840-4860:4840-4860 \
  -p 8080:8080 \
  universal-simulation-engine:latest
```

**Devices:** 20 temperature sensors, 15 pressure transmitters, 15 motor drives, 3 CNC machines, 3 PLC controllers, 4 industrial robots

### Full Factory (Modbus + MQTT + OPC-UA)

```bash
docker run --rm \
  -v $(pwd)/full_factory.yml:/config/factory.yml \
  -p 15000-15020:15000-15020 \
  -p 1883:1883 \
  -p 4840-4850:4840-4850 \
  -p 8080:8080 \
  universal-simulation-engine:latest
```

**Devices:** Modbus sensors + MQTT IoT devices + OPC-UA industrial equipment (CNC, PLC, Robot)

## 📖 Configuration Files

### `simple_factory.yml`

Minimal configuration for testing and development.

- **Use Case:** Quick testing, learning, development
- **Devices:** 3 Modbus TCP devices
- **Ports:** 15000-15002
- **Update Intervals:** 0.5s - 2.0s

### `large_factory.yml`

Production-scale simulation with multiple device types.

- **Use Case:** Load testing, integration testing, demos
- **Devices:** 50 Modbus TCP devices + 10 OPC-UA devices
- **Ports:** 15000-15050 (Modbus), 4840-4860 (OPC-UA)
- **Update Intervals:** 0.5s - 2.0s

### `full_factory.yml`

Complete multi-protocol factory with all three protocols.

- **Use Case:** Full integration testing, multi-protocol demos
- **Devices:** Modbus + MQTT + OPC-UA devices
- **Ports:** 15000+ (Modbus), 1883 (MQTT), 4840+ (OPC-UA)
- **Update Intervals:** 0.5s - 2.0s

## 🛠️ Configuration Structure

All configuration files follow this structure:

```yaml
facility:
  name: "Facility Name"
  description: "Description"

simulation:
  time_acceleration: 1.0 # Real-time

network:
  port_ranges:
    modbus: [start, end]
    opcua: [start, end]

industrial_protocols:
  modbus_tcp:
    enabled: true
    devices:
      device_type_name:
        count: N
        port_start: PORT
        device_template: "template_name"
        update_interval: SECONDS
        data_config:
          # Device-specific configuration

  opcua:
    enabled: true
    security_mode: "None"
    devices:
      device_type_name:
        count: N
        port_start: PORT
        device_template: "template_name"
        update_interval: SECONDS
        data_config:
          # Device-specific configuration
```

## 📊 Device Templates

### Temperature Sensor

```yaml
temperature_sensors:
  count: 5
  port_start: 15000
  device_template: "industrial_temperature_sensor"
  update_interval: 2.0
  data_config:
    temperature_range: [20, 40] # °C
    humidity_range: [30, 70] # %
```

### Pressure Transmitter

```yaml
pressure_transmitters:
  count: 3
  port_start: 15010
  device_template: "hydraulic_pressure_sensor"
  update_interval: 1.0
  data_config:
    pressure_range: [100, 250] # PSI
    flow_range: [10, 150] # L/min
```

### Motor Drive

```yaml
motor_drives:
  count: 4
  port_start: 15020
  device_template: "variable_frequency_drive"
  update_interval: 0.5
  data_config:
    speed_range: [1000, 3600] # RPM
    torque_range: [0, 500] # Nm
```

### OPC-UA Device Templates

### CNC Machine

```yaml
cnc_machines:
  count: 1
  port_start: 4840
  device_template: "opcua_cnc_machine"
  update_interval: 1.0
  data_config:
    spindle_speed_range: [0, 24000] # RPM
    feed_rate_range: [0, 15000] # mm/min
```

### PLC Controller

```yaml
plc_controllers:
  count: 1
  port_start: 4841
  device_template: "opcua_plc_controller"
  update_interval: 0.5
  data_config:
    process_value_range: [0, 100]
    setpoint: 50.0
```

### Industrial Robot

```yaml
industrial_robots:
  count: 1
  port_start: 4842
  device_template: "opcua_industrial_robot"
  update_interval: 0.5
  data_config:
    joint_count: 6
    max_speed_percent: 100
```

## 🧪 Testing Configurations

### Connect with Python (Modbus)

```python
from pymodbus.client import ModbusTcpClient

# Connect to device
client = ModbusTcpClient('localhost', 15000)
client.connect()

# Read data
result = client.read_holding_registers(0, 3)
temp = result.registers[0] / 100.0
humidity = result.registers[1] / 100.0
status = result.registers[2]

print(f"Temperature: {temp}°C")
print(f"Humidity: {humidity}%")
print(f"Status: {status}")

client.close()
```

### Connect with Python (OPC-UA)

```python
import asyncio
from asyncua import Client

async def main():
    client = Client("opc.tcp://localhost:4840/freeopcua/server/")
    async with client:
        # Read CNC machine spindle speed
        node = client.get_node("ns=2;s=SpindleSpeed")
        value = await node.read_value()
        print(f"Spindle Speed: {value} RPM")

asyncio.run(main())
```

### Check API Status

```bash
# Get status
curl http://localhost:8080/status | jq

# List devices
curl http://localhost:8080/devices | jq

# Get device data
curl http://localhost:8080/devices/modbus_temperature_sensors_000/data | jq
```

## 📝 Creating Custom Configurations

1. Copy an example configuration
2. Modify device counts and ports
3. Adjust data ranges for your use case
4. Run with your custom config:

```bash
docker run --rm \
  -v $(pwd)/my_config.yml:/config/factory.yml \
  -p 15000-15100:15000-15100 \
  -p 8080:8080 \
  universal-simulation-engine:latest
```

## 🔍 Configuration Validation

The simulator automatically validates your configuration on startup:

- Port range conflicts
- Device template validity
- Data range sanity checks
- Resource availability

Check logs for validation messages.

## 💡 Tips

### Port Allocation

- Reserve enough ports in `port_ranges` for all devices
- Use sequential `port_start` values for device groups
- Leave gaps between groups for expansion
- Modbus default range: 15000-15100
- OPC-UA default range: 4840-4940 (standard OPC-UA port is 4840)

### Performance

- Increase `update_interval` for better performance
- Reduce `count` if experiencing resource constraints
- Monitor port utilization via `/status` endpoint

### Realistic Data

- Set appropriate `*_range` values for your industry
- Temperature: Industrial ranges typically 0-100°C
- Pressure: Common ranges 0-300 PSI
- Speed: Motor speeds typically 0-3600 RPM

## 📚 More Examples

See the main [examples directory](../) for:

- Modbus client examples
- Monitoring scripts
- Data collection tools
- Integration examples

---

**Need help?** Check the [main README](../../README.md) or open an issue.
