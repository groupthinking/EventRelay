/**
 * Agentic Video Intelligence Engine — Gemini + Google Search grounding.
 *
 * Uses the googleSearch tool as the PRIMARY mechanism to retrieve real-time
 * transcripts, descriptions, chapters, and metadata from YouTube videos.
 * Based on the UVAI PK=998 implementation pattern.
 */

import { GoogleGenAI, Type } from '@google/genai';

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
}

/**
 * Gemini response schema using the @google/genai Type system.
 * Matches the UVAI structured output requirements.
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
  ] as const,
};

/**
 * Build the agentic system instruction for the Gemini model.
 * Implements the Think → Act → Observe → Map loop from PK=998.
 */
function buildSystemInstruction(videoUrl: string): string {
  return `
You are the Agentic Video Intelligence Engine.

MISSION:
1. WATCH the video at ${videoUrl} by searching for its transcript, technical documentation,
   channel description, and chapter markers using your googleSearch tool.
2. THINK: Analyze the sequence of technical events described in the transcript and description.
   Pay special attention to chapter markers — they indicate the video creator's own breakdown
   of the content structure.
3. ACT: Reconstruct the timeline and generate actionable tasks that mirror the video content.
4. OBSERVE & MAP: Extract specific "Action Events" from the video and provide a direct
   code mapping for each.

DATA STRUCTURE REQUIREMENTS:
- title: Accurate video title from search results.
- summary: A high-level technical executive summary (2-3 sentences).
- transcript: An array of {start, duration, text} reconstructed from grounding.
  Use chapter timestamps and description content if a full transcript is unavailable.
  Each entry should cover a meaningful segment (30-120 seconds).
- events: 3-8 key technical milestones with timestamp, label, description, and codeMapping.
- actions: 3-8 concrete tasks a developer/learner should DO after watching.
- topics: Key topics and technologies covered.
- architectureCode: A markdown-formatted architecture overview if technical content is discussed,
  or empty string if not applicable.
- ingestScript: A Python script that processes or replicates the video's key workflow,
  or empty string if not applicable.

IMPORTANT RULES:
- Use your googleSearch tool to find the ACTUAL content. Search for the video URL,
  the video title, and related terms.
- The video creator often provides detailed descriptions with chapter breakdowns.
  USE that metadata — it is high-quality structured content.
- If a spoken transcript is not available, reconstruct content from the description,
  chapters, comments, and related articles found via search.
- NO MOCK DATA. Only use what is found via search grounding.
- Be thorough — capture every key point, technical detail, and actionable insight.
`;
}

/**
 * Executes a deep agentic analysis of a YouTube video using Gemini + Google Search.
 * This is a single API call that handles both transcription AND extraction.
 */
export async function analyzeVideoWithGemini(
  videoUrl: string,
  apiKey: string,
): Promise<VideoAnalysisResult> {
  const ai = new GoogleGenAI({ apiKey });

  const systemInstruction = buildSystemInstruction(videoUrl);

  const response = await ai.models.generateContent({
    model: 'gemini-2.5-flash',
    contents: `Perform Agentic Grounding for Video: ${videoUrl}`,
    config: {
      systemInstruction,
      responseMimeType: 'application/json',
      responseSchema,
      tools: [{ googleSearch: {} }],
      temperature: 0.3,
    },
  });

  const resultText = response.text || '{}';
  return JSON.parse(resultText) as VideoAnalysisResult;
}
