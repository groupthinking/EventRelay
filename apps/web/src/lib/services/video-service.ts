/**
 * Video service — handles video processing workflow via backend API.
 */

import { apiClient } from '../api-client';
import type {
  VideoProcessJobRequest,
  VideoProcessJobResponse,
  VideoJobStatusResponse,
} from '../types';

export const videoService = {
  /** Start async video processing. Returns job_id for polling. */
  async processVideo(req: VideoProcessJobRequest) {
    return apiClient.post<VideoProcessJobResponse>('/api/v1/videos/process', req);
  },

  /** Poll the status of a video-processing job. */
  async getJobStatus(jobId: string) {
    return apiClient.get<VideoJobStatusResponse>(`/api/v1/videos/${jobId}/status`);
  },

  /**
   * Poll until a job reaches a terminal state (complete | failed).
   * Calls `onProgress` on each poll so the UI can update.
   */
  async waitForCompletion(
    jobId: string,
    onProgress?: (status: VideoJobStatusResponse) => void,
    intervalMs = 2000,
    timeoutMs = 300_000,
  ): Promise<VideoJobStatusResponse> {
    const start = Date.now();

    // eslint-disable-next-line no-constant-condition
    while (true) {
      const res = await this.getJobStatus(jobId);

      if (res.status === 'error') {
        throw new Error(res.error || 'Failed to poll job status');
      }

      const data = res.data!;
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
