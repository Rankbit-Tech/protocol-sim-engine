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

        elif device_type == "environmental_sensor":
            # IoT environmental sensor with temperature, humidity, and air quality
            temp_config = self.pattern_config.get("temperature", {})
            humidity_config = self.pattern_config.get("humidity", {})
            air_quality_config = self.pattern_config.get("air_quality", {})

            data.update({
                "temperature": self.generate_temperature(temp_config),
                "humidity": self.generate_humidity(humidity_config),
                **self.generate_air_quality(air_quality_config)
            })

        elif device_type == "energy_meter":
            # Smart energy meter
            energy_config = self.pattern_config.get("energy", {})
            data.update(self.generate_energy_meter_data(energy_config))

        elif device_type == "asset_tracker":
            # Asset tracker / BLE beacon
            tracker_config = self.pattern_config.get("tracker", {})
            data.update(self.generate_asset_tracker_data(tracker_config))

        elif device_type == "generic_sensor":
            # Generic IoT sensor - just temperature and humidity
            temp_config = self.pattern_config.get("temperature", {})
            humidity_config = self.pattern_config.get("humidity", {})

            data.update({
                "temperature": self.generate_temperature(temp_config),
                "humidity": self.generate_humidity(humidity_config)
            })

        elif device_type == "cnc_machine":
            cnc_config = self.pattern_config.get("cnc", self.pattern_config)
            data.update(self.generate_cnc_machine_data(cnc_config))

        elif device_type == "plc_controller":
            plc_config = self.pattern_config.get("plc", self.pattern_config)
            data.update(self.generate_plc_controller_data(plc_config))

        elif device_type == "industrial_robot":
            robot_config = self.pattern_config.get("robot", self.pattern_config)
            data.update(self.generate_robot_data(robot_config))

        return data

    def generate_air_quality(self, config: Dict[str, Any]) -> Dict[str, float]:
        """
        Generate air quality metrics for IoT sensors.

        Args:
            config: Air quality configuration parameters

        Returns:
            Dictionary with air quality metrics
        """
        base_aqi = config.get("base_aqi", 50)

        # Simulate daily patterns (worse during work hours)
        current_hour = time.localtime().tm_hour
        if 9 <= current_hour <= 17:
            work_factor = 1.3
        else:
            work_factor = 0.8

        aqi = base_aqi * work_factor + self.random_state.normal(0, 10)
        aqi = max(0, min(500, aqi))  # AQI bounds

        co2 = 400 + (aqi * 5) + self.random_state.normal(0, 50)
        tvoc = 50 + (aqi * 2) + self.random_state.normal(0, 20)

        # Atmospheric pressure with small variations
        base_pressure = config.get("base_pressure", 1013.25)
        pressure = base_pressure + self.random_state.normal(0, 5)

        return {
            "air_quality_index": round(aqi, 0),
            "co2_ppm": round(max(350, co2), 0),
            "tvoc_ppb": round(max(0, tvoc), 0),
            "pressure_hpa": round(pressure, 2)
        }

    def generate_energy_meter_data(self, config: Dict[str, Any]) -> Dict[str, float]:
        """
        Generate smart meter readings.

        Args:
            config: Energy meter configuration parameters

        Returns:
            Dictionary with energy meter readings
        """
        base_voltage = config.get("base_voltage", 230.0)
        voltage_range = config.get("voltage_range", [220, 240])
        base_current = config.get("base_current", 20.0)
        current_range = config.get("current_range", [0, 100])

        # Voltage with small variation
        voltage = base_voltage + self.random_state.normal(0, 2)
        voltage = max(voltage_range[0], min(voltage_range[1], voltage))

        # Current based on load (higher during work hours)
        current_hour = time.localtime().tm_hour
        if 8 <= current_hour <= 18:
            load_factor = 1.5
        else:
            load_factor = 0.5

        current = base_current * load_factor + self.random_state.normal(0, 5)
        current = max(current_range[0], min(current_range[1], current))

        power_factor_range = config.get("power_factor_range", [0.85, 0.99])
        power_factor = self.random_state.uniform(power_factor_range[0], power_factor_range[1])

        power = (voltage * current * power_factor) / 1000  # kW

        # Cumulative energy (simulated)
        if "energy_kwh" not in self.last_values:
            self.last_values["energy_kwh"] = config.get("initial_energy", 10000.0)

        # Add energy based on power and time since last update
        time_hours = 1.0 / 3600.0  # Assume 1 second update interval
        self.last_values["energy_kwh"] += power * time_hours

        # Frequency with small deviation
        frequency = 50 + self.random_state.normal(0, 0.05)

        return {
            "voltage_v": round(voltage, 1),
            "current_a": round(current, 1),
            "power_kw": round(power, 2),
            "power_factor": round(power_factor, 2),
            "frequency_hz": round(frequency, 2),
            "energy_kwh": round(self.last_values["energy_kwh"], 1),
            "phase": config.get("phase", "L1")
        }

    def generate_asset_tracker_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate asset tracker location data.

        Args:
            config: Asset tracker configuration parameters

        Returns:
            Dictionary with asset tracker data
        """
        zones = config.get("zone_ids", ["zone_a", "zone_b", "zone_c", "warehouse"])

        # Occasionally change zones (simulate asset movement)
        if "current_zone" not in self.last_values or self.random_state.random() < 0.1:
            self.last_values["current_zone"] = self.random_state.choice(zones)

        # Battery drain simulation
        if "battery" not in self.last_values:
            self.last_values["battery"] = 100.0

        drain_rate = config.get("battery_drain_rate", 0.001)
        self.last_values["battery"] -= drain_rate
        self.last_values["battery"] = max(0, self.last_values["battery"])

        # RSSI (signal strength) varies with location
        base_rssi = config.get("base_rssi", -60)
        rssi = base_rssi + self.random_state.normal(0, 10)
        rssi = max(-100, min(-30, rssi))

        # Motion detection (random with higher probability during work hours)
        current_hour = time.localtime().tm_hour
        motion_probability = 0.7 if 8 <= current_hour <= 18 else 0.3
        motion_detected = self.random_state.random() < motion_probability

        # Simulate gateway selection
        gateways = config.get("gateways", ["gateway_01", "gateway_02", "gateway_03"])
        last_gateway = self.random_state.choice(gateways)

        # Asset ID (persistent for this device)
        if "asset_id" not in self.last_values:
            asset_prefix = config.get("asset_prefix", "ASSET")
            asset_num = self.random_state.randint(1000, 9999)
            self.last_values["asset_id"] = f"{asset_prefix}-{asset_num}"

        return {
            "asset_id": self.last_values["asset_id"],
            "zone_id": self.last_values["current_zone"],
            "rssi": round(rssi, 0),
            "battery_percent": round(self.last_values["battery"], 1),
            "motion_detected": motion_detected,
            "last_seen_gateway": last_gateway
        }

    def generate_cnc_machine_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate CNC machine monitoring data with realistic state-driven behavior.

        Args:
            config: CNC machine configuration parameters

        Returns:
            Dictionary with CNC machine data
        """
        speed_range = config.get("spindle_speed_range", [0, 24000])
        feed_range = config.get("feed_rate_range", [0, 15000])

        # Initialize state machine
        if "machine_state" not in self.last_values:
            self.last_values["machine_state"] = "RUNNING"
            self.last_values["state_ticks"] = 0

        self.last_values["state_ticks"] = self.last_values.get("state_ticks", 0) + 1
        state = self.last_values["machine_state"]
        ticks = self.last_values["state_ticks"]
        roll = self.random_state.random()

        # State-aware transitions: each state has its own transition logic
        if state == "RUNNING":
            if roll < 0.005:
                self.last_values["machine_state"] = "ERROR"
                self.last_values["state_ticks"] = 0
            elif roll < 0.015:
                self.last_values["machine_state"] = "IDLE"
                self.last_values["state_ticks"] = 0
        elif state == "IDLE":
            # Idle machines should start running again fairly quickly
            if roll < 0.15:
                self.last_values["machine_state"] = "RUNNING"
                self.last_values["state_ticks"] = 0
            elif roll < 0.18:
                self.last_values["machine_state"] = "SETUP"
                self.last_values["state_ticks"] = 0
        elif state == "ERROR":
            # Auto-recover from error after a short pause (5-15 ticks)
            if ticks > 5 and roll < 0.25:
                self.last_values["machine_state"] = "IDLE"
                self.last_values["state_ticks"] = 0
        elif state == "SETUP":
            # Setup completes after a few ticks
            if ticks > 3 and roll < 0.20:
                self.last_values["machine_state"] = "RUNNING"
                self.last_values["state_ticks"] = 0
                # New program after setup
                programs = config.get("programs", ["G-Code_001", "G-Code_002", "G-Code_003"])
                self.last_values["program_name"] = self.random_state.choice(programs)

        state = self.last_values["machine_state"]

        # Spindle speed depends on state with ramp-up behavior
        base_speed = config.get("base_spindle_speed", 12000.0)
        if state == "RUNNING":
            # Ramp up from idle or vary during operation
            target_speed = base_speed + self.random_state.normal(0, base_speed * 0.03)
            last_speed = self.last_values.get("spindle_speed", base_speed * 0.5)
            # Smooth ramp toward target
            spindle_speed = last_speed + (target_speed - last_speed) * 0.3
            spindle_speed = max(speed_range[0], min(speed_range[1], spindle_speed))
        elif state == "SETUP":
            spindle_speed = self.random_state.uniform(500, 2000)
        else:
            # Ramp down
            last_speed = self.last_values.get("spindle_speed", 0)
            spindle_speed = max(0, last_speed * 0.7)
        self.last_values["spindle_speed"] = spindle_speed

        # Feed rate with similar dynamics
        base_feed = config.get("base_feed_rate", 5000.0)
        if state == "RUNNING":
            target_feed = base_feed + self.random_state.normal(0, base_feed * 0.05)
            last_feed = self.last_values.get("feed_rate", base_feed * 0.5)
            feed_rate = last_feed + (target_feed - last_feed) * 0.3
            feed_rate = max(feed_range[0], min(feed_range[1], feed_rate))
        elif state == "SETUP":
            feed_rate = self.random_state.uniform(100, 500)
        else:
            last_feed = self.last_values.get("feed_rate", 0)
            feed_rate = max(0, last_feed * 0.7)
        self.last_values["feed_rate"] = feed_rate

        # Tool wear increases over time, resets on tool change
        if "tool_wear" not in self.last_values:
            self.last_values["tool_wear"] = self.random_state.uniform(0, 30)

        if state == "RUNNING":
            wear_rate = config.get("tool_wear_rate", 0.01)
            self.last_values["tool_wear"] += wear_rate + self.random_state.normal(0, 0.003)

        # Tool change at ~90% wear triggers SETUP
        if self.last_values["tool_wear"] > 90:
            self.last_values["tool_wear"] = 0.0
            self.last_values["machine_state"] = "SETUP"
            self.last_values["state_ticks"] = 0

        tool_wear = max(0, min(100, self.last_values["tool_wear"]))

        # Part count increments periodically during RUNNING
        if "part_count" not in self.last_values:
            self.last_values["part_count"] = 0

        if state == "RUNNING" and self.random_state.random() < 0.08:
            self.last_values["part_count"] += 1

        # Axis positions trace a realistic toolpath
        current_time = time.time()
        workspace = config.get("workspace_mm", [500, 400, 300])
        if state == "RUNNING":
            axis_x = workspace[0] / 2 + (workspace[0] / 3) * math.sin(current_time * 0.5)
            axis_y = workspace[1] / 2 + (workspace[1] / 3) * math.cos(current_time * 0.4)
            axis_z = workspace[2] / 2 + (workspace[2] / 4) * math.sin(current_time * 0.7)
        else:
            # Park position with slight drift
            axis_x = workspace[0] / 2 + self.random_state.normal(0, 0.5)
            axis_y = workspace[1] / 2 + self.random_state.normal(0, 0.5)
            axis_z = workspace[2] * 0.9 + self.random_state.normal(0, 0.5)

        programs = config.get("programs", ["G-Code_001", "G-Code_002", "G-Code_003"])
        if "program_name" not in self.last_values:
            self.last_values["program_name"] = self.random_state.choice(programs)

        return {
            "spindle_speed_rpm": round(spindle_speed, 1),
            "feed_rate_mm_min": round(feed_rate, 1),
            "tool_wear_percent": round(tool_wear, 1),
            "part_count": int(self.last_values["part_count"]),
            "axis_position_x": round(axis_x, 2),
            "axis_position_y": round(axis_y, 2),
            "axis_position_z": round(axis_z, 2),
            "program_name": self.last_values["program_name"],
            "machine_state": state
        }

    def generate_plc_controller_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate PLC process controller data with PID simulation.

        Args:
            config: PLC controller configuration parameters

        Returns:
            Dictionary with PLC controller data
        """
        pv_range = config.get("process_value_range", [0, 100])
        setpoint = config.get("setpoint", 50.0)

        # PID simulation
        kp = config.get("kp", 1.0)
        ki = config.get("ki", 0.1)
        kd = config.get("kd", 0.05)

        # Mode transitions with state-aware logic
        if "plc_mode" not in self.last_values:
            self.last_values["plc_mode"] = "AUTO"
            self.last_values["integral_term"] = 0.0
            self.last_values["last_error"] = 0.0
            self.last_values["process_value"] = setpoint + self.random_state.normal(0, 5)
            self.last_values["setpoint_target"] = setpoint

        roll = self.random_state.random()
        mode = self.last_values["plc_mode"]

        if mode == "AUTO":
            if roll < 0.005:
                self.last_values["plc_mode"] = "MANUAL"
            elif roll < 0.008:
                self.last_values["plc_mode"] = "CASCADE"
        elif mode == "MANUAL":
            if roll < 0.08:
                self.last_values["plc_mode"] = "AUTO"
        elif mode == "CASCADE":
            if roll < 0.03:
                self.last_values["plc_mode"] = "AUTO"

        mode = self.last_values["plc_mode"]

        # Occasional setpoint changes (simulates operator adjustments)
        if self.random_state.random() < 0.01:
            sp_variation = self.random_state.uniform(-5, 5)
            self.last_values["setpoint_target"] = max(
                pv_range[0] + 10,
                min(pv_range[1] - 10, setpoint + sp_variation)
            )
        active_setpoint = self.last_values["setpoint_target"]

        # Process value with realistic disturbances
        disturbance = self.random_state.normal(0, 2.0)
        pv = self.last_values["process_value"] + disturbance

        if mode == "AUTO" or mode == "CASCADE":
            error = active_setpoint - pv
            self.last_values["integral_term"] += error * ki
            self.last_values["integral_term"] = max(-50, min(50, self.last_values["integral_term"]))
            derivative = error - self.last_values["last_error"]
            control_output = kp * error + self.last_values["integral_term"] + kd * derivative
            control_output = max(0, min(100, control_output))

            pv += control_output * 0.1 - 5.0
            self.last_values["last_error"] = error
        else:
            control_output = config.get("manual_output", 50.0)
            # In manual mode, process drifts more
            pv += self.random_state.normal(0, 1.0)

        pv = max(pv_range[0], min(pv_range[1], pv))
        self.last_values["process_value"] = pv

        # Alarm states
        high_alarm_threshold = config.get("high_alarm", pv_range[1] * 0.9)
        low_alarm_threshold = config.get("low_alarm", pv_range[0] + pv_range[1] * 0.1)

        return {
            "process_value": round(pv, 2),
            "setpoint": round(active_setpoint, 2),
            "control_output": round(control_output, 2),
            "mode": mode,
            "high_alarm": pv > high_alarm_threshold,
            "low_alarm": pv < low_alarm_threshold,
            "integral_term": round(self.last_values["integral_term"], 3),
            "derivative_term": round(self.last_values.get("last_error", 0) * kd, 3),
            "error": round(active_setpoint - pv, 2)
        }

    def generate_robot_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate industrial robot monitoring data with realistic motion.

        Args:
            config: Robot configuration parameters

        Returns:
            Dictionary with robot data
        """
        joint_count = config.get("joint_count", 6)
        max_speed = config.get("max_speed_percent", 100)

        # Initialize state machine
        if "robot_state" not in self.last_values:
            self.last_values["robot_state"] = "RUNNING"
            self.last_values["cycle_count"] = 0
            self.last_values["robot_state_ticks"] = 0
            self.last_values["joint_targets"] = [
                self.random_state.uniform(-180, 180) for _ in range(joint_count)
            ]

        self.last_values["robot_state_ticks"] = self.last_values.get("robot_state_ticks", 0) + 1
        state = self.last_values["robot_state"]
        ticks = self.last_values["robot_state_ticks"]
        roll = self.random_state.random()

        # State-aware transitions
        if state == "RUNNING":
            if roll < 0.008:
                self.last_values["robot_state"] = "PAUSED"
                self.last_values["robot_state_ticks"] = 0
            elif roll < 0.003:
                self.last_values["robot_state"] = "STOPPED"
                self.last_values["robot_state_ticks"] = 0
        elif state == "PAUSED":
            if ticks > 3 and roll < 0.20:
                self.last_values["robot_state"] = "RUNNING"
                self.last_values["robot_state_ticks"] = 0
        elif state == "STOPPED":
            if ticks > 5 and roll < 0.12:
                self.last_values["robot_state"] = "RUNNING"
                self.last_values["robot_state_ticks"] = 0

        state = self.last_values["robot_state"]

        # Joint angles move toward targets
        if "joint_angles" not in self.last_values:
            self.last_values["joint_angles"] = [0.0] * joint_count

        if state == "RUNNING":
            for i in range(joint_count):
                target = self.last_values["joint_targets"][i]
                current = self.last_values["joint_angles"][i]
                diff = target - current
                step = min(abs(diff), 3.0) * (1 if diff > 0 else -1)
                self.last_values["joint_angles"][i] = current + step + self.random_state.normal(0, 0.15)

            # Check if near target, pick new target
            at_target = all(
                abs(self.last_values["joint_angles"][i] - self.last_values["joint_targets"][i]) < 5.0
                for i in range(joint_count)
            )
            if at_target:
                self.last_values["joint_targets"] = [
                    self.random_state.uniform(-180, 180) for _ in range(joint_count)
                ]
                self.last_values["cycle_count"] += 1

        joint_angles = [round(a, 2) for a in self.last_values["joint_angles"]]

        # TCP position with state-dependent motion
        current_time = time.time()
        if state == "RUNNING":
            tcp_x = 500 + 300 * math.sin(current_time * 0.6) + self.random_state.normal(0, 2)
            tcp_y = 200 + 200 * math.cos(current_time * 0.5) + self.random_state.normal(0, 2)
            tcp_z = 400 + 150 * math.sin(current_time * 0.7) + self.random_state.normal(0, 2)
        else:
            tcp_x = 500 + self.random_state.normal(0, 0.3)
            tcp_y = 200 + self.random_state.normal(0, 0.3)
            tcp_z = 600 + self.random_state.normal(0, 0.3)

        # TCP orientation
        tcp_rx = 180 + 10 * math.sin(current_time * 0.3)
        tcp_ry = 5 * math.cos(current_time * 0.4)
        tcp_rz = 90 + 5 * math.sin(current_time * 0.5)

        # Cycle time with variation
        base_cycle_time = config.get("base_cycle_time", 15.0)
        cycle_time = base_cycle_time + self.random_state.normal(0, base_cycle_time * 0.08)
        cycle_time = max(5.0, cycle_time)

        # Payload changes between cycles
        payload_range = config.get("payload_range", [0, 20])
        if "payload" not in self.last_values:
            self.last_values["payload"] = self.random_state.uniform(payload_range[0], payload_range[1])
        if self.random_state.random() < 0.05:
            self.last_values["payload"] = self.random_state.uniform(payload_range[0], payload_range[1])

        # Speed percent with variation during RUNNING
        if state == "RUNNING":
            base = max_speed * 0.85
            speed = base + self.random_state.uniform(0, max_speed * 0.15)
        elif state == "PAUSED":
            speed = 0.0
        else:
            speed = 0.0

        return {
            "joint_angles": joint_angles,
            "tcp_position_x": round(tcp_x, 2),
            "tcp_position_y": round(tcp_y, 2),
            "tcp_position_z": round(tcp_z, 2),
            "tcp_orientation_rx": round(tcp_rx, 2),
            "tcp_orientation_ry": round(tcp_ry, 2),
            "tcp_orientation_rz": round(tcp_rz, 2),
            "program_state": state,
            "cycle_time_s": round(cycle_time, 2),
            "cycle_count": int(self.last_values["cycle_count"]),
            "payload_kg": round(self.last_values["payload"], 1),
            "speed_percent": round(speed, 1)
        }