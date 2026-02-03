import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatusCard } from '@/components/StatusCard';
import { DeviceList } from '@/components/DeviceList';
import { usePolling } from '@/hooks/usePolling';
import {
  fetchStatus,
  fetchDevices,
  fetchProtocols,
  exportDevices,
  downloadBlob,
} from '@/lib/api';
import type { SimulationStatus, Device } from '@/types';
import {
  RefreshCw,
  Download,
  Cpu,
  Radio,
  Clock,
  Activity,
  Circle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProtocolInfo {
  name: string;
  device_count: number;
  status: string;
}

export function Dashboard() {
  const [startTime] = useState(Date.now());
  const [uptime, setUptime] = useState('0:00:00');
  const [protocols, setProtocols] = useState<ProtocolInfo[]>([]);

  const { data: status, refetch: refetchStatus } = usePolling<SimulationStatus>({
    fetchFn: fetchStatus,
    interval: 5000,
  });

  const { data: devicesData, refetch: refetchDevices } = usePolling<{ total_count: number; devices: Device[] }>({
    fetchFn: fetchDevices,
    interval: 5000,
  });

  // Fetch protocols and transform the response
  const fetchProtocolsData = useCallback(async () => {
    try {
      const data = await fetchProtocols();
      const protocolList: ProtocolInfo[] = Object.entries(data.active_protocols || {}).map(
        ([name, info]) => ({
          name,
          device_count: info.device_count,
          status: info.status,
        })
      );
      setProtocols(protocolList);
    } catch (error) {
      console.error('Failed to fetch protocols:', error);
    }
  }, []);

  useEffect(() => {
    fetchProtocolsData();
    const interval = setInterval(fetchProtocolsData, 5000);
    return () => clearInterval(interval);
  }, [fetchProtocolsData]);

  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const hours = Math.floor(elapsed / 3600);
      const minutes = Math.floor((elapsed % 3600) / 60);
      const seconds = elapsed % 60;
      setUptime(`${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    }, 1000);
    return () => clearInterval(timer);
  }, [startTime]);

  const handleRefresh = useCallback(async () => {
    await Promise.all([refetchStatus(), refetchDevices(), fetchProtocolsData()]);
  }, [refetchStatus, refetchDevices, fetchProtocolsData]);

  const handleExport = async () => {
    try {
      const blob = await exportDevices('json');
      downloadBlob(blob, `devices-export-${Date.now()}.json`);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const devices = devicesData?.devices || [];
  const runningDevices = devices.filter(d => d.status === 'running').length;
  const healthPercentage = devices.length > 0
    ? Math.round((runningDevices / devices.length) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="h-6 w-6" />
              <div>
                <h1 className="text-lg font-semibold">Protocol Simulation Engine</h1>
                <p className="text-sm text-muted-foreground">Industrial Device Simulator</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" onClick={handleRefresh}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Status Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatusCard
            title="Total Devices"
            value={status?.device_count || 0}
            icon={Cpu}
          />
          <StatusCard
            title="Active Protocols"
            value={protocols.length}
            icon={Radio}
          />
          <StatusCard
            title="Health"
            value={`${healthPercentage}%`}
            icon={Activity}
          />
          <StatusCard
            title="Uptime"
            value={uptime}
            icon={Clock}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Protocols */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-medium">Protocols</CardTitle>
            </CardHeader>
            <CardContent>
              {protocols.length === 0 ? (
                <p className="text-sm text-muted-foreground">No protocols active</p>
              ) : (
                <div className="space-y-3">
                  {protocols.map((protocol) => (
                    <div
                      key={protocol.name}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div className="flex items-center gap-3">
                        <Circle
                          className={cn(
                            'h-2 w-2',
                            protocol.status === 'active'
                              ? 'fill-green-500 text-green-500'
                              : 'fill-muted text-muted'
                          )}
                        />
                        <span className="text-sm font-medium">
                          {protocol.name === 'modbus_tcp' ? 'Modbus TCP' : protocol.name.toUpperCase()}
                        </span>
                      </div>
                      <Badge variant="secondary">{protocol.device_count}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* System Status */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-medium">System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Simulation</span>
                  <Badge variant={status?.status === 'running' ? 'default' : 'secondary'}>
                    {status?.status || 'Unknown'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Running Devices</span>
                  <span className="text-sm font-medium">{runningDevices} / {devices.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Errors</span>
                  <span className="text-sm font-medium">
                    {devices.reduce((sum, d) => sum + (d.error_count || 0), 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Protocols</span>
                  <span className="text-sm font-medium">
                    {status?.protocols?.join(', ') || 'None'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Device List */}
          <DeviceList devices={devices} title="Devices" maxHeight="280px" />
        </div>
      </main>
    </div>
  );
}
