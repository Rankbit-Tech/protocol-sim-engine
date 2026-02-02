"""
Embedded MQTT Broker Wrapper

This module provides a wrapper for embedded MQTT broker functionality.
It can work with amqtt or connect to an external broker like Mosquitto.
"""

import asyncio
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class EmbeddedMQTTBroker:
    """
    Embedded MQTT broker for standalone simulation.

    This class wraps an MQTT broker library for integrated deployment.
    Currently supports:
    - External broker connection (default)
    - Future: amqtt embedded broker
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 1883,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the embedded broker.

        Args:
            host: Broker bind address
            port: Broker port
            config: Additional broker configuration
        """
        self.host = host
        self.port = port
        self.config = config or {}
        self.broker = None
        self.running = False
        self._broker_task = None

    async def start(self) -> bool:
        """
        Start the embedded broker.

        Returns:
            True if broker started successfully
        """
        try:
            logger.info(
                "Starting embedded MQTT broker",
                host=self.host,
                port=self.port
            )

            # Try to import amqtt for embedded broker
            try:
                from amqtt.broker import Broker

                # Configuration for amqtt broker
                broker_config = {
                    "listeners": {
                        "default": {
                            "type": "tcp",
                            "bind": f"{self.host}:{self.port}"
                        }
                    },
                    "sys_interval": 10,
                    "auth": {
                        "allow-anonymous": True
                    },
                    "topic-check": {
                        "enabled": False
                    }
                }

                # Merge with custom config
                broker_config.update(self.config)

                # Create and start broker
                self.broker = Broker(broker_config)
                await self.broker.start()

                self.running = True
                logger.info("Embedded MQTT broker (amqtt) started successfully")
                return True

            except ImportError:
                logger.warning(
                    "amqtt not installed - embedded broker not available. "
                    "Using external broker mode. Install with: pip install amqtt"
                )
                # Fall back to expecting external broker
                self.running = True  # Assume external broker is running
                return True

        except Exception as e:
            logger.error("Failed to start embedded broker", error=str(e))
            return False

    async def stop(self) -> None:
        """Stop the embedded broker."""
        try:
            if self.broker:
                logger.info("Stopping embedded MQTT broker...")
                await self.broker.shutdown()
                self.broker = None

            self.running = False
            logger.info("Embedded MQTT broker stopped")

        except Exception as e:
            logger.error("Error stopping embedded broker", error=str(e))

    def is_running(self) -> bool:
        """Check if broker is running."""
        return self.running

    def get_status(self) -> Dict[str, Any]:
        """Get broker status information."""
        return {
            "host": self.host,
            "port": self.port,
            "running": self.running,
            "embedded": self.broker is not None
        }


async def check_broker_connectivity(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    Check if an MQTT broker is reachable.

    Args:
        host: Broker hostname
        port: Broker port
        timeout: Connection timeout in seconds

    Returns:
        True if broker is reachable
    """
    try:
        # Try to open a TCP connection to the broker
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True

    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return False
