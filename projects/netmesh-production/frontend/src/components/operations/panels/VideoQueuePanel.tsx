import React, { useState, useEffect } from 'react';

interface VideoJob {
  id: string;
  title: string;
  url: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'paused';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  progress: number;
  duration?: number;
  estimatedTime?: number;
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
  agentId?: string;
  retryCount: number;
}

interface QueueStats {
  total: number;
  queued: number;
  processing: number;
  completed: number;
  failed: number;
  avgProcessingTime: number;
  successRate: number;
}

export function VideoQueuePanel() {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<VideoJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'queued' | 'processing' | 'completed' | 'failed'>('all');

  // Simulate real-time queue data
  useEffect(() => {
    const generateMockJobs = () => {
      const statuses: VideoJob['status'][] = ['queued', 'processing', 'completed', 'failed', 'paused'];
      const priorities: VideoJob['priority'][] = ['low', 'normal', 'high', 'urgent'];

      const mockJobs: VideoJob[] = Array.from({ length: 15 }, (_, i) => {
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const priority = priorities[Math.floor(Math.random() * priorities.length)];
        const progress = status === 'completed' ? 100 : status === 'processing' ? Math.floor(Math.random() * 100) : 0;

        return {
          id: `job-${i + 1}`,
          title: `Video Analysis: ${['Machine Learning Tutorial', 'React Best Practices', 'AI Ethics Discussion', 'Cloud Architecture', 'DevOps Pipeline'][Math.floor(Math.random() * 5)]} #${i + 1}`,
          url: `https://youtube.com/watch?v=${Math.random().toString(36).substr(2, 11)}`,
          status,
          priority,
          progress,
          duration: status === 'completed' ? Math.floor(Math.random() * 600) + 120 : undefined,
          estimatedTime: status === 'processing' ? Math.floor(Math.random() * 300) + 60 : undefined,
          startedAt: status !== 'queued' ? new Date(Date.now() - Math.random() * 3600000) : undefined,
          completedAt: status === 'completed' ? new Date(Date.now() - Math.random() * 1800000) : undefined,
          error: status === 'failed' ? ['Network timeout', 'Invalid video format', 'Processing error'][Math.floor(Math.random() * 3)] : undefined,
          agentId: status === 'processing' ? `video-${Math.floor(Math.random() * 3) + 1}` : undefined,
          retryCount: status === 'failed' ? Math.floor(Math.random() * 3) : 0
        };
      });

      setJobs(mockJobs.sort((a, b) => {
        // Sort by priority first, then by status
        const priorityOrder = { urgent: 4, high: 3, normal: 2, low: 1 };
        const statusOrder = { processing: 4, queued: 3, paused: 2, completed: 1, failed: 0 };

        if (a.priority !== b.priority) {
          return priorityOrder[b.priority] - priorityOrder[a.priority];
        }
        return statusOrder[b.status] - statusOrder[a.status];
      }));

      setIsLoading(false);
    };

    generateMockJobs();

    // Update every 6 seconds
    const interval = setInterval(generateMockJobs, 6000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'queued':
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900';
      case 'processing':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900';
      case 'completed':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900';
      case 'failed':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
      case 'paused':
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900';
      case 'high':
        return 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900';
      case 'normal':
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900';
      case 'low':
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const filteredJobs = jobs.filter(job =>
    filter === 'all' || job.status === filter
  );

  const stats: QueueStats = {
    total: jobs.length,
    queued: jobs.filter(j => j.status === 'queued').length,
    processing: jobs.filter(j => j.status === 'processing').length,
    completed: jobs.filter(j => j.status === 'completed').length,
    failed: jobs.filter(j => j.status === 'failed').length,
    avgProcessingTime: jobs.filter(j => j.duration).reduce((sum, j) => sum + (j.duration || 0), 0) / jobs.filter(j => j.duration).length || 0,
    successRate: Math.round((jobs.filter(j => j.status === 'completed').length / Math.max(jobs.filter(j => j.status !== 'queued').length, 1)) * 100)
  };

  const handlePause = (job: VideoJob) => {
    console.log('Pausing job:', job.id);
    // Implementation would pause the job
  };

  const handleResume = (job: VideoJob) => {
    console.log('Resuming job:', job.id);
    // Implementation would resume the job
  };

  const handleRetry = (job: VideoJob) => {
    console.log('Retrying job:', job.id);
    // Implementation would retry the job
  };

  const handleCancel = (job: VideoJob) => {
    console.log('Canceling job:', job.id);
    // Implementation would cancel the job
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
              <span className="text-2xl">🎥</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Jobs</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.total}</p>
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
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Processing</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.processing}</p>
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
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Completed</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{stats.completed}</p>
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
      </div>

      {/* Queue Management */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Video Processing Queue</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Monitor and manage video processing jobs</p>
            </div>
            <div className="flex items-center space-x-4">
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="queued">Queued</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
                Add Video Job
              </button>
            </div>
          </div>
        </div>

        {/* Job List */}
        <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
          {filteredJobs.map((job) => (
            <div key={job.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(job.status)}`}>
                        {job.status}
                      </span>
                    </div>
                    <div className="flex-shrink-0">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getPriorityColor(job.priority)}`}>
                        {job.priority}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {job.title}
                      </h4>
                      <div className="flex items-center space-x-4 mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          ID: {job.id}
                        </span>
                        {job.agentId && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            Agent: {job.agentId}
                          </span>
                        )}
                        {job.duration && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            Duration: {Math.floor(job.duration / 60)}m {job.duration % 60}s
                          </span>
                        )}
                        {job.estimatedTime && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            ETA: {Math.floor(job.estimatedTime / 60)}m {job.estimatedTime % 60}s
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                      <span>Progress</span>
                      <span>{job.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          job.status === 'completed' ? 'bg-green-500' :
                          job.status === 'failed' ? 'bg-red-500' :
                          job.status === 'processing' ? 'bg-blue-500' : 'bg-gray-400'
                        }`}
                        style={{ width: `${job.progress}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3 ml-4">
                  {/* Controls */}
                  <div className="flex space-x-2">
                    {job.status === 'processing' && (
                      <button
                        onClick={() => handlePause(job)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                        title="Pause Job"
                      >
                        ⏸️
                      </button>
                    )}
                    {job.status === 'paused' && (
                      <button
                        onClick={() => handleResume(job)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                        title="Resume Job"
                      >
                        ▶️
                      </button>
                    )}
                    {job.status === 'failed' && job.retryCount < 3 && (
                      <button
                        onClick={() => handleRetry(job)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                        title="Retry Job"
                      >
                        🔄
                      </button>
                    )}
                    {(job.status === 'queued' || job.status === 'processing') && (
                      <button
                        onClick={() => handleCancel(job)}
                        className="text-gray-400 hover:text-red-600 dark:hover:text-red-400 p-1"
                        title="Cancel Job"
                      >
                        ❌
                      </button>
                    )}
                    <button
                      onClick={() => setSelectedJob(job)}
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

      {/* Job Details Modal */}
      {selectedJob && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                🎥 {selectedJob.title}
              </h3>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Job ID</h4>
                  <p className="text-sm text-gray-900 dark:text-white font-mono">{selectedJob.id}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</h4>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(selectedJob.status)}`}>
                    {selectedJob.status}
                  </span>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Priority</h4>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getPriorityColor(selectedJob.priority)}`}>
                    {selectedJob.priority}
                  </span>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Progress</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedJob.progress}%</p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Video URL</h4>
                <a
                  href={selectedJob.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline break-all"
                >
                  {selectedJob.url}
                </a>
              </div>

              {selectedJob.agentId && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Processing Agent</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedJob.agentId}</p>
                </div>
              )}

              {selectedJob.error && (
                <div>
                  <h4 className="text-sm font-medium text-red-500 dark:text-red-400">Error</h4>
                  <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                    {selectedJob.error}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-3 gap-4">
                {selectedJob.startedAt && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Started</h4>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {selectedJob.startedAt.toLocaleString()}
                    </p>
                  </div>
                )}
                {selectedJob.completedAt && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Completed</h4>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {selectedJob.completedAt.toLocaleString()}
                    </p>
                  </div>
                )}
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">Retry Count</h4>
                  <p className="text-sm text-gray-900 dark:text-white">{selectedJob.retryCount}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
