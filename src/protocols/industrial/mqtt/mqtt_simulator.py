"""
MQTT Device Simulator

This module implements realistic MQTT device simulation with multiple IoT device types,
topic hierarchies, QoS levels, and pub/sub messaging patterns.

Uses a single shared MQTT client for all devices (gateway pattern) for reliability.
"""

import asyncio
import json
import time
import threading
from typing import Any, Dict, List, Optional, Tuple

import structlog

from ....config_parser import MQTTConfig, MQTTDeviceConfig
from ....port_manager import IntelligentPortManager
from ....data_patterns.industrial_patterns import IndustrialDataGenerator

logger = structlog.get_logger(__name__)

# Import paho-mqtt
try:
    import paho.mqtt.client as mqtt
    MQTT_CLIENT = "paho-mqtt"
except ImportError:
    mqtt = None
    MQTT_CLIENT = None
    logger.warning("paho-mqtt library not available. Install paho-mqtt.")


class MQTTDevice:
    """
    Represents a single MQTT IoT device that publishes data to topics.

    Note: The actual MQTT publishing is done through the shared client
    in MQTTDeviceManager.
    """

    def __init__(
        self,
        device_id: str,
        device_config: MQTTDeviceConfig,
        broker_host: str,
        broker_port: int
    ):
        self.device_id = device_id
        self.device_config = device_config
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.device_type = self._extract_device_type(device_config.device_template)

        # State
        self.running = False

        # Data generator
        pattern_config = device_config.data_config or {}
        self.data_generator = IndustrialDataGenerator(device_id, pattern_config)

        # Topic configuration
        self.base_topic = device_config.base_topic or f"devices/{device_id}"
        self.qos = device_config.qos
        self.retain = device_config.retain

        # Message history
        self.message_history: List[Dict] = []
        self.max_history = 100

        # Health tracking
        self.health_status = {
            "status": "stopped",
            "last_publish": None,
            "publish_count": 0,
            "error_count": 0,
            "uptime_start": None
        }

    def _extract_device_type(self, template_name: str) -> str:
        type_mapping = {
            "iot_temperature_sensor": "temperature_sensor",
            "iot_humidity_sensor": "humidity_sensor",
            "iot_environmental_sensor": "environmental_sensor",
            "iot_air_quality_monitor": "air_quality_monitor",
            "smart_meter": "energy_meter",
            "asset_tracker": "asset_tracker",
            "environmental_sensor": "environmental_sensor",
            "generic_iot_sensor": "generic_sensor"
        }
        return type_mapping.get(template_name, "generic_sensor")

    def _build_topics(self) -> Dict[str, str]:
        return {
            "data": f"{self.base_topic}/data",
            "status": f"{self.base_topic}/status",
            "telemetry": f"{self.base_topic}/telemetry",
            "alerts": f"{self.base_topic}/alerts"
        }

    def generate_payload(self) -> Dict[str, Any]:
        """Generate a data payload for publishing."""
        device_data = self.data_generator.generate_device_data(self.device_type)
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "timestamp": time.time(),
            "data": device_data
        }

    def record_publish(self, payload: Dict) -> None:
        """Record a successful publish."""
        self.health_status["last_publish"] = time.time()
        self.health_status["publish_count"] += 1
        self.message_history.append(payload)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def record_error(self) -> None:
        """Record a publish error."""
        self.health_status["error_count"] += 1

    def start(self) -> None:
        """Mark device as started."""
        self.running = True
        self.health_status.update({
            "status": "running",
            "uptime_start": time.time(),
            "error_count": 0
        })

    def stop(self) -> None:
        """Mark device as stopped."""
        self.running = False
        self.health_status["status"] = "stopped"

    def get_status(self) -> Dict[str, Any]:
        uptime = 0
        if self.health_status.get("uptime_start"):
            uptime = time.time() - self.health_status["uptime_start"]

        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "template": self.device_config.device_template,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "base_topic": self.base_topic,
            "qos": self.qos,
            "status": self.health_status["status"],
            "running": self.running,
            "uptime_seconds": round(uptime, 2),
            "publish_count": self.health_status["publish_count"],
            "error_count": self.health_status["error_count"],
            "last_publish": self.health_status.get("last_publish"),
            "publish_interval": self.device_config.publish_interval
        }

    def get_last_message(self) -> Optional[Dict]:
        if self.message_history:
            return self.message_history[-1]
        return None

    def get_message_history(self, limit: int = 10) -> List[Dict]:
        return self.message_history[-limit:]

    def get_register_data(self) -> Optional[Dict]:
        return self.get_last_message()


class MQTTDeviceManager:
    """
    Manages multiple MQTT devices using a single shared MQTT client.

    This gateway pattern is more reliable than per-device connections.
    """

    def __init__(
        self,
        mqtt_config: MQTTConfig,
        port_manager: IntelligentPortManager
    ):
        self.mqtt_config = mqtt_config
        self.port_manager = port_manager
        self.devices: Dict[str, MQTTDevice] = {}
        self.device_allocation_plan: Dict[str, Tuple[str, int]] = {}

        # Broker configuration
        self.broker_host = mqtt_config.broker_host
        self.broker_port = mqtt_config.broker_port
        self.use_embedded_broker = mqtt_config.use_embedded_broker

        # Shared MQTT client
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self._connect_event = threading.Event()
        self._publish_task = None
        self._running = False

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.connected = True
            self._connect_event.set()
            logger.info(
                "MQTT gateway connected to broker",
                broker=f"{self.broker_host}:{self.broker_port}"
            )
        else:
            logger.error("MQTT gateway connection failed", reason_code=reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = False
        self._connect_event.clear()
        if self._running:
            logger.warning("MQTT gateway disconnected", reason_code=reason_code)

    async def initialize(self) -> bool:
        try:
            logger.info("Initializing MQTT Device Manager...")

            if mqtt is None:
                logger.error("paho-mqtt library not available")
                return False

            # Build allocation plan
            self._build_allocation_plan()

            # Create all device instances
            await self._create_devices()

            logger.info(
                "MQTT Device Manager initialized",
                device_count=len(self.devices),
                device_types=list(self.mqtt_config.devices.keys()),
                broker=f"{self.broker_host}:{self.broker_port}",
                mqtt_client=MQTT_CLIENT
            )

            return True

        except Exception as e:
            logger.error("Failed to initialize MQTT Device Manager", error=str(e))
            return False

    def _build_allocation_plan(self) -> None:
        self.device_allocation_plan = {}
        for device_type, device_config in self.mqtt_config.devices.items():
            for i in range(device_config.count):
                device_id = f"mqtt_{device_type}_{i:03d}"
                self.device_allocation_plan[device_id] = ("mqtt", 0)

    async def _create_devices(self) -> None:
        for device_type, device_config in self.mqtt_config.devices.items():
            logger.info(f"Creating {device_config.count} {device_type} MQTT devices...")

            for i in range(device_config.count):
                device_id = f"mqtt_{device_type}_{i:03d}"

                base_topic = device_config.base_topic
                if base_topic:
                    base_topic = f"{base_topic}/{device_id}"
                else:
                    base_topic = f"devices/{device_type}/{device_id}"

                modified_config = MQTTDeviceConfig(
                    count=device_config.count,
                    device_template=device_config.device_template,
                    base_topic=base_topic,
                    publish_interval=device_config.publish_interval,
                    qos=device_config.qos,
                    retain=device_config.retain,
                    locations=device_config.locations,
                    data_config=device_config.data_config
                )

                device = MQTTDevice(
                    device_id=device_id,
                    device_config=modified_config,
                    broker_host=self.broker_host,
                    broker_port=self.broker_port
                )

                self.devices[device_id] = device

    def get_allocation_requirements(self) -> Dict[str, Tuple[str, int]]:
        return self.device_allocation_plan.copy()

    async def start_all_devices(self) -> Optional[Dict[str, MQTTDevice]]:
        try:
            logger.info(f"Starting MQTT gateway and {len(self.devices)} devices...")

            # Check if already running
            if self._running:
                logger.warning("MQTT gateway already running, skipping initialization")
                return self.devices

            # Create and connect shared MQTT client with unique ID
            gateway_id = f"mqtt_gateway_{int(time.time() * 1000)}"  # Use milliseconds
            logger.info(f"Creating MQTT gateway client", client_id=gateway_id)

            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=gateway_id,
                protocol=mqtt.MQTTv311,
                clean_session=True,
            )

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            # Disable auto-reconnect by setting very long delay
            self.client.reconnect_delay_set(min_delay=300, max_delay=600)

            logger.info("Connecting to MQTT broker...")
            try:
                self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            except Exception as e:
                logger.error("MQTT gateway connection failed", error=str(e))
                return None

            logger.info("Starting MQTT loop...")
            self.client.loop_start()

            logger.info("Waiting for connection confirmation...")
            # Use async-friendly wait to avoid blocking the event loop
            # (important when using embedded amqtt broker in same process)
            for _ in range(100):  # 10 seconds total (100 * 0.1s)
                if self._connect_event.is_set():
                    break
                await asyncio.sleep(0.1)
            else:
                logger.error("MQTT gateway connection timeout")
                self.client.loop_stop()
                return None

            logger.info("MQTT gateway connected, setting running flag...")
            self._running = True

            # Mark all devices as started
            for device in self.devices.values():
                device.start()

            # Publish online status for all devices
            for device in self.devices.values():
                topics = device._build_topics()
                status_payload = {
                    "device_id": device.device_id,
                    "status": "online",
                    "timestamp": time.time()
                }
                self.client.publish(
                    topics["status"],
                    json.dumps(status_payload),
                    qos=1,
                    retain=True
                )

            # Start the publish loop
            self._publish_task = asyncio.create_task(self._publish_loop())

            logger.info(
                "MQTT gateway and devices started successfully",
                device_count=len(self.devices)
            )

            return self.devices

        except Exception as e:
            logger.error("Failed to start MQTT devices", error=str(e))
            return None

    async def _publish_loop(self) -> None:
        """Publish data for all devices based on their intervals."""
        # Track last publish time for each device
        last_publish: Dict[str, float] = {}

        try:
            while self._running:
                if not self.connected:
                    logger.warning("MQTT gateway not connected, waiting...")
                    await asyncio.sleep(1)
                    continue

                current_time = time.time()

                for device_id, device in self.devices.items():
                    if not device.running:
                        continue

                    interval = device.device_config.publish_interval
                    last_time = last_publish.get(device_id, 0)

                    if current_time - last_time >= interval:
                        # Time to publish for this device
                        try:
                            payload = device.generate_payload()
                            topics = device._build_topics()

                            result = self.client.publish(
                                topics["data"],
                                json.dumps(payload),
                                qos=device.qos,
                                retain=device.retain
                            )

                            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                                device.record_publish(payload)
                                last_publish[device_id] = current_time
                                logger.debug(
                                    "Published MQTT data",
                                    device_id=device_id,
                                    topic=topics["data"]
                                )
                            else:
                                device.record_error()
                                logger.warning(
                                    "MQTT publish failed",
                                    device_id=device_id,
                                    rc=result.rc
                                )

                        except Exception as e:
                            device.record_error()
                            logger.error(
                                "Error publishing for device",
                                device_id=device_id,
                                error=str(e)
                            )

                # Small sleep to prevent busy loop
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("MQTT publish loop cancelled")
        except Exception as e:
            logger.error("Fatal error in MQTT publish loop", error=str(e))

    async def stop_all_devices(self) -> None:
        try:
            logger.info("Stopping MQTT gateway and devices...")

            self._running = False

            if self._publish_task and not self._publish_task.done():
                self._publish_task.cancel()
                try:
                    await self._publish_task
                except asyncio.CancelledError:
                    pass

            # Publish offline status
            if self.connected and self.client:
                for device in self.devices.values():
                    topics = device._build_topics()
                    status_payload = {
                        "device_id": device.device_id,
                        "status": "offline",
                        "timestamp": time.time()
                    }
                    self.client.publish(
                        topics["status"],
                        json.dumps(status_payload),
                        qos=1,
                        retain=True
                    )
                    device.stop()

            if self.client:
                self.client.loop_stop()
                self.client.disconnect()

            self.connected = False
            logger.info("MQTT gateway and devices stopped")

        except Exception as e:
            logger.error("Error stopping MQTT devices", error=str(e))

    async def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            device_id: device.get_status()
            for device_id, device in self.devices.items()
        }

    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        if device_id in self.devices:
            return self.devices[device_id].get_status()
        return None

    async def restart_device(self, device_id: str) -> bool:
        if device_id not in self.devices:
            return False
        device = self.devices[device_id]
        device.stop()
        device.start()
        return True

    def get_broker_info(self) -> Dict[str, Any]:
        return {
            "broker_host": self.broker_host,
            "broker_port": self.broker_port,
            "embedded": self.use_embedded_broker,
            "status": "connected" if self.connected else "disconnected",
            "gateway_client_id": "mqtt_gateway"
        }

    def get_all_topics(self) -> List[Dict[str, Any]]:
        topics = []
        for device_id, device in self.devices.items():
            device_topics = device._build_topics()
            topics.append({
                "device_id": device_id,
                "topics": device_topics
            })
        return topics
