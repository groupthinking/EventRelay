/**
 * Event service — extract events from transcripts.
 */

import { apiClient } from '../api-client';
import type { EventExtractRequest, EventExtractResponse } from '../types';

export const eventService = {
  /** Extract events from a transcript or completed job. */
  async extractEvents(req: EventExtractRequest) {
    return apiClient.post<EventExtractResponse>('/api/v1/events/extract', req);
  },
};
