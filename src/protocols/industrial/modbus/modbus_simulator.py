"""
Modbus TCP Device Simulator

This module implements realistic Modbus TCP device simulation with multiple device types,
realistic data patterns, and proper protocol compliance.
"""

import asyncio
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog
from pymodbus.server import ModbusTcpServer
from pymodbus import ModbusDeviceIdentification, FramerType
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext, ModbusServerContext

from ....config_parser import ModbusConfig, ModbusDeviceConfig
from ....port_manager import IntelligentPortManager
from ....data_patterns.industrial_patterns import IndustrialDataGenerator

logger = structlog.get_logger(__name__)

class ModbusDevice:
    """
    Represents a single Modbus TCP device with realistic behavior.
    """
    
    def __init__(self, device_id: str, device_config: ModbusDeviceConfig, port: int):
        """
        Initialize a Modbus device.
        
        Args:
            device_id: Unique device identifier
            device_config: Device configuration
            port: TCP port for this device
        """
        self.device_id = device_id
        self.device_config = device_config
        self.port = port
        self.device_type = self._extract_device_type(device_config.device_template)
        self.running = False
        self.server = None
        self.server_task = None
        self.update_task = None
        
        # Initialize data generator with realistic patterns
        pattern_config = device_config.data_config or {}
        self.data_generator = IndustrialDataGenerator(device_id, pattern_config)
        
        # Create Modbus data context
        self.context = self._create_modbus_context()
        
        # Track device health
        self.health_status = {
            "status": "stopped",
            "last_update": None,
            "error_count": 0,
            "uptime_start": None
        }
        
    def _extract_device_type(self, template_name: str) -> str:
        """Extract device type from template name."""
        # Map template names to device types for data generation
        type_mapping = {
            "industrial_temperature_sensor": "temperature_sensor",
            "hydraulic_pressure_sensor": "pressure_transmitter", 
            "variable_frequency_drive": "motor_drive"
        }
        return type_mapping.get(template_name, "generic")
    
    def _create_modbus_context(self) -> ModbusDeviceContext:
        """Create Modbus device context with appropriate register mappings."""
        # Initialize register blocks
        # Coils (0x): 16-bit discrete outputs
        coils = ModbusSequentialDataBlock(0, [False] * 100)
        
        # Discrete Inputs (1x): 16-bit discrete inputs  
        discrete_inputs = ModbusSequentialDataBlock(0, [False] * 100)
        
        # Input Registers (3x): 16-bit analog inputs (read-only)
        input_registers = ModbusSequentialDataBlock(0, [0] * 100)
        
        # Holding Registers (4x): 16-bit analog outputs (read/write)
        holding_registers = ModbusSequentialDataBlock(0, [0] * 100)
        
        # Create device context
        context = ModbusDeviceContext(
            di=discrete_inputs,
            co=coils,
            hr=holding_registers,
            ir=input_registers
        )
        
        return context
    
    def _update_registers_with_realistic_data(self) -> None:
        """Update Modbus registers with realistic industrial data."""
        try:
            # Generate device-specific data
            device_data = self.data_generator.generate_device_data(self.device_type)
            
            if self.device_type == "temperature_sensor":
                # Temperature sensor register mapping
                # HR[0] = temperature (scaled by 100 for 0.01°C resolution)
                # HR[1] = humidity (scaled by 100 for 0.01% resolution)
                # HR[2] = sensor status
                # DI[0] = sensor healthy
                
                temp_scaled = int(device_data["temperature"] * 100)
                humidity_scaled = int(device_data["humidity"] * 100)
                status = device_data["sensor_status"]
                healthy = device_data["sensor_healthy"]
                
                self.context.setValues(3, 0, [temp_scaled, humidity_scaled, status])  # HR
                self.context.setValues(2, 0, [healthy])  # DI
                
            elif self.device_type == "pressure_transmitter":
                # Pressure transmitter register mapping
                # HR[0] = pressure (scaled by 100 for 0.01 PSI resolution)
                # HR[1] = flow rate (scaled by 100 for 0.01 L/min resolution)
                # DI[0] = high pressure alarm
                # DI[1] = low flow alarm
                
                pressure_scaled = int(device_data["pressure"] * 100)
                flow_scaled = int(device_data["flow_rate"] * 100)
                high_alarm = device_data["high_alarm"]
                low_flow_alarm = device_data["low_flow_alarm"]
                
                self.context.setValues(3, 0, [pressure_scaled, flow_scaled])  # HR
                self.context.setValues(2, 0, [high_alarm, low_flow_alarm])  # DI
                
            elif self.device_type == "motor_drive":
                # Motor drive register mapping
                # HR[0] = speed (RPM)
                # HR[1] = torque (scaled by 100 for 0.01 Nm resolution)
                # HR[2] = power (scaled by 100 for 0.01 kW resolution)
                # HR[3] = fault code
                
                speed = int(device_data["speed"])
                torque_scaled = int(device_data["torque"] * 100)
                power_scaled = int(device_data["power"] * 100)
                fault_code = device_data["fault_code"]
                
                self.context.setValues(3, 0, [speed, torque_scaled, power_scaled, fault_code])  # HR
                
            # Update health status
            self.health_status["last_update"] = time.time()
            
        except Exception as e:
            logger.error(
                "Error updating registers",
                device_id=self.device_id,
                error=str(e)
            )
            self.health_status["error_count"] += 1
    
    async def _data_update_loop(self) -> None:
        """Continuous loop to update device data at specified intervals."""
        try:
            while self.running:
                self._update_registers_with_realistic_data()
                await asyncio.sleep(self.device_config.update_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Data update loop cancelled for device {self.device_id}")
        except Exception as e:
            logger.error(
                "Error in data update loop",
                device_id=self.device_id,
                error=str(e)
            )
            self.health_status["error_count"] += 1
    
    async def start(self) -> bool:
        """
        Start the Modbus device simulation.
        
        Returns:
            True if device started successfully
        """
        try:
            logger.info(
                "Starting Modbus device",
                device_id=self.device_id,
                device_type=self.device_type,
                port=self.port
            )
            
            # Create device identification
            identity = ModbusDeviceIdentification()
            identity.VendorName = "Industrial Facility Simulator"
            identity.ProductCode = f"IFS-{self.device_type.upper()}"
            identity.VendorUrl = "https://github.com/industrial-facility-simulator"
            identity.ProductName = f"Simulated {self.device_type}"
            identity.ModelName = self.device_config.device_template
            identity.MajorMinorRevision = "1.0"
            
            # Create server context
            server_context = ModbusServerContext(devices=self.context, single=True)
            
            # Start initial data update
            self._update_registers_with_realistic_data()
            
            # Create the Modbus server
            self.server = ModbusTcpServer(
                context=server_context,
                framer=FramerType.SOCKET,
                identity=identity,
                address=("0.0.0.0", self.port)
            )
            
            # Start server in background task
            self.server_task = asyncio.create_task(self.server.serve_forever())
            
            # Start data update loop
            self.update_task = asyncio.create_task(self._data_update_loop())
            
            # Give server a moment to start
            await asyncio.sleep(0.1)
            
            self.running = True
            self.health_status.update({
                "status": "running",
                "uptime_start": time.time(),
                "error_count": 0
            })
            
            logger.info(
                "Modbus device started successfully",
                device_id=self.device_id,
                port=self.port
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to start Modbus device",
                device_id=self.device_id,
                error=str(e)
            )
            return False
    
    async def stop(self) -> None:
        """Stop the Modbus device simulation."""
        try:
            logger.info(f"Stopping Modbus device {self.device_id}")
            
            self.running = False
            
            # Cancel data update task
            if self.update_task and not self.update_task.done():
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass
            
            # Stop server task
            if self.server_task and not self.server_task.done():
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            
            # Stop server
            if self.server:
                self.server.server_close()
                
            self.health_status["status"] = "stopped"
            
            logger.info(f"Modbus device {self.device_id} stopped successfully")
            
        except Exception as e:
            logger.error(
                "Error stopping Modbus device",
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
            "status": self.health_status["status"],
            "running": self.running,
            "uptime_seconds": round(uptime, 2),
            "error_count": self.health_status["error_count"],
            "last_update": self.health_status.get("last_update"),
            "update_interval": self.device_config.update_interval
        }
    
    def get_register_data(self) -> Dict[str, Any]:
        """Get current Modbus register values (actual simulated data)."""
        try:
            # Read holding registers
            hr_values = self.context.getValues(3, 0, 10)  # Read first 10 holding registers
            
            # Read discrete inputs
            di_values = self.context.getValues(2, 0, 10)  # Read first 10 discrete inputs
            
            # Parse based on device type
            if self.device_type == "temperature_sensor":
                return {
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "timestamp": time.time(),
                    "registers": {
                        "temperature_raw": hr_values[0],
                        "temperature_celsius": hr_values[0] / 100.0,
                        "humidity_raw": hr_values[1],
                        "humidity_percent": hr_values[1] / 100.0,
                        "status_code": hr_values[2],
                        "sensor_healthy": bool(di_values[0])
                    },
                    "raw_data": {
                        "holding_registers": hr_values[:3],
                        "discrete_inputs": di_values[:1]
                    }
                }
            
            elif self.device_type == "pressure_transmitter":
                return {
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "timestamp": time.time(),
                    "registers": {
                        "pressure_raw": hr_values[0],
                        "pressure_psi": hr_values[0] / 100.0,
                        "flow_rate_raw": hr_values[1],
                        "flow_rate_lpm": hr_values[1] / 100.0,
                        "high_pressure_alarm": bool(di_values[0]),
                        "low_flow_alarm": bool(di_values[1])
                    },
                    "raw_data": {
                        "holding_registers": hr_values[:2],
                        "discrete_inputs": di_values[:2]
                    }
                }
            
            elif self.device_type == "motor_drive":
                return {
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "timestamp": time.time(),
                    "registers": {
                        "speed_rpm": hr_values[0],
                        "torque_raw": hr_values[1],
                        "torque_nm": hr_values[1] / 100.0,
                        "power_raw": hr_values[2],
                        "power_kw": hr_values[2] / 100.0,
                        "fault_code": hr_values[3]
                    },
                    "raw_data": {
                        "holding_registers": hr_values[:4],
                        "discrete_inputs": []
                    }
                }
            
            else:
                # Generic device
                return {
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "timestamp": time.time(),
                    "registers": {},
                    "raw_data": {
                        "holding_registers": hr_values,
                        "discrete_inputs": di_values
                    }
                }
                
        except Exception as e:
            logger.error(
                "Error reading register data",
                device_id=self.device_id,
                error=str(e)
            )
            return {
                "device_id": self.device_id,
                "error": str(e),
                "timestamp": time.time()
            }

class ModbusDeviceManager:
    """
    Manages multiple Modbus devices and coordinates their lifecycle.
    """
    
    def __init__(self, modbus_config: ModbusConfig, port_manager: IntelligentPortManager):
        """
        Initialize Modbus device manager.
        
        Args:
            modbus_config: Modbus configuration
            port_manager: Port management system
        """
        self.modbus_config = modbus_config
        self.port_manager = port_manager
        self.devices: Dict[str, ModbusDevice] = {}
        self.device_allocation_plan: Dict[str, Tuple[str, int]] = {}
        
    async def initialize(self) -> bool:
        """Initialize the Modbus device manager."""
        try:
            logger.info("Initializing Modbus Device Manager...")
            
            # Build allocation plan
            self._build_allocation_plan()
            
            # Create all device instances
            await self._create_devices()
            
            logger.info(
                "Modbus Device Manager initialized",
                device_count=len(self.devices),
                device_types=list(self.modbus_config.devices.keys())
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Modbus Device Manager", error=str(e))
            return False
    
    def _build_allocation_plan(self) -> None:
        """Build port allocation plan for all devices."""
        self.device_allocation_plan = {}
        
        for device_type, device_config in self.modbus_config.devices.items():
            for i in range(device_config.count):
                device_id = f"modbus_{device_type}_{i:03d}"
                self.device_allocation_plan[device_id] = ("modbus", 1)  # 1 port per device
    
    async def _create_devices(self) -> None:
        """Create all Modbus device instances."""
        for device_type, device_config in self.modbus_config.devices.items():
            logger.info(f"Creating {device_config.count} {device_type} devices...")
            
            for i in range(device_config.count):
                device_id = f"modbus_{device_type}_{i:03d}"
                
                # Allocate port
                allocated_ports = self.port_manager.allocate_ports(
                    "modbus", 
                    device_id, 
                    1,  # 1 port per device
                    device_config.port_start + i if hasattr(device_config, 'port_start') else None
                )
                
                if not allocated_ports:
                    raise RuntimeError(f"Failed to allocate port for device {device_id}")
                
                port = allocated_ports[0]
                
                # Create device instance
                device = ModbusDevice(device_id, device_config, port)
                self.devices[device_id] = device
                
                logger.debug(
                    "Created Modbus device",
                    device_id=device_id,
                    device_type=device_type,
                    port=port
                )
    
    def get_allocation_requirements(self) -> Dict[str, Tuple[str, int]]:
        """Get allocation requirements for validation."""
        return self.device_allocation_plan.copy()
    
    async def start_all_devices(self) -> Optional[Dict[str, ModbusDevice]]:
        """
        Start all Modbus devices.
        
        Returns:
            Dictionary of running devices or None if any failed
        """
        try:
            logger.info(f"Starting {len(self.devices)} Modbus devices...")
            
            started_devices = {}
            failed_devices = []
            
            # Start devices with some parallelism but not too much to avoid port conflicts
            semaphore = asyncio.Semaphore(5)  # Max 5 concurrent starts
            
            async def start_device(device_id: str, device: ModbusDevice) -> None:
                async with semaphore:
                    if await device.start():
                        started_devices[device_id] = device
                        logger.debug(f"Successfully started device {device_id}")
                    else:
                        failed_devices.append(device_id)
                        logger.error(f"Failed to start device {device_id}")
            
            # Start all devices
            tasks = [
                start_device(device_id, device) 
                for device_id, device in self.devices.items()
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            if failed_devices:
                logger.warning(
                    "Some Modbus devices failed to start",
                    failed_count=len(failed_devices),
                    failed_devices=failed_devices
                )
            
            logger.info(
                "Modbus device startup complete",
                started=len(started_devices),
                failed=len(failed_devices),
                total=len(self.devices)
            )
            
            return started_devices if started_devices else None
            
        except Exception as e:
            logger.error("Failed to start Modbus devices", error=str(e))
            return None
    
    async def stop_all_devices(self) -> None:
        """Stop all Modbus devices."""
        try:
            logger.info("Stopping all Modbus devices...")
            
            # Stop devices in parallel
            tasks = [device.stop() for device in self.devices.values()]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Deallocate ports
            for device_id in self.devices.keys():
                self.port_manager.deallocate_device_ports(device_id)
            
            logger.info("All Modbus devices stopped successfully")
            
        except Exception as e:
            logger.error("Error stopping Modbus devices", error=str(e))
    
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
