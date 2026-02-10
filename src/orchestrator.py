"""
Simulation Orchestrator

This module coordinates all simulation components and manages the lifecycle
of devices and protocols.
"""

import asyncio
from typing import Dict, List, Optional, Set

import structlog

from .config_parser import IndustrialFacilityConfig
from .port_manager import IntelligentPortManager
from .protocols.industrial.modbus.modbus_simulator import ModbusDeviceManager
from .protocols.industrial.mqtt.mqtt_simulator import MQTTDeviceManager
from .protocols.industrial.mqtt.mqtt_broker import EmbeddedMQTTBroker
from .protocols.industrial.opcua.opcua_simulator import OPCUADeviceManager

logger = structlog.get_logger(__name__)

class SimulationOrchestrator:
    """
    Main orchestrator that manages all simulation components.
    
    This class coordinates:
    - Port allocation across protocols
    - Device lifecycle management
    - Protocol-specific simulators
    - Health monitoring and reporting
    """
    
    def __init__(self, config: IndustrialFacilityConfig):
        """
        Initialize the simulation orchestrator.
        
        Args:
            config: Validated configuration object
        """
        self.config = config
        self.port_manager = IntelligentPortManager()
        self.device_managers: Dict[str, any] = {}
        self.running_devices: Dict[str, any] = {}
        self.active_protocols: Set[str] = set()
        self.health_status = {"status": "stopped", "devices": {}}
        self.embedded_mqtt_broker: Optional[EmbeddedMQTTBroker] = None
        
    async def initialize(self) -> bool:
        """
        Initialize the orchestrator and all components.
        
        Returns:
            True if initialization was successful
        """
        try:
            logger.info("Initializing Simulation Orchestrator...")
            
            # Initialize port manager
            network_config = self.config.network
            self.port_manager.initialize_pools(network_config.port_ranges)
            
            # Initialize protocol managers
            await self._initialize_protocol_managers()
            
            # Validate allocation plan
            if not await self._validate_allocation_plan():
                logger.error("Device allocation plan validation failed")
                return False
                
            logger.info(
                "Simulation Orchestrator initialized successfully",
                protocols=list(self.device_managers.keys()),
                facility=self.config.facility.name
            )
            
            self.health_status["status"] = "initialized"
            return True
            
        except Exception as e:
            logger.error("Failed to initialize orchestrator", error=str(e))
            return False
    
    async def _initialize_protocol_managers(self) -> None:
        """Initialize managers for all enabled protocols."""

        # Initialize Modbus manager if enabled
        if self.config.industrial_protocols.modbus_tcp and self.config.industrial_protocols.modbus_tcp.enabled:
            logger.info("Initializing Modbus TCP protocol manager...")
            modbus_manager = ModbusDeviceManager(
                self.config.industrial_protocols.modbus_tcp,
                self.port_manager
            )
            await modbus_manager.initialize()
            self.device_managers["modbus_tcp"] = modbus_manager
            self.active_protocols.add("modbus_tcp")

        # Initialize MQTT manager if enabled
        if self.config.industrial_protocols.mqtt and self.config.industrial_protocols.mqtt.enabled:
            mqtt_config = self.config.industrial_protocols.mqtt

            # Start embedded MQTT broker if configured
            if mqtt_config.use_embedded_broker:
                logger.info("Starting embedded MQTT broker...")
                self.embedded_mqtt_broker = EmbeddedMQTTBroker(
                    host="0.0.0.0",
                    port=mqtt_config.broker_port
                )
                if await self.embedded_mqtt_broker.start():
                    # Wait for broker to be fully ready
                    await asyncio.sleep(0.5)
                    logger.info(
                        "Embedded MQTT broker started",
                        port=mqtt_config.broker_port
                    )
                else:
                    logger.warning(
                        "Failed to start embedded MQTT broker - "
                        "falling back to external broker mode"
                    )

            logger.info("Initializing MQTT protocol manager...")
            mqtt_manager = MQTTDeviceManager(
                mqtt_config,
                self.port_manager
            )
            if await mqtt_manager.initialize():
                self.device_managers["mqtt"] = mqtt_manager
                self.active_protocols.add("mqtt")
            else:
                logger.warning("MQTT manager initialization failed - MQTT devices will not be available")

        # Initialize OPC-UA manager if enabled
        if self.config.industrial_protocols.opcua and self.config.industrial_protocols.opcua.enabled:
            logger.info("Initializing OPC-UA protocol manager...")
            opcua_manager = OPCUADeviceManager(
                self.config.industrial_protocols.opcua,
                self.port_manager
            )
            if await opcua_manager.initialize():
                self.device_managers["opcua"] = opcua_manager
                self.active_protocols.add("opcua")
            else:
                logger.warning("OPC-UA manager initialization failed - OPC-UA devices will not be available")
        
    async def _validate_allocation_plan(self) -> bool:
        """Validate that all devices can be allocated without port conflicts."""
        allocation_plan = {}
        
        # Build allocation plan for all devices
        for protocol_name, manager in self.device_managers.items():
            device_allocations = manager.get_allocation_requirements()
            allocation_plan.update(device_allocations)
            
        # Validate the plan
        return self.port_manager.validate_allocation_plan(allocation_plan)
    
    async def start_all_devices(self) -> bool:
        """
        Start all configured devices and begin simulation.
        
        Returns:
            True if all devices started successfully
        """
        try:
            logger.info("Starting all simulation devices...")
            
            started_count = 0
            total_devices = 0
            
            # Start devices for each protocol
            for protocol_name, manager in self.device_managers.items():
                logger.info(f"Starting {protocol_name} devices...")
                
                devices = await manager.start_all_devices()
                if devices:
                    self.running_devices[protocol_name] = devices
                    device_count = len(devices)
                    started_count += device_count
                    total_devices += device_count
                    
                    logger.info(
                        f"{protocol_name} devices started successfully",
                        device_count=device_count
                    )
                else:
                    logger.error(f"Failed to start {protocol_name} devices")
                    
            if started_count == 0:
                logger.error("No devices were started")
                return False
                
            # Update health status
            await self._update_health_status()
            
            logger.info(
                "All simulation devices started successfully",
                total_devices=started_count,
                protocols=list(self.running_devices.keys())
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to start devices", error=str(e))
            return False
    
    async def stop_all_devices(self) -> None:
        """Stop all running devices and cleanup resources."""
        try:
            logger.info("Stopping all simulation devices...")

            # Stop devices for each protocol
            for protocol_name, manager in self.device_managers.items():
                logger.info(f"Stopping {protocol_name} devices...")
                await manager.stop_all_devices()

            # Stop embedded MQTT broker if running
            if self.embedded_mqtt_broker:
                logger.info("Stopping embedded MQTT broker...")
                await self.embedded_mqtt_broker.stop()
                self.embedded_mqtt_broker = None

            # Clear running devices
            self.running_devices.clear()
            self.active_protocols.clear()

            # Update health status
            self.health_status = {"status": "stopped", "devices": {}}

            logger.info("All simulation devices stopped successfully")

        except Exception as e:
            logger.error("Error stopping devices", error=str(e))
    
    async def _update_health_status(self) -> None:
        """Update the health status of all devices."""
        try:
            device_health = {}
            total_devices = 0
            healthy_devices = 0
            
            # Check health for each protocol
            for protocol_name, manager in self.device_managers.items():
                protocol_health = await manager.get_health_status()
                device_health[protocol_name] = protocol_health
                
                # Count devices
                for device_id, health in protocol_health.items():
                    total_devices += 1
                    if health.get("status") == "running":
                        healthy_devices += 1
            
            # Update overall health
            health_percentage = (healthy_devices / total_devices * 100) if total_devices > 0 else 0
            overall_status = "healthy" if health_percentage >= 95 else "degraded" if health_percentage >= 80 else "unhealthy"
            
            self.health_status = {
                "status": overall_status,
                "devices": device_health,
                "summary": {
                    "total_devices": total_devices,
                    "healthy_devices": healthy_devices,
                    "health_percentage": round(health_percentage, 2)
                },
                "port_utilization": self.port_manager.get_port_utilization()
            }
            
        except Exception as e:
            logger.error("Failed to update health status", error=str(e))
    
    def get_device_count(self) -> int:
        """Get total number of running devices."""
        total = 0
        for devices in self.running_devices.values():
            total += len(devices)
        return total
    
    def get_active_protocols(self) -> Set[str]:
        """Get set of active protocol names."""
        return self.active_protocols.copy()
    
    def get_health_status(self) -> Dict:
        """Get current health status of all devices."""
        return self.health_status.copy()
    
    async def get_device_status(self, device_id: str) -> Optional[Dict]:
        """
        Get status of a specific device.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            Device status dictionary or None if device not found
        """
        for protocol_name, manager in self.device_managers.items():
            device_status = await manager.get_device_status(device_id)
            if device_status:
                return device_status
        return None
    
    async def restart_device(self, device_id: str) -> bool:
        """
        Restart a specific device.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            True if restart was successful
        """
        for protocol_name, manager in self.device_managers.items():
            if await manager.restart_device(device_id):
                logger.info(f"Device {device_id} restarted successfully")
                await self._update_health_status()
                return True
        
        logger.warning(f"Device {device_id} not found for restart")
        return False
    
    def get_allocation_report(self) -> Dict:
        """Get comprehensive allocation and status report."""
        return {
            "facility": {
                "name": self.config.facility.name,
                "description": self.config.facility.description,
                "location": self.config.facility.location
            },
            "simulation": {
                "time_acceleration": self.config.simulation.time_acceleration,
                "fault_injection_rate": self.config.simulation.fault_injection_rate
            },
            "devices": {
                "total_count": self.get_device_count(),
                "by_protocol": {
                    protocol: len(devices) 
                    for protocol, devices in self.running_devices.items()
                }
            },
            "ports": self.port_manager.generate_allocation_report(),
            "health": self.health_status
        }
    
    async def start_monitoring_loop(self) -> None:
        """Start background monitoring loop for health updates."""
        try:
            logger.info("Starting health monitoring loop...")
            
            while self.running_devices:
                await asyncio.sleep(30)  # Update every 30 seconds
                await self._update_health_status()
                
        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
        except Exception as e:
            logger.error("Error in health monitoring loop", error=str(e))
    
    def get_all_devices(self) -> List[Dict]:
        """Get list of all devices with their status."""
        all_devices = []
        
        for protocol_name, devices in self.running_devices.items():
            for device_id, device in devices.items():
                device_info = device.get_status()
                device_info["protocol"] = protocol_name
                all_devices.append(device_info)
        
        return all_devices
    
    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """Get detailed information about a specific device."""
        for protocol_name, devices in self.running_devices.items():
            if device_id in devices:
                device_info = devices[device_id].get_status()
                device_info["protocol"] = protocol_name
                return device_info
        return None
    
    def get_device_data(self, device_id: str) -> Optional[Dict]:
        """Get current data values from a specific device."""
        for protocol_name, devices in self.running_devices.items():
            if device_id in devices:
                device = devices[device_id]

                # Get actual register/message/node data
                if protocol_name == "modbus_tcp":
                    return device.get_register_data()
                elif protocol_name == "mqtt":
                    return device.get_last_message()
                elif protocol_name == "opcua":
                    return device.get_node_data()
        return None
    
    def get_protocol_summary(self) -> Dict[str, Dict]:
        """Get summary of all active protocols."""
        summary = {}
        
        for protocol_name, devices in self.running_devices.items():
            summary[protocol_name] = {
                "device_count": len(devices),
                "status": "active",
                "devices": list(devices.keys())
            }
        
        return summary
    
    def get_devices_by_protocol(self, protocol_name: str) -> List[Dict]:
        """Get all devices for a specific protocol."""
        if protocol_name not in self.running_devices:
            return []
        
        devices_list = []
        for device_id, device in self.running_devices[protocol_name].items():
            device_info = device.get_status()
            device_info["protocol"] = protocol_name
            devices_list.append(device_info)
        
        return devices_list
    
    def get_performance_metrics(self) -> Dict:
        """Get system performance metrics."""
        return {
            "total_devices": self.get_device_count(),
            "active_protocols": list(self.active_protocols),
            "port_utilization": self.port_manager.get_port_utilization(),
            "health_status": self.health_status.get("status"),
            "healthy_device_percentage": self.health_status.get("summary", {}).get("health_percentage", 0)
        }
    
    def export_all_device_data(self, format: str = "json") -> Dict:
        """Export all device data in specified format."""
        import time
        
        all_data = []
        for protocol_name, devices in self.running_devices.items():
            for device_id, device in devices.items():
                device_info = device.get_status()
                device_info["protocol"] = protocol_name
                all_data.append(device_info)
        
        return {
            "format": format,
            "timestamp": time.time(),
            "device_count": len(all_data),
            "data": all_data
        }
