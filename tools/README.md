# Utility Tools

Helper scripts for working with the Universal Simulation Engine.

## 🛠️ Available Tools

### `validate_data.py`

Validate device data and check for realistic patterns.

```bash
# Validate all devices
python tools/validate_data.py --host localhost --port-start 15000 --port-end 15010

# Validate specific device
python tools/validate_data.py --host localhost --port 15000 --device-type temperature

# Continuous monitoring
python tools/validate_data.py --host localhost --port 15000 --continuous --interval 5
```

**Options:**

- `--host`: Modbus server host (default: localhost)
- `--port`: Single port to test
- `--port-start`/`--port-end`: Port range to test
- `--device-type`: Expected device type (temperature, pressure, motor)
- `--continuous`: Run continuously
- `--interval`: Update interval in seconds (default: 5)

## 📊 Monitoring Scripts

### Monitor Devices (Example)

See `examples/monitoring/monitor_devices.py` for real-time monitoring example.

```bash
python examples/monitoring/monitor_devices.py
```

### OPC-UA Client Example

Connect to OPC-UA devices and read node values:

```python
import asyncio
from asyncua import Client

async def main():
    # Connect to CNC machine on port 4840
    client = Client("opc.tcp://localhost:4840/freeopcua/server/")
    async with client:
        # Read spindle speed
        node = client.get_node("ns=2;s=SpindleSpeed")
        value = await node.read_value()
        print(f"Spindle Speed: {value} RPM")

        # Read tool wear
        node = client.get_node("ns=2;s=ToolWearPercent")
        value = await node.read_value()
        print(f"Tool Wear: {value}%")

asyncio.run(main())
```

## 🧪 Testing Tools

### Integration Test

Test Modbus connectivity to Docker container:

```bash
python tests/integration/test_docker_connectivity.py
```

### Smoke Test

Test complete Docker deployment:

```bash
python tests/smoke/test_docker_deployment.py
```

## 📝 Custom Tool Development

### Template

```python
#!/usr/bin/env python3
"""Custom tool description"""

from pymodbus.client import ModbusTcpClient
import time

def main():
    # Connect to device
    client = ModbusTcpClient('localhost', 15000)
    if not client.connect():
        print("Failed to connect")
        return

    # Read and process data
    result = client.read_holding_registers(0, 10)
    if not result.isError():
        # Process registers
        for i, value in enumerate(result.registers):
            print(f"Register {i}: {value}")

    client.close()

if __name__ == "__main__":
    main()
```

## 🔧 Common Operations

### Read Device Data

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('localhost', 15000)
client.connect()

# Read temperature (scaled by 100)
result = client.read_holding_registers(0, 1)
temperature = result.registers[0] / 100.0
print(f"Temperature: {temperature}°C")

client.close()
```

### Monitor Multiple Devices

```python
import time
from pymodbus.client import ModbusTcpClient

devices = [
    ('localhost', 15000, 'Temperature Sensor'),
    ('localhost', 15001, 'Pressure Transmitter'),
    ('localhost', 15002, 'Motor Drive'),
]

while True:
    for host, port, name in devices:
        client = ModbusTcpClient(host, port)
        if client.connect():
            result = client.read_holding_registers(0, 3)
            if not result.isError():
                print(f"{name} ({port}): {result.registers}")
            client.close()

    time.sleep(5)
```

### Data Collection

```python
import csv
import time
from pymodbus.client import ModbusTcpClient
from datetime import datetime

client = ModbusTcpClient('localhost', 15000)
client.connect()

with open('data.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Timestamp', 'Temperature', 'Humidity', 'Status'])

    for _ in range(100):
        result = client.read_holding_registers(0, 3)
        if not result.isError():
            timestamp = datetime.now().isoformat()
            temp = result.registers[0] / 100.0
            humidity = result.registers[1] / 100.0
            status = result.registers[2]
            writer.writerow([timestamp, temp, humidity, status])

        time.sleep(1)

client.close()
```

## 📚 API Tool Examples

### Check System Status

```bash
curl http://localhost:8080/status | jq
```

### List All Devices

```bash
curl http://localhost:8080/devices | jq '.devices[] | {id: .device_id, type: .device_type, port: .port}'
```

### Get Device Data

```bash
# Get specific device data
curl http://localhost:8080/devices/modbus_temperature_sensors_000/data | jq

# Get all devices data
curl http://localhost:8080/devices | jq '.devices[] | .device_id' | while read id; do
  echo "Device: $id"
  curl -s http://localhost:8080/devices/$id/data | jq
  echo ""
done
```

### List OPC-UA Servers

```bash
curl http://localhost:8080/opcua/servers | jq
```

### Get OPC-UA Device Nodes

```bash
curl http://localhost:8080/opcua/devices/opcua_cnc_machines_000/nodes | jq
```

### Monitor Health

```bash
# Continuous health monitoring
watch -n 5 'curl -s http://localhost:8080/health | jq'
```

## 🔍 Debugging Tools

### Port Scanner

Check which Modbus ports are responding:

```bash
for port in {15000..15010}; do
  timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null && echo "Port $port: OPEN"
done
```

Check which OPC-UA ports are responding:

```bash
for port in {4840..4850}; do
  timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null && echo "Port $port: OPEN (OPC-UA)"
done
```

### Register Dump

Dump all holding registers from a device:

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('localhost', 15000)
client.connect()

# Read first 100 holding registers
result = client.read_holding_registers(0, 100)
if not result.isError():
    for i, value in enumerate(result.registers):
        print(f"HR[{40001+i}]: {value}")

client.close()
```

## 💡 Tips

- Use `--help` flag on any tool for detailed usage
- Check tool exit codes for automation (`$?` in bash)
- Log output with `tee` for debugging: `tool.py | tee output.log`
- Use `watch` command for live monitoring
- Combine with `jq` for JSON processing

## 📖 Additional Resources

- [Main README](../README.md)
- [Configuration Examples](../examples/configs/README.md)
- [Protocol Documentation](../docs/protocols/)

---

**Need a specific tool?** Open an issue with your use case. run: sleep 15
