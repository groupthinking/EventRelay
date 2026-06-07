import { NextResponse } from 'next/server';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

export async function POST(request: Request) {
  try {
    if (!BACKEND_AVAILABLE) {
      return NextResponse.json(
        { answer: 'Chat requires a backend connection. Configure BACKEND_URL to enable the AI assistant.' },
        { status: 503 }
      );
    }

    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(process.env.EVENTRELAY_API_KEY ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY } : {}) },
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
  } catch (error) {
    console.error('Chat proxy error:', error);
    return NextResponse.json(
      { answer: 'Failed to connect to the AI assistant. Please ensure the backend is running.' },
      { status: 502 }
    );
  }
}
