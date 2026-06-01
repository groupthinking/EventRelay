/**
 * Chat resource — conversational AI assistant.
 */

import type { EventRelayClient } from "../client";
import type { ChatRequest, ChatResponse } from "../types";

export class ChatResource {
  constructor(private readonly _client: EventRelayClient) {}

  /**
   * Send a message to the AI assistant.
   *
   * @param params - `query` is required (max 2000 chars).
   * @returns `ChatResponse` with the assistant's reply.
   */
  async send(params: ChatRequest): Promise<ChatResponse> {
    return this._client._post("/api/v1/chat", params) as Promise<ChatResponse>;
  }
}
