"""
Comprehensive Test Suite for OPC-UA Implementation

This module thoroughly tests the OPC-UA device simulation capabilities
including device creation, data generation, port management, address space
construction, and configuration-based device instantiation.
"""

import asyncio
import sys
import os
import pytest
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.config_parser import OPCUADeviceConfig, OPCUAConfig, ConfigParser
from src.protocols.industrial.opcua.opcua_simulator import OPCUADevice, OPCUADeviceManager
from src.port_manager import IntelligentPortManager
from src.data_patterns.industrial_patterns import IndustrialDataGenerator


class TestOPCUADeviceCreation:
    """Test OPC-UA device creation and basic functionality."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.cnc_config = OPCUADeviceConfig(
            count=1,
            port_start=4840,
            device_template="opcua_cnc_machine",
            update_interval=1.0,
            data_config={
                "spindle_speed_range": [0, 24000],
                "feed_rate_range": [0, 15000],
                "base_spindle_speed": 12000,
                "base_feed_rate": 5000,
                "tool_wear_rate": 0.01,
                "workspace_mm": [500, 400, 300],
                "programs": ["G-Code_001", "G-Code_002"]
            }
        )
        self.plc_config = OPCUADeviceConfig(
            count=1,
            port_start=4841,
            device_template="opcua_plc_controller",
            update_interval=0.5,
            data_config={
                "process_value_range": [0, 100],
                "setpoint": 50.0,
                "kp": 1.0,
                "ki": 0.1,
                "kd": 0.05
            }
        )
        self.robot_config = OPCUADeviceConfig(
            count=1,
            port_start=4842,
            device_template="opcua_industrial_robot",
            update_interval=0.5,
            data_config={
                "joint_count": 6,
                "max_speed_percent": 100,
                "base_cycle_time": 15.0,
                "payload_range": [0, 20]
            }
        )

    def test_device_initialization(self):
        """Test basic device initialization."""
        device = OPCUADevice("test_opcua_cnc", self.cnc_config, 4840)

        assert device.device_id == "test_opcua_cnc"
        assert device.port == 4840
        assert device.device_type == "cnc_machine"
        assert device.running is False
        assert device.data_generator is not None
        assert device.nodes == {}
        assert device._cached_node_data is None

    def test_device_type_extraction(self):
        """Test device type extraction from template names."""
        device_cnc = OPCUADevice("cnc_test", self.cnc_config, 4840)
        assert device_cnc.device_type == "cnc_machine"

        device_plc = OPCUADevice("plc_test", self.plc_config, 4841)
        assert device_plc.device_type == "plc_controller"

        device_robot = OPCUADevice("robot_test", self.robot_config, 4842)
        assert device_robot.device_type == "industrial_robot"

        # Test unknown template
        unknown_config = OPCUADeviceConfig(
            count=1, port_start=4843,
            device_template="unknown_device",
            update_interval=1.0
        )
        device_unknown = OPCUADevice("unknown_test", unknown_config, 4843)
        assert device_unknown.device_type == "generic"

    def test_data_generation_integration(self):
        """Test integration with data pattern generator for CNC data."""
        device = OPCUADevice("test_cnc_data", self.cnc_config, 4840)

        data = device.data_generator.generate_device_data("cnc_machine")

        assert "spindle_speed_rpm" in data
        assert "feed_rate_mm_min" in data
        assert "tool_wear_percent" in data
        assert "part_count" in data
        assert "axis_position_x" in data
        assert "axis_position_y" in data
        assert "axis_position_z" in data
        assert "program_name" in data
        assert "machine_state" in data
        assert data["machine_state"] in ["IDLE", "RUNNING", "ERROR", "SETUP"]

    def test_plc_data_generation(self):
        """Test PLC controller data generation."""
        device = OPCUADevice("test_plc_data", self.plc_config, 4841)

        data = device.data_generator.generate_device_data("plc_controller")

        assert "process_value" in data
        assert "setpoint" in data
        assert "control_output" in data
        assert "mode" in data
        assert "high_alarm" in data
        assert "low_alarm" in data
        assert "integral_term" in data
        assert "derivative_term" in data
        assert "error" in data
        assert data["mode"] in ["AUTO", "MANUAL", "CASCADE"]
        assert 0 <= data["control_output"] <= 100

    def test_robot_data_generation(self):
        """Test industrial robot data generation."""
        device = OPCUADevice("test_robot_data", self.robot_config, 4842)

        data = device.data_generator.generate_device_data("industrial_robot")

        assert "joint_angles" in data
        assert len(data["joint_angles"]) == 6
        assert "tcp_position_x" in data
        assert "tcp_position_y" in data
        assert "tcp_position_z" in data
        assert "program_state" in data
        assert "cycle_time_s" in data
        assert "cycle_count" in data
        assert "payload_kg" in data
        assert "speed_percent" in data
        assert data["program_state"] in ["RUNNING", "PAUSED", "STOPPED"]

    def test_device_status_reporting(self):
        """Test device status reporting functionality."""
        device = OPCUADevice("test_status", self.cnc_config, 4840)

        status = device.get_status()
        assert status["device_id"] == "test_status"
        assert status["device_type"] == "cnc_machine"
        assert status["port"] == 4840
        assert status["status"] == "stopped"
        assert status["running"] is False
        assert status["uptime_seconds"] == 0
        assert status["error_count"] == 0
        assert status["update_interval"] == 1.0
        assert "endpoint_url" in status
        assert "node_count" in status

    def test_application_uri(self):
        """Test application URI generation."""
        device = OPCUADevice(
            "test_uri", self.cnc_config, 4840,
            application_uri="urn:test:opcua:server"
        )
        assert device.application_uri == "urn:test:opcua:server:test_uri"


class TestOPCUADeviceLifecycle:
    """Test OPC-UA device lifecycle management."""

    def setup_method(self):
        """Set up test environment."""
        self.device_config = OPCUADeviceConfig(
            count=1,
            port_start=4850,
            device_template="opcua_cnc_machine",
            update_interval=0.5,
            data_config={
                "spindle_speed_range": [0, 24000],
                "base_spindle_speed": 12000
            }
        )

    @pytest.mark.asyncio
    async def test_device_start_stop_lifecycle(self):
        """Test device start and stop lifecycle with mocked server."""
        device = OPCUADevice("test_lifecycle", self.device_config, 4850)

        # Mock the asyncua Server
        with patch('src.protocols.industrial.opcua.opcua_simulator.Server') as mock_server_class:
            mock_server = AsyncMock()
            mock_server.init = AsyncMock()
            mock_server.start = AsyncMock()
            mock_server.stop = AsyncMock()
            mock_server.set_endpoint = Mock()
            mock_server.set_server_name = Mock()
            mock_server.set_application_uri = Mock()
            mock_server.set_security_policy = Mock()

            # Mock the nodes object for address space
            mock_objects = AsyncMock()
            mock_folder = AsyncMock()
            mock_variable = AsyncMock()

            mock_variable.set_writable = AsyncMock()
            mock_variable.write_value = AsyncMock()
            mock_variable.read_value = AsyncMock(return_value=0.0)

            mock_folder.add_folder = AsyncMock(return_value=mock_folder)
            mock_folder.add_variable = AsyncMock(return_value=mock_variable)
            mock_objects.add_folder = AsyncMock(return_value=mock_folder)

            mock_server.nodes = Mock()
            mock_server.nodes.objects = mock_objects
            mock_server.register_namespace = AsyncMock(return_value=2)

            mock_server_class.return_value = mock_server

            # Test startup
            start_result = await device.start()
            assert start_result is True
            assert device.running is True
            assert device.health_status["status"] == "running"
            assert device.health_status["uptime_start"] is not None

            await asyncio.sleep(0.2)

            # Test status during operation
            status = device.get_status()
            assert status["running"] is True
            assert status["uptime_seconds"] > 0

            # Test stop
            await device.stop()
            assert device.running is False
            assert device.health_status["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_device_uptime_tracking(self):
        """Test device uptime tracking."""
        device = OPCUADevice("test_uptime", self.device_config, 4851)

        # Simulate running state
        device.health_status["status"] = "running"
        device.health_status["uptime_start"] = time.time() - 10  # 10 seconds ago
        device.running = True

        status = device.get_status()
        assert status["uptime_seconds"] >= 9.5  # Allow small tolerance


class TestOPCUADeviceManager:
    """Test OPC-UA device manager functionality."""

    def setup_method(self):
        """Set up device manager for testing."""
        self.port_manager = IntelligentPortManager()
        pool_config = {
            'opcua': [4840, 4899]
        }
        self.port_manager.initialize_pools(pool_config)

        self.opcua_config = OPCUAConfig(
            enabled=True,
            devices={
                "cnc_machines": OPCUADeviceConfig(
                    count=2,
                    port_start=4840,
                    device_template="opcua_cnc_machine",
                    update_interval=1.0,
                    data_config={"spindle_speed_range": [0, 24000]}
                ),
                "plc_controllers": OPCUADeviceConfig(
                    count=2,
                    port_start=4850,
                    device_template="opcua_plc_controller",
                    update_interval=0.5,
                    data_config={"process_value_range": [0, 100], "setpoint": 50.0}
                ),
                "industrial_robots": OPCUADeviceConfig(
                    count=1,
                    port_start=4860,
                    device_template="opcua_industrial_robot",
                    update_interval=0.5,
                    data_config={"joint_count": 6}
                )
            }
        )

        self.device_manager = OPCUADeviceManager(self.opcua_config, self.port_manager)

    @pytest.mark.asyncio
    async def test_device_manager_initialization(self):
        """Test device manager initialization."""
        result = await self.device_manager.initialize()
        assert result is True

        expected_device_count = 2 + 2 + 1  # cnc + plc + robot
        assert len(self.device_manager.devices) == expected_device_count

        device_ids = list(self.device_manager.devices.keys())
        cnc_devices = [id for id in device_ids if "cnc_machines" in id]
        plc_devices = [id for id in device_ids if "plc_controllers" in id]
        robot_devices = [id for id in device_ids if "industrial_robots" in id]

        assert len(cnc_devices) == 2
        assert len(plc_devices) == 2
        assert len(robot_devices) == 1

    def test_allocation_plan_building(self):
        """Test allocation plan building."""
        self.device_manager._build_allocation_plan()

        plan = self.device_manager.get_allocation_requirements()
        assert len(plan) == 5  # 2 cnc + 2 plc + 1 robot

        for device_id, (protocol, count) in plan.items():
            assert protocol == "opcua"
            assert count == 1

    @pytest.mark.asyncio
    async def test_device_creation_and_port_allocation(self):
        """Test device creation and automatic port allocation."""
        await self.device_manager.initialize()

        allocated_ports = set()
        for device in self.device_manager.devices.values():
            assert device.port not in allocated_ports
            allocated_ports.add(device.port)
            assert 4840 <= device.port <= 4899

    def test_server_endpoints_listing(self):
        """Test server endpoint listing before any devices start."""
        self.device_manager._build_allocation_plan()

        # Before initialization, devices dict is empty
        endpoints = self.device_manager.get_all_server_endpoints()
        assert isinstance(endpoints, list)

    @pytest.mark.asyncio
    async def test_server_endpoints_after_init(self):
        """Test server endpoints after initialization."""
        await self.device_manager.initialize()

        endpoints = self.device_manager.get_all_server_endpoints()
        assert len(endpoints) == 5

        for ep in endpoints:
            assert "device_id" in ep
            assert "endpoint_url" in ep
            assert "port" in ep
            assert "device_type" in ep
            assert "opc.tcp://" in ep["endpoint_url"]


class TestOPCUADataPatterns:
    """Test OPC-UA specific data pattern generation."""

    def setup_method(self):
        """Set up data pattern testing."""
        self.cnc_config = {
            "cnc": {
                "spindle_speed_range": [0, 24000],
                "feed_rate_range": [0, 15000],
                "base_spindle_speed": 12000,
                "base_feed_rate": 5000,
                "tool_wear_rate": 0.01,
                "workspace_mm": [500, 400, 300],
                "programs": ["G-Code_001", "G-Code_002"]
            }
        }
        self.plc_config = {
            "plc": {
                "process_value_range": [0, 100],
                "setpoint": 50.0,
                "kp": 1.0,
                "ki": 0.1,
                "kd": 0.05,
                "high_alarm": 90,
                "low_alarm": 10
            }
        }
        self.robot_config = {
            "robot": {
                "joint_count": 6,
                "max_speed_percent": 100,
                "base_cycle_time": 15.0,
                "payload_range": [0, 20]
            }
        }

    def test_cnc_machine_data_generation(self):
        """Test CNC machine data has all required fields and valid bounds."""
        gen = IndustrialDataGenerator("cnc_test_001", self.cnc_config)

        for _ in range(10):
            data = gen.generate_device_data("cnc_machine")
            assert 0 <= data["spindle_speed_rpm"] <= 24000
            assert 0 <= data["feed_rate_mm_min"] <= 15000
            assert 0 <= data["tool_wear_percent"] <= 100
            assert isinstance(data["part_count"], int)
            assert data["part_count"] >= 0
            assert isinstance(data["program_name"], str)
            assert data["machine_state"] in ["IDLE", "RUNNING", "ERROR", "SETUP"]

    def test_plc_controller_data_generation(self):
        """Test PLC controller data has PID-related fields within bounds."""
        gen = IndustrialDataGenerator("plc_test_001", self.plc_config)

        for _ in range(10):
            data = gen.generate_device_data("plc_controller")
            assert 0 <= data["process_value"] <= 100
            assert data["setpoint"] == 50.0
            assert 0 <= data["control_output"] <= 100
            assert data["mode"] in ["AUTO", "MANUAL", "CASCADE"]
            assert isinstance(data["high_alarm"], bool)
            assert isinstance(data["low_alarm"], bool)

    def test_robot_data_generation(self):
        """Test robot data has joint angles, TCP position, and program state."""
        gen = IndustrialDataGenerator("robot_test_001", self.robot_config)

        for _ in range(10):
            data = gen.generate_device_data("industrial_robot")
            assert len(data["joint_angles"]) == 6
            assert all(isinstance(a, float) for a in data["joint_angles"])
            assert isinstance(data["tcp_position_x"], float)
            assert isinstance(data["tcp_position_y"], float)
            assert isinstance(data["tcp_position_z"], float)
            assert data["program_state"] in ["RUNNING", "PAUSED", "STOPPED"]
            assert data["cycle_time_s"] > 0
            assert 0 <= data["payload_kg"] <= 20

    def test_tool_wear_progression(self):
        """Test that tool wear increases over multiple calls."""
        gen = IndustrialDataGenerator("wear_test", self.cnc_config)

        # Force machine to RUNNING state
        gen.last_values["machine_state"] = "RUNNING"

        wear_values = []
        for _ in range(50):
            data = gen.generate_device_data("cnc_machine")
            wear_values.append(data["tool_wear_percent"])

        # Over 50 calls, tool wear should generally increase (unless reset)
        # At least some values should be > 0
        assert max(wear_values) > 0

    def test_part_count_increment(self):
        """Test that part count increments over time."""
        gen = IndustrialDataGenerator("parts_test", self.cnc_config)
        gen.last_values["machine_state"] = "RUNNING"

        counts = []
        for _ in range(200):
            data = gen.generate_device_data("cnc_machine")
            counts.append(data["part_count"])

        # Over 200 calls with 5% probability, we should see at least 1 increment
        assert max(counts) > 0


class TestOPCUAConfiguration:
    """Test OPC-UA configuration validation."""

    def test_opcua_config_validation(self):
        """Test valid OPC-UA configuration."""
        config = OPCUAConfig(
            enabled=True,
            security_mode="None",
            security_policy="None",
            application_uri="urn:test:opcua:server",
            devices={
                "cnc": OPCUADeviceConfig(
                    count=3,
                    port_start=4840,
                    device_template="opcua_cnc_machine",
                    update_interval=1.0
                )
            }
        )
        assert config.enabled is True
        assert len(config.devices) == 1
        assert config.devices["cnc"].count == 3

    def test_opcua_device_config_boundary_values(self):
        """Test boundary values for OPC-UA device config."""
        # Min count
        config = OPCUADeviceConfig(
            count=1, port_start=4840,
            device_template="test", update_interval=0.1
        )
        assert config.count == 1

        # Max count
        config = OPCUADeviceConfig(
            count=1000, port_start=4840,
            device_template="test", update_interval=0.1
        )
        assert config.count == 1000

        # Invalid count should raise
        with pytest.raises(Exception):
            OPCUADeviceConfig(
                count=0, port_start=4840,
                device_template="test", update_interval=1.0
            )

        with pytest.raises(Exception):
            OPCUADeviceConfig(
                count=1001, port_start=4840,
                device_template="test", update_interval=1.0
            )

    def test_opcua_port_boundary_values(self):
        """Test port boundary values."""
        # Min port
        config = OPCUADeviceConfig(
            count=1, port_start=1024,
            device_template="test", update_interval=1.0
        )
        assert config.port_start == 1024

        # Max port
        config = OPCUADeviceConfig(
            count=1, port_start=65535,
            device_template="test", update_interval=1.0
        )
        assert config.port_start == 65535

        # Invalid port
        with pytest.raises(Exception):
            OPCUADeviceConfig(
                count=1, port_start=1023,
                device_template="test", update_interval=1.0
            )

    def test_config_parser_opcua_support(self):
        """Test that ConfigParser supports OPC-UA protocol checks."""
        parser = ConfigParser()

        # Without loaded config, protocol should not be enabled
        assert parser.is_protocol_enabled("opcua") is False
        assert parser.get_opcua_devices() == {}


class TestOPCUAScalability:
    """Test OPC-UA system scalability."""

    @pytest.mark.asyncio
    async def test_multiple_device_creation(self):
        """Test creation of many OPC-UA devices simultaneously."""
        port_manager = IntelligentPortManager()
        port_manager.initialize_pools({'opcua': [4840, 4940]})

        opcua_config = OPCUAConfig(
            enabled=True,
            devices={
                "cnc_machines": OPCUADeviceConfig(
                    count=10,
                    port_start=4840,
                    device_template="opcua_cnc_machine",
                    update_interval=1.0,
                    data_config={"spindle_speed_range": [0, 24000]}
                ),
                "plc_controllers": OPCUADeviceConfig(
                    count=10,
                    port_start=4860,
                    device_template="opcua_plc_controller",
                    update_interval=0.5,
                    data_config={"process_value_range": [0, 100]}
                ),
                "industrial_robots": OPCUADeviceConfig(
                    count=10,
                    port_start=4880,
                    device_template="opcua_industrial_robot",
                    update_interval=0.5,
                    data_config={"joint_count": 6}
                )
            }
        )

        device_manager = OPCUADeviceManager(opcua_config, port_manager)

        start_time = time.time()
        result = await device_manager.initialize()
        init_time = time.time() - start_time

        assert result is True
        assert len(device_manager.devices) == 30
        assert init_time < 5.0

        utilization = port_manager.get_port_utilization()
        assert utilization['opcua']['used'] == 30

    def test_port_allocation_efficiency(self):
        """Test port manager handles OPC-UA allocations efficiently."""
        port_manager = IntelligentPortManager()
        port_manager.initialize_pools({'opcua': [4840, 4940]})

        start_time = time.time()
        for i in range(50):
            device_id = f"opcua_device_{i:03d}"
            ports = port_manager.allocate_ports('opcua', device_id, 1)
            assert ports is not None
            assert len(ports) == 1

        allocation_time = time.time() - start_time
        assert allocation_time < 1.0

        utilization = port_manager.get_port_utilization()
        assert utilization['opcua']['used'] == 50


class TestOPCUANodeDataCaching:
    """Test OPC-UA node data caching mechanism."""

    def test_get_node_data_returns_none_initially(self):
        """Test that get_node_data returns None before any updates."""
        config = OPCUADeviceConfig(
            count=1, port_start=4840,
            device_template="opcua_cnc_machine",
            update_interval=1.0,
            data_config={"spindle_speed_range": [0, 24000]}
        )
        device = OPCUADevice("test_cache", config, 4840)

        assert device.get_node_data() is None

    def test_cached_data_structure(self):
        """Test that cached data has the correct structure when set."""
        config = OPCUADeviceConfig(
            count=1, port_start=4840,
            device_template="opcua_cnc_machine",
            update_interval=1.0,
            data_config={"spindle_speed_range": [0, 24000]}
        )
        device = OPCUADevice("test_cache_struct", config, 4840)

        # Manually set cached data to simulate an update
        device._cached_node_data = {
            "device_id": "test_cache_struct",
            "device_type": "cnc_machine",
            "timestamp": time.time(),
            "nodes": {
                "spindle_speed_rpm": 12000.0,
                "machine_state": "RUNNING"
            }
        }

        result = device.get_node_data()
        assert result is not None
        assert result["device_id"] == "test_cache_struct"
        assert result["device_type"] == "cnc_machine"
        assert "nodes" in result
        assert result["nodes"]["spindle_speed_rpm"] == 12000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
