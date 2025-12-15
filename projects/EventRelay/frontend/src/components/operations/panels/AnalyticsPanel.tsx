import React, { useState, useEffect } from 'react';
import { AdvancedCharts } from '../../charts/AdvancedCharts';

interface AnalyticsMetric {
  name: string;
  value: number;
  change: number;
  trend: 'up' | 'down' | 'stable';
  period: string;
}

interface UsageStats {
  totalVideos: number;
  totalProcessingTime: number;
  averageProcessingTime: number;
  successRate: number;
  costPerVideo: number;
  monthlyActiveUsers: number;
}

export function AnalyticsPanel() {
  const [metrics, setMetrics] = useState<AnalyticsMetric[]>([]);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | '90d'>('7d');

  useEffect(() => {
    const generateMockData = () => {
      const mockMetrics: AnalyticsMetric[] = [
        {
          name: 'Videos Processed',
          value: Math.floor(Math.random() * 1000) + 500,
          change: (Math.random() - 0.5) * 200,
          trend: Math.random() > 0.5 ? 'up' : 'down',
          period: timeRange
        },
        {
          name: 'API Requests',
          value: Math.floor(Math.random() * 5000) + 2000,
          change: (Math.random() - 0.5) * 1000,
          trend: Math.random() > 0.5 ? 'up' : 'down',
          period: timeRange
        },
        {
          name: 'Processing Time',
          value: Math.floor(Math.random() * 300) + 120,
          change: (Math.random() - 0.5) * 60,
          trend: Math.random() > 0.6 ? 'up' : 'down',
          period: timeRange
        },
        {
          name: 'Error Rate',
          value: Math.random() * 5,
          change: (Math.random() - 0.5) * 2,
          trend: Math.random() > 0.7 ? 'up' : 'down',
          period: timeRange
        },
        {
          name: 'Cost (USD)',
          value: Math.floor(Math.random() * 500) + 100,
          change: (Math.random() - 0.5) * 100,
          trend: Math.random() > 0.5 ? 'up' : 'down',
          period: timeRange
        },
        {
          name: 'Active Users',
          value: Math.floor(Math.random() * 1000) + 200,
          change: (Math.random() - 0.5) * 200,
          trend: 'up',
          period: timeRange
        }
      ];

      const mockUsageStats: UsageStats = {
        totalVideos: Math.floor(Math.random() * 10000) + 5000,
        totalProcessingTime: Math.floor(Math.random() * 50000) + 20000,
        averageProcessingTime: Math.floor(Math.random() * 300) + 120,
        successRate: 95 + Math.random() * 4,
        costPerVideo: Math.random() * 0.5 + 0.1,
        monthlyActiveUsers: Math.floor(Math.random() * 5000) + 1000
      };

      setMetrics(mockMetrics);
      setUsageStats(mockUsageStats);
      setIsLoading(false);
    };

    generateMockData();

    // Update every 10 seconds
    const interval = setInterval(generateMockData, 10000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      default:
        return '➡️';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Analytics Dashboard</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">Usage statistics and performance metrics</p>
          </div>
          <div className="flex items-center space-x-4">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
            </select>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
              Export Report
            </button>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {metrics.map((metric, index) => (
          <div key={index} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">{metric.name}</h4>
              <span className="text-lg">{getTrendIcon(metric.trend)}</span>
            </div>
            <div className="flex items-baseline">
              <span className="text-3xl font-bold text-gray-900 dark:text-white">
                {typeof metric.value === 'number' && metric.value < 10
                  ? metric.value.toFixed(2)
                  : Math.round(metric.value).toLocaleString()}
              </span>
              {metric.name.includes('Rate') && <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">%</span>}
              {metric.name.includes('Cost') && <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">$</span>}
            </div>
            <div className={`text-sm mt-2 ${getTrendColor(metric.trend)}`}>
              {metric.change > 0 ? '+' : ''}{metric.change.toFixed(1)} from last {metric.period}
            </div>
          </div>
        ))}
      </div>

      {/* Usage Statistics */}
      {usageStats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Usage Overview</h4>
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Total Videos Processed</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {usageStats.totalVideos.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Total Processing Time</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {Math.floor(usageStats.totalProcessingTime / 3600)}h {Math.floor((usageStats.totalProcessingTime % 3600) / 60)}m
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Average Processing Time</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {usageStats.averageProcessingTime}s
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Success Rate</span>
                <span className="text-sm font-medium text-green-600 dark:text-green-400">
                  {usageStats.successRate.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Cost per Video</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  ${usageStats.costPerVideo.toFixed(3)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Monthly Active Users</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {usageStats.monthlyActiveUsers.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Performance Trends</h4>
            <AdvancedCharts
              data={metrics.slice(0, 4).map(m => ({
                name: m.name,
                value: m.value,
                timestamp: new Date().toISOString()
              }))}
              height={250}
            />
          </div>
        </div>
      )}

      {/* Charts Section */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Detailed Analytics</h4>
        <AdvancedCharts
          data={metrics.map(m => ({
            name: m.name,
            value: m.value,
            timestamp: new Date().toISOString()
          }))}
          height={400}
        />
      </div>
    </div>
  );
}
