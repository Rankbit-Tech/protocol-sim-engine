"""
OPC-UA Device Simulator

This module implements realistic OPC-UA device simulation with structured address spaces,
multiple device types, and proper protocol compliance using the asyncua library.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog
from asyncua import Server, ua

from ....config_parser import OPCUAConfig, OPCUADeviceConfig
from ....port_manager import IntelligentPortManager
from ....data_patterns.industrial_patterns import IndustrialDataGenerator

logger = structlog.get_logger(__name__)


class OPCUADevice:
    """
    Represents a single OPC-UA device with a structured address space.

    Each device runs its own OPC-UA server on a dedicated port with
    an address space organized into Identification, Parameters, and Status folders.
    """

    def __init__(self, device_id: str, device_config: OPCUADeviceConfig, port: int,
                 application_uri: str = "urn:protocol-sim-engine:opcua:server"):
        """
        Initialize an OPC-UA device.

        Args:
            device_id: Unique device identifier
            device_config: Device configuration
            port: TCP port for this device's OPC-UA server
            application_uri: OPC-UA application URI
        """
        self.device_id = device_id
        self.device_config = device_config
        self.port = port
        self.application_uri = f"{application_uri}:{device_id}"
        self.device_type = self._extract_device_type(device_config.device_template)
        self.running = False
        self.server: Optional[Server] = None
        self.update_task: Optional[asyncio.Task] = None

        # Initialize data generator with realistic patterns
        pattern_config = device_config.data_config or {}
        self.data_generator = IndustrialDataGenerator(device_id, pattern_config)

        # Node references for value updates (populated during address space build)
        self.nodes: Dict[str, Any] = {}

        # Cached node data for synchronous access (updated by _update_node_values)
        self._cached_node_data: Optional[Dict[str, Any]] = None

        # Track device health
        self.health_status = {
            "status": "stopped",
            "last_update": None,
            "error_count": 0,
            "uptime_start": None
        }

    def _extract_device_type(self, template_name: str) -> str:
        """Extract device type from template name."""
        type_mapping = {
            "opcua_cnc_machine": "cnc_machine",
            "opcua_plc_controller": "plc_controller",
            "opcua_industrial_robot": "industrial_robot"
        }
        return type_mapping.get(template_name, "generic")

    async def _build_address_space(self) -> None:
        """Build the OPC-UA address space with device-specific nodes."""
        idx = await self.server.register_namespace(
            f"urn:protocol-sim-engine:{self.device_id}"
        )

        objects = self.server.nodes.objects

        # Create device folder: Objects > DeviceSet > {DeviceName}
        device_set = await objects.add_folder(idx, "DeviceSet")
        device_folder = await device_set.add_folder(idx, self.device_id)

        # Identification folder
        ident = await device_folder.add_folder(idx, "Identification")
        await ident.add_variable(idx, "Manufacturer", "Protocol Sim Engine")
        await ident.add_variable(idx, "Model", self.device_config.device_template)
        await ident.add_variable(idx, "SerialNumber", self.device_id)

        # Parameters folder (device-type specific, writable values)
        params = await device_folder.add_folder(idx, "Parameters")

        # Status folder
        status_folder = await device_folder.add_folder(idx, "Status")
        self.nodes["DeviceHealth"] = await status_folder.add_variable(
            idx, "DeviceHealth", "NORMAL"
        )
        self.nodes["ErrorCode"] = await status_folder.add_variable(
            idx, "ErrorCode", 0, ua.VariantType.Int32
        )
        self.nodes["OperatingMode"] = await status_folder.add_variable(
            idx, "OperatingMode", "AUTO"
        )

        # Build device-type specific parameters
        if self.device_type == "cnc_machine":
            await self._build_cnc_nodes(idx, params)
        elif self.device_type == "plc_controller":
            await self._build_plc_nodes(idx, params)
        elif self.device_type == "industrial_robot":
            await self._build_robot_nodes(idx, params)

        # Make all parameter nodes writable
        for node in self.nodes.values():
            await node.set_writable()

    async def _build_cnc_nodes(self, idx: int, params: Any) -> None:
        """Build CNC machine address space nodes."""
        self.nodes["SpindleSpeed"] = await params.add_variable(
            idx, "SpindleSpeed", 0.0, ua.VariantType.Double
        )
        self.nodes["FeedRate"] = await params.add_variable(
            idx, "FeedRate", 0.0, ua.VariantType.Double
        )
        self.nodes["ToolWearPercent"] = await params.add_variable(
            idx, "ToolWearPercent", 0.0, ua.VariantType.Double
        )
        self.nodes["PartCount"] = await params.add_variable(
            idx, "PartCount", 0, ua.VariantType.Int32
        )
        self.nodes["AxisPosition_X"] = await params.add_variable(
            idx, "AxisPosition_X", 0.0, ua.VariantType.Double
        )
        self.nodes["AxisPosition_Y"] = await params.add_variable(
            idx, "AxisPosition_Y", 0.0, ua.VariantType.Double
        )
        self.nodes["AxisPosition_Z"] = await params.add_variable(
            idx, "AxisPosition_Z", 0.0, ua.VariantType.Double
        )
        self.nodes["ProgramName"] = await params.add_variable(
            idx, "ProgramName", "G-Code_001"
        )
        self.nodes["MachineState"] = await params.add_variable(
            idx, "MachineState", "IDLE"
        )

    async def _build_plc_nodes(self, idx: int, params: Any) -> None:
        """Build PLC process controller address space nodes."""
        self.nodes["ProcessValue"] = await params.add_variable(
            idx, "ProcessValue", 0.0, ua.VariantType.Double
        )
        self.nodes["Setpoint"] = await params.add_variable(
            idx, "Setpoint", 50.0, ua.VariantType.Double
        )
        self.nodes["ControlOutput"] = await params.add_variable(
            idx, "ControlOutput", 0.0, ua.VariantType.Double
        )
        self.nodes["Mode"] = await params.add_variable(
            idx, "Mode", "AUTO"
        )
        self.nodes["HighAlarm"] = await params.add_variable(
            idx, "HighAlarm", False, ua.VariantType.Boolean
        )
        self.nodes["LowAlarm"] = await params.add_variable(
            idx, "LowAlarm", False, ua.VariantType.Boolean
        )
        self.nodes["IntegralTerm"] = await params.add_variable(
            idx, "IntegralTerm", 0.0, ua.VariantType.Double
        )
        self.nodes["DerivativeTerm"] = await params.add_variable(
            idx, "DerivativeTerm", 0.0, ua.VariantType.Double
        )
        self.nodes["Error"] = await params.add_variable(
            idx, "Error", 0.0, ua.VariantType.Double
        )

    async def _build_robot_nodes(self, idx: int, params: Any) -> None:
        """Build industrial robot address space nodes."""
        joint_count = self.device_config.data_config.get("joint_count", 6) if self.device_config.data_config else 6

        for i in range(joint_count):
            self.nodes[f"JointAngle_{i+1}"] = await params.add_variable(
                idx, f"JointAngle_{i+1}", 0.0, ua.VariantType.Double
            )

        self.nodes["TCPPosition_X"] = await params.add_variable(
            idx, "TCPPosition_X", 0.0, ua.VariantType.Double
        )
        self.nodes["TCPPosition_Y"] = await params.add_variable(
            idx, "TCPPosition_Y", 0.0, ua.VariantType.Double
        )
        self.nodes["TCPPosition_Z"] = await params.add_variable(
            idx, "TCPPosition_Z", 0.0, ua.VariantType.Double
        )
        self.nodes["TCPOrientation_Rx"] = await params.add_variable(
            idx, "TCPOrientation_Rx", 0.0, ua.VariantType.Double
        )
        self.nodes["TCPOrientation_Ry"] = await params.add_variable(
            idx, "TCPOrientation_Ry", 0.0, ua.VariantType.Double
        )
        self.nodes["TCPOrientation_Rz"] = await params.add_variable(
            idx, "TCPOrientation_Rz", 0.0, ua.VariantType.Double
        )
        self.nodes["ProgramState"] = await params.add_variable(
            idx, "ProgramState", "STOPPED"
        )
        self.nodes["CycleTime"] = await params.add_variable(
            idx, "CycleTime", 0.0, ua.VariantType.Double
        )
        self.nodes["CycleCount"] = await params.add_variable(
            idx, "CycleCount", 0, ua.VariantType.Int32
        )
        self.nodes["PayloadKg"] = await params.add_variable(
            idx, "PayloadKg", 0.0, ua.VariantType.Double
        )
        self.nodes["SpeedPercent"] = await params.add_variable(
            idx, "SpeedPercent", 0.0, ua.VariantType.Double
        )

    async def _update_node_values(self) -> None:
        """Update OPC-UA node values with generated data."""
        try:
            device_data = self.data_generator.generate_device_data(self.device_type)

            if self.device_type == "cnc_machine":
                await self.nodes["SpindleSpeed"].write_value(
                    device_data["spindle_speed_rpm"], ua.VariantType.Double
                )
                await self.nodes["FeedRate"].write_value(
                    device_data["feed_rate_mm_min"], ua.VariantType.Double
                )
                await self.nodes["ToolWearPercent"].write_value(
                    device_data["tool_wear_percent"], ua.VariantType.Double
                )
                await self.nodes["PartCount"].write_value(
                    device_data["part_count"], ua.VariantType.Int32
                )
                await self.nodes["AxisPosition_X"].write_value(
                    device_data["axis_position_x"], ua.VariantType.Double
                )
                await self.nodes["AxisPosition_Y"].write_value(
                    device_data["axis_position_y"], ua.VariantType.Double
                )
                await self.nodes["AxisPosition_Z"].write_value(
                    device_data["axis_position_z"], ua.VariantType.Double
                )
                await self.nodes["ProgramName"].write_value(device_data["program_name"])
                await self.nodes["MachineState"].write_value(device_data["machine_state"])
                await self.nodes["OperatingMode"].write_value(device_data["machine_state"])

                self._cached_node_data = {
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "timestamp": time.time(),
                    "nodes": {
                        "spindle_speed_rpm": device_data["spindle_speed_rpm"],
                        "feed_rate_mm_min": device_data["feed_rate_mm_min"],
                        "tool_wear_percent": device_data["tool_wear_percent"],
                        "part_count": device_data["part_count"],
                        "axis_position_x": device_data["axis_position_x"],
                        "axis_position_y": device_data["axis_position_y"],
                        "axis_position_z": device_data["axis_position_z"],
                        "program_name": device_data["program_name"],
                        "machine_state": device_data["machine_state"]
                    }
                }

            elif self.device_type == "plc_controller":
                await self.nodes["ProcessValue"].write_value(
                    device_data["process_value"], ua.VariantType.Double
                )
                await self.nodes["Setpoint"].write_value(
                    device_data["setpoint"], ua.VariantType.Double
                )
                await self.nodes["ControlOutput"].write_value(
                    device_data["control_output"], ua.VariantType.Double
                )
                await self.nodes["Mode"].write_value(device_data["mode"])
                await self.nodes["HighAlarm"].write_value(
                    device_data["high_alarm"], ua.VariantType.Boolean
                )
                await self.nodes["LowAlarm"].write_value(
                    device_data["low_alarm"], ua.VariantType.Boolean
                )
                await self.nodes["IntegralTerm"].write_value(
                    device_data["integral_term"], ua.VariantType.Double
                )
                await self.nodes["DerivativeTerm"].write_value(
                    device_data["derivative_term"], ua.VariantType.Double
                )
                await self.nodes["Error"].write_value(
                    device_data["error"], ua.VariantType.Double
                )
                await self.nodes["OperatingMode"].write_value(device_data["mode"])

                self._cached_node_data = {
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "timestamp": time.time(),
                    "nodes": {
                        "process_value": device_data["process_value"],
                        "setpoint": device_data["setpoint"],
                        "control_output": device_data["control_output"],
                        "mode": device_data["mode"],
                        "high_alarm": device_data["high_alarm"],
                        "low_alarm": device_data["low_alarm"],
                        "integral_term": device_data["integral_term"],
                        "derivative_term": device_data["derivative_term"],
                        "error": device_data["error"]
                    }
                }

            elif self.device_type == "industrial_robot":
                joint_angles = device_data["joint_angles"]
                for i, angle in enumerate(joint_angles):
                    node_key = f"JointAngle_{i+1}"
                    if node_key in self.nodes:
                        await self.nodes[node_key].write_value(
                            angle, ua.VariantType.Double
                        )

                await self.nodes["TCPPosition_X"].write_value(
                    device_data["tcp_position_x"], ua.VariantType.Double
                )
                await self.nodes["TCPPosition_Y"].write_value(
                    device_data["tcp_position_y"], ua.VariantType.Double
                )
                await self.nodes["TCPPosition_Z"].write_value(
                    device_data["tcp_position_z"], ua.VariantType.Double
                )
                await self.nodes["TCPOrientation_Rx"].write_value(
                    device_data["tcp_orientation_rx"], ua.VariantType.Double
                )
                await self.nodes["TCPOrientation_Ry"].write_value(
                    device_data["tcp_orientation_ry"], ua.VariantType.Double
                )
                await self.nodes["TCPOrientation_Rz"].write_value(
                    device_data["tcp_orientation_rz"], ua.VariantType.Double
                )
                await self.nodes["ProgramState"].write_value(device_data["program_state"])
                await self.nodes["CycleTime"].write_value(
                    device_data["cycle_time_s"], ua.VariantType.Double
                )
                await self.nodes["CycleCount"].write_value(
                    device_data["cycle_count"], ua.VariantType.Int32
                )
                await self.nodes["PayloadKg"].write_value(
                    device_data["payload_kg"], ua.VariantType.Double
                )
                await self.nodes["SpeedPercent"].write_value(
                    device_data["speed_percent"], ua.VariantType.Double
                )
                await self.nodes["OperatingMode"].write_value(device_data["program_state"])

                self._cached_node_data = {
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "timestamp": time.time(),
                    "nodes": {
                        "joint_angles": device_data["joint_angles"],
                        "tcp_position_x": device_data["tcp_position_x"],
                        "tcp_position_y": device_data["tcp_position_y"],
                        "tcp_position_z": device_data["tcp_position_z"],
                        "tcp_orientation_rx": device_data["tcp_orientation_rx"],
                        "tcp_orientation_ry": device_data["tcp_orientation_ry"],
                        "tcp_orientation_rz": device_data["tcp_orientation_rz"],
                        "program_state": device_data["program_state"],
                        "cycle_time_s": device_data["cycle_time_s"],
                        "cycle_count": device_data["cycle_count"],
                        "payload_kg": device_data["payload_kg"],
                        "speed_percent": device_data["speed_percent"]
                    }
                }

            # Update common status nodes
            await self.nodes["DeviceHealth"].write_value("NORMAL")
            await self.nodes["ErrorCode"].write_value(0, ua.VariantType.Int32)

            # Add common fields to cached data
            if self._cached_node_data and "nodes" in self._cached_node_data:
                self._cached_node_data["nodes"]["device_health"] = "NORMAL"
                self._cached_node_data["nodes"]["error_code"] = 0

            self.health_status["last_update"] = time.time()

        except Exception as e:
            logger.error(
                "Error updating OPC-UA node values",
                device_id=self.device_id,
                error=str(e)
            )
            self.health_status["error_count"] += 1

    async def _data_update_loop(self) -> None:
        """Continuous loop to update device data at specified intervals."""
        try:
            while self.running:
                await self._update_node_values()
                await asyncio.sleep(self.device_config.update_interval)
        except asyncio.CancelledError:
            logger.info(f"Data update loop cancelled for device {self.device_id}")
        except Exception as e:
            logger.error(
                "Error in OPC-UA data update loop",
                device_id=self.device_id,
                error=str(e)
            )
            self.health_status["error_count"] += 1

    async def start(self) -> bool:
        """
        Start the OPC-UA device simulation.

        Returns:
            True if device started successfully
        """
        try:
            logger.info(
                "Starting OPC-UA device",
                device_id=self.device_id,
                device_type=self.device_type,
                port=self.port
            )

            # Create and configure OPC-UA server
            self.server = Server()
            await self.server.init()

            self.server.set_endpoint(f"opc.tcp://0.0.0.0:{self.port}/freeopcua/server/")
            self.server.set_server_name(f"Protocol Sim Engine - {self.device_id}")
            self.server.set_application_uri(self.application_uri)

            # Disable security for simulation (configurable via config)
            self.server.set_security_policy(
                [ua.SecurityPolicyType.NoSecurity]
            )

            # Build the address space
            await self._build_address_space()

            # Start the server
            await self.server.start()

            # Start data update loop
            self.running = True
            self.update_task = asyncio.create_task(self._data_update_loop())

            self.health_status.update({
                "status": "running",
                "uptime_start": time.time(),
                "error_count": 0
            })

            logger.info(
                "OPC-UA device started successfully",
                device_id=self.device_id,
                port=self.port,
                endpoint=f"opc.tcp://0.0.0.0:{self.port}/freeopcua/server/"
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to start OPC-UA device",
                device_id=self.device_id,
                error=str(e)
            )
            return False

    async def stop(self) -> None:
        """Stop the OPC-UA device simulation."""
        try:
            logger.info(f"Stopping OPC-UA device {self.device_id}")

            self.running = False

            # Cancel data update task
            if self.update_task and not self.update_task.done():
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass

            # Stop OPC-UA server
            if self.server:
                await self.server.stop()
                self.server = None

            self.health_status["status"] = "stopped"

            logger.info(f"OPC-UA device {self.device_id} stopped successfully")

        except Exception as e:
            logger.error(
                "Error stopping OPC-UA device",
                device_id=self.device_id,
                error=str(e)
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current device status and statistics."""
        uptime = 0
        if self.health_status.get("uptime_start"):
            uptime = time.time() - self.health_status["uptime_start"]

        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "template": self.device_config.device_template,
            "port": self.port,
            "endpoint_url": f"opc.tcp://0.0.0.0:{self.port}/freeopcua/server/",
            "status": self.health_status["status"],
            "running": self.running,
            "uptime_seconds": round(uptime, 2),
            "error_count": self.health_status["error_count"],
            "last_update": self.health_status.get("last_update"),
            "update_interval": self.device_config.update_interval,
            "node_count": len(self.nodes)
        }

    def get_node_data(self) -> Optional[Dict[str, Any]]:
        """
        Get cached OPC-UA node values (updated by the background update loop).

        Returns:
            Dictionary of all node values with device metadata, or None if no data yet
        """
        return self._cached_node_data


class OPCUADeviceManager:
    """
    Manages multiple OPC-UA devices and coordinates their lifecycle.
    """

    def __init__(self, opcua_config: OPCUAConfig, port_manager: IntelligentPortManager):
        """
        Initialize OPC-UA device manager.

        Args:
            opcua_config: OPC-UA configuration
            port_manager: Port management system
        """
        self.opcua_config = opcua_config
        self.port_manager = port_manager
        self.devices: Dict[str, OPCUADevice] = {}
        self.device_allocation_plan: Dict[str, Tuple[str, int]] = {}

    async def initialize(self) -> bool:
        """Initialize the OPC-UA device manager."""
        try:
            logger.info("Initializing OPC-UA Device Manager...")

            # Build allocation plan
            self._build_allocation_plan()

            # Create all device instances
            await self._create_devices()

            logger.info(
                "OPC-UA Device Manager initialized",
                device_count=len(self.devices),
                device_types=list(self.opcua_config.devices.keys())
            )

            return True

        except Exception as e:
            logger.error("Failed to initialize OPC-UA Device Manager", error=str(e))
            return False

    def _build_allocation_plan(self) -> None:
        """Build port allocation plan for all devices."""
        self.device_allocation_plan = {}

        for device_type, device_config in self.opcua_config.devices.items():
            for i in range(device_config.count):
                device_id = f"opcua_{device_type}_{i:03d}"
                self.device_allocation_plan[device_id] = ("opcua", 1)  # 1 port per device

    async def _create_devices(self) -> None:
        """Create all OPC-UA device instances."""
        for device_type, device_config in self.opcua_config.devices.items():
            logger.info(f"Creating {device_config.count} {device_type} OPC-UA devices...")

            for i in range(device_config.count):
                device_id = f"opcua_{device_type}_{i:03d}"

                # Allocate port
                allocated_ports = self.port_manager.allocate_ports(
                    "opcua",
                    device_id,
                    1,  # 1 port per device
                    device_config.port_start + i if hasattr(device_config, 'port_start') else None
                )

                if not allocated_ports:
                    raise RuntimeError(f"Failed to allocate port for device {device_id}")

                port = allocated_ports[0]

                # Create device instance
                device = OPCUADevice(
                    device_id,
                    device_config,
                    port,
                    self.opcua_config.application_uri
                )
                self.devices[device_id] = device

                logger.debug(
                    "Created OPC-UA device",
                    device_id=device_id,
                    device_type=device_type,
                    port=port
                )

    def get_allocation_requirements(self) -> Dict[str, Tuple[str, int]]:
        """Get allocation requirements for validation."""
        return self.device_allocation_plan.copy()

    async def start_all_devices(self) -> Optional[Dict[str, OPCUADevice]]:
        """
        Start all OPC-UA devices.

        Returns:
            Dictionary of running devices or None if all failed
        """
        try:
            logger.info(f"Starting {len(self.devices)} OPC-UA devices...")

            started_devices = {}
            failed_devices = []

            # Start devices with limited parallelism to avoid port conflicts
            semaphore = asyncio.Semaphore(5)

            async def start_device(device_id: str, device: OPCUADevice) -> None:
                async with semaphore:
                    if await device.start():
                        started_devices[device_id] = device
                        logger.debug(f"Successfully started OPC-UA device {device_id}")
                    else:
                        failed_devices.append(device_id)
                        logger.error(f"Failed to start OPC-UA device {device_id}")

            tasks = [
                start_device(device_id, device)
                for device_id, device in self.devices.items()
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

            if failed_devices:
                logger.warning(
                    "Some OPC-UA devices failed to start",
                    failed_count=len(failed_devices),
                    failed_devices=failed_devices
                )

            logger.info(
                "OPC-UA device startup complete",
                started=len(started_devices),
                failed=len(failed_devices),
                total=len(self.devices)
            )

            return started_devices if started_devices else None

        except Exception as e:
            logger.error("Failed to start OPC-UA devices", error=str(e))
            return None

    async def stop_all_devices(self) -> None:
        """Stop all OPC-UA devices."""
        try:
            logger.info("Stopping all OPC-UA devices...")

            tasks = [device.stop() for device in self.devices.values()]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Deallocate ports
            for device_id in self.devices.keys():
                self.port_manager.deallocate_device_ports(device_id)

            logger.info("All OPC-UA devices stopped successfully")

        except Exception as e:
            logger.error("Error stopping OPC-UA devices", error=str(e))

    async def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all devices."""
        health_status = {}
        for device_id, device in self.devices.items():
            health_status[device_id] = device.get_status()
        return health_status

    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific device."""
        if device_id in self.devices:
            return self.devices[device_id].get_status()
        return None

    async def restart_device(self, device_id: str) -> bool:
        """Restart a specific device."""
        if device_id not in self.devices:
            return False

        device = self.devices[device_id]
        await device.stop()
        return await device.start()

    def get_all_server_endpoints(self) -> List[Dict[str, Any]]:
        """Get endpoint information for all OPC-UA servers."""
        endpoints = []
        for device_id, device in self.devices.items():
            endpoints.append({
                "device_id": device_id,
                "device_type": device.device_type,
                "endpoint_url": f"opc.tcp://0.0.0.0:{device.port}/freeopcua/server/",
                "port": device.port,
                "status": device.health_status["status"],
                "node_count": len(device.nodes)
            })
        return endpoints
