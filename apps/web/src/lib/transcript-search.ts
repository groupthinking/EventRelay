/**
 * Pure transcript search helpers.
 *
 * Extracted from `InteractiveTranscript.tsx` and `TranscriptViewer.tsx` so the
 * search behavior optimized in PR #972 (issue #908) is directly testable. The
 * web suite runs in vitest's `node` environment by design — no jsdom, no
 * component rendering — so keeping this logic pure is what makes it coverable
 * at all. `src/lib/timestamp.ts` follows the same pattern for these components.
 *
 * Behavior here is intentionally identical to the shipped inline versions,
 * including the performance property that the query is normalized **once per
 * filtering pass** rather than once per segment.
 */

export interface TranscriptSegment {
  id: string;
  speaker: string;
  speakerColor: string;
  startTime: number; // seconds
  endTime: number;
  text: string;
}

export interface TranscriptFilter {
  /** Raw, un-normalized search query. Empty/nullish means "no search". */
  search: string;
  /** Optional exact speaker match. Nullish means "all speakers". */
  speaker?: string | null;
}

export interface TranscriptSearchConfig {
  /** Capturing, case-insensitive, non-global regex for `String.split`. */
  regex: RegExp;
  /** Pre-lowercased query, so comparisons allocate nothing per part. */
  lower: string;
}

/** Escapes every regex metacharacter so a query is matched literally. */
function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Builds the highlight config for a query, or `null` when there is nothing to
 * highlight.
 *
 * The regex is deliberately **non-global**: `.test()` on a global regex mutates
 * `lastIndex`, so repeated calls against the same instance desync and start
 * returning false.
 */
export function buildSearchConfig(query: string): TranscriptSearchConfig | null {
  if (!query) return null;
  return {
    regex: new RegExp(`(${escapeRegExp(query)})`, 'i'),
    lower: query.toLowerCase(),
  };
}

/**
 * Filters transcript segments by speaker and free-text search.
 *
 * Contract worth preserving (issue #908):
 * - An empty/nullish query matches **every** segment, never zero.
 * - A segment with missing text is a non-match, never a thrown TypeError.
 * - The query is lowercased exactly once per call, not once per segment.
 */
export function filterSegments(
  segments: readonly TranscriptSegment[],
  { search, speaker }: TranscriptFilter,
): TranscriptSegment[] {
  // Hoisted out of the loop: removes N toLowerCase() allocations per keystroke
  // update on long transcripts. This is the optimization PR #972 shipped.
  const lowerSearchQuery = search ? search.toLowerCase() : '';

  return segments.filter((seg) => {
    // Short-circuit the speaker check so non-matching rows skip string work.
    const matchesSpeaker = !speaker || seg.speaker === speaker;
    if (!matchesSpeaker) return false;

    return (
      !search || (seg.text ? seg.text.toLowerCase().includes(lowerSearchQuery) : false)
    );
  });
}
