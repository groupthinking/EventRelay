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
export declare function resolveGeminiApiKey(): string;
/**
 * Check if any Gemini/Google AI API key is available.
 */
export declare function hasGeminiKey(): boolean;
/**
 * Get a shared GoogleGenAI instance.
 * Automatically selects Gemini API or Vertex AI Express Mode.
 */
export declare function getGeminiClient(): GoogleGenAI;
