"""
Configuration Parser for Industrial Facility Simulator

This module handles loading, parsing, and validating YAML configuration files
for the simulation platform.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger(__name__)

class NetworkConfig(BaseModel):
    """Network configuration settings."""
    base_ip: str = "192.168.100.0/24"
    port_ranges: Dict[str, List[int]] = Field(default_factory=lambda: {
        "modbus": [5020, 5500],
        "opcua": [4840, 4940],
        "mqtt": [1883, 1883],
        "http": [3000, 3200]
    })

class ModbusDeviceConfig(BaseModel):
    """Configuration for Modbus devices."""
    count: int = Field(gt=0, le=1000)
    port_start: int = Field(ge=1024, le=65535)
    device_template: str
    locations: Optional[List[str]] = None
    update_interval: float = Field(gt=0, default=2.0)
    data_config: Optional[Dict[str, Any]] = None

class ModbusConfig(BaseModel):
    """Modbus protocol configuration."""
    enabled: bool = True
    devices: Dict[str, ModbusDeviceConfig] = Field(default_factory=dict)


class MQTTDeviceConfig(BaseModel):
    """Configuration for MQTT devices."""
    count: int = Field(gt=0, le=1000)
    device_template: str
    base_topic: Optional[str] = None  # Auto-generated if not provided
    publish_interval: float = Field(gt=0, default=5.0)  # Seconds
    qos: int = Field(ge=0, le=2, default=0)
    retain: bool = False
    locations: Optional[List[str]] = None
    data_config: Optional[Dict[str, Any]] = None


class MQTTConfig(BaseModel):
    """MQTT protocol configuration."""
    enabled: bool = True
    use_embedded_broker: bool = True  # Use embedded or connect to external
    broker_host: str = "localhost"
    broker_port: int = Field(ge=1024, le=65535, default=1883)
    client_id_prefix: str = "sim_"
    devices: Dict[str, MQTTDeviceConfig] = Field(default_factory=dict)


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
    security_mode: str = "None"
    security_policy: str = "None"
    application_uri: str = "urn:protocol-sim-engine:opcua:server"
    devices: Dict[str, OPCUADeviceConfig] = Field(default_factory=dict)


class IndustrialProtocolsConfig(BaseModel):
    """Industrial protocols configuration."""
    modbus_tcp: Optional[ModbusConfig] = None
    mqtt: Optional[MQTTConfig] = None
    opcua: Optional[OPCUAConfig] = None

class SimulationConfig(BaseModel):
    """Global simulation settings."""
    time_acceleration: float = Field(gt=0, default=1.0)
    start_time: Optional[str] = None
    data_retention: str = "24h"
    fault_injection_rate: float = Field(ge=0, le=1, default=0.02)

class FacilityConfig(BaseModel):
    """Facility information configuration."""
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    shift_schedule: str = "24x7"

class IndustrialFacilityConfig(BaseModel):
    """Root configuration model for the Industrial Facility Simulator."""
    
    facility: FacilityConfig
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    industrial_protocols: IndustrialProtocolsConfig = Field(default_factory=IndustrialProtocolsConfig)
    
    @validator('facility')
    def validate_facility(cls, v):
        if not v.name.strip():
            raise ValueError("Facility name cannot be empty")
        return v
    
    class Config:
        extra = "allow"  # Allow additional fields for future extensibility

class ConfigParser:
    """Configuration parser and validator for Industrial Facility Simulator."""
    
    def __init__(self):
        """Initialize the configuration parser."""
        self.config: Optional[IndustrialFacilityConfig] = None
        
    async def load_config(self, config_file: Path) -> Optional[IndustrialFacilityConfig]:
        """
        Load and validate configuration from YAML file.
        
        Args:
            config_file: Path to the YAML configuration file
            
        Returns:
            Validated configuration object or None if loading failed
        """
        try:
            logger.info(f"Loading configuration from {config_file}")
            
            # Check if file exists
            if not config_file.exists():
                # Create default config if file doesn't exist
                logger.warning(f"Configuration file {config_file} not found, creating default")
                await self._create_default_config(config_file)
                
            # Load YAML file
            with open(config_file, 'r') as f:
                raw_config = yaml.safe_load(f)
                
            if not raw_config:
                logger.error("Configuration file is empty")
                return None
                
            # Validate configuration using Pydantic model
            self.config = IndustrialFacilityConfig(**raw_config)
            
            logger.info(
                "Configuration loaded successfully",
                facility_name=self.config.facility.name,
                protocols=self._get_enabled_protocols()
            )
            
            return self.config
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            return None
    
    def _get_enabled_protocols(self) -> List[str]:
        """Get list of enabled protocols."""
        enabled_protocols = []

        if self.config and self.config.industrial_protocols:
            if self.config.industrial_protocols.modbus_tcp and self.config.industrial_protocols.modbus_tcp.enabled:
                enabled_protocols.append("modbus_tcp")
            if self.config.industrial_protocols.mqtt and self.config.industrial_protocols.mqtt.enabled:
                enabled_protocols.append("mqtt")
            if self.config.industrial_protocols.opcua and self.config.industrial_protocols.opcua.enabled:
                enabled_protocols.append("opcua")

        return enabled_protocols
    
    async def _create_default_config(self, config_file: Path) -> None:
        """Create a default configuration file."""
        try:
            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            default_config = {
                "facility": {
                    "name": "Default Industrial Facility",
                    "description": "Example industrial facility simulation",
                    "location": "Virtual Factory Floor 1",
                    "shift_schedule": "24x7"
                },
                "simulation": {
                    "time_acceleration": 1.0,
                    "data_retention": "24h",
                    "fault_injection_rate": 0.02
                },
                "network": {
                    "base_ip": "192.168.100.0/24",
                    "port_ranges": {
                        "modbus": [5020, 5500],
                        "opcua": [4840, 4940],
                        "mqtt": [1883, 1883],
                        "http": [3000, 3200]
                    }
                },
                "industrial_protocols": {
                    "modbus_tcp": {
                        "enabled": True,
                        "devices": {
                            "temperature_sensors": {
                                "count": 5,
                                "port_start": 5020,
                                "device_template": "industrial_temperature_sensor",
                                "locations": ["line_1", "line_2", "assembly"],
                                "update_interval": 2.0,
                                "data_config": {
                                    "temperature_range": [18, 45],
                                    "humidity_range": [30, 80],
                                    "calibration_drift": 0.001
                                }
                            },
                            "pressure_transmitters": {
                                "count": 3,
                                "port_start": 5025,
                                "device_template": "hydraulic_pressure_sensor",
                                "locations": ["hydraulic_press_1", "hydraulic_press_2"],
                                "update_interval": 1.0,
                                "data_config": {
                                    "pressure_range": [0, 300],
                                    "flow_range": [10, 150],
                                    "alarm_thresholds": {
                                        "high_pressure": 250,
                                        "low_flow": 20
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
                
            logger.info(f"Created default configuration file: {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
            raise
    
    def get_modbus_devices(self) -> Dict[str, ModbusDeviceConfig]:
        """Get Modbus device configurations."""
        if (self.config and
            self.config.industrial_protocols and
            self.config.industrial_protocols.modbus_tcp and
            self.config.industrial_protocols.modbus_tcp.enabled):
            return self.config.industrial_protocols.modbus_tcp.devices
        return {}

    def get_mqtt_devices(self) -> Dict[str, "MQTTDeviceConfig"]:
        """Get MQTT device configurations."""
        if (self.config and
            self.config.industrial_protocols and
            self.config.industrial_protocols.mqtt and
            self.config.industrial_protocols.mqtt.enabled):
            return self.config.industrial_protocols.mqtt.devices
        return {}
    
    def get_opcua_devices(self) -> Dict[str, OPCUADeviceConfig]:
        """Get OPC-UA device configurations."""
        if (self.config and
            self.config.industrial_protocols and
            self.config.industrial_protocols.opcua and
            self.config.industrial_protocols.opcua.enabled):
            return self.config.industrial_protocols.opcua.devices
        return {}

    def get_network_config(self) -> NetworkConfig:
        """Get network configuration."""
        return self.config.network if self.config else NetworkConfig()
    
    def get_facility_info(self) -> Optional[FacilityConfig]:
        """Get facility information."""
        return self.config.facility if self.config else None
    
    def is_protocol_enabled(self, protocol: str) -> bool:
        """Check if a specific protocol is enabled."""
        if not self.config or not self.config.industrial_protocols:
            return False

        if protocol == "modbus_tcp":
            modbus_config = self.config.industrial_protocols.modbus_tcp
            return modbus_config is not None and modbus_config.enabled

        if protocol == "mqtt":
            mqtt_config = self.config.industrial_protocols.mqtt
            return mqtt_config is not None and mqtt_config.enabled

        if protocol == "opcua":
            opcua_config = self.config.industrial_protocols.opcua
            return opcua_config is not None and opcua_config.enabled

        return False
    
    def validate_port_ranges(self) -> bool:
        """Validate that port ranges don't overlap."""
        if not self.config:
            return False
            
        network_config = self.config.network
        used_ports = set()
        
        # Check Modbus devices
        modbus_devices = self.get_modbus_devices()
        for device_name, device_config in modbus_devices.items():
            device_ports = range(device_config.port_start, 
                               device_config.port_start + device_config.count)
            for port in device_ports:
                if port in used_ports:
                    logger.error(f"Port conflict detected: {port} used by multiple devices")
                    return False
                used_ports.add(port)
                
        logger.info(f"Port validation successful, {len(used_ports)} ports allocated")
        return True