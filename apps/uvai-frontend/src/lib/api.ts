/**
 * UVAI API Client
 * Handles communication with the backend video analysis API
 */

export interface TranscriptActionRequest {
  youtube_url: string;
  action_type?: 'full_analysis' | 'transcript_only' | 'summary_only';
}

export interface VideoAnalysis {
  video_id: string;
  title?: string;
  duration?: number;
  transcript: string;
  summary?: string;
  key_insights?: string[];
  action_items?: ActionItem[];
  timestamps?: Timestamp[];
  metadata?: Record<string, unknown>;
}

export interface ActionItem {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed';
}

export interface Timestamp {
  time: number;
  label: string;
  description?: string;
}

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: string;
  message?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Validates a YouTube URL format
 */
export function validateYoutubeUrl(url: string): { isValid: boolean; error?: string } {
  if (!url) {
    return { isValid: false, error: 'URL is required' };
  }

  const patterns = [
    /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]{11}/,
    /^https?:\/\/youtu\.be\/[\w-]{11}/,
    /^https?:\/\/(www\.)?youtube\.com\/embed\/[\w-]{11}/,
    /^https?:\/\/(www\.)?youtube\.com\/shorts\/[\w-]{11}/,
  ];

  const isValid = patterns.some(pattern => pattern.test(url));

  if (!isValid) {
    return { isValid: false, error: 'Please enter a valid YouTube URL' };
  }

  return { isValid: true };
}

/**
 * Extracts video ID from YouTube URL
 */
export function extractVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([\w-]{11})/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) {
      return match[1];
    }
  }

  return null;
}

/**
 * Generates YouTube embed URL from video URL
 */
export function getYoutubeEmbedUrl(url: string): string {
  const videoId = extractVideoId(url);
  if (!videoId) return '';
  return `https://www.youtube.com/embed/${videoId}`;
}

/**
 * Analyzes a video using the backend API
 */
export async function analyzeVideo(
  request: TranscriptActionRequest
): Promise<ApiResponse<VideoAnalysis>> {
  try {
    const response = await fetch(`${API_BASE_URL}/transcript-action`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        status: 'error',
        error: errorData.detail || `Request failed with status ${response.status}`,
      };
    }

    const data = await response.json();
    return {
      status: 'success',
      data: data,
    };
  } catch (error) {
    return {
      status: 'error',
      error: error instanceof Error ? error.message : 'An unexpected error occurred',
    };
  }
}

/**
 * Checks API health status
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
