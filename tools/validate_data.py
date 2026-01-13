#!/usr/bin/env python3
"""
Data Validation Tool for Universal Simulation Engine

This script validates that simulated devices are generating realistic and correct data.
"""

import argparse
import asyncio
import time
from typing import Dict, List, Any
from pymodbus.client import ModbusTcpClient
import structlog

logger = structlog.get_logger(__name__)

class DataValidator:
    """Validates device data for correctness and realism."""
    
    def __init__(self, host: str = "localhost"):
        self.host = host
        self.validation_results = []
        
    def validate_modbus_device(self, port: int, device_type: str, duration: int = 60) -> Dict[str, Any]:
        """
        Validate a Modbus device for the specified duration.
        
        Args:
            port: Modbus TCP port
            device_type: Type of device (temperature_sensor, pressure_transmitter, motor_drive)
            duration: Duration to collect data (seconds)
            
        Returns:
            Validation results dictionary
        """
        logger.info(f"Validating Modbus device on port {port} for {duration} seconds...")
        
        client = ModbusTcpClient(self.host, port=port)
        if not client.connect():
            return {
                "success": False,
                "error": f"Failed to connect to device on port {port}"
            }
        
        readings = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # Read holding registers (typically 0-2 for basic sensors)
                result = client.read_holding_registers(0, 3)
                
                if result.isError():
                    logger.warning(f"Read error on port {port}")
                    time.sleep(1)
                    continue
                    
                readings.append({
                    "timestamp": time.time(),
                    "values": result.registers
                })
                
                time.sleep(2)  # Sample every 2 seconds
                
        finally:
            client.close()
        
        # Analyze collected data
        return self._analyze_readings(port, device_type, readings)
    
    def _analyze_readings(self, port: int, device_type: str, readings: List[Dict]) -> Dict[str, Any]:
        """Analyze collected readings for validity."""
        
        if not readings:
            return {
                "success": False,
                "port": port,
                "error": "No readings collected"
            }
        
        result = {
            "success": True,
            "port": port,
            "device_type": device_type,
            "total_readings": len(readings),
            "checks": {}
        }
        
        # Extract values
        all_values = [r["values"] for r in readings]
        
        # Check 1: Data is changing (not stuck)
        unique_values = len(set(tuple(v) for v in all_values))
        result["checks"]["data_changes"] = {
            "status": "PASS" if unique_values > len(readings) * 0.1 else "FAIL",
            "unique_readings": unique_values,
            "total_readings": len(readings),
            "message": f"{unique_values}/{len(readings)} unique readings"
        }
        
        # Check 2: Values are within expected ranges (device-specific)
        range_check = self._check_value_ranges(device_type, all_values)
        result["checks"]["value_ranges"] = range_check
        
        # Check 3: No wild jumps (realistic changes)
        stability_check = self._check_stability(all_values)
        result["checks"]["stability"] = stability_check
        
        # Check 4: Timing consistency
        timing_check = self._check_timing(readings)
        result["checks"]["timing"] = timing_check
        
        # Overall pass/fail
        all_passed = all(
            check.get("status") == "PASS" 
            for check in result["checks"].values()
        )
        result["overall_status"] = "PASS" if all_passed else "FAIL"
        
        return result
    
    def _check_value_ranges(self, device_type: str, values: List[List[int]]) -> Dict[str, Any]:
        """Check if values are within expected ranges for device type."""
        
        ranges = {
            "temperature_sensor": {
                "register_0": (1800, 4500),  # 18-45°C × 100
                "register_1": (3000, 8000),  # 30-80% humidity × 100
                "register_2": (0, 5)          # Status code
            },
            "pressure_transmitter": {
                "register_0": (0, 30000),     # 0-300 PSI × 100
                "register_1": (1000, 15000),  # 10-150 L/min × 100
                "register_2": (0, 5)          # Status
            },
            "motor_drive": {
                "register_0": (0, 3600),      # 0-3600 RPM
                "register_1": (0, 5000),      # 0-500 Nm × 10
                "register_2": (0, 1000)       # 0-100 kW × 10
            }
        }
        
        expected_ranges = ranges.get(device_type, {})
        if not expected_ranges:
            return {
                "status": "SKIP",
                "message": f"Unknown device type: {device_type}"
            }
        
        violations = []
        for idx, (reg_name, (min_val, max_val)) in enumerate(expected_ranges.items()):
            for reading in values:
                if idx < len(reading):
                    value = reading[idx]
                    if not (min_val <= value <= max_val):
                        violations.append(f"{reg_name}: {value} not in [{min_val}, {max_val}]")
        
        return {
            "status": "PASS" if not violations else "FAIL",
            "violations": violations[:5],  # Show first 5 violations
            "total_violations": len(violations)
        }
    
    def _check_stability(self, values: List[List[int]]) -> Dict[str, Any]:
        """Check for unrealistic jumps in values."""
        
        large_jumps = []
        
        for i in range(1, len(values)):
            prev = values[i-1]
            curr = values[i]
            
            for reg_idx in range(min(len(prev), len(curr))):
                change = abs(curr[reg_idx] - prev[reg_idx])
                
                # Maximum realistic change per 2-second interval
                # Temperature: 10°C × 100 = 1000
                # Pressure: 50 PSI × 100 = 5000
                # Motor speed: 500 RPM
                max_change = 5000
                
                if change > max_change:
                    large_jumps.append({
                        "register": reg_idx,
                        "change": change,
                        "from": prev[reg_idx],
                        "to": curr[reg_idx]
                    })
        
        return {
            "status": "PASS" if len(large_jumps) < len(values) * 0.05 else "FAIL",
            "large_jumps": len(large_jumps),
            "total_intervals": len(values) - 1,
            "message": f"{len(large_jumps)} unrealistic jumps detected"
        }
    
    def _check_timing(self, readings: List[Dict]) -> Dict[str, Any]:
        """Check if readings arrive at consistent intervals."""
        
        if len(readings) < 2:
            return {"status": "SKIP", "message": "Not enough readings"}
        
        intervals = []
        for i in range(1, len(readings)):
            interval = readings[i]["timestamp"] - readings[i-1]["timestamp"]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        max_deviation = max(abs(i - avg_interval) for i in intervals)
        
        # Expect ~2 second intervals with <0.5s deviation
        return {
            "status": "PASS" if max_deviation < 0.5 else "WARN",
            "average_interval": round(avg_interval, 2),
            "max_deviation": round(max_deviation, 2),
            "message": f"Average: {avg_interval:.2f}s, Max deviation: {max_deviation:.2f}s"
        }

def print_validation_results(results: Dict[str, Any]):
    """Pretty print validation results."""
    
    print("\n" + "="*70)
    print(f"📊 Validation Results - Port {results['port']}")
    print("="*70)
    
    print(f"\nDevice Type: {results.get('device_type', 'Unknown')}")
    print(f"Total Readings: {results.get('total_readings', 0)}")
    print(f"Overall Status: {results.get('overall_status', 'UNKNOWN')}")
    
    print("\n" + "-"*70)
    print("Individual Checks:")
    print("-"*70)
    
    for check_name, check_result in results.get("checks", {}).items():
        status = check_result.get("status", "UNKNOWN")
        status_symbol = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
        
        print(f"\n{status_symbol} {check_name.replace('_', ' ').title()}: {status}")
        print(f"   {check_result.get('message', '')}")
        
        if "violations" in check_result and check_result["violations"]:
            print(f"   Violations: {check_result['violations']}")
    
    print("\n" + "="*70)

async def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate simulation data from Universal Simulation Engine"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Simulator host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Modbus TCP port to validate"
    )
    parser.add_argument(
        "--device-type",
        choices=["temperature_sensor", "pressure_transmitter", "motor_drive"],
        required=True,
        help="Type of device to validate"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Validation duration in seconds (default: 60)"
    )
    
    args = parser.parse_args()
    
    validator = DataValidator(args.host)
    
    print(f"\n🔍 Starting validation of {args.device_type} on port {args.port}")
    print(f"   Duration: {args.duration} seconds")
    print(f"   Host: {args.host}\n")
    
    results = validator.validate_modbus_device(
        port=args.port,
        device_type=args.device_type,
        duration=args.duration
    )
    
    print_validation_results(results)
    
    # Exit with appropriate code
    if results.get("overall_status") == "PASS":
        print("\n✅ All validation checks passed!")
        return 0
    else:
        print("\n❌ Some validation checks failed!")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))