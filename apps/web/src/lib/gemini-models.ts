import 'server-only';

/**
 * Central Gemini model selection. Gemini 3.8 uses provider-managed sampling;
 * per-workload environment overrides retain access to supported older models.
 */

/** Fast model for transcription search, agents, and structured output without search. */
export const GEMINI_FAST_MODEL =
  process.env.GEMINI_FAST_MODEL?.trim() || 'gemini-3.8-flash';

/** Model when googleSearch grounding is required without structured schema. */
export const GEMINI_SEARCH_MODEL =
  process.env.GEMINI_SEARCH_MODEL?.trim() || GEMINI_FAST_MODEL;

/** Model when responseSchema structured JSON is required (no googleSearch). */
export const GEMINI_STRUCTURED_MODEL =
  process.env.GEMINI_STRUCTURED_MODEL?.trim() || GEMINI_FAST_MODEL;