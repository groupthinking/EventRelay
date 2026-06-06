/**
 * EventRelay API client (SC7) — the frontend's ONLY path to the backend.
 *
 * Targets the clean job-centric contract in service/openapi.json
 * (POST /api/v1/jobs, GET /api/v1/jobs/{id}[/transcript|/events|/artifacts]).
 *
 * Hard rule for SC7: this module imports NOTHING from a model SDK
 * (@google/genai, @google/generative-ai, openai). The frontend is a pure
 * consumer of the contract; if the backend is down the UI shows an error, it
 * does not silently fall back to calling a model. The guard test asserts this.
 *
 * Interim status: hand-written to match the new contract. It is the drop-in
 * replacement target for the Stainless-generated TS SDK once that is
 * regenerated from service/openapi.json.
 */

const DEFAULT_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  'http://localhost:8000';

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed';

export interface SubmitJobRequest {
  video_url: string;
  language?: string | null;
  options?: Record<string, unknown> | null;
}

export interface SubmitJobResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobView {
  job_id: string;
  status: JobStatus;
  video_url: string;
  created_at: string;
  updated_at: string;
  error?: string | null;
}

export interface EventItem {
  type: string;
  ts: string;
  payload: Record<string, unknown>;
}

export interface Artifacts {
  summary: string;
  tasks: string[];
  insights: Record<string, unknown>;
}

export class EventRelayError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'EventRelayError';
  }
}

const TERMINAL: ReadonlySet<JobStatus> = new Set<JobStatus>(['succeeded', 'failed']);

export class EventRelayClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = DEFAULT_BACKEND_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      });
    } catch (err) {
      // Network failure / backend down — surface it, never fall back to a model.
      throw new EventRelayError(
        `backend unreachable: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new EventRelayError(body.detail || res.statusText, res.status);
    }
    return (await res.json()) as T;
  }

  submitJob(req: SubmitJobRequest): Promise<SubmitJobResponse> {
    return this.request<SubmitJobResponse>('/api/v1/jobs', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  getJob(jobId: string): Promise<JobView> {
    return this.request<JobView>(`/api/v1/jobs/${encodeURIComponent(jobId)}`);
  }

  async getTranscript(jobId: string): Promise<string> {
    const v = await this.request<{ job_id: string; transcript: string }>(
      `/api/v1/jobs/${encodeURIComponent(jobId)}/transcript`,
    );
    return v.transcript;
  }

  async getEvents(jobId: string): Promise<EventItem[]> {
    const v = await this.request<{ job_id: string; events: EventItem[] }>(
      `/api/v1/jobs/${encodeURIComponent(jobId)}/events`,
    );
    return v.events;
  }

  async getArtifacts(jobId: string): Promise<Artifacts> {
    const v = await this.request<{ job_id: string; artifacts: Artifacts }>(
      `/api/v1/jobs/${encodeURIComponent(jobId)}/artifacts`,
    );
    return v.artifacts;
  }

  /** Poll job status until terminal or timeout. */
  async pollUntilDone(
    jobId: string,
    { intervalMs = 2000, timeoutMs = 180_000 }: { intervalMs?: number; timeoutMs?: number } = {},
  ): Promise<JobView> {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const job = await this.getJob(jobId);
      if (TERMINAL.has(job.status)) return job;
      if (Date.now() >= deadline) {
        throw new EventRelayError(`timed out waiting for job ${jobId}`);
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  }
}

export const eventRelay = new EventRelayClient();
