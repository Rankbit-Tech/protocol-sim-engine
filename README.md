# Universal Simulation Engine

**Open-Source Industrial Protocol & Device Simulation Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/docker/v/developeryashsolanki/protocol-sim-engine?label=docker)](https://hub.docker.com/r/developeryashsolanki/protocol-sim-engine)
[![Docker Pulls](https://img.shields.io/docker/pulls/developeryashsolanki/protocol-sim-engine)](https://hub.docker.com/r/developeryashsolanki/protocol-sim-engine)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Image Size](https://img.shields.io/docker/image-size/developeryashsolanki/protocol-sim-engine/latest)](https://hub.docker.com/r/developeryashsolanki/protocol-sim-engine)

Simulate industrial devices and protocols without hardware. Perfect for development, testing, training, and prototyping IoT/IIoT applications.

## 🚀 Quick Start

### Run with Docker (Recommended)

The easiest way to get started is using the pre-built Docker image from Docker Hub:

```bash
# Pull the latest image
docker pull developeryashsolanki/protocol-sim-engine:latest

# Run with default configuration (Modbus + MQTT + OPC-UA devices)
docker run -d \
  --name protocol-sim \
  -p 8080:8080 \
  -p 1883:1883 \
  -p 15000-15002:15000-15002 \
  -p 4840-4850:4840-4850 \
  developeryashsolanki/protocol-sim-engine:latest

# Access the API
curl http://localhost:8080/health

# View API documentation
open http://localhost:8080/docs
```

**What you get out of the box:**

- ✅ 3 pre-configured Modbus TCP devices
- ✅ Temperature sensor on port 15000
- ✅ Pressure transmitter on port 15001
- ✅ Motor drive (VFD) on port 15002
- ✅ 10 MQTT IoT devices (sensors, meters, trackers)
- ✅ **Embedded MQTT broker** (no external broker needed!)
- ✅ 3 OPC-UA devices (CNC machine, PLC controller, industrial robot)
- ✅ OPC-UA servers on ports 4840-4842
- ✅ REST API on port 8080
- ✅ Interactive API docs at `/docs`
- ✅ Health monitoring at `/health`

### Run with Custom Configuration

```bash
# Run with your own config file
docker run -d \
  --name protocol-sim \
  -v $(pwd)/my-config.yml:/config/factory.yml \
  -p 8080:8080 \
  -p 15000-15010:15000-15010 \
  developeryashsolanki/protocol-sim-engine:latest
```

### Available Docker Tags

- `latest` - Latest stable release
- `0.4.0` - Current version with OPC-UA support
- `0.3.0` - React frontend migration
- `0.2.0` - Previous stable version
- `0.1.0` - Initial release

```bash
# Use specific version for production
docker pull developeryashsolanki/protocol-sim-engine:0.4.0
```

### Build from Source (Optional)

Only needed if you want to modify the code:

```bash
# Clone repository
git clone https://github.com/Rankbit-Tech/protocol-sim-engine.git
cd protocol-sim-engine

# Build Docker image
docker build -t protocol-sim-engine:dev .

# Run your custom build
docker run -d \
  --name protocol-sim-dev \
  -p 8080:8080 \
  -p 15000-15002:15000-15002 \
  protocol-sim-engine:dev
```

## 🐳 Docker Usage Guide

### Basic Commands

```bash
# Pull latest image
docker pull developeryashsolanki/protocol-sim-engine:latest

# Start container
docker run -d --name protocol-sim \
  -p 8080:8080 -p 15000-15002:15000-15002 \
  -p 1883:1883 -p 4840-4850:4840-4850 \
  developeryashsolanki/protocol-sim-engine:latest

# View logs
docker logs protocol-sim

# Follow logs in real-time
docker logs -f protocol-sim

# Stop container
docker stop protocol-sim

# Start stopped container
docker start protocol-sim

# Remove container
docker rm protocol-sim

# View container stats
docker stats protocol-sim
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  protocol-sim:
    image: developeryashsolanki/protocol-sim-engine:latest
    container_name: protocol-sim
    ports:
      - "8080:8080"
      - "15000-15010:15000-15010"
      - "1883:1883"
      - "4840-4850:4840-4850"
    volumes:
      - ./config.yml:/config/factory.yml
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

Run with Docker Compose:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment

For production environments:

```bash
# Use specific version tag
docker run -d \
  --name protocol-sim-prod \
  --restart=always \
  --memory="1g" \
  --cpus="2" \
  -p 8080:8080 \
  -p 15000-15010:15000-15010 \
  -v /opt/config/factory.yml:/config/factory.yml \
  -v /var/log/protocol-sim:/app/logs \
  developeryashsolanki/protocol-sim-engine:0.4.0

# Check health
curl http://localhost:8080/health
```

### Environment Variables

```bash
# Run with environment variables
docker run -d \
  --name protocol-sim \
  -e LOG_LEVEL=INFO \
  -e TIME_ACCELERATION=1.0 \
  -p 8080:8080 \
  -p 15000-15002:15000-15002 \
  -p 1883:1883 \
  -p 4840-4850:4840-4850 \
  developeryashsolanki/protocol-sim-engine:latest
```

### Network Configuration

```bash
# Create custom network
docker network create industrial-net

# Run on custom network
docker run -d \
  --name protocol-sim \
  --network industrial-net \
  -p 8080:8080 \
  -p 15000-15002:15000-15002 \
  -p 1883:1883 \
  -p 4840-4850:4840-4850 \
  developeryashsolanki/protocol-sim-engine:latest
```

## ✨ Features

### Currently Supported

- ✅ **Modbus TCP** - Full protocol simulation with realistic device behavior
  - Temperature sensors (0.01°C resolution)
  - Pressure transmitters (0.01 PSI resolution)
  - Motor drives (VFDs with speed, torque, power)
  - Flow meters, level sensors, valve controllers
- ✅ **MQTT** - IoT sensor networks with embedded broker
  - Environmental sensors (temperature, humidity, air quality)
  - Smart energy meters (voltage, current, power)
  - Asset trackers (zone tracking, battery level)
  - **Embedded MQTT broker** - No external broker required!
  - Configurable QoS levels (0, 1, 2)
  - Custom topic hierarchies
- ✅ **OPC-UA** - Industrial automation standard with structured address space
  - CNC machine monitors (spindle speed, feed rate, tool wear, axis positions)
  - PLC process controllers (PID control, setpoints, alarms)
  - Industrial robots (joint angles, TCP position, cycle time, payload)
  - Hierarchical node structure (DeviceSet/Identification/Parameters/Status)
  - Compatible with standard OPC-UA clients (UaExpert, Prosys, asyncua)
- ✅ **Configuration-Driven** - YAML-based device configuration
- ✅ **REST API** - Full REST API for monitoring and control
- ✅ **Realistic Data** - Industrial-grade data patterns with noise and correlation
- ✅ **Multi-Device** - Run 1 to 1000+ devices simultaneously
- ✅ **Port Management** - Automatic port allocation and conflict prevention

### Coming Soon

- 🔜 Ethernet/IP - Allen-Bradley PLCs
- 🔜 BLE/Bluetooth - Asset tracking and wearables
- 🔜 CCTV/RTSP - Security camera simulation

## 📖 Usage Examples

### Simple Factory (3 Devices)

Create `factory.yml`:

```yaml
facility:
  name: "My Test Factory"
  description: "Simple test facility"

simulation:
  time_acceleration: 1.0

network:
  port_ranges:
    modbus: [15000, 15100]

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
          temperature_range: [20, 35]
          humidity_range: [40, 70]

      pressure_transmitters:
        count: 1
        port_start: 15001
        device_template: "hydraulic_pressure_sensor"
        update_interval: 1.0
        data_config:
          pressure_range: [100, 200]
          flow_range: [10, 150]

      motor_drives:
        count: 1
        port_start: 15002
        device_template: "variable_frequency_drive"
        update_interval: 0.5
        data_config:
          speed_range: [1000, 3000]
          torque_range: [0, 500]
```

Run:

```bash
docker run -d \
  --name my-factory \
  -v $(pwd)/factory.yml:/config/factory.yml \
  -p 8080:8080 \
  -p 15000-15002:15000-15002 \
  developeryashsolanki/protocol-sim-engine:latest

# Check it's running
curl http://localhost:8080/health
```

### MQTT IoT Sensors

The simulator includes a **built-in MQTT broker** - no external broker needed!

```yaml
# Add to your factory.yml
industrial_protocols:
  mqtt:
    enabled: true
    use_embedded_broker: true # Built-in broker, no setup needed!
    broker_port: 1883
    devices:
      environmental_sensors:
        count: 5
        device_template: "iot_environmental_sensor"
        base_topic: "factory/sensors"
        publish_interval: 5.0
        qos: 1
        data_config:
          temperature_range: [18, 35]
          humidity_range: [30, 80]

      energy_meters:
        count: 3
        device_template: "smart_meter"
        base_topic: "factory/energy"
        publish_interval: 10.0
        qos: 1
```

Run and subscribe to messages:

```bash
# Run simulator (broker starts automatically)
docker run -d \
  --name iot-sim \
  -p 8080:8080 \
  -p 1883:1883 \
  developeryashsolanki/protocol-sim-engine:latest

# Subscribe to all factory messages (using any MQTT client)
mosquitto_sub -h localhost -t "factory/#" -v
```

**Using an external broker instead:**

```yaml
industrial_protocols:
  mqtt:
    enabled: true
    use_embedded_broker: false # Use your own broker
    broker_host: "my-broker.example.com"
    broker_port: 1883
```

### OPC-UA Devices

The simulator runs dedicated OPC-UA servers for each device with structured address spaces.

```yaml
# Add to your factory.yml
industrial_protocols:
  opcua:
    enabled: true
    security_mode: "None"
    security_policy: "None"
    application_uri: "urn:protocol-sim-engine:opcua:server"
    devices:
      cnc_machines:
        count: 1
        port_start: 4840
        device_template: "opcua_cnc_machine"
        update_interval: 1.0
        data_config:
          spindle_speed_range: [0, 24000]
          feed_rate_range: [0, 15000]

      plc_controllers:
        count: 1
        port_start: 4841
        device_template: "opcua_plc_controller"
        update_interval: 0.5
        data_config:
          process_value_range: [0, 100]
          setpoint: 50.0

      industrial_robots:
        count: 1
        port_start: 4842
        device_template: "opcua_industrial_robot"
        update_interval: 0.5
        data_config:
          joint_count: 6
          max_speed_percent: 100
```

Connect with an OPC-UA client:

```python
import asyncio
from asyncua import Client

async def main():
    client = Client("opc.tcp://localhost:4840/freeopcua/server/")
    async with client:
        # Browse the address space
        root = client.nodes.root
        objects = await root.get_children()
        print("Root children:", objects)

        # Read a specific node value
        node = client.get_node("ns=2;s=SpindleSpeed")
        value = await node.read_value()
        print(f"Spindle Speed: {value} RPM")

asyncio.run(main())
```

### Test Modbus Connectivity

```python
from pymodbus.client import ModbusTcpClient

# Connect to temperature sensor
client = ModbusTcpClient('localhost', 15000)
client.connect()

# Read temperature (register 40001, scaled by 100)
result = client.read_holding_registers(0, 1)
temperature = result.registers[0] / 100.0
print(f"Temperature: {temperature}°C")

client.close()
```

## 🔧 API Endpoints

Once running, access the API at `http://localhost:8080`:

- **GET /status** - System status and device count
- **GET /devices** - List all devices
- **GET /devices/{id}** - Get device details
- **GET /devices/{id}/data** - Get current device data
- **GET /protocols** - List active protocols
- **GET /health** - Health check
- **GET /docs** - Interactive API documentation

**MQTT-specific endpoints:**

- **GET /mqtt/broker** - MQTT broker status (embedded: true/false)
- **GET /mqtt/topics** - All active MQTT topics
- **GET /mqtt/devices/{id}/messages** - Recent messages from device

**OPC-UA-specific endpoints:**

- **GET /opcua/servers** - List all OPC-UA server endpoints and status
- **GET /opcua/devices/{id}/nodes** - Current node values for a device

Example:

```bash
# Check status
curl http://localhost:8080/status

# List all devices
curl http://localhost:8080/devices

# Get device data
curl http://localhost:8080/devices/modbus_temperature_sensors_000/data
```

## 🧪 Testing

```bash
# Run all tests
./run_all_tests.sh

# Run specific tests
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
```

## 📊 Monitoring Dashboard

Access the web dashboard at `http://localhost:8080`:

**Dashboard** (`/dashboard`)

- System status overview (device count, protocols, health, uptime)
- Protocol list with device counts and status indicators
- Device list with real-time status

**Data Monitor** (`/data-monitor`)

- Real-time telemetry streaming from all devices
- Multi-select device filter with checkboxes
- Configurable refresh rates (1s, 2s, 5s, 10s)
- Pause/resume data streaming
- Export logs as text file

The frontend is built with React, TypeScript, and shadcn/ui components.

## 🛠️ Configuration Reference

### Device Templates

#### Temperature Sensor

```yaml
device_template: "industrial_temperature_sensor"
data_config:
  temperature_range: [min, max] # °C
  humidity_range: [min, max] # %
```

**Modbus Registers:**

- HR[40001]: Temperature (scaled × 100)
- HR[40002]: Humidity (scaled × 100)
- HR[40003]: Status (0=OK)
- DI[10001]: Sensor healthy (bool)

#### Pressure Transmitter

```yaml
device_template: "hydraulic_pressure_sensor"
data_config:
  pressure_range: [min, max] # PSI
  flow_range: [min, max] # L/min
```

**Modbus Registers:**

- HR[40001]: Pressure (scaled × 100)
- HR[40002]: Flow rate (scaled × 100)
- DI[10001]: High pressure alarm
- DI[10002]: Low flow alarm

#### Motor Drive (VFD)

```yaml
device_template: "variable_frequency_drive"
data_config:
  speed_range: [min, max] # RPM
  torque_range: [min, max] # Nm
```

**Modbus Registers:**

- HR[40001]: Speed (RPM)
- HR[40002]: Torque (scaled × 100)
- HR[40003]: Power (scaled × 100)
- HR[40004]: Fault code

### MQTT Device Templates

#### Environmental Sensor

```yaml
device_template: "iot_environmental_sensor"
base_topic: "factory/sensors"
publish_interval: 5.0 # seconds
qos: 1
data_config:
  temperature_range: [18, 35]
  humidity_range: [30, 80]
```

**MQTT Message (JSON):**

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
    "pressure_hpa": 1013.25
  }
}
```

#### Smart Energy Meter

```yaml
device_template: "smart_meter"
base_topic: "factory/energy"
publish_interval: 10.0
qos: 1
```

**MQTT Message (JSON):**

```json
{
  "device_id": "mqtt_energy_meters_000",
  "device_type": "energy_meter",
  "data": {
    "voltage_v": 231.4,
    "current_a": 32.1,
    "power_kw": 6.52,
    "power_factor": 0.88,
    "energy_kwh": 10000.0
  }
}
```

#### Asset Tracker

```yaml
device_template: "asset_tracker"
base_topic: "factory/assets"
publish_interval: 30.0
qos: 0
data_config:
  zone_ids: ["zone_a", "zone_b", "warehouse"]
```

### OPC-UA Device Templates

#### CNC Machine Monitor

```yaml
device_template: "opcua_cnc_machine"
port_start: 4840
update_interval: 1.0
data_config:
  spindle_speed_range: [0, 24000] # RPM
  feed_rate_range: [0, 15000] # mm/min
```

**OPC-UA Nodes:**

- `SpindleSpeed` (Double, RPM)
- `FeedRate` (Double, mm/min)
- `ToolWearPercent` (Double, 0-100%)
- `PartCount` (Int32)
- `AxisPosition_X/Y/Z` (Double, mm)
- `ProgramName` (String)
- `MachineState` (String: IDLE/RUNNING/ERROR/SETUP)

#### PLC Process Controller

```yaml
device_template: "opcua_plc_controller"
port_start: 4841
update_interval: 0.5
data_config:
  process_value_range: [0, 100]
  setpoint: 50.0
```

**OPC-UA Nodes:**

- `ProcessValue` (Double)
- `Setpoint` (Double)
- `ControlOutput` (Double, 0-100%)
- `Mode` (String: AUTO/MANUAL/CASCADE)
- `HighAlarm` / `LowAlarm` (Boolean)
- `IntegralTerm` / `DerivativeTerm` (Double)

#### Industrial Robot

```yaml
device_template: "opcua_industrial_robot"
port_start: 4842
update_interval: 0.5
data_config:
  joint_count: 6
  max_speed_percent: 100
```

**OPC-UA Nodes:**

- `JointAngle_1` through `JointAngle_6` (Double, degrees)
- `TCPPosition_X/Y/Z` (Double, mm)
- `TCPOrientation_Rx/Ry/Rz` (Double, degrees)
- `ProgramState` (String: RUNNING/PAUSED/STOPPED)
- `CycleTime` (Double, seconds)
- `CycleCount` (Int32)
- `PayloadKg` (Double)
- `SpeedPercent` (Double, 0-100%)

## 📁 Project Structure

```
universal-simulation-engine/
├── src/                          # Python backend
│   ├── protocols/               # Protocol implementations
│   │   └── industrial/
│   │       ├── modbus/         # Modbus TCP simulator
│   │       ├── mqtt/           # MQTT simulator + embedded broker
│   │       └── opcua/          # OPC-UA simulator + servers
│   ├── config_parser.py        # Configuration management
│   ├── orchestrator.py         # Main orchestrator
│   ├── port_manager.py         # Port allocation
│   └── data_patterns/          # Realistic data generation
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── ui/            # shadcn/ui components
│   │   │   ├── Dashboard.tsx  # Main dashboard
│   │   │   └── DataMonitor.tsx # Real-time monitor
│   │   ├── lib/               # API client & utilities
│   │   └── types/             # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── examples/                    # Example configurations
│   └── configs/                # Ready-to-use configs
├── tests/                       # Test suite
├── config/                      # Default configuration
├── tools/                       # Utility tools
└── docs/                        # Documentation
```

**📚 Complete Documentation:**

- [📖 Documentation Index](docs/INDEX.md) - Complete navigation guide
- [📝 Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md) - What's been built
- [🔧 Modbus Protocol Guide](docs/protocols/modbus/README.md) - Detailed Modbus docs
- [📡 MQTT Protocol Guide](docs/protocols/mqtt/README.md) - MQTT & IoT device docs
- [🏭 OPC-UA Protocol Guide](docs/protocols/opcua/README.md) - OPC-UA device & server docs
- [⚙️ Configuration Examples](examples/configs/README.md) - Ready-to-use configs
- [🛠️ Tools Guide](tools/README.md) - Utility tools

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run linter
poetry run ruff check src/
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Docker Hub**: [developeryashsolanki/protocol-sim-engine](https://hub.docker.com/r/developeryashsolanki/protocol-sim-engine)
- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
- **GitHub**: [Rankbit-Tech/protocol-sim-engine](https://github.com/Rankbit-Tech/protocol-sim-engine)
- **Issue Tracker**: [GitHub Issues](https://github.com/Rankbit-Tech/protocol-sim-engine/issues)

## 🙏 Acknowledgments

Built for the industrial IoT community to accelerate development and testing.

## 📧 Support

- GitHub Issues for bug reports
- Discussions for questions
- Email: yash.solanki@rankbit.tech

---

**Status**: Production Ready - Modbus TCP ✅ | MQTT ✅ | OPC-UA ✅ | React Frontend ✅

**Version**: 0.4.0

**Last Updated**: February 2026
