/**
 * Transcript resource — run transcript-action workflows.
 */

import type { EventRelayClient } from "../client";
import type { TranscriptActionRequest, TranscriptActionResponse } from "../types";

export class TranscriptResource {
  constructor(private readonly _client: EventRelayClient) {}

  /**
   * Run the transcript-action workflow for a YouTube video.
   *
   * @param params - `video_url` is required.
   * @returns `TranscriptActionResponse` with transcript and actions.
   */
  async action(params: TranscriptActionRequest): Promise<TranscriptActionResponse> {
    return this._client._post(
      "/api/v1/transcript-action",
      params
    ) as Promise<TranscriptActionResponse>;
  }
}
