"""
Comprehensive Test Suite for MQTT Protocol Implementation

This module thoroughly tests the MQTT protocol simulation capabilities
including device creation, data generation, topic management, and message publishing.
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

from src.config_parser import MQTTDeviceConfig, MQTTConfig, ConfigParser
from src.protocols.industrial.mqtt.mqtt_simulator import MQTTDevice, MQTTDeviceManager
from src.port_manager import IntelligentPortManager
from src.data_patterns.industrial_patterns import IndustrialDataGenerator


class TestMQTTDeviceCreation:
    """Test MQTT device creation and basic functionality."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.device_config = MQTTDeviceConfig(
            count=1,
            device_template="iot_environmental_sensor",
            base_topic="test/sensors",
            publish_interval=1.0,
            qos=1,
            data_config={
                "temperature_range": [20, 30],
                "humidity_range": [40, 60]
            }
        )

    def test_device_initialization(self):
        """Test basic device initialization."""
        device = MQTTDevice(
            device_id="test_device_001",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        assert device.device_id == "test_device_001"
        assert device.broker_host == "localhost"
        assert device.broker_port == 1883
        assert device.device_type == "environmental_sensor"
        assert device.base_topic == "test/sensors"
        assert device.qos == 1
        assert device.running is False
        assert device.data_generator is not None

    def test_device_type_extraction(self):
        """Test device type extraction from template names."""
        # Test environmental sensor
        config1 = MQTTDeviceConfig(
            count=1,
            device_template="iot_environmental_sensor",
            publish_interval=1.0
        )
        device1 = MQTTDevice("env_test", config1, "localhost", 1883)
        assert device1.device_type == "environmental_sensor"

        # Test smart meter
        config2 = MQTTDeviceConfig(
            count=1,
            device_template="smart_meter",
            publish_interval=1.0
        )
        device2 = MQTTDevice("meter_test", config2, "localhost", 1883)
        assert device2.device_type == "energy_meter"

        # Test asset tracker
        config3 = MQTTDeviceConfig(
            count=1,
            device_template="asset_tracker",
            publish_interval=1.0
        )
        device3 = MQTTDevice("tracker_test", config3, "localhost", 1883)
        assert device3.device_type == "asset_tracker"

        # Test generic sensor
        config4 = MQTTDeviceConfig(
            count=1,
            device_template="unknown_template",
            publish_interval=1.0
        )
        device4 = MQTTDevice("generic_test", config4, "localhost", 1883)
        assert device4.device_type == "generic_sensor"

    def test_topic_building(self):
        """Test topic hierarchy is built correctly."""
        device = MQTTDevice(
            device_id="test_device_001",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        topics = device._build_topics()

        assert "data" in topics
        assert "status" in topics
        assert "telemetry" in topics
        assert "alerts" in topics
        assert topics["data"] == "test/sensors/data"
        assert topics["status"] == "test/sensors/status"

    def test_status_reporting(self):
        """Test device status reporting."""
        device = MQTTDevice(
            device_id="test_device_001",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        status = device.get_status()

        assert status["device_id"] == "test_device_001"
        assert status["status"] == "stopped"
        assert status["running"] is False
        assert status["publish_count"] == 0
        assert status["error_count"] == 0
        assert status["qos"] == 1
        assert status["base_topic"] == "test/sensors"

    def test_message_history(self):
        """Test message history management."""
        device = MQTTDevice(
            device_id="test_device_001",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        # Add messages
        for i in range(150):  # More than max_history (100)
            device._add_to_history({"index": i, "value": f"message_{i}"})

        # Should only keep last 100
        assert len(device.message_history) == 100
        assert device.message_history[-1]["index"] == 149
        assert device.message_history[0]["index"] == 50

    def test_get_last_message(self):
        """Test retrieving last message."""
        device = MQTTDevice(
            device_id="test_device_001",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        # Initially no messages
        assert device.get_last_message() is None

        # Add messages
        device._add_to_history({"msg": "first"})
        device._add_to_history({"msg": "second"})
        device._add_to_history({"msg": "third"})

        last_msg = device.get_last_message()
        assert last_msg["msg"] == "third"

    def test_get_message_history_with_limit(self):
        """Test retrieving message history with limit."""
        device = MQTTDevice(
            device_id="test_device_001",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        # Add messages
        for i in range(20):
            device._add_to_history({"index": i})

        # Get last 5
        history = device.get_message_history(limit=5)
        assert len(history) == 5
        assert history[-1]["index"] == 19
        assert history[0]["index"] == 15


class TestMQTTDeviceLifecycle:
    """Test MQTT device lifecycle management."""

    def setup_method(self):
        """Set up test environment."""
        self.device_config = MQTTDeviceConfig(
            count=1,
            device_template="iot_environmental_sensor",
            publish_interval=0.5
        )

    @pytest.mark.asyncio
    async def test_device_start_without_broker(self):
        """Test device start behavior when broker is not available."""
        device = MQTTDevice(
            device_id="test_lifecycle",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        # Start the device - it should return True and set running to True
        # even without a broker (the publish loop will handle connection errors)
        start_result = await device.start()
        assert start_result is True
        assert device.running is True
        assert device.health_status["status"] == "running"

        # Stop the device
        await device.stop()
        assert device.running is False
        assert device.health_status["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_device_stop_cancels_task(self):
        """Test that stopping device cancels the publish task."""
        device = MQTTDevice(
            device_id="test_task_cancel",
            device_config=self.device_config,
            broker_host="localhost",
            broker_port=1883
        )

        await device.start()
        assert device.publish_task is not None
        assert not device.publish_task.done()

        await device.stop()
        assert device.running is False
        # Task should be cancelled
        await asyncio.sleep(0.1)
        assert device.publish_task.done() or device.publish_task.cancelled()


class TestMQTTDeviceManager:
    """Test MQTT device manager functionality."""

    def setup_method(self):
        """Set up device manager for testing."""
        self.port_manager = IntelligentPortManager()
        pool_config = {
            'mqtt': [1883, 1883],
            'modbus': [15000, 15100]
        }
        self.port_manager.initialize_pools(pool_config)

        # Create MQTT config with multiple device types
        self.mqtt_config = MQTTConfig(
            enabled=True,
            use_embedded_broker=False,
            broker_host="localhost",
            broker_port=1883,
            devices={
                "environmental_sensors": MQTTDeviceConfig(
                    count=3,
                    device_template="iot_environmental_sensor",
                    base_topic="factory/environment",
                    publish_interval=5.0
                ),
                "energy_meters": MQTTDeviceConfig(
                    count=2,
                    device_template="smart_meter",
                    base_topic="factory/energy",
                    publish_interval=10.0
                )
            }
        )

        self.device_manager = MQTTDeviceManager(self.mqtt_config, self.port_manager)

    @pytest.mark.asyncio
    async def test_device_manager_initialization(self):
        """Test device manager initialization."""
        result = await self.device_manager.initialize()
        assert result is True

        # Verify devices were created
        expected_device_count = 3 + 2  # env sensors + energy meters
        assert len(self.device_manager.devices) == expected_device_count

        # Verify device IDs
        device_ids = list(self.device_manager.devices.keys())
        env_sensors = [id for id in device_ids if "environmental_sensors" in id]
        energy_meters = [id for id in device_ids if "energy_meters" in id]

        assert len(env_sensors) == 3
        assert len(energy_meters) == 2

    def test_allocation_plan_building(self):
        """Test allocation plan building."""
        self.device_manager._build_allocation_plan()

        plan = self.device_manager.get_allocation_requirements()
        assert len(plan) == 5  # 3 env + 2 energy

        # Verify plan structure
        for device_id, (protocol, count) in plan.items():
            assert protocol == "mqtt"
            assert count == 0  # MQTT doesn't use per-device ports

    @pytest.mark.asyncio
    async def test_device_creation_with_unique_topics(self):
        """Test that each device gets a unique topic."""
        await self.device_manager.initialize()

        # Check that all devices have unique base topics
        base_topics = set()
        for device in self.device_manager.devices.values():
            assert device.base_topic not in base_topics
            base_topics.add(device.base_topic)

    def test_broker_info(self):
        """Test broker info retrieval."""
        broker_info = self.device_manager.get_broker_info()

        assert broker_info["broker_host"] == "localhost"
        assert broker_info["broker_port"] == 1883
        assert broker_info["embedded"] is False

    @pytest.mark.asyncio
    async def test_get_all_topics(self):
        """Test retrieving all topics."""
        await self.device_manager.initialize()

        topics = self.device_manager.get_all_topics()

        assert len(topics) == 5  # 5 devices
        for topic_info in topics:
            assert "device_id" in topic_info
            assert "topics" in topic_info
            assert "data" in topic_info["topics"]
            assert "status" in topic_info["topics"]


class TestMQTTDataGeneration:
    """Test MQTT-specific data generation."""

    def setup_method(self):
        """Set up data generation testing."""
        self.config = {
            "temperature": {"base_value": 25.0, "temperature_range": [20, 30]},
            "humidity": {"base_value": 50.0, "humidity_range": [40, 60]},
            "air_quality": {"base_aqi": 50},
            "energy": {"base_voltage": 230.0, "base_current": 20.0},
            "tracker": {"zone_ids": ["zone_a", "zone_b", "zone_c"]}
        }
        self.data_generator = IndustrialDataGenerator("test_mqtt_device", self.config)

    def test_environmental_sensor_data_generation(self):
        """Test environmental sensor data generation."""
        data = self.data_generator.generate_device_data("environmental_sensor")

        assert "temperature" in data
        assert "humidity" in data
        assert "air_quality_index" in data
        assert "co2_ppm" in data
        assert "tvoc_ppb" in data
        assert "pressure_hpa" in data

        # Check ranges
        assert 0 <= data["air_quality_index"] <= 500
        assert data["co2_ppm"] >= 350
        assert data["tvoc_ppb"] >= 0

    def test_energy_meter_data_generation(self):
        """Test energy meter data generation."""
        data = self.data_generator.generate_device_data("energy_meter")

        assert "voltage_v" in data
        assert "current_a" in data
        assert "power_kw" in data
        assert "power_factor" in data
        assert "frequency_hz" in data
        assert "energy_kwh" in data
        assert "phase" in data

        # Check ranges
        assert 200 <= data["voltage_v"] <= 260
        assert data["current_a"] >= 0
        assert data["power_kw"] >= 0
        assert 0.7 <= data["power_factor"] <= 1.0
        assert 49 <= data["frequency_hz"] <= 51

    def test_asset_tracker_data_generation(self):
        """Test asset tracker data generation."""
        data = self.data_generator.generate_device_data("asset_tracker")

        assert "asset_id" in data
        assert "zone_id" in data
        assert "rssi" in data
        assert "battery_percent" in data
        assert "motion_detected" in data
        assert "last_seen_gateway" in data

        # Check ranges
        assert -100 <= data["rssi"] <= -30
        assert 0 <= data["battery_percent"] <= 100
        assert isinstance(data["motion_detected"], bool)
        assert data["zone_id"] in ["zone_a", "zone_b", "zone_c"]

    def test_generic_sensor_data_generation(self):
        """Test generic sensor data generation."""
        data = self.data_generator.generate_device_data("generic_sensor")

        assert "temperature" in data
        assert "humidity" in data

    def test_air_quality_generation(self):
        """Test air quality metric generation."""
        air_quality = self.data_generator.generate_air_quality(self.config["air_quality"])

        assert "air_quality_index" in air_quality
        assert "co2_ppm" in air_quality
        assert "tvoc_ppb" in air_quality
        assert "pressure_hpa" in air_quality

        assert 0 <= air_quality["air_quality_index"] <= 500
        assert air_quality["co2_ppm"] >= 350

    def test_energy_meter_generation(self):
        """Test energy meter data generation method."""
        energy_data = self.data_generator.generate_energy_meter_data(self.config["energy"])

        required_keys = ["voltage_v", "current_a", "power_kw", "power_factor", "frequency_hz", "energy_kwh"]
        for key in required_keys:
            assert key in energy_data

    def test_asset_tracker_generation(self):
        """Test asset tracker data generation method."""
        tracker_data = self.data_generator.generate_asset_tracker_data(self.config["tracker"])

        required_keys = ["asset_id", "zone_id", "rssi", "battery_percent", "motion_detected", "last_seen_gateway"]
        for key in required_keys:
            assert key in tracker_data

    def test_battery_drain_over_time(self):
        """Test battery drain simulation for asset trackers."""
        config = {"battery_drain_rate": 1.0}  # High drain for testing

        initial_data = self.data_generator.generate_asset_tracker_data(config)
        initial_battery = initial_data["battery_percent"]

        # Generate more data points
        for _ in range(10):
            data = self.data_generator.generate_asset_tracker_data(config)

        final_battery = data["battery_percent"]

        # Battery should have decreased
        assert final_battery < initial_battery


class TestConfigurationBasedMQTTDeviceCreation:
    """Test configuration-based MQTT device creation."""

    def setup_method(self):
        """Set up configuration testing."""
        self.config_parser = ConfigParser()
        self.test_config_file = Path("test_mqtt_config.yml")

    def teardown_method(self):
        """Clean up test files."""
        if self.test_config_file.exists():
            self.test_config_file.unlink()

    @pytest.mark.asyncio
    async def test_mqtt_config_in_default_configuration(self):
        """Test that MQTT config is properly loaded from default configuration."""
        config = await self.config_parser.load_config(self.test_config_file)

        assert config is not None
        # Check if MQTT is in the industrial_protocols (may or may not be enabled)
        # The default config should have MQTT defined
        protocols = config.industrial_protocols
        assert protocols is not None

    def test_mqtt_device_config_validation(self):
        """Test MQTT device configuration validation."""
        # Valid config
        valid_config = MQTTDeviceConfig(
            count=5,
            device_template="iot_environmental_sensor",
            publish_interval=5.0,
            qos=1
        )
        assert valid_config.count == 5
        assert valid_config.qos == 1

        # Invalid count
        with pytest.raises(ValueError):
            MQTTDeviceConfig(
                count=0,  # Invalid - must be > 0
                device_template="test",
                publish_interval=1.0
            )

        # Invalid QoS
        with pytest.raises(ValueError):
            MQTTDeviceConfig(
                count=1,
                device_template="test",
                publish_interval=1.0,
                qos=3  # Invalid - must be 0, 1, or 2
            )

    def test_mqtt_config_validation(self):
        """Test MQTT configuration validation."""
        # Valid config
        valid_config = MQTTConfig(
            enabled=True,
            broker_host="localhost",
            broker_port=1883,
            devices={}
        )
        assert valid_config.enabled is True
        assert valid_config.broker_port == 1883

        # Invalid port
        with pytest.raises(ValueError):
            MQTTConfig(
                enabled=True,
                broker_port=80000  # Invalid - port too high
            )


class TestMQTTScalability:
    """Test MQTT system scalability."""

    @pytest.mark.asyncio
    async def test_multiple_device_creation(self):
        """Test creation of multiple MQTT devices."""
        port_manager = IntelligentPortManager()
        port_manager.initialize_pools({'mqtt': [1883, 1883]})

        mqtt_config = MQTTConfig(
            enabled=True,
            broker_host="localhost",
            broker_port=1883,
            devices={
                "sensors": MQTTDeviceConfig(
                    count=50,
                    device_template="iot_environmental_sensor",
                    publish_interval=5.0
                ),
                "meters": MQTTDeviceConfig(
                    count=25,
                    device_template="smart_meter",
                    publish_interval=10.0
                ),
                "trackers": MQTTDeviceConfig(
                    count=25,
                    device_template="asset_tracker",
                    publish_interval=30.0
                )
            }
        )

        device_manager = MQTTDeviceManager(mqtt_config, port_manager)

        # Measure initialization time
        start_time = time.time()
        result = await device_manager.initialize()
        init_time = time.time() - start_time

        assert result is True
        assert len(device_manager.devices) == 100  # 50 + 25 + 25
        assert init_time < 5.0  # Should initialize within 5 seconds

    @pytest.mark.asyncio
    async def test_device_manager_health_status(self):
        """Test health status reporting with multiple devices."""
        port_manager = IntelligentPortManager()
        port_manager.initialize_pools({'mqtt': [1883, 1883]})

        mqtt_config = MQTTConfig(
            enabled=True,
            broker_host="localhost",
            broker_port=1883,
            devices={
                "sensors": MQTTDeviceConfig(
                    count=10,
                    device_template="iot_environmental_sensor",
                    publish_interval=5.0
                )
            }
        )

        device_manager = MQTTDeviceManager(mqtt_config, port_manager)
        await device_manager.initialize()

        health_status = await device_manager.get_health_status()

        assert len(health_status) == 10
        for device_id, status in health_status.items():
            assert "status" in status
            assert "device_type" in status
            assert "publish_count" in status


class TestMQTTBrokerIntegration:
    """Test MQTT broker integration functionality."""

    def test_broker_info_structure(self):
        """Test broker info returns correct structure."""
        port_manager = IntelligentPortManager()
        port_manager.initialize_pools({'mqtt': [1883, 1883]})

        mqtt_config = MQTTConfig(
            enabled=True,
            use_embedded_broker=True,
            broker_host="0.0.0.0",
            broker_port=1883,
            devices={}
        )

        device_manager = MQTTDeviceManager(mqtt_config, port_manager)
        broker_info = device_manager.get_broker_info()

        assert broker_info["broker_host"] == "0.0.0.0"
        assert broker_info["broker_port"] == 1883
        assert broker_info["embedded"] is True
        assert "status" in broker_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
