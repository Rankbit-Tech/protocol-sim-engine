"""
MQTT Protocol Simulation Module

This module provides MQTT protocol simulation capabilities with support for
multiple IoT device types, topic hierarchies, and QoS levels.
"""

from .mqtt_simulator import MQTTDevice, MQTTDeviceManager

__all__ = ["MQTTDevice", "MQTTDeviceManager"]
