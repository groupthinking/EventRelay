/**
 * Same-run Act payload: reuse Analyze transcript/events instead of
 * re-fetching the video from its URL.
 */

export const MIN_ACT_TRANSCRIPT_CHARS = 40;
export const MAX_ACT_TRANSCRIPT_CHARS = 24_000;
export const MAX_ACT_EVENTS = 40;

export type ActEvent = {
  type?: string;
  title: string;
  description?: string;
};

export type SameRunActInput = {
  url: string;
  videoTitle?: string;
  transcript?: string;
  events?: ActEvent[];
};

export function usableProvidedTranscript(text?: string | null): string | undefined {
  const trimmed = (text || '').trim();
  if (trimmed.length < MIN_ACT_TRANSCRIPT_CHARS) return undefined;
  return trimmed.slice(0, MAX_ACT_TRANSCRIPT_CHARS);
}

export function sanitizeActEvents(events: unknown): ActEvent[] | undefined {
  if (!Array.isArray(events)) return undefined;
  const out: ActEvent[] = [];
  for (const raw of events.slice(0, MAX_ACT_EVENTS)) {
    if (!raw || typeof raw !== 'object') continue;
    const row = raw as Record<string, unknown>;
    const title = typeof row.title === 'string' ? row.title.trim() : '';
    if (!title) continue;
    out.push({
      type: typeof row.type === 'string' ? row.type.slice(0, 40) : undefined,
      title: title.slice(0, 200),
      description:
        typeof row.description === 'string' ? row.description.slice(0, 500) : undefined,
    });
  }
  return out.length > 0 ? out : undefined;
}

export function buildSameRunActInput(opts: {
  url: string;
  videoTitle?: string;
  transcript?: string | null;
  events?: unknown;
}): SameRunActInput {
  return {
    url: opts.url.trim(),
    videoTitle: opts.videoTitle?.trim().slice(0, 200) || undefined,
    transcript: usableProvidedTranscript(opts.transcript),
    events: sanitizeActEvents(opts.events),
  };
}

export function formatEventsContext(events?: ActEvent[]): string {
  if (!events?.length) return '';
  const lines = events.map((event) => {
    const kind = event.type || 'event';
    return `- [${kind}] ${event.title}${event.description ? `: ${event.description}` : ''}`;
  });
  return `\n\nEVENTS FROM ANALYZE:\n${lines.join('\n')}`;
}

/** Transcript plus Analyze events, sized for the action agent prompt. */
export function buildActionAgentSource(transcript: string, events?: ActEvent[]): string {
  const ctx = formatEventsContext(events);
  if (!ctx) return transcript;
  const room = Math.max(MIN_ACT_TRANSCRIPT_CHARS, 12_000 - ctx.length);
  return transcript.slice(0, room) + ctx;
}
