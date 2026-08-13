import { describe, expect, it } from 'vitest';
import { withWorldVercelFetch } from '@/lib/world-vercel-fetch';

describe('withWorldVercelFetch (issue #1538)', () => {
  it('restores global fetch after success', async () => {
    const original = globalThis.fetch;
    await withWorldVercelFetch(async () => 'ok');
    expect(globalThis.fetch).toBe(original);
  });

  it('restores global fetch after a throw', async () => {
    const original = globalThis.fetch;
    await expect(
      withWorldVercelFetch(async () => {
        throw new Error('boom');
      }),
    ).rejects.toThrow('boom');
    expect(globalThis.fetch).toBe(original);
  });

  it('runs the callback while fetch is rebound', async () => {
    const original = globalThis.fetch;
    const seen = await withWorldVercelFetch(async () => globalThis.fetch);
    expect(seen).not.toBe(original);
    expect(globalThis.fetch).toBe(original);
  });
});
