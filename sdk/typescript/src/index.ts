/**
 * EventRelay SDK — TypeScript/JavaScript entry point.
 *
 * @example
 * ```ts
 * import { EventRelayClient } from "@eventrelay/sdk";
 *
 * const client = new EventRelayClient({
 *   apiKey: "your-api-key",
 *   baseUrl: "http://localhost:8000",
 * });
 *
 * // Process a YouTube video
 * const job = await client.videos.process({
 *   video_url: "https://www.youtube.com/watch?v=auJzb1D-fag",
 * });
 * console.log(job.job_id);
 *
 * // Extract events from transcript
 * const events = await client.events.extract({
 *   transcript: "The speaker discussed building a React app...",
 * });
 * console.log(events.events);
 *
 * // Dispatch agents
 * const dispatch = await client.agents.dispatch({ events: events.events });
 * console.log(dispatch.executions);
 * ```
 */

export { EventRelayClient, EventRelayAPIError } from "./client";
export type { EventRelayClientOptions } from "./types";

// Request / response types
export type {
  JobStatus,
  AgentStatus,
  VideoProcessJobRequest,
  VideoProcessJobResponse,
  VideoJobStatusResponse,
  EventExtractRequest,
  ExtractedEvent,
  EventExtractResponse,
  AgentDispatchRequest,
  AgentExecution,
  AgentDispatchResponse,
  AgentStatusResponse,
  TranscriptActionRequest,
  TranscriptActionResponse,
  ChatRequest,
  ChatResponse,
  HealthResponse,
} from "./types";

// Resource classes (for advanced use-cases / sub-classing)
export { VideosResource } from "./resources/videos";
export { EventsResource } from "./resources/events";
export { AgentsResource } from "./resources/agents";
export { TranscriptResource } from "./resources/transcript";
export { ChatResource } from "./resources/chat";
export { HealthResource } from "./resources/health";
