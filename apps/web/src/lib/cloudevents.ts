import 'server-only';

import { appendFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

import { retryWithBackoff } from '@/lib/error-handling';

/**
 * CloudEvents v1.0 publisher for the Next.js frontend pipeline.
 *
 * Emits standardized events at each video processing stage so that
 * downstream consumers (Pub/Sub, webhooks, file sink) can react.
 *
 * Delivery model (durable outbox, best-effort forwarding):
 *
 * 1. Every event is appended to a local JSONL outbox
 *    (`/tmp/cloudevents.jsonl` by default, `CLOUDEVENTS_FILE_SINK` to
 *    override). The outbox is per-instance and ephemeral on serverless —
 *    it is a local durability/observability record, not a distributed log.
 * 2. If `CLOUDEVENTS_WEBHOOK_URL` is set, the event is POSTed there with
 *    bounded retries (3 attempts, exponential backoff). A failed delivery
 *    is logged, never thrown — the event remains in the outbox.
 *
 * `publishEvent` never rejects: observability must not break the pipeline.
 * Consumers must dedupe on `id` (at-least-once delivery).
 */

export interface CloudEvent {
  id: string;
  source: string;
  specversion: '1.0';
  type: string;
  time: string;
  subject?: string;
  datacontenttype: string;
  data: Record<string, unknown>;
}

function makeEvent(
  type: string,
  data: Record<string, unknown>,
  subject?: string,
): CloudEvent {
  return {
    id: crypto.randomUUID(),
    source: '/eventrelay/api/video',
    specversion: '1.0',
    type,
    time: new Date().toISOString(),
    subject,
    datacontenttype: 'application/json',
    data,
  };
}

// Event types following CloudEvents naming convention
export const EventTypes = {
  VIDEO_RECEIVED: 'com.eventrelay.video.received',
  TRANSCRIPT_STARTED: 'com.eventrelay.transcript.started',
  TRANSCRIPT_COMPLETED: 'com.eventrelay.transcript.completed',
  EXTRACTION_STARTED: 'com.eventrelay.extraction.started',
  EXTRACTION_COMPLETED: 'com.eventrelay.extraction.completed',
  PIPELINE_QUEUED: 'com.eventrelay.pipeline.queued',
  PIPELINE_COMPLETED: 'com.eventrelay.pipeline.completed',
  PIPELINE_FAILED: 'com.eventrelay.pipeline.failed',
} as const;

const WEBHOOK_MAX_ATTEMPTS = 3;
const WEBHOOK_BASE_DELAY_MS = 500;
const WEBHOOK_TIMEOUT_MS = 5_000;

function outboxPath(): string {
  return process.env.CLOUDEVENTS_FILE_SINK || '/tmp/cloudevents.jsonl';
}

/** Append the event to the local JSONL outbox. Best-effort; never throws. */
async function writeOutbox(event: CloudEvent): Promise<void> {
  const path = outboxPath();
  try {
    await mkdir(dirname(path), { recursive: true });
    await appendFile(path, `${JSON.stringify(event)}\n`, 'utf8');
  } catch (error) {
    console.warn('[CloudEvents] Outbox write failed:', error);
  }
}

/** POST one delivery attempt. Throws on network error or non-2xx. */
async function postWebhookOnce(webhookUrl: string, event: CloudEvent): Promise<void> {
  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/cloudevents+json',
    },
    body: JSON.stringify(event),
    signal: AbortSignal.timeout(WEBHOOK_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new Error(`webhook responded ${response.status}`);
  }
}

/**
 * Publish a CloudEvent.
 *
 * - Always appended to the local JSONL outbox.
 * - If CLOUDEVENTS_WEBHOOK_URL is set → POST with bounded retries.
 * - Never rejects.
 */
export async function publishEvent(
  type: string,
  data: Record<string, unknown>,
  subject?: string,
): Promise<void> {
  const event = makeEvent(type, data, subject);

  // Durable local record first: even if forwarding fails, the event exists.
  await writeOutbox(event);

  const webhookUrl = process.env.CLOUDEVENTS_WEBHOOK_URL;
  if (webhookUrl) {
    try {
      await retryWithBackoff(
        () => postWebhookOnce(webhookUrl, event),
        WEBHOOK_MAX_ATTEMPTS,
        WEBHOOK_BASE_DELAY_MS,
      );
    } catch (error) {
      console.warn(
        '[CloudEvents] Webhook delivery failed after retries; event retained in outbox:',
        error,
      );
    }
  }

  // Always log the event for observability
  console.log(`[CloudEvent] ${type}`, JSON.stringify({ id: event.id, subject }));
}
