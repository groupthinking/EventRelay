"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.analyzeVideoWithGemini = analyzeVideoWithGemini;
const genai_1 = require("@google/genai");
const gemini_client_1 = require("./gemini-client");
/**
 * Gemini response schema using the @google/genai Type system.
 * Matches the UVAI PK=998 structured output requirements exactly.
 */
const responseSchema = {
    type: genai_1.Type.OBJECT,
    properties: {
        title: { type: genai_1.Type.STRING },
        summary: { type: genai_1.Type.STRING },
        transcript: {
            type: genai_1.Type.ARRAY,
            items: {
                type: genai_1.Type.OBJECT,
                properties: {
                    start: { type: genai_1.Type.NUMBER, description: 'Seconds from video start' },
                    duration: { type: genai_1.Type.NUMBER },
                    text: { type: genai_1.Type.STRING },
                },
                required: ['start', 'duration', 'text'],
            },
        },
        events: {
            type: genai_1.Type.ARRAY,
            items: {
                type: genai_1.Type.OBJECT,
                properties: {
                    timestamp: { type: genai_1.Type.NUMBER },
                    label: { type: genai_1.Type.STRING },
                    description: { type: genai_1.Type.STRING },
                    codeMapping: {
                        type: genai_1.Type.STRING,
                        description: 'One-line code implementation of the action',
                    },
                    cloudService: { type: genai_1.Type.STRING },
                },
                required: ['timestamp', 'label', 'description', 'codeMapping', 'cloudService'],
            },
        },
        actions: {
            type: genai_1.Type.ARRAY,
            items: {
                type: genai_1.Type.OBJECT,
                properties: {
                    title: { type: genai_1.Type.STRING },
                    description: { type: genai_1.Type.STRING },
                    category: {
                        type: genai_1.Type.STRING,
                        enum: ['setup', 'build', 'deploy', 'learn', 'research', 'configure'],
                    },
                    estimatedMinutes: { type: genai_1.Type.NUMBER, nullable: true },
                },
                required: ['title', 'description', 'category'],
            },
        },
        topics: { type: genai_1.Type.ARRAY, items: { type: genai_1.Type.STRING } },
        architectureCode: { type: genai_1.Type.STRING },
        ingestScript: { type: genai_1.Type.STRING },
        e22Snippets: {
            type: genai_1.Type.ARRAY,
            items: {
                type: genai_1.Type.OBJECT,
                properties: {
                    title: { type: genai_1.Type.STRING },
                    description: { type: genai_1.Type.STRING },
                    code: { type: genai_1.Type.STRING },
                    language: { type: genai_1.Type.STRING },
                },
                required: ['title', 'description', 'code', 'language'],
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
    ],
};
/**
 * Build the agentic system instruction for the Gemini model.
 * Implements the Think → Act → Observe → Map loop from PK=998.
 */
function buildSystemInstruction(videoUrl) {
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
async function analyzeVideoWithGemini(videoUrl) {
    const ai = (0, gemini_client_1.getGeminiClient)();
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
    return JSON.parse(resultText);
}
//# sourceMappingURL=gemini-video-analyzer.js.map