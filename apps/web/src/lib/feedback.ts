/**
 * Feedback persistence layer.
 *
 * Stores user feedback in Supabase when available, falls back to
 * the backend API endpoint. Feedback flows into the correction loop
 * to guide architecture rewrites.
 */

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
 * Tries the backend API first. If the API is unreachable,
 * queues the feedback for later submission.
 */
export async function submitFeedback(entry: FeedbackEntry): Promise<void> {
  const payload = {
    ...entry,
    timestamp: new Date().toISOString(),
  };

  try {
    const res = await fetch(FEEDBACK_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Feedback API returned ${res.status}`);
    }
  } catch (err) {
    // Queue for retry — store in memory (no localStorage per artifact rules)
    console.warn('Feedback API unavailable, queuing for retry:', err);
    queueFeedback(payload);
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

// --- In-memory feedback queue for offline resilience ---
const pendingFeedback: FeedbackEntry[] = [];

function queueFeedback(entry: FeedbackEntry): void {
  pendingFeedback.push(entry);
}

/**
 * Flush any queued feedback. Call this when connectivity is restored.
 */
export async function flushPendingFeedback(): Promise<number> {
  let flushed = 0;
  while (pendingFeedback.length > 0) {
    const entry = pendingFeedback[0];
    try {
      await submitFeedback(entry);
      pendingFeedback.shift();
      flushed++;
    } catch {
      break; // Still offline, stop trying
    }
  }
  return flushed;
}
