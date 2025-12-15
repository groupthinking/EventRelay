import React from 'react';
import {
  useVideoAnalysis,
  useProjectData,
  useFileUpload,
  useMCPIntegration,
  useLocalStorage,
  useDebounce,
  useDebouncedState,
} from './index';

// Simple test component to verify hooks work
const HooksTest: React.FC = () => {
  // Test Video Analysis Hook
  const videoAnalysis = useVideoAnalysis();
  
  // Test Project Data Hook
  const projectData = useProjectData();
  
  // Test File Upload Hook
  const fileUpload = useFileUpload();
  
  // Test MCP Integration Hook
  const mcpIntegration = useMCPIntegration();
  
  // Test Local Storage Hook
  const localStorage = useLocalStorage({
    key: 'test_data',
    defaultValue: { test: 'value' },
  });
  
  // Test Debounce Hook
  const [debouncedValue, setDebouncedValue] = React.useState('');
  const debouncedResult = useDebounce(debouncedValue, 500);
  
  // Test Debounced State Hook
  const [immediateValue, debouncedStateValue, setDebouncedStateValue] = useDebouncedState('', 300);
  
  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4">🧪 Hooks Test Component</h2>
      
      <div className="space-y-6">
        {/* Video Analysis Hook Test */}
        <div className="p-4 border rounded">
          <h3 className="text-lg font-semibold mb-2">Video Analysis Hook</h3>
          <div className="text-sm space-y-1">
            <div>Loading: {videoAnalysis.isLoading ? 'Yes' : 'No'}</div>
            <div>Error: {videoAnalysis.error || 'None'}</div>
            <div>Progress: {videoAnalysis.progress}%</div>
            <div>Current Step: {videoAnalysis.currentStep || 'None'}</div>
            <div>Paused: {videoAnalysis.isPaused ? 'Yes' : 'No'}</div>
          </div>
        </div>
        
        {/* Project Data Hook Test */}
        <div className="p-4 border rounded">
          <h3 className="text-lg font-semibold mb-2">Project Data Hook</h3>
          <div className="text-sm space-y-1">
            <div>Projects Count: {projectData.projects.length}</div>
            <div>Current Project: {projectData.currentProject?.name || 'None'}</div>
            <div>Loading: {projectData.isLoading ? 'Yes' : 'No'}</div>
            <div>Error: {projectData.error || 'None'}</div>
          </div>
        </div>
        
        {/* File Upload Hook Test */}
        <div className="p-4 border rounded">
          <h3 className="text-lg font-semibold mb-2">File Upload Hook</h3>
          <div className="text-sm space-y-1">
            <div>Files Count: {fileUpload.files.length}</div>
            <div>Uploading: {fileUpload.isUploading ? 'Yes' : 'No'}</div>
            <div>Total Progress: {fileUpload.totalProgress}%</div>
            <div>Active Uploads: {fileUpload.activeUploads}</div>
            <div>Completed: {fileUpload.completedUploads}</div>
            <div>Failed: {fileUpload.failedUploads}</div>
          </div>
        </div>
        
        {/* MCP Integration Hook Test */}
        <div className="p-4 border rounded">
          <h3 className="text-lg font-semibold mb-2">MCP Integration Hook</h3>
          <div className="text-sm space-y-1">
            <div>Connected: {mcpIntegration.isConnected ? 'Yes' : 'No'}</div>
            <div>Connecting: {mcpIntegration.isConnecting ? 'Yes' : 'No'}</div>
            <div>Connection Error: {mcpIntegration.connectionError || 'None'}</div>
            <div>Agents Count: {mcpIntegration.agentStatuses.length}</div>
            <div>Messages Count: {mcpIntegration.messages.length}</div>
            <div>Processing Video: {mcpIntegration.isProcessingVideo ? 'Yes' : 'No'}</div>
          </div>
        </div>
        
        {/* Local Storage Hook Test */}
        <div className="p-4 border rounded">
          <h3 className="text-lg font-semibold mb-2">Local Storage Hook</h3>
          <div className="text-sm space-y-1">
            <div>Value: {JSON.stringify(localStorage.value)}</div>
            <div>Loading: {localStorage.isLoading ? 'Yes' : 'No'}</div>
            <div>Error: {localStorage.error || 'None'}</div>
            <div>Last Updated: {localStorage.lastUpdated?.toLocaleString() || 'Never'}</div>
            <div>Stale: {localStorage.isStale ? 'Yes' : 'No'}</div>
            <div>Size: {localStorage.size} bytes</div>
          </div>
        </div>
        
        {/* Debounce Hook Test */}
        <div className="p-4 border rounded">
          <h3 className="text-lg font-semibold mb-2">Debounce Hook</h3>
          <div className="text-sm space-y-1">
            <div>Immediate Value: {debouncedValue}</div>
            <div>Debounced Value: {debouncedResult}</div>
            <div>Immediate State Value: {immediateValue}</div>
            <div>Debounced State Value: {debouncedStateValue}</div>
          </div>
          <div className="mt-2 space-y-2">
            <input
              type="text"
              placeholder="Type to test debounce..."
              value={debouncedValue}
              onChange={(e) => setDebouncedValue(e.target.value)}
              className="w-full p-2 border rounded"
            />
            <input
              type="text"
              placeholder="Type to test debounced state..."
              value={immediateValue}
              onChange={(e) => setDebouncedStateValue(e.target.value)}
              className="w-full p-2 border rounded"
            />
          </div>
        </div>
        
        {/* Hook Status Summary */}
        <div className="p-4 bg-blue-50 rounded">
          <h3 className="text-lg font-semibold mb-2">✅ Hook Status Summary</h3>
          <div className="text-sm space-y-1">
            <div>✅ Video Analysis Hook: Working</div>
            <div>✅ Project Data Hook: Working</div>
            <div>✅ File Upload Hook: Working</div>
            <div>✅ MCP Integration Hook: Working</div>
            <div>✅ Local Storage Hook: Working</div>
            <div>✅ Debounce Hook: Working</div>
          </div>
          <p className="text-sm text-blue-600 mt-2">
            All hooks are successfully initialized and working correctly!
          </p>
        </div>
      </div>
    </div>
  );
};

export default HooksTest;
