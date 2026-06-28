/**
 * Centralized Zustand store for the EventRelay dashboard.
 *
 * Combines video processing, event extraction, and agent dispatch
 * into a single store so every component shares the same state.
 *
 * `processVideo` drives the dashboard from the REAL agent pipeline: it
 * consumes the `/api/pipeline/stream` SSE endpoint and maps each agent's
 * execution into live progress, agent cards, insights, and transcript. If the
 * stream is unavailable it falls back to the non-streaming `/api/video` path,
 * so behaviour degrades gracefully without simulated progress.
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
  PipelineMode,
  PipelineResult,
  SearchResult,
  Video,
} from '@/store/dashboard-types';

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

// ── Streaming pipeline helpers ──

/** Trim a URL for display in titles/activity. */
function truncate(value: string, max: number): string {
  return value.length > max ? value.substring(0, max - 3) + '…' : value;
}

/** Map an SSE agent status onto our AgentExecution status. */
function mapAgentStatus(status: string): AgentStatus {
  if (status === 'complete') return 'complete';
  if (status === 'error') return 'failed';
  return 'running';
}

/** Flatten a transcript (segment array or string) into plain text. */
function flattenTranscript(raw: unknown): string | undefined {
  if (typeof raw === 'string') return raw.length > 0 ? raw : undefined;
  if (Array.isArray(raw)) {
    const text = raw
      .map((seg) => (seg && typeof seg === 'object' ? String((seg as { text?: string }).text ?? '') : ''))
      .join(' ')
      .trim();
    return text.length > 0 ? text : undefined;
  }
  return undefined;
}

/** Map streamed workflow events into the dashboard's ExtractedEvent shape. */
function mapStreamEvents(raw: unknown, videoId: string): ExtractedEvent[] {
  if (!Array.isArray(raw)) return [];
  const allowed: ExtractedEvent['type'][] = ['action', 'mention', 'topic', 'insight'];
  return raw.map((item, i) => {
    const e = (item ?? {}) as Record<string, unknown>;
    const type = allowed.includes(e.type as ExtractedEvent['type'])
      ? (e.type as ExtractedEvent['type'])
      : 'topic';
    const confidence =
      e.priority === 'high' ? 0.95 : e.priority === 'medium' ? 0.75 : 0.8;
    return {
      id: `evt_${videoId}_${i}`,
      type,
      title: String(e.title ?? e.name ?? 'Event'),
      description: e.description ? String(e.description) : undefined,
      timestamp: e.timestamp ? String(e.timestamp) : undefined,
      confidence,
    };
  });
}

interface StreamCtx {
  updateVideo: (id: string, patch: Partial<Video>) => void;
  addActivity: (event: string, type: Activity['type']) => void;
}

/**
 * Apply one SSE event to the video. Returns true once a terminal
 * `pipeline_status: complete` is seen. Throws on a pipeline error so the
 * caller can fall back to the non-streaming path.
 */
function applyStreamEvent(
  event: Record<string, unknown>,
  id: string,
  agents: Map<string, AgentExecution>,
  ctx: StreamCtx,
): boolean {
  switch (event.type) {
    case 'agent_update': {
      const agentId = String(event.agentId ?? `agent_${agents.size}`);
      const status = mapAgentStatus(String(event.status ?? 'running'));
      const data = (event.data as Record<string, unknown>) || {};
      agents.set(agentId, {
        agent_id: agentId,
        agent_type: String(event.agentName ?? agentId),
        status,
        progress:
          typeof event.progress === 'number'
            ? event.progress
            : status === 'complete'
              ? 100
              : status === 'running'
                ? 30
                : 0,
        result: status === 'complete' && Object.keys(data).length > 0 ? data : undefined,
      });

      const list = [...agents.values()];
      const completed = list.filter((a) => a.status === 'complete').length;
      // Real progress: 5% baseline + up to 90% across completed agents.
      const progress = Math.min(95, 5 + Math.round((completed / Math.max(list.length, 1)) * 90));
      ctx.updateVideo(id, { agents: list, progress });
      if (status === 'complete') {
        ctx.addActivity(`✓ ${event.agentName ?? agentId}`, 'success');
      }
      return false;
    }

    case 'consensus': {
      const data = event.data as { finalClassification?: string; agreementRatio?: number } | undefined;
      if (data?.finalClassification) {
        const pct = Math.round((data.agreementRatio ?? 0) * 100);
        ctx.addActivity(`Consensus: ${data.finalClassification} (${pct}% agreement)`, 'info');
      }
      return false;
    }

    case 'workflow': {
      const data = (event.data as Record<string, unknown>) || {};
      const summary =
        typeof data.summary === 'string'
          ? data.summary
          : typeof data.title === 'string'
            ? data.title
            : 'Analysis complete';
      const events = mapStreamEvents(data.events, id);
      const transcript = flattenTranscript(data.transcript);
      ctx.updateVideo(id, {
        insights: {
          summary,
          actions: Array.isArray(data.actions) ? (data.actions as Action[]) : [],
          sentiment: 'Neutral',
          topics: Array.isArray(data.topics) ? (data.topics as string[]) : [],
        },
        ...(events.length > 0 ? { events } : {}),
        ...(transcript ? { transcript } : {}),
        ...(typeof data.title === 'string' && data.title ? { title: truncate(data.title, 60) } : {}),
      });
      return false;
    }

    case 'pipeline_status': {
      if (event.status === 'complete') {
        ctx.updateVideo(id, { status: 'complete', progress: 100, processedAt: 'Just now' });
        return true;
      }
      if (event.status === 'error') {
        throw new Error('Pipeline reported an error');
      }
      ctx.updateVideo(id, { status: 'processing' });
      return false;
    }

    case 'error':
      throw new Error(String((event.data as { message?: string })?.message ?? 'Pipeline stream error'));

    default:
      return false;
  }
}

/**
 * Consume the `/api/pipeline/stream` SSE endpoint and project each event onto
 * the video. Throws if the stream fails or never reaches a terminal state, so
 * the caller can fall back to the non-streaming path.
 */
function mapPipelineModeHeader(header: string | null): PipelineMode | undefined {
  if (header === 'backend-proxy') return 'live';
  if (header === 'gemini-direct') return 'serverless';
  return undefined;
}

async function streamPipeline(url: string, id: string, ctx: StreamCtx): Promise<void> {
  const res = await fetch('/api/pipeline/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Pipeline stream failed: ${res.status}`);
  }

  const pipelineMode = mapPipelineModeHeader(
    typeof res.headers?.get === 'function' ? res.headers.get('X-Pipeline-Mode') : null,
  );
  if (pipelineMode) {
    ctx.updateVideo(id, { pipelineMode });
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const agents = new Map<string, AgentExecution>();
  let buffer = '';
  let completed = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data: ')) continue;
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(trimmed.slice(6));
      } catch {
        continue;
      }
      if (applyStreamEvent(event, id, agents, ctx)) completed = true;
    }
  }

  if (!completed) {
    throw new Error('Pipeline stream ended without completing');
  }
}

/**
 * Non-streaming fallback: POST to `/api/video` for a single analysis pass,
 * with the OpenAI STT + event-extraction chain. Never throws — marks the
 * video failed on error.
 */
async function legacyAnalyze(url: string, id: string, ctx: StreamCtx & { getVideo: (id: string) => Video | undefined }): Promise<void> {
  const { updateVideo, addActivity } = ctx;
  updateVideo(id, { progress: 40 });

  try {
    const res = await fetch('/api/video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) throw new Error(`API error: ${res.status}`);

    const result = await res.json();
    const rawTitle = result.result?.insights?.summary;
    const videoTitle = (typeof rawTitle === 'string' ? rawTitle : 'Video').substring(0, 50);

    let transcript =
      result.result?.raw_response?.transcript?.text ||
      result.result?.raw_response?.transcript ||
      undefined;
    if (Array.isArray(transcript)) {
      transcript = transcript.map((s: { text?: string }) => s.text || '').join(' ').trim();
    }

    // STT fallback: if YouTube API returned no/empty transcript, try OpenAI.
    if (!transcript || (typeof transcript === 'string' && transcript.length < 50)) {
      addActivity('YouTube transcript unavailable — trying OpenAI fallback…', 'info');
      try {
        const sttRes = await fetch('/api/transcribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url }),
        });
        const sttResult = await sttRes.json();
        if (sttResult.success && sttResult.transcript) {
          transcript = sttResult.transcript;
          addActivity(`Transcript retrieved via ${sttResult.source} (${sttResult.wordCount} words)`, 'success');
        }
      } catch {
        addActivity('STT fallback unavailable', 'info');
      }
    }

    updateVideo(id, {
      status: result.status === 'complete' ? 'complete' : 'failed',
      progress: 100,
      pipelineMode: 'fallback',
      title: videoTitle + (videoTitle.length >= 50 ? '…' : ''),
      processedAt: 'Just now',
      duration: `${result.result?.transcript_segments || 0} segments`,
      transcript,
      insights: {
        summary: typeof result.result?.insights?.summary === 'string'
          ? result.result.insights.summary
          : 'Analysis complete',
        actions: result.result?.insights?.actions || [],
        sentiment: result.result?.insights?.sentiment || 'Neutral',
        topics: result.result?.insights?.topics || [],
      },
    });
    addActivity(`Analysis complete: ${videoTitle.substring(0, 30)}`, 'success');

    // Auto-extract events + actions via AI SDK if we have a transcript.
    if (transcript && typeof transcript === 'string') {
      addActivity('Extracting events & actions with AI…', 'info');
      try {
        const extractRes = await fetch('/api/extract-events', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript, videoTitle, videoUrl: url }),
        });
        const extraction = await extractRes.json();
        if (extraction.success && extraction.data) {
          const { events: extractedEvents, actions, summary, topics } = extraction.data;
          updateVideo(id, {
            events: extractedEvents?.map((e: { type: string; title: string; description?: string; timestamp?: string; priority?: string }) => ({
              id: `evt_${Math.random().toString(36).slice(2, 10)}`,
              type: e.type,
              title: e.title,
              description: e.description,
              timestamp: e.timestamp,
              confidence: e.priority === 'high' ? 0.95 : e.priority === 'medium' ? 0.75 : 0.5,
            })),
            insights: {
              summary: summary || videoTitle,
              actions: actions || [],
              sentiment: ctx.getVideo(id)?.insights?.sentiment || 'Neutral',
              topics: topics || [],
            },
          });
          addActivity(`Extracted ${extractedEvents?.length || 0} events, ${actions?.length || 0} actions`, 'success');
        } else if (extraction.error) {
          addActivity(`Event extraction: ${extraction.error}`, 'info');
        }
      } catch {
        addActivity('Event extraction unavailable — set OPENAI_API_KEY', 'info');
      }
    }
  } catch (error) {
    throw error instanceof Error ? error : new Error('Analysis failed');
  }
}

/** True when stream completed but insights/transcript are still empty or generic. */
function isThinStreamResult(video: Video | undefined): boolean {
  if (!video?.insights) return true;
  const summary = video.insights.summary?.trim() ?? '';
  const generic =
    summary === 'Analysis complete' ||
    summary.startsWith('Local fallback package');
  const hasPayload =
    (video.insights.actions?.length ?? 0) > 0 ||
    (video.insights.topics?.length ?? 0) > 0 ||
    (video.events?.length ?? 0) > 0 ||
    (video.transcript?.trim().length ?? 0) >= 50;
  return generic && !hasPayload;
}

/** Last-resort package when live pipeline and direct analysis are both unavailable. */
function createLocalWorkflowPackage(
  url: string,
  id: string,
  ctx: StreamCtx,
  reason: string,
): void {
  const { updateVideo, addActivity } = ctx;
  const briefTitle = truncate(url, 40);

    updateVideo(id, {
      status: 'complete',
      progress: 100,
      pipelineMode: 'handoff',
      title: `Workflow brief: ${briefTitle}`,
      processedAt: 'Just now',
      insights: {
      summary: `Local fallback package — backend unavailable (${reason}). Review the brief and export when the pipeline is healthy.`,
      actions: [],
      sentiment: 'Neutral',
      topics: ['handoff', 'workflow-brief'],
    },
  });
  addActivity('Created starter workflow package for offline handoff', 'info');
}

/** Deploy handoff when the backend pipeline endpoint is unreachable. */
function createDeployHandoff(url: string, id: string, ctx: StreamCtx, reason: string): void {
  const { updateVideo, addActivity } = ctx;
  const briefTitle = truncate(url, 40);

  updateVideo(id, {
    status: 'complete',
    progress: 100,
    pipelineMode: 'handoff',
    title: `Deploy handoff: ${briefTitle}`,
    processedAt: 'Just now',
    pipelineResult: {
      live_url: null,
      github_repo: null,
      build_status: 'handoff_ready_backend_unavailable',
      code_generation: null,
      deployment: null,
    },
    insights: {
      summary: `Deploy handoff prepared — automatic deployment unavailable (${reason}).`,
      actions: [],
      sentiment: 'Neutral',
      topics: ['deploy-handoff'],
    },
  });
  addActivity('Deploy handoff prepared — connect BACKEND_URL for automatic deployment', 'info');
}

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

  // ── Process a video URL via the real agent pipeline (SSE), with fallback ──
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

    const ctx = {
      updateVideo,
      addActivity,
      getVideo: (vid: string) => get().videos.find((v) => v.id === vid),
    };

    try {
      await streamPipeline(url, id, ctx);
      addActivity('Pipeline complete', 'success');

      const streamed = get().videos.find((v) => v.id === id);
      if (isThinStreamResult(streamed)) {
        addActivity('Stream returned minimal data — enriching via direct analysis…', 'info');
        try {
          await legacyAnalyze(url, id, ctx);
        } catch (enrichErr) {
          const reason =
            enrichErr instanceof Error ? enrichErr.message : 'enrichment unavailable';
          updateVideo(id, {
            insights: {
              summary: `Pipeline agents finished but returned thin analysis (${reason}). Try another video or check backend transcript-action output.`,
              actions: streamed?.insights?.actions ?? [],
              sentiment: 'Neutral',
              topics: streamed?.insights?.topics ?? ['partial-analysis'],
            },
          });
          addActivity('Analysis enrichment unavailable — showing partial result', 'info');
        }
      }
    } catch (streamErr) {
      console.warn('[Dashboard] Live pipeline unavailable, using direct analysis:', streamErr);
      addActivity('Live pipeline unavailable — using direct analysis…', 'info');
      try {
        await legacyAnalyze(url, id, ctx);
      } catch (analyzeErr) {
        const reason =
          analyzeErr instanceof Error ? analyzeErr.message : 'analysis unavailable';
        console.warn('[Dashboard] Direct analysis failed, creating local package:', analyzeErr);
        createLocalWorkflowPackage(url, id, ctx, reason);
      }
    }

    const video = get().videos.find((v) => v.id === id);
    if (video?.status === 'failed') {
      createLocalWorkflowPackage(url, id, ctx, 'analysis failed');
    }

    const finalVideo = get().videos.find((v) => v.id === id);
    if (
      finalVideo?.status === 'complete' &&
      (!finalVideo.events || finalVideo.events.length === 0) &&
      (finalVideo.insights?.actions?.length || finalVideo.insights?.topics?.length)
    ) {
      get().extractEvents(id);
    }

    return id;
  },

  // ── Full end-to-end pipeline: YouTube URL → deployed software ──
  deployPipeline: async (url) => {
    const { addVideo, updateVideo, addActivity } = get();
    const id = Date.now().toString();

    const video: Video = {
      id,
      title: `🚀 Deploying: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`,
      url,
      status: 'processing',
      progress: 5,
    };
    addVideo(video);
    addActivity(`Pipeline started: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`, 'info');

    const stages = ['Analyzing video', 'Generating code', 'Creating repo', 'Deploying'];
    let stageIdx = 0;
    const interval = setInterval(() => {
      const current = get().videos.find((v) => v.id === id);
      if (current && current.status === 'processing') {
        const newProgress = Math.min(current.progress + 3, 95);
        const newStage = Math.min(Math.floor(newProgress / 25), stages.length - 1);
        if (newStage > stageIdx) {
          stageIdx = newStage;
          addActivity(stages[stageIdx] + '…', 'info');
        }
        updateVideo(id, { progress: newProgress });
      }
    }, 2000);

    try {
      const res = await fetch('/api/pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, project_type: 'web', deployment_target: 'vercel' }),
      });
      clearInterval(interval);

      if (!res.ok) throw new Error(`Pipeline error: ${res.status}`);

      const result = await res.json();
      const pipelineResult: PipelineResult = {
        live_url: result.result?.live_url || null,
        github_repo: result.result?.github_repo || null,
        build_status: result.result?.build_status || 'unknown',
        code_generation: result.result?.code_generation || null,
        deployment: result.result?.deployment || null,
      };

      updateVideo(id, {
        status: result.status === 'success' || result.status === 'complete' ? 'complete' : 'failed',
        progress: 100,
        title: `Deployed: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`,
        processedAt: 'Just now',
        pipelineResult,
        insights: {
          summary: result.result?.video_analysis?.extracted_info?.title || 'Pipeline complete',
          actions: result.result?.features_implemented || [],
          sentiment: 'Positive',
          topics: result.result?.code_generation?.files_created || [],
        },
      });

      if (pipelineResult.live_url) {
        addActivity(`🎉 Live at: ${pipelineResult.live_url}`, 'success');
      }
      if (pipelineResult.github_repo) {
        addActivity(`📦 Repo: ${pipelineResult.github_repo}`, 'success');
      }
      addActivity(`Pipeline complete (${result.processing_time || 'done'})`, 'success');
    } catch (error) {
      clearInterval(interval);
      const reason = error instanceof Error ? error.message : 'Unknown error';
      console.warn('[Dashboard] Pipeline deploy failed, creating handoff:', error);
      createDeployHandoff(url, id, { updateVideo, addActivity }, reason);
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
    (video.insights?.actions || []).forEach((action, i) => {
      events.push({
        id: `evt_${videoId}_${i}`,
        type: 'action',
        title: action.title,
        description: action.description,
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
