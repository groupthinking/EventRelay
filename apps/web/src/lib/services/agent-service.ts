/**
 * Agent service — dispatch and monitor agent executions.
 */

import { apiClient } from '../api-client';
import type {
  AgentDispatchRequest,
  AgentDispatchResponse,
  AgentStatusResponse,
} from '../types';

export const agentService = {
  /** Dispatch agents to process extracted events. */
  async dispatch(req: AgentDispatchRequest) {
    return apiClient.post<AgentDispatchResponse>('/api/v1/agents/dispatch', req);
  },

  /** Get the current status of an agent execution. */
  async getStatus(agentId: string) {
    return apiClient.get<AgentStatusResponse>(`/api/v1/agents/${agentId}/status`);
  },
};
