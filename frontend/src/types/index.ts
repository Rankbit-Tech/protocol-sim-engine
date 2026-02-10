export interface Device {
  device_id: string;
  device_type: string;
  template: string;
  status: string;
  running: boolean;
  uptime_seconds: number;
  error_count: number;
  protocol?: string;
  // Modbus specific
  port?: number;
  last_update?: number;
  update_interval?: number;
  // MQTT specific
  broker?: string;
  base_topic?: string;
  qos?: number;
  publish_count?: number;
  last_publish?: number | null;
  publish_interval?: number;
  // OPC-UA specific
  endpoint_url?: string;
  security_mode?: string;
  node_count?: number;
}

export interface DeviceData {
  device_id: string;
  device_type: string;
  timestamp: number;
  registers?: {
    temperature_raw?: number;
    temperature_celsius?: number;
    humidity_raw?: number;
    humidity_percent?: number;
    status_code?: number;
    sensor_healthy?: boolean;
    pressure_raw?: number;
    pressure_psi?: number;
    flow_rate_raw?: number;
    flow_rate_lpm?: number;
    high_pressure_alarm?: boolean;
    low_flow_alarm?: boolean;
    speed_rpm?: number;
    torque_raw?: number;
    torque_nm?: number;
    power_raw?: number;
    power_kw?: number;
    fault_code?: number;
  };
  data?: {
    timestamp?: number;
    device_id?: string;
    device_type?: string;
    temperature?: number;
    humidity?: number;
    air_quality_index?: number;
    co2_ppm?: number;
    tvoc_ppb?: number;
    pressure_hpa?: number;
    voltage_v?: number;
    current_a?: number;
    power_kw?: number;
    power_factor?: number;
    frequency_hz?: number;
    energy_kwh?: number;
    phase?: string;
    zone_id?: string;
    battery_level?: number;
    battery_percent?: number;
    rssi?: number;
    last_seen?: number;
    asset_id?: string;
    motion_detected?: boolean;
    last_seen_gateway?: string;
  };
  raw_data?: {
    holding_registers?: number[];
    discrete_inputs?: boolean[];
  };
  nodes?: {
    // CNC Machine
    spindle_speed_rpm?: number;
    feed_rate_mm_min?: number;
    tool_wear_percent?: number;
    part_count?: number;
    axis_position_x?: number;
    axis_position_y?: number;
    axis_position_z?: number;
    program_name?: string;
    machine_state?: string;
    // PLC Controller
    process_value?: number;
    setpoint?: number;
    control_output?: number;
    mode?: string;
    high_alarm?: boolean;
    low_alarm?: boolean;
    integral_term?: number;
    derivative_term?: number;
    error?: number;
    // Robot
    joint_angles?: number[];
    tcp_position_x?: number;
    tcp_position_y?: number;
    tcp_position_z?: number;
    program_state?: string;
    cycle_time_s?: number;
    cycle_count?: number;
    payload_kg?: number;
    speed_percent?: number;
    // Common
    device_health?: string;
    error_code?: number;
  };
}

export interface SimulationStatus {
  status: string;
  device_count: number;
  protocols: string[];
  health?: HealthInfo;
}

export interface HealthInfo {
  status: string;
  devices: Record<string, Record<string, Device>>;
  summary: {
    total_devices: number;
    healthy_devices: number;
    health_percentage: number;
  };
  port_utilization: Record<string, {
    total: number;
    used: number;
    available: number;
    utilization_percent: number;
  }>;
}

export interface Protocol {
  name: string;
  device_count: number;
  status: string;
}

export interface ProtocolsResponse {
  protocols: Protocol[];
}

export interface DevicesResponse {
  total_count: number;
  devices: Device[];
}

export interface MQTTBrokerStatus {
  broker_host: string;
  broker_port: number;
  embedded: boolean;
  status: string;
  gateway_client_id: string;
}

export interface LogEntry {
  id: string;
  timestamp: number;
  device_id: string;
  device_type: string;
  data: DeviceData;
}
