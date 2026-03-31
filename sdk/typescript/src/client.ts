/**
 * EventRelay API client for TypeScript / JavaScript.
 *
 * Generated via Stainless from openapi/eventrelay.openapi.json.
 */

import type { EventRelayClientOptions } from "./types";
import { VideosResource } from "./resources/videos";
import { EventsResource } from "./resources/events";
import { AgentsResource } from "./resources/agents";
import { TranscriptResource } from "./resources/transcript";
import { ChatResource } from "./resources/chat";
import { HealthResource } from "./resources/health";

const DEFAULT_BASE_URL = "https://api.uvai.io";
const DEFAULT_TIMEOUT_MS = 60_000;
const DEFAULT_MAX_RETRIES = 2;
const RETRY_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

/**
 * Perform a fetch with retry logic and raise on HTTP errors.
 *
 * @internal
 */
export async function fetchWithRetry(
  url: string,
  init: RequestInit,
  maxRetries: number,
  timeout: number
): Promise<unknown> {
  let attempt = 0;
  let lastError: unknown;

  while (attempt <= maxRetries) {
    const controller = new AbortController();
    const timerId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...init,
        signal: controller.signal,
      });
      clearTimeout(timerId);

      if (RETRY_STATUS_CODES.has(response.status) && attempt < maxRetries) {
        attempt++;
        continue;
      }

      if (!response.ok) {
        const body = await response.text().catch(() => "");
        throw new EventRelayAPIError(response.status, response.statusText, body);
      }

      const json = await response.json();
      // Unwrap ApiResponse envelope if present
      if (
        json &&
        typeof json === "object" &&
        "status" in json &&
        "data" in json &&
        (json.status === "success" || json.status === "error")
      ) {
        return json.data;
      }
      return json;
    } catch (err) {
      clearTimeout(timerId);
      lastError = err;
      if (err instanceof EventRelayAPIError && !RETRY_STATUS_CODES.has(err.statusCode)) {
        throw err;
      }
      attempt++;
    }
  }

  throw lastError;
}

/** Thrown when the EventRelay API returns a non-2xx HTTP status. */
export class EventRelayAPIError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly statusText: string,
    public readonly body: string
  ) {
    super(`EventRelay API Error ${statusCode}: ${statusText}`);
    this.name = "EventRelayAPIError";
  }
}

/**
 * EventRelay API client.
 *
 * @example
 * ```ts
 * import { EventRelayClient } from "@eventrelay/sdk";
 *
 * const client = new EventRelayClient({ apiKey: "..." });
 *
 * const job = await client.videos.process({
 *   video_url: "https://www.youtube.com/watch?v=auJzb1D-fag",
 * });
 * console.log(job.job_id);
 * ```
 */
export class EventRelayClient {
  private readonly _apiKey: string;
  private readonly _baseUrl: string;
  private readonly _timeout: number;
  private readonly _maxRetries: number;

  /** Process YouTube videos and manage the video library. */
  readonly videos: VideosResource;
  /** Extract structured events from transcripts. */
  readonly events: EventsResource;
  /** Dispatch and monitor AI agents. */
  readonly agents: AgentsResource;
  /** Transcript-action workflows. */
  readonly transcript: TranscriptResource;
  /** Conversational AI assistant. */
  readonly chat: ChatResource;
  /** API health and readiness checks. */
  readonly health: HealthResource;

  constructor(options: EventRelayClientOptions = {}) {
    this._apiKey =
      options.apiKey ??
      (typeof process !== "undefined" ? process.env.EVENTRELAY_API_KEY ?? "" : "");
    this._baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this._timeout = options.timeout ?? DEFAULT_TIMEOUT_MS;
    this._maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;

    this.videos = new VideosResource(this);
    this.events = new EventsResource(this);
    this.agents = new AgentsResource(this);
    this.transcript = new TranscriptResource(this);
    this.chat = new ChatResource(this);
    this.health = new HealthResource(this);
  }

  /** @internal */
  _headers(): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this._apiKey) {
      headers["X-API-Key"] = this._apiKey;
    }
    return headers;
  }

  /** @internal */
  _url(path: string): string {
    return `${this._baseUrl}${path}`;
  }

  /** @internal */
  async _get(path: string): Promise<unknown> {
    return fetchWithRetry(
      this._url(path),
      { method: "GET", headers: this._headers() },
      this._maxRetries,
      this._timeout
    );
  }

  /** @internal */
  async _post(path: string, body: unknown): Promise<unknown> {
    return fetchWithRetry(
      this._url(path),
      {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify(body),
      },
      this._maxRetries,
      this._timeout
    );
  }

  /** @internal */
  async _delete(path: string): Promise<unknown> {
    return fetchWithRetry(
      this._url(path),
      { method: "DELETE", headers: this._headers() },
      this._maxRetries,
      this._timeout
    );
  }
}
