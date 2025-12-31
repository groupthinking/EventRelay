# Phase 3-6: UI Components, State, Testing & Documentation - Copilot Prompts

## Phase 3: Core Integration Features

### Prompt 3.1: Video URL Input Component

```
Create a video input component for EventRelay workflow.

Context:
- Working in: apps/web/src/components/VideoInput.tsx (create new file)
- Using: React, TypeScript, videoService
- Goal: User can paste YouTube URL and start processing

Requirements:

1. Input form with validation:
   - Text input for YouTube URL
   - Submit button
   - URL format validation
   - Loading state during submission
   - Error message display

2. Integration with videoService:
   - Call processVideo on submit
   - Handle success/error responses
   - Pass job_id to parent component

3. User feedback:
   - Disable button while loading
   - Show spinner or loading text
   - Display validation errors inline
   - Clear error on input change

Implementation:
```typescript
// apps/web/src/components/VideoInput.tsx
'use client';

import { useState, FormEvent } from 'react';
import { videoService } from '@/services/video-service';
import { VideoProcessResponse } from '@/types';

interface VideoInputProps {
  onSubmit: (response: VideoProcessResponse) => void;
  onError?: (error: string) => void;
}

export function VideoInput({ onSubmit, onError }: VideoInputProps) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateUrl = (url: string): boolean => {
    if (!url.trim()) {
      setError('Please enter a YouTube URL');
      return false;
    }

    const videoId = videoService.extractVideoId(url);
    if (!videoId) {
      setError('Invalid YouTube URL format');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateUrl(url)) {
      return;
    }

    setLoading(true);

    try {
      const response = await videoService.processVideo(url);
      setUrl(''); // Clear input on success
      onSubmit(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process video';
      setError(message);
      onError?.(message);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (value: string) => {
    setUrl(value);
    if (error) {
      setError(null); // Clear error on input change
    }
  };

  return (
    <div className="video-input">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label htmlFor="video-url" className="block text-sm font-medium mb-2">
            YouTube Video URL
          </label>
          <input
            id="video-url"
            type="text"
            value={url}
            onChange={(e) => handleInputChange(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
            aria-invalid={!!error}
            aria-describedby={error ? 'url-error' : undefined}
          />
          {error && (
            <p id="url-error" className="mt-1 text-sm text-red-600">
              {error}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <Spinner />
              Processing...
            </span>
          ) : (
            'Process Video'
          )}
        </button>
      </form>

      <div className="mt-4 text-sm text-gray-600">
        <p>Example: https://youtube.com/watch?v=auJzb1D-fag</p>
      </div>
    </div>
  );
}

// Simple spinner component
function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
```

Styling (if using CSS modules):
```css
/* apps/web/src/components/VideoInput.module.css */
.videoInput {
  max-width: 600px;
  margin: 0 auto;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input:disabled {
  background-color: #f9fafb;
  cursor: not-allowed;
}

.error {
  color: #dc2626;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.button {
  padding: 0.75rem 1.5rem;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.button:hover:not(:disabled) {
  background-color: #2563eb;
}

.button:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}
```
```

---

### Prompt 3.2: Video Status Display Component

```
Create a component to display video processing status and results.

Context:
- Working in: apps/web/src/components/VideoStatus.tsx (create new file)
- Using: React, TypeScript, videoService
- Goal: Show processing progress and final results

Implementation:
```typescript
// apps/web/src/components/VideoStatus.tsx
'use client';

import { useEffect, useState } from 'react';
import { videoService } from '@/services/video-service';
import { VideoStatusResponse } from '@/types';

interface VideoStatusProps {
  jobId: string;
  onComplete?: (status: VideoStatusResponse) => void;
}

export function VideoStatus({ jobId, onComplete }: VideoStatusProps) {
  const [status, setStatus] = useState<VideoStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const pollStatus = async () => {
      try {
        const result = await videoService.pollUntilComplete(
          jobId,
          (progress) => {
            if (!cancelled) {
              setStatus(progress);
              setLoading(false);
            }
          }
        );

        if (!cancelled) {
          setStatus(result);
          setLoading(false);
          onComplete?.(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to get status');
          setLoading(false);
        }
      }
    };

    pollStatus();

    return () => {
      cancelled = true;
    };
  }, [jobId, onComplete]);

  if (loading && !status) {
    return (
      <div className="video-status">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-status error">
        <h3 className="text-lg font-semibold text-red-600">Error</h3>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <div className="video-status">
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-semibold">Processing Status</h3>
          <StatusBadge status={status.status} />
        </div>

        {status.metadata && (
          <div className="text-sm text-gray-600">
            <p className="font-medium">{status.metadata.title}</p>
            <p>{status.metadata.channel}</p>
          </div>
        )}
      </div>

      {status.status === 'processing' && (
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span>Progress</span>
            <span>{status.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${status.progress}%` }}
            />
          </div>
        </div>
      )}

      {status.status === 'completed' && status.transcript && (
        <div className="mt-4">
          <h4 className="font-medium mb-2">Transcript</h4>
          <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="text-sm whitespace-pre-wrap">{status.transcript}</pre>
          </div>
        </div>
      )}

      {status.status === 'failed' && status.error && (
        <div className="mt-4 p-4 bg-red-50 rounded-lg">
          <p className="text-red-600">{status.error}</p>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status as keyof typeof colors] || 'bg-gray-100'}`}>
      {status}
    </span>
  );
}
```
```

---

### Prompt 3.3: Event List Component

```
Create a component to display extracted events.

Implementation:
```typescript
// apps/web/src/components/EventList.tsx
'use client';

import { useState, useMemo } from 'react';
import { Event, EventType } from '@/types';
import { eventService } from '@/services/event-service';

interface EventListProps {
  events: Event[];
  onEventSelect?: (event: Event) => void;
}

export function EventList({ events, onEventSelect }: EventListProps) {
  const [filter, setFilter] = useState<EventType | 'all'>('all');
  const [sortBy, setSortBy] = useState<'timestamp' | 'confidence'>('timestamp');

  const filteredAndSorted = useMemo(() => {
    let result = events;

    // Apply filter
    if (filter !== 'all') {
      result = eventService.filterByType(result, filter);
    }

    // Apply sort
    if (sortBy === 'timestamp') {
      result = eventService.sortByTimestamp(result);
    } else {
      result = eventService.sortByConfidence(result);
    }

    return result;
  }, [events, filter, sortBy]);

  const eventsByType = useMemo(() => {
    return eventService.groupByType(events);
  }, [events]);

  return (
    <div className="event-list">
      <div className="mb-4">
        <h3 className="text-lg font-semibold mb-2">
          Extracted Events ({events.length})
        </h3>

        <div className="flex gap-4 mb-4">
          <div>
            <label className="text-sm text-gray-600 mr-2">Filter:</label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as EventType | 'all')}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="all">All Types</option>
              {Object.values(EventType).map((type) => (
                <option key={type} value={type}>
                  {type} ({eventsByType[type]?.length || 0})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm text-gray-600 mr-2">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'timestamp' | 'confidence')}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="timestamp">Timestamp</option>
              <option value="confidence">Confidence</option>
            </select>
          </div>
        </div>
      </div>

      {filteredAndSorted.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No events found
        </div>
      ) : (
        <div className="space-y-2">
          {filteredAndSorted.map((event) => (
            <EventCard
              key={event.id}
              event={event}
              onClick={() => onEventSelect?.(event)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface EventCardProps {
  event: Event;
  onClick: () => void;
}

function EventCard({ event, onClick }: EventCardProps) {
  const timestamp = eventService.formatTimestamp(event.timestamp);

  return (
    <div
      className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition"
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <EventTypeIcon type={event.type} />
          <span className="text-xs font-medium text-gray-500 uppercase">
            {event.type}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{timestamp}</span>
          <ConfidenceBadge confidence={event.confidence} />
        </div>
      </div>

      <p className="text-sm">{event.description}</p>

      {Object.keys(event.metadata).length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          {Object.entries(event.metadata).map(([key, value]) => (
            <span key={key} className="mr-3">
              {key}: {String(value)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function EventTypeIcon({ type }: { type: EventType }) {
  const icons = {
    [EventType.ACTION]: '⚡',
    [EventType.MENTION]: '💬',
    [EventType.TOPIC]: '📌',
    [EventType.DECISION]: '✓',
    [EventType.QUESTION]: '❓',
    [EventType.INSTRUCTION]: '📋',
  };

  return <span className="text-lg">{icons[type] || '•'}</span>;
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percentage = Math.round(confidence * 100);
  const color =
    confidence >= 0.8
      ? 'bg-green-100 text-green-800'
      : confidence >= 0.5
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800';

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {percentage}%
    </span>
  );
}
```
```

---

### Prompt 3.4: Agent Dashboard Component

```
Create a dashboard to display agent execution status.

Implementation:
```typescript
// apps/web/src/components/AgentDashboard.tsx
'use client';

import { useEffect, useState } from 'react';
import { agentService } from '@/services/agent-service';
import { AgentExecution, AgentType } from '@/types';

interface AgentDashboardProps {
  agentIds: string[];
  onComplete?: (results: Map<string, AgentExecution>) => void;
}

export function AgentDashboard({ agentIds, onComplete }: AgentDashboardProps) {
  const [agents, setAgents] = useState<Map<string, AgentExecution>>(new Map());
  const [monitoring, setMonitoring] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const monitor = async () => {
      try {
        const results = await agentService.monitorAgents(
          agentIds,
          (statuses) => {
            if (!cancelled) {
              setAgents(new Map(statuses));
            }
          }
        );

        if (!cancelled) {
          setAgents(results);
          setMonitoring(false);
          onComplete?.(results);
        }
      } catch (err) {
        console.error('Agent monitoring error:', err);
        if (!cancelled) {
          setMonitoring(false);
        }
      }
    };

    monitor();

    return () => {
      cancelled = true;
    };
  }, [agentIds, onComplete]);

  const agentList = Array.from(agents.values());
  const completed = agentList.filter(a => a.status === 'completed').length;
  const failed = agentList.filter(a => a.status === 'failed').length;

  return (
    <div className="agent-dashboard">
      <div className="mb-4">
        <h3 className="text-lg font-semibold mb-2">
          Agent Execution Status
        </h3>
        <div className="flex gap-4 text-sm">
          <span>Total: {agentList.length}</span>
          <span className="text-green-600">Completed: {completed}</span>
          <span className="text-red-600">Failed: {failed}</span>
          {monitoring && <span className="text-blue-600">Monitoring...</span>}
        </div>
      </div>

      <div className="space-y-3">
        {agentList.map((agent) => (
          <AgentCard key={agent.agent_id} agent={agent} />
        ))}
      </div>
    </div>
  );
}

interface AgentCardProps {
  agent: AgentExecution;
}

function AgentCard({ agent }: AgentCardProps) {
  return (
    <div className="p-4 border rounded-lg">
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <AgentIcon type={agent.agent_type} />
            <span className="font-medium">{formatAgentType(agent.agent_type)}</span>
          </div>
          <span className="text-xs text-gray-500">{agent.agent_id}</span>
        </div>
        <AgentStatusBadge status={agent.status} />
      </div>

      {agent.status === 'running' && (
        <div className="mb-3">
          <div className="flex justify-between text-sm mb-1">
            <span>Progress</span>
            <span>{agent.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${agent.progress}%` }}
            />
          </div>
        </div>
      )}

      {agent.error && (
        <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-600">
          {agent.error}
        </div>
      )}

      {agent.started_at && (
        <div className="text-xs text-gray-500 mt-2">
          Started: {new Date(agent.started_at).toLocaleString()}
          {agent.completed_at && (
            <> • Completed: {new Date(agent.completed_at).toLocaleString()}</>
          )}
        </div>
      )}
    </div>
  );
}

function AgentIcon({ type }: { type: AgentType }) {
  const icons = {
    [AgentType.CODE_GENERATOR]: '💻',
    [AgentType.CONTENT_CREATOR]: '✍️',
    [AgentType.WORKFLOW_TRIGGER]: '🔄',
    [AgentType.DATA_ANALYZER]: '📊',
  };

  return <span className="text-xl">{icons[type] || '🤖'}</span>;
}

function AgentStatusBadge({ status }: { status: string }) {
  const colors = {
    queued: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status as keyof typeof colors]}`}>
      {status}
    </span>
  );
}

function formatAgentType(type: AgentType): string {
  return type.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}
```
```

---

## Phase 4: State Management

### Prompt 4.1: Zustand Store Setup

```
Setup Zustand for state management.

Context:
- Working in: apps/web/src/store/ (create directory)
- Using: Zustand library
- Goal: Centralized state for video processing workflow

Installation:
```bash
cd apps/web
npm install zustand
```

Implementation:
```typescript
// apps/web/src/store/use-app-store.ts

import create from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import {
  VideoStatusResponse,
  Event,
  AgentExecution,
} from '@/types';

interface VideoState {
  jobId: string | null;
  videoId: string | null;
  status: VideoStatusResponse | null;
  error: string | null;
}

interface EventState {
  events: Event[];
  selectedEvent: Event | null;
}

interface AgentState {
  agents: Map<string, AgentExecution>;
  activeCount: number;
}

interface AppState {
  // Video state
  video: VideoState;
  setVideoJob: (jobId: string, videoId: string) => void;
  setVideoStatus: (status: VideoStatusResponse) => void;
  setVideoError: (error: string) => void;
  clearVideo: () => void;

  // Event state
  events: EventState;
  setEvents: (events: Event[]) => void;
  selectEvent: (event: Event | null) => void;
  addEvent: (event: Event) => void;

  // Agent state
  agents: AgentState;
  setAgentStatus: (agentId: string, status: AgentExecution) => void;
  updateAgents: (agents: Map<string, AgentExecution>) => void;
  clearAgents: () => void;

  // Global actions
  reset: () => void;
}

const initialState = {
  video: {
    jobId: null,
    videoId: null,
    status: null,
    error: null,
  },
  events: {
    events: [],
    selectedEvent: null,
  },
  agents: {
    agents: new Map(),
    activeCount: 0,
  },
};

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        ...initialState,

        // Video actions
        setVideoJob: (jobId, videoId) =>
          set((state) => ({
            video: { ...state.video, jobId, videoId, error: null },
          })),

        setVideoStatus: (status) =>
          set((state) => ({
            video: { ...state.video, status },
          })),

        setVideoError: (error) =>
          set((state) => ({
            video: { ...state.video, error },
          })),

        clearVideo: () =>
          set((state) => ({
            video: initialState.video,
          })),

        // Event actions
        setEvents: (events) =>
          set((state) => ({
            events: { ...state.events, events },
          })),

        selectEvent: (event) =>
          set((state) => ({
            events: { ...state.events, selectedEvent: event },
          })),

        addEvent: (event) =>
          set((state) => ({
            events: {
              ...state.events,
              events: [...state.events.events, event],
            },
          })),

        // Agent actions
        setAgentStatus: (agentId, status) =>
          set((state) => {
            const newAgents = new Map(state.agents.agents);
            newAgents.set(agentId, status);

            return {
              agents: {
                agents: newAgents,
                activeCount: Array.from(newAgents.values()).filter(
                  (a) => a.status === 'running' || a.status === 'queued'
                ).length,
              },
            };
          }),

        updateAgents: (agents) =>
          set(() => ({
            agents: {
              agents,
              activeCount: Array.from(agents.values()).filter(
                (a) => a.status === 'running' || a.status === 'queued'
              ).length,
            },
          })),

        clearAgents: () =>
          set((state) => ({
            agents: initialState.agents,
          })),

        // Global reset
        reset: () => set(initialState),
      }),
      {
        name: 'eventrelay-storage',
        partialize: (state) => ({
          // Only persist certain parts
          video: state.video,
        }),
      }
    )
  )
);

// Selectors
export const selectVideoStatus = (state: AppState) => state.video.status;
export const selectEvents = (state: AppState) => state.events.events;
export const selectActiveAgents = (state: AppState) =>
  Array.from(state.agents.agents.values()).filter(
    (a) => a.status === 'running' || a.status === 'queued'
  );
```

Usage in components:
```typescript
'use client';

import { useAppStore, selectVideoStatus } from '@/store/use-app-store';

export function MyComponent() {
  const videoStatus = useAppStore(selectVideoStatus);
  const setVideoStatus = useAppStore((state) => state.setVideoStatus);
  const events = useAppStore((state) => state.events.events);

  // Component logic
}
```
```

---

## Phase 5: Testing & Validation

### Prompt 5.1: Backend API Tests

```
Create comprehensive tests for backend API endpoints.

Context:
- Working in: tests/api/ (create directory)
- Using: pytest, FastAPI TestClient
- Goal: Validate all API endpoints work correctly

Implementation:
```python
# tests/api/test_video_endpoints.py

import pytest
from fastapi.testclient import TestClient
from src.uvai.api.main import app

client = TestClient(app)

class TestVideoEndpoints:
    """Test video processing endpoints"""

    def test_process_video_success(self):
        """Test successful video processing initiation"""
        response = client.post(
            "/api/v1/videos/process",
            json={
                "video_url": "https://youtube.com/watch?v=auJzb1D-fag"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "job_id" in data["data"]
        assert "video_id" in data["data"]
        assert data["data"]["video_id"] == "auJzb1D-fag"

    def test_process_video_invalid_url(self):
        """Test video processing with invalid URL"""
        response = client.post(
            "/api/v1/videos/process",
            json={"video_url": "https://example.com/not-youtube"}
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert data["status"] == "error"

    def test_get_video_status(self):
        """Test retrieving video processing status"""
        # First create a job
        process_response = client.post(
            "/api/v1/videos/process",
            json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"}
        )
        job_id = process_response.json()["data"]["job_id"]

        # Then get status
        response = client.get(f"/api/v1/videos/{job_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["job_id"] == job_id
        assert data["data"]["status"] in ["pending", "processing", "completed", "failed"]

    def test_get_video_status_not_found(self):
        """Test getting status for non-existent job"""
        response = client.get("/api/v1/videos/nonexistent-job-id/status")

        assert response.status_code == 404


# tests/api/test_event_endpoints.py

class TestEventEndpoints:
    """Test event extraction endpoints"""

    def test_extract_events_from_transcript(self):
        """Test event extraction from transcript text"""
        transcript = """
        In this video, I will demonstrate three key concepts.
        First, we'll discuss the importance of testing.
        Second, I'll show you how to implement it.
        Finally, we'll review the best practices.
        """

        response = client.post(
            "/api/v1/events/extract",
            json={"transcript": transcript}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "events" in data["data"]
        assert len(data["data"]["events"]) > 0

    def test_list_events_for_video(self):
        """Test listing events for a video"""
        video_id = "auJzb1D-fag"

        response = client.get(
            f"/api/v1/events?video_id={video_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "items" in data["data"]


# tests/api/test_agent_endpoints.py

class TestAgentEndpoints:
    """Test agent dispatch endpoints"""

    def test_dispatch_agents(self):
        """Test dispatching agents for events"""
        response = client.post(
            "/api/v1/agents/dispatch",
            json={
                "video_id": "auJzb1D-fag",
                "events": ["event-1", "event-2"],
                "agents": [
                    {
                        "agent_type": "code_generator",
                        "parameters": {},
                        "priority": 5
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "executions" in data["data"]
        assert len(data["data"]["executions"]) > 0

    def test_get_agent_status(self):
        """Test getting agent execution status"""
        # First dispatch an agent
        dispatch_response = client.post(
            "/api/v1/agents/dispatch",
            json={
                "video_id": "auJzb1D-fag",
                "events": ["event-1"],
                "agents": [{"agent_type": "code_generator"}]
            }
        )
        agent_id = dispatch_response.json()["data"]["executions"][0]["agent_id"]

        # Then get status
        response = client.get(f"/api/v1/agents/{agent_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["agent_id"] == agent_id


# tests/api/test_health_endpoints.py

class TestHealthEndpoints:
    """Test health and monitoring endpoints"""

    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in data

    def test_system_status(self):
        """Test system status endpoint"""
        response = client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "uptime_seconds" in data["data"]
        assert "cpu_percent" in data["data"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

Run tests:
```bash
cd /home/runner/work/EventRelay/EventRelay
pytest tests/api/ -v --cov
```
```

---

### Prompt 5.2: Frontend Component Tests

```
Create tests for React components.

Context:
- Working in: apps/web/src/__tests__/ (create directory)
- Using: Jest, React Testing Library
- Goal: Test components in isolation

Installation:
```bash
cd apps/web
npm install --save-dev @testing-library/react @testing-library/jest-dom @testing-library/user-event jest jest-environment-jsdom
```

Configuration:
```javascript
// apps/web/jest.config.js
const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};

module.exports = createJestConfig(customJestConfig);
```

```typescript
// apps/web/jest.setup.js
import '@testing-library/jest-dom';
```

Tests:
```typescript
// apps/web/src/__tests__/components/VideoInput.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VideoInput } from '@/components/VideoInput';
import { videoService } from '@/services/video-service';

jest.mock('@/services/video-service');

describe('VideoInput', () => {
  const mockOnSubmit = jest.fn();
  const mockOnError = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders input and button', () => {
    render(<VideoInput onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText(/youtube video url/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /process video/i })).toBeInTheDocument();
  });

  it('validates empty URL', async () => {
    render(<VideoInput onSubmit={mockOnSubmit} onError={mockOnError} />);

    const button = screen.getByRole('button', { name: /process video/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/please enter a youtube url/i)).toBeInTheDocument();
    });
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('validates invalid URL format', async () => {
    (videoService.extractVideoId as jest.Mock).mockReturnValue(null);

    render(<VideoInput onSubmit={mockOnSubmit} onError={mockOnError} />);

    const input = screen.getByLabelText(/youtube video url/i);
    await userEvent.type(input, 'https://example.com/not-youtube');

    const button = screen.getByRole('button', { name: /process video/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/invalid youtube url format/i)).toBeInTheDocument();
    });
  });

  it('submits valid URL', async () => {
    const mockResponse = {
      job_id: 'job-123',
      video_id: 'auJzb1D-fag',
      status: 'pending',
      created_at: new Date().toISOString(),
    };

    (videoService.extractVideoId as jest.Mock).mockReturnValue('auJzb1D-fag');
    (videoService.processVideo as jest.Mock).mockResolvedValue(mockResponse);

    render(<VideoInput onSubmit={mockOnSubmit} />);

    const input = screen.getByLabelText(/youtube video url/i);
    await userEvent.type(input, 'https://youtube.com/watch?v=auJzb1D-fag');

    const button = screen.getByRole('button', { name: /process video/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(mockResponse);
    });
  });

  it('shows loading state during submission', async () => {
    (videoService.extractVideoId as jest.Mock).mockReturnValue('auJzb1D-fag');
    (videoService.processVideo as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(<VideoInput onSubmit={mockOnSubmit} />);

    const input = screen.getByLabelText(/youtube video url/i);
    await userEvent.type(input, 'https://youtube.com/watch?v=auJzb1D-fag');

    const button = screen.getByRole('button', { name: /process video/i });
    fireEvent.click(button);

    expect(screen.getByText(/processing.../i)).toBeInTheDocument();
    expect(button).toBeDisabled();
  });
});
```

Run tests:
```bash
cd apps/web
npm test
```
```

---

## Phase 6: Documentation & Polish

### Prompt 6.1: API Documentation

```
Enhance OpenAPI documentation for all endpoints.

Context:
- Working in: Backend endpoint files
- Using: FastAPI OpenAPI features
- Goal: Complete, accurate API documentation

Add comprehensive docstrings and examples to all endpoints:

```python
@router.post(
    "/process",
    response_model=APIResponse[VideoProcessResponse],
    summary="Process YouTube video",
    description="""
    Submit a YouTube video URL for processing.
    
    This endpoint initiates an asynchronous processing job that:
    1. Downloads video metadata
    2. Extracts and transcribes audio
    3. Parses transcript into structured text
    4. Prepares for event extraction
    
    The response includes a job_id that can be used to poll for status.
    
    **Rate Limit:** 10 requests per minute
    
    **Processing Time:** Typically 30-120 seconds depending on video length
    """,
    responses={
        200: {
            "description": "Video processing job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "job_id": "550e8400-e29b-41d4-a716-446655440000",
                            "video_id": "auJzb1D-fag",
                            "status": "pending",
                            "created_at": "2024-01-01T12:00:00Z"
                        },
                        "timestamp": "2024-01-01T12:00:00Z",
                        "request_id": "req_123456789"
                    }
                }
            }
        },
        422: {
            "description": "Invalid request format",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "error": "Validation Error",
                        "detail": "Must be a valid YouTube URL",
                        "request_id": "req_123456789"
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded"
        }
    },
    tags=["Video Processing"]
)
async def process_video(request: VideoProcessRequest):
    """Process a YouTube video"""
    # Implementation
    pass
```

Regenerate docs and verify at http://localhost:8000/docs
```

---

### Prompt 6.2: Complete README

```
Update project README with complete integration guide.

Add to README.md:

```markdown
## 🎯 Complete Setup Guide

### Quick Start (5 minutes)

1. **Clone and setup backend:**
   ```bash
   git clone https://github.com/groupthinking/EventRelay.git
   cd EventRelay
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev,youtube,ml]
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Start backend:**
   ```bash
   uvicorn uvai.api.main:app --reload --port 8000
   ```

4. **Setup frontend (new terminal):**
   ```bash
   cd apps/web
   npm install
   cp .env.local.example .env.local
   # Edit .env.local if needed
   ```

5. **Start frontend:**
   ```bash
   npm run dev
   ```

6. **Access application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Testing the Integration

1. Open http://localhost:3000
2. Paste a YouTube URL (try: https://youtube.com/watch?v=auJzb1D-fag)
3. Click "Process Video"
4. Watch the progress as it:
   - Extracts transcript
   - Identifies events
   - Dispatches agents
   - Shows results

### Architecture

```
Frontend (Next.js) :3000
         ↓ HTTP/REST
Backend (FastAPI) :8000
         ↓
    ┌────┴────┐
    ↓         ↓
YouTube API   Gemini API
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/videos/process` | POST | Submit video for processing |
| `/api/v1/videos/{job_id}/status` | GET | Get processing status |
| `/api/v1/events/extract` | POST | Extract events from transcript |
| `/api/v1/agents/dispatch` | POST | Dispatch agents for events |
| `/api/v1/health` | GET | Health check |

See full API documentation at `/docs` endpoint.

### Troubleshooting

**CORS errors:**
- Ensure backend is running on port 8000
- Check CORS origins in `main_v2.py`
- Verify `NEXT_PUBLIC_API_URL` in frontend

**Video processing fails:**
- Check API keys in `.env`
- Verify YouTube URL is valid
- Check backend logs for errors

**Frontend can't connect:**
- Ensure `NEXT_PUBLIC_API_URL` is set correctly
- Verify backend is accessible at that URL
- Check browser console for errors
```
```

---

## Testing Checklist

After implementing all phases:

### Backend
- [ ] All endpoints respond correctly
- [ ] CORS configured for frontend
- [ ] Error handling works
- [ ] Request IDs in responses
- [ ] OpenAPI docs complete
- [ ] Tests pass: `pytest tests/ -v`

### Frontend
- [ ] Video input accepts URLs
- [ ] Status polling works
- [ ] Events display correctly
- [ ] Agent dashboard updates
- [ ] State management works
- [ ] Tests pass: `npm test`

### Integration
- [ ] Full workflow works end-to-end
- [ ] No CORS errors
- [ ] Real-time updates function
- [ ] Errors handled gracefully
- [ ] UI responsive

### Documentation
- [ ] README updated
- [ ] API docs complete
- [ ] Setup guide tested
- [ ] Troubleshooting section added

## Success Criteria

✅ User can paste YouTube URL and see results
✅ Backend and frontend communicate correctly
✅ All API endpoints work as expected
✅ Error handling is comprehensive
✅ Tests pass with >80% coverage
✅ Documentation is complete and accurate
