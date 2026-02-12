import OpenAI from 'openai';
import { NextResponse } from 'next/server';

let _client: OpenAI | null = null;
function getClient() {
  if (!_client) _client = new OpenAI();
  return _client;
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

    // Use OpenAI Responses API — better caching (40-80%), built-in tool loop
    const response = await getClient().responses.create({
      model: 'gpt-4o-mini',
      instructions: `You are an expert content analyst. Extract structured data from video transcripts.
Be specific and practical — no vague or generic items.
For events: classify type (action/topic/insight/tool/resource) and priority (high/medium/low).
For actions: generate concrete tasks a developer/learner should DO after watching.`,
      input: `Analyze this video transcript and extract structured data.

Video: ${videoTitle || videoUrl || 'Unknown'}

TRANSCRIPT:
${trimmed}`,
      text: {
        format: {
          type: 'json_schema',
          name: 'event_extraction',
          schema: extractionSchema,
          strict: true,
        },
      },
    });

    const parsed = JSON.parse(response.output_text);
    return NextResponse.json({ success: true, data: parsed });
  } catch (error) {
    console.error('Event extraction error:', error);
    const message = error instanceof Error ? error.message : String(error);

    return NextResponse.json({
      success: false,
      error: message.includes('API key') || message.includes('OPENAI_API_KEY')
        ? 'OpenAI API key not configured. Set OPENAI_API_KEY in your environment.'
        : message,
      data: { events: [], actions: [], summary: '', topics: [] },
    });
  }
}
