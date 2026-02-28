/**
 * Agentic Video Intelligence Engine — Gemini + Google Search grounding.
 *
 * Uses the googleSearch tool as the PRIMARY mechanism to retrieve real-time
 * transcripts, descriptions, chapters, and metadata from YouTube videos.
 * Based on the UVAI PK=998 implementation pattern.
 *
 * NOTE: Vertex AI does NOT support responseSchema (controlled generation)
 * combined with googleSearch tool. JSON structure is enforced via prompt.
 */

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
}

/**
 * Build the agentic system instruction for the Gemini model.
 * Implements the Think → Act → Observe → Map loop from PK=998.
 */
function buildSystemInstruction(videoUrl: string): string {
  return `You are the Agentic Video Intelligence Engine.

MISSION:
1. WATCH the video at ${videoUrl} by searching for its transcript, technical documentation,
   channel description, and chapter markers using your googleSearch tool.
2. THINK: Analyze the sequence of technical events described in the transcript and description.
   Pay special attention to chapter markers — they indicate the video creator's own breakdown
   of the content structure.
3. ACT: Reconstruct the timeline and generate actionable tasks that mirror the video content.
4. OBSERVE & MAP: Extract specific "Action Events" from the video and provide a direct
   code mapping for each.

IMPORTANT RULES:
- Use your googleSearch tool to find the ACTUAL content. Search for the video URL,
  the video title, and related terms.
- The video creator often provides detailed descriptions with chapter breakdowns.
  USE that metadata — it is high-quality structured content.
- If a spoken transcript is not available, reconstruct content from the description,
  chapters, comments, and related articles found via search.
- NO MOCK DATA. Only use what is found via search grounding.
- Be thorough — capture every key point, technical detail, and actionable insight.

You MUST respond with ONLY valid JSON (no markdown fences, no extra text) matching this exact structure:
{
  "title": "Accurate video title",
  "summary": "2-3 sentence technical executive summary",
  "transcript": [
    {"start": 0, "duration": 60, "text": "segment text covering 30-120 seconds each"}
  ],
  "events": [
    {"timestamp": 0, "label": "Event Name", "description": "What happened", "codeMapping": "one-line code", "cloudService": "relevant service"}
  ],
  "actions": [
    {"title": "Task title", "description": "What to do", "category": "setup|build|deploy|learn|research|configure", "estimatedMinutes": 15}
  ],
  "topics": ["topic1", "topic2"],
  "architectureCode": "markdown architecture overview or empty string",
  "ingestScript": "Python script or empty string"
}`;
}

/**
 * Executes a deep agentic analysis of a YouTube video using Gemini + Google Search.
 * This is a single API call that handles both transcription AND extraction.
 */
export async function analyzeVideoWithGemini(
  videoUrl: string,
): Promise<VideoAnalysisResult> {
  const ai = getGeminiClient();

  const systemInstruction = buildSystemInstruction(videoUrl);

  const response = await ai.models.generateContent({
    model: 'gemini-2.5-flash',
    contents: `Perform Agentic Grounding for Video: ${videoUrl}`,
    config: {
      systemInstruction,
      tools: [{ googleSearch: {} }],
      temperature: 0.3,
    },
  });

  const resultText = (response.text || '').trim();
  // Strip markdown code fences if present
  const cleaned = resultText.replace(/^```(?:json)?\s*\n?/i, '').replace(/\n?```\s*$/i, '');
  return JSON.parse(cleaned) as VideoAnalysisResult;
}
