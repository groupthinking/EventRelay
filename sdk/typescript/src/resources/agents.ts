/**
 * Agents resource — dispatch and monitor AI agents.
 */

import type { EventRelayClient } from "../client";
import type {
  AgentDispatchRequest,
  AgentDispatchResponse,
  AgentStatusResponse,
} from "../types";

export class AgentsResource {
  constructor(private readonly _client: EventRelayClient) {}

  /**
   * Dispatch AI agents for the given events.
   *
   * When `events` is empty and `transcript` is provided, the backend will
   * auto-extract events before dispatching.
   *
   * @param params - Dispatch parameters.
   * @returns `AgentDispatchResponse` with a list of `AgentExecution` objects.
   */
  async dispatch(params: AgentDispatchRequest): Promise<AgentDispatchResponse> {
    return this._client._post("/api/v1/agents/dispatch", params) as Promise<AgentDispatchResponse>;
  }

  /**
   * Retrieve the current status of a dispatched agent.
   *
   * @param agentId - The `agent_id` returned inside an `AgentExecution` by {@link dispatch}.
   * @returns `AgentStatusResponse` with status and optional result.
   */
  async getStatus(agentId: string): Promise<AgentStatusResponse> {
    return this._client._get(`/api/v1/agents/${agentId}/status`) as Promise<AgentStatusResponse>;
  }
}
