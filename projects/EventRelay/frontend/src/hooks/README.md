# 🪝 Enhanced Custom Hooks

This directory contains a comprehensive collection of enhanced custom React hooks designed for the UVAI YouTube Extension project. These hooks provide powerful state management, data persistence, and utility functions with TypeScript support.

## 📚 Table of Contents

- [Video Analysis Hook](#video-analysis-hook)
- [Project Data Hook](#project-data-hook)
- [File Upload Hook](#file-upload-hook)
- [MCP Integration Hook](#mcp-integration-hook)
- [Local Storage Hook](#local-storage-hook)
- [Debounce Hooks](#debounce-hooks)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## 🎥 Video Analysis Hook

### `useVideoAnalysis(options?)`

A comprehensive hook for analyzing YouTube videos with progress tracking, pause/resume functionality, and detailed metadata extraction.

#### Features
- **Progress Tracking**: Real-time progress updates with step-by-step analysis
- **Pause/Resume**: Control analysis execution
- **Error Handling**: Comprehensive error handling with retry mechanisms
- **Metadata Extraction**: Video information, chapters, and analysis results
- **Abort Support**: Cancel ongoing analysis operations

#### Usage

```tsx
import { useVideoAnalysis } from '../hooks';

const VideoAnalyzer = () => {
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
  } = useVideoAnalysis({
    includeTranscript: true,
    includeChapters: true,
    includeCodeExtraction: true,
    qualityThreshold: 8,
  });

  const handleAnalyze = async () => {
    try {
      const result = await analyzeVideo('https://youtube.com/watch?v=...');
      console.log('Analysis complete:', result);
    } catch (error) {
      console.error('Analysis failed:', error);
    }
  };

  return (
    <div>
      <button onClick={handleAnalyze} disabled={isLoading}>
        {isLoading ? 'Analyzing...' : 'Analyze Video'}
      </button>
      
      {isLoading && (
        <div>
          <div className="progress-bar" style={{ width: `${progress}%` }} />
          <p>{currentStep}</p>
        </div>
      )}
      
      {error && <p className="error">{error}</p>}
      
      {data && (
        <div>
          <h3>Analysis Results</h3>
          <p>Summary: {data.summary}</p>
          <p>Difficulty: {data.difficulty}</p>
          <p>Estimated Time: {data.estimatedLearningTime} minutes</p>
        </div>
      )}
    </div>
  );
};
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `includeTranscript` | `boolean` | `true` | Include video transcript in analysis |
| `includeChapters` | `boolean` | `true` | Generate video chapters |
| `includeCodeExtraction` | `boolean` | `true` | Extract code examples from video |
| `includeSentimentAnalysis` | `boolean` | `true` | Analyze video sentiment |
| `qualityThreshold` | `number` | `7` | Minimum quality score (1-10) |
| `maxKeyPoints` | `number` | `10` | Maximum key points to extract |

## 📁 Project Data Hook

### `useProjectData()`

A powerful hook for managing project data, learning progress, and project lifecycle with local storage persistence.

#### Features
- **Project Management**: Create, update, delete, and track projects
- **Learning Progress**: Track video watching progress and completion
- **Filtering & Sorting**: Advanced project filtering and sorting capabilities
- **Local Storage**: Automatic persistence with localStorage
- **Statistics**: Comprehensive project analytics and metrics
- **Import/Export**: Data portability with JSON export/import

#### Usage

```tsx
import { useProjectData } from '../hooks';

const ProjectManager = () => {
  const {
    projects,
    currentProject,
    createProject,
    updateProject,
    deleteProject,
    setCurrentProject,
    getProjectStats,
    getFilteredProjects,
    filterProjects,
    sortProjects,
    searchProjects,
  } = useProjectData();

  const handleCreateProject = () => {
    const newProject = createProject({
      name: 'My Learning Project',
      description: 'A project to learn React',
      status: 'active',
      tags: ['react', 'learning'],
      priority: 'high',
      estimatedDuration: 10,
      videoIds: [],
      notes: [],
      collaborators: [],
    });
    
    setCurrentProject(newProject);
  };

  const stats = getProjectStats();
  const filteredProjects = getFilteredProjects();

  return (
    <div>
      <div className="stats">
        <div>Total: {stats.total}</div>
        <div>Completed: {stats.completed}</div>
        <div>Active: {stats.active}</div>
        <div>Progress: {stats.averageProgress}%</div>
      </div>
      
      <button onClick={handleCreateProject}>Create Project</button>
      
      <div className="projects">
        {filteredProjects.map(project => (
          <div key={project.id} className="project">
            <h3>{project.name}</h3>
            <p>{project.description}</p>
            <div className="progress-bar" style={{ width: `${project.progress}%` }} />
            <button onClick={() => setCurrentProject(project)}>Select</button>
            <button onClick={() => deleteProject(project.id)}>Delete</button>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## 📤 File Upload Hook

### `useFileUpload(options?)`

A robust hook for managing file uploads with chunked uploads, progress tracking, and comprehensive error handling.

#### Features
- **Chunked Uploads**: Large file support with configurable chunk sizes
- **Progress Tracking**: Real-time upload progress for individual files
- **Concurrent Uploads**: Multiple simultaneous uploads
- **Error Handling**: Comprehensive error handling with retry mechanisms
- **File Validation**: Custom file validation support
- **Metadata Extraction**: Automatic file metadata extraction
- **Abort Support**: Cancel ongoing uploads

#### Usage

```tsx
import { useFileUpload } from '../hooks';

const FileUploader = () => {
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
    chunkSize: 1024 * 1024, // 1MB chunks
    concurrentUploads: 3,
    retryAttempts: 3,
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

  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    addFiles(selectedFiles);
  };

  const stats = getUploadStats();

  return (
    <div>
      <input type="file" multiple onChange={handleFileSelect} />
      
      <div className="stats">
        <div>Total: {stats.total}</div>
        <div>Uploading: {stats.uploading}</div>
        <div>Completed: {stats.completed}</div>
        <div>Failed: {stats.failed}</div>
      </div>
      
      {isUploading && (
        <div className="progress">
          <div className="progress-bar" style={{ width: `${totalProgress}%` }} />
          <p>{activeUploads} active uploads • {totalProgress}% complete</p>
        </div>
      )}
      
      <div className="files">
        {files.map(file => (
          <div key={file.id} className="file">
            <div className="file-info">
              <span>{file.name}</span>
              <span>{file.size} bytes</span>
              <span className={`status ${file.status}`}>{file.status}</span>
            </div>
            
            {file.status === 'uploading' && (
              <div className="file-progress">
                <div className="progress-bar" style={{ width: `${file.progress}%` }} />
                <span>{file.progress}%</span>
              </div>
            )}
            
            <div className="file-actions">
              {file.status === 'uploading' && (
                <button onClick={() => cancelUpload(file.id)}>Cancel</button>
              )}
              {file.status === 'failed' && (
                <button onClick={() => retryUpload(file.id)}>Retry</button>
              )}
              <button onClick={() => removeFile(file.id)}>Remove</button>
            </div>
          </div>
        ))}
      </div>
      
      <div className="actions">
        <button onClick={clearCompleted} disabled={completedUploads === 0}>
          Clear Completed
        </button>
        <button onClick={clearAll} disabled={files.length === 0}>
          Clear All
        </button>
      </div>
    </div>
  );
};
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `chunkSize` | `number` | `1024 * 1024` | Size of upload chunks in bytes |
| `concurrentUploads` | `number` | `3` | Maximum concurrent uploads |
| `retryAttempts` | `number` | `3` | Number of retry attempts on failure |
| `retryDelay` | `number` | `1000` | Delay between retries in milliseconds |
| `validateFile` | `function` | `() => true` | Custom file validation function |
| `onProgress` | `function` | `() => {}` | Progress callback |
| `onComplete` | `function` | `() => {}` | Completion callback |
| `onError` | `function` | `() => {}` | Error callback |

## 🔌 MCP Integration Hook

### `useMCPIntegration(options?)`

A comprehensive hook for integrating with MCP (Model Context Protocol) services with connection management and real-time updates.

#### Features
- **Connection Management**: Automatic connection handling with reconnection
- **Health Monitoring**: Real-time service health checks
- **Agent Management**: Track and manage MCP agents
- **System Metrics**: Monitor system performance and resources
- **Video Processing**: Integrated video processing capabilities
- **Chat Interface**: Real-time messaging with MCP services
- **Error Handling**: Comprehensive error handling and recovery

#### Usage

```tsx
import { useMCPIntegration } from '../hooks';

const MCPInterface = () => {
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
    autoReconnect: true,
    reconnectDelay: 5000,
    healthCheckInterval: 10000,
    onConnectionChange: (connected) => {
      console.log('Connection changed:', connected);
    },
    onError: (error) => {
      console.error('MCP error:', error);
    },
  });

  const handleSendMessage = async () => {
    if (messageText.trim()) {
      await sendMessage(messageText);
      setMessageText('');
    }
  };

  const handleProcessVideo = async () => {
    try {
      const result = await processVideo(videoUrl, {
        quality: 'high',
        format: 'mp4',
        includeTranscript: true,
        includeChapters: true,
      });
      console.log('Video processed:', result);
    } catch (error) {
      console.error('Video processing failed:', error);
    }
  };

  const systemHealth = getSystemHealth();

  return (
    <div>
      <div className="connection">
        <button onClick={connect} disabled={isConnecting || isConnected}>
          {isConnecting ? 'Connecting...' : isConnected ? 'Connected' : 'Connect'}
        </button>
        
        {isConnected && (
          <button onClick={disconnect}>Disconnect</button>
        )}
      </div>
      
      {connectionError && (
        <div className="error">Connection Error: {connectionError}</div>
      )}
      
      {isConnected && (
        <div>
          <div className="status">
            <div>Agents: {agentStatuses.length}</div>
            <div>System Health: {systemHealth}</div>
            <div>Messages: {messages.length}</div>
          </div>
          
          <div className="chat">
            <input
              type="text"
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="Type a message..."
            />
            <button onClick={handleSendMessage}>Send</button>
          </div>
          
          <div className="video-processing">
            <input
              type="text"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="Enter video URL"
            />
            <button onClick={handleProcessVideo} disabled={isProcessingVideo}>
              {isProcessingVideo ? 'Processing...' : 'Process Video'}
            </button>
          </div>
          
          {isProcessingVideo && (
            <div className="progress">
              <div className="progress-bar" style={{ width: `${videoProcessingProgress}%` }} />
              <p>{currentVideoTask}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `autoReconnect` | `boolean` | `true` | Automatically reconnect on disconnection |
| `reconnectDelay` | `number` | `5000` | Delay before reconnection attempts |
| `healthCheckInterval` | `number` | `10000` | Health check interval in milliseconds |
| `maxRetries` | `number` | `5` | Maximum reconnection attempts |
| `enableLogging` | `boolean` | `true` | Enable connection logging |
| `onConnectionChange` | `function` | `() => {}` | Connection state change callback |
| `onAgentUpdate` | `function` | `() => {}` | Agent status update callback |
| `onSystemMetricsUpdate` | `function` | `() => {}` | System metrics update callback |
| `onVideoProcessingComplete` | `function` | `() => {}` | Video processing completion callback |
| `onError` | `function` | `() => {}` | Error callback |

## 💾 Local Storage Hook

### `useLocalStorage(options)`

A powerful hook for managing local storage with encryption, compression, validation, and cross-tab synchronization.

#### Features
- **Type Safety**: Full TypeScript support with generic types
- **Encryption**: Optional encryption for sensitive data
- **Compression**: Data compression for large values
- **Validation**: Custom validation functions
- **Versioning**: Data version compatibility checking
- **TTL Support**: Time-to-live for data expiration
- **Cross-tab Sync**: Automatic synchronization across browser tabs
- **Import/Export**: Data portability with JSON export/import
- **Checksums**: Data integrity verification

#### Usage

```tsx
import { useLocalStorage } from '../hooks';

const DataManager = () => {
  const {
    value: storedData,
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
    key: 'user_preferences',
    defaultValue: {
      theme: 'light',
      language: 'en',
      notifications: true,
      autoSave: true,
    },
    version: '1.0.0',
    encrypt: true,
    compression: true,
    ttl: 24 * 60 * 60 * 1000, // 24 hours
    validate: (data) => {
      return data && typeof data === 'object' && 'theme' in data;
    },
    onError: (error) => console.error('Storage error:', error),
    onSync: (value) => console.log('Data synced:', value),
  });

  const handleThemeChange = (theme) => {
    setValue({ ...storedData, theme });
  };

  const handleImport = async (file) => {
    const success = await importData(file);
    if (success) {
      console.log('Data imported successfully');
    }
  };

  const storageInfo = getStorageInfo();

  return (
    <div>
      {isLoading && <div>Loading...</div>}
      
      {error && <div className="error">Error: {error}</div>}
      
      <div className="preferences">
        <div>
          <label>Theme:</label>
          <select value={storedData.theme} onChange={(e) => handleThemeChange(e.target.value)}>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="auto">Auto</option>
          </select>
        </div>
        
        <div>
          <label>Language:</label>
          <select value={storedData.language} onChange={(e) => setValue({ ...storedData, language: e.target.value })}>
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
          </select>
        </div>
        
        <div>
          <label>
            <input
              type="checkbox"
              checked={storedData.notifications}
              onChange={(e) => setValue({ ...storedData, notifications: e.target.checked })}
            />
            Enable Notifications
          </label>
        </div>
      </div>
      
      <div className="storage-info">
        <div>Size: {size} bytes</div>
        <div>Last Updated: {lastUpdated?.toLocaleString() || 'Never'}</div>
        <div>Stale: {isStale ? 'Yes' : 'No'}</div>
        {storageInfo && (
          <div>Age: {Math.round(storageInfo.age / 1000)}s</div>
        )}
      </div>
      
      <div className="actions">
        <button onClick={exportData}>Export Data</button>
        <button onClick={removeValue}>Remove Data</button>
        <button onClick={clearAll}>Clear All</button>
        <input type="file" accept=".json" onChange={(e) => handleImport(e.target.files[0])} />
      </div>
    </div>
  );
};
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `key` | `string` | **required** | Storage key (will be prefixed with 'uvai_') |
| `defaultValue` | `T` | **required** | Default value for the storage item |
| `version` | `string` | `'1.0.0'` | Data version for compatibility checking |
| `validate` | `function` | `undefined` | Custom validation function |
| `serialize` | `function` | `JSON.stringify` | Custom serialization function |
| `deserialize` | `function` | `JSON.parse` | Custom deserialization function |
| `encrypt` | `boolean` | `false` | Enable encryption |
| `encryptionKey` | `string` | `'uvai_default_key'` | Encryption key |
| `ttl` | `number` | `undefined` | Time-to-live in milliseconds |
| `compression` | `boolean` | `false` | Enable data compression |
| `onError` | `function` | `() => {}` | Error callback |
| `onSync` | `function` | `() => {}` | Sync callback |

## ⏱️ Debounce Hooks

### `useDebounce(value, delay)`

A simple hook for debouncing values with a specified delay.

### `useDebouncedCallback(callback, options)`

A hook for debouncing function calls with advanced options.

### `useDebouncedState(initialValue, delay)`

A hook that provides both immediate and debounced state values.

### `useDebouncedEffect(effect, dependencies, delay)`

A hook for debouncing useEffect dependencies.

### `useDebouncedAsyncCallback(callback, options)`

A hook for debouncing async function calls with success/error callbacks.

### `useDebouncedSearch(searchFunction, options)`

A specialized hook for debounced search functionality.

### `useDebouncedForm(initialValues, options)`

A hook for debounced form handling with validation.

#### Usage

```tsx
import {
  useDebounce,
  useDebouncedCallback,
  useDebouncedState,
  useDebouncedSearch,
  useDebouncedForm,
} from '../hooks';

const SearchInterface = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedQuery = useDebounce(searchQuery, 500);
  
  const [immediateValue, debouncedValue, setValue] = useDebouncedState('', 300);
  
  const debouncedCallback = useDebouncedCallback(
    (value) => {
      console.log('Debounced callback:', value);
    },
    { delay: 1000, leading: false, trailing: true }
  );
  
  const { search, results, isSearching, error } = useDebouncedSearch(
    async (query) => {
      const response = await fetch(`/api/search?q=${query}`);
      return response.json();
    },
    { delay: 500, minQueryLength: 2 }
  );
  
  const { values, errors, isValidating, setValue, submit } = useDebouncedForm(
    { name: '', email: '', message: '' },
    {
      delay: 1000,
      onSubmit: (values) => {
        console.log('Form submitted:', values);
      },
      onValidation: async (values) => {
        const errors = [];
        if (!values.name) errors.push('Name is required');
        if (!values.email) errors.push('Email is required');
        return errors.length > 0 ? errors : null;
      },
    }
  );
  
  const handleSearch = (query) => {
    setSearchQuery(query);
    search(query);
  };
  
  return (
    <div>
      <input
        type="text"
        placeholder="Search..."
        value={searchQuery}
        onChange={(e) => handleSearch(e.target.value)}
      />
      
      {isSearching && <div>Searching...</div>}
      
      {error && <div className="error">{error}</div>}
      
      <div className="results">
        {results.map(result => (
          <div key={result.id}>{result.title}</div>
        ))}
      </div>
      
      <div className="form">
        <input
          type="text"
          placeholder="Name"
          value={values.name}
          onChange={(e) => setValue('name', e.target.value)}
        />
        {errors.name && <span className="error">{errors.name}</span>}
        
        <button onClick={submit} disabled={isValidating}>
          {isValidating ? 'Validating...' : 'Submit'}
        </button>
      </div>
    </div>
  );
};
```

#### Debounce Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `delay` | `number` | **required** | Debounce delay in milliseconds |
| `leading` | `boolean` | `false` | Execute on leading edge |
| `trailing` | `boolean` | `true` | Execute on trailing edge |
| `maxWait` | `number` | `undefined` | Maximum wait time before execution |

## 🚀 Usage Examples

### Basic Hook Usage

```tsx
import { useVideoAnalysis, useProjectData } from '../hooks';

const VideoLearningApp = () => {
  const { analyzeVideo, isLoading, data } = useVideoAnalysis();
  const { createProject, projects } = useProjectData();
  
  const handleVideoAnalysis = async (url) => {
    try {
      const result = await analyzeVideo(url);
      createProject({
        name: result.summary,
        description: `Learning from: ${url}`,
        status: 'active',
        tags: result.topics,
        priority: 'medium',
        estimatedDuration: result.estimatedLearningTime / 60,
        videoIds: [url],
        notes: [],
        collaborators: [],
      });
    } catch (error) {
      console.error('Failed to analyze video:', error);
    }
  };
  
  return (
    <div>
      <button onClick={() => handleVideoAnalysis('https://youtube.com/watch?v=...')}>
        Analyze Video
      </button>
      
      {isLoading && <div>Analyzing...</div>}
      
      {data && (
        <div>
          <h2>Analysis Results</h2>
          <p>{data.summary}</p>
          <ul>
            {data.keyPoints.map(point => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      )}
      
      <div>
        <h2>Projects ({projects.length})</h2>
        {projects.map(project => (
          <div key={project.id}>
            <h3>{project.name}</h3>
            <p>{project.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### Advanced Hook Composition

```tsx
import { useVideoAnalysis, useFileUpload, useMCPIntegration } from '../hooks';

const AdvancedVideoProcessor = () => {
  const { analyzeVideo, isLoading: isAnalyzing } = useVideoAnalysis();
  const { addFiles, files, isUploading } = useFileUpload();
  const { processVideo, isProcessingVideo } = useMCPIntegration();
  
  const handleFileUpload = async (uploadedFiles) => {
    // Process uploaded video files
    for (const file of uploadedFiles) {
      if (file.status === 'completed') {
        try {
          // Analyze with local hook
          const analysis = await analyzeVideo(file.url);
          
          // Process with MCP service
          const result = await processVideo(file.url, {
            quality: 'high',
            includeTranscript: true,
            includeChapters: true,
          });
          
          console.log('Processing complete:', { analysis, result });
        } catch (error) {
          console.error('Processing failed:', error);
        }
      }
    }
  };
  
  return (
    <div>
      <input
        type="file"
        multiple
        accept="video/*"
        onChange={(e) => addFiles(Array.from(e.target.files || []))}
      />
      
      {(isUploading || isAnalyzing || isProcessingVideo) && (
        <div className="status">
          {isUploading && <span>Uploading...</span>}
          {isAnalyzing && <span>Analyzing...</span>}
          {isProcessingVideo && <span>Processing...</span>}
        </div>
      )}
      
      <div className="files">
        {files.map(file => (
          <div key={file.id} className={`file ${file.status}`}>
            <span>{file.name}</span>
            <span>{file.status}</span>
            {file.progress > 0 && (
              <div className="progress" style={{ width: `${file.progress}%` }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

## 🎯 Best Practices

### 1. Hook Composition
- Combine multiple hooks to create complex functionality
- Use custom hooks to abstract business logic
- Keep hooks focused on single responsibilities

### 2. Error Handling
- Always implement error boundaries for hook errors
- Use try-catch blocks for async operations
- Provide meaningful error messages to users

### 3. Performance Optimization
- Use `useCallback` and `useMemo` for expensive operations
- Implement proper cleanup in useEffect hooks
- Avoid unnecessary re-renders with proper dependency arrays

### 4. Type Safety
- Define comprehensive interfaces for all data structures
- Use generic types for flexible hook implementations
- Provide proper TypeScript types for all hook parameters

### 5. Testing
- Test hooks in isolation using React Testing Library
- Mock external dependencies and API calls
- Test error scenarios and edge cases

### 6. Accessibility
- Ensure hooks work with screen readers
- Provide proper ARIA labels and descriptions
- Support keyboard navigation where applicable

## 🔧 Development

### Adding New Hooks

1. Create a new file in the `hooks/` directory
2. Implement the hook with proper TypeScript interfaces
3. Add comprehensive JSDoc documentation
4. Include usage examples and edge cases
5. Update the `index.ts` file to export the new hook
6. Add the hook to the demo page for testing

### Testing Hooks

```tsx
import { renderHook, act } from '@testing-library/react';
import { useVideoAnalysis } from '../hooks';

describe('useVideoAnalysis', () => {
  it('should initialize with default state', () => {
    const { result } = renderHook(() => useVideoAnalysis());
    
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.data).toBe(null);
  });
  
  it('should handle video analysis', async () => {
    const { result } = renderHook(() => useVideoAnalysis());
    
    await act(async () => {
      await result.current.analyzeVideo('https://youtube.com/watch?v=...');
    });
    
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeDefined();
  });
});
```

## 📖 Additional Resources

- [React Hooks Documentation](https://reactjs.org/docs/hooks-intro.html)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Custom Hooks Best Practices](https://reactjs.org/docs/hooks-custom.html)

## 🤝 Contributing

When contributing to these hooks:

1. Follow the existing code style and patterns
2. Add comprehensive TypeScript interfaces
3. Include JSDoc documentation for all functions
4. Write tests for new functionality
5. Update the demo page with examples
6. Ensure backward compatibility

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
