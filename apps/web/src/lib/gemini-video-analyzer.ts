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
function buildSystemInstruction(videoUrl: string): string {
  const videoId = videoUrl.match(/[?&]v=([^&]+)/)?.[1] || videoUrl;
  return `You are the Agentic Video Intelligence Engine.

MISSION:
1. WATCH the video (Video ID: ${videoId}) by searching for its transcript, technical documentation,
   and chapter markers using your googleSearch tool.
2. THINK: Analyze the sequence of technical events described in the transcript.
3. ACT: Reconstruct the timeline and generate Python 'ingest.py' logic that mimics
   the data patterns discussed in the video.
4. OBSERVE & MAP: Extract specific "Action Events" from the video and provide a direct
   "E22 Mapping" (code logic) for each.

DATA STRUCTURE REQUIREMENTS:
- title: Accurate video title from search results.
- summary: A high-level technical executive summary.
- transcript: An array of {start, duration, text} reconstructed from grounding.
  Use chapter timestamps and description content if a full transcript is unavailable.
  Each entry should cover a meaningful segment (30-120 seconds).
- events: 3-5 key technical milestones with timestamp, label, description, and codeMapping.
- actions: 3-8 concrete tasks a developer/learner should DO after watching.
- topics: Key topics and technologies covered.
- architectureCode: A Markdown-formatted cloud architecture blueprint.
- ingestScript: A robust, modular Python script using Playwright for high-density ingestion.
- e22Snippets: 3-5 production-ready code snippets for E22 cloud solutions.

STRICT RULE: NO MOCK DATA. Only use what is found via search grounding.
- Use your googleSearch tool to find the ACTUAL content.
- The video creator often provides detailed descriptions with chapter breakdowns.
  USE that metadata — it is high-quality structured content.
- If a spoken transcript is not available, reconstruct content from the description,
  chapters, comments, and related articles found via search.
- Be thorough — capture every key point, technical detail, and actionable insight.`;
}

/**
 * Executes a deep agentic analysis of a YouTube video using Gemini + Google Search.
 * Uses gemini-3-pro-preview with responseSchema + googleSearch (PK=998 pattern).
 * This is a single API call that handles both transcription AND extraction.
 */
export async function analyzeVideoWithGemini(
  videoUrl: string,
): Promise<VideoAnalysisResult> {
  const ai = getGeminiClient();

  const systemInstruction = buildSystemInstruction(videoUrl);

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
}
