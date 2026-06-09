/**
 * Zustand store for the Transcription-Driven Action Agent.
 *
 * Holds a single `PromptLifecycle` and drives it through the state machine
 * (`action-lifecycle.ts`) by calling the real API routes:
 *   - `/api/transcribe`      → audio/URL to transcript
 *   - `/api/agents/actions`  → transcript to executed tool calls (fulfilment)
 *
 * The server route extracts and fulfils actions atomically, so on the client we
 * advance `extracting → dispatching → fulfilled` once the response lands. This
 * keeps every lifecycle phase observable for the dashboard without simulating
 * progress (REAL_MODE_ONLY).
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

interface SourceInput {
  url?: string;
  audioUrl?: string;
  videoTitle?: string;
}

interface ActionAgentState {
  lifecycle: PromptLifecycle;
  isRunning: boolean;
  /** Full flow: capture → transcribe (via /api/transcribe) → extract+fulfil actions. */
  runFromSource: (input: SourceInput) => Promise<void>;
  /** Skip capture/transcription and run the agent on an existing transcript. */
  runFromTranscript: (transcript: string, videoTitle?: string) => Promise<void>;
  reset: () => void;
}

export const useActionAgentStore = create<ActionAgentState>((set, get) => {
  /** Apply a lifecycle event to the current state. */
  function apply(event: LifecycleEvent) {
    set((s) => ({ lifecycle: reduceLifecycle(s.lifecycle, event) }));
  }

  /** Call /api/agents/actions and advance through dispatching → fulfilled. */
  async function fulfilActions(transcript: string, videoTitle?: string): Promise<void> {
    const jobId = get().lifecycle.id;
    const res = await fetch('/api/agents/actions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript, videoTitle, jobId }),
    });
    const body = await res.json();

    if (!res.ok || !body.success) {
      apply({ type: 'ERROR', error: body.error || `Action agent failed (${res.status})` });
      return;
    }

    const actions = (body.actions ?? []) as AgentAction[];
    // The server already executed the tools, so the actions arrive resolved.
    apply({ type: 'ACTIONS_EXTRACTED', actions: actions.map((a) => ({ ...a, status: 'pending' })), provider: body.provider });
    apply({ type: 'ACTIONS_FULFILLED', actions });
  }

  return {
    lifecycle: createLifecycle(newId()),
    isRunning: false,

    async runFromTranscript(transcript, videoTitle) {
      if (get().isRunning) return;
      set({ isRunning: true, lifecycle: createLifecycle(newId()) });
      try {
        // Jump straight to a known transcript: capture → transcribe are implicit.
        apply({ type: 'START_CAPTURE' });
        apply({ type: 'AUDIO_CAPTURED' });
        apply({ type: 'TRANSCRIBED', transcript });
        await fulfilActions(transcript, videoTitle);
      } catch (err) {
        apply({ type: 'ERROR', error: err instanceof Error ? err.message : String(err) });
      } finally {
        set({ isRunning: false });
      }
    },

    async runFromSource({ url, audioUrl, videoTitle }) {
      if (get().isRunning) return;
      set({ isRunning: true, lifecycle: createLifecycle(newId()) });
      try {
        apply({ type: 'START_CAPTURE' });
        apply({ type: 'AUDIO_CAPTURED' });

        const res = await fetch('/api/transcribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, audioUrl }),
        });
        const body = await res.json();

        if (!res.ok || !body.success || !body.transcript) {
          apply({ type: 'ERROR', error: body.error || `Transcription failed (${res.status})` });
          return;
        }

        apply({ type: 'TRANSCRIBED', transcript: body.transcript });
        await fulfilActions(body.transcript, videoTitle || body.metadata?.title);
      } catch (err) {
        apply({ type: 'ERROR', error: err instanceof Error ? err.message : String(err) });
      } finally {
        set({ isRunning: false });
      }
    },

    reset() {
      set({ lifecycle: createLifecycle(newId()), isRunning: false });
    },
  };
});
