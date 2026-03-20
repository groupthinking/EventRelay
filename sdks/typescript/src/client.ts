import {
  ClientOptions,
  HealthResponse,
  TranscriptActionRequest,
  TranscriptActionResponse,
  VideoProcessingRequest,
  VideoProcessingResponse,
  VideoToSoftwareRequest,
  VideoToSoftwareResponse,
} from "./types.js";

export class EventRelayClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly timeoutMs: number;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? "http://localhost:8000";
    this.apiKey = options.apiKey;
    this.timeoutMs = options.timeoutMs ?? 30000;
  }

  private buildHeaders(): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
    }
    return headers;
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers: { ...this.buildHeaders(), ...(init.headers ?? {}) },
        signal: controller.signal,
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(
          `Request to ${path} failed with ${response.status}: ${detail}`,
        );
      }
      return (await response.json()) as T;
    } finally {
      clearTimeout(timeout);
    }
  }

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/api/v1/health", { method: "GET" });
  }

  async transcriptAction(
    payload: TranscriptActionRequest,
  ): Promise<TranscriptActionResponse> {
    return this.request<TranscriptActionResponse>(
      "/api/v1/transcript-action",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  async videoToSoftware(
    payload: VideoToSoftwareRequest,
  ): Promise<VideoToSoftwareResponse> {
    return this.request<VideoToSoftwareResponse>(
      "/api/v1/video-to-software",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  async processVideo(
    payload: VideoProcessingRequest,
  ): Promise<VideoProcessingResponse> {
    return this.request<VideoProcessingResponse>("/api/v1/process-video", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}
