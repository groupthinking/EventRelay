import React, { useState, useEffect } from 'react';

interface Deployment {
  id: string;
  name: string;
  platform: 'vercel' | 'netlify' | 'fly';
  status: 'success' | 'failed' | 'in_progress' | 'queued';
  branch: string;
  commit: string;
  startedAt: Date;
  duration?: number;
  url?: string;
  logs: string[];
  error?: string;
}

interface DeploymentStats {
  total: number;
  successful: number;
  failed: number;
  inProgress: number;
  successRate: number;
}

export function DeploymentMonitorPanel() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'success' | 'failed' | 'in_progress'>('all');

  // Simulate real-time deployment data
  useEffect(() => {
    const generateMockDeployments = () => {
      const platforms = ['vercel', 'netlify', 'fly'];
      const statuses: Deployment['status'][] = ['success', 'failed', 'in_progress', 'queued'];
      const branches = ['main', 'develop', 'feature/ops-dashboard'];

      const mockDeployments: Deployment[] = Array.from({ length: 12 }, (_, i) => {
        const platform = platforms[Math.floor(Math.random() * platforms.length)];
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const startedAt = new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000);

        return {
          id: `deploy-${i + 1}`,
          name: `UVAI-${platform}-v${Math.floor(Math.random() * 100)}`,
          platform: platform as any,
          status,
          branch: branches[Math.floor(Math.random() * branches.length)],
          commit: `${Math.random().toString(36).substr(2, 9)}`,
          startedAt,
          duration: status === 'success' || status === 'failed' ? Math.floor(Math.random() * 300) + 30 : undefined,
          url: status === 'success' ? `https://${platform}.app/${Math.random().toString(36).substr(2, 8)}` : undefined,
          logs: [
            'Starting deployment...',
            'Building application...',
            'Installing dependencies...',
            status === 'success' ? 'Deployment completed successfully!' :
            status === 'failed' ? 'Error: Build failed with exit code 1' :
            'Processing deployment...'
          ],
          error: status === 'failed' ? 'Build failed: Module not found' : undefined
        };
      });

      setDeployments(mockDeployments.sort((a, b) => b.startedAt.getTime() - a.startedAt.getTime()));
      setIsLoading(false);
    };

    generateMockDeployments();

    // Update every 10 seconds
    const interval = setInterval(generateMockDeployments, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900';
      case 'failed':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
      case 'in_progress':
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900';
      case 'queued':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'vercel':
        return '▲';
      case 'netlify':
        return 'N';
      case 'fly':
        return 'F';
      default:
        return '•';
    }
  };

  const filteredDeployments = deployments.filter(deployment =>
    filter === 'all' || deployment.status === filter
  );

  const stats: DeploymentStats = {
    total: deployments.length,
    successful: deployments.filter(d => d.status === 'success').length,
    failed: deployments.filter(d => d.status === 'failed').length,
    inProgress: deployments.filter(d => d.status === 'in_progress').length,
    successRate: Math.round((deployments.filter(d => d.status === 'success').length / deployments.length) * 100)
  };

  const handleRedeploy = (deployment: Deployment) => {
    console.log('Redeploying:', deployment.id);
    // Implementation would trigger redeployment
  };

  const handleRollback = (deployment: Deployment) => {
    console.log('Rolling back:', deployment.id);
    // Implementation would trigger rollback
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
              <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Deployments</p>
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
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Successful</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.successful}</p>
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
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Failed</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.failed}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
              <svg className="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">In Progress</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.inProgress}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Deployment History</h3>
          <div className="flex items-center space-x-4">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="success">Successful</option>
              <option value="failed">Failed</option>
              <option value="in_progress">In Progress</option>
            </select>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
              New Deployment
            </button>
          </div>
        </div>

        {/* Deployment List */}
        <div className="space-y-4">
          {filteredDeployments.map((deployment) => (
            <div key={deployment.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="text-2xl font-bold text-gray-400">{getPlatformIcon(deployment.platform)}</div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">{deployment.name}</h4>
                    <div className="flex items-center space-x-4 mt-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {deployment.branch} • {deployment.commit.slice(0, 7)}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {deployment.startedAt.toLocaleString()}
                      </span>
                      {deployment.duration && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {Math.floor(deployment.duration / 60)}m {deployment.duration % 60}s
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  {deployment.url && (
                    <a
                      href={deployment.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm"
                    >
                      View Live
                    </a>
                  )}
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(deployment.status)}`}>
                    {deployment.status.replace('_', ' ')}
                  </span>
                  <div className="flex space-x-2">
                    {deployment.status === 'success' && (
                      <button
                        onClick={() => handleRedeploy(deployment)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                        title="Redeploy"
                      >
                        🔄
                      </button>
                    )}
                    {deployment.status === 'success' && (
                      <button
                        onClick={() => handleRollback(deployment)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                        title="Rollback"
                      >
                        ↶
                      </button>
                    )}
                    <button
                      onClick={() => setSelectedDeployment(deployment)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                      title="View Logs"
                    >
                      📋
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Logs Modal */}
      {selectedDeployment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-96 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Deployment Logs: {selectedDeployment.name}
              </h3>
              <button
                onClick={() => setSelectedDeployment(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <div className="px-6 py-4 max-h-80 overflow-y-auto bg-gray-900 text-green-400 font-mono text-sm">
              {selectedDeployment.logs.map((log, index) => (
                <div key={index} className="mb-1">
                  <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> {log}
                </div>
              ))}
              {selectedDeployment.error && (
                <div className="text-red-400 mt-4">
                  <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> ERROR: {selectedDeployment.error}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
