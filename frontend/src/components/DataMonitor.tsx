import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Checkbox } from '@/components/ui/checkbox';
import { StatusCard } from '@/components/StatusCard';
import { fetchDevices, fetchDeviceData, downloadText } from '@/lib/api';
import type { Device, DeviceData, LogEntry } from '@/types';
import { Pause, Play, RefreshCw, Download, Cpu, Database, Clock, Activity, Circle, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const REFRESH_OPTIONS = [
  { value: '1000', label: '1s' },
  { value: '2000', label: '2s' },
  { value: '5000', label: '5s' },
  { value: '10000', label: '10s' },
];

function formatDeviceData(data: DeviceData): string {
  if (data.registers) {
    const r = data.registers;
    if (r.temperature_celsius !== undefined) {
      return `${r.temperature_celsius}°C · ${r.humidity_percent}% humidity · Status: ${r.status_code === 0 ? 'OK' : r.status_code}`;
    }
    if (r.pressure_psi !== undefined) {
      const alarms = [];
      if (r.high_pressure_alarm) alarms.push('HIGH');
      if (r.low_flow_alarm) alarms.push('LOW FLOW');
      return `${r.pressure_psi} PSI · ${r.flow_rate_lpm} L/min${alarms.length ? ` · Alarm: ${alarms.join(', ')}` : ''}`;
    }
    if (r.speed_rpm !== undefined) {
      return `${r.speed_rpm} RPM · ${r.torque_nm} Nm · ${r.power_kw} kW${r.fault_code ? ` · Fault: ${r.fault_code}` : ''}`;
    }
  }
  if (data.data) {
    const d = data.data;
    if (d.temperature !== undefined && d.co2_ppm !== undefined) {
      return `${d.temperature}°C · ${d.humidity}% · AQI: ${d.air_quality_index} · CO2: ${d.co2_ppm} ppm`;
    }
    if (d.voltage_v !== undefined) {
      return `${d.voltage_v}V · ${d.current_a}A · ${d.power_kw} kW · PF: ${d.power_factor}`;
    }
    if (d.zone_id !== undefined) {
      const battery = d.battery_percent ?? d.battery_level ?? 'N/A';
      return `Zone: ${d.zone_id} · Battery: ${battery}% · RSSI: ${d.rssi} dBm`;
    }
  }
  if (data.nodes) {
    const n = data.nodes;
    if (n.spindle_speed_rpm !== undefined) {
      return `${n.spindle_speed_rpm} RPM · Feed: ${n.feed_rate_mm_min} mm/min · Tool: ${n.tool_wear_percent}% · Parts: ${n.part_count} · ${n.machine_state}`;
    }
    if (n.process_value !== undefined) {
      const alarms = [];
      if (n.high_alarm) alarms.push('HIGH');
      if (n.low_alarm) alarms.push('LOW');
      return `PV: ${n.process_value} · SP: ${n.setpoint} · Out: ${n.control_output}% · Mode: ${n.mode}${alarms.length ? ` · Alarm: ${alarms.join(', ')}` : ''}`;
    }
    if (n.program_state !== undefined) {
      return `${n.program_state} · Cycle: ${n.cycle_time_s}s · Payload: ${n.payload_kg}kg · Speed: ${n.speed_percent}%`;
    }
  }
  return JSON.stringify(data.nodes || data.data || data.registers || {});
}

function formatDeviceType(type: string): string {
  return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

export function DataMonitor() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState('5000');
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [dataPoints, setDataPoints] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    fetchDevices().then((data) => {
      setDevices(data.devices);
      // Select all devices by default
      setSelectedDevices(data.devices.map((d) => d.device_id));
    });
  }, []);

  const filteredDevices = useMemo(() => {
    if (selectedDevices.length === 0) return devices;
    return devices.filter((device) => selectedDevices.includes(device.device_id));
  }, [devices, selectedDevices]);

  const toggleDevice = (deviceId: string) => {
    setSelectedDevices((prev) =>
      prev.includes(deviceId)
        ? prev.filter((id) => id !== deviceId)
        : [...prev, deviceId]
    );
  };

  const selectAll = () => setSelectedDevices(devices.map((d) => d.device_id));
  const selectNone = () => setSelectedDevices([]);

  const fetchAllData = useCallback(async () => {
    if (isPaused || filteredDevices.length === 0) return;

    const promises = filteredDevices.map(async (device) => {
      try {
        const data = await fetchDeviceData(device.device_id);
        return {
          id: `${device.device_id}-${Date.now()}-${Math.random()}`,
          timestamp: Date.now(),
          device_id: device.device_id,
          device_type: device.device_type,
          data,
        } as LogEntry;
      } catch {
        return null;
      }
    });

    const results = await Promise.all(promises);
    const validResults = results.filter((r): r is LogEntry => r !== null);

    if (validResults.length > 0) {
      setLogs((prev) => [...validResults, ...prev].slice(0, 50));
      setDataPoints((prev) => prev + validResults.length);
      setLastUpdate(new Date());
    }
  }, [isPaused, filteredDevices]);

  useEffect(() => {
    if (!isPaused) {
      fetchAllData();
      intervalRef.current = window.setInterval(fetchAllData, parseInt(refreshInterval));
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isPaused, refreshInterval, fetchAllData]);

  const handleExportLogs = () => {
    const logText = logs
      .map((log) => {
        const time = new Date(log.timestamp).toISOString();
        const data = formatDeviceData(log.data);
        return `[${time}] ${log.device_id}: ${data}`;
      })
      .join('\n');
    downloadText(logText, `data-logs-${Date.now()}.txt`);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="h-6 w-6" />
              <div>
                <h1 className="text-lg font-semibold">Data Monitor</h1>
                <p className="text-sm text-muted-foreground">Real-time device telemetry</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Circle
                className={cn(
                  'h-2 w-2',
                  isPaused ? 'fill-yellow-500 text-yellow-500' : 'fill-green-500 text-green-500'
                )}
              />
              <span className="text-sm text-muted-foreground">
                {isPaused ? 'Paused' : 'Live'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Controls */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Refresh:</span>
                <Select value={refreshInterval} onValueChange={setRefreshInterval}>
                  <SelectTrigger className="w-20">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {REFRESH_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Devices:</span>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" size="sm" className="w-48 justify-between">
                      <span className="truncate">
                        {selectedDevices.length === 0
                          ? 'None selected'
                          : selectedDevices.length === devices.length
                          ? 'All devices'
                          : `${selectedDevices.length} selected`}
                      </span>
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-72 p-0" align="start">
                    <div className="flex items-center gap-2 p-2 border-b">
                      <Button variant="ghost" size="sm" onClick={selectAll}>
                        All
                      </Button>
                      <Button variant="ghost" size="sm" onClick={selectNone}>
                        None
                      </Button>
                    </div>
                    <ScrollArea className="h-64">
                      <div className="p-2 space-y-1">
                        {devices.map((device) => (
                          <label
                            key={device.device_id}
                            className="flex items-center gap-2 p-2 rounded hover:bg-accent cursor-pointer"
                          >
                            <Checkbox
                              checked={selectedDevices.includes(device.device_id)}
                              onCheckedChange={() => toggleDevice(device.device_id)}
                            />
                            <span className="text-sm truncate">{device.device_id}</span>
                          </label>
                        ))}
                      </div>
                    </ScrollArea>
                  </PopoverContent>
                </Popover>
              </div>

              <div className="flex items-center gap-2 ml-auto">
                <Button
                  variant={isPaused ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setIsPaused(!isPaused)}
                >
                  {isPaused ? <Play className="h-4 w-4 mr-1" /> : <Pause className="h-4 w-4 mr-1" />}
                  {isPaused ? 'Resume' : 'Pause'}
                </Button>
                <Button variant="outline" size="sm" onClick={fetchAllData}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={handleExportLogs}>
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatusCard
            title="Devices"
            value={filteredDevices.length}
            icon={Cpu}
          />
          <StatusCard
            title="Data Points"
            value={dataPoints}
            icon={Database}
          />
          <StatusCard
            title="Last Update"
            value={lastUpdate ? lastUpdate.toLocaleTimeString() : '—'}
            icon={Clock}
          />
        </div>

        {/* Log Stream */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-medium">Live Stream</CardTitle>
              <span className="text-sm text-muted-foreground">{logs.length} entries</span>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              {logs.length === 0 ? (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  Waiting for data...
                </div>
              ) : (
                <div className="space-y-2 pr-4">
                  {logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 rounded-lg border bg-muted/30"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{log.device_id}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDeviceType(log.device_type)}
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground font-mono">
                        {formatDeviceData(log.data)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
