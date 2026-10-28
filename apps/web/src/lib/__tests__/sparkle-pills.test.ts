import { describe, expect, it } from 'vitest';
import { resolveSparklePillsResponse } from '@/lib/sparkle-pills';

describe('sparkle-pills', () => {
  it('retains every supplied tool instead of truncating after eight entries', () => {
    const response = resolveSparklePillsResponse({
      query: 'Build me a system for using sparkle pills',
      sparkleInterview: {
        useCase: 'focus sessions',
        trigger: 'weekdays at 08:30',
        tools: ['Tool-1', 'Tool-2', 'Tool-3', 'Tool-4', 'Tool-5', 'Tool-6', 'Tool-7', 'Tool-8', 'Tool-9'],
        constraints: 'No notifications after 21:00',
        successSignal: '5 sessions each week',
      },
    });

    expect(response).not.toBeNull();
    expect(response?.requiresInterview).toBe(false);
    if (response && response.requiresInterview === false && 'interview' in response) {
      expect(response.interview.tools).toHaveLength(9);
      expect(response.interview.tools[8]).toBe('Tool-9');
    }
  });

  it('supports explicit sparkle intent without sparkle phrase in query', () => {
    const response = resolveSparklePillsResponse({
      query: 'Use case details only',
      sparkleIntent: true,
    });

    expect(response).not.toBeNull();
    expect(response?.requiresInterview).toBe(true);
  });
});
