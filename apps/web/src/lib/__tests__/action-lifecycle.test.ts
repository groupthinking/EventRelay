import { describe, it, expect } from 'vitest';
import {
  canTransition,
  createLifecycle,
  isComplete,
  reduceLifecycle,
  type AgentAction,
  type PromptLifecycle,
} from '@/lib/action-lifecycle';

const NOW = () => '2026-01-01T00:00:00.000Z';

function fresh(): PromptLifecycle {
  return createLifecycle('p1', NOW);
}

const ACTIONS: AgentAction[] = [
  { tool: 'create_workflow_task', input: { title: 'X' }, status: 'fulfilled', result: 'Created task "X"' },
];

describe('action lifecycle state machine', () => {
  it('starts idle with no actions', () => {
    const s = fresh();
    expect(s.phase).toBe('idle');
    expect(s.actions).toEqual([]);
  });

  it('walks the full happy path to fulfilled', () => {
    let s = fresh();
    s = reduceLifecycle(s, { type: 'START_CAPTURE' }, NOW);
    expect(s.phase).toBe('capturing');
    s = reduceLifecycle(s, { type: 'AUDIO_CAPTURED' }, NOW);
    expect(s.phase).toBe('transcribing');
    s = reduceLifecycle(s, { type: 'TRANSCRIBED', transcript: 'hello world' }, NOW);
    expect(s.phase).toBe('extracting');
    expect(s.transcript).toBe('hello world');
    s = reduceLifecycle(s, { type: 'ACTIONS_EXTRACTED', actions: ACTIONS, provider: 'openai' }, NOW);
    expect(s.phase).toBe('dispatching');
    expect(s.provider).toBe('openai');
    s = reduceLifecycle(s, { type: 'ACTIONS_FULFILLED', actions: ACTIONS }, NOW);
    expect(s.phase).toBe('fulfilled');
    expect(isComplete(s)).toBe(true);
  });

  it('coerces an illegal transition into failed with a descriptive error', () => {
    const s = fresh();
    const next = reduceLifecycle(s, { type: 'TRANSCRIBED', transcript: 'x' }, NOW);
    expect(next.phase).toBe('failed');
    expect(next.error).toContain('Illegal transition: TRANSCRIBED from idle');
  });

  it('accepts ERROR from any non-terminal phase', () => {
    let s = reduceLifecycle(fresh(), { type: 'START_CAPTURE' }, NOW);
    s = reduceLifecycle(s, { type: 'ERROR', error: 'mic denied' }, NOW);
    expect(s.phase).toBe('failed');
    expect(s.error).toBe('mic denied');
  });

  it('RESET only applies from terminal phases and clears state', () => {
    const failed = reduceLifecycle(fresh(), { type: 'TRANSCRIBED', transcript: 'x' }, NOW);
    expect(failed.phase).toBe('failed');
    const reset = reduceLifecycle(failed, { type: 'RESET' }, NOW);
    expect(reset.phase).toBe('idle');
    expect(reset.error).toBeUndefined();
    expect(reset.id).toBe('p1');
  });

  it('canTransition matches the reducer rules', () => {
    expect(canTransition('idle', 'START_CAPTURE')).toBe(true);
    expect(canTransition('idle', 'TRANSCRIBED')).toBe(false);
    expect(canTransition('transcribing', 'ERROR')).toBe(true);
    expect(canTransition('fulfilled', 'ERROR')).toBe(false);
    expect(canTransition('fulfilled', 'RESET')).toBe(true);
    expect(canTransition('idle', 'RESET')).toBe(false);
  });

  it('isComplete is false until fulfilled', () => {
    const s = reduceLifecycle(fresh(), { type: 'START_CAPTURE' }, NOW);
    expect(isComplete(s)).toBe(false);
  });
});
