/**
 * Zustand store for the Transcription-Driven Action Agent.
 *
 * Holds a single `PromptLifecycle` and drives it through the state machine
 * (`action-lifecycle.ts`) by calling the real API routes:
 *   - `/api/transcribe`      → audio/URL to transcript
 *   - `/api/agents/actions`  → review-only tool plan, then explicit fulfilment
 *
 * Preparation and execution are deliberately separate. The client advances to
 * `dispatching` after a plan is prepared, and only reaches `fulfilled` after a
 * second, explicit user confirmation executes that exact plan.
 */

import { create } from 'zustand';
import {
  createLifecycle,
  reduceLifecycle,
  type AgentAction,
  type LifecycleEvent,
  type PromptLifecycle,
} from '@/lib/action-lifecycle';

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `prompt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Upper bound on each API round-trip. Transcription of long sources is the
 * slowest leg, so this matches the serverless function ceiling rather than a
 * typical request; without it a hung fetch leaves `isRunning` stuck forever.
 */
const REQUEST_TIMEOUT_MS = 300_000;

const ACTION_STATUSES = ['pending', 'fulfilled', 'failed'] as const;

/** Runtime guard for action payloads coming back from /api/agents/actions. */
function isAgentAction(value: unknown): value is AgentAction {
  if (!value || typeof value !== 'object') return false;
  const a = value as Record<string, unknown>;
  return (
    typeof a.tool === 'string' &&
    typeof a.input === 'object' &&
    a.input !== null &&
    typeof a.status === 'string' &&
    (ACTION_STATUSES as readonly string[]).includes(a.status)
  );
}

interface SourceInput {
  url?: string;
  audioUrl?: string;
  videoTitle?: string;
}

interface ActionAgentState {
  lifecycle: PromptLifecycle;
  isRunning: boolean;
  /** Video whose transcript produced the current plan. Prevents cross-video confirmation. */
  sourceVideoId: string | null;
  /** Full flow: capture → transcribe (via /api/transcribe) → extract+fulfil actions. */
  runFromSource: (input: SourceInput) => Promise<void>;
  /** Skip capture/transcription and run the agent on an existing transcript. */
  runFromTranscript: (transcript: string, videoTitle?: string, sourceVideoId?: string) => Promise<void>;
  /** Execute the exact prepared action list after explicit review. */
  confirmPreparedActions: (selectedActions?: AgentAction[], expectedVideoId?: string) => Promise<void>;
  reset: () => void;
}

export const useActionAgentStore = create<ActionAgentState>((set, get) => {
  /** Apply a lifecycle event to the current state. */
  function apply(event: LifecycleEvent) {
    set((s) => ({ lifecycle: reduceLifecycle(s.lifecycle, event) }));
  }

  /** Ask the model for a review-only action plan. No tool executes here. */
  async function prepareActions(transcript: string, videoTitle?: string): Promise<void> {
    const jobId = get().lifecycle.id;
    const res = await fetch('/api/agents/actions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'preview', transcript, videoTitle, jobId }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    const body = await res.json();

    if (!res.ok || !body.success) {
      apply({ type: 'ERROR', error: body.error || `Action agent failed (${res.status})` });
      return;
    }

    const actions: AgentAction[] = Array.isArray(body.actions)
      ? body.actions.filter(isAgentAction)
      : [];
    apply({ type: 'ACTIONS_EXTRACTED', actions, provider: body.provider });
    if (actions.length === 0) apply({ type: 'ACTIONS_FULFILLED', actions });
  }

  return {
    lifecycle: createLifecycle(newId()),
    isRunning: false,
    sourceVideoId: null,

    async runFromTranscript(transcript, videoTitle, sourceVideoId) {
      if (get().isRunning) return;
      set({ isRunning: true, lifecycle: createLifecycle(newId()), sourceVideoId: sourceVideoId ?? null });
      try {
        // Jump straight to a known transcript: capture → transcribe are implicit.
        apply({ type: 'START_CAPTURE' });
        apply({ type: 'AUDIO_CAPTURED' });
        apply({ type: 'TRANSCRIBED', transcript });
        await prepareActions(transcript, videoTitle);
      } catch (err) {
        apply({ type: 'ERROR', error: err instanceof Error ? err.message : String(err) });
      } finally {
        set({ isRunning: false });
      }
    },

    async runFromSource({ url, audioUrl, videoTitle }) {
      if (get().isRunning) return;
      set({ isRunning: true, lifecycle: createLifecycle(newId()), sourceVideoId: null });
      try {
        apply({ type: 'START_CAPTURE' });
        apply({ type: 'AUDIO_CAPTURED' });

        const res = await fetch('/api/transcribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, audioUrl }),
          signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
        const body = await res.json();

        if (!res.ok || !body.success || !body.transcript) {
          apply({ type: 'ERROR', error: body.error || `Transcription failed (${res.status})` });
          return;
        }

        apply({ type: 'TRANSCRIBED', transcript: body.transcript });
        await prepareActions(body.transcript, videoTitle || body.metadata?.title);
      } catch (err) {
        apply({ type: 'ERROR', error: err instanceof Error ? err.message : String(err) });
      } finally {
        set({ isRunning: false });
      }
    },

    async confirmPreparedActions(selectedActions, expectedVideoId) {
      if (get().isRunning || get().lifecycle.phase !== 'dispatching') return;
      if (expectedVideoId && get().sourceVideoId !== expectedVideoId) {
        return;
      }
      const { id: jobId, actions: preparedActions } = get().lifecycle;
      const actions = selectedActions ?? preparedActions;
      if (actions.length === 0) return;
      set({ isRunning: true });
      try {
        const res = await fetch('/api/agents/actions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: 'execute', actions, jobId }),
          signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
        const body = await res.json();
        if (!res.ok || !body.success) {
          apply({ type: 'ERROR', error: body.error || `Action execution failed (${res.status})` });
          return;
        }
        const fulfilled: AgentAction[] = Array.isArray(body.actions)
          ? body.actions.filter(isAgentAction)
          : [];
        apply({ type: 'ACTIONS_FULFILLED', actions: fulfilled });
      } catch (err) {
        apply({ type: 'ERROR', error: err instanceof Error ? err.message : String(err) });
      } finally {
        set({ isRunning: false });
      }
    },

    reset() {
      set({ lifecycle: createLifecycle(newId()), isRunning: false, sourceVideoId: null });
    },
  };
});
