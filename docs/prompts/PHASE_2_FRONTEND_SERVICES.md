# Phase 2: Frontend Service Layer - Copilot Prompts

## Overview
These prompts guide the creation of a robust service layer for frontend-backend communication.

---

## Prompt 2.1: API Client Service

```
Create a production-ready API client service for EventRelay frontend.

Context:
- Working in: apps/web/src/services/api-client.ts (create new file)
- Using: TypeScript, fetch API, Next.js 14+
- Goal: Centralized backend communication with error handling

Requirements:

1. Create APIClient class with:
   - Base URL configuration from environment
   - Request/response interceptors
   - Automatic retry logic for transient failures
   - Timeout handling
   - Request ID tracking
   - Error parsing

2. Support all HTTP methods:
   - GET, POST, PUT, DELETE, PATCH
   - Proper Content-Type headers
   - JSON request/response handling
   - File upload support (multipart/form-data)

3. Add authentication support:
   - Include auth tokens in headers
   - Handle token refresh
   - Redirect on 401 Unauthorized

4. Implement error handling:
   - Parse error responses
   - Convert to typed Error objects
   - Include request ID for debugging
   - User-friendly error messages

Implementation:
```typescript
// apps/web/src/services/api-client.ts

interface RequestOptions extends RequestInit {
  timeout?: number;
  retry?: number;
}

interface APIResponse<T = any> {
  status: 'success' | 'error';
  data: T;
  timestamp: string;
  request_id: string;
}

interface ErrorResponse {
  status: 'error';
  error: string;
  detail?: string;
  request_id: string;
  timestamp: string;
  path?: string;
}

export class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public requestId?: string,
    public detail?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class APIClient {
  private baseURL: string;
  private defaultTimeout: number = 30000; // 30s
  private maxRetries: number = 3;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  /**
   * Make HTTP request with retry logic and error handling
   */
  async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const {
      timeout = this.defaultTimeout,
      retry = this.maxRetries,
      ...fetchOptions
    } = options;

    const url = `${this.baseURL}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...fetchOptions.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        await this.handleErrorResponse(response);
      }

      const data: APIResponse<T> = await response.json();
      return data.data;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof APIError) {
        throw error;
      }

      // Retry on network errors
      if (retry > 0 && this.isRetryable(error)) {
        await this.delay(1000 * (this.maxRetries - retry + 1));
        return this.request(endpoint, { ...options, retry: retry - 1 });
      }

      throw new APIError(
        error instanceof Error ? error.message : 'Network error',
        0
      );
    }
  }

  /**
   * Handle error responses from API
   */
  private async handleErrorResponse(response: Response): Promise<never> {
    let errorData: ErrorResponse;

    try {
      errorData = await response.json();
    } catch {
      throw new APIError(
        response.statusText || 'Unknown error',
        response.status
      );
    }

    throw new APIError(
      errorData.error,
      response.status,
      errorData.request_id,
      errorData.detail
    );
  }

  /**
   * Check if error is retryable
   */
  private isRetryable(error: any): boolean {
    if (error.name === 'AbortError') return false; // Timeout
    if (error instanceof APIError && error.statusCode >= 400 && error.statusCode < 500) {
      return false; // Client errors are not retryable
    }
    return true;
  }

  /**
   * Delay helper for retry logic
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Convenience methods
  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T>(
    endpoint: string,
    data?: any,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put<T>(
    endpoint: string,
    data?: any,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

// Export singleton instance
export const apiClient = new APIClient();
```

Usage example:
```typescript
import { apiClient } from './api-client';

// In a component or service
const data = await apiClient.get('/api/v1/videos/123');
const result = await apiClient.post('/api/v1/videos/process', {
  video_url: 'https://youtube.com/watch?v=auJzb1D-fag'
});
```

Testing:
```typescript
// apps/web/src/services/__tests__/api-client.test.ts
import { apiClient, APIError } from '../api-client';

describe('APIClient', () => {
  it('should make GET request', async () => {
    // Test implementation
  });

  it('should retry on network error', async () => {
    // Test implementation
  });

  it('should throw APIError on 4xx', async () => {
    // Test implementation
  });
});
```
```

---

## Prompt 2.2: Type Definitions

```
Create TypeScript type definitions that mirror backend Pydantic models.

Context:
- Working in: apps/web/src/types/ (create directory and files)
- Using: TypeScript 5+
- Goal: Type safety between frontend and backend

Requirements:

1. Create types for all API request/response models:
   - Video processing types
   - Event types
   - Agent types
   - Common types (pagination, errors)

2. Match backend Pydantic models exactly:
   - Same field names
   - Same data types
   - Same optional/required fields
   - Same enums

3. Add JSDoc comments:
   - Describe each type
   - Document field meanings
   - Include examples

4. Export from central index:
   - Clean imports in components
   - Organized by domain

File structure:
```
apps/web/src/types/
├── index.ts          # Re-export all types
├── api.ts            # API response wrappers
├── video.ts          # Video-related types
├── event.ts          # Event-related types
└── agent.ts          # Agent-related types
```

Implementation:

```typescript
// apps/web/src/types/api.ts

/**
 * Standard API response wrapper
 */
export interface APIResponse<T = any> {
  status: 'success' | 'error' | 'pending';
  data: T;
  timestamp: string;
  request_id: string;
}

/**
 * Error response from API
 */
export interface ErrorResponse {
  status: 'error';
  error: string;
  detail?: string;
  request_id: string;
  timestamp: string;
  path?: string;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// apps/web/src/types/video.ts

/**
 * Request to process a YouTube video
 */
export interface VideoProcessRequest {
  /** YouTube video URL (youtube.com or youtu.be) */
  video_url: string;
  /** Optional processing configuration */
  options?: Record<string, any>;
}

/**
 * Response when video processing starts
 */
export interface VideoProcessResponse {
  /** Unique job identifier */
  job_id: string;
  /** YouTube video ID */
  video_id: string;
  /** Initial status */
  status: 'pending' | 'queued';
  /** When job was created */
  created_at: string;
}

/**
 * Video processing status
 */
export type VideoProcessStatus = 
  | 'pending'
  | 'processing' 
  | 'completed' 
  | 'failed';

/**
 * Detailed status of video processing job
 */
export interface VideoStatusResponse {
  job_id: string;
  video_id: string;
  status: VideoProcessStatus;
  /** Progress percentage (0-100) */
  progress: number;
  /** Video transcript (when available) */
  transcript?: string;
  /** Extracted events (when available) */
  events?: Event[];
  /** Error message (when failed) */
  error?: string;
  /** Video metadata */
  metadata?: VideoMetadata;
}

/**
 * Video metadata from YouTube
 */
export interface VideoMetadata {
  title: string;
  channel: string;
  duration: number; // seconds
  thumbnail_url: string;
  published_at: string;
  description?: string;
  view_count?: number;
}

// apps/web/src/types/event.ts

/**
 * Types of events that can be extracted
 */
export enum EventType {
  ACTION = 'action',
  MENTION = 'mention',
  TOPIC = 'topic',
  DECISION = 'decision',
  QUESTION = 'question',
  INSTRUCTION = 'instruction',
}

/**
 * Structured event extracted from video transcript
 */
export interface Event {
  /** Unique event identifier */
  id: string;
  /** YouTube video ID */
  video_id: string;
  /** Event classification */
  type: EventType;
  /** Human-readable description */
  description: string;
  /** Timestamp in video (seconds) */
  timestamp: number;
  /** AI confidence score (0.0-1.0) */
  confidence: number;
  /** Additional context */
  metadata: Record<string, any>;
  /** When event was extracted */
  created_at: string;
}

/**
 * Request to extract events
 */
export interface ExtractEventsRequest {
  /** Raw transcript text */
  transcript?: string;
  /** Or video ID to use cached transcript */
  video_id?: string;
}

/**
 * Response from event extraction
 */
export interface ExtractEventsResponse {
  events: Event[];
  total_count: number;
  processing_time_ms: number;
}

// apps/web/src/types/agent.ts

/**
 * Types of agents available
 */
export enum AgentType {
  CODE_GENERATOR = 'code_generator',
  CONTENT_CREATOR = 'content_creator',
  WORKFLOW_TRIGGER = 'workflow_trigger',
  DATA_ANALYZER = 'data_analyzer',
}

/**
 * Agent execution status
 */
export type AgentStatus = 
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed';

/**
 * Configuration for an agent
 */
export interface AgentConfig {
  agent_type: AgentType;
  parameters?: Record<string, any>;
  /** Priority (1-10, higher = more important) */
  priority?: number;
}

/**
 * Request to dispatch agents
 */
export interface DispatchAgentsRequest {
  video_id: string;
  /** Event IDs to process */
  events: string[];
  /** Agents to execute */
  agents: AgentConfig[];
  options?: Record<string, any>;
}

/**
 * Agent execution tracking
 */
export interface AgentExecution {
  agent_id: string;
  agent_type: AgentType;
  status: AgentStatus;
  /** Progress percentage (0-100) */
  progress: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

/**
 * Response when agents are dispatched
 */
export interface DispatchAgentsResponse {
  executions: AgentExecution[];
  dispatch_id: string;
}

/**
 * Results from completed agent
 */
export interface AgentResults {
  agent_id: string;
  /** Generated outputs */
  outputs: Array<Record<string, any>>;
  /** URLs or paths to generated artifacts */
  artifacts: string[];
  /** Execution logs */
  logs: string[];
  /** Total execution time in milliseconds */
  execution_time_ms: number;
}

// apps/web/src/types/index.ts

/**
 * EventRelay API Types
 * 
 * TypeScript definitions matching backend Pydantic models
 */

// Re-export all types
export * from './api';
export * from './video';
export * from './event';
export * from './agent';
```

Usage in components:
```typescript
import {
  VideoProcessRequest,
  VideoStatusResponse,
  Event,
  AgentExecution,
} from '@/types';

function VideoProcessor() {
  const [status, setStatus] = useState<VideoStatusResponse | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  
  // Type-safe component logic
}
```
```

---

## Prompt 2.3: Video Service

```
Create a service for all video-related API operations.

Context:
- Working in: apps/web/src/services/video-service.ts (create new file)
- Using: APIClient, TypeScript types
- Goal: Encapsulate video processing logic

Requirements:

1. Implement video processing methods:
   - processVideo(url): Submit video for processing
   - getVideoStatus(jobId): Poll processing status
   - getVideo(videoId): Get cached video data
   - listVideos(): List all processed videos

2. Add polling helper:
   - Poll status until completed/failed
   - Configurable interval and timeout
   - Return final status

3. Include validation:
   - Validate YouTube URLs
   - Check URL format
   - Extract video ID

4. Add caching:
   - Cache video metadata
   - Cache transcripts
   - Avoid redundant requests

Implementation:
```typescript
// apps/web/src/services/video-service.ts

import { apiClient, APIError } from './api-client';
import {
  VideoProcessRequest,
  VideoProcessResponse,
  VideoStatusResponse,
  VideoMetadata,
} from '@/types';

export class VideoService {
  private pollingInterval = 2000; // 2s
  private pollingTimeout = 300000; // 5min

  /**
   * Submit YouTube video for processing
   */
  async processVideo(videoUrl: string, options?: Record<string, any>): Promise<VideoProcessResponse> {
    this.validateYouTubeUrl(videoUrl);

    const request: VideoProcessRequest = {
      video_url: videoUrl,
      options,
    };

    return apiClient.post<VideoProcessResponse>(
      '/api/v1/videos/process',
      request
    );
  }

  /**
   * Get current status of processing job
   */
  async getVideoStatus(jobId: string): Promise<VideoStatusResponse> {
    return apiClient.get<VideoStatusResponse>(
      `/api/v1/videos/${jobId}/status`
    );
  }

  /**
   * Poll until video processing completes
   * 
   * @returns Final status (completed or failed)
   * @throws {Error} If polling times out
   */
  async pollUntilComplete(
    jobId: string,
    onProgress?: (status: VideoStatusResponse) => void
  ): Promise<VideoStatusResponse> {
    const startTime = Date.now();

    while (true) {
      const status = await this.getVideoStatus(jobId);

      // Call progress callback
      if (onProgress) {
        onProgress(status);
      }

      // Check if done
      if (status.status === 'completed' || status.status === 'failed') {
        return status;
      }

      // Check timeout
      if (Date.now() - startTime > this.pollingTimeout) {
        throw new Error('Video processing timeout');
      }

      // Wait before next poll
      await this.delay(this.pollingInterval);
    }
  }

  /**
   * Process video and wait for completion
   * 
   * Convenience method that combines processVideo and pollUntilComplete
   */
  async processVideoAndWait(
    videoUrl: string,
    onProgress?: (status: VideoStatusResponse) => void
  ): Promise<VideoStatusResponse> {
    const response = await this.processVideo(videoUrl);
    return this.pollUntilComplete(response.job_id, onProgress);
  }

  /**
   * Get processed video by video ID
   */
  async getVideo(videoId: string): Promise<VideoStatusResponse> {
    return apiClient.get<VideoStatusResponse>(
      `/api/v1/videos/${videoId}`
    );
  }

  /**
   * Validate YouTube URL format
   */
  private validateYouTubeUrl(url: string): void {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/;
    
    if (!youtubeRegex.test(url)) {
      throw new Error('Invalid YouTube URL format');
    }
  }

  /**
   * Extract video ID from YouTube URL
   */
  extractVideoId(url: string): string | null {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/,
      /youtube\.com\/embed\/([^&\s]+)/,
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) {
        return match[1];
      }
    }

    return null;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export singleton
export const videoService = new VideoService();
```

Usage in React component:
```typescript
'use client';

import { useState } from 'react';
import { videoService } from '@/services/video-service';
import { VideoStatusResponse } from '@/types';

export function VideoProcessor() {
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState<VideoStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Process with progress updates
      const result = await videoService.processVideoAndWait(
        url,
        (progress) => {
          setStatus(progress);
        }
      );

      setStatus(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Enter YouTube URL"
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Processing...' : 'Process Video'}
      </button>

      {error && <div className="error">{error}</div>}

      {status && (
        <div>
          <p>Status: {status.status}</p>
          <p>Progress: {status.progress}%</p>
          {status.transcript && <pre>{status.transcript}</pre>}
        </div>
      )}
    </form>
  );
}
```
```

---

## Prompt 2.4: Event Service

```
Create a service for event extraction and management.

Context:
- Working in: apps/web/src/services/event-service.ts (create new file)
- Using: APIClient, TypeScript types
- Goal: Handle event extraction and filtering

Implementation:
```typescript
// apps/web/src/services/event-service.ts

import { apiClient } from './api-client';
import {
  Event,
  EventType,
  ExtractEventsRequest,
  ExtractEventsResponse,
  PaginatedResponse,
} from '@/types';

export class EventService {
  /**
   * Extract events from transcript or video
   */
  async extractEvents(
    transcriptOrVideoId: string,
    isVideoId: boolean = false
  ): Promise<ExtractEventsResponse> {
    const request: ExtractEventsRequest = isVideoId
      ? { video_id: transcriptOrVideoId }
      : { transcript: transcriptOrVideoId };

    return apiClient.post<ExtractEventsResponse>(
      '/api/v1/events/extract',
      request
    );
  }

  /**
   * List events for a video
   */
  async listEvents(
    videoId: string,
    options?: {
      eventType?: EventType;
      page?: number;
      limit?: number;
    }
  ): Promise<PaginatedResponse<Event>> {
    const params = new URLSearchParams();
    params.append('video_id', videoId);
    
    if (options?.eventType) {
      params.append('event_type', options.eventType);
    }
    if (options?.page) {
      params.append('page', options.page.toString());
    }
    if (options?.limit) {
      params.append('limit', options.limit.toString());
    }

    return apiClient.get<PaginatedResponse<Event>>(
      `/api/v1/events?${params.toString()}`
    );
  }

  /**
   * Get specific event details
   */
  async getEvent(eventId: string): Promise<Event> {
    return apiClient.get<Event>(`/api/v1/events/${eventId}`);
  }

  /**
   * Filter events by type
   */
  filterByType(events: Event[], type: EventType): Event[] {
    return events.filter(event => event.type === type);
  }

  /**
   * Sort events by confidence
   */
  sortByConfidence(events: Event[], descending: boolean = true): Event[] {
    return [...events].sort((a, b) =>
      descending ? b.confidence - a.confidence : a.confidence - b.confidence
    );
  }

  /**
   * Sort events by timestamp
   */
  sortByTimestamp(events: Event[]): Event[] {
    return [...events].sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Group events by type
   */
  groupByType(events: Event[]): Record<EventType, Event[]> {
    return events.reduce((acc, event) => {
      if (!acc[event.type]) {
        acc[event.type] = [];
      }
      acc[event.type].push(event);
      return acc;
    }, {} as Record<EventType, Event[]>);
  }

  /**
   * Format timestamp for display (MM:SS)
   */
  formatTimestamp(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
}

export const eventService = new EventService();
```
```

---

## Prompt 2.5: Agent Service

```
Create a service for agent dispatch and tracking.

Context:
- Working in: apps/web/src/services/agent-service.ts (create new file)
- Using: APIClient, TypeScript types
- Goal: Manage agent execution lifecycle

Implementation:
```typescript
// apps/web/src/services/agent-service.ts

import { apiClient } from './api-client';
import {
  AgentType,
  AgentConfig,
  AgentExecution,
  AgentResults,
  AgentStatus,
  DispatchAgentsRequest,
  DispatchAgentsResponse,
} from '@/types';

export class AgentService {
  private pollingInterval = 3000; // 3s

  /**
   * Dispatch agents to process events
   */
  async dispatchAgents(
    videoId: string,
    eventIds: string[],
    agents: AgentConfig[]
  ): Promise<DispatchAgentsResponse> {
    const request: DispatchAgentsRequest = {
      video_id: videoId,
      events: eventIds,
      agents,
    };

    return apiClient.post<DispatchAgentsResponse>(
      '/api/v1/agents/dispatch',
      request
    );
  }

  /**
   * Get agent execution status
   */
  async getAgentStatus(agentId: string): Promise<AgentExecution> {
    return apiClient.get<AgentExecution>(
      `/api/v1/agents/${agentId}/status`
    );
  }

  /**
   * Get agent results
   */
  async getAgentResults(agentId: string): Promise<AgentResults> {
    return apiClient.get<AgentResults>(
      `/api/v1/agents/${agentId}/results`
    );
  }

  /**
   * List all agents for a video
   */
  async listAgents(
    videoId: string,
    status?: AgentStatus
  ): Promise<AgentExecution[]> {
    const params = new URLSearchParams({ video_id: videoId });
    if (status) {
      params.append('status', status);
    }

    return apiClient.get<AgentExecution[]>(
      `/api/v1/agents?${params.toString()}`
    );
  }

  /**
   * Poll agent status until completion
   */
  async pollUntilComplete(
    agentId: string,
    onProgress?: (status: AgentExecution) => void
  ): Promise<AgentExecution> {
    while (true) {
      const status = await this.getAgentStatus(agentId);

      if (onProgress) {
        onProgress(status);
      }

      if (status.status === 'completed' || status.status === 'failed') {
        return status;
      }

      await this.delay(this.pollingInterval);
    }
  }

  /**
   * Monitor multiple agents simultaneously
   */
  async monitorAgents(
    agentIds: string[],
    onUpdate?: (statuses: Map<string, AgentExecution>) => void
  ): Promise<Map<string, AgentExecution>> {
    const statuses = new Map<string, AgentExecution>();
    
    while (statuses.size < agentIds.length) {
      const updates = await Promise.all(
        agentIds.map(id => this.getAgentStatus(id))
      );

      updates.forEach(status => {
        statuses.set(status.agent_id, status);
      });

      if (onUpdate) {
        onUpdate(statuses);
      }

      // Check if all complete
      const allDone = updates.every(
        s => s.status === 'completed' || s.status === 'failed'
      );

      if (allDone) {
        break;
      }

      await this.delay(this.pollingInterval);
    }

    return statuses;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

export const agentService = new AgentService();
```
```

---

## Prompt 2.6: Environment Configuration

```
Setup environment configuration for frontend.

Context:
- Working in: apps/web/ directory
- Using: Next.js environment variables
- Goal: Configure API URLs and app settings

Tasks:

1. Create .env.local.example:
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# App Configuration
NEXT_PUBLIC_APP_NAME=EventRelay
NEXT_PUBLIC_APP_VERSION=2.0.0

# Feature Flags
NEXT_PUBLIC_ENABLE_WEBSOCKET=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false

# Development
NEXT_PUBLIC_DEBUG=false
```

2. Create .env.local for development:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_APP_NAME=EventRelay
NEXT_PUBLIC_DEBUG=true
```

3. Create apps/web/src/lib/config.ts:
```typescript
// apps/web/src/lib/config.ts

interface AppConfig {
  api: {
    baseURL: string;
    wsURL: string;
    timeout: number;
  };
  app: {
    name: string;
    version: string;
  };
  features: {
    websocket: boolean;
    analytics: boolean;
  };
  debug: boolean;
}

function getConfig(): AppConfig {
  return {
    api: {
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      wsURL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
      timeout: 30000,
    },
    app: {
      name: process.env.NEXT_PUBLIC_APP_NAME || 'EventRelay',
      version: process.env.NEXT_PUBLIC_APP_VERSION || '2.0.0',
    },
    features: {
      websocket: process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET === 'true',
      analytics: process.env.NEXT_PUBLIC_ENABLE_ANALYTICS === 'true',
    },
    debug: process.env.NEXT_PUBLIC_DEBUG === 'true',
  };
}

export const config = getConfig();

// Validate configuration
if (!config.api.baseURL) {
  throw new Error('NEXT_PUBLIC_API_URL is required');
}
```

4. Update .gitignore:
```
# Environment files
.env.local
.env.*.local
```

5. Document in README:
```markdown
## Frontend Configuration

Copy `.env.local.example` to `.env.local`:

```bash
cd apps/web
cp .env.local.example .env.local
```

Required variables:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)
- `NEXT_PUBLIC_WS_URL`: WebSocket URL (optional)

See `.env.local.example` for all available options.
```
```

---

## Testing Checklist

After implementing Phase 2:

- [ ] APIClient can make requests to backend
- [ ] APIClient handles errors correctly
- [ ] APIClient retries on failure
- [ ] All types match backend models
- [ ] VideoService can process videos
- [ ] VideoService can poll status
- [ ] EventService can extract events
- [ ] AgentService can dispatch agents
- [ ] Environment config loads correctly
- [ ] NEXT_PUBLIC_API_URL is used
- [ ] Types provide autocomplete

Test with:
```bash
# In apps/web directory
npm install
npm run dev

# Test in browser console:
import { apiClient } from './src/services/api-client';
const data = await apiClient.get('/api/v1/health');
console.log(data);
```
