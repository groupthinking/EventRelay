/**
 * Agent service — dispatch and monitor agent executions.
 */
import type { AgentDispatchRequest, AgentDispatchResponse, AgentStatusResponse } from '../types';
export declare const agentService: {
    /** Dispatch agents to process extracted events. */
    dispatch(req: AgentDispatchRequest): Promise<import("../types").ApiResponse<AgentDispatchResponse>>;
    /** Get the current status of an agent execution. */
    getStatus(agentId: string): Promise<import("../types").ApiResponse<AgentStatusResponse>>;
    /** Send an A2A inter-agent message. */
    sendA2AMessage(params: {
        sender?: string;
        recipient: string;
        content: Record<string, unknown>;
        conversation_id?: string;
    }): Promise<import("../types").ApiResponse<{
        conversation_id: string;
        timestamp: string;
    }>>;
    /** Get A2A message log (optionally filtered by conversation). */
    getA2ALog(conversationId?: string, limit?: number): Promise<import("../types").ApiResponse<{
        messages: Record<string, unknown>[];
        count: number;
    }>>;
};
