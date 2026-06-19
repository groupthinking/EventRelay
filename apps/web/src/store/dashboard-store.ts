/**
 * Centralized Zustand store for the EventRelay dashboard.
 *
 * SC7: the dashboard is a PURE consumer of the backend contract. Every data
 * value comes from an `eventRelay.*` call against the clean `/api/v1/jobs`
 * API — there is no client-side transcription, event extraction, model call,
 * or synthetic agent mesh in here. If the backend is unreachable the video is
 * marked `failed`; the UI never falls back to calling a model.
 *
 *   submitJob ─▶ poll status ─▶ getTranscript / getEvents / getArtifacts
 */

import { create } from 'zustand';
import type { ExtractedEvent } from '@/lib/types';
import {
  eventRelay,
  EventRelayError,
  type EventItem,
  type Artifacts,
  type JobStatus,
} from '@/lib/eventrelay-client';

// ── Types ──

export interface Action {
  title: string;
  description: string;
  category: string;
  estimatedMinutes?: number | null;
}

export interface Video {
  id: string;
  title: string;
  url: string;
  status: 'processing' | 'complete' | 'failed';
  progress: number;
  thumbnail?: string;
  duration?: string;
  processedAt?: string;
  transcript?: string;
  events?: ExtractedEvent[];
  insights?: {
    summary: string;
    actions: Action[];
    sentiment: string;
    topics: string[];
  };
}

export interface Activity {
  time: string;
  event: string;
  type: 'success' | 'info' | 'error';
}

interface DashboardState {
  // Data
  videos: Video[];
  activities: Activity[];
  selectedVideoId: string | null;
  loading: boolean;

  // Computed
  selectedVideo: () => Video | undefined;

  // Mutators
  addVideo: (video: Video) => void;
  updateVideo: (id: string, patch: Partial<Video>) => void;
  removeVideo: (id: string) => void;
  selectVideo: (id: string | null) => void;
  addActivity: (event: string, type: Activity['type']) => void;
  setLoading: (loading: boolean) => void;

  // Workflow
  processVideo: (url: string) => Promise<string>;
}

// ── Contract → view mappers ──

/**
 * Create a display-friendly string truncated to at most `max` characters.
 *
 * @param value - The input string (e.g., a URL) to truncate
 * @param max - Maximum allowed length of the returned string, including the ellipsis if added
 * @returns The original string when its length is less than or equal to `max`; otherwise a truncated string that ends with the Unicode ellipsis character `…`
 */
function truncate(value: string, max: number): string {
  return value.length > max ? value.substring(0, max - 3) + '…' : value;
}

const EXTRACTED_TYPES: ReadonlySet<ExtractedEvent['type']> = new Set([
  'action',
  'mention',
  'topic',
  'insight',
]);

/**
 * Convert a backend EventItem into a normalized ExtractedEvent suitable for display.
 *
 * @param e - Backend event object containing `type`, `payload`, and `ts`.
 * @param i - Zero-based index used to generate the event `id` as `evt_<i>`.
 * @returns The normalized ExtractedEvent:
 * - `id`: `evt_<i>`
 * - `type`: first taxonomy segment present in `EXTRACTED_TYPES`, or `'topic'` if none
 * - `title`: `payload.title` or `payload.name` or `payload.text`, falling back to the original `e.type`
 * - `description`: `payload.description` (if present)
 * - `timestamp`: `payload.timestamp` or `e.ts`
 * - `confidence`: numeric `payload.confidence` or `0.8` by default
 */
function toExtractedEvent(e: EventItem, i: number): ExtractedEvent {
  const p = e.payload ?? {};
  // Display category comes from whichever taxonomy segment names one
  // (e.g. youtube.action.created → action, youtube.topic.detected → topic).
  const segment = e.type
    .split('.')
    .find((s): s is ExtractedEvent['type'] => EXTRACTED_TYPES.has(s as ExtractedEvent['type']));
  const type: ExtractedEvent['type'] = segment ?? 'topic';
  const str = (k: string): string | undefined =>
    typeof p[k] === 'string' ? (p[k] as string) : undefined;
  return {
    id: `evt_${i}`,
    type,
    title: str('title') ?? str('name') ?? str('text') ?? e.type,
    description: str('description'),
    timestamp: str('timestamp') ?? e.ts,
    confidence: typeof p.confidence === 'number' ? (p.confidence as number) : 0.8,
  };
}

/**
 * Convert backend Artifacts into the dashboard's insights object.
 *
 * @param a - Artifacts returned by the backend (may contain `insights`, `tasks`, and `summary`)
 * @returns An insights object with `summary`, `actions`, `sentiment`, and `topics` populated from `a`. `actions` is derived from `a.tasks` (each task becomes an action with category `Task`), `sentiment` falls back to `"Neutral"` when not provided as a string, and `topics` is an array when available.
 */
function toInsights(a: Artifacts): NonNullable<Video['insights']> {
  const ins = a.insights ?? {};
  return {
    summary: a.summary || 'Analysis complete',
    actions: (a.tasks ?? []).map((t) => ({
      title: t,
      description: '',
      category: 'Task',
    })),
    sentiment: typeof ins.sentiment === 'string' ? (ins.sentiment as string) : 'Neutral',
    topics: Array.isArray(ins.topics) ? (ins.topics as string[]) : [],
  };
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  videos: [],
  activities: [],
  selectedVideoId: null,
  loading: false,

  selectedVideo: () => {
    const { videos, selectedVideoId } = get();
    return videos.find((v) => v.id === selectedVideoId);
  },

  addVideo: (video) => set((s) => ({ videos: [video, ...s.videos] })),

  updateVideo: (id, patch) =>
    set((s) => ({
      videos: s.videos.map((v) => (v.id === id ? { ...v, ...patch } : v)),
    })),

  removeVideo: (id) =>
    set((s) => ({
      videos: s.videos.filter((v) => v.id !== id),
      selectedVideoId: s.selectedVideoId === id ? null : s.selectedVideoId,
    })),

  selectVideo: (id) => set({ selectedVideoId: id }),

  addActivity: (event, type) => {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    set((s) => ({
      activities: [{ time, event, type }, ...s.activities].slice(0, 30),
    }));
  },

  setLoading: (loading) => set({ loading }),

  // ── Submit a YouTube URL and drive the real job lifecycle to completion ──
  processVideo: async (url) => {
    const { addVideo, updateVideo, addActivity } = get();
    const id = Date.now().toString();

    addVideo({
      id,
      title: `Analyzing: ${truncate(url, 50)}`,
      url,
      status: 'processing',
      progress: 5,
    });
    addActivity(`Processing started: ${truncate(url, 40)}`, 'info');

    try {
      const { job_id } = await eventRelay.submitJob({ video_url: url });
      updateVideo(id, { progress: 20 });

      // Poll the real status lifecycle (queued → running → succeeded/failed).
      let status: JobStatus = 'queued';
      for (;;) {
        const job = await eventRelay.getJob(job_id);
        status = job.status;
        if (status === 'succeeded' || status === 'failed') break;
        updateVideo(id, { progress: status === 'running' ? 60 : 30 });
        await new Promise((r) => setTimeout(r, 2000));
      }

      if (status === 'failed') {
        updateVideo(id, { status: 'failed', progress: 0 });
        addActivity('Job failed on the backend', 'error');
        return id;
      }

      updateVideo(id, { progress: 85 });
      const [transcript, events, artifacts] = await Promise.all([
        eventRelay.getTranscript(job_id),
        eventRelay.getEvents(job_id),
        eventRelay.getArtifacts(job_id),
      ]);

      const insights = toInsights(artifacts);
      updateVideo(id, {
        status: 'complete',
        progress: 100,
        processedAt: 'Just now',
        title: truncate(insights.summary, 60),
        transcript: transcript || undefined,
        events: events.map(toExtractedEvent),
        insights,
      });
      addActivity(
        `Analysis complete: ${events.length} events, ${artifacts.tasks.length} tasks`,
        'success',
      );
    } catch (error) {
      const message =
        error instanceof EventRelayError
          ? error.message
          : error instanceof Error
            ? error.message
            : 'Unknown error';
      updateVideo(id, { status: 'failed', progress: 0 });
      addActivity(`Analysis failed: ${message}`, 'error');
    }

    return id;
  },
}));
