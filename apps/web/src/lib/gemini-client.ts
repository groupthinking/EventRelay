/**
 * Shared Gemini/Google AI client factory.
 *
 * Supports two authentication modes:
 *   1. Gemini API: uses GEMINI_API_KEY or GOOGLE_API_KEY
 *   2. Vertex AI: uses Vertex_AI_API_KEY with project/location
 *      (Express Mode — API key instead of service account)
 *
 * Env vars for Vertex AI:
 *   - Vertex_AI_API_KEY: the Vertex AI API key
 *   - GOOGLE_CLOUD_PROJECT: GCP project ID (default: uvai-730bb)
 *   - GOOGLE_CLOUD_LOCATION: GCP location (default: us-central1)
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

/**
 * Determine if we should use Vertex AI mode.
 * True when the only available key is Vertex_AI_API_KEY,
 * or when GOOGLE_CLOUD_PROJECT is explicitly set.
 */
function shouldUseVertexAI(): boolean {
  // If standard Gemini keys are set, use Gemini API
  if (process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY) return false;
  // If Vertex AI key is available, use Vertex AI Express Mode
  if (process.env.Vertex_AI_API_KEY) return true;
  return false;
}

let _gemini: GoogleGenAI | null = null;
let _lastKey = '';
let _lastMode = '';

/**
 * Get a shared GoogleGenAI instance, creating one if needed.
 * Automatically selects Gemini API or Vertex AI Express Mode.
 */
export function getGeminiClient(): GoogleGenAI {
  const key = resolveGeminiApiKey();
  const mode = shouldUseVertexAI() ? 'vertex' : 'gemini';

  if (!_gemini || _lastKey !== key || _lastMode !== mode) {
    if (mode === 'vertex') {
      _gemini = new GoogleGenAI({
        vertexai: true,
        apiKey: key,
        project: process.env.GOOGLE_CLOUD_PROJECT || 'uvai-730bb',
        location: process.env.GOOGLE_CLOUD_LOCATION || 'us-central1',
      });
    } else {
      _gemini = new GoogleGenAI({ apiKey: key });
    }
    _lastKey = key;
    _lastMode = mode;
  }
  return _gemini;
}
