# Universal Simulation Engine - Documentation Index

**Complete documentation for the Universal Simulation Engine**

Last Updated: February 10, 2026

---

## 📚 Table of Contents

### 🚀 Getting Started

1. [Quick Start Guide](../README.md#-quick-start) - Get running in 5 minutes
2. [Installation Guide](../README.md#build-from-source) - Build from source
3. [First Factory Setup](tutorials/first_factory.md) - Step-by-step tutorial
4. [Configuration Basics](configuration/basics.md) - Understanding YAML configs

### 📖 Core Documentation

#### Protocol Guides

- [Modbus TCP Protocol](protocols/modbus/README.md) - Complete Modbus implementation
  - Device types, register mappings, examples
  - Testing guide, troubleshooting
- [MQTT Protocol](protocols/mqtt/README.md) - IoT sensor simulation
  - Environmental sensors, energy meters, asset trackers
  - **Built-in MQTT broker** (no external setup needed)
  - Configurable QoS, topics, publish intervals
- [OPC-UA Protocol](protocols/opcua/README.md) - Industrial automation (CNC, PLC, Robot)
  - CNC machine monitors, PLC process controllers, industrial robots
  - Dedicated OPC-UA servers with structured address spaces
  - Compatible with standard OPC-UA clients

#### Configuration Reference

- [Configuration Schema](configuration/schema.md) - Complete YAML reference
- [Device Templates](configuration/device_templates.md) - Available device types
- [Network Settings](configuration/network.md) - Port management and allocation
- [Data Patterns](configuration/data_patterns.md) - Realistic data generation

#### Architecture & Design

- [System Architecture](architecture/system_design.md) - Overall system design
- [Orchestrator Engine](architecture/orchestrator.md) - Core coordination
- [Port Management](architecture/port_manager.md) - Automatic port allocation
- [Data Generation](architecture/data_generation.md) - Realistic patterns

### 💻 API Reference

- [REST API Guide](api/rest_api.md) - Complete API documentation
- [Web Dashboard](api/web_dashboard.md) - Monitoring interface
- [Data Monitor](api/data_monitor.md) - Real-time data streaming
- [Python SDK](api/python_sdk.md) - Coming soon

### 📝 Examples & Tutorials

#### Quick Start Examples

- [Simple Factory](../examples/configs/README.md#simple-factory-3-devices) - 3 devices
- [Large Factory](../examples/configs/README.md#large-factory-100-devices) - 100 devices
- [Automotive Plant](../examples/automotive_plant/README.md) - Complete example
- [Smart Building](../examples/smart_building/README.md) - BMS simulation

#### Code Examples

- [Modbus Quick Start](../examples/modbus/quick_start.py) - Python client
- [Monitor Devices](../examples/monitoring/monitor_devices.py) - Real-time monitoring
- [Custom Protocols](examples/custom_protocol.md) - Extend the platform

#### Tutorials

- [Your First Factory](tutorials/first_factory.md) - Complete walkthrough
- [Testing Industrial Apps](tutorials/testing_guide.md) - Use simulators for testing
- [Scaling to 1000+ Devices](tutorials/scaling.md) - Performance optimization
- [Docker Deployment](tutorials/docker_deployment.md) - Production setup

### 🧪 Testing & Development

- [Testing Guide](../tests/README.md) - Running tests
- [Unit Tests](testing/unit_tests.md) - Test structure
- [Integration Tests](testing/integration_tests.md) - Multi-protocol testing
- [Development Setup](development/setup.md) - Developer environment
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute

### 🛠️ Tools & Utilities

- [Tools Overview](../tools/README.md) - Available utilities
- [Data Validation](../tools/validate_data.py) - Validate device data
- [Configuration Generator](tools/config_generator.md) - Auto-generate configs
- [Protocol Analyzer](tools/protocol_analyzer.md) - Debug protocols

### 🐛 Troubleshooting

- [Common Issues](troubleshooting/common_issues.md) - FAQ and solutions
- [Port Conflicts](troubleshooting/port_conflicts.md) - Resolving port issues
- [Docker Problems](troubleshooting/docker.md) - Container troubleshooting
- [Protocol Debugging](troubleshooting/protocol_debug.md) - Debug connections

### 📦 Deployment

- [Docker Deployment](deployment/docker.md) - Container deployment
- [Kubernetes](deployment/kubernetes.md) - K8s orchestration
- [Docker Compose](deployment/docker_compose.md) - Multi-container setup
- [Production Best Practices](deployment/production.md) - Enterprise deployment

### 🔍 Reference

#### Protocol Specifications

- [Modbus TCP Specification](reference/modbus_spec.md) - Protocol details
- [Register Mappings](reference/register_mappings.md) - Device registers
- [Data Types](reference/data_types.md) - Supported data types
- [Error Codes](reference/error_codes.md) - Error handling

#### Configuration Reference

- [YAML Schema](reference/yaml_schema.md) - Complete schema
- [Environment Variables](reference/environment.md) - Configuration options
- [Command Line Options](reference/cli.md) - CLI reference

---

## 🎯 Quick Navigation by Use Case

### For Developers Testing Applications

1. Start with [Quick Start Guide](../README.md#-quick-start)
2. Use [Simple Factory Example](../examples/configs/simple_factory.yml)
3. Connect with [Python Client Example](../examples/modbus/quick_start.py)
4. Monitor with [Data Monitor](api/data_monitor.md)

### For Learning Industrial Protocols

1. Read [Modbus TCP Guide](protocols/modbus/README.md)
2. Try [First Factory Tutorial](tutorials/first_factory.md)
3. Experiment with [Device Templates](configuration/device_templates.md)
4. Use [Protocol Analyzer](tools/protocol_analyzer.md)

### For Production Deployment

1. Review [Architecture Guide](architecture/system_design.md)
2. Follow [Docker Deployment](deployment/docker.md)
3. Implement [Production Best Practices](deployment/production.md)
4. Set up [Monitoring & Alerts](deployment/monitoring.md)

### For Contributing

1. Read [Contributing Guide](../CONTRIBUTING.md)
2. Set up [Development Environment](development/setup.md)
3. Review [Code Structure](architecture/code_structure.md)
4. Run [Test Suite](testing/unit_tests.md)

---

## 📊 Implementation Status

### ✅ Completed (Production Ready)

- **Modbus TCP Protocol** - Full implementation
  - Temperature sensors, pressure transmitters, motor drives
  - Realistic data generation with industrial patterns
  - Complete register mappings and device types
- **MQTT Protocol** - Full implementation with embedded broker
  - Environmental sensors, smart energy meters, asset trackers
  - **Built-in MQTT broker** (amqtt) - no external setup needed
  - Configurable QoS levels (0, 1, 2), topic hierarchies
  - Gateway pattern for reliable multi-device publishing
- **OPC-UA Protocol** - Full implementation with dedicated servers
  - CNC machine monitors, PLC process controllers, industrial robots
  - Hierarchical address space (DeviceSet/Identification/Parameters/Status)
  - `asyncua`-based servers, compatible with standard OPC-UA clients
  - Realistic data patterns (tool wear, PID control, robot cycles)
- **Configuration System** - YAML-based configuration
- **REST API** - 15+ endpoints for monitoring/control
- **React Frontend** - Modern responsive dashboard (React + TypeScript + shadcn/ui)
- **Real-Time Data Monitor** - Streaming data viewer with multi-select device filter
- **Port Management** - Automatic allocation and conflict prevention
- **Docker Support** - Single-image deployment
- **Testing Framework** - Unit tests, integration tests

### 🚧 In Progress

- Additional device templates
- Enhanced documentation

### 📋 Planned

- Bluetooth/BLE simulation
- CCTV/RTSP streaming
- Ethernet/IP protocol
- Kubernetes deployment templates
- Cloud integration (AWS, Azure, GCP)

---

## 🔗 External Resources

### Protocol Standards

- [Modbus Protocol](https://modbus.org/) - Official specification
- [OPC-UA](https://opcfoundation.org/) - OPC Foundation
- [MQTT](https://mqtt.org/) - MQTT specification

### Tools & Libraries

- [pyModbus](https://github.com/pymodbus-dev/pymodbus) - Python Modbus library
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Docker](https://docs.docker.com/) - Container platform

### Learning Resources

- [Industrial IoT Guide](https://www.iiot-world.com/)
- [Protocol Tutorials](https://www.automation.com/)

---

## 💡 Tips for Navigation

- Use **Ctrl+F** (Cmd+F on Mac) to search this index
- All relative links work from this file's location
- Documentation follows consistent structure
- Code examples are runnable
- Each section includes "Next Steps" links

---

## 📧 Need Help?

- **Quick Questions**: Check [Common Issues](troubleshooting/common_issues.md)
- **Bug Reports**: [GitHub Issues](https://github.com/yourusername/universal-simulation-engine/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/yourusername/universal-simulation-engine/discussions)
- **Email Support**: support@example.com

---

**Happy Simulating! 🚀**

_This documentation is continuously updated. Last update: February 10, 2026_
