# OPC-UA Protocol Guide

**Complete guide to OPC-UA industrial device simulation**

Version: 0.4.0
Status: Production Ready
Last Updated: February 10, 2026

---

## Overview

The OPC-UA protocol implementation simulates industrial automation devices using the [asyncua](https://github.com/FreeOpcUa/opcua-asyncio) library. Each device runs its own OPC-UA server on a dedicated port with a structured address space organized into Identification, Parameters, and Status folders.

### Supported Device Types

| Device Type | Template Name | Description |
|---|---|---|
| CNC Machine | `opcua_cnc_machine` | 5-axis CNC machining center with spindle, feed, tool wear, axis positions |
| PLC Controller | `opcua_plc_controller` | PID process controller with setpoint tracking, alarms, mode switching |
| Industrial Robot | `opcua_industrial_robot` | 6-axis industrial robot with joint angles, TCP position, cycle tracking |

### Key Features

- **Per-device OPC-UA servers** - Each device gets its own server and port
- **Structured address spaces** - DeviceSet > Device > Identification/Parameters/Status
- **Writable nodes** - All parameter nodes are writable for interactive testing
- **State machine simulation** - Realistic state transitions (RUNNING, IDLE, ERROR, etc.)
- **Configurable security** - NoSecurity mode for simulation (default)
- **REST API integration** - Cached node data accessible via REST endpoints

---

## Quick Start

### Configuration

Add OPC-UA devices to your `factory.yml`:

```yaml
industrial_protocols:
  opcua:
    enabled: true
    security_mode: "None"
    security_policy: "None"
    application_uri: "urn:my-plant:opcua:server"
    devices:
      cnc_machines:
        count: 2
        port_start: 4840
        device_template: "opcua_cnc_machine"
        update_interval: 1.0
        data_config:
          spindle_speed_range: [0, 18000]
          feed_rate_range: [0, 12000]
          base_spindle_speed: 8000
          base_feed_rate: 4000
          tool_wear_rate: 0.015
          workspace_mm: [800, 600, 500]
          programs: ["EngineBlock_Op10", "EngineBlock_Op20"]
```

### Run with Docker

```bash
docker run -d \
  --name protocol-sim \
  -p 8080:8080 \
  -p 4840-4850:4840-4850 \
  -v $(pwd)/factory.yml:/config/factory.yml \
  developeryashsolanki/protocol-sim-engine:latest
```

### Connect with a Client

```python
from asyncua import Client

async def read_cnc():
    async with Client("opc.tcp://localhost:4840/freeopcua/server/") as client:
        # Browse to device nodes
        objects = client.nodes.objects
        device_set = await objects.get_child("0:DeviceSet")
        # ... browse the address space
```

Or use any OPC-UA client tool (e.g., UaExpert, Prosys OPC UA Browser).

---

## Address Space Structure

Every OPC-UA device follows the same address space layout:

```
Objects
└── DeviceSet
    └── {device_id}
        ├── Identification
        │   ├── Manufacturer: "Protocol Sim Engine"
        │   ├── Model: {device_template}
        │   └── SerialNumber: {device_id}
        ├── Parameters
        │   └── (device-type specific nodes - see below)
        └── Status
            ├── DeviceHealth: "NORMAL"
            ├── ErrorCode: 0 (Int32)
            └── OperatingMode: "AUTO"
```

Each device is registered in its own namespace: `urn:protocol-sim-engine:{device_id}`

---

## Device Types

### CNC Machining Center

Simulates a 5-axis CNC machining center with realistic state-driven behavior.

**Template:** `opcua_cnc_machine`

#### Nodes

| Node Name | Data Type | Description |
|---|---|---|
| SpindleSpeed | Double | Current spindle speed (RPM) |
| FeedRate | Double | Feed rate (mm/min) |
| ToolWearPercent | Double | Tool wear (0-100%) |
| PartCount | Int32 | Parts produced |
| AxisPosition_X | Double | X-axis position (mm) |
| AxisPosition_Y | Double | Y-axis position (mm) |
| AxisPosition_Z | Double | Z-axis position (mm) |
| ProgramName | String | Active G-code program |
| MachineState | String | Current state |

#### State Machine

```
RUNNING ──(0.5% chance)──> ERROR
RUNNING ──(1.5% chance)──> IDLE
IDLE ────(15% chance)───> RUNNING
IDLE ────(3% chance)────> SETUP
ERROR ───(after 5 ticks, 25%)──> IDLE
SETUP ───(after 3 ticks, 20%)──> RUNNING
```

- **RUNNING**: Spindle at speed, feed rate active, tool wear increasing, axis positions tracing toolpath
- **IDLE**: Spindle ramping down, parked position
- **SETUP**: Low spindle speed, new program may be loaded
- **ERROR**: Spindle ramping down, auto-recovery after pause

Tool changes trigger automatically at ~90% wear, switching to SETUP state.

#### Configuration

```yaml
data_config:
  spindle_speed_range: [0, 18000]    # RPM limits
  feed_rate_range: [0, 12000]        # mm/min limits
  base_spindle_speed: 8000           # Nominal speed during RUNNING
  base_feed_rate: 4000               # Nominal feed rate
  tool_wear_rate: 0.015              # Wear increment per tick
  workspace_mm: [800, 600, 500]      # X, Y, Z workspace envelope
  programs: ["Op10", "Op20", "Op30"] # Available G-code programs
```

---

### PLC Process Controller

Simulates a PID process controller for temperature/pressure control loops.

**Template:** `opcua_plc_controller`

#### Nodes

| Node Name | Data Type | Description |
|---|---|---|
| ProcessValue | Double | Current process value |
| Setpoint | Double | Active setpoint |
| ControlOutput | Double | PID output (0-100%) |
| Mode | String | Control mode |
| HighAlarm | Boolean | High alarm active |
| LowAlarm | Boolean | Low alarm active |
| IntegralTerm | Double | PID integral component |
| DerivativeTerm | Double | PID derivative component |
| Error | Double | Setpoint - ProcessValue |

#### Control Modes

- **AUTO**: PID controller actively tracking setpoint
- **MANUAL**: Fixed control output, process drifts
- **CASCADE**: Secondary PID loop (similar to AUTO with different transition probabilities)

#### PID Simulation

The PLC implements a realistic PID control loop:
- Process disturbances via Gaussian noise
- Integral windup protection (clamped to +-50)
- Occasional setpoint changes (simulating operator adjustments)
- Alarm states based on configurable thresholds

#### Configuration

```yaml
data_config:
  process_value_range: [60, 220]  # Process value limits
  setpoint: 180.0                 # Target setpoint
  kp: 2.0                        # Proportional gain
  ki: 0.3                        # Integral gain
  kd: 0.1                        # Derivative gain
  high_alarm: 210                 # High alarm threshold
  low_alarm: 100                  # Low alarm threshold
```

---

### Industrial Robot

Simulates a 6-axis industrial robot with realistic motion and cycle tracking.

**Template:** `opcua_industrial_robot`

#### Nodes

| Node Name | Data Type | Description |
|---|---|---|
| JointAngle_1..6 | Double | Joint angles (degrees) |
| TCPPosition_X | Double | Tool center point X (mm) |
| TCPPosition_Y | Double | Tool center point Y (mm) |
| TCPPosition_Z | Double | Tool center point Z (mm) |
| TCPOrientation_Rx | Double | TCP roll (degrees) |
| TCPOrientation_Ry | Double | TCP pitch (degrees) |
| TCPOrientation_Rz | Double | TCP yaw (degrees) |
| ProgramState | String | Current state |
| CycleTime | Double | Cycle time (seconds) |
| CycleCount | Int32 | Completed cycles |
| PayloadKg | Double | Current payload (kg) |
| SpeedPercent | Double | Speed override (%) |

#### State Machine

```
RUNNING ──(0.8% chance)──> PAUSED
RUNNING ──(0.3% chance)──> STOPPED
PAUSED ──(after 3 ticks, 20%)──> RUNNING
STOPPED ──(after 5 ticks, 12%)──> RUNNING
```

- **RUNNING**: Joints moving toward targets, TCP tracing path, cycles incrementing
- **PAUSED**: Joints frozen, speed at 0%
- **STOPPED**: Joints frozen, speed at 0%, longer recovery time

#### Configuration

```yaml
data_config:
  joint_count: 6               # Number of joints (default: 6)
  max_speed_percent: 80        # Maximum speed override
  base_cycle_time: 22.0        # Nominal cycle time (seconds)
  payload_range: [5, 15]       # Payload range (kg)
```

---

## REST API Endpoints

### OPC-UA Specific

| Endpoint | Method | Description |
|---|---|---|
| `/opcua/endpoints` | GET | List all OPC-UA server endpoints |
| `/opcua/devices/{id}/nodes` | GET | Get cached node values for a device |
| `/devices/{id}/data` | GET | Get device data (works for all protocols) |

### Example Responses

**GET /opcua/endpoints**

```json
[
  {
    "device_id": "opcua_cnc_machines_000",
    "device_type": "cnc_machine",
    "endpoint_url": "opc.tcp://0.0.0.0:4840/freeopcua/server/",
    "port": 4840,
    "status": "running",
    "node_count": 12
  }
]
```

**GET /devices/opcua_cnc_machines_000/data**

```json
{
  "device_id": "opcua_cnc_machines_000",
  "device_type": "cnc_machine",
  "timestamp": 1739184000.0,
  "nodes": {
    "spindle_speed_rpm": 8042.3,
    "feed_rate_mm_min": 4012.7,
    "tool_wear_percent": 23.4,
    "part_count": 147,
    "axis_position_x": 412.5,
    "axis_position_y": 287.3,
    "axis_position_z": 198.6,
    "program_name": "EngineBlock_Op10",
    "machine_state": "RUNNING"
  }
}
```

---

## Network Configuration

Each OPC-UA device runs on its own port. Port allocation follows the configuration:

```yaml
network:
  port_ranges:
    opcua: [4840, 4900]  # Available port range

industrial_protocols:
  opcua:
    devices:
      cnc_machines:
        count: 2
        port_start: 4840   # First CNC at 4840, second at 4841
      plc_controllers:
        count: 2
        port_start: 4842   # First PLC at 4842, second at 4843
      industrial_robots:
        count: 2
        port_start: 4844   # First robot at 4844, second at 4845
```

**Endpoint URL format:** `opc.tcp://0.0.0.0:{port}/freeopcua/server/`

When connecting from outside Docker, use `localhost` instead of `0.0.0.0`.

---

## Troubleshooting

### Common Issues

**Port already in use**
```
Failed to start OPC-UA device: [Errno 98] Address already in use
```
Solution: Change `port_start` or ensure no other OPC-UA servers are running on those ports.

**Connection refused from client**
- Ensure the Docker container exposes the OPC-UA ports: `-p 4840-4850:4840-4850`
- Check device status via REST API: `curl http://localhost:8080/devices`

**Nodes not updating**
- Check the `update_interval` setting (lower = faster updates)
- Verify device health via `GET /devices/{id}`

### Logging

OPC-UA device events are logged via structlog. Check container logs:

```bash
docker logs protocol-sim | grep "OPC-UA"
```

---

## Full Example Configuration

See [examples/configs/full_factory.yml](../../../examples/configs/full_factory.yml) for a complete multi-protocol configuration with 24 devices across Modbus TCP, MQTT, and OPC-UA.
