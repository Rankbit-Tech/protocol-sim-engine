import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Device } from '@/types';
import { cn } from '@/lib/utils';
import { Circle } from 'lucide-react';

interface DeviceListProps {
  devices: Device[];
  title?: string;
  maxHeight?: string;
}

function formatDeviceType(type: string): string {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatLastUpdate(timestamp: number | null | undefined): string {
  if (!timestamp) return 'Never';
  const seconds = Math.floor((Date.now() / 1000) - timestamp);
  if (seconds < 5) return 'Just now';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function formatInterval(interval: number | undefined): string {
  if (!interval) return '';
  if (interval < 1) return `${interval * 1000}ms`;
  return `${interval}s`;
}

export function DeviceList({ devices, title = 'Devices', maxHeight = '400px' }: DeviceListProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">{title}</CardTitle>
          <span className="text-sm text-muted-foreground">{devices.length} total</span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <ScrollArea style={{ height: maxHeight }}>
          <div className="space-y-2 pr-4">
            {devices.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No devices</p>
            ) : (
              devices.map((device) => {
                const lastUpdate = device.last_update || device.last_publish;
                const interval = device.update_interval || device.publish_interval;
                const isActive = device.status === 'running' && lastUpdate &&
                  (Date.now() / 1000 - lastUpdate) < (interval ? interval * 3 : 30);

                return (
                  <div
                    key={device.device_id}
                    className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Circle
                          className={cn(
                            'h-2 w-2 flex-shrink-0',
                            isActive ? 'fill-green-500 text-green-500' : 'fill-muted text-muted'
                          )}
                        />
                        <span className="text-sm font-medium truncate">{device.device_id}</span>
                      </div>
                      <Badge variant="outline" className="flex-shrink-0">
                        {device.protocol === 'modbus_tcp' ? 'Modbus' : device.protocol?.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      <div>Type: {formatDeviceType(device.device_type)}</div>
                      <div>Last: {formatLastUpdate(lastUpdate)}</div>
                      {device.port && <div>Port: {device.port}</div>}
                      {interval && <div>Interval: {formatInterval(interval)}</div>}
                      {device.publish_count !== undefined && (
                        <div>Published: {device.publish_count}</div>
                      )}
                      {device.error_count !== undefined && device.error_count > 0 && (
                        <div className="text-destructive">Errors: {device.error_count}</div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
