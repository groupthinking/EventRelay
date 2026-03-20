/**
 * Events resource — extract structured events from transcripts.
 */

import type { EventRelayClient } from "../client";
import type { EventExtractRequest, EventExtractResponse } from "../types";

export class EventsResource {
  constructor(private readonly _client: EventRelayClient) {}

  /**
   * Extract structured events from a transcript.
   *
   * Provide at least one of `transcript`, `jobId`, or `videoUrl`.
   *
   * @param params - Extraction parameters.
   * @returns `EventExtractResponse` containing a list of `ExtractedEvent` objects.
   */
  async extract(params: EventExtractRequest): Promise<EventExtractResponse> {
    return this._client._post("/api/v1/events/extract", params) as Promise<EventExtractResponse>;
  }
}
