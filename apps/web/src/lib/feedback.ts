/** Feedback client for the durable feedback API. */

export interface FeedbackEntry {
  videoId: string;
  tab: string;
  rating: number; // 1-5
  comment?: string;
  timestamp?: string;
}

const FEEDBACK_API = '/api/v1/feedback';

/**
 * Submit feedback for a specific video tab.
 *
 * A resolved promise means the server accepted the entry. Network and HTTP
 * failures reject so callers never claim that an in-memory value was saved.
 */
export async function submitFeedback(entry: FeedbackEntry): Promise<void> {
  const payload = {
    ...entry,
    timestamp: new Date().toISOString(),
  };

  const res = await fetch(FEEDBACK_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Feedback API returned ${res.status}`);
  }
}

/**
 * Retrieve feedback for a video (for the correction loop to consume).
 */
export async function getFeedback(videoId: string, tab?: string): Promise<FeedbackEntry[]> {
  try {
    const params = new URLSearchParams({ videoId });
    if (tab) params.append('tab', tab);

    const res = await fetch(`${FEEDBACK_API}?${params}`);
    if (!res.ok) return [];

    const data = await res.json();
    return data.feedback || [];
  } catch {
    return [];
  }
}

/**
 * Retained for compatibility with older callers. Feedback is no longer kept
 * in volatile memory because a reload would silently discard it.
 */
export async function flushPendingFeedback(): Promise<number> {
  return 0;
}
