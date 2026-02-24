# v0.5.0 - EtherNet/IP (CIP) Protocol Support

## Release v0.5.0 - EtherNet/IP Protocol

### What's New

#### EtherNet/IP Protocol Support

The simulator now supports **EtherNet/IP**, the dominant industrial Ethernet protocol used by Allen-Bradley (Rockwell Automation) PLCs and drives across North American manufacturing. Three new device types simulate real Allen-Bradley hardware, each running its own CIP-over-TCP server on port 44818+.

Unlike a superficial mock, this implementation speaks the real **CIP (Common Industrial Protocol) wire format** — any standard EtherNet/IP client (pycomm3, Ignition SCADA, FactoryTalk, UaGateway) can connect and read/write tags without modification.

**ControlLogix 5580 PLC** (`eip_controllogix_plc`)

- PID control loop: ProcessValue, Setpoint, ControlOutput, Mode, HighAlarm, LowAlarm, Error
- Operational tags: CycleTime (DINT, ms), BatchCount (DINT), RunStatus (BOOL)
- Mode switching: AUTO (1), MANUAL (0), CASCADE (2)
- BatchCount auto-increments when process is within setpoint tolerance

**PowerFlex 755 Drive** (`eip_powerflex_drive`)

- 4-state machine: Stopped → Forward → Reverse → Fault (probabilistic transitions)
- Physics-based data: `OutputFrequency` ramps with acceleration time; `OutputVoltage = freq × V/Hz`; `DriveTemp` exponentially approaches thermal equilibrium
- Tags: OutputFrequency, OutputVoltage, OutputCurrent, MotorSpeed (RPM), Torque, DCBusVoltage, DriveTemp, FaultCode, RunStatus, AccelTime

**CompactLogix I/O Module** (`eip_io_module`)

- 16 DI bits (4 × DINT), 16 DO bits (4 × DINT), 8 AI channels (REAL), 4 AO channels (REAL)
- Realistic simulation: DI bits flip at 5% probability per tick; DO mirrors DI at 30% lag; AI channels random-walk ±0.5%/tick; AO channels hold stable setpoints
- Tags: DI_Word[4], DO_Word[4], AI_Channel[8], AO_Channel[4], ModuleStatus, SlotNumber

#### CIP Server Architecture

Each EtherNet/IP device runs a dedicated asyncio TCP server:

- **RegisterSession** (0x0065) / **UnregisterSession** (0x0066) — full session lifecycle
- **SendRRData** (0x006F) — CIP service dispatcher with session validation
- **ReadTag** (0x4C) — read any tag by EPATH symbolic name
- **WriteTag** (0x4D) — write any tag (type-checked)
- **MultipleServicePacket** (0x0A) — batch read/write in a single request
- CIP data types: BOOL, INT, DINT, REAL, and typed arrays (e.g. REAL[8])
- Default port range: 44818-44820 (configurable per device)

#### New API Endpoints

- `GET /ethernetip/connections` — List all CIP server endpoints with tag count and active session count
- `GET /ethernetip/devices/{id}/tags` — Read all current tag values for a device

#### Frontend Updates

- Data Monitor now displays EtherNet/IP telemetry in a human-readable format:
  - ControlLogix PLC: `PV: 44.5 · SP: 50.0 · Out: 63.2% · Mode: AUTO`
  - PowerFlex Drive: `49.8 Hz · 1493 RPM · 18.3A · 31.2°C · FORWARD`
  - I/O Module: `Slot: 1 · Status: OK · Avg AI: 51.4%`

### Bug Fixes

- Fixed `get_health_status()` in `EtherNetIPDeviceManager` to return the flat `{device_id: status_dict}` format expected by the orchestrator health aggregation loop.

### Infrastructure

- Docker image exposes EtherNet/IP ports (44818-44820)
- No new Python dependencies — CIP protocol implemented in pure asyncio (same approach as OPC-UA)
- New `ethernet_ip:` section in `config/default_config.yml` and `config/test_all_protocols.yml`
- New test suite: 71 tests across 8 test classes covering codec, device lifecycle, server logic, data patterns, configuration, and scalability

### Upgrade Notes

No breaking changes. The API and existing Modbus/MQTT/OPC-UA functionality remain unchanged. Simply pull the new image:

```bash
docker pull developeryashsolanki/protocol-sim-engine:0.5.0
```

Running with all four protocols:

```bash
docker run -d \
  --name protocol-sim \
  -p 8080:8080 \
  -p 1883:1883 \
  -p 15000-15002:15000-15002 \
  -p 4840-4842:4840-4842 \
  -p 44818-44820:44818-44820 \
  developeryashsolanki/protocol-sim-engine:0.5.0
```

This runs **14 devices** across 4 protocols:
- 3 Modbus TCP devices (ports 15000-15002)
- 5 MQTT devices (embedded broker on port 1883)
- 3 OPC-UA devices (ports 4840-4842)
- 3 EtherNet/IP devices (ports 44818-44820)

Connect an EtherNet/IP client:

```python
from pycomm3 import CIPDriver

with CIPDriver("localhost:44818") as plc:
    tags = plc.read("ProcessValue", "Setpoint", "Mode")
    print(f"PV={tags[0].value:.1f}, SP={tags[1].value:.1f}, Mode={tags[2].value}")
```

Access the dashboard at http://localhost:8080
Read EtherNet/IP tags via REST at http://localhost:8080/ethernetip/devices/eip_controllogix_plcs_000/tags
