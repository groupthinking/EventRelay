import 'server-only';

import OpenAI from 'openai';
import { Type } from '@google/genai';
import { getGeminiClient, hasGeminiKey } from '@/lib/gemini-client';
import { GEMINI_SEARCH_MODEL, GEMINI_STRUCTURED_MODEL } from '@/lib/gemini-models';
import {
  gatewayChat,
  hasAiGatewayKey,
  stripJsonCodeFence,
  toGatewayModelId,
} from '@/lib/vercel-ai-gateway';

let _openai: OpenAI | null = null;
function getOpenAI() {
  if (!_openai) _openai = new OpenAI();
  return _openai;
}

// JSON Schema for structured extraction via OpenAI Responses API
const extractionSchema = {
  type: 'object' as const,
  properties: {
    events: {
      type: 'array' as const,
      items: {
        type: 'object' as const,
        properties: {
          type: { type: 'string' as const, enum: ['action', 'topic', 'insight', 'tool', 'resource'] },
          title: { type: 'string' as const, description: 'Short descriptive title' },
          description: { type: 'string' as const, description: 'One-sentence explanation' },
          timestamp: { type: ['string', 'null'] as const, description: 'Time in video if mentioned, e.g. "02:15", or null' },
          priority: { type: 'string' as const, enum: ['high', 'medium', 'low'] },
        },
        required: ['type', 'title', 'description', 'timestamp', 'priority'],
        additionalProperties: false,
      },
    },
    actions: {
      type: 'array' as const,
      items: {
        type: 'object' as const,
        properties: {
          title: { type: 'string' as const },
          description: { type: 'string' as const },
          category: { type: 'string' as const, enum: ['setup', 'build', 'deploy', 'learn', 'research', 'configure'] },
          estimatedMinutes: { type: ['number', 'null'] as const },
        },
        required: ['title', 'description', 'category', 'estimatedMinutes'],
        additionalProperties: false,
      },
    },
    summary: { type: 'string' as const, description: '2-3 sentence summary of the content' },
    topics: { type: 'array' as const, items: { type: 'string' as const }, description: 'Key topics covered' },
  },
  required: ['events', 'actions', 'summary', 'topics'],
  additionalProperties: false,
};

// Gemini responseSchema using @google/genai Type system
const geminiResponseSchema = {
  type: Type.OBJECT,
  properties: {
    events: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          type: { type: Type.STRING, enum: ['action', 'topic', 'insight', 'tool', 'resource'] },
          title: { type: Type.STRING },
          description: { type: Type.STRING },
          timestamp: { type: Type.STRING, nullable: true },
          priority: { type: Type.STRING, enum: ['high', 'medium', 'low'] },
        },
        required: ['type', 'title', 'description', 'timestamp', 'priority'],
      },
    },
    actions: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          title: { type: Type.STRING },
          description: { type: Type.STRING },
          category: { type: Type.STRING, enum: ['setup', 'build', 'deploy', 'learn', 'research', 'configure'] },
          estimatedMinutes: { type: Type.NUMBER, nullable: true },
        },
        required: ['title', 'description', 'category', 'estimatedMinutes'],
      },
    },
    summary: { type: Type.STRING },
    topics: { type: Type.ARRAY, items: { type: Type.STRING } },
  },
  required: ['events', 'actions', 'summary', 'topics'],
};

const SYSTEM_PROMPT = `You are an expert content analyst. Extract structured data from video transcripts.
Be specific and practical — no vague or generic items.
For events: classify type (action/topic/insight/tool/resource) and priority (high/medium/low).
For actions: generate concrete tasks a developer/learner should DO after watching.`;

function buildUserPrompt(trimmed: string, videoTitle?: string, videoUrl?: string) {
  return `Analyze this video transcript and extract structured data.

Video: ${videoTitle || videoUrl || 'Unknown'}

TRANSCRIPT:
${trimmed}

Respond with ONLY valid JSON matching this structure:
{
  "events": [{"type": "action|topic|insight|tool|resource", "title": "...", "description": "...", "timestamp": "02:15" or null, "priority": "high|medium|low"}],
  "actions": [{"title": "...", "description": "...", "category": "setup|build|deploy|learn|research|configure", "estimatedMinutes": number or null}],
  "summary": "2-3 sentence summary",
  "topics": ["topic1", "topic2"]
}`;
}

async function extractWithOpenAI(trimmed: string, videoTitle?: string, videoUrl?: string) {
  const response = await getOpenAI().responses.create({
    model: 'gpt-4o-mini',
    instructions: SYSTEM_PROMPT,
    input: buildUserPrompt(trimmed, videoTitle, videoUrl),
    text: {
      format: {
        type: 'json_schema',
        name: 'event_extraction',
        schema: extractionSchema,
        strict: true,
      },
    },
  });
  const text = response.output_text;
  if (!text) {
    throw new Error('OpenAI returned an empty response');
  }
  return JSON.parse(text);
}

async function extractWithGemini(trimmed: string, videoTitle?: string, videoUrl?: string) {
  const prompt = `${SYSTEM_PROMPT}\n\n${buildUserPrompt(trimmed, videoTitle, videoUrl)}`;

  if (hasAiGatewayKey()) {
    const result = await gatewayChat({
      model: toGatewayModelId(GEMINI_STRUCTURED_MODEL),
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        {
          role: 'user',
          content: `${buildUserPrompt(trimmed, videoTitle, videoUrl)}\n\nReturn ONLY valid JSON.`,
        },
      ],
      max_tokens: 4096,
      temperature: 0.3,
    });
    return JSON.parse(stripJsonCodeFence(result.content));
  }

  const ai = getGeminiClient();
  const response = await ai.models.generateContent({
    model: GEMINI_STRUCTURED_MODEL,
    contents: prompt,
    config: {
      temperature: 0.3,
      responseMimeType: 'application/json',
      responseSchema: geminiResponseSchema,
    },
  });
  const text = response.text ?? '';
  if (!text) {
    throw new Error('Gemini returned an empty response');
  }
  return JSON.parse(text);
}

export interface ExtractionInput {
  transcript?: string;
  videoTitle?: string;
  videoUrl?: string;
}

export interface ExtractionData {
  events: Array<{
    type: string;
    title: string;
    description: string;
    timestamp: string | null;
    priority: string;
  }>;
  actions: Array<{
    title: string;
    description: string;
    category: string;
    estimatedMinutes: number | null;
  }>;
  summary: string;
  topics: string[];
}

export interface ExtractionResult {
  success: boolean;
  provider?: string;
  data: ExtractionData;
  error?: string;
}

/**
 * Core event extraction logic — runs entirely in-process, no internal HTTP calls.
 * Called by both /api/extract-events (route handler) and /api/video (inline fallback).
 */
export async function extractEvents({ transcript, videoTitle, videoUrl }: ExtractionInput): Promise<ExtractionResult> {
  const empty: ExtractionData = { events: [], actions: [], summary: '', topics: [] };

  let parsed: ExtractionData | undefined;
  let provider = 'openai';

  try {
    // Path 1: transcript text available → run structured extraction
    if (transcript && typeof transcript === 'string' && transcript.length > 50) {
      const trimmed = transcript.slice(0, 8000);

      if (process.env.OPENAI_API_KEY) {
        try {
          parsed = await extractWithOpenAI(trimmed, videoTitle, videoUrl);
        } catch (err) {
          // Fall back to Gemini for ANY OpenAI failure (rate limit, network,
          // empty/malformed output), not just quota — as long as a key exists.
          if (hasGeminiKey()) {
            console.warn('OpenAI extraction failed, falling back to Gemini:', err);
            parsed = await extractWithGemini(trimmed, videoTitle, videoUrl);
            provider = 'gemini';
          } else {
            throw err;
          }
        }
      } else if (hasGeminiKey()) {
        parsed = await extractWithGemini(trimmed, videoTitle, videoUrl);
        provider = 'gemini';
      }
    }

    // Path 2: no transcript but have videoUrl + Gemini → direct video analysis via Google Search
    if (!parsed && videoUrl && hasGeminiKey()) {
      const videoPrompt = `${SYSTEM_PROMPT}\n\nAnalyze this YouTube video and extract structured data.
Find the video's transcript, description, and chapter content.

Video URL: ${videoUrl}
${videoTitle ? `Video Title: ${videoTitle}` : ''}

Extract events, actions, summary, and topics from the actual video content.
Respond with ONLY valid JSON matching the required structure.`;

      if (hasAiGatewayKey()) {
        const result = await gatewayChat({
          model: toGatewayModelId(GEMINI_SEARCH_MODEL),
          messages: [{ role: 'user', content: videoPrompt }],
          max_tokens: 4096,
          temperature: 0.3,
        });
        parsed = JSON.parse(stripJsonCodeFence(result.content));
      } else {
        const ai = getGeminiClient();
        const response = await ai.models.generateContent({
          model: GEMINI_SEARCH_MODEL,
          contents: videoPrompt,
          config: {
            temperature: 0.3,
            responseMimeType: 'application/json',
            tools: [{ googleSearch: {} }],
          },
        });
        const text = response.text ?? '';
        if (!text) {
          throw new Error('Gemini returned an empty response');
        }
        parsed = JSON.parse(text);
      }
      provider = 'gemini-search';
    }
  } catch (err) {
    // Honor the ExtractionResult contract: never throw, always return a result.
    const message = err instanceof Error ? err.message : 'Unknown extraction error';
    console.error('Event extraction failed:', err);
    return { success: false, error: message, data: empty };
  }

  if (!parsed) {
    return {
      success: false,
      error: 'No AI API key configured or all extraction attempts failed. Set GEMINI_API_KEY.',
      data: empty,
    };
  }

  return { success: true, provider, data: parsed };
}
