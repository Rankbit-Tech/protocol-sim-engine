# Modbus TCP Protocol Documentation

Complete reference for Modbus TCP device simulation in the Universal Simulation Engine.

## 📋 Overview

The Modbus TCP simulator provides full-featured industrial device simulation with:

- ✅ **Protocol Compliance** - Full Modbus TCP standard implementation
- ✅ **Realistic Behavior** - Industrial-grade data patterns with noise
- ✅ **Multiple Device Types** - Temperature, pressure, motor drives, and more
- ✅ **Scalability** - Support for 1000+ concurrent devices
- ✅ **Auto-configuration** - YAML-based device definition

## 🚀 Quick Start

### Basic Configuration

```yaml
industrial_protocols:
  modbus_tcp:
    enabled: true
    devices:
      temperature_sensors:
        count: 1
        port_start: 15000
        device_template: "industrial_temperature_sensor"
        update_interval: 2.0
        data_config:
          temperature_range: [20, 40]
          humidity_range: [30, 70]
```

### Connect and Read

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('localhost', 15000)
client.connect()

# Read temperature (HR 40001)
result = client.read_holding_registers(0, 1)
temperature = result.registers[0] / 100.0
print(f"Temperature: {temperature}°C")

client.close()
```

## 📊 Device Types

### Temperature Sensor

**Template:** `industrial_temperature_sensor`

**Configuration:**

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

**Modbus Registers:**

| Address | Type | Name        | Units | Scaling | Description          |
| ------- | ---- | ----------- | ----- | ------- | -------------------- |
| 40001   | HR   | Temperature | °C    | ×100    | Current temperature  |
| 40002   | HR   | Humidity    | %     | ×100    | Current humidity     |
| 40003   | HR   | Status      | -     | 1       | Sensor status (0=OK) |
| 10001   | DI   | Healthy     | bool  | -       | Sensor health flag   |

**Python Example:**

```python
result = client.read_holding_registers(0, 3)
temp = result.registers[0] / 100.0      # °C
humidity = result.registers[1] / 100.0  # %
status = result.registers[2]            # 0 = OK

discrete = client.read_discrete_inputs(0, 1)
healthy = discrete.bits[0]              # True/False
```

### Pressure Transmitter

**Template:** `hydraulic_pressure_sensor`

**Configuration:**

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

**Modbus Registers:**

| Address | Type | Name       | Units | Scaling | Description         |
| ------- | ---- | ---------- | ----- | ------- | ------------------- |
| 40001   | HR   | Pressure   | PSI   | ×100    | Current pressure    |
| 40002   | HR   | Flow Rate  | L/min | ×100    | Current flow rate   |
| 40003   | HR   | Status     | -     | 1       | Sensor status       |
| 10001   | DI   | High Alarm | bool  | -       | Pressure high alarm |
| 10002   | DI   | Low Flow   | bool  | -       | Low flow alarm      |

**Python Example:**

```python
result = client.read_holding_registers(0, 2)
pressure = result.registers[0] / 100.0   # PSI
flow = result.registers[1] / 100.0       # L/min

alarms = client.read_discrete_inputs(0, 2)
high_pressure = alarms.bits[0]
low_flow = alarms.bits[1]
```

### Motor Drive (VFD)

**Template:** `variable_frequency_drive`

**Configuration:**

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

**Modbus Registers:**

| Address | Type | Name       | Units | Scaling | Description       |
| ------- | ---- | ---------- | ----- | ------- | ----------------- |
| 40001   | HR   | Speed      | RPM   | 1       | Motor speed       |
| 40002   | HR   | Torque     | Nm    | ×100    | Output torque     |
| 40003   | HR   | Power      | kW    | ×100    | Power consumption |
| 40004   | HR   | Fault Code | -     | 1       | Fault code (0=OK) |

**Python Example:**

```python
result = client.read_holding_registers(0, 4)
speed = result.registers[0]              # RPM
torque = result.registers[1] / 100.0     # Nm
power = result.registers[2] / 100.0      # kW
fault = result.registers[3]              # 0 = OK
```

## 🔧 Configuration Options

### Global Settings

```yaml
industrial_protocols:
  modbus_tcp:
    enabled: true # Enable/disable protocol
    devices:# Device definitions
      # ... device configurations
```

### Device Configuration

```yaml
device_group_name:
  count: N # Number of devices
  port_start: PORT # Starting port
  device_template: "template_name" # Device template
  update_interval: SECONDS # Data update frequency
  data_config:# Template-specific config
    # ... depends on device type
```

### Data Configuration

Each device template has specific `data_config` options:

**Temperature Sensor:**

- `temperature_range`: [min, max] in °C
- `humidity_range`: [min, max] in %

**Pressure Transmitter:**

- `pressure_range`: [min, max] in PSI
- `flow_range`: [min, max] in L/min

**Motor Drive:**

- `speed_range`: [min, max] in RPM
- `torque_range`: [min, max] in Nm

## 📈 Data Patterns

### Realistic Behavior

All simulated data includes:

- **Gaussian Noise**: ±0.1-0.5% random variation
- **Time Correlation**: Values change gradually, not instantly
- **Industrial Limits**: Proper range clamping
- **Sensor Drift**: Small long-term drift simulation

### Example Data Output

```
Temperature Sensor (Port 15000):
  Time 0s:  temp=25.32°C, humidity=55.2%
  Time 2s:  temp=25.38°C, humidity=55.0%
  Time 4s:  temp=25.29°C, humidity=55.3%
  Time 6s:  temp=25.41°C, humidity=54.9%
```

## 🧪 Testing

### Basic Connectivity Test

```python
from pymodbus.client import ModbusTcpClient

def test_connection(host, port):
    client = ModbusTcpClient(host, port)
    if client.connect():
        print(f"✅ Connected to {host}:{port}")
        client.close()
        return True
    print(f"❌ Failed to connect to {host}:{port}")
    return False

# Test multiple devices
for port in range(15000, 15003):
    test_connection('localhost', port)
```

### Data Validation Test

```python
def validate_temperature_sensor(host, port):
    client = ModbusTcpClient(host, port)
    client.connect()

    # Read multiple times
    readings = []
    for _ in range(10):
        result = client.read_holding_registers(0, 2)
        temp = result.registers[0] / 100.0
        readings.append(temp)
        time.sleep(0.5)

    # Verify realistic variation
    assert min(readings) >= 18  # Min range
    assert max(readings) <= 45  # Max range
    assert len(set(readings)) > 5  # Has variation

    client.close()
    print("✅ Temperature sensor validation passed")
```

## 🐛 Troubleshooting

### Connection Issues

**Problem:** Cannot connect to Modbus device

**Solutions:**

- Verify port is in range specified in configuration
- Check Docker port mapping: `-p 15000-15010:15000-15010`
- Ensure device started successfully (check logs)
- Test with: `telnet localhost 15000`

### Data Issues

**Problem:** Register values seem incorrect

**Solutions:**

- Check scaling factors (temperature/pressure ×100)
- Verify register address (0-based in pymodbus, 40001+ in docs)
- Read enough registers for complete data
- Check device type matches configuration

### Performance Issues

**Problem:** Slow response or timeouts

**Solutions:**

- Reduce `update_interval` in configuration
- Limit concurrent connections
- Increase timeout in client: `ModbusTcpClient(timeout=5)`
- Monitor system resources

## 📚 Advanced Topics

### Multiple Devices

```python
devices = [
    ('localhost', 15000, 'temperature'),
    ('localhost', 15001, 'pressure'),
    ('localhost', 15002, 'motor'),
]

clients = {}
for host, port, dtype in devices:
    client = ModbusTcpClient(host, port)
    if client.connect():
        clients[dtype] = client

# Use clients...
# Remember to close all
for client in clients.values():
    client.close()
```

### Continuous Monitoring

```python
import time
from datetime import datetime

client = ModbusTcpClient('localhost', 15000)
client.connect()

try:
    while True:
        result = client.read_holding_registers(0, 3)
        timestamp = datetime.now().isoformat()
        temp = result.registers[0] / 100.0

        print(f"{timestamp} - Temperature: {temp}°C")
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    client.close()
```

### Data Logging

```python
import csv
from datetime import datetime

with open('sensor_data.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Timestamp', 'Temperature', 'Humidity'])

    client = ModbusTcpClient('localhost', 15000)
    client.connect()

    for _ in range(100):
        result = client.read_holding_registers(0, 2)
        timestamp = datetime.now().isoformat()
        temp = result.registers[0] / 100.0
        humidity = result.registers[1] / 100.0

        writer.writerow([timestamp, temp, humidity])
        time.sleep(1)

    client.close()
```

## 🔗 References

- **Modbus Specification**: [modbus.org](https://modbus.org)
- **PyModbus Documentation**: [pymodbus.readthedocs.io](https://pymodbus.readthedocs.io)
- **Main Documentation**: [../../README.md](../../README.md)
- **Configuration Examples**: [../../../examples/configs/README.md](../../../examples/configs/README.md)

---

**Protocol Status**: ✅ Production Ready

**Last Updated**: January 2026
