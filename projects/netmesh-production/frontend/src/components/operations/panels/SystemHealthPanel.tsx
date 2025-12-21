import React, { useState, useEffect } from 'react';
import { AdvancedCharts } from '../../charts/AdvancedCharts';

interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
  change: number;
}

interface ServiceStatus {
  name: string;
  status: 'online' | 'offline' | 'degraded';
  uptime: number;
  responseTime: number;
  lastChecked: Date;
}

export function SystemHealthPanel() {
  const [metrics, setMetrics] = useState<SystemMetric[]>([]);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Simulate real-time data updates
  useEffect(() => {
    const generateMockData = () => {
      const mockMetrics: SystemMetric[] = [
        {
          name: 'CPU Usage',
          value: Math.random() * 100,
          unit: '%',
          status: Math.random() > 0.8 ? 'warning' : 'healthy',
          trend: Math.random() > 0.5 ? 'up' : 'down',
          change: (Math.random() - 0.5) * 20
        },
        {
          name: 'Memory Usage',
          value: Math.random() * 100,
          unit: '%',
          status: Math.random() > 0.9 ? 'critical' : Math.random() > 0.7 ? 'warning' : 'healthy',
          trend: Math.random() > 0.5 ? 'up' : 'down',
          change: (Math.random() - 0.5) * 15
        },
        {
          name: 'Disk Usage',
          value: Math.random() * 100,
          unit: '%',
          status: Math.random() > 0.95 ? 'critical' : 'healthy',
          trend: 'stable',
          change: (Math.random() - 0.5) * 5
        },
        {
          name: 'Network I/O',
          value: Math.random() * 1000,
          unit: 'MB/s',
          status: 'healthy',
          trend: Math.random() > 0.5 ? 'up' : 'down',
          change: (Math.random() - 0.5) * 200
        },
        {
          name: 'Active Connections',
          value: Math.floor(Math.random() * 1000) + 100,
          unit: 'connections',
          status: 'healthy',
          trend: 'up',
          change: Math.floor(Math.random() * 50)
        },
        {
          name: 'Error Rate',
          value: Math.random() * 5,
          unit: '%',
          status: Math.random() > 0.8 ? 'warning' : 'healthy',
          trend: Math.random() > 0.5 ? 'up' : 'down',
          change: (Math.random() - 0.5) * 2
        }
      ];

      const mockServices: ServiceStatus[] = [
        {
          name: 'API Gateway',
          status: 'online',
          uptime: 99.9,
          responseTime: Math.random() * 200 + 50,
          lastChecked: new Date()
        },
        {
          name: 'Database',
          status: 'online',
          uptime: 99.8,
          responseTime: Math.random() * 100 + 20,
          lastChecked: new Date()
        },
        {
          name: 'MCP Server',
          status: Math.random() > 0.95 ? 'degraded' : 'online',
          uptime: 99.5,
          responseTime: Math.random() * 300 + 100,
          lastChecked: new Date()
        },
        {
          name: 'Video Processing',
          status: 'online',
          uptime: 98.7,
          responseTime: Math.random() * 500 + 200,
          lastChecked: new Date()
        },
        {
          name: 'File Storage',
          status: 'online',
          uptime: 99.9,
          responseTime: Math.random() * 150 + 30,
          lastChecked: new Date()
        },
        {
          name: 'Cache Layer',
          status: Math.random() > 0.9 ? 'offline' : 'online',
          uptime: 97.3,
          responseTime: Math.random() * 50 + 10,
          lastChecked: new Date()
        }
      ];

      setMetrics(mockMetrics);
      setServices(mockServices);
      setIsLoading(false);
    };

    generateMockData();

    // Update every 5 seconds
    const interval = setInterval(generateMockData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'online':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900';
      case 'warning':
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900';
      case 'critical':
      case 'offline':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '↗️';
      case 'down':
        return '↘️';
      default:
        return '→';
    }
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* System Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {metrics.map((metric, index) => (
          <div key={index} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">{metric.name}</h3>
                <div className="flex items-baseline mt-1">
                  <span className="text-2xl font-semibold text-gray-900 dark:text-white">
                    {typeof metric.value === 'number' && metric.value < 10
                      ? metric.value.toFixed(1)
                      : Math.round(metric.value)}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">{metric.unit}</span>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(metric.status)}`}>
                  {metric.status}
                </span>
                <span className="text-sm">{getTrendIcon(metric.trend)}</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>{metric.change > 0 ? '+' : ''}{metric.change.toFixed(1)} from last hour</span>
              <span>Live</span>
            </div>
          </div>
        ))}
      </div>

      {/* Service Status */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Service Status</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">Real-time status of all platform services</p>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {services.map((service, index) => (
            <div key={index} className="px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`w-3 h-3 rounded-full ${
                    service.status === 'online' ? 'bg-green-500' :
                    service.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                  }`}></div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">{service.name}</h4>
                    <div className="flex items-center space-x-4 mt-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {service.uptime}% uptime
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {service.responseTime.toFixed(0)}ms response
                      </span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(service.status)}`}>
                    {service.status}
                  </span>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {service.lastChecked.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Charts */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Performance Trends</h3>
        <AdvancedCharts
          data={metrics.map(m => ({
            name: m.name,
            value: m.value,
            timestamp: new Date().toISOString()
          }))}
          height={300}
        />
      </div>
    </div>
  );
}
