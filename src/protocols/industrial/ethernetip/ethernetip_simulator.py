"""
EtherNet/IP Device Simulator

Implements Allen-Bradley style EtherNet/IP devices (ControlLogix PLC,
PowerFlex VFD drive, CompactLogix I/O module) using a custom asyncio
CIP/TCP server on port 44818+.

Each device owns one CIPServer listening on its allocated port. Data is
shared via a plain dict (tag_store) between the device (writer) and the
server (reader) — safe because asyncio is single-threaded.
"""

import asyncio
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog

from ....config_parser import EtherNetIPConfig, EtherNetIPDeviceConfig
from ....port_manager import IntelligentPortManager
from ....data_patterns.industrial_patterns import IndustrialDataGenerator
from .cip_constants import CIPDataType
from .cip_server import CIPServer

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Tag store definitions: {tag_name: {"type_code": int, "value": Any, "element_count": int}}
# ---------------------------------------------------------------------------

def _controllogix_initial_tags() -> Dict[str, Dict[str, Any]]:
    return {
        "ProcessValue":  {"type_code": CIPDataType.REAL, "value": 0.0,   "element_count": 1},
        "Setpoint":      {"type_code": CIPDataType.REAL, "value": 50.0,  "element_count": 1},
        "ControlOutput": {"type_code": CIPDataType.REAL, "value": 0.0,   "element_count": 1},
        "Mode":          {"type_code": CIPDataType.INT,  "value": 1,     "element_count": 1},
        "HighAlarm":     {"type_code": CIPDataType.BOOL, "value": False,  "element_count": 1},
        "LowAlarm":      {"type_code": CIPDataType.BOOL, "value": False,  "element_count": 1},
        "Error":         {"type_code": CIPDataType.REAL, "value": 0.0,   "element_count": 1},
        "CycleTime":     {"type_code": CIPDataType.DINT, "value": 1000,  "element_count": 1},
        "BatchCount":    {"type_code": CIPDataType.DINT, "value": 0,     "element_count": 1},
        "RunStatus":     {"type_code": CIPDataType.BOOL, "value": True,  "element_count": 1},
    }


def _powerflex_initial_tags() -> Dict[str, Dict[str, Any]]:
    return {
        "OutputFrequency": {"type_code": CIPDataType.REAL, "value": 0.0,   "element_count": 1},
        "OutputVoltage":   {"type_code": CIPDataType.REAL, "value": 0.0,   "element_count": 1},
        "OutputCurrent":   {"type_code": CIPDataType.REAL, "value": 0.0,   "element_count": 1},
        "MotorSpeed":      {"type_code": CIPDataType.DINT, "value": 0,     "element_count": 1},
        "Torque":          {"type_code": CIPDataType.REAL, "value": 0.0,   "element_count": 1},
        "DCBusVoltage":    {"type_code": CIPDataType.REAL, "value": 650.0, "element_count": 1},
        "DriveTemp":       {"type_code": CIPDataType.REAL, "value": 25.0,  "element_count": 1},
        "FaultCode":       {"type_code": CIPDataType.INT,  "value": 0,     "element_count": 1},
        "RunStatus":       {"type_code": CIPDataType.INT,  "value": 0,     "element_count": 1},
        "AccelTime":       {"type_code": CIPDataType.REAL, "value": 5.0,   "element_count": 1},
    }


def _io_module_initial_tags() -> Dict[str, Dict[str, Any]]:
    return {
        "DI_Word":      {"type_code": CIPDataType.DINT, "value": [0, 0, 0, 0], "element_count": 4},
        "DO_Word":      {"type_code": CIPDataType.DINT, "value": [0, 0, 0, 0], "element_count": 4},
        "AI_Channel":   {"type_code": CIPDataType.REAL, "value": [0.0] * 8,    "element_count": 8},
        "AO_Channel":   {"type_code": CIPDataType.REAL, "value": [0.0] * 4,    "element_count": 4},
        "ModuleStatus": {"type_code": CIPDataType.INT,  "value": 0,            "element_count": 1},
        "SlotNumber":   {"type_code": CIPDataType.DINT, "value": 1,            "element_count": 1},
    }


# ---------------------------------------------------------------------------
# EtherNetIPDevice
# ---------------------------------------------------------------------------

class EtherNetIPDevice:
    """
    Represents a single EtherNet/IP device with a CIP/TCP server.

    The device maintains a tag_store dict and a data generator. The generator
    updates tag values on each tick; the CIPServer exposes them to clients.
    """

    def __init__(self, device_id: str, device_config: EtherNetIPDeviceConfig, port: int):
        self.device_id = device_id
        self.device_config = device_config
        self.port = port
        self.device_type = self._extract_device_type(device_config.device_template)
        self.running = False
        self.update_task: Optional[asyncio.Task] = None

        # Tag store: shared with CIPServer (single asyncio thread, no locking needed)
        self.tag_store: Dict[str, Dict[str, Any]] = {}

        # Data generator
        pattern_config = device_config.data_config or {}
        self.data_generator = IndustrialDataGenerator(device_id, pattern_config)

        # CIP server
        device_info = self._build_device_info()
        self.cip_server = CIPServer(
            host="0.0.0.0",
            port=port,
            device_info=device_info,
            tag_store=self.tag_store,
        )

        self.health_status: Dict[str, Any] = {
            "status": "stopped",
            "last_update": None,
            "error_count": 0,
            "uptime_start": None,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_device_type(self, template_name: str) -> str:
        type_mapping = {
            "eip_controllogix_plc": "controllogix_plc",
            "eip_powerflex_drive":  "powerflex_drive",
            "eip_io_module":        "io_module",
        }
        return type_mapping.get(template_name, "controllogix_plc")

    def _build_device_info(self) -> Dict[str, Any]:
        """Build device identity info used by ListIdentity and RegisterSession."""
        serial = random.randint(0x10000000, 0x7FFFFFFF)
        product_names = {
            "controllogix_plc": "ControlLogix 5580 PLC",
            "powerflex_drive":  "PowerFlex 755 Drive",
            "io_module":        "CompactLogix 5069 I/O",
        }
        return {
            "vendor_id":    0x0001,    # Rockwell Automation
            "device_type":  0x000E,    # PLC
            "product_code": 0x0014,
            "revision_major": 1,
            "revision_minor": 1,
            "serial_number": serial,
            "product_name":  product_names.get(self.device_type, "EIP Device"),
        }

    def _initialize_tag_store(self) -> None:
        """Populate the tag store with device-type specific initial values."""
        if self.device_type == "controllogix_plc":
            self.tag_store.update(_controllogix_initial_tags())
        elif self.device_type == "powerflex_drive":
            self.tag_store.update(_powerflex_initial_tags())
        elif self.device_type == "io_module":
            tags = _io_module_initial_tags()
            # Apply configured slot number
            slot = (self.device_config.data_config or {}).get("slot_number", 1)
            tags["SlotNumber"]["value"] = slot
            self.tag_store.update(tags)
        else:
            # Generic fallback
            self.tag_store.update(_controllogix_initial_tags())

    # ------------------------------------------------------------------
    # Tag update helpers
    # ------------------------------------------------------------------

    def _update_controllogix_tags(self, data: Dict[str, Any]) -> None:
        self.tag_store["ProcessValue"]["value"]  = float(data.get("process_value", 0.0))
        self.tag_store["Setpoint"]["value"]      = float(data.get("setpoint", 50.0))
        self.tag_store["ControlOutput"]["value"] = float(data.get("control_output", 0.0))
        self.tag_store["Mode"]["value"]          = int(data.get("mode", 1))
        self.tag_store["HighAlarm"]["value"]     = bool(data.get("high_alarm", False))
        self.tag_store["LowAlarm"]["value"]      = bool(data.get("low_alarm", False))
        self.tag_store["Error"]["value"]         = float(data.get("error", 0.0))
        self.tag_store["CycleTime"]["value"]     = int(data.get("cycle_time_ms", 1000))
        self.tag_store["BatchCount"]["value"]    = int(data.get("batch_count", 0))
        self.tag_store["RunStatus"]["value"]     = bool(data.get("run_status", True))

    def _update_powerflex_tags(self, data: Dict[str, Any]) -> None:
        self.tag_store["OutputFrequency"]["value"] = float(data.get("output_frequency", 0.0))
        self.tag_store["OutputVoltage"]["value"]   = float(data.get("output_voltage", 0.0))
        self.tag_store["OutputCurrent"]["value"]   = float(data.get("output_current", 0.0))
        self.tag_store["MotorSpeed"]["value"]      = int(data.get("motor_speed_rpm", 0))
        self.tag_store["Torque"]["value"]          = float(data.get("torque", 0.0))
        self.tag_store["DCBusVoltage"]["value"]    = float(data.get("dc_bus_voltage", 650.0))
        self.tag_store["DriveTemp"]["value"]       = float(data.get("drive_temp", 25.0))
        self.tag_store["FaultCode"]["value"]       = int(data.get("fault_code", 0))
        self.tag_store["RunStatus"]["value"]       = int(data.get("run_status", 0))
        self.tag_store["AccelTime"]["value"]       = float(data.get("accel_time", 5.0))

    def _update_io_module_tags(self, data: Dict[str, Any]) -> None:
        self.tag_store["DI_Word"]["value"]      = [int(w) for w in data.get("di_words", [0]*4)]
        self.tag_store["DO_Word"]["value"]      = [int(w) for w in data.get("do_words", [0]*4)]
        self.tag_store["AI_Channel"]["value"]   = [float(v) for v in data.get("ai_channels", [0.0]*8)]
        self.tag_store["AO_Channel"]["value"]   = [float(v) for v in data.get("ao_channels", [0.0]*4)]
        self.tag_store["ModuleStatus"]["value"] = int(data.get("module_status", 0))
        self.tag_store["SlotNumber"]["value"]   = int(data.get("slot_number", 1))

    async def _update_tag_values(self) -> None:
        """Generate new data and write it to the tag store."""
        try:
            device_data = self.data_generator.generate_device_data(self.device_type)
            if self.device_type == "controllogix_plc":
                self._update_controllogix_tags(device_data)
            elif self.device_type == "powerflex_drive":
                self._update_powerflex_tags(device_data)
            elif self.device_type == "io_module":
                self._update_io_module_tags(device_data)
            self.health_status["last_update"] = time.time()
        except Exception as e:
            logger.error(
                "Error updating EtherNet/IP tag values",
                device_id=self.device_id,
                error=str(e),
            )
            self.health_status["error_count"] += 1

    async def _data_update_loop(self) -> None:
        """Continuous loop to update tag values at configured interval."""
        try:
            while self.running:
                await self._update_tag_values()
                await asyncio.sleep(self.device_config.update_interval)
        except asyncio.CancelledError:
            logger.info(f"EtherNet/IP data update loop cancelled for {self.device_id}")
        except Exception as e:
            logger.error(
                "Error in EtherNet/IP data update loop",
                device_id=self.device_id,
                error=str(e),
            )
            self.health_status["error_count"] += 1

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> bool:
        """Start the CIP server and data update loop."""
        try:
            logger.info(
                "Starting EtherNet/IP device",
                device_id=self.device_id,
                device_type=self.device_type,
                port=self.port,
            )

            # Initialise tag store with zeros
            self._initialize_tag_store()

            # Run one update so clients see real data immediately
            await self._update_tag_values()

            # Start CIP TCP server
            if not await self.cip_server.start():
                logger.error("CIP server failed to start", device_id=self.device_id)
                return False

            # Start data update task
            self.running = True
            self.update_task = asyncio.create_task(self._data_update_loop())

            self.health_status.update({
                "status": "running",
                "uptime_start": time.time(),
                "error_count": 0,
            })

            logger.info(
                "EtherNet/IP device started",
                device_id=self.device_id,
                port=self.port,
                tag_count=len(self.tag_store),
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to start EtherNet/IP device",
                device_id=self.device_id,
                error=str(e),
            )
            return False

    async def stop(self) -> None:
        """Stop the data update loop and CIP server."""
        try:
            logger.info(f"Stopping EtherNet/IP device {self.device_id}")

            self.running = False

            if self.update_task and not self.update_task.done():
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass

            await self.cip_server.stop()

            self.health_status["status"] = "stopped"
            logger.info(f"EtherNet/IP device {self.device_id} stopped")

        except Exception as e:
            logger.error(
                "Error stopping EtherNet/IP device",
                device_id=self.device_id,
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Status / data access
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return device status dict."""
        uptime = 0.0
        if self.health_status.get("uptime_start"):
            uptime = time.time() - self.health_status["uptime_start"]
        return {
            "device_id":       self.device_id,
            "device_type":     self.device_type,
            "template":        self.device_config.device_template,
            "port":            self.port,
            "endpoint":        f"tcp://0.0.0.0:{self.port}",
            "status":          self.health_status["status"],
            "running":         self.running,
            "uptime_seconds":  round(uptime, 2),
            "error_count":     self.health_status["error_count"],
            "last_update":     self.health_status.get("last_update"),
            "update_interval": self.device_config.update_interval,
            "tag_count":       len(self.tag_store),
            "session_count":   self.cip_server.get_session_count(),
        }

    def get_tag_data(self) -> Optional[Dict[str, Any]]:
        """
        Return current tag values plus device metadata.

        Returns None if the device is not yet running (no data generated).
        """
        if not self.running and not self.health_status.get("last_update"):
            return None

        tags = {}
        for name, entry in self.tag_store.items():
            tags[name] = {
                "type":  CIPDataType.type_name(entry["type_code"]),
                "value": entry["value"],
                "count": entry["element_count"],
            }

        return {
            "device_id":   self.device_id,
            "device_type": self.device_type,
            "port":        self.port,
            "timestamp":   self.health_status.get("last_update"),
            "tags":        tags,
        }


# ---------------------------------------------------------------------------
# EtherNetIPDeviceManager
# ---------------------------------------------------------------------------

class EtherNetIPDeviceManager:
    """
    Manages multiple EtherNet/IP devices and their CIP servers.
    """

    def __init__(self, eip_config: EtherNetIPConfig, port_manager: IntelligentPortManager):
        self.eip_config = eip_config
        self.port_manager = port_manager
        self.devices: Dict[str, EtherNetIPDevice] = {}
        # device_id → ("ethernet_ip", port_count)
        self.device_allocation_plan: Dict[str, Tuple[str, int]] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self) -> bool:
        """Build allocation plan and create device instances."""
        try:
            logger.info("Initializing EtherNet/IP Device Manager...")

            self._build_allocation_plan()
            await self._create_devices()

            logger.info(
                "EtherNet/IP Device Manager initialized",
                device_count=len(self.devices),
                device_types=list(self.eip_config.devices.keys()),
            )
            return True

        except Exception as e:
            logger.error("Failed to initialize EtherNet/IP Device Manager", error=str(e))
            return False

    def _build_allocation_plan(self) -> None:
        """Register all devices in the allocation plan."""
        self.device_allocation_plan = {}
        for device_type, device_config in self.eip_config.devices.items():
            for i in range(device_config.count):
                device_id = f"eip_{device_type}_{i:03d}"
                self.device_allocation_plan[device_id] = ("ethernet_ip", 1)

    async def _create_devices(self) -> None:
        """Instantiate all EtherNetIPDevice objects with allocated ports."""
        for device_type, device_config in self.eip_config.devices.items():
            logger.info(f"Creating {device_config.count} {device_type} EtherNet/IP devices...")

            for i in range(device_config.count):
                device_id = f"eip_{device_type}_{i:03d}"

                # Allocate 1 port per device
                allocated_ports = self.port_manager.allocate_ports(
                    "ethernet_ip",
                    device_id,
                    1,
                    preferred_start=device_config.port_start + i,
                )

                if not allocated_ports:
                    logger.error(
                        "Failed to allocate port for EtherNet/IP device",
                        device_id=device_id,
                    )
                    continue

                port = allocated_ports[0]
                device = EtherNetIPDevice(device_id, device_config, port)
                self.devices[device_id] = device

    def get_allocation_requirements(self) -> Dict[str, Tuple[str, int]]:
        """Return port allocation requirements for validation.

        Returns a copy of the allocation plan in the format expected by
        IntelligentPortManager.validate_allocation_plan():
            {device_id: (protocol, port_count)}
        """
        return self.device_allocation_plan.copy()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_all_devices(self) -> Optional[Dict[str, "EtherNetIPDevice"]]:
        """Start all EtherNet/IP devices concurrently.

        Returns:
            Dict mapping device_id → EtherNetIPDevice for successfully started
            devices, or None if all failed.
        """
        if not self.devices:
            logger.warning("No EtherNet/IP devices to start")
            return None

        logger.info(f"Starting {len(self.devices)} EtherNet/IP devices...")

        started_devices: Dict[str, "EtherNetIPDevice"] = {}
        failed_devices: List[str] = []

        async def _start_one(device_id: str, device: "EtherNetIPDevice") -> None:
            if await device.start():
                started_devices[device_id] = device
            else:
                failed_devices.append(device_id)

        await asyncio.gather(
            *[_start_one(did, dev) for did, dev in self.devices.items()],
            return_exceptions=True,
        )

        if failed_devices:
            logger.warning(
                "Some EtherNet/IP devices failed to start",
                failed_count=len(failed_devices),
                failed_devices=failed_devices,
            )

        logger.info(
            "EtherNet/IP device startup complete",
            started=len(started_devices),
            failed=len(failed_devices),
        )

        return started_devices if started_devices else None

    async def stop_all_devices(self) -> None:
        """Stop all EtherNet/IP devices."""
        logger.info(f"Stopping {len(self.devices)} EtherNet/IP devices...")
        await asyncio.gather(
            *[device.stop() for device in self.devices.values()],
            return_exceptions=True,
        )

    # ------------------------------------------------------------------
    # Health / status
    # ------------------------------------------------------------------

    async def get_health_status(self) -> Dict[str, Any]:
        """Return health status for all devices (flat device_id → status dict)."""
        return {
            device_id: device.get_status()
            for device_id, device in self.devices.items()
        }

    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Return status for a single device."""
        device = self.devices.get(device_id)
        return device.get_status() if device else None

    async def restart_device(self, device_id: str) -> bool:
        """Stop and restart a single device."""
        device = self.devices.get(device_id)
        if not device:
            logger.error(f"Cannot restart unknown device: {device_id}")
            return False
        await device.stop()
        await asyncio.sleep(0.5)
        return await device.start()

    def get_all_device_endpoints(self) -> List[Dict[str, Any]]:
        """Return list of CIP TCP endpoint info for all devices."""
        return [
            {
                "device_id":   device_id,
                "device_type": device.device_type,
                "host":        "0.0.0.0",
                "port":        device.port,
                "endpoint":    f"tcp://0.0.0.0:{device.port}",
                "tag_count":   len(device.tag_store),
                "running":     device.running,
            }
            for device_id, device in self.devices.items()
        ]
