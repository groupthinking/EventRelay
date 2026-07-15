/**
 * EventRelay SDK — shared TypeScript types.
 *
 * These types mirror the Pydantic models in the backend
 * (src/youtube_extension/backend/api/v1/models.py) and are derived from
 * openapi/eventrelay.openapi.json.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type JobStatus =
  | "pending"
  | "downloading"
  | "transcribing"
  | "extracting"
  | "complete"
  | "failed";

export type AgentStatus = "queued" | "running" | "complete" | "failed";

// ---------------------------------------------------------------------------
// Video Processing
// ---------------------------------------------------------------------------

export interface VideoProcessJobRequest {
  /** Full YouTube video URL */
  video_url: string;
  /** Transcript language code (default "en") */
  language?: string;
  /** Optional processing overrides */
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
  /** Progress percentage 0–100 */
  progress: number;
  video_url?: string;
  transcript?: string;
  metadata?: Record<string, unknown>;
  error?: string;
  /** Machine-readable slug describing why a job failed (e.g. 'gemini_api_timeout') */
  error_reason?: string;
  /** UTC creation timestamp (ISO 8601); used by job-store retention (expire_before). */
  created_at: string;
}

// ---------------------------------------------------------------------------
// Event Extraction
// ---------------------------------------------------------------------------

export interface EventExtractRequest {
  /** Job ID from video processing */
  job_id?: string;
  /** Raw transcript text */
  transcript?: string;
  video_url?: string;
}

export interface ExtractedEvent {
  id: string;
  /** "action" | "mention" | "topic" | "insight" */
  type: string;
  title: string;
  description?: string;
  /** Time in video, e.g. "02:15" */
  timestamp?: string;
  /** Confidence score 0–1 */
  confidence: number;
}

export interface EventExtractResponse {
  job_id?: string;
  events: ExtractedEvent[];
  event_count: number;
}

// ---------------------------------------------------------------------------
// Agent Dispatch
// ---------------------------------------------------------------------------

export interface AgentDispatchRequest {
  job_id?: string;
  events?: Record<string, unknown>[];
  /** Transcript — events will be auto-extracted when events is empty */
  transcript?: string;
  /** Restrict dispatch to specific agent type identifiers */
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

// ---------------------------------------------------------------------------
// Transcript Action
// ---------------------------------------------------------------------------

export interface TranscriptActionRequest {
  /** Transcript language code (default "en") */
  language?: string;
  /** Raw transcript text to run actions against */
  transcript_text: string;
  /** Optional video-related options (e.g., URL, id, processing hints) */
  video_options?: Record<string, unknown>;
}

export interface TranscriptActionResponse {
  /** Whether the transcript action orchestration completed successfully */
  success: boolean;
  /** Additional metadata about the transcript/action run */
  metadata?: Record<string, unknown>;
  /** Canonical transcript representation or enriched transcript payload */
  transcript?: string | Record<string, unknown>;
  /** Outputs produced by transcript actions */
  outputs?: Array<Record<string, unknown>>;
  /** Errors encountered during orchestration or action execution */
  errors?: Array<unknown>;
  /** Low-level orchestration/debugging information */
  orchestration_meta?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export interface ChatRequest {
  query: string;
  video_id?: string;
  video_url?: string;
  context?: string;
  session_id?: string;
  history?: Array<Record<string, string>>;
}

export interface ChatResponse {
  response: string;
  status: string;
  session_id: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  version?: string;
  /** Server time when this health snapshot was generated (ISO 8601). */
  timestamp: string;
  /** Health status of core components, keyed by component name. */
  components: Record<string, unknown>;
}

/** Response type for /api/v1/health/detailed */
export interface HealthDetailedResponse {
  /** Basic system health information. */
  basic: Record<string, unknown>;
  /** Connector-specific health information. */
  connectors: Record<string, unknown>;
  /** Pipeline and processing health information. */
  pipeline: Record<string, unknown>;
  /** Server time when this detailed health snapshot was generated (ISO 8601). */
  timestamp: string;
}
// ---------------------------------------------------------------------------
// Client configuration
// ---------------------------------------------------------------------------

export interface EventRelayClientOptions {
  /** API key — falls back to EVENTRELAY_API_KEY env variable */
  apiKey?: string;
  /** Base URL (default: https://api.uvai.io) */
  baseUrl?: string;
  /** HTTP timeout in milliseconds (default: 60000) */
  timeout?: number;
  /** Max retry attempts on transient errors (default: 2) */
  maxRetries?: number;
}
