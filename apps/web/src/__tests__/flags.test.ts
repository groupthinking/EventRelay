import { vercelAdapter } from '@flags-sdk/vercel';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { agentWorkflowUi, customBadge } from '@/flags';

beforeEach(() => {
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  vi.spyOn(console, 'info').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe.each([
  { key: customBadge.key, featureFlag: customBadge },
  { key: agentWorkflowUi.key, featureFlag: agentWorkflowUi },
])('$key', ({ featureFlag }) => {
  function evaluateFlag() {
    return featureFlag.run({
      identify: undefined,
      request: new Request('https://uvai.example/'),
    });
  }

  it.each([
    '@vercel/flags-core: No flag definitions available. Provide a datafile or bundled definitions.',
    'Flag provider unavailable',
  ])('defaults to disabled when evaluation fails: %s', async (message) => {
    vi.spyOn(vercelAdapter(), 'decide').mockRejectedValue(new Error(message));

    await expect(evaluateFlag()).resolves.toBe(false);
  });

  it('defaults to disabled when the provider returns no value', async () => {
    vi.spyOn(vercelAdapter(), 'decide').mockResolvedValue(undefined);

    await expect(evaluateFlag()).resolves.toBe(false);
  });

  it.each([true, false])('preserves the provider value %s', async (value) => {
    vi.spyOn(vercelAdapter(), 'decide').mockResolvedValue(value);

    await expect(evaluateFlag()).resolves.toBe(value);
  });

  it('does not swallow Next.js control-flow errors', async () => {
    const redirect = Object.assign(new Error('NEXT_REDIRECT'), {
      digest: 'NEXT_REDIRECT;replace;/login;307;',
    });
    vi.spyOn(vercelAdapter(), 'decide').mockRejectedValue(redirect);

    await expect(evaluateFlag()).rejects.toBe(redirect);
  });
});
