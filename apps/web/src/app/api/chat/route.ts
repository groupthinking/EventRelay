import { NextResponse } from 'next/server';
import { generateText } from 'ai';
import { aiGateway, GATEWAY_CHAT_MODEL } from '@/lib/ai-gateway';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Primary path: proxy to backend agent orchestration. This preserves the
    // existing production behaviour and must not be regressed.
    if (BACKEND_AVAILABLE) {
      const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.EVENTRELAY_API_KEY ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY } : {}),
        },
        body: JSON.stringify({
          message: body.query,
          video_url: body.video_url || '',
          video_id: body.video_id || '',
          conversation_history: body.history || [],
        }),
        signal: AbortSignal.timeout(30_000),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Chat API error:', response.status, errorText);
        return NextResponse.json(
          { answer: 'The AI assistant is temporarily unavailable. Please try again.' },
          { status: response.status }
        );
      }

      const data = await response.json();
      return NextResponse.json({
        answer: data.response || data.answer || data.message || 'No response generated.',
      });
    }

    // Fallback path: AI Gateway when no backend is configured. Only activates
    // when BACKEND_URL is unset AND AI_GATEWAY_API_KEY is present, so the
    // existing 503 behaviour is preserved when neither is configured.
    if (!process.env.AI_GATEWAY_API_KEY) {
      return NextResponse.json(
        { answer: 'Chat requires either a BACKEND_URL or an AI_GATEWAY_API_KEY to be configured.' },
        { status: 503 }
      );
    }

    const history: Array<{ role: 'user' | 'assistant'; content: string }> = Array.isArray(body.history)
      ? body.history
      : [];

    const systemPrompt = body.video_url
      ? `You are a helpful AI assistant specializing in video content analysis. The user is asking about this video: ${body.video_url}`
      : 'You are a helpful AI assistant.';

    const messages: Array<{ role: 'user' | 'assistant'; content: string }> = [
      ...history,
      { role: 'user', content: body.query || body.message || '' },
    ];

    const { text } = await generateText({
      model: aiGateway(GATEWAY_CHAT_MODEL),
      system: systemPrompt,
      messages,
    });

    return NextResponse.json({ answer: text });
  } catch (error) {
    console.error('Chat proxy error:', error);
    return NextResponse.json(
      { answer: 'Failed to connect to the AI assistant. Please ensure BACKEND_URL or AI_GATEWAY_API_KEY is configured.' },
      { status: 502 }
    );
  }
}
