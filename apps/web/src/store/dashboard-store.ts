/**
 * Zustand store for studio video records.
 *
 * `processVideo` starts one durable Workflow run and only marks a record
 * complete when the persisted result includes verified source evidence and a
 * passing quality gate. Failures stay failures; progress reflects observed
 * run state rather than timers.
 */

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type {
  ExtractedEvent,
  AgentExecution,
} from '@/lib/types';
import type {
  Action,
  PipelineResult,
  SearchResult,
  Video,
} from '@/store/dashboard-types';
import { formatSeconds } from '@/lib/timestamp';
import { emitVideoPack, type VideoPackCitation } from '@/lib/emit-video-pack';
import {
  pollVideoToActions,
  startVideoToActions,
} from '@/lib/studio-workflow';
import type { VideoToActionsResult } from '@/lib/studio-workflow';
import type { TranscriptSegment } from '@/lib/analysis-evidence';
import { compileLinkedSop } from '@/lib/linked-sop';

export type {
  Action,
  PipelineResult,
  SearchResult,
  Video,
} from '@/store/dashboard-types';

export const ANALYSIS_STOPPED_MESSAGE =
  'Analysis stopped in this browser. Server work already accepted may continue.';

interface DashboardState {
  // Data
  videos: Video[];
  selectedVideoId: string | null;
  loading: boolean;

  // Computed
  selectedVideo: () => Video | undefined;

  // Actions
  addVideo: (video: Video) => void;
  updateVideo: (id: string, patch: Partial<Video>) => void;
  removeVideo: (id: string) => void;
  selectVideo: (id: string | null) => void;
  setLoading: (loading: boolean) => void;

  // Workflow actions
  processVideo: (url: string, opts?: { signal?: AbortSignal }) => Promise<string>;

  // Search actions
  searchQuery: string;
  searchResults: SearchResult[];
  searchLoading: boolean;
  setSearchQuery: (query: string) => void;
}

/** Trim a URL for display in titles/activity. */
function truncate(value: string, max: number): string {
  return value.length > max ? value.substring(0, max - 3) + '…' : value;
}

function formatVerifiedTranscript(segments: TranscriptSegment[]): string | undefined {
  if (segments.length === 0) return undefined;
  const hasTimings = segments.some((segment) => segment.duration > 0);
  const text = segments
    .map((segment) => hasTimings
      ? `[${formatSeconds(segment.start)}] ${segment.text}`
      : segment.text)
    .join('\n')
    .trim();
  return text || undefined;
}

function normalizeDashboardActions(value: unknown): Action[] {
  if (!Array.isArray(value)) return [];

  return value.flatMap((item) => {
    if (typeof item === 'string' && item.trim()) {
      return [{
        title: item.trim(),
        description: '',
        category: 'recommended',
        estimatedMinutes: null,
      }];
    }
    if (!item || typeof item !== 'object') return [];

    const candidate = item as Record<string, unknown>;
    const title = typeof candidate.title === 'string' ? candidate.title.trim() : '';
    if (!title) return [];
    return [{
      title,
      description: typeof candidate.description === 'string' ? candidate.description : '',
      category:
        typeof candidate.category === 'string' && candidate.category.trim()
          ? candidate.category
          : 'recommended',
      estimatedMinutes:
        typeof candidate.estimatedMinutes === 'number' ? candidate.estimatedMinutes : null,
    }];
  });
}

function verifiedResultPatch(
  id: string,
  runId: string,
  result: VideoToActionsResult | undefined,
  pack?: VideoPackCitation,
): Partial<Video> {
  const analysis = result?.analysis;
  const provenance = result?.provenance;
  const quality = result?.quality;
  if (!analysis || !provenance || !quality?.passed) {
    throw new Error(
      quality?.issues.join(' ') || 'Workflow completed without a verified analysis envelope.',
    );
  }

  const transcript = formatVerifiedTranscript(analysis.transcript || []);
  const actions = normalizeDashboardActions(analysis.actions);
  const linkedSop = compileLinkedSop({
    transcript,
    segments: analysis.transcript || [],
    events: (analysis.events || []).map((event) => ({
      timestamp: event.timestamp,
      label: event.label,
      description: event.description,
    })),
    actions,
    topics: analysis.topics || [],
    packTools: pack?.pack.stack?.tools,
  });
  const events: ExtractedEvent[] = (analysis.events || []).map((event, index) => ({
    id: `evt_${id}_${index}`,
    type: 'insight',
    title: event.label,
    description: event.description,
    timestamp: Number.isFinite(event.timestamp) ? String(event.timestamp) : undefined,
    sourceSegment: event.codeMapping || undefined,
  }));
  const agents: AgentExecution[] = [
    {
      agent_id: `${runId}:acquisition`,
      agent_type: 'Transcript Acquisition',
      status: 'complete',
      progress: 100,
      result: {
        source: provenance.transcriptSource,
        segments: provenance.segmentCount,
        contentSha256: provenance.contentSha256,
      },
    },
    {
      agent_id: `${runId}:analysis`,
      agent_type: 'Evidence Analysis',
      status: 'complete',
      progress: 100,
      result: { provider: result.provider, actions: result.actionCount },
    },
    {
      agent_id: `${runId}:quality`,
      agent_type: 'Evidence Quality Gate',
      status: 'complete',
      progress: 100,
      result: { state: quality.state, validationPassed: quality.passed },
    },
  ];

  return {
    status: 'complete',
    progress: 100,
    pipelineMode: 'workflow',
    title: truncate(analysis.title || 'Verified video analysis', 60),
    processedAt: new Date().toISOString(),
    duration: `${provenance.segmentCount} segments`,
    transcript,
    events,
    agents,
    provenance,
    quality,
    failure: undefined,
    insights: {
      summary: analysis.summary,
      actions,
      sentiment: 'Unscored',
      topics: analysis.topics || [],
      linkedSop,
      ...(analysis.project_scaffold != null
        ? { project_scaffold: analysis.project_scaffold }
        : {}),
    },
  };
}

function workflowFailurePatch(url: string, startedAt: string, message: string): Partial<Video> {
  const stage = /workflow|run id|start/i.test(message)
    ? 'start'
    : /transcript|caption|acquisition|speech-to-text/i.test(message)
      ? 'acquisition'
      : /quality|evidence|verified/i.test(message)
        ? 'quality'
        : 'analysis';
  const failedAt = new Date().toISOString();

  return {
    status: 'failed',
    progress: 100,
    title: `Analysis blocked: ${truncate(url, 38)}`,
    processedAt: failedAt,
    failure: {
      stage,
      message,
      retryable: stage !== 'quality',
      failedAt,
    },
    provenance: {
      sourceUrl: url,
      sourceHost: (() => {
        try { return new URL(url).hostname; } catch { return ''; }
      })(),
      acquisitionMethod: 'unavailable',
      transcriptSource: 'unknown',
      transcriptVerified: false,
      acquiredAt: startedAt,
      segmentCount: 0,
      timedSegmentCount: 0,
      durationCoverageSeconds: null,
      warnings: [message],
    },
    quality: {
      state: 'unavailable',
      passed: false,
      issues: [message],
      transcriptCharacters: 0,
      segmentCount: 0,
      timedSegmentCount: 0,
      checkedAt: failedAt,
    },
    insights: {
      summary: 'Analysis was not generated because source evidence could not be verified.',
      actions: [],
      sentiment: 'Unscored',
      topics: [],
    },
  };
}

let persistenceSucceeded = false;
export function dashboardPersistenceSucceeded(): boolean {
  return persistenceSucceeded;
}

const dashboardStorage = {
  getItem: (name: string) => {
    try {
      if (typeof window === 'undefined') return null;
      const value = window.localStorage.getItem(name);
      persistenceSucceeded = true;
      return value;
    } catch { persistenceSucceeded = false; return null; }
  },
  setItem: (name: string, value: string) => {
    persistenceSucceeded = false;
    try {
      if (typeof window === 'undefined') return;
      window.localStorage.setItem(name, value);
      persistenceSucceeded = true;
    } catch { /* Keep the updated in-memory state usable when storage is denied or full. */ }
  },
  removeItem: (name: string) => {
    try {
      if (typeof window !== 'undefined') window.localStorage.removeItem(name);
    } catch { persistenceSucceeded = false; }
  },
};

function isStoredVideo(value: unknown): value is Video {
  if (!value || typeof value !== 'object') return false;
  const row = value as Record<string, unknown>;
  return typeof row.id === 'string' && typeof row.title === 'string' && typeof row.url === 'string'
    && typeof row.progress === 'number' && Number.isFinite(row.progress)
    && ['processing', 'complete', 'failed'].includes(String(row.status));
}
export const useDashboardStore = create<DashboardState>()(
  persist(
    (set, get) => ({
  videos: [],
  selectedVideoId: null,
  loading: false,

  searchQuery: '',
  searchResults: [],
  searchLoading: false,

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

  selectVideo: (id) => set({
    selectedVideoId: id,
    searchQuery: '',
    searchResults: [],
    searchLoading: false,
  }),

  setLoading: (loading) => set({ loading }),
  setSearchQuery: (query) => set({ searchQuery: query }),

  // ── Process a video URL through one durable, evidence-gated workflow ──
  processVideo: async (url, opts) => {
    const { addVideo, updateVideo } = get();
    const signal = opts?.signal;
    const id = crypto.randomUUID();
    const startedAt = new Date().toISOString();

    addVideo({
      id,
      title: `Analyzing: ${truncate(url, 50)}`,
      url,
      status: 'processing',
      progress: 0,
      pipelineMode: 'workflow',
    });

    let locallyStopped = false;
    const stopLocalAnalysis = () => {
      if (locallyStopped) return;
      locallyStopped = true;
      updateVideo(id, {
        status: 'failed',
        title: `Analysis stopped: ${truncate(url, 38)}`,
        failure: {
          stage: 'analysis',
          message: ANALYSIS_STOPPED_MESSAGE,
          retryable: true,
          failedAt: new Date().toISOString(),
        },
      });
    };
    signal?.addEventListener('abort', stopLocalAnalysis, { once: true });

    try {
      signal?.throwIfAborted();
      const videoPack = await emitVideoPack(url, { signal });
      signal?.throwIfAborted();
      updateVideo(id, { videoPack, progress: 5 });

      const started = await startVideoToActions({ url, signal });
      // Preserve a known accepted run for later readback, even if local waiting stopped.
      if (started.runId) {
        updateVideo(id, {
          runId: started.runId,
          statusUrl: started.statusUrl || `/api/workflows/video-to-actions/${encodeURIComponent(started.runId)}`,
        });
      }
      signal?.throwIfAborted();
      if (!started.ok || !started.runId) {
        throw new Error(
          `Workflow start failed: ${started.error || started.message || 'no run ID returned.'}`,
        );
      }

      updateVideo(id, {
        runId: started.runId,
        statusUrl: started.statusUrl || `/api/workflows/video-to-actions/${encodeURIComponent(started.runId)}`,
        progress: 10,
      });

      const terminal = await pollVideoToActions(started.runId, {
        statusUrl: started.statusUrl,
        attempts: 180,
        delayMs: 2000,
        signal,
      });

      signal?.throwIfAborted();

      if (terminal.runStatus !== 'completed') {
        if (terminal.runStatus === 'running' || terminal.runStatus === 'pending') {
          updateVideo(id, { status: 'processing', progress: 10 });
          return id;
        }
        throw new Error(terminal.error || terminal.message || `Workflow ${terminal.runStatus || 'failed'}.`);
      }

      updateVideo(id, verifiedResultPatch(id, started.runId, terminal.result, videoPack));
    } catch (error) {
      if (signal?.aborted) {
        stopLocalAnalysis();
        return id;
      }
      const message = error instanceof Error ? error.message : 'Analysis failed.';
      updateVideo(id, workflowFailurePatch(url, startedAt, message));
    } finally {
      signal?.removeEventListener('abort', stopLocalAnalysis);
    }

    return id;
  },
}),
    {
      name: 'eventrelay-dashboard-v1',
      partialize: (state) => ({
        videos: state.videos,
      }),
      storage: createJSONStorage(() => dashboardStorage),
      merge: (persisted, current) => {
        if (!persisted || typeof persisted !== 'object') return current;
        const saved = persisted as Record<string, unknown>;
        return {
          ...current,
          videos: Array.isArray(saved.videos) ? saved.videos.filter(isStoredVideo) : current.videos,
        };
      },
      skipHydration: true,
    },
  ),
);
