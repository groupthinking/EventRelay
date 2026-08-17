import type { ExtractedEvent, AgentExecution } from '@/lib/types';
import type { AnalysisProvenance, EvidenceAssessment } from '@/lib/analysis-evidence';

export interface PipelineResult {
  live_url: string | null;
  github_repo: string | null;
  build_status: string;
  code_generation: {
    framework: string;
    files_created: string[];
    entry_point: string;
  } | null;
  deployment: {
    status: string;
    platforms: string[];
    urls: Record<string, string>;
  } | null;
}

export interface Action {
  title: string;
  description: string;
  category: string;
  estimatedMinutes?: number | null;
}

export type PipelineMode = 'workflow' | 'live' | 'serverless' | 'fallback' | 'handoff';

export interface Video {
  id: string;
  title: string;
  url: string;
  status: 'processing' | 'complete' | 'failed';
  progress: number;
  /** How analysis ran: backend SSE, Gemini, legacy /api/video, or offline handoff. */
  pipelineMode?: PipelineMode;
  thumbnail?: string;
  duration?: string;
  processedAt?: string;
  transcript?: string;
  events?: ExtractedEvent[];
  agents?: AgentExecution[];
  pipelineResult?: PipelineResult;
  /** Async backend job id when pipeline runs in background. */
  jobId?: string;
  /** Poll URL for async job status. */
  statusUrl?: string;
  /** Durable Workflow DevKit generation identity. */
  runId?: string;
  provenance?: AnalysisProvenance;
  quality?: EvidenceAssessment;
  failure?: {
    stage: 'start' | 'acquisition' | 'analysis' | 'quality' | 'persistence' | 'deployment' | 'unknown';
    message: string;
    retryable: boolean;
    failedAt: string;
  };
  insights?: {
    summary: string;
    actions: Action[];
    sentiment: string;
    topics: string[];
    /**
     * Gemini project scaffold from backend TranscriptActionAgent
     * (repository_structure, core_modules, integration_points).
     * Canonical plan surface for F3; paired with Act on findings tools.
     */
    project_scaffold?: unknown;
  };
}

export interface Activity {
  time: string;
  event: string;
  type: 'success' | 'info' | 'error';
}

export interface SearchResult {
  start: number;
  duration: number;
  text: string;
  score: number;
}
