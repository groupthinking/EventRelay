"use strict";
/**
 * Video service — handles video processing workflow via backend API.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.videoService = void 0;
const api_client_1 = require("../api-client");
exports.videoService = {
    /** Start async video processing. Returns job_id for polling. */
    async processVideo(req) {
        return api_client_1.apiClient.post('/api/v1/videos/process', req);
    },
    /** Poll the status of a video-processing job. */
    async getJobStatus(jobId) {
        return api_client_1.apiClient.get(`/api/v1/videos/${jobId}/status`);
    },
    /**
     * Poll until a job reaches a terminal state (complete | failed).
     * Calls `onProgress` on each poll so the UI can update.
     */
    async waitForCompletion(jobId, onProgress, intervalMs = 2000, timeoutMs = 300_000) {
        const start = Date.now();
        // eslint-disable-next-line no-constant-condition
        while (true) {
            const res = await this.getJobStatus(jobId);
            if (res.status === 'error') {
                throw new Error(res.error || 'Failed to poll job status');
            }
            const data = res.data;
            onProgress?.(data);
            if (data.status === 'complete' || data.status === 'failed') {
                return data;
            }
            if (Date.now() - start > timeoutMs) {
                throw new Error('Video processing timed out');
            }
            await new Promise((r) => setTimeout(r, intervalMs));
        }
    },
};
//# sourceMappingURL=video-service.js.map