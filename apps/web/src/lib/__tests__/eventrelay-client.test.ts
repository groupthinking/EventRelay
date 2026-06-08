import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { EventRelayClient, EventRelayError } from '../eventrelay-client';

const json = (data: unknown, status = 200): Response =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

describe('EventRelayClient', () => {
  afterEach(() => vi.restoreAllMocks());

  it('submits a job to the clean /api/v1/jobs contract', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(json({ job_id: 'j1', status: 'queued' }));
    const client = new EventRelayClient('http://backend');

    const res = await client.submitJob({ video_url: 'https://youtu.be/dQw4w9WgXcQ' });

    expect(res).toEqual({ job_id: 'j1', status: 'queued' });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://backend/api/v1/jobs');
    expect((init as RequestInit).method).toBe('POST');
  });

  it('reads typed events from the contract', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      json({ job_id: 'j1', events: [{ type: 'youtube.video.captured', ts: 't', payload: {} }] }),
    );
    const events = await new EventRelayClient('http://b').getEvents('j1');
    expect(events[0].type).toBe('youtube.video.captured');
  });

  // SC7 acceptance: backend down → typed error, NO model fallback.
  it('throws EventRelayError when the backend is unreachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('ECONNREFUSED'));
    await expect(new EventRelayClient('http://b').getJob('j1')).rejects.toBeInstanceOf(
      EventRelayError,
    );
  });

  it('surfaces HTTP error status from the backend', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'job not found' }, 404));
    await expect(new EventRelayClient('http://b').getJob('nope')).rejects.toMatchObject({
      status: 404,
    });
  });

  // SC7 structural guard: the data path must not import a model SDK.
  it('imports no model SDK (pure consumer of the contract)', () => {
    const src = readFileSync(
      fileURLToPath(new URL('../eventrelay-client.ts', import.meta.url)),
      'utf8',
    );
    // Match an actual import/require of a model SDK — not a prose mention of
    // one in the module's own documentation.
    expect(src).not.toMatch(
      /(?:import|require)\b[^\n]*['"](?:@google\/genai|@google\/generative-ai|openai)['"]/,
    );
  });
});
