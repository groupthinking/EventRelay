import 'server-only';

/**
 * Central Gemini model selection.
 *
 * gemini-3.1-pro-preview has zero free-tier quota on AI Studio (limit: 0).
 * gemini-2.5-flash has free-tier headroom but cannot combine responseSchema
 * with googleSearch — callers must pick one or the other per request.
 */

/** Fast model for transcription search, agents, and structured output without search. */
export const GEMINI_FAST_MODEL =
  process.env.GEMINI_FAST_MODEL?.trim() || 'gemini-2.5-flash';

/** Model when googleSearch grounding is required without structured schema. */
export const GEMINI_SEARCH_MODEL =
  process.env.GEMINI_SEARCH_MODEL?.trim() || GEMINI_FAST_MODEL;

/** Model when responseSchema structured JSON is required (no googleSearch). */
export const GEMINI_STRUCTURED_MODEL =
  process.env.GEMINI_STRUCTURED_MODEL?.trim() || GEMINI_FAST_MODEL;