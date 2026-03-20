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
export declare const EventTypes: {
    readonly VIDEO_RECEIVED: "com.eventrelay.video.received";
    readonly TRANSCRIPT_STARTED: "com.eventrelay.transcript.started";
    readonly TRANSCRIPT_COMPLETED: "com.eventrelay.transcript.completed";
    readonly EXTRACTION_STARTED: "com.eventrelay.extraction.started";
    readonly EXTRACTION_COMPLETED: "com.eventrelay.extraction.completed";
    readonly PIPELINE_COMPLETED: "com.eventrelay.pipeline.completed";
    readonly PIPELINE_FAILED: "com.eventrelay.pipeline.failed";
};
/**
 * Publish a CloudEvent.
 *
 * - If WEBHOOK_URL is set → POST to that URL
 * - Otherwise → append to /tmp/cloudevents.jsonl (dev/Vercel)
 */
export declare function publishEvent(type: string, data: Record<string, unknown>, subject?: string): Promise<void>;
