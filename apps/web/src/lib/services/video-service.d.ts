/**
 * Video service — handles video processing workflow via backend API.
 */
import type { VideoProcessJobRequest, VideoProcessJobResponse, VideoJobStatusResponse } from '../types';
export declare const videoService: {
    /** Start async video processing. Returns job_id for polling. */
    processVideo(req: VideoProcessJobRequest): Promise<import("../types").ApiResponse<VideoProcessJobResponse>>;
    /** Poll the status of a video-processing job. */
    getJobStatus(jobId: string): Promise<import("../types").ApiResponse<VideoJobStatusResponse>>;
    /**
     * Poll until a job reaches a terminal state (complete | failed).
     * Calls `onProgress` on each poll so the UI can update.
     */
    waitForCompletion(jobId: string, onProgress?: (status: VideoJobStatusResponse) => void, intervalMs?: number, timeoutMs?: number): Promise<VideoJobStatusResponse>;
};
