/**
 * Centralized Zustand store for the EventRelay dashboard.
 *
 * Combines video processing, event extraction, and agent dispatch
 * into a single store so every component shares the same state.
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
  AgentStatus,
} from '@/lib/types';
import type {
  Action,
  Activity,
  PipelineResult,
  SearchResult,
  Video,
} from '@/store/dashboard-types';
import { formatSeconds } from '@/lib/timestamp';
import { emitVideoPack } from '@/lib/emit-video-pack';
import {
  pollVideoToActions,
  startVideoToActions,
} from '@/lib/studio-workflow';
import type { VideoToActionsResult } from '@/lib/studio-workflow';
import type { TranscriptSegment } from '@/lib/analysis-evidence';
import { compileLinkedSop } from '@/lib/linked-sop';

export type {
  Action,
  Activity,
  PipelineResult,
  SearchResult,
  Video,
} from '@/store/dashboard-types';

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
  processVideo: (url: string) => Promise<string>;
  resumeProcessingRuns: () => Promise<void>;
  deployPipeline: (url: string) => Promise<void>;
  extractEvents: (videoId: string) => void;
  dispatchToAgents: (videoId: string) => Promise<void>;
  refreshAgentStatus: (videoId: string) => Promise<void>;

  // Search actions
  searchQuery: string;
  searchResults: SearchResult[];
  searchLoading: boolean;
  setSearchQuery: (query: string) => void;
  performSearch: (videoId: string, query: string) => Promise<void>;
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

const activeRunResumptions = new Set<string>();

const noopStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set, get) => ({
  videos: [],
  activities: [],
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

  addActivity: (event, type) => {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    set((s) => ({
      activities: [{ time, event, type }, ...s.activities].slice(0, 30),
    }));
  },

  setLoading: (loading) => set({ loading }),
  setSearchQuery: (query) => set({ searchQuery: query }),

  // ── Perform semantic RAG search against video chunks ──
  performSearch: async (videoId, query) => {
    if (!query.trim()) {
      set({ searchResults: [] });
      return;
    }

    set({ searchLoading: true });
    get().addActivity(`Searching for: "${query}"`, 'info');

    try {
      const res = await fetch(`/api/video/search?videoId=${encodeURIComponent(videoId)}&q=${encodeURIComponent(query)}`);
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = await res.json();
      set({ searchResults: data.results || [] });
      get().addActivity(`Found ${data.results?.length || 0} matching segments`, 'success');
    } catch (err) {
      console.error('Search error:', err);
      get().addActivity('Search failed. Video may not have finished embedding.', 'error');
      set({ searchResults: [] });
    } finally {
      set({ searchLoading: false });
    }
  },

  // ── Process a video URL through one durable, evidence-gated workflow ──
  processVideo: async (url) => {
    const { addVideo, updateVideo, addActivity } = get();
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
    addActivity(`Processing started: ${truncate(url, 40)}`, 'info');

    try {
      const videoPack = await emitVideoPack(url);
      updateVideo(id, { videoPack, progress: 5 });
      addActivity(`Video pack ${videoPack.version} ${videoPack.sourceHash.slice(0, 12)}`, 'success');

      const started = await startVideoToActions({ url });
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
      addActivity(`Durable run created: ${started.runId}`, 'success');

      const terminal = await pollVideoToActions(started.runId, {
        attempts: 180,
        delayMs: 2000,
      });

      if (terminal.runStatus !== 'completed') {
        if (terminal.runStatus === 'running' || terminal.runStatus === 'pending') {
          updateVideo(id, { status: 'processing', progress: 10 });
          addActivity(`Run still ${terminal.runStatus}; result remains addressable by run ID`, 'info');
          return id;
        }
        throw new Error(terminal.error || terminal.message || `Workflow ${terminal.runStatus || 'failed'}.`);
      }

      updateVideo(id, verifiedResultPatch(id, started.runId, terminal.result));
      addActivity('Verified analysis persisted by the durable workflow', 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Analysis failed.';
      updateVideo(id, workflowFailurePatch(url, startedAt, message));
      addActivity(`Analysis blocked: ${message}`, 'error');
    }

    return id;
  },

  // ── Resume durable runs that outlived a tab refresh or prior poll window ──
  resumeProcessingRuns: async () => {
    const candidates = get().videos.filter(
      (video) => video.status === 'processing' && Boolean(video.runId),
    );

    await Promise.all(candidates.map(async (video) => {
      const runId = video.runId;
      if (!runId || activeRunResumptions.has(runId)) return;
      activeRunResumptions.add(runId);
      try {
        const terminal = await pollVideoToActions(runId, {
          attempts: 180,
          delayMs: 2000,
        });
        if (terminal.runStatus === 'completed') {
          get().updateVideo(video.id, verifiedResultPatch(video.id, runId, terminal.result));
          get().addActivity(`Recovered verified durable run: ${runId}`, 'success');
          return;
        }
        if (terminal.runStatus === 'failed' || terminal.runStatus === 'cancelled') {
          const message = terminal.error || terminal.message || `Workflow ${terminal.runStatus}.`;
          get().updateVideo(
            video.id,
            workflowFailurePatch(video.url, video.processedAt || new Date().toISOString(), message),
          );
          get().addActivity(`Analysis blocked: ${message}`, 'error');
        }
      } catch (error) {
        get().addActivity(
          `Run recovery check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          'error',
        );
      } finally {
        activeRunResumptions.delete(runId);
      }
    }));
  },

  // ── Full end-to-end pipeline: YouTube URL → deployed software ──
  deployPipeline: async (url) => {
    const { addVideo, updateVideo, addActivity } = get();
    const id = crypto.randomUUID();

    const video: Video = {
      id,
      title: `Deploying: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`,
      url,
      status: 'processing',
      progress: 0,
      pipelineMode: 'live',
    };
    addVideo(video);
    addActivity(`Pipeline started: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`, 'info');

    try {
      const res = await fetch('/api/pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, project_type: 'web', deployment_target: 'vercel', async: true }),
      });
      if (!res.ok) throw new Error(`Pipeline error: ${res.status}`);

      const result = await res.json();
      // Support async kickoff response (job pending) vs full sync result
      const isAsyncPending = result.async_processing || result.status === 'pending' || !!result.job_id;
      const pipelineResult: PipelineResult = {
        live_url: (result.result || result).live_url || null,
        github_repo: (result.result || result).github_repo || null,
        build_status: (result.result || result).build_status || (isAsyncPending ? 'pending' : 'unknown'),
        code_generation: (result.result || result).code_generation || null,
        deployment: (result.result || result).deployment || null,
      };
      const terminalSuccess =
        !isAsyncPending &&
        (result.status === 'success' || result.status === 'complete') &&
        typeof pipelineResult.live_url === 'string' &&
        pipelineResult.live_url.startsWith('https://') &&
        !String(pipelineResult.build_status).includes('handoff') &&
        !String(pipelineResult.build_status).includes('fallback');
      const terminalFailure = !isAsyncPending && !terminalSuccess;
      const now = new Date().toISOString();

      updateVideo(id, {
        status: isAsyncPending ? 'processing' : terminalSuccess ? 'complete' : 'failed',
        progress: isAsyncPending ? 20 : 100,
        title: terminalSuccess
          ? `Deployed: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`
          : terminalFailure
            ? `Deployment blocked: ${url.length > 34 ? url.substring(0, 31) + '…' : url}`
            : `Deployment queued: ${url.length > 35 ? url.substring(0, 32) + '…' : url}`,
        processedAt: isAsyncPending ? undefined : now,
        pipelineResult,
        failure: terminalFailure
          ? {
              stage: 'deployment',
              message: result.message || 'Pipeline ended without a verified live deployment URL.',
              retryable: true,
              failedAt: now,
            }
          : undefined,
        insights: {
          summary:
            (result.result?.video_analysis?.extracted_info?.title || result.video_analysis?.title) ||
            (isAsyncPending
              ? 'Deployment job queued. Completion has not yet been verified.'
              : terminalSuccess
                ? 'Deployment verified with a live HTTPS URL.'
                : 'Deployment did not produce a verified live URL.'),
          actions: normalizeDashboardActions(
            result.result?.features_implemented || result.features_implemented,
          ),
          sentiment: 'Unscored',
          topics: (result.result?.code_generation?.files_created || result.code_generation?.files) || [],
        },
        jobId: result.job_id || result.id,
        statusUrl: result.status_url,
      });

      if (pipelineResult.live_url) {
        addActivity(`Live URL returned: ${pipelineResult.live_url}`, terminalSuccess ? 'success' : 'info');
      }
      if (pipelineResult.github_repo) {
        addActivity(`Repository: ${pipelineResult.github_repo}`, 'success');
      }
      addActivity(
        isAsyncPending
          ? 'Deployment job queued; awaiting a terminal status'
          : terminalSuccess
            ? `Deployment verified (${result.processing_time || 'duration unavailable'})`
            : 'Deployment blocked: no verified live result was returned',
        isAsyncPending ? 'info' : terminalSuccess ? 'success' : 'error',
      );
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Unknown error';
      const failedAt = new Date().toISOString();
      console.warn('[Dashboard] Pipeline deploy failed:', error);
      updateVideo(id, {
        status: 'failed',
        progress: 100,
        title: `Deployment blocked: ${truncate(url, 34)}`,
        processedAt: failedAt,
        pipelineResult: {
          live_url: null,
          github_repo: null,
          build_status: 'failed_backend_unavailable',
          code_generation: null,
          deployment: null,
        },
        failure: {
          stage: 'deployment',
          message: reason,
          retryable: true,
          failedAt,
        },
        insights: {
          summary: `Deployment was not completed: ${reason}`,
          actions: [],
          sentiment: 'Unscored',
          topics: [],
        },
      });
      addActivity(`Deployment blocked: ${reason}`, 'error');
    }
  },

  // ── Re-derive events from a completed video's insights ──
  extractEvents: (videoId) => {
    const { videos, updateVideo, addActivity } = get();
    const video = videos.find((v) => v.id === videoId);
    if (!video) return;

    addActivity('Extracting events…', 'info');

    const events: ExtractedEvent[] = [];

    // Derive events from insights
    normalizeDashboardActions(video.insights?.actions || []).forEach((action, i) => {
      events.push({
        id: `evt_${videoId}_${i}`,
        type: 'action',
        title: action.title,
        description: action.description,
      });
    });
    (video.insights?.topics || []).forEach((topic, i) => {
      events.push({
        id: `evt_${videoId}_t${i}`,
        type: 'topic',
        title: topic,
      });
    });

    updateVideo(videoId, { events });
    addActivity(`Extracted ${events.length} events`, 'success');
  },

  // ── Dispatch the video's events to the real backend agent + MCP layer ──
  dispatchToAgents: async (videoId) => {
    const { videos, updateVideo, addActivity } = get();
    const video = videos.find((v) => v.id === videoId);
    if (!video?.events?.length) {
      addActivity('No events to dispatch — extract events first', 'info');
      return;
    }

    addActivity(`Dispatching agents to act on ${video.events.length} events…`, 'info');
    try {
      const res = await fetch('/api/agents/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          events: video.events.map((e) => ({
            id: e.id,
            type: e.type,
            title: e.title,
            description: e.description,
          })),
          transcript: video.transcript,
        }),
      });

      if (res.status === 503) {
        addActivity('Agent backend offline — deploy FastAPI and set BACKEND_URL', 'info');
        return;
      }
      if (!res.ok) throw new Error(`Dispatch failed: ${res.status}`);

      const data = await res.json();
      const executions: AgentExecution[] = Array.isArray(data.executions) ? data.executions : [];
      updateVideo(videoId, { agents: executions });
      addActivity(`Dispatched ${executions.length} agents`, 'success');
    } catch (error) {
      addActivity(
        `Agent dispatch failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'error',
      );
    }
  },

  // ── Poll status for any running/queued dispatched agents ──
  refreshAgentStatus: async (videoId) => {
    const { videos, updateVideo } = get();
    const video = videos.find((v) => v.id === videoId);
    const pending = (video?.agents || []).filter(
      (a) => a.status === 'running' || a.status === 'queued',
    );
    if (pending.length === 0) return;

    const refreshed = await Promise.all(
      pending.map(async (agent) => {
        try {
          const res = await fetch(`/api/agents/status?agentId=${encodeURIComponent(agent.agent_id)}`);
          if (!res.ok) return agent;
          const data = await res.json();
          return {
            ...agent,
            status: (data.status as AgentStatus) || agent.status,
            progress: typeof data.progress === 'number' ? data.progress : agent.progress,
            result: data.result ?? agent.result,
            error: data.error ?? agent.error,
          } satisfies AgentExecution;
        } catch {
          return agent;
        }
      }),
    );

    const byId = new Map(refreshed.map((a) => [a.agent_id, a]));
    const merged = (get().videos.find((v) => v.id === videoId)?.agents || []).map(
      (a) => byId.get(a.agent_id) ?? a,
    );
    updateVideo(videoId, { agents: merged });
  },
}),
    {
      name: 'eventrelay-dashboard-v1',
      partialize: (state) => ({
        videos: state.videos,
        activities: state.activities,
      }),
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? localStorage : noopStorage,
      ),
      skipHydration: true,
    },
  ),
);
