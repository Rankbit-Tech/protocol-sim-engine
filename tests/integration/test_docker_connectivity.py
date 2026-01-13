#!/usr/bin/env python3
"""
Test script to verify Modbus connectivity to the Docker container
"""

import sys
import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

def test_modbus_device(host, port, device_name, register_addresses):
    """Test connection and read registers from a Modbus device"""
    print(f"\n🔍 Testing {device_name} on {host}:{port}")
    print("=" * 50)
    
    client = ModbusTcpClient(host=host, port=port)
    
    try:
        # Connect to device
        if not client.connect():
            print(f"❌ Failed to connect to {device_name}")
            return False
            
        print(f"✅ Connected to {device_name}")
        
        # Read registers
        for reg_addr, reg_name in register_addresses.items():
            try:
                response = client.read_holding_registers(address=reg_addr - 40001, count=1)
                if response.isError():
                    print(f"❌ Error reading {reg_name} (register {reg_addr}): {response}")
                else:
                    value = response.registers[0]
                    # Convert from raw register value if needed
                    if 'temperature' in reg_name.lower():
                        actual_value = value / 100.0  # Temperature scaled by 100
                        print(f"📊 {reg_name}: {actual_value:.2f}°C (raw: {value})")
                    elif 'pressure' in reg_name.lower():
                        actual_value = value / 100.0  # Pressure scaled by 100
                        print(f"📊 {reg_name}: {actual_value:.2f} PSI (raw: {value})")
                    elif 'speed' in reg_name.lower():
                        print(f"📊 {reg_name}: {value} RPM")
                    else:
                        print(f"📊 {reg_name}: {value}")
                        
            except Exception as e:
                print(f"❌ Exception reading {reg_name}: {e}")
        
        # Test discrete inputs
        try:
            response = client.read_discrete_inputs(address=0, count=4)
            if not response.isError():
                print(f"📊 Status bits: {response.bits[:4]}")
        except Exception as e:
            print(f"📊 Status bits: Not available ({e})")
            
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Exception testing {device_name}: {e}")
        return False

def main():
    """Main test function"""
    print("🏭 Industrial Facility Simulator - Docker Modbus Test")
    print("=" * 60)
    
    host = "localhost"
    
    # Define devices and their expected registers
    devices = {
        15000: {
            "name": "Temperature Sensor",
            "registers": {
                40001: "Temperature",
                40002: "Humidity", 
                40003: "Status"
            }
        },
        15001: {
            "name": "Pressure Transmitter", 
            "registers": {
                40001: "Pressure",
                40002: "Flow Rate",
                40003: "Status"
            }
        },
        15002: {
            "name": "Motor Drive",
            "registers": {
                40001: "Speed",
                40002: "Torque", 
                40003: "Power",
                40004: "Fault Code"
            }
        }
    }
    
    # Test each device
    results = []
    for port, device_info in devices.items():
        success = test_modbus_device(
            host, 
            port, 
            device_info["name"], 
            device_info["registers"]
        )
        results.append((device_info["name"], success))
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for device_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {device_name}")
        if not success:
            all_passed = False
    
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())