import { openai } from '@ai-sdk/openai';
import { generateObject } from 'ai';
import { jsonSchema } from 'ai';
import { NextResponse } from 'next/server';

const ExtractionSchema = jsonSchema<{
  events: Array<{
    type: 'action' | 'topic' | 'insight' | 'tool' | 'resource';
    title: string;
    description: string;
    timestamp?: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  actions: Array<{
    title: string;
    description: string;
    category: 'setup' | 'build' | 'deploy' | 'learn' | 'research' | 'configure';
    estimatedMinutes?: number;
  }>;
  summary: string;
  topics: string[];
}>({
  type: 'object',
  properties: {
    events: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['action', 'topic', 'insight', 'tool', 'resource'] },
          title: { type: 'string', description: 'Short descriptive title' },
          description: { type: 'string', description: 'One-sentence explanation' },
          timestamp: { type: 'string', description: 'Time in video if mentioned, e.g. "02:15"' },
          priority: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['type', 'title', 'description', 'priority'],
      },
    },
    actions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          description: { type: 'string' },
          category: { type: 'string', enum: ['setup', 'build', 'deploy', 'learn', 'research', 'configure'] },
          estimatedMinutes: { type: 'number' },
        },
        required: ['title', 'description', 'category'],
      },
    },
    summary: { type: 'string', description: '2-3 sentence summary of the content' },
    topics: { type: 'array', items: { type: 'string' }, description: 'Key topics covered' },
  },
  required: ['events', 'actions', 'summary', 'topics'],
});

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

    const { object } = await generateObject({
      model: openai('gpt-4o-mini'),
      schema: ExtractionSchema,
      prompt: `Analyze this video transcript and extract structured data.

Video: ${videoTitle || videoUrl || 'Unknown'}

TRANSCRIPT:
${trimmed}

Instructions:
- Extract every actionable event, key topic, insight, tool mention, and resource reference.
- For each event, classify its type and priority.
- Generate concrete action items — things a developer/learner should DO after watching.
- Provide a concise summary and list of topics covered.
- Be specific and practical — no vague or generic items.`,
    });

    return NextResponse.json({ success: true, data: object });
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
