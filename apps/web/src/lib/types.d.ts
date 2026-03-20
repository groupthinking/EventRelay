/**
 * TypeScript types mirroring backend Pydantic models.
 * Keep in sync with src/youtube_extension/backend/api/v1/models.py
 */
export interface ApiResponse<T = unknown> {
    status: 'success' | 'error';
    data?: T;
    error?: string;
    detail?: string;
    timestamp: string;
    request_id: string;
}
export type JobStatus = 'pending' | 'downloading' | 'transcribing' | 'extracting' | 'complete' | 'failed';
export type AgentStatus = 'queued' | 'running' | 'complete' | 'failed';
export interface VideoProcessJobRequest {
    video_url: string;
    language?: string;
    options?: Record<string, unknown>;
}
export interface VideoProcessJobResponse {
    job_id: string;
    video_url: string;
    status: JobStatus;
}
export interface VideoJobStatusResponse {
    job_id: string;
    status: JobStatus;
    progress: number;
    video_url?: string;
    transcript?: string;
    metadata?: Record<string, unknown>;
    error?: string;
}
export interface EventExtractRequest {
    job_id?: string;
    transcript?: string;
    video_url?: string;
}
export interface ExtractedEvent {
    id: string;
    type: 'action' | 'mention' | 'topic' | 'insight';
    title: string;
    description?: string;
    timestamp?: string;
    confidence: number;
}
export interface EventExtractResponse {
    job_id?: string;
    events: ExtractedEvent[];
    event_count: number;
}
export interface AgentDispatchRequest {
    job_id?: string;
    events?: Record<string, unknown>[];
    transcript?: string;
    agent_types?: string[];
}
export interface AgentExecution {
    agent_id: string;
    agent_type: string;
    status: AgentStatus;
    progress: number;
    event_id?: string;
    result?: Record<string, unknown>;
    error?: string;
}
export interface AgentDispatchResponse {
    dispatch_id: string;
    executions: AgentExecution[];
}
export interface AgentStatusResponse {
    agent_id: string;
    agent_type: string;
    status: AgentStatus;
    progress: number;
    result?: Record<string, unknown>;
    error?: string;
}
export interface DashboardMetrics {
    status: string;
    timestamp: string;
    metrics: {
        activeWorkflows: number;
        totalProcessed: number;
        errorRate: number;
    };
}
export interface VideoInsights {
    summary: string;
    actions: string[];
    sentiment: string;
    topics: string[];
    strategy?: unknown;
    project_scaffold?: unknown;
}
