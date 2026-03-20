export interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  timeoutMs?: number;
}

export interface VideoClipOptions {
  start_seconds?: number;
  end_seconds?: number;
  fps?: number;
}

export interface TranscriptActionRequest {
  video_url: string;
  language?: string;
  transcript_text?: string;
  video_options?: VideoClipOptions;
}

export interface TranscriptActionResponse {
  success: boolean;
  video_url: string;
  metadata: Record<string, unknown>;
  transcript: Record<string, unknown>;
  outputs: Record<string, unknown>;
  errors: string[];
  orchestration_meta: Record<string, unknown>;
}

export interface VideoProcessingRequest {
  video_url: string;
  options?: Record<string, unknown>;
}

export interface VideoProcessingResponse {
  result: Record<string, unknown>;
  status: string;
  progress?: number;
  timestamp: string;
}

export interface VideoToSoftwareRequest {
  video_url: string;
  project_type?: string;
  deployment_target?: string;
  features?: string[];
}

export interface VideoToSoftwareResponse {
  video_url: string;
  project_name: string;
  project_type: string;
  deployment_target: string;
  live_url: string;
  github_repo: string;
  build_status: string;
  processing_time: string;
  features_implemented: string[];
  video_analysis: Record<string, unknown>;
  code_generation: Record<string, unknown>;
  deployment: Record<string, unknown>;
  status: string;
  timestamp: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version?: string;
  components?: Record<string, unknown>;
}
