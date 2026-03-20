"use strict";
/**
 * Event service — extract events from transcripts.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.eventService = void 0;
const api_client_1 = require("../api-client");
exports.eventService = {
    /** Extract events from a transcript or completed job. */
    async extractEvents(req) {
        return api_client_1.apiClient.post('/api/v1/events/extract', req);
    },
};
//# sourceMappingURL=event-service.js.map