import React, { useState, useEffect } from 'react';
import { MainLayout } from '../layout/MainLayout';
import { SystemHealthPanel } from './panels/SystemHealthPanel';
import { DeploymentMonitorPanel } from './panels/DeploymentMonitorPanel';
import { AgentManagementPanel } from './panels/AgentManagementPanel';
import { VideoQueuePanel } from './panels/VideoQueuePanel';
import { AnalyticsPanel } from './panels/AnalyticsPanel';
import { SecurityPanel } from './panels/SecurityPanel';
import { useAppStore } from '../../store/appStore';

type ActivePanel = 'health' | 'deployments' | 'agents' | 'queue' | 'analytics' | 'security';

interface OperationsDashboardProps {
  initialPanel?: ActivePanel;
}

export function OperationsDashboard({ initialPanel = 'health' }: OperationsDashboardProps) {
  const [activePanel, setActivePanel] = useState<ActivePanel>(initialPanel);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const { theme } = useAppStore();

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const panels = [
    {
      id: 'health' as ActivePanel,
      label: 'System Health',
      icon: '🩺',
      description: 'Monitor system performance and health metrics'
    },
    {
      id: 'deployments' as ActivePanel,
      label: 'Deployments',
      icon: '🚀',
      description: 'Track deployment status and manage releases'
    },
    {
      id: 'agents' as ActivePanel,
      label: 'Agent Management',
      icon: '🤖',
      description: 'Control and monitor AI agents and MCP servers'
    },
    {
      id: 'queue' as ActivePanel,
      label: 'Video Queue',
      icon: '🎥',
      description: 'Manage video processing jobs and queue status'
    },
    {
      id: 'analytics' as ActivePanel,
      label: 'Analytics',
      icon: '📊',
      description: 'View usage statistics and performance reports'
    },
    {
      id: 'security' as ActivePanel,
      label: 'Security',
      icon: '🔒',
      description: 'Monitor security events and audit logs'
    }
  ];

  const renderActivePanel = () => {
    switch (activePanel) {
      case 'health':
        return <SystemHealthPanel />;
      case 'deployments':
        return <DeploymentMonitorPanel />;
      case 'agents':
        return <AgentManagementPanel />;
      case 'queue':
        return <VideoQueuePanel />;
      case 'analytics':
        return <AnalyticsPanel />;
      case 'security':
        return <SecurityPanel />;
      default:
        return <SystemHealthPanel />;
    }
  };

  return (
    <MainLayout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  🏗️ Operations Dashboard
                </h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Real-time monitoring and management of the UVAI platform
                </p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Last updated: {lastUpdate.toLocaleTimeString()}
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-green-600 dark:text-green-400 font-medium">
                    Live
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white dark:bg-gray-800 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex space-x-8" aria-label="Tabs">
              {panels.map((panel) => (
                <button
                  key={panel.id}
                  onClick={() => setActivePanel(panel.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                    activePanel === panel.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{panel.icon}</span>
                    <span>{panel.label}</span>
                  </div>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Panel Description */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">
                {panels.find(p => p.id === activePanel)?.icon}
              </span>
              <div>
                <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">
                  {panels.find(p => p.id === activePanel)?.label}
                </h2>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  {panels.find(p => p.id === activePanel)?.description}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            renderActivePanel()
          )}
        </div>
      </div>
    </MainLayout>
  );
}
