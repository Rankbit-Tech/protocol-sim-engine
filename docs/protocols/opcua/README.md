# OPC-UA Protocol Guide

**Complete guide to OPC-UA industrial device simulation**

Version: 0.4.0
Status: Production Ready
Last Updated: February 10, 2026

---

## Overview

The OPC-UA implementation provides realistic simulation of industrial automation equipment using the OPC Unified Architecture standard. Each device runs its own OPC-UA server with a structured, hierarchical address space — the modern approach to industrial data modeling.

### Key Features

- **Dedicated OPC-UA Servers** - Each device runs a standalone asyncua server on its own port
- **Structured Address Space** - Hierarchical nodes: DeviceSet / Identification / Parameters / Status
- **3 Device Types** - CNC machines, PLC controllers, industrial robots
- **Realistic Data** - Industrial-grade data patterns (tool wear progression, PID control, robot cycles)
- **Standard Compliance** - Compatible with UaExpert, Prosys, and any OPC-UA client
- **Configurable Security** - None, Sign, or SignAndEncrypt modes

---

## Quick Start

### 1. Enable OPC-UA in Configuration

```yaml
# config.yml
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
```

### 2. Run the Simulator

```bash
docker run -d \
  --name opcua-sim \
  -p 8080:8080 \
  -p 4840-4850:4840-4850 \
  developeryashsolanki/protocol-sim-engine:0.4.0
```

### 3. Connect with an OPC-UA Client

```python
import asyncio
from asyncua import Client

async def main():
    client = Client("opc.tcp://localhost:4840/freeopcua/server/")
    async with client:
        root = client.nodes.root
        objects = await root.get_children()
        print("Root children:", objects)

        # Read spindle speed from CNC machine
        node = client.get_node("ns=2;s=SpindleSpeed")
        value = await node.read_value()
        print(f"Spindle Speed: {value} RPM")

asyncio.run(main())
```

Or use a graphical client like **UaExpert** or **Prosys OPC-UA Browser**:

1. Open the client
2. Add server: `opc.tcp://localhost:4840/freeopcua/server/`
3. Connect (no authentication required with `security_mode: "None"`)
4. Browse the address space under `Objects > DeviceSet`

---

## Device Types

### CNC Machine Monitor (`opcua_cnc_machine`)

Simulates a CNC machining center with spindle monitoring, tool wear tracking, and axis position reporting.

**Configuration:**

```yaml
cnc_machines:
  count: 2
  port_start: 4840
  device_template: "opcua_cnc_machine"
  locations: ["machining_cell_1", "machining_cell_2"]
  update_interval: 1.0
  data_config:
    spindle_speed_range: [0, 24000] # RPM
    feed_rate_range: [0, 15000] # mm/min
    base_spindle_speed: 8000
    base_feed_rate: 4000
    tool_wear_rate: 0.015
    workspace_mm: [800, 600, 500]
    programs: ["EngineBlock_Op10", "EngineBlock_Op20"]
```

**OPC-UA Nodes:**

| Node Name         | Data Type | Unit   | Description                                                    |
| ----------------- | --------- | ------ | -------------------------------------------------------------- |
| `SpindleSpeed`    | Double    | RPM    | Current spindle rotation speed                                 |
| `FeedRate`        | Double    | mm/min | Cutting feed rate                                              |
| `ToolWearPercent` | Double    | %      | Tool wear (0-100%, increases over time, resets on tool change) |
| `PartCount`       | Int32     | -      | Total parts produced (incrementing)                            |
| `AxisPosition_X`  | Double    | mm     | X-axis position                                                |
| `AxisPosition_Y`  | Double    | mm     | Y-axis position                                                |
| `AxisPosition_Z`  | Double    | mm     | Z-axis position                                                |
| `ProgramName`     | String    | -      | Currently running NC program                                   |
| `MachineState`    | String    | -      | IDLE, RUNNING, ERROR, or SETUP                                 |

**Data Behavior:**

- Tool wear increases gradually over time and resets periodically (simulates tool change)
- Part count increments as machining cycles complete
- Axis positions trace machining paths within the configured workspace
- Spindle speed and feed rate vary with noise around base values

---

### PLC Process Controller (`opcua_plc_controller`)

Simulates a PLC running a PID control loop with setpoint tracking, alarm monitoring, and mode switching.

**Configuration:**

```yaml
plc_controllers:
  count: 2
  port_start: 4842
  device_template: "opcua_plc_controller"
  locations: ["paint_booth_ctrl", "curing_oven_ctrl"]
  update_interval: 0.5
  data_config:
    process_value_range: [60, 220]
    setpoint: 180.0
    kp: 2.0
    ki: 0.3
    kd: 0.1
    high_alarm: 210
    low_alarm: 100
```

**OPC-UA Nodes:**

| Node Name        | Data Type | Unit              | Description                                       |
| ---------------- | --------- | ----------------- | ------------------------------------------------- |
| `ProcessValue`   | Double    | engineering units | Current measured process value                    |
| `Setpoint`       | Double    | engineering units | Target setpoint                                   |
| `ControlOutput`  | Double    | %                 | PID control output (0-100%)                       |
| `Mode`           | String    | -                 | AUTO, MANUAL, or CASCADE                          |
| `HighAlarm`      | Boolean   | -                 | True when process value exceeds high threshold    |
| `LowAlarm`       | Boolean   | -                 | True when process value drops below low threshold |
| `IntegralTerm`   | Double    | -                 | PID integral accumulator                          |
| `DerivativeTerm` | Double    | -                 | PID derivative term                               |
| `Error`          | Double    | -                 | Setpoint minus process value                      |

**Data Behavior:**

- Process value tracks toward setpoint with realistic overshoot and settling
- Alarms activate when process value exceeds configured thresholds
- Mode switches between AUTO/MANUAL/CASCADE

---

### Industrial Robot (`opcua_industrial_robot`)

Simulates a 6-axis industrial robot with joint position tracking, cycle monitoring, and payload reporting.

**Configuration:**

```yaml
industrial_robots:
  count: 2
  port_start: 4844
  device_template: "opcua_industrial_robot"
  locations: ["weld_cell_left", "weld_cell_right"]
  update_interval: 0.5
  data_config:
    joint_count: 6
    max_speed_percent: 80
    base_cycle_time: 22.0
    payload_range: [5, 15]
```

**OPC-UA Nodes:**

| Node Name                             | Data Type | Unit    | Description                      |
| ------------------------------------- | --------- | ------- | -------------------------------- |
| `JointAngle_1` through `JointAngle_6` | Double    | degrees | Joint positions for all 6 axes   |
| `TCPPosition_X`                       | Double    | mm      | Tool center point X position     |
| `TCPPosition_Y`                       | Double    | mm      | Tool center point Y position     |
| `TCPPosition_Z`                       | Double    | mm      | Tool center point Z position     |
| `TCPOrientation_Rx`                   | Double    | degrees | Tool rotation around X           |
| `TCPOrientation_Ry`                   | Double    | degrees | Tool rotation around Y           |
| `TCPOrientation_Rz`                   | Double    | degrees | Tool rotation around Z           |
| `ProgramState`                        | String    | -       | RUNNING, PAUSED, or STOPPED      |
| `CycleTime`                           | Double    | seconds | Duration of last completed cycle |
| `CycleCount`                          | Int32     | -       | Total cycles completed           |
| `PayloadKg`                           | Double    | kg      | Current payload weight           |
| `SpeedPercent`                        | Double    | %       | Current speed override (0-100%)  |

**Data Behavior:**

- Joint angles move through programmed positions in a cyclic pattern
- Cycle time varies around the base cycle time with realistic noise
- Cycle count increments as programs complete
- Payload changes between operations

---

## Address Space Structure

Every OPC-UA device creates the following hierarchical node structure:

```
Root
└── Objects
    └── DeviceSet
        └── {DeviceName}
            ├── Identification
            │   ├── Manufacturer (String)
            │   ├── Model (String)
            │   └── SerialNumber (String)
            ├── Parameters
            │   ├── {device-specific node 1}
            │   ├── {device-specific node 2}
            │   └── ...
            └── Status
                ├── DeviceHealth (String: "NORMAL"/"WARNING"/"FAILURE")
                ├── ErrorCode (Int32)
                └── OperatingMode (String)
```

- **Identification** - Static metadata about the device
- **Parameters** - Live, updating device-specific data (see node tables above)
- **Status** - Device health and operating mode

---

## Configuration Reference

### Global OPC-UA Settings

```yaml
industrial_protocols:
  opcua:
    enabled: true # Enable/disable OPC-UA
    security_mode: "None" # None, Sign, SignAndEncrypt
    security_policy: "None" # None, Basic256Sha256
    application_uri: "urn:protocol-sim-engine:opcua:server" # Server application URI
    devices:
      # ... device groups ...
```

### Device Group Settings

```yaml
devices:
  group_name:
    count: 1 # Number of devices in this group
    port_start: 4840 # Starting port (each device gets port_start + index)
    device_template: "..." # One of: opcua_cnc_machine, opcua_plc_controller, opcua_industrial_robot
    locations: ["loc1"] # Optional location labels
    update_interval: 1.0 # Data update frequency in seconds
    data_config:# Device-specific data configuration
      # ... (see device type sections above)
```

### Port Allocation

- Default port range: `4840-4940`
- Each device uses one port
- Ports are allocated sequentially from `port_start`
- Port conflicts are detected automatically by the port manager
- Standard OPC-UA port is 4840 (matching the IANA-assigned port)

Add the port range to your network configuration:

```yaml
network:
  port_ranges:
    opcua: [4840, 4940]
```

---

## API Endpoints

### List OPC-UA Servers

```
GET /opcua/servers
```

Returns all running OPC-UA server endpoints:

```json
{
  "servers": [
    {
      "device_id": "opcua_cnc_machines_000",
      "device_type": "cnc_machine",
      "endpoint_url": "opc.tcp://0.0.0.0:4840/freeopcua/server/",
      "port": 4840,
      "status": "running",
      "node_count": 12
    }
  ]
}
```

### Get Device Node Values

```
GET /opcua/devices/{device_id}/nodes
```

Returns current node values for a specific device:

```json
{
  "device_id": "opcua_cnc_machines_000",
  "nodes": {
    "spindle_speed_rpm": 12500.3,
    "feed_rate_mm_min": 4200.0,
    "tool_wear_percent": 34.2,
    "part_count": 157,
    "axis_position_x": 245.8,
    "axis_position_y": 120.3,
    "axis_position_z": -50.1,
    "program_name": "EngineBlock_Op10",
    "machine_state": "RUNNING"
  }
}
```

### General Device Endpoints

The standard device endpoints also work with OPC-UA devices:

```bash
# List all devices (includes OPC-UA)
curl http://localhost:8080/devices

# Get OPC-UA device data
curl http://localhost:8080/devices/opcua_cnc_machines_000/data

# System status (shows opcua in protocols list)
curl http://localhost:8080/status
```

---

## Frontend Integration

### Dashboard

The dashboard automatically detects OPC-UA devices and displays:

- OPC-UA protocol in the protocols list with device count
- Individual device status indicators
- Health percentage across all protocols

### Data Monitor

The Data Monitor formats OPC-UA telemetry for each device type:

- **CNC Machine**: `12500 RPM · Feed: 4200 mm/min · Tool: 34% · Parts: 157 · RUNNING`
- **PLC Controller**: `PV: 178.5 · SP: 180.0 · Out: 42% · Mode: AUTO · Alarm: None`
- **Robot**: `RUNNING · Cycle: 22.3s · Payload: 8.5kg · Speed: 80%`

---

## Troubleshooting

### Common Issues

**OPC-UA server not starting**

- Check that the configured port is not in use: `lsof -i :4840`
- Verify `opcua.enabled: true` in your config
- Check container logs: `docker logs protocol-sim`

**Cannot connect with OPC-UA client**

- Ensure port is exposed in Docker: `-p 4840:4840`
- Use the correct endpoint URL: `opc.tcp://localhost:4840/freeopcua/server/`
- If using security, ensure client and server security policies match

**Node values not updating**

- Check `update_interval` in your configuration (lower = faster updates)
- Verify device is running: `curl http://localhost:8080/devices`
- Check device health: `curl http://localhost:8080/health`

**Port conflicts**

- The port manager handles conflicts automatically
- If manual port assignment conflicts, adjust `port_start` values
- Check allocated ports: `curl http://localhost:8080/opcua/servers`

### Debugging with API

```bash
# Check if OPC-UA is active
curl http://localhost:8080/status | jq '.protocols'

# List all OPC-UA servers
curl http://localhost:8080/opcua/servers | jq

# Get specific device nodes
curl http://localhost:8080/opcua/devices/opcua_cnc_machines_000/nodes | jq
```

---

## Architecture

### Implementation Details

- **Library**: `asyncua` (formerly `opcua-asyncio`) - async Python OPC-UA stack
- **Server**: Each `OPCUADevice` runs an independent `asyncua.Server` instance
- **Data Generation**: Reuses `IndustrialDataGenerator` from `src/data_patterns/industrial_patterns.py`
- **Update Loop**: Background async task updates node values at configured intervals
- **Node Caching**: Values are cached for synchronous API access via `get_node_data()`

### File Structure

```
src/protocols/industrial/opcua/
├── __init__.py              # Package initialization
└── opcua_simulator.py       # OPCUADevice + OPCUADeviceManager classes
```

### Integration Points

- `src/config_parser.py` - `OPCUAConfig` and `OPCUADeviceConfig` Pydantic models
- `src/orchestrator.py` - OPC-UA manager initialization and device data retrieval
- `src/main.py` - `/opcua/*` API endpoints
- `frontend/src/types/index.ts` - TypeScript interfaces for OPC-UA data
- `frontend/src/components/DataMonitor.tsx` - OPC-UA telemetry formatting

---

## Full Example Configuration

See [examples/configs/full_factory.yml](../../../examples/configs/full_factory.yml) for a complete multi-protocol configuration including Modbus, MQTT, and OPC-UA devices.

---

**See also:**

- [Modbus TCP Protocol Guide](../modbus/README.md) - Modbus implementation
- [MQTT Protocol Guide](../mqtt/README.md) - MQTT & IoT devices
- [Configuration Examples](../../../examples/configs/README.md) - Ready-to-use configs
- [Main README](../../../README.md) - Project overview

---

_For the latest updates, see [docs/INDEX.md](../../INDEX.md)_
