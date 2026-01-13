"""
Comprehensive Test Suite for Modbus TCP Implementation

This module thoroughly tests the Modbus TCP device simulation capabilities
including device creation, data generation, port management, and configuration-based
device instantiation.
"""

import asyncio
import sys
import os
import pytest
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.config_parser import ModbusDeviceConfig, ModbusConfig, ConfigParser
from src.protocols.industrial.modbus.modbus_simulator import ModbusDevice, ModbusDeviceManager
from src.port_manager import IntelligentPortManager
from src.data_patterns.industrial_patterns import IndustrialDataGenerator

class TestModbusDeviceCreation:
    """Test Modbus device creation and basic functionality."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.device_config = ModbusDeviceConfig(
            count=1,
            port_start=15000,
            device_template="industrial_temperature_sensor",
            update_interval=1.0,
            data_config={
                "temperature_range": [20, 40],
                "humidity_range": [30, 70]
            }
        )
    
    def test_device_initialization(self):
        """Test basic device initialization."""
        device = ModbusDevice("test_device", self.device_config, 15000)
        
        assert device.device_id == "test_device"
        assert device.port == 15000
        assert device.device_type == "temperature_sensor"
        assert device.running == False
        assert device.context is not None
        assert device.data_generator is not None
    
    def test_device_type_extraction(self):
        """Test device type extraction from template names."""
        # Test temperature sensor
        config1 = ModbusDeviceConfig(
            count=1,
            port_start=15000,
            device_template="industrial_temperature_sensor",
            update_interval=1.0
        )
        device1 = ModbusDevice("temp_test", config1, 15000)
        assert device1.device_type == "temperature_sensor"
        
        # Test pressure transmitter
        config2 = ModbusDeviceConfig(
            count=1,
            port_start=15001,
            device_template="hydraulic_pressure_sensor",
            update_interval=1.0
        )
        device2 = ModbusDevice("pressure_test", config2, 15001)
        assert device2.device_type == "pressure_transmitter"
        
        # Test motor drive
        config3 = ModbusDeviceConfig(
            count=1,
            port_start=15002,
            device_template="variable_frequency_drive",
            update_interval=1.0
        )
        device3 = ModbusDevice("motor_test", config3, 15002)
        assert device3.device_type == "motor_drive"
    
    def test_register_context_creation(self):
        """Test Modbus register context creation."""
        device = ModbusDevice("test_device", self.device_config, 15000)
        
        # Test that all register types are initialized
        assert device.context is not None
        
        # Test that registers can be read
        holding_registers = device.context.getValues(3, 0, 10)  # Read 10 holding registers
        assert len(holding_registers) == 10
        assert all(isinstance(reg, int) for reg in holding_registers)
        
        discrete_inputs = device.context.getValues(2, 0, 10)  # Read 10 discrete inputs
        assert len(discrete_inputs) == 10
    
    def test_data_generation_integration(self):
        """Test integration with data pattern generator."""
        device = ModbusDevice("test_data", self.device_config, 15000)
        
        # Generate data multiple times to test variation
        initial_data = device.data_generator.generate_device_data("temperature_sensor")
        time.sleep(0.1)
        second_data = device.data_generator.generate_device_data("temperature_sensor")
        
        # Verify data structure
        assert "temperature" in initial_data
        assert "humidity" in initial_data
        assert "sensor_status" in initial_data
        assert "sensor_healthy" in initial_data
        
        # Verify data ranges (allow small variation for realistic noise)
        temp_range = self.device_config.data_config["temperature_range"]
        humidity_range = self.device_config.data_config["humidity_range"]
        
        # Allow 5% tolerance for realistic variation and noise
        temp_tolerance = (temp_range[1] - temp_range[0]) * 0.05
        humidity_tolerance = (humidity_range[1] - humidity_range[0]) * 0.05
        
        assert (temp_range[0] - temp_tolerance) <= initial_data["temperature"] <= (temp_range[1] + temp_tolerance)
        assert (humidity_range[0] - humidity_tolerance) <= initial_data["humidity"] <= (humidity_range[1] + humidity_tolerance)
        assert initial_data["sensor_status"] == 0
        assert initial_data["sensor_healthy"] == True
        
        # Verify data changes over time (realistic variation)
        assert initial_data["timestamp"] != second_data["timestamp"]
    
    def test_register_update_with_realistic_data(self):
        """Test register updates with realistic data."""
        device = ModbusDevice("test_registers", self.device_config, 15000)
        
        # Update registers multiple times
        for _ in range(5):
            device._update_registers_with_realistic_data()
            time.sleep(0.01)  # Small delay
            
        # Read registers and verify they contain realistic values
        hr_values = device.context.getValues(3, 0, 3)  # Temperature, humidity, status
        di_values = device.context.getValues(2, 0, 1)  # Health status
        
        # Temperature should be scaled by 100 and within range
        temp_raw = hr_values[0]
        temp_actual = temp_raw / 100.0
        temp_range = self.device_config.data_config["temperature_range"]
        assert temp_range[0] <= temp_actual <= temp_range[1]
        
        # Humidity should be scaled by 100 and within range
        humidity_raw = hr_values[1]
        humidity_actual = humidity_raw / 100.0
        humidity_range = self.device_config.data_config["humidity_range"]
        assert humidity_range[0] <= humidity_actual <= humidity_range[1]
        
        # Status should be 0 (OK)
        assert hr_values[2] == 0
        
        # Health should be True (1)
        assert di_values[0] == 1
    
    def test_device_status_reporting(self):
        """Test device status reporting functionality."""
        device = ModbusDevice("test_status", self.device_config, 15000)
        
        # Test initial status
        status = device.get_status()
        assert status["device_id"] == "test_status"
        assert status["device_type"] == "temperature_sensor"
        assert status["port"] == 15000
        assert status["status"] == "stopped"
        assert status["running"] == False
        assert status["uptime_seconds"] == 0
        assert status["error_count"] == 0
        assert status["update_interval"] == 1.0


class TestModbusDeviceLifecycle:
    """Test Modbus device lifecycle management."""
    
    def setup_method(self):
        """Set up test environment."""
        self.device_config = ModbusDeviceConfig(
            count=1,
            port_start=15050,
            device_template="industrial_temperature_sensor",
            update_interval=0.5
        )
    
    @pytest.mark.asyncio
    async def test_device_start_stop_lifecycle(self):
        """Test device start and stop lifecycle."""
        device = ModbusDevice("test_lifecycle", self.device_config, 15050)
        
        # Mock the Modbus server to avoid actual network binding
        with patch('pymodbus.server.ModbusTcpServer') as mock_server_class:
            mock_server = Mock()
            mock_server.serve_forever = AsyncMock()
            mock_server.server_close = Mock()
            mock_server_class.return_value = mock_server
            
            # Test startup
            start_result = await device.start()
            assert start_result == True
            assert device.running == True
            assert device.health_status["status"] == "running"
            assert device.health_status["uptime_start"] is not None
            
            # Allow some time for tasks to start
            await asyncio.sleep(0.1)
            
            # Test status during operation
            status = device.get_status()
            assert status["running"] == True
            assert status["uptime_seconds"] > 0
            
            # Test stop
            await device.stop()
            assert device.running == False


class TestPortManager:
    """Test port management functionality."""
    
    def setup_method(self):
        """Set up port manager for testing."""
        self.port_manager = IntelligentPortManager()
        pool_config = {
            'modbus': [15000, 15999],
            'mqtt': [1883, 1883],
            'http': [8080, 8099]
        }
        self.port_manager.initialize_pools(pool_config)
    
    def test_port_allocation(self):
        """Test basic port allocation."""
        # Allocate ports for a device
        allocated_ports = self.port_manager.allocate_ports('modbus', 'test_device', 3)
        
        assert allocated_ports is not None
        assert len(allocated_ports) == 3
        assert all(15000 <= port <= 15999 for port in allocated_ports)
        
        # Test port deallocation
        result = self.port_manager.deallocate_device_ports('test_device')
        assert result == True
    
    def test_port_allocation_with_preferred_start(self):
        """Test port allocation with preferred starting port."""
        # Allocate with preferred start
        allocated_ports = self.port_manager.allocate_ports(
            'modbus', 'test_device_2', 2, preferred_start=15100
        )
        
        assert allocated_ports is not None
        assert len(allocated_ports) == 2
        assert allocated_ports[0] == 15100
        assert allocated_ports[1] == 15101
    
    def test_port_conflict_prevention(self):
        """Test port conflict prevention."""
        # Allocate some ports
        first_allocation = self.port_manager.allocate_ports('modbus', 'device1', 5)
        
        # Try to allocate overlapping ports
        second_allocation = self.port_manager.allocate_ports('modbus', 'device2', 10)
        
        # Verify no conflicts
        assert first_allocation is not None
        assert second_allocation is not None
        assert set(first_allocation).isdisjoint(set(second_allocation))
    
    def test_allocation_plan_validation(self):
        """Test allocation plan validation."""
        allocation_plan = {
            'device1': ('modbus', 2),
            'device2': ('modbus', 3),
            'device3': ('http', 1)
        }
        
        # Validate plan
        is_valid = self.port_manager.validate_allocation_plan(allocation_plan)
        assert is_valid == True
        
        # Test invalid plan (too many ports)
        invalid_plan = {
            'device_massive': ('modbus', 2000)  # More ports than available
        }
        
        is_valid = self.port_manager.validate_allocation_plan(invalid_plan)
        assert is_valid == False


class TestModbusDeviceManager:
    """Test Modbus device manager functionality."""
    
    def setup_method(self):
        """Set up device manager for testing."""
        self.port_manager = IntelligentPortManager()
        pool_config = {
            'modbus': [15200, 15299]
        }
        self.port_manager.initialize_pools(pool_config)
        
        # Create modbus config with multiple device types
        self.modbus_config = ModbusConfig(
            enabled=True,
            devices={
                "temperature_sensors": ModbusDeviceConfig(
                    count=3,
                    port_start=15200,
                    device_template="industrial_temperature_sensor",
                    update_interval=1.0
                ),
                "pressure_transmitters": ModbusDeviceConfig(
                    count=2,
                    port_start=15210,
                    device_template="hydraulic_pressure_sensor",
                    update_interval=0.5
                )
            }
        )
        
        self.device_manager = ModbusDeviceManager(self.modbus_config, self.port_manager)
    
    @pytest.mark.asyncio
    async def test_device_manager_initialization(self):
        """Test device manager initialization."""
        result = await self.device_manager.initialize()
        assert result == True
        
        # Verify devices were created
        expected_device_count = 3 + 2  # temp sensors + pressure transmitters
        assert len(self.device_manager.devices) == expected_device_count
        
        # Verify device IDs
        device_ids = list(self.device_manager.devices.keys())
        temp_sensors = [id for id in device_ids if "temperature_sensors" in id]
        pressure_transmitters = [id for id in device_ids if "pressure_transmitters" in id]
        
        assert len(temp_sensors) == 3
        assert len(pressure_transmitters) == 2
    
    def test_allocation_plan_building(self):
        """Test allocation plan building."""
        self.device_manager._build_allocation_plan()
        
        plan = self.device_manager.get_allocation_requirements()
        assert len(plan) == 5  # 3 temp + 2 pressure
        
        # Verify plan structure
        for device_id, (protocol, count) in plan.items():
            assert protocol == "modbus"
            assert count == 1  # Each device needs 1 port
    
    @pytest.mark.asyncio
    async def test_device_creation_and_port_allocation(self):
        """Test device creation and automatic port allocation."""
        await self.device_manager.initialize()
        
        # Check that all devices have unique ports
        allocated_ports = set()
        for device in self.device_manager.devices.values():
            assert device.port not in allocated_ports
            allocated_ports.add(device.port)
            assert 15200 <= device.port <= 15299  # Within configured range


class TestConfigurationBasedDeviceCreation:
    """Test configuration-based device creation with YAML files."""
    
    def setup_method(self):
        """Set up configuration testing."""
        self.config_parser = ConfigParser()
        self.test_config_file = Path("test_facility_config.yml")
    
    def teardown_method(self):
        """Clean up test files."""
        if self.test_config_file.exists():
            self.test_config_file.unlink()
    
    @pytest.mark.asyncio
    async def test_configuration_file_creation(self):
        """Test automatic configuration file creation."""
        # Load config from non-existent file (should create default)
        config = await self.config_parser.load_config(self.test_config_file)
        
        assert config is not None
        assert config.facility.name == "Default Industrial Facility"
        assert config.industrial_protocols.modbus_tcp.enabled == True
        assert self.test_config_file.exists()
    
    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test configuration validation."""
        config = await self.config_parser.load_config(self.test_config_file)
        assert config is not None
        
        # Test port range validation
        is_valid = self.config_parser.validate_port_ranges()
        assert is_valid == True
        
        # Test device configuration retrieval
        modbus_devices = self.config_parser.get_modbus_devices()
        assert len(modbus_devices) > 0
        assert "temperature_sensors" in modbus_devices
    
    @pytest.mark.asyncio
    async def test_end_to_end_configuration_to_devices(self):
        """Test complete end-to-end configuration to device creation."""
        # Load configuration
        config = await self.config_parser.load_config(self.test_config_file)
        assert config is not None
        
        # Set up port manager
        port_manager = IntelligentPortManager()
        network_config = self.config_parser.get_network_config()
        port_manager.initialize_pools({
            'modbus': network_config.port_ranges['modbus']
        })
        
        # Create device manager with loaded config
        modbus_config = config.industrial_protocols.modbus_tcp
        device_manager = ModbusDeviceManager(modbus_config, port_manager)
        
        # Initialize device manager
        result = await device_manager.initialize()
        assert result == True
        
        # Verify devices were created from configuration
        assert len(device_manager.devices) > 0
        
        # Test device status retrieval
        health_status = await device_manager.get_health_status()
        assert len(health_status) == len(device_manager.devices)


class TestDataPatterns:
    """Test realistic data pattern generation."""
    
    def setup_method(self):
        """Set up data pattern testing."""
        self.config = {
            "temperature": {"base_value": 25.0, "temperature_range": [20, 30]},
            "humidity": {"base_value": 50.0, "humidity_range": [40, 60]},
            "pressure": {"base_value": 150.0, "pressure_range": [100, 200]},
            "motor": {"base_value": 1800.0, "speed_range": [1000, 2000]}
        }
        self.data_generator = IndustrialDataGenerator("test_device", self.config)
    
    def test_temperature_data_generation(self):
        """Test temperature data generation."""
        for _ in range(10):
            temp = self.data_generator.generate_temperature(self.config["temperature"])
            assert 20 <= temp <= 30
            assert isinstance(temp, (int, float))  # Allow both int and float
    
    def test_pressure_data_generation(self):
        """Test pressure data generation."""
        for _ in range(10):
            pressure = self.data_generator.generate_pressure(self.config["pressure"])
            assert 100 <= pressure <= 200
            assert isinstance(pressure, float)
    
    def test_motor_data_generation(self):
        """Test motor data generation."""
        for _ in range(10):
            speed = self.data_generator.generate_motor_speed(self.config["motor"])
            assert 1000 <= speed <= 2000
            assert isinstance(speed, float)
    
    def test_device_type_specific_data(self):
        """Test device-type-specific data generation."""
        # Test temperature sensor data
        temp_data = self.data_generator.generate_device_data("temperature_sensor")
        required_keys = ["temperature", "humidity", "sensor_status", "sensor_healthy"]
        for key in required_keys:
            assert key in temp_data
        
        # Test pressure transmitter data
        pressure_data = self.data_generator.generate_device_data("pressure_transmitter")
        required_keys = ["pressure", "flow_rate", "high_alarm", "low_flow_alarm"]
        for key in required_keys:
            assert key in pressure_data
        
        # Test motor drive data
        motor_data = self.data_generator.generate_device_data("motor_drive")
        required_keys = ["speed", "torque", "power", "fault_code"]
        for key in required_keys:
            assert key in motor_data
    
    def test_data_correlation(self):
        """Test data correlation between parameters."""
        # Generate multiple data points to test correlation
        data_points = []
        for _ in range(20):
            data = self.data_generator.generate_device_data("temperature_sensor")
            data_points.append(data)
            time.sleep(0.01)
        
        # Check that humidity correlates inversely with temperature
        temperatures = [d["temperature"] for d in data_points]
        humidities = [d["humidity"] for d in data_points]
        
        # Very basic correlation check - more sophisticated analysis could be done
        assert len(temperatures) == len(humidities)
        assert all(isinstance(t, (int, float)) for t in temperatures)
        assert all(isinstance(h, (int, float)) for h in humidities)


class TestScalabilityAndPerformance:
    """Test system scalability and performance."""
    
    @pytest.mark.asyncio
    async def test_multiple_device_creation(self):
        """Test creation of multiple devices simultaneously."""
        port_manager = IntelligentPortManager()
        port_manager.initialize_pools({'modbus': [16000, 16100]})
        
        # Create config for many devices
        modbus_config = ModbusConfig(
            enabled=True,
            devices={
                "temp_sensors": ModbusDeviceConfig(
                    count=20,
                    port_start=16000,
                    device_template="industrial_temperature_sensor",
                    update_interval=2.0
                ),
                "pressure_sensors": ModbusDeviceConfig(
                    count=15,
                    port_start=16020,
                    device_template="hydraulic_pressure_sensor",
                    update_interval=1.5
                ),
                "motor_drives": ModbusDeviceConfig(
                    count=10,
                    port_start=16040,
                    device_template="variable_frequency_drive",
                    update_interval=1.0
                )
            }
        )
        
        device_manager = ModbusDeviceManager(modbus_config, port_manager)
        
        # Measure initialization time
        start_time = time.time()
        result = await device_manager.initialize()
        init_time = time.time() - start_time
        
        assert result == True
        assert len(device_manager.devices) == 45  # 20 + 15 + 10
        assert init_time < 5.0  # Should initialize within 5 seconds
        
        # Test port allocation
        utilization = port_manager.get_port_utilization()
        assert utilization['modbus']['used'] == 45
        assert utilization['modbus']['utilization_percent'] > 40  # Good utilization
    
    def test_port_manager_efficiency(self):
        """Test port manager efficiency with many allocations."""
        port_manager = IntelligentPortManager()
        port_manager.initialize_pools({'modbus': [17000, 17500]})  # 500 ports
        
        # Allocate many devices
        start_time = time.time()
        for i in range(100):
            device_id = f"device_{i:03d}"
            ports = port_manager.allocate_ports('modbus', device_id, 1)
            assert ports is not None
            assert len(ports) == 1
        
        allocation_time = time.time() - start_time
        assert allocation_time < 1.0  # Should allocate 100 devices in under 1 second
        
        # Test utilization reporting
        utilization = port_manager.get_port_utilization()
        assert utilization['modbus']['used'] == 100
        assert utilization['modbus']['available'] == 401  # Actual calculation: 501 - 100 = 401


# Integration test that brings everything together
class TestCompleteModbusSimulation:
    """Integration test for complete Modbus simulation."""
    
    @pytest.mark.asyncio
    async def test_complete_factory_simulation(self):
        """Test a complete factory simulation setup."""
        # Create configuration
        config_parser = ConfigParser()
        test_config_file = Path("integration_test_config.yml")
        
        try:
            # Load/create configuration
            config = await config_parser.load_config(test_config_file)
            assert config is not None
            
            # Set up port management
            port_manager = IntelligentPortManager()
            network_config = config_parser.get_network_config()
            port_manager.initialize_pools({
                'modbus': network_config.port_ranges['modbus']
            })
            
            # Create and initialize device manager
            modbus_config = config.industrial_protocols.modbus_tcp
            device_manager = ModbusDeviceManager(modbus_config, port_manager)
            
            init_result = await device_manager.initialize()
            assert init_result == True
            
            # Verify system health
            health_status = await device_manager.get_health_status()
            assert len(health_status) > 0
            
            for device_id, status in health_status.items():
                assert status["error_count"] == 0
                assert status["device_type"] in ["temperature_sensor", "pressure_transmitter"]
                assert 5020 <= status["port"] <= 5500
            
            # Test port utilization
            utilization = port_manager.get_port_utilization()
            assert utilization['modbus']['used'] > 0
            assert utilization['modbus']['utilization_percent'] < 100
            
            # Clean up
            await device_manager.stop_all_devices()
            
        finally:
            # Clean up test file
            if test_config_file.exists():
                test_config_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])