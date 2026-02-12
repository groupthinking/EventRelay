import OpenAI from 'openai';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { NextResponse } from 'next/server';

let _openai: OpenAI | null = null;
function getOpenAI() {
  if (!_openai) _openai = new OpenAI();
  return _openai;
}

let _gemini: GoogleGenerativeAI | null = null;
function getGemini() {
  if (!_gemini) _gemini = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || '');
  return _gemini;
}

// JSON Schema for structured extraction via Responses API
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
  const model = getGemini().getGenerativeModel({
    model: 'gemini-2.0-flash',
    generationConfig: {
      responseMimeType: 'application/json',
      temperature: 0.3,
    },
  });
  const result = await model.generateContent(`${SYSTEM_PROMPT}\n\n${buildUserPrompt(trimmed, videoTitle, videoUrl)}`);
  const text = result.response.text();
  return JSON.parse(text);
}

export async function POST(request: Request) {
  try {
    const { transcript, videoTitle, videoUrl } = await request.json();

    if (!transcript || typeof transcript !== 'string') {
      return NextResponse.json(
        { error: 'transcript (string) is required' },
        { status: 400 }
      );
    }

    const trimmed = transcript.slice(0, 8000);
    let parsed;
    let provider = 'openai';

    // Try OpenAI first, fall back to Gemini on quota/auth errors
    if (process.env.OPENAI_API_KEY) {
      try {
        parsed = await extractWithOpenAI(trimmed, videoTitle, videoUrl);
      } catch (err) {
        const msg = err instanceof Error ? err.message : '';
        if ((msg.includes('429') || msg.includes('quota') || msg.includes('rate')) && process.env.GEMINI_API_KEY) {
          console.warn('OpenAI quota hit, falling back to Gemini');
          parsed = await extractWithGemini(trimmed, videoTitle, videoUrl);
          provider = 'gemini';
        } else {
          throw err;
        }
      }
    } else if (process.env.GEMINI_API_KEY) {
      parsed = await extractWithGemini(trimmed, videoTitle, videoUrl);
      provider = 'gemini';
    } else {
      return NextResponse.json({
        success: false,
        error: 'No AI API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY.',
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
