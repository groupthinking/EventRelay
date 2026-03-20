"use strict";
/**
 * Agent service — dispatch and monitor agent executions.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.agentService = void 0;
const api_client_1 = require("../api-client");
exports.agentService = {
    /** Dispatch agents to process extracted events. */
    async dispatch(req) {
        return api_client_1.apiClient.post('/api/v1/agents/dispatch', req);
    },
    /** Get the current status of an agent execution. */
    async getStatus(agentId) {
        return api_client_1.apiClient.get(`/api/v1/agents/${agentId}/status`);
    },
    /** Send an A2A inter-agent message. */
    async sendA2AMessage(params) {
        return api_client_1.apiClient.post('/api/v1/agents/a2a/send', params);
    },
    /** Get A2A message log (optionally filtered by conversation). */
    async getA2ALog(conversationId, limit = 50) {
        const params = new URLSearchParams();
        if (conversationId)
            params.set('conversation_id', conversationId);
        params.set('limit', String(limit));
        return api_client_1.apiClient.get(`/api/v1/agents/a2a/log?${params}`);
    },
};
//# sourceMappingURL=agent-service.js.map