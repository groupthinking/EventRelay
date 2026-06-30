/**
 * Agentic Video Intelligence Engine — Gemini + Google Search grounding.
 *
 * Uses the googleSearch tool as the PRIMARY mechanism to retrieve real-time
 * transcripts, descriptions, chapters, and metadata from YouTube videos.
 * Based on the UVAI PK=998 implementation pattern.
 *
 * Uses gemini-3-pro-preview which supports responseSchema + googleSearch
 * together (older models like gemini-2.5-flash do not).
 */

import { Type } from '@google/genai';
import { getGeminiClient } from './gemini-client';

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
 * Executes a deep agentic analysis of a YouTube video using Gemini + Google Search.
 * Uses gemini-3-pro-preview with responseSchema + googleSearch (PK=998 pattern).
 * Performs exponential backoff specifically handling 503 "high traffic" errors.
 */
export async function analyzeVideoWithGemini(
  videoUrl: string,
): Promise<VideoAnalysisResult> {
  const ai = getGeminiClient();

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

  const systemInstruction = buildSystemInstruction(videoUrl, actualTranscript);

  // 2. Wrap the API call in an exponential backoff retry loop (max 3 retries)
  const MAX_RETRIES = 3;
  let attempt = 0;
  
  while (attempt < MAX_RETRIES) {
    try {
      const response = await ai.models.generateContent({
        model: 'gemini-3-pro-preview',
        contents: `Perform Agentic Grounding for Video: ${videoUrl}`,
        config: {
          systemInstruction,
          responseMimeType: 'application/json',
          responseSchema,
          tools: [{ googleSearch: {} }],
        },
      });

      const resultText = response.text || '{}';
      return JSON.parse(resultText) as VideoAnalysisResult;
      
    } catch (error: any) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      // Check if this is a 503 Service Unavailable / High Traffic error
      if (errorMessage.includes('503') || errorMessage.toLowerCase().includes('high traffic') || errorMessage.includes('overloaded')) {
        attempt++;
        if (attempt >= MAX_RETRIES) {
          throw new Error(`Gemini API overloaded after ${MAX_RETRIES} attempts. Please try again later. Original error: ${errorMessage}`);
        }
        
        // Exponential backoff: 2s, 4s, 8s
        const backoffTime = Math.pow(2, attempt) * 1000;
        console.warn(`[Video Analyzer] Gemini 503 error. Retrying attempt ${attempt}/${MAX_RETRIES} in ${backoffTime}ms...`);
        await delay(backoffTime);
      } else {
        // Unhandled error (e.g. 400 Bad Request), throw immediately
        throw error;
      }
    }
  }

  throw new Error("Failed to generate content due to an unknown error.");
}
