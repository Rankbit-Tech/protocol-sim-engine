# v0.4.0 - OPC UA Industrial Protocol Support

## Release v0.4.0 - OPC UA Protocol

### What's New

#### OPC UA Protocol Support

The simulator now supports OPC UA (OPC Unified Architecture), the modern standard for industrial data exchange. Three new device types simulate real factory equipment, each running its own OPC UA server with a structured address space.

**CNC Machine Monitor** (`opcua_cnc_machine`)

- Spindle speed, feed rate, tool wear, part count, axis positions (X/Y/Z)
- Tool wear progression with periodic resets (tool change simulation)

**PLC Process Controller** (`opcua_plc_controller`)

- PID control loop: process value, setpoint, control output
- Mode switching (AUTO/MANUAL/CASCADE), high/low alarms

**Industrial Robot** (`opcua_industrial_robot`)

- 6-axis joint angles, TCP position and orientation
- Program state, cycle time, payload, speed percentage

#### OPC UA Server Architecture

- Each device runs a dedicated `asyncua` OPC UA server
- Hierarchical address space: `DeviceSet/{Name}/Identification|Parameters|Status`
- Default port range: 4840-4850 (configurable per device)
- Compatible with standard OPC UA clients (UaExpert, Prosys, etc.)

#### New API Endpoints

- `GET /opcua/servers` - List all OPC UA server endpoints with status
- `GET /opcua/devices/{id}/nodes` - Read current node values for a device

#### Frontend Updates

- Dashboard automatically displays OPC UA protocol and device counts
- Data Monitor streams and formats OPC UA device telemetry (CNC, PLC, Robot)

### Bug Fixes

- Fixed pattern data generation for industrial data patterns

### Infrastructure

- Docker image exposes OPC UA ports (4840-4850)
- Added `asyncua` dependency for OPC UA server implementation
- New `full_factory.yml` example config with all 3 protocols (Modbus + MQTT + OPC UA)
- Comprehensive unit test suite (7 test classes, 677 lines)

### Upgrade Notes

No breaking changes. The API and existing Modbus/MQTT functionality remain unchanged. Simply pull the new image:

```bash
docker pull developeryashsolanki/protocol-sim-engine:0.4.0
```

Running with OPC UA ports exposed:

```bash
docker run -d \
  -p 8080:8080 \
  -p 1883:1883 \
  -p 15000-15002:15000-15002 \
  -p 4840-4850:4840-4850 \
  developeryashsolanki/protocol-sim-engine:0.4.0
```

Access the dashboard at http://localhost:8080
Connect an OPC UA client to `opc.tcp://localhost:4840`
