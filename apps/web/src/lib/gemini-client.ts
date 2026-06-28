import 'server-only';

/**
 * Shared Gemini/Google AI client factory.
 *
 * Supports two authentication modes:
 *   1. Gemini API: uses GEMINI_API_KEY or GOOGLE_API_KEY
 *   2. Vertex AI Express Mode: uses Vertex_AI_API_KEY
 *      (apiKey + vertexai: true — no project/location needed)
 *
 * See: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/vertex-ai-express-mode-api-reference
 */

import { GoogleGenAI } from '@google/genai';

/**
 * Resolve the best available Google/Gemini API key.
 */
export function resolveGeminiApiKey(): string {
  return (
    process.env.Vertex_AI_API_KEY ||
    process.env.GEMINI_API_KEY ||
    process.env.GOOGLE_API_KEY ||
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
 * Determine if we should use Vertex AI Express Mode.
 */
function shouldUseVertexAI(): boolean {
  if (process.env.GOOGLE_GENAI_USE_VERTEXAI === 'true') return true;
  if (process.env.Vertex_AI_API_KEY) return true;
  return false;
}

let _gemini: GoogleGenAI | null = null;
let _lastKey = '';
let _lastMode = '';

/**
 * Get a shared GoogleGenAI instance.
 * Automatically selects Gemini API or Vertex AI Express Mode.
 */
export function getGeminiClient(): GoogleGenAI {
  const key = resolveGeminiApiKey();
  const mode = shouldUseVertexAI() ? 'vertex' : 'gemini';

  if (!_gemini || _lastKey !== key || _lastMode !== mode) {
    if (mode === 'vertex') {
      // Vertex AI Express Mode: apiKey + vertexai only
      _gemini = new GoogleGenAI({
        vertexai: true,
        apiKey: key,
      });
    } else {
      _gemini = new GoogleGenAI({ apiKey: key });
    }
    _lastKey = key;
    _lastMode = mode;
  }
  return _gemini;
}
