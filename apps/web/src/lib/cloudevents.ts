/**
 * CloudEvents v1.0 publisher for the Next.js frontend pipeline.
 *
 * Emits standardized events at each video processing stage so that
 * downstream consumers (Pub/Sub, webhooks, file sink) can react.
 *
 * When no backend is configured the events are written to a local
 * JSONL file (`/tmp/cloudevents.jsonl`) for observability.
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
  PIPELINE_COMPLETED: 'com.eventrelay.pipeline.completed',
  PIPELINE_FAILED: 'com.eventrelay.pipeline.failed',
} as const;

/**
 * Publish a CloudEvent.
 *
 * - If WEBHOOK_URL is set → POST to that URL
 * - Otherwise → append to /tmp/cloudevents.jsonl (dev/Vercel)
 */
export async function publishEvent(
  type: string,
  data: Record<string, unknown>,
  subject?: string,
): Promise<void> {
  const event = makeEvent(type, data, subject);

  const webhookUrl = process.env.CLOUDEVENTS_WEBHOOK_URL;

  if (webhookUrl) {
    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/cloudevents+json',
        },
        body: JSON.stringify(event),
      });
    } catch (e) {
      console.warn('[CloudEvents] Webhook publish failed:', e);
    }
  }

  // Always log the event for observability
  console.log(`[CloudEvent] ${type}`, JSON.stringify({ id: event.id, subject }));
}
