import 'server-only';
import { formatApiError } from '@/lib/error-handling';

/**
 * Shared Gemini/Google AI client factory.
 *
 * Supports two authentication modes:
 *   1. Gemini API (AI Studio): GEMINI_API_KEY or GOOGLE_API_KEY
 *   2. Vertex AI Express Mode: Vertex_AI_API_KEY
 *      (apiKey + vertexai: true — no project/location needed)
 *
 * When both AI Studio and Vertex keys exist, AI Studio wins unless
 * GOOGLE_GENAI_USE_VERTEXAI=true is set explicitly.
 *
 * See: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/vertex-ai-express-mode-api-reference
 */

import { GoogleGenAI } from '@google/genai';
import { hasAiGatewayKey } from './vercel-ai-gateway';

export type GeminiAuthMode = 'gateway' | 'studio' | 'vertex' | 'none';

export interface GeminiConfig {
  configured: boolean;
  mode: GeminiAuthMode;
}

export interface ClassifiedGeminiError {
  code: string;
  message: string;
  userMessage: string;
}

/**
 * Resolve which auth mode is active. AI Studio is preferred when both key types exist.
 */
export function getGeminiAuthMode(): GeminiAuthMode {
  if (hasAiGatewayKey()) return 'gateway';

  if (process.env.GOOGLE_GENAI_USE_VERTEXAI === 'true') {
    const key =
      process.env.Vertex_AI_API_KEY ||
      process.env.GEMINI_API_KEY ||
      process.env.GOOGLE_API_KEY ||
      '';
    return key ? 'vertex' : 'none';
  }

  const studioKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '';
  if (studioKey) return 'studio';
  if (process.env.Vertex_AI_API_KEY) return 'vertex';
  return 'none';
}

export function getGeminiConfig(): GeminiConfig {
  const mode = getGeminiAuthMode();
  return { configured: mode !== 'none', mode };
}

/**
 * Resolve the best available Google/Gemini API key for the active auth mode.
 */
export function resolveGeminiApiKey(): string {
  const mode = getGeminiAuthMode();
  if (mode === 'studio') {
    return process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '';
  }
  if (mode === 'vertex') {
    return (
      process.env.Vertex_AI_API_KEY ||
      process.env.GEMINI_API_KEY ||
      process.env.GOOGLE_API_KEY ||
      ''
    );
  }
  return '';
}

/**
 * Check if any Gemini/Google AI API key is available.
 */
export function hasGeminiKey(): boolean {
  return hasAiGatewayKey() || resolveGeminiApiKey().length > 0;
}

/** Active LLM routing label for observability (gateway takes precedence). */
export function getGeminiRoutingLabel(): string {
  const mode = getGeminiAuthMode();
  if (mode === 'gateway') {
    return `gateway:${process.env.VERCEL_AI_GATEWAY_MODEL?.trim() || 'google/gemini-2.5-flash'}`;
  }
  if (mode === 'vertex') return 'vertex';
  if (mode === 'studio') return 'studio';
  return 'none';
}

/**
 * Map provider errors to stable codes for API responses and logs.
 */
export function classifyGeminiError(error: unknown): ClassifiedGeminiError {
  const message = formatApiError(error).message;

  if (message.includes('BILLING_DISABLED')) {
    return {
      code: 'BILLING_DISABLED',
      message,
      userMessage:
        'Google Cloud billing is disabled for the configured Vertex project. Enable GCP billing or set GEMINI_API_KEY (AI Studio) in Vercel.',
    };
  }
  if (message.includes('429') || message.includes('RESOURCE_EXHAUSTED')) {
    return {
      code: 'RATE_LIMITED',
      message,
      userMessage: 'Gemini rate limit exceeded. Retry shortly or reduce concurrent pipeline runs.',
    };
  }
  if (message.includes('403') || message.includes('PERMISSION_DENIED')) {
    return {
      code: 'PERMISSION_DENIED',
      message,
      userMessage: 'Gemini API access denied. Verify the API key, billing, and model access for this project.',
    };
  }
  if (message.toLowerCase().includes('timed out') || message.includes('DEADLINE_EXCEEDED')) {
    return {
      code: 'TIMEOUT',
      message,
      userMessage: 'Gemini analysis timed out before completing.',
    };
  }

  return {
    code: 'GEMINI_ERROR',
    message,
    userMessage: 'Gemini video analysis failed. Check provider configuration and billing.',
  };
}

function shouldUseVertexAI(): boolean {
  return getGeminiAuthMode() === 'vertex';
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
  if (!key) {
    throw new Error(
      'No direct Gemini API key configured. Set GEMINI_API_KEY or route through AI_GATEWAY_API_KEY.',
    );
  }
  const mode = shouldUseVertexAI() ? 'vertex' : 'gemini';

  if (!_gemini || _lastKey !== key || _lastMode !== mode) {
    if (mode === 'vertex') {
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
