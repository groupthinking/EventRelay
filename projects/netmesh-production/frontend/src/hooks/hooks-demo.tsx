import React, { useState } from 'react';
import {
  useVideoAnalysis,
  useProjectData,
  useFileUpload,
  useMCPIntegration,
  useLocalStorage,
  useDebounce,
  useDebouncedCallback,
  useDebouncedState,
  useDebouncedSearch,
  useDebouncedForm,
} from './index';

// Demo component for Video Analysis Hook
const VideoAnalysisDemo: React.FC = () => {
  const [videoUrl, setVideoUrl] = useState('');
  const {
    isLoading,
    error,
    data,
    progress,
    currentStep,
    metadata,
    isPaused,
    analyzeVideo,
    togglePause,
    cancelAnalysis,
    retryAnalysis,
    getInsights,
  } = useVideoAnalysis();

  const handleAnalyze = () => {
    if (videoUrl.trim()) {
      analyzeVideo(videoUrl);
    }
  };

  const insights = getInsights();

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h3 className="text-xl font-semibold mb-4">🎥 Video Analysis Hook</h3>
      
      <div className="space-y-4">
        <div>
          <input
            type="text"
            placeholder="Enter YouTube URL"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={handleAnalyze}
            disabled={isLoading || !videoUrl.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            {isLoading ? 'Analyzing...' : 'Analyze Video'}
          </button>
          
          {isLoading && (
            <>
              <button
                onClick={togglePause}
                className="px-4 py-2 bg-yellow-500 text-white rounded"
              >
                {isPaused ? 'Resume' : 'Pause'}
              </button>
              <button
                onClick={cancelAnalysis}
                className="px-4 py-2 bg-red-500 text-white rounded"
              >
                Cancel
              </button>
            </>
          )}
          
          {error && (
            <button
              onClick={retryAnalysis}
              className="px-4 py-2 bg-green-500 text-white rounded"
            >
              Retry
            </button>
          )}
        </div>

        {isLoading && (
          <div className="space-y-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-600">{currentStep}</p>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-100 text-red-700 rounded">
            Error: {error}
          </div>
        )}

        {metadata && (
          <div className="p-3 bg-blue-50 rounded">
            <h4 className="font-medium">Video Metadata</h4>
            <p className="text-sm">{metadata.title}</p>
            <p className="text-sm text-gray-600">{metadata.channel}</p>
          </div>
        )}

        {insights && (
          <div className="p-3 bg-green-50 rounded">
            <h4 className="font-medium">Analysis Insights</h4>
            <p className="text-sm">Difficulty: {insights.difficulty}</p>
            <p className="text-sm">Time: {insights.timeInvestment}</p>
            <p className="text-sm">Quality: {insights.quality}</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Demo component for Project Data Hook
const ProjectDataDemo: React.FC = () => {
  const {
    projects,
    currentProject,
    createProject,
    updateProject,
    deleteProject,
    setCurrentProject,
    getProjectStats,
    getFilteredProjects,
  } = useProjectData();

  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');

  const handleCreateProject = () => {
    if (newProjectName.trim()) {
      createProject({
        name: newProjectName,
        description: newProjectDesc,
        status: 'draft',
        tags: ['demo'],
        priority: 'medium',
        estimatedDuration: 2,
        progress: 0,
        actualDuration: 0,
        videoIds: [],
        notes: [],
        collaborators: [],
      });
      setNewProjectName('');
      setNewProjectDesc('');
    }
  };

  const stats = getProjectStats();
  const filteredProjects = getFilteredProjects();

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h3 className="text-xl font-semibold mb-4">📁 Project Data Hook</h3>
      
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <input
              type="text"
              placeholder="Project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="w-full p-2 border rounded"
            />
          </div>
          <div>
            <input
              type="text"
              placeholder="Description"
              value={newProjectDesc}
              onChange={(e) => setNewProjectDesc(e.target.value)}
              className="w-full p-2 border rounded"
            />
          </div>
        </div>
        
        <button
          onClick={handleCreateProject}
          disabled={!newProjectName.trim()}
          className="px-4 py-2 bg-green-500 text-white rounded disabled:opacity-50"
        >
          Create Project
        </button>

        <div className="grid grid-cols-4 gap-4 text-center">
          <div className="p-3 bg-blue-50 rounded">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-600">Total</div>
          </div>
          <div className="p-3 bg-green-50 rounded">
            <div className="text-2xl font-bold">{stats.completed}</div>
            <div className="text-sm text-gray-600">Completed</div>
          </div>
          <div className="p-3 bg-yellow-50 rounded">
            <div className="text-2xl font-bold">{stats.active}</div>
            <div className="text-sm text-gray-600">Active</div>
          </div>
          <div className="p-3 bg-purple-50 rounded">
            <div className="text-2xl font-bold">{stats.averageProgress}%</div>
            <div className="text-sm text-gray-600">Avg Progress</div>
          </div>
        </div>

        <div className="space-y-2">
          <h4 className="font-medium">Projects ({filteredProjects.length})</h4>
          {filteredProjects.slice(0, 3).map((project) => (
            <div key={project.id} className="p-3 border rounded flex justify-between items-center">
              <div>
                <div className="font-medium">{project.name}</div>
                <div className="text-sm text-gray-600">{project.description}</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentProject(project)}
                  className="px-2 py-1 bg-blue-500 text-white text-xs rounded"
                >
                  Select
                </button>
                <button
                  onClick={() => deleteProject(project.id)}
                  className="px-2 py-1 bg-red-500 text-white text-xs rounded"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        {currentProject && (
          <div className="p-3 bg-blue-50 rounded">
            <h4 className="font-medium">Current Project</h4>
            <p className="text-sm">{currentProject.name}</p>
            <p className="text-sm text-gray-600">{currentProject.description}</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Demo component for File Upload Hook
const FileUploadDemo: React.FC = () => {
  const {
    files,
    isUploading,
    totalProgress,
    activeUploads,
    completedUploads,
    failedUploads,
    addFiles,
    removeFile,
    cancelUpload,
    retryUpload,
    clearCompleted,
    clearAll,
    getUploadStats,
  } = useFileUpload({
    onProgress: (fileId, progress) => {
      console.log(`File ${fileId}: ${progress}%`);
    },
    onComplete: (fileId, result) => {
      console.log(`File ${fileId} completed:`, result);
    },
    onError: (fileId, error) => {
      console.log(`File ${fileId} failed:`, error);
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length > 0) {
      addFiles(selectedFiles);
    }
  };

  const stats = getUploadStats();

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h3 className="text-xl font-semibold mb-4">📤 File Upload Hook</h3>
      
      <div className="space-y-4">
        <div>
          <input
            type="file"
            multiple
            onChange={handleFileSelect}
            className="w-full p-2 border rounded"
          />
        </div>

        <div className="grid grid-cols-4 gap-4 text-center">
          <div className="p-3 bg-blue-50 rounded">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-600">Total</div>
          </div>
          <div className="p-3 bg-yellow-50 rounded">
            <div className="text-2xl font-bold">{stats.uploading}</div>
            <div className="text-sm text-gray-600">Uploading</div>
          </div>
          <div className="p-3 bg-green-50 rounded">
            <div className="text-2xl font-bold">{stats.completed}</div>
            <div className="text-sm text-gray-600">Completed</div>
          </div>
          <div className="p-3 bg-red-50 rounded">
            <div className="text-2xl font-bold">{stats.failed}</div>
            <div className="text-sm text-gray-600">Failed</div>
          </div>
        </div>

        {isUploading && (
          <div className="space-y-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${totalProgress}%` }}
              />
            </div>
            <p className="text-sm text-gray-600">
              {activeUploads} active uploads • {totalProgress}% complete
            </p>
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={clearCompleted}
            disabled={completedUploads === 0}
            className="px-4 py-2 bg-gray-500 text-white rounded disabled:opacity-50"
          >
            Clear Completed
          </button>
          <button
            onClick={clearAll}
            disabled={files.length === 0}
            className="px-4 py-2 bg-red-500 text-white rounded disabled:opacity-50"
          >
            Clear All
          </button>
        </div>

        <div className="space-y-2">
          <h4 className="font-medium">Files ({files.length})</h4>
          {files.map((file) => (
            <div key={file.id} className="p-3 border rounded">
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-medium">{file.name}</div>
                  <div className="text-sm text-gray-600">
                    {file.size} bytes • {file.type}
                  </div>
                </div>
                <div className="flex gap-2">
                  {file.status === 'uploading' && (
                    <button
                      onClick={() => cancelUpload(file.id)}
                      className="px-2 py-1 bg-red-500 text-white text-xs rounded"
                    >
                      Cancel
                    </button>
                  )}
                  {file.status === 'failed' && (
                    <button
                      onClick={() => retryUpload(file.id)}
                      className="px-2 py-1 bg-green-500 text-white text-xs rounded"
                    >
                      Retry
                    </button>
                  )}
                  <button
                    onClick={() => removeFile(file.id)}
                    className="px-2 py-1 bg-gray-500 text-white text-xs rounded"
                  >
                    Remove
                  </button>
                </div>
              </div>
              
              {file.status === 'uploading' && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${file.progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {file.progress}% • {file.uploadedBytes} / {file.size} bytes
                  </p>
                </div>
              )}
              
              {file.status === 'failed' && file.error && (
                <p className="text-xs text-red-600 mt-1">Error: {file.error}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Demo component for MCP Integration Hook
const MCPIntegrationDemo: React.FC = () => {
  const {
    isConnected,
    isConnecting,
    connectionError,
    agentStatuses,
    systemMetrics,
    messages,
    isProcessingVideo,
    videoProcessingProgress,
    currentVideoTask,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
    processVideo,
    getSystemHealth,
  } = useMCPIntegration({
    onConnectionChange: (connected) => {
      console.log('MCP connection changed:', connected);
    },
    onError: (error) => {
      console.log('MCP error:', error);
    },
  });

  const [messageText, setMessageText] = useState('');
  const [videoUrl, setVideoUrl] = useState('');

  const handleSendMessage = () => {
    if (messageText.trim()) {
      sendMessage(messageText);
      setMessageText('');
    }
  };

  const handleProcessVideo = () => {
    if (videoUrl.trim()) {
      processVideo(videoUrl, {
        quality: 'high',
        format: 'mp4',
        includeTranscript: true,
        includeChapters: true,
      });
    }
  };

  const systemHealth = getSystemHealth();

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h3 className="text-xl font-semibold mb-4">🔌 MCP Integration Hook</h3>
      
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            onClick={connect}
            disabled={isConnecting || isConnected}
            className="px-4 py-2 bg-green-500 text-white rounded disabled:opacity-50"
          >
            {isConnecting ? 'Connecting...' : isConnected ? 'Connected' : 'Connect'}
          </button>
          
          {isConnected && (
            <button
              onClick={disconnect}
              className="px-4 py-2 bg-red-500 text-white rounded"
            >
              Disconnect
            </button>
          )}
        </div>

        {connectionError && (
          <div className="p-3 bg-red-100 text-red-700 rounded">
            Connection Error: {connectionError}
          </div>
        )}

        {isConnected && (
          <>
            <div className="grid grid-cols-3 gap-4">
              <div className="p-3 bg-blue-50 rounded text-center">
                <div className="text-lg font-bold">{agentStatuses.length}</div>
                <div className="text-sm text-gray-600">Agents</div>
              </div>
              <div className="p-3 bg-green-50 rounded text-center">
                <div className="text-lg font-bold capitalize">{systemHealth}</div>
                <div className="text-sm text-gray-600">System Health</div>
              </div>
              <div className="p-3 bg-purple-50 rounded text-center">
                <div className="text-lg font-bold">{messages.length}</div>
                <div className="text-sm text-gray-600">Messages</div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Send Message</h4>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Type a message..."
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    className="flex-1 p-2 border rounded"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!messageText.trim()}
                    className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-2">Process Video</h4>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter video URL"
                    value={videoUrl}
                    onChange={(e) => setVideoUrl(e.target.value)}
                    className="flex-1 p-2 border rounded"
                  />
                  <button
                    onClick={handleProcessVideo}
                    disabled={!videoUrl.trim() || isProcessingVideo}
                    className="px-4 py-2 bg-purple-500 text-white rounded disabled:opacity-50"
                  >
                    {isProcessingVideo ? 'Processing...' : 'Process'}
                  </button>
                </div>
              </div>

              {isProcessingVideo && (
                <div className="space-y-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${videoProcessingProgress}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-600">{currentVideoTask}</p>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={clearMessages}
                  disabled={messages.length === 0}
                  className="px-4 py-2 bg-gray-500 text-white rounded disabled:opacity-50"
                >
                  Clear Messages
                </button>
              </div>

              {messages.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-medium">Recent Messages</h4>
                  <div className="max-h-40 overflow-y-auto space-y-2">
                    {messages.slice(-5).map((message) => (
                      <div
                        key={message.id}
                        className={`p-2 rounded text-sm ${
                          message.role === 'user'
                            ? 'bg-blue-100 text-blue-800'
                            : message.role === 'assistant'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        <div className="font-medium capitalize">{message.role}</div>
                        <div>{message.content}</div>
                        <div className="text-xs text-gray-600">
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Demo component for Local Storage Hook
const LocalStorageDemo: React.FC = () => {
  const {
    value: storedValue,
    isLoading,
    error,
    lastUpdated,
    isStale,
    size,
    setValue,
    removeValue,
    clearAll,
    getStorageInfo,
    exportData,
    importData,
  } = useLocalStorage({
    key: 'demo_data',
    defaultValue: { name: 'Demo User', count: 0, preferences: {} },
    version: '1.0.0',
    onError: (error) => console.error('Storage error:', error),
    onSync: (value) => console.log('Storage synced:', value),
  });

  const [importFile, setImportFile] = useState<File | null>(null);
  const storageInfo = getStorageInfo();

  const handleImport = async () => {
    if (importFile) {
      const success = await importData(importFile);
      if (success) {
        setImportFile(null);
      }
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h3 className="text-xl font-semibold mb-4">💾 Local Storage Hook</h3>
      
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={storedValue.name}
              onChange={(e) => setValue({ ...storedValue, name: e.target.value })}
              className="w-full p-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Count</label>
            <input
              type="number"
              value={storedValue.count}
              onChange={(e) => setValue({ ...storedValue, count: parseInt(e.target.value) || 0 })}
              className="w-full p-2 border rounded"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setValue({ ...storedValue, count: storedValue.count + 1 })}
            className="px-4 py-2 bg-blue-500 text-white rounded"
          >
            Increment Count
          </button>
          <button
            onClick={() => setValue({ ...storedValue, count: 0 })}
            className="px-4 py-2 bg-yellow-500 text-white rounded"
          >
            Reset Count
          </button>
        </div>

        <div className="grid grid-cols-4 gap-4 text-center">
          <div className="p-3 bg-blue-50 rounded">
            <div className="text-lg font-bold">{isLoading ? '...' : '✓'}</div>
            <div className="text-sm text-gray-600">Status</div>
          </div>
          <div className="p-3 bg-green-50 rounded">
            <div className="text-lg font-bold">{size}</div>
            <div className="text-sm text-gray-600">Size (bytes)</div>
          </div>
          <div className="p-3 bg-yellow-50 rounded">
            <div className="text-lg font-bold">{isStale ? 'Yes' : 'No'}</div>
            <div className="text-sm text-gray-600">Stale</div>
          </div>
          <div className="p-3 bg-purple-50 rounded">
            <div className="text-lg font-bold">
              {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Never'}
            </div>
            <div className="text-sm text-gray-600">Last Updated</div>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-100 text-red-700 rounded">
            Storage Error: {error}
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={exportData}
            className="px-4 py-2 bg-green-500 text-white rounded"
          >
            Export Data
          </button>
          <button
            onClick={removeValue}
            className="px-4 py-2 bg-red-500 text-white rounded"
          >
            Remove Value
          </button>
          <button
            onClick={clearAll}
            className="px-4 py-2 bg-gray-500 text-white rounded"
          >
            Clear All
          </button>
        </div>

        <div>
          <h4 className="font-medium mb-2">Import Data</h4>
          <div className="flex gap-2">
            <input
              type="file"
              accept=".json"
              onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              className="flex-1 p-2 border rounded"
            />
            <button
              onClick={handleImport}
              disabled={!importFile}
              className="px-4 py-2 bg-purple-500 text-white rounded disabled:opacity-50"
            >
              Import
            </button>
          </div>
        </div>

        {storageInfo && (
          <div className="p-3 bg-gray-50 rounded">
            <h4 className="font-medium">Storage Info</h4>
            <div className="text-sm space-y-1">
              <div>Size: {storageInfo.size} bytes</div>
              <div>Version: {storageInfo.version}</div>
              <div>Age: {storageInfo.age ? Math.round(storageInfo.age / 1000) : 0}s</div>
              <div>Expired: {storageInfo.isExpired ? 'Yes' : 'No'}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Demo component for Debounce Hooks
const DebounceDemo: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [formValues, setFormValues] = useState({ name: '', email: '', message: '' });
  
  const debouncedSearchQuery = useDebounce(searchQuery, 500);
  const [debouncedValue, setDebouncedValue] = useState('');
  
  const debouncedCallback = useDebouncedCallback(
    (value: string) => {
      console.log('Debounced callback executed:', value);
    },
    { delay: 1000, leading: false, trailing: true }
  );

  const { search, results, isSearching, error } = useDebouncedSearch(
    async (query: string) => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      return [
        { id: 1, title: `Result 1 for "${query}"` },
        { id: 2, title: `Result 2 for "${query}"` },
        { id: 3, title: `Result 3 for "${query}"` },
      ];
    },
    { delay: 500, minQueryLength: 2 }
  );

  const { values, errors, isValidating, setValue, submit } = useDebouncedForm(
    { name: '', email: '', message: '' },
    {
      delay: 1000,
      onSubmit: (values) => {
        console.log('Form submitted:', values);
        alert('Form submitted successfully!');
      },
      onValidation: (values) => {
        const errors: string[] = [];
        if (!values.name) errors.push('Name is required');
        if (!values.email) errors.push('Email is required');
        if (!values.message) errors.push('Message is required');
        return errors.length > 0 ? errors : null;
      },
    }
  );

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h3 className="text-xl font-semibold mb-4">⏱️ Debounce Hooks</h3>
      
      <div className="space-y-6">
        {/* Basic Debounce */}
        <div>
          <h4 className="font-medium mb-2">Basic Debounce</h4>
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Type to see debounced value..."
              value={debouncedValue}
              onChange={(e) => setDebouncedValue(e.target.value)}
              className="w-full p-2 border rounded"
            />
            <p className="text-sm text-gray-600">
              Debounced value: {debouncedValue}
            </p>
          </div>
        </div>

        {/* Debounced Callback */}
        <div>
          <h4 className="font-medium mb-2">Debounced Callback</h4>
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Type to trigger debounced callback..."
              onChange={(e) => debouncedCallback(e.target.value)}
              className="w-full p-2 border rounded"
            />
            <p className="text-sm text-gray-600">
              Check console for callback execution
            </p>
          </div>
        </div>

        {/* Debounced Search */}
        <div>
          <h4 className="font-medium mb-2">Debounced Search</h4>
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Search (min 2 characters)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                search(e.target.value);
              }}
              className="w-full p-2 border rounded"
            />
            
            {isSearching && (
              <p className="text-sm text-blue-600">Searching...</p>
            )}
            
            {error && (
              <p className="text-sm text-red-600">Error: {error}</p>
            )}
            
            {results.length > 0 && (
              <div className="space-y-1">
                <p className="text-sm font-medium">Results:</p>
                {results.map((result) => (
                  <div key={result.id} className="p-2 bg-gray-50 rounded text-sm">
                    {result.title}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Debounced Form */}
        <div>
          <h4 className="font-medium mb-2">Debounced Form</h4>
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Name"
              value={values.name}
              onChange={(e) => setValue('name', e.target.value)}
              className="w-full p-2 border rounded"
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name}</p>
            )}
            
            <input
              type="email"
              placeholder="Email"
              value={values.email}
              onChange={(e) => setValue('email', e.target.value)}
              className="w-full p-2 border rounded"
            />
            {errors.email && (
              <p className="text-sm text-red-600">{errors.email}</p>
            )}
            
            <textarea
              placeholder="Message"
              value={values.message}
              onChange={(e) => setValue('message', e.target.value)}
              className="w-full p-2 border rounded"
              rows={3}
            />
            {errors.message && (
              <p className="text-sm text-red-600">{errors.message}</p>
            )}
            
            <div className="flex gap-2">
              <button
                onClick={submit}
                disabled={isValidating}
                className="px-4 py-2 bg-green-500 text-white rounded disabled:opacity-50"
              >
                {isValidating ? 'Validating...' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main demo component
const HooksDemo: React.FC = () => {
  const [activeTab, setActiveTab] = useState('video');

  const tabs = [
    { id: 'video', label: 'Video Analysis', component: <VideoAnalysisDemo /> },
    { id: 'project', label: 'Project Data', component: <ProjectDataDemo /> },
    { id: 'upload', label: 'File Upload', component: <FileUploadDemo /> },
    { id: 'mcp', label: 'MCP Integration', component: <MCPIntegrationDemo /> },
    { id: 'storage', label: 'Local Storage', component: <LocalStorageDemo /> },
    { id: 'debounce', label: 'Debounce', component: <DebounceDemo /> },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🪝 Enhanced Hooks Demo
          </h1>
          <p className="text-xl text-gray-600">
            Interactive examples of all the enhanced custom hooks
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-md mb-6">
          <div className="flex overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 bg-blue-50'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Active Tab Content */}
        {tabs.find(tab => tab.id === activeTab)?.component}
      </div>
    </div>
  );
};

export default HooksDemo;
