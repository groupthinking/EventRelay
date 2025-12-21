import React, { useState, useEffect } from 'react';

interface Agent {
  id: string;
  name: string;
  type: 'mcp_server' | 'video_processor' | 'data_analyzer' | 'api_handler';
  status: 'online' | 'offline' | 'degraded' | 'maintenance';
  uptime: number;
  cpu: number;
  memory: number;
  requestsProcessed: number;
  errorRate: number;
  lastHealthCheck: Date;
  config: {
    maxConcurrency: number;
    timeout: number;
    retryAttempts: number;
  };
}

interface AgentStats {
  total: number;
  online: number;
  degraded: number;
  offline: number;
  avgUptime: number;
  totalRequests: number;
}

export function AgentManagementPanel() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'online' | 'offline' | 'degraded'>('all');

  // Simulate real-time agent data
  useEffect(() => {
    const generateMockAgents = () => {
      const agentTypes: Agent['type'][] = ['mcp_server', 'video_processor', 'data_analyzer', 'api_handler'];
      const statuses: Agent['status'][] = ['online', 'offline', 'degraded', 'maintenance'];

      const mockAgents: Agent[] = [
        {
          id: 'mcp-001',
          name: 'Primary MCP Server',
          type: 'mcp_server',
          status: 'online',
          uptime: 99.9,
          cpu: Math.random() * 30 + 10,
          memory: Math.random() * 40 + 20,
          requestsProcessed: Math.floor(Math.random() * 10000) + 5000,
          errorRate: Math.random() * 0.5,
          lastHealthCheck: new Date(),
          config: { maxConcurrency: 100, timeout: 30, retryAttempts: 3 }
        },
        {
          id: 'video-001',
          name: 'Video Transcription Agent',
          type: 'video_processor',
          status: 'online',
          uptime: 98.5,
          cpu: Math.random() * 60 + 20,
          memory: Math.random() * 50 + 30,
          requestsProcessed: Math.floor(Math.random() * 5000) + 2000,
          errorRate: Math.random() * 1.5,
          lastHealthCheck: new Date(),
          config: { maxConcurrency: 5, timeout: 300, retryAttempts: 2 }
        },
        {
          id: 'video-002',
          name: 'Video Analysis Agent',
          type: 'video_processor',
          status: Math.random() > 0.8 ? 'degraded' : 'online',
          uptime: 97.2,
          cpu: Math.random() * 70 + 15,
          memory: Math.random() * 45 + 25,
          requestsProcessed: Math.floor(Math.random() * 3000) + 1500,
          errorRate: Math.random() * 2.0,
          lastHealthCheck: new Date(),
          config: { maxConcurrency: 3, timeout: 600, retryAttempts: 1 }
        },
        {
          id: 'data-001',
          name: 'Content Analyzer',
          type: 'data_analyzer',
          status: 'online',
          uptime: 99.1,
          cpu: Math.random() * 25 + 5,
          memory: Math.random() * 30 + 15,
          requestsProcessed: Math.floor(Math.random() * 8000) + 3000,
          errorRate: Math.random() * 0.8,
          lastHealthCheck: new Date(),
          config: { maxConcurrency: 20, timeout: 60, retryAttempts: 3 }
        },
        {
          id: 'api-001',
          name: 'API Gateway Handler',
          type: 'api_handler',
          status: Math.random() > 0.9 ? 'offline' : 'online',
          uptime: 95.8,
          cpu: Math.random() * 20 + 5,
          memory: Math.random() * 25 + 10,
          requestsProcessed: Math.floor(Math.random() * 15000) + 8000,
          errorRate: Math.random() * 1.2,
          lastHealthCheck: new Date(),
          config: { maxConcurrency: 50, timeout: 10, retryAttempts: 5 }
        }
      ];

      setAgents(mockAgents);
      setIsLoading(false);
    };

    generateMockAgents();

    // Update every 8 seconds
    const interval = setInterval(generateMockAgents, 8000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900';
      case 'offline':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900';
      case 'maintenance':
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'mcp_server':
        return '🖥️';
      case 'video_processor':
        return '🎥';
      case 'data_analyzer':
        return '📊';
      case 'api_handler':
        return '🔗';
      default:
        return '🤖';
    }
  };

  const filteredAgents = agents.filter(agent =>
    filter === 'all' || agent.status === filter
  );

  const stats: AgentStats = {
    total: agents.length,
    online: agents.filter(a => a.status === 'online').length,
    degraded: agents.filter(a => a.status === 'degraded').length,
    offline: agents.filter(a => a.status === 'offline').length,
    avgUptime: agents.reduce((sum, a) => sum + a.uptime, 0) / agents.length,
    totalRequests: agents.reduce((sum, a) => sum + a.requestsProcessed, 0)
  };

  const handleRestart = (agent: Agent) => {
    console.log('Restarting agent:', agent.id);
    // Implementation would restart the agent
  };

  const handleConfigure = (agent: Agent) => {
    console.log('Configuring agent:', agent.id);
    // Implementation would open configuration modal
  };

  const handleScale = (agent: Agent, direction: 'up' | 'down') => {
    console.log(`${direction === 'up' ? 'Scaling up' : 'Scaling down'} agent:`, agent.id);
    // Implementation would scale the agent
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            </div>
          ))}
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm animate-pulse">
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <span className="text-2xl">🤖</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Agents</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.total}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Online</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.online}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
              <svg className="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Degraded</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.degraded}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
              <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Offline</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.offline}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Agent Management */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Agent Management</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Monitor and control AI agents and MCP servers</p>
            </div>
            <div className="flex items-center space-x-4">
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="online">Online</option>
                <option value="degraded">Degraded</option>
                <option value="offline">Offline</option>
              </select>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
                Add Agent
              </button>
            </div>
          </div>
        </div>

        {/* Agent List */}
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {filteredAgents.map((agent) => (
            <div key={agent.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="text-2xl">{getTypeIcon(agent.type)}</div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">{agent.name}</h4>
                    <div className="flex items-center space-x-4 mt-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ID: {agent.id}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {agent.requestsProcessed.toLocaleString()} requests
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {agent.uptime.toFixed(1)}% uptime
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  {/* Performance Metrics */}
                  <div className="text-right text-xs text-gray-500 dark:text-gray-400">
                    <div>CPU: {agent.cpu.toFixed(1)}%</div>
                    <div>Memory: {agent.memory.toFixed(1)}%</div>
                    <div>Error: {agent.errorRate.toFixed(1)}%</div>
                  </div>

                  {/* Status */}
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(agent.status)}`}>
                    {agent.status}
                  </span>

                  {/* Controls */}
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleRestart(agent)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="Restart Agent"
                    >
                      🔄
                    </button>
                    <button
                      onClick={() => handleScale(agent, 'up')}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="Scale Up"
                    >
                      ⬆️
                    </button>
                    <button
                      onClick={() => handleScale(agent, 'down')}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="Scale Down"
                    >
                      ⬇️
                    </button>
                    <button
                      onClick={() => handleConfigure(agent)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="Configure"
                    >
                      ⚙️
                    </button>
                    <button
                      onClick={() => setSelectedAgent(agent)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="View Details"
                    >
                      👁️
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Agent Details Modal */}
      {selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                {getTypeIcon(selectedAgent.type)} {selectedAgent.name}
              </h3>
              <button
                onClick={() => setSelectedAgent(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Agent ID</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedAgent.id}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Type</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedAgent.type.replace('_', ' ')}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Uptime</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedAgent.uptime.toFixed(1)}%</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Requests Processed</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedAgent.requestsProcessed.toLocaleString()}</p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Configuration</h4>
                <div className="bg-gray-50 dark:bg-gray-700 rounded p-3 text-xs font-mono">
                  <div>Max Concurrency: {selectedAgent.config.maxConcurrency}</div>
                  <div>Timeout: {selectedAgent.config.timeout}s</div>
                  <div>Retry Attempts: {selectedAgent.config.retryAttempts}</div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Performance Metrics</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {selectedAgent.cpu.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">CPU</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {selectedAgent.memory.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Memory</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {selectedAgent.errorRate.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Error Rate</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
