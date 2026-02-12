/**
 * Centralized Zustand store for the EventRelay dashboard.
 *
 * Combines video processing, event extraction, and agent dispatch
 * into a single store so every component shares the same state.
 */

import { create } from 'zustand';
import type {
  ExtractedEvent,
  AgentExecution,
  VideoJobStatusResponse,
} from '@/lib/types';

// ── Types ──

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
  agents?: AgentExecution[];
  insights?: {
    summary: string;
    actions: string[];
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

  // Actions
  addVideo: (video: Video) => void;
  updateVideo: (id: string, patch: Partial<Video>) => void;
  removeVideo: (id: string) => void;
  selectVideo: (id: string | null) => void;
  addActivity: (event: string, type: Activity['type']) => void;
  setLoading: (loading: boolean) => void;

  // Workflow actions
  processVideo: (url: string) => Promise<void>;
  extractEvents: (videoId: string) => void;
  dispatchAgents: (videoId: string) => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  videos: [],
  activities: [],
  selectedVideoId: null,
  loading: true,

  selectedVideo: () => {
    const { videos, selectedVideoId } = get();
    return videos.find((v) => v.id === selectedVideoId);
  },

  addVideo: (video) =>
    set((s) => ({ videos: [video, ...s.videos] })),

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

  // ── Process a video URL via the Next.js API route ──
  processVideo: async (url) => {
    const { addVideo, updateVideo, addActivity } = get();
    const id = Date.now().toString();

    const video: Video = {
      id,
      title: `Analyzing: ${url.length > 50 ? url.substring(0, 47) + '…' : url}`,
      url,
      status: 'processing',
      progress: 10,
    };
    addVideo(video);
    addActivity(`Processing started: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`, 'info');

    // Simulate incremental progress
    const interval = setInterval(() => {
      const current = get().videos.find((v) => v.id === id);
      if (current && current.status === 'processing') {
        updateVideo(id, { progress: Math.min(current.progress + 5, 95) });
      }
    }, 1000);

    try {
      const res = await fetch('/api/video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      clearInterval(interval);

      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const result = await res.json();
      const videoTitle = result.result?.insights?.summary?.substring(0, 50) || 'Video';

      updateVideo(id, {
        status: result.status === 'complete' ? 'complete' : 'failed',
        progress: 100,
        title: videoTitle + (videoTitle.length >= 50 ? '…' : ''),
        processedAt: 'Just now',
        duration: `${result.result?.transcript_segments || 0} segments`,
        transcript:
          result.result?.raw_response?.transcript?.text ||
          result.result?.raw_response?.transcript ||
          undefined,
        insights: {
          summary: result.result?.insights?.summary || 'Analysis complete',
          actions: result.result?.insights?.actions || [],
          sentiment: result.result?.insights?.sentiment || 'Neutral',
          topics: result.result?.insights?.topics || [],
        },
      });

      const actionCount = result.result?.insights?.actions?.length || 0;
      addActivity(`Analysis complete: ${videoTitle.substring(0, 30)}`, 'success');
      if (actionCount > 0) {
        addActivity(`Generated ${actionCount} action item${actionCount > 1 ? 's' : ''}`, 'success');
      }
    } catch (error) {
      clearInterval(interval);
      updateVideo(id, { status: 'failed', progress: 0 });
      addActivity(
        `Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'error',
      );
    }
  },

  // ── Extract events from a completed video ──
  extractEvents: (videoId) => {
    const { videos, updateVideo, addActivity } = get();
    const video = videos.find((v) => v.id === videoId);
    if (!video) return;

    addActivity('Extracting events…', 'info');

    const events: ExtractedEvent[] = [];

    // Derive events from insights
    (video.insights?.actions || []).forEach((action, i) => {
      events.push({
        id: `evt_${videoId}_${i}`,
        type: 'action',
        title: action,
        confidence: 0.85,
      });
    });
    (video.insights?.topics || []).forEach((topic, i) => {
      events.push({
        id: `evt_${videoId}_t${i}`,
        type: 'topic',
        title: topic,
        confidence: 0.9,
      });
    });

    updateVideo(videoId, { events });
    addActivity(`Extracted ${events.length} events`, 'success');
  },

  // ── Dispatch agents for extracted events ──
  dispatchAgents: (videoId) => {
    const { videos, updateVideo, addActivity } = get();
    const video = videos.find((v) => v.id === videoId);
    if (!video?.events?.length) return;

    addActivity('Dispatching agents…', 'info');

    const agentTypes = ['analyzer', 'content_creator'];
    const executions: AgentExecution[] = video.events.slice(0, 5).flatMap((event) =>
      agentTypes.map((agentType) => ({
        agent_id: `agent_${videoId}_${event.id}_${agentType}`,
        agent_type: agentType,
        status: 'running' as const,
        progress: 0,
        event_id: event.id,
      })),
    );

    updateVideo(videoId, { agents: executions });

    // Simulate agent completion
    executions.forEach((exec) => {
      setTimeout(() => {
        const currentVideo = get().videos.find((v) => v.id === videoId);
        if (!currentVideo) return;

        const completed: AgentExecution = {
          ...exec,
          status: 'complete',
          progress: 100,
          result: {
            summary: `Processed by ${exec.agent_type}`,
            output: `Analysis complete for event ${exec.event_id}`,
          },
        };

        updateVideo(videoId, {
          agents: (currentVideo.agents || []).map((a) =>
            a.agent_id === exec.agent_id ? completed : a,
          ),
        });
      }, 1500 + Math.random() * 3000);
    });

    addActivity(`Dispatched ${executions.length} agents`, 'success');
  },
}));
