# OPC-UA Protocol Implementation Plan

**Author:** Claude (AI-assisted)
**Date:** February 10, 2026
**Target Version:** 0.4.0
**Status:** Proposed

---

## 1. What is OPC-UA and Why It Matters

### What is OPC-UA?

OPC Unified Architecture (OPC-UA) is the modern, platform-independent standard for industrial data exchange. Developed by the OPC Foundation, it replaces the older COM/DCOM-based OPC Classic with a secure, cross-platform protocol that runs on everything from embedded PLCs to cloud servers.

Key characteristics:
- **Information Modeling** — OPC-UA organizes data as a structured address space of typed nodes (objects, variables, methods), not flat register tables like Modbus.
- **Client-Server Architecture** — Clients browse the address space and read/write/subscribe to node values. Our simulator will act as an OPC-UA **server**.
- **Subscriptions & Monitored Items** — Clients can subscribe to value changes and get pushed updates at configurable intervals, rather than polling.
- **Security Built-in** — Supports authentication, encryption (TLS), and signing at the protocol level.
- **Discovery** — Servers can advertise themselves on a network via Local Discovery Servers.

### Why Implement It?

OPC-UA is the **#1 standard for modern industrial automation**. It's mandated or preferred by:
- **Industry 4.0 / Smart Manufacturing** — The reference architecture (RAMI 4.0) specifies OPC-UA as the communication layer.
- **Major PLC vendors** — Siemens, Rockwell/Allen-Bradley, Beckhoff, B&R all expose OPC-UA servers on their controllers.
- **SCADA & MES systems** — Ignition, WinCC, FactoryTalk, AVEVA all use OPC-UA as a primary data source.
- **Cloud IoT platforms** — AWS IoT SiteWise, Azure IoT, Google Cloud IoT all have native OPC-UA connectors.

Simulating OPC-UA completes the "big three" of industrial protocols alongside Modbus TCP and MQTT, making this platform useful for the vast majority of industrial IoT development and testing workflows.

---

## 2. Architecture Overview

### How It Fits Into the Existing System

The OPC-UA implementation follows the same patterns established by Modbus and MQTT:

```
config_parser.py          → OPCUAConfig, OPCUADeviceConfig (Pydantic models)
orchestrator.py            → Initializes OPCUADeviceManager alongside Modbus/MQTT
opcua_simulator.py         → OPCUADevice + OPCUADeviceManager classes
industrial_patterns.py     → Reuses existing data generators (no changes needed)
main.py                    → New /opcua/* API endpoints
frontend/src/types/        → Extended TypeScript interfaces
frontend/src/components/   → DataMonitor + Dashboard updates
```

### Protocol Library

We will use **`asyncua`** (formerly `opcua-asyncio`), the actively maintained async Python OPC-UA library. It provides:
- Full OPC-UA server implementation
- Address space management
- Subscription support
- Security policy configuration
- Python 3.12 compatible, async/await native

```toml
# pyproject.toml addition
asyncua = ">=1.1.0"
```

### Device Types (3 New Device Types)

Following the convention of 3 device types per protocol:

| # | Device Type | Template Name | Description | Industrial Use Case |
|---|---|---|---|---|
| 1 | **CNC Machine Monitor** | `opcua_cnc_machine` | Spindle speed, feed rate, tool wear, part count, axis positions | Machine tool monitoring |
| 2 | **PLC Process Controller** | `opcua_plc_controller` | Setpoints, process values, PID outputs, mode, alarm states | Process control |
| 3 | **Industrial Robot** | `opcua_industrial_robot` | Joint angles, TCP position, program state, cycle time, payload | Robotics monitoring |

These device types were chosen because:
- They represent **equipment that typically exposes OPC-UA servers** in real factories.
- They are distinct from the Modbus (sensors/drives) and MQTT (IoT/asset) device types.
- They showcase OPC-UA's strength: **structured, hierarchical data** rather than flat registers.

---

## 3. Detailed Implementation Plan

### Phase 1: Backend Core (Config + Simulator)

#### 3.1 Configuration Models (`src/config_parser.py`)

Add Pydantic models following the existing pattern:

```python
class OPCUADeviceConfig(BaseModel):
    """Configuration for OPC-UA devices."""
    count: int = Field(gt=0, le=1000)
    port_start: int = Field(ge=1024, le=65535)
    device_template: str
    locations: Optional[List[str]] = None
    update_interval: float = Field(gt=0, default=1.0)
    data_config: Optional[Dict[str, Any]] = None

class OPCUAConfig(BaseModel):
    """OPC-UA protocol configuration."""
    enabled: bool = True
    devices: Dict[str, OPCUADeviceConfig] = Field(default_factory=dict)
    security_mode: str = "None"  # None, Sign, SignAndEncrypt
    security_policy: str = "None"  # None, Basic256Sha256
    application_uri: str = "urn:protocol-sim-engine:opcua:server"
```

Update `IndustrialProtocolsConfig`:
```python
class IndustrialProtocolsConfig(BaseModel):
    modbus_tcp: Optional[ModbusConfig] = None
    mqtt: Optional[MQTTConfig] = None
    opcua: Optional[OPCUAConfig] = None  # NEW
```

#### 3.2 OPC-UA Simulator (`src/protocols/industrial/opcua/opcua_simulator.py`)

**`OPCUADevice` class** — mirrors `ModbusDevice` structure:

| Method | Purpose | Pattern Source |
|---|---|---|
| `__init__()` | Init device with config, port, data generator | Same as `ModbusDevice.__init__` |
| `_extract_device_type()` | Map template name to device type string | Same as Modbus/MQTT |
| `_build_address_space()` | Create OPC-UA nodes (replaces `_create_modbus_context`) | OPC-UA specific |
| `_update_node_values()` | Update node values with generated data (replaces `_update_registers_with_realistic_data`) | OPC-UA specific |
| `_data_update_loop()` | Async loop for periodic value updates | Same as Modbus |
| `start()` | Create & start OPC-UA server + update loop | Same pattern as Modbus |
| `stop()` | Stop server and cancel tasks | Same as Modbus |
| `get_status()` | Return device status dict | Same as Modbus |
| `get_node_data()` | Read current node values (replaces `get_register_data`) | OPC-UA specific |

**Address space structure** per device type:

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
            │   ├── {param1} (Double/Int/Bool)
            │   ├── {param2} (Double/Int/Bool)
            │   └── ...
            └── Status
                ├── DeviceHealth (String: "NORMAL"/"WARNING"/"FAILURE")
                ├── ErrorCode (Int32)
                └── OperatingMode (String)
```

**CNC Machine node values:**
- `SpindleSpeed` (Double, RPM)
- `FeedRate` (Double, mm/min)
- `ToolWearPercent` (Double, 0-100%)
- `PartCount` (Int32)
- `AxisPosition_X` / `_Y` / `_Z` (Double, mm)
- `ProgramName` (String)
- `MachineState` (String: "IDLE"/"RUNNING"/"ERROR"/"SETUP")

**PLC Process Controller node values:**
- `ProcessValue` (Double, engineering units)
- `Setpoint` (Double, engineering units)
- `ControlOutput` (Double, 0-100%)
- `Mode` (String: "AUTO"/"MANUAL"/"CASCADE")
- `HighAlarm` / `LowAlarm` (Boolean)
- `IntegralTerm` / `DerivativeTerm` (Double)

**Industrial Robot node values:**
- `JointAngles` (array of 6 Doubles, degrees)
- `TCPPosition_X` / `_Y` / `_Z` (Double, mm)
- `TCPOrientation_Rx` / `_Ry` / `_Rz` (Double, degrees)
- `ProgramState` (String: "RUNNING"/"PAUSED"/"STOPPED")
- `CycleTime` (Double, seconds)
- `PayloadKg` (Double)
- `SpeedPercent` (Double, 0-100%)

**`OPCUADeviceManager` class** — mirrors `ModbusDeviceManager`:

| Method | Purpose |
|---|---|
| `__init__()` | Store config and port manager reference |
| `initialize()` | Build allocation plan, create device instances |
| `_build_allocation_plan()` | Map device IDs to ("opcua", 1) port requirements |
| `_create_devices()` | Allocate ports and instantiate `OPCUADevice` objects |
| `get_allocation_requirements()` | Return plan for validation |
| `start_all_devices()` | Start all OPC-UA servers (semaphore-limited parallelism) |
| `stop_all_devices()` | Stop all servers, deallocate ports |
| `get_health_status()` | Aggregate device statuses |
| `get_device_status()` | Single device lookup |
| `restart_device()` | Stop + start a device |

#### 3.3 Data Generation (`src/data_patterns/industrial_patterns.py`)

Add three new generator methods to `IndustrialDataGenerator`:

- `generate_cnc_machine_data(config)` — spindle speed with vibration patterns, tool wear that increases over time with periodic resets (tool change), axis positions that trace machining paths, part count that increments.
- `generate_plc_controller_data(config)` — PID control loop simulation with setpoint tracking, overshoot, settling time, mode changes.
- `generate_robot_data(config)` — joint angles that move through programmed positions, cycle time with variation, payload changes.

Update `generate_device_data()` to handle the three new device types.

#### 3.4 Orchestrator Integration (`src/orchestrator.py`)

Add OPC-UA initialization following the exact pattern at line 82-134:

```python
from .protocols.industrial.opcua.opcua_simulator import OPCUADeviceManager

# In _initialize_protocol_managers():
if self.config.industrial_protocols.opcua and self.config.industrial_protocols.opcua.enabled:
    logger.info("Initializing OPC-UA protocol manager...")
    opcua_manager = OPCUADeviceManager(
        self.config.industrial_protocols.opcua,
        self.port_manager
    )
    await opcua_manager.initialize()
    self.device_managers["opcua"] = opcua_manager
    self.active_protocols.add("opcua")
```

Update `get_device_data()` to handle the `"opcua"` protocol:
```python
elif protocol_name == "opcua":
    return device.get_node_data()
```

#### 3.5 API Endpoints (`src/main.py`)

Add OPC-UA specific endpoints following the MQTT pattern (lines 363-414):

```
GET /opcua/servers          → List all OPC-UA server endpoints
GET /opcua/devices/{id}/nodes → Browse address space nodes for a device
```

#### 3.6 Default Config (`config/default_config.yml`)

Add OPC-UA section:

```yaml
industrial_protocols:
  # ... existing modbus_tcp and mqtt sections ...

  opcua:
    enabled: true
    security_mode: "None"
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

### Phase 2: Frontend Updates

#### 3.7 TypeScript Types (`frontend/src/types/index.ts`)

Extend `Device` interface:
```typescript
// OPC-UA specific
endpoint_url?: string;
security_mode?: string;
node_count?: number;
```

Extend `DeviceData` to add an `opcua_nodes` field:
```typescript
nodes?: {
  // CNC Machine
  spindle_speed_rpm?: number;
  feed_rate_mm_min?: number;
  tool_wear_percent?: number;
  part_count?: number;
  machine_state?: string;
  // PLC Controller
  process_value?: number;
  setpoint?: number;
  control_output?: number;
  mode?: string;
  // Robot
  program_state?: string;
  cycle_time_s?: number;
  payload_kg?: number;
  speed_percent?: number;
};
```

#### 3.8 DataMonitor Component (`frontend/src/components/DataMonitor.tsx`)

Add OPC-UA formatting to `formatDeviceData()`:

```typescript
if (data.nodes) {
  const n = data.nodes;
  if (n.spindle_speed_rpm !== undefined) {
    return `${n.spindle_speed_rpm} RPM · Feed: ${n.feed_rate_mm_min} mm/min · Tool: ${n.tool_wear_percent}% · Parts: ${n.part_count} · ${n.machine_state}`;
  }
  if (n.process_value !== undefined) {
    return `PV: ${n.process_value} · SP: ${n.setpoint} · Out: ${n.control_output}% · Mode: ${n.mode}`;
  }
  if (n.program_state !== undefined) {
    return `${n.program_state} · Cycle: ${n.cycle_time_s}s · Payload: ${n.payload_kg}kg · Speed: ${n.speed_percent}%`;
  }
}
```

#### 3.9 Dashboard Component (`frontend/src/components/Dashboard.tsx`)

No structural changes needed — the Dashboard already dynamically reads protocol names and device counts from the API. OPC-UA devices will appear automatically.

### Phase 3: Docker & Config

#### 3.10 Dockerfile

Update the port EXPOSE directive to include OPC-UA ports:
```dockerfile
EXPOSE 8080 1883 15000-15002 4840-4842
```

#### 3.11 Docker run command

Update the recommended run command:
```bash
docker run -d --name protocol-sim \
  -p 8080:8080 \
  -p 1883:1883 \
  -p 15000-15002:15000-15002 \
  -p 4840-4842:4840-4842 \
  protocol-sim-engine:latest
```

---

## 4. File Change Summary

| File | Action | Description |
|---|---|---|
| `pyproject.toml` | MODIFY | Add `asyncua >= 1.1.0` dependency |
| `src/config_parser.py` | MODIFY | Add `OPCUADeviceConfig`, `OPCUAConfig`, update `IndustrialProtocolsConfig` |
| `src/orchestrator.py` | MODIFY | Add OPC-UA manager initialization, update `get_device_data()` |
| `src/main.py` | MODIFY | Add `/opcua/*` endpoints |
| `src/protocols/industrial/opcua/__init__.py` | CREATE | Package init |
| `src/protocols/industrial/opcua/opcua_simulator.py` | CREATE | `OPCUADevice` + `OPCUADeviceManager` |
| `src/data_patterns/industrial_patterns.py` | MODIFY | Add 3 new generator methods, update `generate_device_data()` |
| `config/default_config.yml` | MODIFY | Add `opcua` section with 3 device groups |
| `frontend/src/types/index.ts` | MODIFY | Add OPC-UA fields to `Device` and `DeviceData` |
| `frontend/src/components/DataMonitor.tsx` | MODIFY | Add OPC-UA data formatting |
| `Dockerfile` | MODIFY | Expose OPC-UA ports |
| `tests/unit/test_opcua_protocol.py` | CREATE | Unit tests for OPC-UA |

**New files:** 2
**Modified files:** 10

---

## 5. Testing Plan

### 5.1 Unit Tests (`tests/unit/test_opcua_protocol.py`)

Following the exact structure of `test_modbus_protocol.py` and `test_mqtt_protocol.py`:

**TestOPCUADeviceCreation**
- `test_device_initialization` — Verify device_id, port, device_type, running state
- `test_device_type_extraction` — Verify template-to-type mapping for all 3 types
- `test_address_space_creation` — Verify nodes are created and readable
- `test_data_generation_integration` — Verify data generator produces correct fields
- `test_node_value_updates` — Verify `_update_node_values()` writes correct data
- `test_device_status_reporting` — Verify `get_status()` structure

**TestOPCUADeviceLifecycle**
- `test_device_start_stop_lifecycle` — Mock server, verify start/stop state transitions
- `test_device_uptime_tracking` — Verify uptime counter works

**TestOPCUADeviceManager**
- `test_device_manager_initialization` — Verify correct number of devices created
- `test_allocation_plan_building` — Verify plan has correct device count and port requirements
- `test_device_creation_and_port_allocation` — Verify unique port per device in correct range

**TestOPCUADataPatterns**
- `test_cnc_machine_data_generation` — Verify all CNC fields present and within bounds
- `test_plc_controller_data_generation` — Verify PID-related fields present and within bounds
- `test_robot_data_generation` — Verify joint angles, TCP position, program state
- `test_tool_wear_progression` — Verify tool wear increases over multiple calls
- `test_part_count_increment` — Verify part count increments

**TestOPCUAConfiguration**
- `test_opcua_config_validation` — Valid and invalid configs
- `test_opcua_device_config_validation` — Boundary testing for fields

**TestOPCUAScalability**
- `test_multiple_device_creation` — Create 30+ devices, verify < 5s init time
- `test_port_allocation_efficiency` — Verify port manager handles OPC-UA allocations

### 5.2 Integration Tests (`tests/integration/test_opcua_integration.py`)

- `test_opcua_client_connection` — Start a device, connect with asyncua client, read values
- `test_opcua_subscription` — Subscribe to node changes, verify updates arrive
- `test_multi_protocol_simulation` — Run Modbus + MQTT + OPC-UA together, verify all healthy
- `test_opcua_address_space_browsing` — Connect and browse the full node tree

### 5.3 Docker Smoke Tests

- Verify container starts with OPC-UA enabled in default config
- Verify `GET /status` shows `opcua` in protocols list
- Verify `GET /devices` includes OPC-UA devices
- Verify `GET /devices/{opcua_device_id}/data` returns node values
- Verify OPC-UA port (4840) is accessible from host

### 5.4 Frontend Testing

- Verify Dashboard shows OPC-UA protocol with device count
- Verify DataMonitor streams OPC-UA device data
- Verify OPC-UA data displays formatted correctly (not raw JSON)

---

## 6. Implementation Order

Execute in this order to maintain a working system at each step:

| Step | What | Depends On | Estimated Effort |
|---|---|---|---|
| 1 | Add `asyncua` to `pyproject.toml` | Nothing | Small |
| 2 | Add config models to `config_parser.py` | Nothing | Small |
| 3 | Create `opcua_simulator.py` with `OPCUADevice` + `OPCUADeviceManager` | Steps 1-2 |  Large |
| 4 | Add data generators to `industrial_patterns.py` | Nothing | Medium |
| 5 | Wire into `orchestrator.py` | Steps 2-3 | Small |
| 6 | Add API endpoints to `main.py` | Step 5 | Small |
| 7 | Update `default_config.yml` | Step 2 | Small |
| 8 | Write unit tests | Steps 2-4 | Medium |
| 9 | Update frontend types and components | Step 6 | Medium |
| 10 | Update Dockerfile and test Docker build | Step 7 | Small |
| 11 | Run full integration tests | All | Medium |
| 12 | Update documentation | All | Small |

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `asyncua` library compatibility with Python 3.12 | Blocks entire implementation | Verified: asyncua 1.1.x supports Python 3.12. Pin version in pyproject.toml |
| Port conflicts with real OPC-UA servers on dev machines | Devices fail to start | Use configurable ports (4840-4842 default), same pattern as Modbus port_start |
| OPC-UA server startup is slower than Modbus | Longer container startup time | Start OPC-UA servers with same semaphore pattern (max 5 concurrent) |
| Address space complexity vs flat registers | More code to maintain | Keep node structure simple and consistent across device types |
| Docker image size increase | Larger pull times | `asyncua` is pure Python, minimal size impact |

---

## 8. Success Criteria

The implementation is complete when:

- [ ] 3 OPC-UA device types are running in Docker alongside Modbus and MQTT
- [ ] `GET /status` shows `opcua` in the protocols list
- [ ] `GET /devices` includes OPC-UA devices with correct status
- [ ] `GET /devices/{id}/data` returns structured node values for each device type
- [ ] An external OPC-UA client (e.g., UaExpert, Prosys) can connect and browse nodes
- [ ] Frontend Dashboard shows OPC-UA protocol and devices
- [ ] Frontend DataMonitor streams and formats OPC-UA data
- [ ] All unit tests pass
- [ ] Docker container starts with all 3 protocols in < 10 seconds
- [ ] Health check shows 100% for all devices
