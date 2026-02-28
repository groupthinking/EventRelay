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

  /** Send an A2A inter-agent message. */
  async sendA2AMessage(params: {
    sender?: string;
    recipient: string;
    content: Record<string, unknown>;
    conversation_id?: string;
  }) {
    return apiClient.post<{ conversation_id: string; timestamp: string }>(
      '/api/v1/agents/a2a/send',
      params,
    );
  },

  /** Get A2A message log (optionally filtered by conversation). */
  async getA2ALog(conversationId?: string, limit = 50) {
    const params = new URLSearchParams();
    if (conversationId) params.set('conversation_id', conversationId);
    params.set('limit', String(limit));
    return apiClient.get<{ messages: Record<string, unknown>[]; count: number }>(
      `/api/v1/agents/a2a/log?${params}`,
    );
  },
};
