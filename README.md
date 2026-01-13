# Universal Simulation Engine

**Open-Source Industrial Protocol & Device Simulation Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

Simulate industrial devices and protocols without hardware. Perfect for development, testing, training, and prototyping IoT/IIoT applications.

## 🚀 Quick Start

### Run with Docker (Recommended)

```bash
# Pull the image (when available on Docker Hub)
docker pull universal-simulation-engine:latest

# Run with example configuration
docker run --rm \
  -v $(pwd)/config.yml:/config/factory.yml \
  -p 15000-15010:15000-15010 \
  -p 8080:8080 \
  universal-simulation-engine:latest
```

### Build from Source

```bash
# Clone repository
git clone https://github.com/yourusername/universal-simulation-engine.git
cd universal-simulation-engine

# Build Docker image
docker build -t universal-simulation-engine:latest .

# Run with example config
docker run --rm \
  -v $(pwd)/examples/configs/simple_factory.yml:/config/factory.yml \
  -p 15000-15002:15000-15002 \
  -p 8080:8080 \
  universal-simulation-engine:latest
```

## ✨ Features

### Currently Supported

- ✅ **Modbus TCP** - Full protocol simulation with realistic device behavior
  - Temperature sensors (0.01°C resolution)
  - Pressure transmitters (0.01 PSI resolution)
  - Motor drives (VFDs with speed, torque, power)
  - Flow meters, level sensors, valve controllers
- ✅ **Configuration-Driven** - YAML-based device configuration
- ✅ **REST API** - Full REST API for monitoring and control
- ✅ **Realistic Data** - Industrial-grade data patterns with noise and correlation
- ✅ **Multi-Device** - Run 1 to 1000+ devices simultaneously
- ✅ **Port Management** - Automatic port allocation and conflict prevention

### Coming Soon

- 🔜 MQTT - IoT sensor networks
- 🔜 OPC-UA - Industrial automation standard
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
docker run --rm \
  -v $(pwd)/factory.yml:/config/factory.yml \
  -p 15000-15002:15000-15002 \
  -p 8080:8080 \
  universal-simulation-engine:latest
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

Access the web dashboard at `http://localhost:8080/dashboard` to:

- View live device status
- Monitor data in real-time
- Check system health
- View port utilization

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

## 📁 Project Structure

```
universal-simulation-engine/
├── src/                          # Source code
│   ├── protocols/               # Protocol implementations
│   │   └── industrial/
│   │       └── modbus/         # Modbus TCP simulator
│   ├── config_parser.py        # Configuration management
│   ├── orchestrator.py         # Main orchestrator
│   ├── port_manager.py         # Port allocation
│   └── data_patterns/          # Realistic data generation
├── examples/                    # Example configurations
│   └── configs/                # Ready-to-use configs
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests (25 tests)
│   ├── integration/            # Integration tests
│   └── smoke/                  # Docker deployment tests
├── config/                      # Default configuration
├── tools/                       # Utility tools
└── docs/                        # Documentation
```

**📚 Complete Documentation:**

- [📖 Documentation Index](docs/INDEX.md) - Complete navigation guide
- [📝 Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md) - What's been built
- [🔧 Modbus Protocol Guide](docs/protocols/modbus/README.md) - Detailed protocol docs
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

- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
- **Issue Tracker**: GitHub Issues
- **Docker Hub**: Coming soon

## 🙏 Acknowledgments

Built for the industrial IoT community to accelerate development and testing.

## 📧 Support

- GitHub Issues for bug reports
- Discussions for questions
- Email: support@example.com

---

**Status**: Production Ready - Modbus TCP Protocol ✅

**Version**: 0.1.0

**Last Updated**: January 2026
