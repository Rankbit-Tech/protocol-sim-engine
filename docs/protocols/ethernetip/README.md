# EtherNet/IP Protocol Guide

**EtherNet/IP (CIP over TCP/UDP) simulation for Allen-Bradley industrial devices**

Version: 0.5.0 | Status: Production Ready | Updated: February 24, 2026

---

## Overview

EtherNet/IP is the most widely deployed industrial Ethernet protocol in North America. It layers the **Common Industrial Protocol (CIP)** over standard TCP/IP, running on TCP port 44818. Allen-Bradley (Rockwell Automation) PLCs (ControlLogix, CompactLogix), drives (PowerFlex), and I/O modules all speak EtherNet/IP.

The simulator implements a **real CIP-over-TCP server** — not a stub or mock. Any standard EtherNet/IP client can connect on port 44818+, register a session, and read/write tags using the same wire format as physical hardware.

### Protocol Stack

```
Application Layer   CIP Services (ReadTag, WriteTag, MultipleServicePacket)
                         ↓
Transport Layer     CIP Encapsulation (24-byte header, SendRRData)
                         ↓
Session Layer       RegisterSession / UnregisterSession
                         ↓
Network Layer       TCP/IP (port 44818 per device)
```

---

## Quick Start

```bash
docker run -d --name protocol-sim \
  -p 8080:8080 \
  -p 44818-44820:44818-44820 \
  developeryashsolanki/protocol-sim-engine:0.5.0

# List EtherNet/IP device endpoints
curl http://localhost:8080/ethernetip/connections

# Read all tags from ControlLogix PLC
curl http://localhost:8080/ethernetip/devices/eip_controllogix_plcs_000/tags
```

---

## Device Types

### ControlLogix 5580 PLC (`eip_controllogix_plc`)

Simulates a Rockwell Automation ControlLogix PLC running a PID process control loop.

**CIP Tags:**

| Tag | Type | Description |
|-----|------|-------------|
| `ProcessValue` | REAL | Current process variable (PV) |
| `Setpoint` | REAL | PID setpoint (SP) |
| `ControlOutput` | REAL | PID output (0–100%) |
| `Mode` | INT | 0=MANUAL, 1=AUTO, 2=CASCADE |
| `HighAlarm` | BOOL | PV exceeded high threshold |
| `LowAlarm` | BOOL | PV fell below low threshold |
| `Error` | REAL | SP − PV |
| `CycleTime` | DINT | Scan cycle time (ms) |
| `BatchCount` | DINT | Completed batch count |
| `RunStatus` | BOOL | True when running (not MANUAL) |

**Configuration:**

```yaml
industrial_protocols:
  ethernet_ip:
    enabled: true
    devices:
      controllogix_plcs:
        count: 1
        port_start: 44818
        device_template: "eip_controllogix_plc"
        update_interval: 1.0
        data_config:
          process_value_range: [0, 100]
          setpoint: 50.0
          kp: 1.0        # Proportional gain
          ki: 0.1        # Integral gain
          kd: 0.05       # Derivative gain
          high_alarm: 90
          low_alarm: 10
          cycle_time_ms: 1000
```

---

### PowerFlex 755 VFD Drive (`eip_powerflex_drive`)

Simulates a Rockwell Automation PowerFlex 755 variable frequency drive with a physics-based 4-state machine.

**Drive States:**

| State | RunStatus Value | Description |
|-------|----------------|-------------|
| Stopped | 0 | Drive stopped, frequency decaying |
| Forward | 1 | Running forward, frequency ramping to target |
| Reverse | 2 | Running in reverse |
| Fault | 3 | Fault condition, FaultCode set |

**State Transition Probabilities (per tick):**

- Stopped → Forward: 10%
- Forward → Stopped: 3%
- Forward → Reverse: 1%
- Forward → Fault: 0.5%
- Fault → Stopped: 30% (after ≥10 ticks in fault)

**CIP Tags:**

| Tag | Type | Description |
|-----|------|-------------|
| `OutputFrequency` | REAL | Output frequency (Hz) |
| `OutputVoltage` | REAL | Output voltage (V = freq × V/Hz) |
| `OutputCurrent` | REAL | Motor current (A) |
| `MotorSpeed` | DINT | Motor speed (RPM = freq × 30) |
| `Torque` | REAL | Motor torque (Nm) |
| `DCBusVoltage` | REAL | DC bus voltage (~650V) |
| `DriveTemp` | REAL | Heat sink temperature (°C) |
| `FaultCode` | INT | 0=none, 1/2/3=fault types |
| `RunStatus` | INT | 0=Stopped, 1=Forward, 2=Reverse, 3=Fault |
| `AccelTime` | REAL | Acceleration ramp time (s) |

**Configuration:**

```yaml
      powerflex_drives:
        count: 1
        port_start: 44819
        device_template: "eip_powerflex_drive"
        update_interval: 0.5
        data_config:
          frequency_range: [0, 60]    # Hz
          base_frequency: 50.0        # Hz target when running
          max_current: 50.0           # A at full load
          v_per_hz: 7.6               # Volts per Hz (V/f ratio)
          max_torque: 500             # Nm maximum
          accel_time: 5.0             # Seconds to reach full speed
```

---

### CompactLogix I/O Module (`eip_io_module`)

Simulates a CompactLogix digital/analog I/O module with 128 digital I/O bits and 12 analog channels.

**CIP Tags:**

| Tag | Type | Description |
|-----|------|-------------|
| `DI_Word` | DINT[4] | 4 × 32-bit digital input words (128 DI bits total) |
| `DO_Word` | DINT[4] | 4 × 32-bit digital output words (128 DO bits total) |
| `AI_Channel` | REAL[8] | 8 analog input channels (0–100% engineering units) |
| `AO_Channel` | REAL[4] | 4 analog output channels (0–100%, stable setpoints) |
| `ModuleStatus` | INT | 0=OK, 1=WARNING, 2=FAULT |
| `SlotNumber` | DINT | Chassis slot number |

**Simulation Behaviour:**

- **Digital Inputs**: Each bit has a 5% probability of toggling per update tick
- **Digital Outputs**: Mirror DI bits with a 30% probability lag per word per tick
- **Analog Inputs**: Random-walk ±0.5% per tick, clamped 0–100%
- **Analog Outputs**: Hold stable setpoints from `data_config` with ±0.1% noise

**Configuration:**

```yaml
      io_modules:
        count: 1
        port_start: 44820
        device_template: "eip_io_module"
        update_interval: 0.5
        data_config:
          slot_number: 1
          ao_0_setpoint: 50.0   # AO channel 0 setpoint (%)
          ao_1_setpoint: 25.0   # AO channel 1 setpoint (%)
          ao_2_setpoint: 75.0   # AO channel 2 setpoint (%)
          ao_3_setpoint: 50.0   # AO channel 3 setpoint (%)
```

---

## Connecting with EtherNet/IP Clients

### pycomm3 (Python)

```python
from pycomm3 import CIPDriver

# Connect to ControlLogix PLC (port 44818)
with CIPDriver("localhost:44818") as plc:
    # Read multiple tags in one request
    tags = plc.read("ProcessValue", "Setpoint", "Mode", "HighAlarm")
    print(f"PV: {tags[0].value:.2f}")
    print(f"SP: {tags[1].value:.2f}")
    print(f"Mode: {['MANUAL','AUTO','CASCADE'][tags[2].value]}")
    print(f"High Alarm: {tags[3].value}")

    # Write a tag
    plc.write(("Setpoint", 75.0))
```

```python
# Connect to PowerFlex drive (port 44819)
with CIPDriver("localhost:44819") as drive:
    tags = drive.read("OutputFrequency", "MotorSpeed", "RunStatus", "DriveTemp")
    status_map = {0: "STOPPED", 1: "FORWARD", 2: "REVERSE", 3: "FAULT"}
    print(f"{tags[0].value:.1f} Hz  |  {tags[1].value} RPM  |  {status_map[tags[3].value]}")
```

### Raw TCP / Python asyncio

```python
import asyncio, struct

async def read_tag(host: str, port: int, tag_name: str):
    reader, writer = await asyncio.open_connection(host, port)

    # RegisterSession
    reg_request = struct.pack("<HHIIQII", 0x0065, 4, 0, 0, 0, 1, 0)
    writer.write(reg_request)
    response = await reader.readexactly(28)
    session_handle = struct.unpack("<I", response[4:8])[0]
    print(f"Session: {session_handle:#010x}")

    writer.close()
    await writer.wait_closed()

asyncio.run(read_tag("localhost", 44818, "ProcessValue"))
```

---

## REST API

### `GET /ethernetip/connections`

Returns all EtherNet/IP device endpoints.

```bash
curl http://localhost:8080/ethernetip/connections
```

```json
{
  "connection_count": 3,
  "connections": [
    {
      "device_id": "eip_controllogix_plcs_000",
      "device_type": "controllogix_plc",
      "host": "0.0.0.0",
      "port": 44818,
      "endpoint": "tcp://0.0.0.0:44818",
      "tag_count": 10,
      "running": true
    },
    {
      "device_id": "eip_powerflex_drives_000",
      "device_type": "powerflex_drive",
      "host": "0.0.0.0",
      "port": 44819,
      "endpoint": "tcp://0.0.0.0:44819",
      "tag_count": 10,
      "running": true
    },
    {
      "device_id": "eip_io_modules_000",
      "device_type": "io_module",
      "host": "0.0.0.0",
      "port": 44820,
      "endpoint": "tcp://0.0.0.0:44820",
      "tag_count": 6,
      "running": true
    }
  ]
}
```

### `GET /ethernetip/devices/{device_id}/tags`

Returns current tag values for a specific device.

```bash
curl http://localhost:8080/ethernetip/devices/eip_controllogix_plcs_000/tags
```

```json
{
  "device_id": "eip_controllogix_plcs_000",
  "device_type": "controllogix_plc",
  "port": 44818,
  "timestamp": 1771937003.26,
  "tags": {
    "ProcessValue": { "type": "REAL", "value": 44.46, "count": 1 },
    "Setpoint":     { "type": "REAL", "value": 50.0,  "count": 1 },
    "ControlOutput":{ "type": "REAL", "value": 68.18, "count": 1 },
    "Mode":         { "type": "INT",  "value": 1,     "count": 1 },
    "HighAlarm":    { "type": "BOOL", "value": false,  "count": 1 },
    "LowAlarm":     { "type": "BOOL", "value": false,  "count": 1 },
    "Error":        { "type": "REAL", "value": 5.54,  "count": 1 },
    "CycleTime":    { "type": "DINT", "value": 1000,  "count": 1 },
    "BatchCount":   { "type": "DINT", "value": 12,    "count": 1 },
    "RunStatus":    { "type": "BOOL", "value": true,   "count": 1 }
  }
}
```

### Generic device data endpoint

The standard `/devices/{id}/data` endpoint also works:

```bash
curl http://localhost:8080/devices/eip_powerflex_drives_000/data
```

---

## CIP Protocol Implementation

### Supported Commands (Encapsulation Layer)

| Command | Code | Description |
|---------|------|-------------|
| `ListIdentity` | 0x0063 | Device identification (Vendor ID, product name, etc.) |
| `RegisterSession` | 0x0065 | Open a session, receive session handle |
| `UnregisterSession` | 0x0066 | Close a session |
| `SendRRData` | 0x006F | Send a request/reply data item (main service transport) |

### Supported CIP Services

| Service | Code | Description |
|---------|------|-------------|
| `ReadTag` | 0x4C | Read a tag by name (returns type + value) |
| `WriteTag` | 0x4D | Write a value to a tag by name |
| `MultipleServicePacket` | 0x0A | Bundle multiple reads/writes in one request |

### CIP Data Types

| Type | Code | Python mapping |
|------|------|---------------|
| `BOOL` | 0xC1 | bool |
| `INT` | 0xC3 | int (16-bit signed) |
| `DINT` | 0xC4 | int (32-bit signed) |
| `REAL` | 0xCA | float (32-bit IEEE-754) |
| Arrays | — | list of the above types |

---

## Architecture

### File Structure

```
src/protocols/industrial/ethernetip/
├── __init__.py
├── cip_constants.py        # CIP command/service/type codes
├── cip_protocol.py         # Pure encode/decode functions (no I/O)
├── cip_server.py           # asyncio TCP server (CIPServer class)
└── ethernetip_simulator.py # EtherNetIPDevice + EtherNetIPDeviceManager
```

### How It Works

```
EtherNetIPDevice
  ├── tag_store: dict          # Shared data store (no lock needed — asyncio)
  │     ├── "ProcessValue": {"type_code": 0xCA, "value": 44.5, "element_count": 1}
  │     └── ...
  ├── CIPServer               # asyncio TCP on port 44818
  │     ├── sessions: dict    # {handle → client_addr}
  │     └── Per-client loop:
  │           readexactly(24) → decode header
  │           readexactly(length) → dispatch command
  │           encode response → write to socket
  └── _data_update_loop()     # Updates tag_store every update_interval seconds
```

Each device owns one `CIPServer` instance. The `tag_store` is a plain dict shared between the device (writer) and the server (reader) — safe because asyncio is single-threaded.

---

## Network Configuration

```yaml
network:
  port_ranges:
    ethernet_ip: [44818, 44918]   # Pool of 100 ports

industrial_protocols:
  ethernet_ip:
    enabled: true
    devices:
      controllogix_plcs:
        port_start: 44818         # First device gets this port
        count: 3                  # Three devices → ports 44818, 44819, 44820
```

Port allocation is automatic — devices get consecutive ports starting from `port_start`, validated against the `ethernet_ip` pool to prevent conflicts.

---

## Troubleshooting

### Client cannot connect

- Verify the port is exposed in Docker: `-p 44818-44820:44818-44820`
- Confirm device is running: `curl http://localhost:8080/ethernetip/connections`
- Check container logs: `docker logs protocol-sim`

### Tag not found error

- Tag names are case-sensitive (`ProcessValue` not `processvalue`)
- Use the REST API to list available tags: `GET /ethernetip/devices/{id}/tags`
- Array tags use the form `AI_Channel` (returns full array); element access (`AI_Channel[0]`) is not supported by the current ReadTag service but can be done via the REST API

### Wrong data type error on WriteTag

- The type code in your write request must match the tag's registered type
- Read the tag first to confirm its `type` field, then use the matching CIP type code

---

## Compatibility

Tested with:
- **pycomm3** ≥ 0.12 (Python EtherNet/IP client)
- **Wireshark** with EtherNet/IP dissector (for packet inspection)

Standard EtherNet/IP clients that implement the CIP encapsulation spec should work. UCMM (Unconnected Message Manager) is the communication path used — implicit/class 1 connected messaging (I/O scanning) is not implemented.

---

## Related Documentation

- [README.md](../../../README.md) — Project overview and quick start
- [Implementation Summary](../../IMPLEMENTATION_SUMMARY.md) — Full platform details
- [Modbus TCP Guide](../modbus/README.md) — Modbus protocol docs
- [MQTT Guide](../mqtt/README.md) — MQTT IoT sensor docs
- [OPC-UA Guide](../opcua/README.md) — OPC-UA server docs
