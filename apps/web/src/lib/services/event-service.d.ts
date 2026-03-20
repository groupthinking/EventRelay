/**
 * Event service — extract events from transcripts.
 */
import type { EventExtractRequest, EventExtractResponse } from '../types';
export declare const eventService: {
    /** Extract events from a transcript or completed job. */
    extractEvents(req: EventExtractRequest): Promise<import("../types").ApiResponse<EventExtractResponse>>;
};
