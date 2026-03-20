/**
 * Videos resource — process YouTube videos and manage the video library.
 */

import type { EventRelayClient } from "../client";
import type {
  VideoProcessJobRequest,
  VideoProcessJobResponse,
  VideoJobStatusResponse,
} from "../types";

export class VideosResource {
  constructor(private readonly _client: EventRelayClient) {}

  /**
   * Submit a YouTube video for async processing.
   *
   * @param params - `video_url` is required; `language` and `options` are optional.
   * @returns `VideoProcessJobResponse` containing the `job_id`.
   */
  async process(params: VideoProcessJobRequest): Promise<VideoProcessJobResponse> {
    return this._client._post("/api/v1/videos/process", params) as Promise<VideoProcessJobResponse>;
  }

  /**
   * Poll processing status for a given job.
   *
   * @param jobId - The `job_id` returned by {@link process}.
   * @returns `VideoJobStatusResponse` with current status and progress.
   */
  async getStatus(jobId: string): Promise<VideoJobStatusResponse> {
    return this._client._get(`/api/v1/videos/${jobId}/status`) as Promise<VideoJobStatusResponse>;
  }

  /**
   * List all processed videos in the library.
   */
  async list(): Promise<unknown[]> {
    return this._client._get("/api/v1/videos") as Promise<unknown[]>;
  }

  /**
   * Retrieve metadata for a single video.
   *
   * @param videoId - YouTube video ID (11-character string).
   */
  async retrieve(videoId: string): Promise<unknown> {
    return this._client._get(`/api/v1/videos/${videoId}`);
  }

  /**
   * Remove a processed video from the cache.
   *
   * @param videoId - YouTube video ID.
   */
  async delete(videoId: string): Promise<unknown> {
    return this._client._delete(`/api/v1/cache/${videoId}`);
  }
}
