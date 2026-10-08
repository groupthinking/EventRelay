vi.mock('server-only', () => ({}));

import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { EventTypes, publishEvent } from '@/lib/cloudevents';

describe('cloudevents durable outbox', () => {
  let dir: string;
  let sink: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'cloudevents-test-'));
    sink = join(dir, 'outbox.jsonl');
    vi.stubEnv('CLOUDEVENTS_FILE_SINK', sink);
    vi.stubEnv('CLOUDEVENTS_WEBHOOK_URL', '');
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    rmSync(dir, { recursive: true, force: true });
  });

  function readOutbox(): Array<Record<string, unknown>> {
    const raw = readFileSync(sink, 'utf8').trim();
    if (!raw) return [];
    return raw.split('\n').map((line) => JSON.parse(line));
  }

  it(
    'appends every event to the JSONL outbox even with no webhook configured',
    async () => {
      await publishEvent(EventTypes.VIDEO_RECEIVED, { url: 'https://youtu.be/x' }, 'subj-1');

      const events = readOutbox();
      expect(events).toHaveLength(1);
      expect(events[0]).toMatchObject({
        specversion: '1.0',
        type: 'com.eventrelay.video.received',
        subject: 'subj-1',
        datacontenttype: 'application/json',
        data: { url: 'https://youtu.be/x' },
      });
      expect(typeof events[0].id).toBe('string');
      expect(fetch).not.toHaveBeenCalled();
    },
    10_000,
  );

  it(
    'posts to the webhook on success and keeps the outbox record',
    async () => {
      vi.stubEnv('CLOUDEVENTS_WEBHOOK_URL', 'https://hooks.example.test/e');
      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, status: 200 });

      await publishEvent(EventTypes.PIPELINE_COMPLETED, { ok: true });

      expect(fetch).toHaveBeenCalledTimes(1);
      const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(init.method).toBe('POST');
      expect(init.headers['Content-Type']).toBe('application/cloudevents+json');
      const body = JSON.parse(init.body);
      expect(body.type).toBe('com.eventrelay.pipeline.completed');
      expect(readOutbox()).toHaveLength(1);
    },
    10_000,
  );

  it(
    'retries webhook delivery on transient failure and then succeeds',
    async () => {
      vi.stubEnv('CLOUDEVENTS_WEBHOOK_URL', 'https://hooks.example.test/e');
      const fetchMock = fetch as ReturnType<typeof vi.fn>;
      fetchMock
        .mockRejectedValueOnce(new Error('boom'))
        .mockResolvedValueOnce({ ok: false, status: 500 })
        .mockResolvedValueOnce({ ok: true, status: 200 });

      await publishEvent(EventTypes.PIPELINE_FAILED, { error: 'x' });

      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(readOutbox()).toHaveLength(1);
    },
    20_000,
  );

  it(
    'never rejects when the webhook keeps failing; the event stays in the outbox',
    async () => {
      vi.stubEnv('CLOUDEVENTS_WEBHOOK_URL', 'https://hooks.example.test/e');
      (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('down'));

      await expect(
        publishEvent(EventTypes.TRANSCRIPT_STARTED, { url: 'u' }),
      ).resolves.toBeUndefined();

      expect(fetch).toHaveBeenCalledTimes(3);
      const events = readOutbox();
      expect(events).toHaveLength(1);
      expect(events[0].type).toBe('com.eventrelay.transcript.started');
    },
    20_000,
  );
});
