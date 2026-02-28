/**
 * Shared Gemini/Google AI client factory.
 *
 * Resolves the API key from multiple env var names and returns a
 * configured GoogleGenAI instance. Supports:
 *   - GEMINI_API_KEY (standard Gemini API)
 *   - GOOGLE_API_KEY (alternate name)
 *   - Vertex_AI_API_KEY (Vercel env var)
 */

import { GoogleGenAI } from '@google/genai';

/**
 * Resolve the best available Google/Gemini API key.
 * Returns the first non-empty key found, or empty string.
 */
export function resolveGeminiApiKey(): string {
  return (
    process.env.GEMINI_API_KEY ||
    process.env.GOOGLE_API_KEY ||
    process.env.Vertex_AI_API_KEY ||
    ''
  );
}

/**
 * Check if any Gemini/Google AI API key is available.
 */
export function hasGeminiKey(): boolean {
  return resolveGeminiApiKey().length > 0;
}

let _gemini: GoogleGenAI | null = null;
let _lastKey = '';

/**
 * Get a shared GoogleGenAI instance, creating one if needed.
 * Re-creates the instance if the resolved key changes.
 */
export function getGeminiClient(): GoogleGenAI {
  const key = resolveGeminiApiKey();
  if (!_gemini || _lastKey !== key) {
    _gemini = new GoogleGenAI({ apiKey: key });
    _lastKey = key;
  }
  return _gemini;
}
