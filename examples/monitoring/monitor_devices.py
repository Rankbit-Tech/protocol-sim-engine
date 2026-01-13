#!/usr/bin/env python3
"""
Real-time Device Monitoring Example

This script demonstrates how to monitor devices in real-time,
detect anomalies, and log important events.
"""

import argparse
import asyncio
import time
from datetime import datetime
from typing import Dict, List
import requests
from pymodbus.client import ModbusTcpClient

class DeviceMonitor:
    """Real-time monitoring of simulated devices."""
    
    def __init__(self, api_base: str = "http://localhost:8080"):
        self.api_base = api_base
        self.alert_thresholds = {
            "temperature_high": 40.0,  # °C
            "temperature_low": 20.0,
            "pressure_high": 250.0,    # PSI
            "pressure_low": 10.0,
            "no_data_timeout": 10.0    # seconds
        }
        self.device_history = {}
        
    async def monitor_all_devices(self, duration: int = 300, interval: int = 5):
        """
        Monitor all devices for specified duration.
        
        Args:
            duration: Total monitoring duration in seconds
            interval: Check interval in seconds
        """
        print(f"\n🔍 Starting device monitoring for {duration} seconds")
        print(f"   Checking every {interval} seconds")
        print(f"   API: {self.api_base}\n")
        print("="*80)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < duration:
            iteration += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n[{timestamp}] Iteration #{iteration}")
            print("-"*80)
            
            try:
                # Get all devices
                response = requests.get(f"{self.api_base}/devices", timeout=5)
                devices = response.json().get("devices", [])
                
                if not devices:
                    print("⚠️  No devices found")
                    await asyncio.sleep(interval)
                    continue
                
                # Monitor each device
                for device in devices:
                    await self._monitor_device(device)
                
                # Check system health
                await self._check_system_health()
                
            except Exception as e:
                print(f"❌ Error during monitoring: {e}")
            
            await asyncio.sleep(interval)
        
        print("\n" + "="*80)
        print("✅ Monitoring completed")
        self._print_summary()
    
    async def _monitor_device(self, device: Dict):
        """Monitor a single device."""
        device_id = device.get("id", "unknown")
        device_type = device.get("type", "unknown")
        protocol = device.get("protocol", "unknown")
        port = device.get("port")
        
        print(f"\n📟 {device_id} ({device_type} on port {port})")
        
        try:
            if protocol == "modbus_tcp":
                await self._monitor_modbus_device(device_id, port, device_type)
            else:
                print(f"   ℹ️  Protocol {protocol} - monitoring via API only")
                await self._monitor_via_api(device_id)
                
        except Exception as e:
            print(f"   ❌ Error monitoring device: {e}")
            self._log_alert(device_id, "monitoring_error", str(e))
    
    async def _monitor_modbus_device(self, device_id: str, port: int, device_type: str):
        """Monitor a Modbus device by reading its registers."""
        client = ModbusTcpClient("localhost", port=port)
        
        if not client.connect():
            print(f"   ❌ Failed to connect to port {port}")
            self._log_alert(device_id, "connection_failed", f"Port {port}")
            return
        
        try:
            # Read holding registers
            result = client.read_holding_registers(0, 3)
            
            if result.isError():
                print(f"   ❌ Read error")
                self._log_alert(device_id, "read_error", "Failed to read registers")
                return
            
            # Parse values based on device type
            values = result.registers
            
            if device_type == "temperature_sensor":
                temp = values[0] / 100.0  # Temperature in °C
                humidity = values[1] / 100.0  # Humidity in %
                status = values[2]
                
                print(f"   🌡️  Temperature: {temp:.2f}°C")
                print(f"   💧 Humidity: {humidity:.1f}%")
                print(f"   📊 Status: {status}")
                
                # Check thresholds
                if temp > self.alert_thresholds["temperature_high"]:
                    print(f"   ⚠️  HIGH TEMPERATURE ALERT: {temp:.2f}°C")
                    self._log_alert(device_id, "high_temperature", f"{temp:.2f}°C")
                elif temp < self.alert_thresholds["temperature_low"]:
                    print(f"   ⚠️  LOW TEMPERATURE ALERT: {temp:.2f}°C")
                    self._log_alert(device_id, "low_temperature", f"{temp:.2f}°C")
                else:
                    print(f"   ✅ Temperature within normal range")
                
            elif device_type == "pressure_transmitter":
                pressure = values[0] / 100.0  # Pressure in PSI
                flow = values[1] / 100.0  # Flow in L/min
                status = values[2]
                
                print(f"   📈 Pressure: {pressure:.2f} PSI")
                print(f"   💨 Flow: {flow:.2f} L/min")
                print(f"   📊 Status: {status}")
                
                # Check thresholds
                if pressure > self.alert_thresholds["pressure_high"]:
                    print(f"   ⚠️  HIGH PRESSURE ALERT: {pressure:.2f} PSI")
                    self._log_alert(device_id, "high_pressure", f"{pressure:.2f} PSI")
                elif pressure < self.alert_thresholds["pressure_low"]:
                    print(f"   ⚠️  LOW PRESSURE ALERT: {pressure:.2f} PSI")
                    self._log_alert(device_id, "low_pressure", f"{pressure:.2f} PSI")
                else:
                    print(f"   ✅ Pressure within normal range")
                
            elif device_type == "motor_drive":
                speed = values[0]  # RPM
                torque = values[1] / 10.0  # Nm
                power = values[2] / 10.0  # kW
                
                print(f"   ⚡ Speed: {speed} RPM")
                print(f"   🔧 Torque: {torque:.1f} Nm")
                print(f"   💪 Power: {power:.1f} kW")
                print(f"   ✅ Motor operating normally")
            
            # Store in history
            self._update_history(device_id, {"values": values, "timestamp": time.time()})
            
        finally:
            client.close()
    
    async def _monitor_via_api(self, device_id: str):
        """Monitor device via API endpoint."""
        try:
            response = requests.get(f"{self.api_base}/devices/{device_id}/data", timeout=5)
            data = response.json()
            
            if "error" in data:
                print(f"   ❌ {data['error']}")
                return
            
            print(f"   📊 Data: {data.get('values', {})}")
            print(f"   ✅ Device responding")
            
        except Exception as e:
            print(f"   ❌ API error: {e}")
    
    async def _check_system_health(self):
        """Check overall system health."""
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            health = response.json()
            
            status = health.get("status", "unknown")
            if status == "healthy":
                print(f"\n💚 System Health: HEALTHY")
            else:
                print(f"\n⚠️  System Health: {status}")
                if "reason" in health:
                    print(f"   Reason: {health['reason']}")
                    
        except Exception as e:
            print(f"\n❌ Health check failed: {e}")
    
    def _update_history(self, device_id: str, data: Dict):
        """Update device history."""
        if device_id not in self.device_history:
            self.device_history[device_id] = []
        self.device_history[device_id].append(data)
        # Keep last 100 readings
        if len(self.device_history[device_id]) > 100:
            self.device_history[device_id].pop(0)
    
    def _log_alert(self, device_id: str, alert_type: str, details: str):
        """Log an alert (in production, this would go to a logging system)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = f"[{timestamp}] ALERT: {device_id} - {alert_type} - {details}"
        
        # In production, send to logging system, email, Slack, etc.
        print(f"   🚨 {alert_msg}")
    
    def _print_summary(self):
        """Print monitoring summary."""
        print("\n📊 Monitoring Summary")
        print("="*80)
        print(f"Total devices monitored: {len(self.device_history)}")
        for device_id, history in self.device_history.items():
            print(f"  • {device_id}: {len(history)} readings collected")
        print("="*80)

async def main():
    """Main monitoring function."""
    parser = argparse.ArgumentParser(
        description="Monitor devices in Universal Simulation Engine"
    )
    parser.add_argument(
        "--api",
        default="http://localhost:8080",
        help="API base URL (default: http://localhost:8080)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Monitoring duration in seconds (default: 300)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Check interval in seconds (default: 5)"
    )
    
    args = parser.parse_args()
    
    monitor = DeviceMonitor(args.api)
    
    try:
        await monitor.monitor_all_devices(
            duration=args.duration,
            interval=args.interval
        )
    except KeyboardInterrupt:
        print("\n\n⏸️  Monitoring interrupted by user")
        monitor._print_summary()

if __name__ == "__main__":
    asyncio.run(main())