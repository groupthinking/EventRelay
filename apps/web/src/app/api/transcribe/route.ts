import { NextResponse } from 'next/server';
import { fetchTranscript } from '@/lib/transcription-service';

/**
 * POST /api/transcribe
 *
 * Multi-strategy transcript extraction (now powers both this endpoint and the Video Intelligence pipeline):
 *   1. YouTube captions via backend (fast + free)
 *   2. Gemini fallback + Google Search
 *   3. OpenAI Responses API with web_search
 *   4. Direct audio STT via OpenAI Whisper
 */
export async function POST(request: Request) {
  try {
    const { url, audioUrl, language = 'en' } = await request.json();

    const result = await fetchTranscript({ url, audioUrl, language });

    if (!result.success) {
      return NextResponse.json(
        { success: false, error: result.error, transcript: '' },
        { status: result.error?.includes('url or audioUrl') ? 400 : 500 },
      );
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error('Transcription route error:', error);
    const message = error instanceof Error ? error.message : String(error);

    return NextResponse.json({
      success: false,
      error: message.includes('API key')
        ? 'AI API key not configured. Set OPENAI_API_KEY or GEMINI_API_KEY.'
        : message,
      transcript: '',
    }, { status: 500 });
  }
}
