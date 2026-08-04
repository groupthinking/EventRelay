import 'server-only';

/**
 * Agentic Video Intelligence Engine — Gemini + Google Search grounding.
 *
 * Uses the googleSearch tool as the PRIMARY mechanism to retrieve real-time
 * transcripts, descriptions, chapters, and metadata from YouTube videos.
 * Based on the UVAI PK=998 implementation pattern.
 *
 * Uses gemini-2.5-flash with responseSchema when a real transcript is available.
 * When no transcript exists, falls back to googleSearch grounding without schema
 * (gemini-2.5-flash cannot combine responseSchema + googleSearch).
 */

import { Type } from '@google/genai';
import { hasAiGatewayKey } from './vercel-ai-gateway';
import { getGeminiClient } from './gemini-client';
import { GEMINI_SEARCH_MODEL, GEMINI_STRUCTURED_MODEL } from './gemini-models';
import {
  gatewayChat,
  stripJsonCodeFence,
  toGatewayModelId,
} from './vercel-ai-gateway';

export interface VideoAnalysisResult {
  title: string;
  summary: string;
  transcript: { start: number; duration: number; text: string }[];
  events: {
    timestamp: number;
    label: string;
    description: string;
    codeMapping: string;
    cloudService: string;
  }[];
  actions: {
    title: string;
    description: string;
    category: string;
    estimatedMinutes: number | null;
  }[];
  topics: string[];
  architectureCode: string;
  ingestScript: string;
  e22Snippets: {
    title: string;
    description: string;
    code: string;
    language: string;
  }[];
  /** Optional TranscriptActionAgent project scaffold (backend path). */
  project_scaffold?: unknown;
}

/**
 * Gemini response schema using the @google/genai Type system.
 * Matches the UVAI PK=998 structured output requirements exactly.
 */
const responseSchema = {
  type: Type.OBJECT,
  properties: {
    title: { type: Type.STRING },
    summary: { type: Type.STRING },
    transcript: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          start: { type: Type.NUMBER, description: 'Seconds from video start' },
          duration: { type: Type.NUMBER },
          text: { type: Type.STRING },
        },
        required: ['start', 'duration', 'text'] as const,
      },
    },
    events: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          timestamp: { type: Type.NUMBER },
          label: { type: Type.STRING },
          description: { type: Type.STRING },
          codeMapping: {
            type: Type.STRING,
            description: 'One-line code implementation of the action',
          },
          cloudService: { type: Type.STRING },
        },
        required: ['timestamp', 'label', 'description', 'codeMapping', 'cloudService'] as const,
      },
    },
    actions: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          title: { type: Type.STRING },
          description: { type: Type.STRING },
          category: {
            type: Type.STRING,
            enum: ['setup', 'build', 'deploy', 'learn', 'research', 'configure'],
          },
          estimatedMinutes: { type: Type.NUMBER, nullable: true },
        },
        required: ['title', 'description', 'category'] as const,
      },
    },
    topics: { type: Type.ARRAY, items: { type: Type.STRING } },
    architectureCode: { type: Type.STRING },
    ingestScript: { type: Type.STRING },
    e22Snippets: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          title: { type: Type.STRING },
          description: { type: Type.STRING },
          code: { type: Type.STRING },
          language: { type: Type.STRING },
        },
        required: ['title', 'description', 'code', 'language'] as const,
      },
    },
  },
  required: [
    'title',
    'summary',
    'transcript',
    'events',
    'actions',
    'topics',
    'architectureCode',
    'ingestScript',
    'e22Snippets',
  ] as const,
};

/**
 * Build the agentic system instruction for the Gemini model.
 * Implements the Think → Act → Observe → Map loop from PK=998.
 */
function buildSystemInstruction(videoUrl: string, actualTranscript: string): string {
  const videoId = videoUrl.match(/[?&]v=([^&]+)/)?.[1] || videoUrl;
  return `You are the Agentic Video Intelligence Engine.

MISSION:
1. WATCH the video (Video ID: ${videoId}). We have provided the ACTUAL spoken transcript below. Use it as your primary source of truth.
2. THINK: Analyze the sequence of technical events described in the transcript.
3. ACT: Reconstruct the timeline and generate Python 'ingest.py' logic that mimics the data patterns discussed in the video.
4. OBSERVE & MAP: Extract specific "Action Events" from the video and provide a direct "E22 Mapping" (code logic) for each.

DATA STRUCTURE REQUIREMENTS:
- title: Accurate video title. Feel free to use googleSearch to find exact title/metadata if needed.
- summary: A high-level technical executive summary.
- transcript: Return a structured array of {start, duration, text} representing the exact transcript provided below. Group the raw text into logical 30-120 second segments if timestamps aren't fully available.
- events: 3-5 key technical milestones with timestamp, label, description, and codeMapping.
- actions: 3-8 concrete tasks a developer/learner should DO after watching.
- topics: Key topics and technologies covered.
- architectureCode: A Markdown-formatted cloud architecture blueprint.
- ingestScript: A robust, modular Python script using Playwright for high-density ingestion.
- e22Snippets: 3-5 production-ready code snippets for E22 cloud solutions.

=== ACTUAL VIDEO TRANSCRIPT ===
${actualTranscript ? actualTranscript : "(No transcript available, you MUST use googleSearch to reconstruct content from descriptions, chapters, and comments)"}
=== END TRANSCRIPT ===`;
}

// Utility to delay operations
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Raised when the model's response cannot be parsed as the analysis JSON.
 * Distinct from API errors so the retry loop can treat malformed output as
 * retryable — production logs show Gemini intermittently emitting invalid or
 * truncated JSON that a fresh attempt resolves.
 */
export class AnalysisParseError extends Error {
  constructor(
    message: string,
    readonly rawSnippet: string,
  ) {
    super(message);
    this.name = 'AnalysisParseError';
  }
}

/**
 * Parses a model response into a VideoAnalysisResult. Strips markdown fences,
 * and on failure salvages the outermost {...} span (models occasionally wrap
 * the object in prose or emit trailing garbage). Throws AnalysisParseError
 * when no valid JSON object can be recovered.
 */
export function parseAnalysisResult(raw: string): VideoAnalysisResult {
  const cleaned = stripJsonCodeFence(raw);
  try {
    return JSON.parse(cleaned) as VideoAnalysisResult;
  } catch (parseError) {
    // Salvage the outermost {...} span — from the fence-stripped string first,
    // then from the raw response in case fence stripping mangled the payload.
    for (const source of [cleaned, raw]) {
      const start = source.indexOf('{');
      const end = source.lastIndexOf('}');
      if (start === -1 || end <= start) continue;
      try {
        const salvaged = JSON.parse(source.slice(start, end + 1)) as VideoAnalysisResult;
        console.warn('[Video Analyzer] Salvaged analysis JSON from a noisy model response.');
        return salvaged;
      } catch {
        // try the next source, then fall through to the typed error below
      }
    }
    const message = parseError instanceof Error ? parseError.message : String(parseError);
    throw new AnalysisParseError(
      `Model returned unparseable analysis JSON: ${message}`,
      cleaned.slice(0, 200),
    );
  }
}

/**
 * Executes a deep agentic analysis of a YouTube video using Gemini + Google Search.
 * Performs exponential backoff for 503 overload and 429 quota errors.
 */
async function analyzeVideoWithGateway(
  videoUrl: string,
  systemInstruction: string,
  model: string,
): Promise<VideoAnalysisResult> {
  const result = await gatewayChat({
    model: toGatewayModelId(model),
    messages: [
      { role: 'system', content: systemInstruction },
      {
        role: 'user',
        content:
          `Perform Agentic Grounding for Video: ${videoUrl}. ` +
          'Return ONLY a single JSON object matching the required schema. No markdown fences.',
      },
    ],
    // 16k cap: production logs showed 8k truncating long analyses mid-string,
    // which surfaced as "Unterminated string in JSON" parse failures.
    max_tokens: 16_384,
    temperature: 0.2,
    timeoutMs: 55_000,
  });
  return parseAnalysisResult(result.content);
}

export async function analyzeVideoWithGemini(
  videoUrl: string,
): Promise<VideoAnalysisResult> {
  // 1. Fetch the absolute real transcript FIRST (bypasses Gemini hallucination)
  let actualTranscript = '';
  try {
    const { fetchTranscript } = await import('./transcription-service');
    const result = await fetchTranscript({ url: videoUrl });
    if (result.success && result.transcript) {
      actualTranscript = result.transcript;
      console.log(`[Video Analyzer] Successfully fetched real transcript (${result.wordCount} words)`);
    } else {
      console.warn(`[Video Analyzer] Could not fetch real transcript: ${result.error}`);
    }
  } catch (err) {
    console.error(`[Video Analyzer] Error fetching real transcript:`, err);
  }

  const hasTranscript = actualTranscript.trim().length > 50;
  const systemInstruction = buildSystemInstruction(videoUrl, actualTranscript);
  const model = hasTranscript ? GEMINI_STRUCTURED_MODEL : GEMINI_SEARCH_MODEL;

  // 2. Wrap the API call in an exponential backoff retry loop (max 3 retries)
  const MAX_RETRIES = 3;
  let attempt = 0;

  while (attempt < MAX_RETRIES) {
    try {
      if (hasAiGatewayKey()) {
        return await analyzeVideoWithGateway(videoUrl, systemInstruction, model);
      }

      const ai = getGeminiClient();
      const response = await ai.models.generateContent({
        model,
        contents: `Perform Agentic Grounding for Video: ${videoUrl}`,
        config: hasTranscript
          ? {
              systemInstruction,
              responseMimeType: 'application/json',
              responseSchema,
            }
          : {
              systemInstruction,
              responseMimeType: 'application/json',
              tools: [{ googleSearch: {} }],
            },
      });

      const resultText = response.text || '{}';
      return parseAnalysisResult(resultText);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      const retryable =
        error instanceof AnalysisParseError ||
        errorMessage.includes('503') ||
        errorMessage.toLowerCase().includes('high traffic') ||
        errorMessage.includes('overloaded') ||
        errorMessage.includes('429') ||
        errorMessage.includes('RESOURCE_EXHAUSTED');

      if (retryable) {
        attempt++;
        if (attempt >= MAX_RETRIES) {
          throw new Error(
            `Gemini analysis failed after ${MAX_RETRIES} attempts. Original error: ${errorMessage}`,
          );
        }

        const backoffTime = Math.pow(2, attempt) * 1000;
        console.warn(
          `[Video Analyzer] Gemini retryable error (${model}). Attempt ${attempt}/${MAX_RETRIES} in ${backoffTime}ms...`,
        );
        await delay(backoffTime);
      } else {
        throw error;
      }
    }
  }

  throw new Error('Failed to generate content due to an unknown error.');
}
