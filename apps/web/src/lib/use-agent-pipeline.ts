/**
 * useAgentPipeline — React hook for real-time agent pipeline visualization.
 *
 * Connects to `/api/pipeline/stream` (SSE) and maps incoming events into
 * PipelineState that drives the existing visualization components.
 *
 * Three modes:
 *   - 'live'       — SSE backed by FastAPI backend (BACKEND_URL configured)
 *   - 'serverless' — SSE backed by Gemini (no backend, has GEMINI key)
 *   - 'demo'       — local simulation fallback (no keys at all)
 */

'use client';

import { useCallback, useRef, useState } from 'react';
import type {
  AgentNode,
  ConsensusResult,
  PipelineState,
  TraceStep,
} from './agent-types';
import {
  createDefaultAgents,
  createDefaultConnections,
  simulatePipeline,
} from './agent-pipeline';

export type PipelineMode = 'idle' | 'live' | 'serverless' | 'demo';

export interface UseAgentPipelineReturn {
  state: PipelineState;
  mode: PipelineMode;
  startPipeline: (url: string) => void;
  resetPipeline: () => void;
}

function makeInitialState(): PipelineState {
  return {
    id: 'default',
    videoUrl: '',
    videoTitle: '',
    status: 'idle',
    agents: createDefaultAgents(),
    connections: createDefaultConnections(),
    trace: [],
  };
}

/** Parse a raw SSE `data:` line into a typed object. */
function parseSSELine(line: string): Record<string, unknown> | null {
  if (!line.startsWith('data: ')) return null;
  try {
    return JSON.parse(line.slice(6));
  } catch {
    return null;
  }
}

/** Map SSE agentId to our internal agent record key. */
const SSE_TO_INTERNAL_ID: Record<string, string> = {
  orchestrator: 'orchestrator',
  router: 'router',
  crew: 'crew',
  transcript_analyst: 'transcript',
  visual_analyst: 'visual',
  audio_analyst: 'audio',
  action_gen: 'action_gen',
  quality: 'quality',
};

export function useAgentPipeline(): UseAgentPipelineReturn {
  const [state, setState] = useState<PipelineState>(makeInitialState);
  const [mode, setMode] = useState<PipelineMode>('idle');
  const abortRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const simulationRef = useRef<{ cancel: () => void } | null>(null);

  /** Apply an `agent_update` SSE event to the current PipelineState. */
  const applyAgentUpdate = useCallback(
    (event: Record<string, unknown>) => {
      const sseAgentId = event.agentId as string;
      const internalId = SSE_TO_INTERNAL_ID[sseAgentId] || sseAgentId;
      const status = event.status as AgentNode['status'];
      const duration = (event.duration as number) || undefined;
      const data = (event.data as Record<string, unknown>) || {};

      setState((prev) => {
        // Update agent
        const agents = { ...prev.agents };
        if (agents[internalId]) {
          agents[internalId] = {
            ...agents[internalId],
            status,
            progress: status === 'complete' ? 100 : status === 'running' ? 30 : 0,
            executionTimeMs: duration ? duration * 1000 : agents[internalId].executionTimeMs,
          };
        }

        // Build trace step
        const agentName = (event.agentName as string) || agents[internalId]?.name || internalId;
        const agentRole = agents[internalId]?.role || 'orchestrator';
        const traceStep: TraceStep = {
          id: `trace_${prev.trace.length}`,
          agentId: internalId,
          agentName,
          agentRole,
          status,
          timestamp: (event.timestamp as string) || new Date().toISOString(),
          durationMs: duration ? duration * 1000 : undefined,
          input: status === 'running' ? { type: 'data', preview: 'Processing…' } : undefined,
          output: status === 'complete' && data
            ? { type: 'data', preview: Object.entries(data).map(([k, v]) => `${k}: ${v}`).join(', ') }
            : undefined,
        };

        // Update connections (activate when source completes)
        const connections = prev.connections.map((c) => {
          if (c.from === internalId && status === 'complete') {
            return { ...c, active: true };
          }
          if (c.to === internalId && status === 'running') {
            return { ...c, dataFlowing: true };
          }
          if (c.to === internalId && status === 'complete') {
            return { ...c, dataFlowing: false };
          }
          return c;
        });

        return {
          ...prev,
          agents,
          connections,
          trace: [...prev.trace, traceStep],
        };
      });
    },
    [],
  );

  /** Apply a `consensus` SSE event. */
  const applyConsensus = useCallback((event: Record<string, unknown>) => {
    const data = event.data as {
      votes: Array<{
        agentId: string;
        agentName: string;
        classification: string;
        confidence: number;
      }>;
      finalClassification: string;
      agreementRatio: number;
    };
    if (!data) return;

    const consensus: ConsensusResult = {
      finalClassification: data.finalClassification,
      agreementRatio: data.agreementRatio,
      method: '2-of-3',
      votes: data.votes.map((v) => ({
        agentId: SSE_TO_INTERNAL_ID[v.agentId] || v.agentId,
        agentName: v.agentName,
        classification: v.classification,
        confidence: v.confidence,
        agrees: v.classification === data.finalClassification,
      })),
    };

    setState((prev) => ({ ...prev, consensus }));
  }, []);

  /** Apply a `pipeline_status` SSE event. */
  const applyPipelineStatus = useCallback(
    (event: Record<string, unknown>) => {
      const status = event.status as string;
      const eventData = (event.data as Record<string, unknown>) || {};

      if (status === 'running') {
        const serverMode = eventData.mode as string;
        setMode(serverMode?.includes('backend') ? 'live' : 'serverless');
        setState((prev) => ({ ...prev, status: 'processing' }));
      } else if (status === 'complete') {
        setState((prev) => ({
          ...prev,
          status: 'complete',
          completedAt: new Date().toISOString(),
        }));
      } else if (status === 'error') {
        setState((prev) => ({ ...prev, status: 'error' }));
      }
    },
    [],
  );

  /** Apply a `workflow` SSE event. */
  const applyWorkflow = useCallback((event: Record<string, unknown>) => {
    const data = event.data as Record<string, unknown>;
    if (!data) return;

    const workflow = (data.workflow as string) || '';
    const title = (data.title as string) || '';
    const summary = (data.summary as string) || '';

    setState((prev) => ({
      ...prev,
      videoTitle: title || prev.videoTitle,
      outputWorkflow: `## ${title}\n\n${summary}\n\n### Actions\n${workflow}`,
    }));
  }, []);

  /** Start the pipeline. Tries SSE first, falls back to demo simulation. */
  const startPipeline = useCallback(
    (url: string) => {
      // Abort any in-flight request
      if (abortRef.current) abortRef.current.abort();
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
      if (simulationRef.current) simulationRef.current.cancel();

      const controller = new AbortController();
      let timedOut = false;
      abortRef.current = controller;
      // Match Vercel stream route budget (maxDuration 240s) — avoid demo fallback on slow backend jobs.
      const STREAM_WAIT_MS = 210_000;
      const resetStreamTimeout = () => {
        if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
        timeoutRef.current = window.setTimeout(() => {
          timedOut = true;
          controller.abort();
        }, STREAM_WAIT_MS);
      };
      timeoutRef.current = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, STREAM_WAIT_MS);

      // Reset state to validating
      setState({
        id: `pipeline_${Date.now()}`,
        videoUrl: url,
        videoTitle: `Processing: ${url.length > 50 ? url.substring(0, 47) + '…' : url}`,
        status: 'validating',
        startedAt: new Date().toISOString(),
        agents: createDefaultAgents(),
        connections: createDefaultConnections(),
        trace: [],
      });

      const runDemoFallback = (reason: unknown) => {
        console.warn('[AgentPipeline] SSE unavailable, falling back to demo:', reason);
        setMode('demo');

        const freshState: PipelineState = {
          id: `pipeline_${Date.now()}`,
          videoUrl: url,
          videoTitle: url,
          status: 'validating',
          startedAt: new Date().toISOString(),
          agents: createDefaultAgents(),
          connections: createDefaultConnections(),
          trace: [],
        };
        setState(freshState);

        simulationRef.current = simulatePipeline(url, url, (newState) => {
          setState(newState);
        });
      };

      // Try SSE endpoint
      fetch('/api/pipeline/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok || !response.body) {
            throw new Error(`Stream failed: ${response.status}`);
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let completed = false;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            resetStreamTimeout();

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed) continue;
              const event = parseSSELine(trimmed);
              if (!event) continue;

              switch (event.type) {
                case 'agent_update':
                  applyAgentUpdate(event);
                  break;
                case 'consensus':
                  applyConsensus(event);
                  break;
                case 'pipeline_status':
                  if (event.status === 'complete' || event.status === 'error') completed = true;
                  applyPipelineStatus(event);
                  break;
                case 'workflow':
                  applyWorkflow(event);
                  break;
                case 'error':
                  console.error('[AgentPipeline] Stream error:', event.data);
                  setState((prev) => ({ ...prev, status: 'error' }));
                  break;
              }
            }
          }

          if (!completed) {
            throw new Error('Stream ended before the pipeline completed');
          }
        })
        .finally(() => {
          if (timeoutRef.current) {
            window.clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }
        })
        .catch((err) => {
          if (controller.signal.aborted && !timedOut) return;
          runDemoFallback(timedOut ? new Error('Pipeline stream timed out') : err);
        });
    },
    [applyAgentUpdate, applyConsensus, applyPipelineStatus, applyWorkflow],
  );

  /** Reset everything to idle. */
  const resetPipeline = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    if (simulationRef.current) simulationRef.current.cancel();
    timeoutRef.current = null;
    simulationRef.current = null;
    setState(makeInitialState());
    setMode('idle');
  }, []);

  return { state, mode, startPipeline, resetPipeline };
}
