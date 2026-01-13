#!/usr/bin/env python3
"""
🏭 Industrial Facility Simulator - Modbus TCP Example

This example demonstrates the Modbus TCP device simulation capabilities
with realistic industrial device types and data patterns.

Usage:
    python modbus_example.py

The script will start 3 different Modbus devices:
- Temperature sensor on port 15000
- Pressure transmitter on port 15001  
- Motor drive on port 15002

Connect using any Modbus TCP client to test the devices.
"""

import sys
import os
import asyncio
import time
import signal

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_parser import ModbusDeviceConfig
from protocols.industrial.modbus.modbus_simulator import ModbusDevice
from port_manager import IntelligentPortManager


class ModbusSimulatorDemo:
    """Demo class for Modbus TCP device simulation."""
    
    def __init__(self):
        self.devices = []
        self.port_manager = IntelligentPortManager()
        self.running = False
        
        # Configure port pools
        pool_config = {
            'modbus': [15000, 15999],
            'mqtt': [1883, 1883], 
            'http': [8080, 8099]
        }
        self.port_manager.initialize_pools(pool_config)
        
    async def create_demo_devices(self):
        """Create demonstration Modbus devices."""
        
        # Device configurations
        device_configs = [
            {
                'id': 'temp_sensor_001',
                'template': 'industrial_temperature_sensor',
                'port': 15000,
                'data_config': {
                    'temperature_range': [18, 45],
                    'humidity_range': [30, 80]
                }
            },
            {
                'id': 'pressure_sensor_001', 
                'template': 'hydraulic_pressure_sensor',
                'port': 15001,
                'data_config': {
                    'pressure_range': [0, 300],
                    'flow_range': [10, 150]
                }
            },
            {
                'id': 'motor_drive_001',
                'template': 'variable_frequency_drive', 
                'port': 15002,
                'data_config': {
                    'speed_range': [0, 3600],
                    'torque_range': [0, 500],
                    'power_range': [0, 100]
                }
            }
        ]
        
        print("📟 Starting Modbus devices...")
        
        for config in device_configs:
            # Create device configuration
            device_config = ModbusDeviceConfig(
                count=1,
                port_start=config['port'],
                device_template=config['template'],
                update_interval=1.5,
                data_config=config['data_config']
            )
            
            # Create device
            device = ModbusDevice(config['id'], device_config, config['port'])
            
            # Start device
            if await device.start():
                self.devices.append(device)
                device_type = device.device_type
                print(f"✅ {config['id']} started on port {config['port']}")
                print(f"   📊 Device type: {device_type}")
            else:
                print(f"❌ Failed to start {config['id']}")
                
    def print_connection_info(self):
        """Print connection information for users."""
        print("\n🌐 Connection Information:")
        print("Connect using any Modbus TCP client:")
        
        print("- Temperature Sensor: localhost:15000")
        print("  • HR[0] = Temperature (°C * 100)")
        print("  • HR[1] = Humidity (% * 100)")
        print("  • HR[2] = Status (0=OK)")
        print("  • DI[0] = Sensor Health (1=OK)")
        
        print("\n- Pressure Sensor: localhost:15001")
        print("  • HR[0] = Pressure (PSI * 100)")
        print("  • HR[1] = Flow Rate (L/min * 100)")
        print("  • DI[0] = High Pressure Alarm")
        print("  • DI[1] = Low Flow Alarm")
        
        print("\n- Motor Drive: localhost:15002")
        print("  • HR[0] = Speed (RPM)")
        print("  • HR[1] = Torque (Nm * 100)")
        print("  • HR[2] = Power (kW * 100)")
        print("  • HR[3] = Fault Code")
        
        print("\n🔄 Devices are running with realistic data patterns...")
        print("📊 Data updates automatically every 1-2 seconds")
        print("⏹️  Press Ctrl+C to stop")
        
    async def status_monitor(self):
        """Monitor and display device status periodically."""
        start_time = time.time()
        
        while self.running:
            await asyncio.sleep(5)  # Update every 5 seconds
            
            current_time = time.time()
            print(f"\n📈 Device Status at {current_time - start_time:.1f}s:")
            
            for device in self.devices:
                status = device.get_status()
                uptime = status.get('uptime_seconds', 0)
                print(f"   {device.device_id}: {status['status']} ({uptime:.1f}s uptime)")
                
    async def stop_all_devices(self):
        """Stop all running devices."""
        print("\n🛑 Stopping all devices...")
        
        for device in self.devices:
            await device.stop()
            print(f"   ✅ Stopped {device.device_id}")
            
    async def run(self):
        """Run the demo."""
        self.running = True
        
        # Set up signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print("\n\n🛑 Received shutdown signal...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # Create and start devices
            await self.create_demo_devices()
            
            if not self.devices:
                print("❌ No devices started successfully!")
                return
                
            # Print connection info
            self.print_connection_info()
            
            # Start status monitoring
            monitor_task = asyncio.create_task(self.status_monitor())
            
            # Wait for shutdown
            while self.running:
                await asyncio.sleep(0.1)
                
            # Cancel monitoring
            monitor_task.cancel()
            
        finally:
            # Stop all devices
            await self.stop_all_devices()
            print("✅ Demo completed successfully!")


async def main():
    """Main entry point."""
    print("🏭 Modbus TCP Device Simulator")
    print("=" * 50)
    
    demo = ModbusSimulatorDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())