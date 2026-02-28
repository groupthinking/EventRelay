import OpenAI from 'openai';
import { Type } from '@google/genai';
import { NextResponse } from 'next/server';
import { getGeminiClient, hasGeminiKey } from '@/lib/gemini-client';

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
        required: ['type', 'title', 'description', 'priority'],
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
        required: ['title', 'description', 'category'],
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
  return JSON.parse(response.output_text);
}

async function extractWithGemini(trimmed: string, videoTitle?: string, videoUrl?: string) {
  const ai = getGeminiClient();
  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: `${SYSTEM_PROMPT}\n\n${buildUserPrompt(trimmed, videoTitle, videoUrl)}`,
    config: {
      temperature: 0.3,
      responseMimeType: 'application/json',
      responseSchema: geminiResponseSchema,
      tools: [{ googleSearch: {} }],
    },
  });
  const text = response.text ?? '';
  return JSON.parse(text);
}

export async function POST(request: Request) {
  try {
    const { transcript, videoTitle, videoUrl } = await request.json();

    // Accept either transcript text OR videoUrl for direct Gemini analysis
    if ((!transcript || typeof transcript !== 'string') && !videoUrl) {
      return NextResponse.json(
        { error: 'transcript (string) or videoUrl is required' },
        { status: 400 }
      );
    }

    let parsed;
    let provider = 'openai';

    // If we have transcript text, use the existing extraction logic
    if (transcript && typeof transcript === 'string' && transcript.length > 50) {
      const trimmed = transcript.slice(0, 8000);

      if (process.env.OPENAI_API_KEY) {
        try {
          parsed = await extractWithOpenAI(trimmed, videoTitle, videoUrl);
        } catch (err) {
          const msg = err instanceof Error ? err.message : '';
          if ((msg.includes('429') || msg.includes('quota') || msg.includes('rate')) && hasGeminiKey()) {
            console.warn('OpenAI quota hit, falling back to Gemini');
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

    // If no transcript but have videoUrl + Gemini, do direct video analysis via Google Search
    if (!parsed && videoUrl && hasGeminiKey()) {
      try {
        const ai = getGeminiClient();
        const response = await ai.models.generateContent({
          model: 'gemini-3-pro-preview',
          contents: `${SYSTEM_PROMPT}\n\nAnalyze this YouTube video and extract structured data.
Use your Google Search tool to find the video's transcript, description, and chapter content.

Video URL: ${videoUrl}
${videoTitle ? `Video Title: ${videoTitle}` : ''}

Extract events, actions, summary, and topics from the actual video content found via search.`,
          config: {
            temperature: 0.3,
            responseMimeType: 'application/json',
            responseSchema: geminiResponseSchema,
            tools: [{ googleSearch: {} }],
          },
        });
        const text = response.text ?? '';
        parsed = JSON.parse(text);
        provider = 'gemini-search';
      } catch (e) {
        console.warn('Gemini direct video extraction failed:', e);
      }
    }

    if (!parsed) {
      return NextResponse.json({
        success: false,
        error: 'No AI API key configured or all extraction attempts failed. Set GEMINI_API_KEY.',
        data: { events: [], actions: [], summary: '', topics: [] },
      });
    }

    return NextResponse.json({ success: true, provider, data: parsed });
  } catch (error) {
    console.error('Event extraction error:', error);
    const message = error instanceof Error ? error.message : String(error);

    return NextResponse.json({
      success: false,
      error: message,
      data: { events: [], actions: [], summary: '', topics: [] },
    });
  }
}
