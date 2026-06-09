/**
 * Lifecycle state machine for the Transcription-Driven Action Agent.
 *
 * Models a single "prompt" as it travels from audio capture through to action
 * fulfilment:
 *
 *   idle → capturing → transcribing → extracting → dispatching → fulfilled
 *
 * Any state can transition to `failed` (via an ERROR event), and `failed` /
 * `fulfilled` can be reset back to `idle`. The reducer is pure and free of any
 * framework or I/O so it can be unit-tested in isolation and reused by both the
 * Zustand store (browser) and the API route (server).
 */

// ── States ──

export type LifecyclePhase =
  | 'idle'
  | 'capturing'
  | 'transcribing'
  | 'extracting'
  | 'dispatching'
  | 'fulfilled'
  | 'failed';

/** A single executable action the agent decided to take from the transcript. */
export interface AgentAction {
  /** Tool name the model invoked, e.g. `create_workflow_task`. */
  tool: string;
  /** Arguments the model supplied for the tool. */
  input: Record<string, unknown>;
  /** Fulfilment status of this individual action. */
  status: 'pending' | 'fulfilled' | 'failed';
  /** Human-readable result summary once executed. */
  result?: string;
  /** Whether the underlying tool reported an error. */
  isError?: boolean;
}

/** The full record tracked for one prompt, from capture to fulfilment. */
export interface PromptLifecycle {
  id: string;
  phase: LifecyclePhase;
  /** Final transcript text (populated after `TRANSCRIBED`). */
  transcript?: string;
  /** Provider that produced the actions, e.g. `openai` / `gemini`. */
  provider?: string;
  /** Actions extracted from the transcript and their fulfilment status. */
  actions: AgentAction[];
  /** Populated when `phase === 'failed'`. */
  error?: string;
  startedAt: string;
  updatedAt: string;
}

// ── Events ──

export type LifecycleEvent =
  | { type: 'START_CAPTURE' }
  | { type: 'AUDIO_CAPTURED' }
  | { type: 'TRANSCRIBED'; transcript: string }
  | { type: 'ACTIONS_EXTRACTED'; actions: AgentAction[]; provider?: string }
  | { type: 'ACTIONS_FULFILLED'; actions: AgentAction[] }
  | { type: 'ERROR'; error: string }
  | { type: 'RESET' };

// ── Transition table ──

/**
 * Allowed phase transitions. `ERROR` and `RESET` are handled separately because
 * they are valid from (almost) any phase.
 */
const TRANSITIONS: Record<LifecyclePhase, Partial<Record<LifecycleEvent['type'], LifecyclePhase>>> = {
  idle: { START_CAPTURE: 'capturing' },
  capturing: { AUDIO_CAPTURED: 'transcribing' },
  transcribing: { TRANSCRIBED: 'extracting' },
  extracting: { ACTIONS_EXTRACTED: 'dispatching' },
  dispatching: { ACTIONS_FULFILLED: 'fulfilled' },
  fulfilled: {},
  failed: {},
};

/** Returns true if `event` is a legal transition from `phase`. */
export function canTransition(phase: LifecyclePhase, event: LifecycleEvent['type']): boolean {
  if (event === 'RESET') return phase === 'fulfilled' || phase === 'failed';
  if (event === 'ERROR') return phase !== 'fulfilled' && phase !== 'failed';
  return TRANSITIONS[phase]?.[event] !== undefined;
}

// ── Construction ──

export function createLifecycle(id: string, now: () => string = () => new Date().toISOString()): PromptLifecycle {
  const ts = now();
  return {
    id,
    phase: 'idle',
    actions: [],
    startedAt: ts,
    updatedAt: ts,
  };
}

// ── Reducer ──

/**
 * Pure reducer. Applies `event` to `state`, returning a new lifecycle. Illegal
 * transitions are coerced into the `failed` phase with a descriptive error
 * rather than throwing, so callers never crash on an unexpected event ordering.
 */
export function reduceLifecycle(
  state: PromptLifecycle,
  event: LifecycleEvent,
  now: () => string = () => new Date().toISOString(),
): PromptLifecycle {
  const updatedAt = now();

  if (event.type === 'RESET') {
    return createLifecycle(state.id, now);
  }

  if (event.type === 'ERROR') {
    return { ...state, phase: 'failed', error: event.error, updatedAt };
  }

  if (!canTransition(state.phase, event.type)) {
    return {
      ...state,
      phase: 'failed',
      error: `Illegal transition: ${event.type} from ${state.phase}`,
      updatedAt,
    };
  }

  const phase = TRANSITIONS[state.phase][event.type] as LifecyclePhase;

  switch (event.type) {
    case 'TRANSCRIBED':
      return { ...state, phase, transcript: event.transcript, updatedAt };
    case 'ACTIONS_EXTRACTED':
      return { ...state, phase, actions: event.actions, provider: event.provider, updatedAt };
    case 'ACTIONS_FULFILLED':
      return { ...state, phase, actions: event.actions, updatedAt };
    default:
      return { ...state, phase, updatedAt };
  }
}

/** Convenience: true once every extracted action has been resolved. */
export function isComplete(state: PromptLifecycle): boolean {
  return (
    state.phase === 'fulfilled' &&
    state.actions.every((a) => a.status === 'fulfilled' || a.status === 'failed')
  );
}
