"""
Industrial Data Pattern Generation

This module provides realistic data generation patterns that mimic real industrial devices.
"""

import math
import random
import time
from typing import Any, Dict, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

class IndustrialDataGenerator:
    """
    Generates realistic data patterns for industrial devices.
    
    This class provides various pattern types:
    - Sinusoidal patterns with noise (temperature cycles, etc.)
    - Random walk patterns (drift over time)
    - Step functions (process changes)
    - Correlated patterns (humidity vs temperature)
    """
    
    def __init__(self, device_id: str, pattern_config: Dict[str, Any]):
        """
        Initialize data generator for a specific device.
        
        Args:
            device_id: Unique device identifier
            pattern_config: Configuration for data patterns
        """
        self.device_id = device_id
        self.pattern_config = pattern_config
        self.start_time = time.time()
        self.last_values: Dict[str, float] = {}
        self.drift_accumulator: Dict[str, float] = {}
        self.random_state = np.random.RandomState(hash(device_id) % 2**32)
        
    def generate_temperature(self, config: Dict[str, Any]) -> float:
        """
        Generate realistic temperature data.
        
        Args:
            config: Temperature configuration parameters
            
        Returns:
            Generated temperature value in Celsius
        """
        current_time = time.time()
        elapsed_hours = (current_time - self.start_time) / 3600.0
        
        # Base temperature from configuration
        base_temp = config.get("base_value", 25.0)
        
        # Daily cycle (sinusoidal pattern)
        daily_cycle = config.get("daily_cycle", {})
        if daily_cycle.get("enabled", True):
            amplitude = daily_cycle.get("amplitude", 5.0)
            peak_hour = daily_cycle.get("peak_hour", 14.0)  # 2 PM
            
            # Time of day in hours (0-24)
            time_of_day = (elapsed_hours % 24)
            phase_shift = (peak_hour - 6) * math.pi / 12  # Peak at specified hour
            
            daily_variation = amplitude * math.sin(
                (time_of_day * 2 * math.pi / 24) - phase_shift
            )
        else:
            daily_variation = 0
            
        # Industrial heating effect
        heating_config = config.get("industrial_heating", {})
        if heating_config.get("enabled", False):
            current_hour = time.localtime().tm_hour
            heating_periods = heating_config.get("heating_periods", ["09:00-17:00"])
            
            # Check if we're in a heating period
            in_heating_period = False
            for period in heating_periods:
                start_str, end_str = period.split("-")
                start_hour = int(start_str.split(":")[0])
                end_hour = int(end_str.split(":")[0])
                
                if start_hour <= current_hour <= end_hour:
                    in_heating_period = True
                    break
                    
            heating_effect = (
                heating_config.get("heating_effect", 10.0) if in_heating_period else 0
            )
        else:
            heating_effect = 0
            
        # Random noise
        noise_config = config.get("noise", {})
        noise_std = noise_config.get("std_dev", 0.5)
        noise = self.random_state.normal(0, noise_std)
        
        # Sensor drift over time
        drift_config = config.get("sensor_drift", {})
        if drift_config.get("enabled", False):
            drift_rate = drift_config.get("drift_rate", 0.001)  # degrees per hour
            
            if "temperature" not in self.drift_accumulator:
                self.drift_accumulator["temperature"] = 0
                
            self.drift_accumulator["temperature"] += drift_rate * (elapsed_hours % 1)
            
            # Reset drift on calibration (monthly)
            calibration_interval = drift_config.get("calibration_reset", "monthly")
            if calibration_interval == "monthly" and elapsed_hours > 720:  # 30 days
                self.drift_accumulator["temperature"] = 0
        else:
            self.drift_accumulator["temperature"] = 0
            
        # Combine all effects
        temperature = (
            base_temp + 
            daily_variation + 
            heating_effect + 
            noise + 
            self.drift_accumulator.get("temperature", 0)
        )
        
        # Apply realistic bounds
        temp_range = config.get("temperature_range", [18, 45])
        temperature = max(temp_range[0], min(temp_range[1], temperature))
        
        self.last_values["temperature"] = temperature
        return round(temperature, 2)
    
    def generate_humidity(self, config: Dict[str, Any]) -> float:
        """
        Generate realistic humidity data (often correlated with temperature).
        
        Args:
            config: Humidity configuration parameters
            
        Returns:
            Generated humidity value as percentage
        """
        base_humidity = config.get("base_value", 45.0)
        variation = config.get("variation", 15.0)
        
        # Correlation with temperature (inverse relationship)
        correlation_factor = config.get("correlation_factor", -0.3)
        if "temperature" in self.last_values:
            temp_deviation = self.last_values["temperature"] - 25.0  # Assume 25°C baseline
            correlated_change = correlation_factor * temp_deviation
        else:
            correlated_change = 0
            
        # Random variation
        random_variation = self.random_state.normal(0, variation / 3)
        
        humidity = base_humidity + correlated_change + random_variation
        
        # Apply realistic bounds
        humidity_range = config.get("humidity_range", [30, 80])
        humidity = max(humidity_range[0], min(humidity_range[1], humidity))
        
        self.last_values["humidity"] = humidity
        return round(humidity, 2)
    
    def generate_pressure(self, config: Dict[str, Any]) -> float:
        """
        Generate realistic pressure data for hydraulic/pneumatic systems.
        
        Args:
            config: Pressure configuration parameters
            
        Returns:
            Generated pressure value in PSI
        """
        base_pressure = config.get("base_value", 150.0)
        pressure_range = config.get("pressure_range", [0, 300])
        
        # Simulate pressure fluctuations based on system load
        current_time = time.time()
        
        # Add periodic pressure changes (system cycling)
        cycle_period = config.get("cycle_period", 300)  # 5 minutes
        cycle_amplitude = config.get("cycle_amplitude", 20.0)
        
        cycle_phase = (current_time % cycle_period) / cycle_period * 2 * math.pi
        pressure_cycle = cycle_amplitude * math.sin(cycle_phase)
        
        # Add random fluctuations
        noise = self.random_state.normal(0, 5.0)
        
        # Simulate load-based variations
        load_factor = config.get("load_factor", 1.0)
        load_variation = load_factor * self.random_state.uniform(-10, 10)
        
        pressure = base_pressure + pressure_cycle + noise + load_variation
        
        # Apply bounds
        pressure = max(pressure_range[0], min(pressure_range[1], pressure))
        
        self.last_values["pressure"] = pressure
        return round(pressure, 2)
    
    def generate_flow_rate(self, config: Dict[str, Any]) -> float:
        """
        Generate realistic flow rate data (often correlated with pressure).
        
        Args:
            config: Flow rate configuration parameters
            
        Returns:
            Generated flow rate in L/min
        """
        base_flow = config.get("base_value", 50.0)
        flow_range = config.get("flow_range", [10, 150])
        
        # Correlation with pressure
        correlation_factor = config.get("pressure_correlation", 0.5)
        if "pressure" in self.last_values:
            pressure_normalized = (self.last_values["pressure"] - 150) / 150
            flow_adjustment = correlation_factor * pressure_normalized * base_flow
        else:
            flow_adjustment = 0
            
        # Add turbulence/noise
        turbulence = self.random_state.normal(0, base_flow * 0.05)
        
        flow_rate = base_flow + flow_adjustment + turbulence
        
        # Apply bounds
        flow_rate = max(flow_range[0], min(flow_range[1], flow_rate))
        
        self.last_values["flow_rate"] = flow_rate
        return round(flow_rate, 2)
    
    def generate_motor_speed(self, config: Dict[str, Any]) -> float:
        """
        Generate realistic motor speed data (RPM).
        
        Args:
            config: Motor speed configuration parameters
            
        Returns:
            Generated motor speed in RPM
        """
        base_speed = config.get("base_value", 1800.0)
        speed_range = config.get("speed_range", [0, 3600])
        
        # Simulate load variations affecting speed
        load_variation = config.get("load_variation", 0.02)
        load_factor = 1 + self.random_state.normal(0, load_variation)
        
        # Add mechanical vibration/oscillation
        vibration_freq = config.get("vibration_frequency", 50)  # Hz
        vibration_amplitude = config.get("vibration_amplitude", 10)
        
        current_time = time.time()
        vibration = vibration_amplitude * math.sin(2 * math.pi * vibration_freq * current_time)
        
        motor_speed = (base_speed * load_factor) + vibration
        
        # Apply bounds
        motor_speed = max(speed_range[0], min(speed_range[1], motor_speed))
        
        self.last_values["motor_speed"] = motor_speed
        return round(motor_speed, 1)
    
    def generate_motor_torque(self, config: Dict[str, Any]) -> float:
        """
        Generate realistic motor torque data (correlated with speed and load).
        
        Args:
            config: Motor torque configuration parameters
            
        Returns:
            Generated motor torque in Nm
        """
        base_torque = config.get("base_value", 100.0)
        torque_range = config.get("torque_range", [0, 500])
        
        # Inverse relationship with speed (P = T * ω)
        if "motor_speed" in self.last_values:
            speed_factor = self.last_values["motor_speed"] / 1800.0  # Normalize
            # Higher speed typically means lower torque for constant power
            torque_adjustment = base_torque * (1.2 - speed_factor * 0.4)
        else:
            torque_adjustment = base_torque
            
        # Add load fluctuations
        load_noise = self.random_state.normal(0, base_torque * 0.1)
        
        torque = torque_adjustment + load_noise
        
        # Apply bounds
        torque = max(torque_range[0], min(torque_range[1], torque))
        
        self.last_values["motor_torque"] = torque
        return round(torque, 2)
    
    def generate_power_consumption(self, config: Dict[str, Any]) -> float:
        """
        Generate realistic power consumption data.
        
        Args:
            config: Power configuration parameters
            
        Returns:
            Generated power consumption in kW
        """
        base_power = config.get("base_value", 25.0)
        power_range = config.get("power_range", [0, 100])
        
        # Calculate power from speed and torque if available
        if "motor_speed" in self.last_values and "motor_torque" in self.last_values:
            # P = T * ω / 9549 (kW from Nm and RPM)
            calculated_power = (
                self.last_values["motor_torque"] * 
                self.last_values["motor_speed"] / 9549
            )
            # Use calculated power as base, but add some variation
            base_power = calculated_power
            
        # Add efficiency variations and electrical noise
        efficiency_variation = self.random_state.normal(0.95, 0.05)  # 95% ± 5%
        electrical_noise = self.random_state.normal(0, base_power * 0.02)
        
        power = base_power * efficiency_variation + electrical_noise
        
        # Apply bounds
        power = max(power_range[0], min(power_range[1], power))
        
        self.last_values["power"] = power
        return round(power, 2)
    
    def generate_fault_code(self, config: Dict[str, Any]) -> int:
        """
        Generate realistic fault codes based on fault injection rate.
        
        Args:
            config: Fault configuration parameters
            
        Returns:
            Fault code (0 = no fault)
        """
        fault_probability = config.get("fault_probability", 0.001)
        possible_faults = config.get("fault_codes", [0, 1, 2, 5, 8, 10])
        
        if self.random_state.random() < fault_probability:
            # Generate a fault (exclude 0 which means no fault)
            fault_codes = [code for code in possible_faults if code != 0]
            if fault_codes:
                fault_code = self.random_state.choice(fault_codes)
                logger.warning(
                    "Fault injected",
                    device_id=self.device_id,
                    fault_code=fault_code
                )
                return fault_code
                
        return 0  # No fault
    
    def generate_device_data(self, device_type: str) -> Dict[str, Any]:
        """
        Generate complete device data based on device type.
        
        Args:
            device_type: Type of device to simulate
            
        Returns:
            Dictionary of generated values
        """
        data = {
            "timestamp": time.time(),
            "device_id": self.device_id,
            "device_type": device_type
        }
        
        if device_type == "temperature_sensor":
            temp_config = self.pattern_config.get("temperature", {})
            humidity_config = self.pattern_config.get("humidity", {})
            
            data.update({
                "temperature": self.generate_temperature(temp_config),
                "humidity": self.generate_humidity(humidity_config),
                "sensor_status": 0,  # 0 = OK
                "sensor_healthy": True
            })
            
        elif device_type == "pressure_transmitter":
            pressure_config = self.pattern_config.get("pressure", {})
            flow_config = self.pattern_config.get("flow_rate", {})
            
            data.update({
                "pressure": self.generate_pressure(pressure_config),
                "flow_rate": self.generate_flow_rate(flow_config),
                "high_alarm": data.get("pressure", 0) > pressure_config.get("alarm_thresholds", {}).get("high_pressure", 250),
                "low_flow_alarm": data.get("flow_rate", 0) < pressure_config.get("alarm_thresholds", {}).get("low_flow", 20)
            })
            
        elif device_type == "motor_drive":
            motor_config = self.pattern_config.get("motor", {})
            
            data.update({
                "speed": self.generate_motor_speed(motor_config),
                "torque": self.generate_motor_torque(motor_config),
                "power": self.generate_power_consumption(motor_config),
                "fault_code": self.generate_fault_code(motor_config)
            })
            
        return data