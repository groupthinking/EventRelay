import { NextResponse } from 'next/server';
import { fetchTranscript } from '@/lib/transcription-service';
import { parseJsonSafely } from '@/lib/error-handling';

export const runtime = 'nodejs';
export const maxDuration = 120;

/**
 * POST /api/transcribe
 *
 * Multi-strategy transcript extraction with comprehensive error handling:
 *   1. YouTube captions via backend (fast + free) - with circuit breaker
 *   2. Gemini fallback + Google Search - with exponential backoff
 *   3. OpenAI Responses API with web search - with rate limit handling
 *   4. Direct audio STT via OpenAI Whisper
 *
 * The JSON-parse and catch-all branches return static, machine-readable payloads
 * (`code` + fixed `error`); raw upstream provider text is logged server-side only,
 * since it can carry account IDs and partial API keys. The `!result.success`
 * branches below return `fetchTranscript`'s own app-authored message verbatim —
 * these are not upstream text, and they carry no `code`:
 *   - 400: Invalid input (missing URL, malformed JSON)
 *   - 429: Rate limited (implement backoff or upgrade service plan)
 *   - 500: Service unavailable (check API keys and billing)
 *   - 503: Cascading failures (all fallback strategies exhausted)
 */
export async function POST(request: Request) {
  try {
    // Parse JSON with detailed error handling
    let body: Record<string, unknown>;
    try {
      body = await parseJsonSafely(request);
    } catch (parseError) {
      console.error('Transcription route JSON parse error:', parseError);
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid JSON in request body',
          code: 'invalid_json',
          transcript: '',
        },
        { status: 400 }
      );
    }

    // Validate required fields
    const { url, audioUrl, language = 'en' } = body;
    if (!url && !audioUrl) {
      return NextResponse.json(
        {
          success: false,
          error: 'Either url or audioUrl is required',
          accepted_fields: ['url', 'audioUrl', 'language'],
          transcript: '',
        },
        { status: 400 }
      );
    }

    // Fetch transcript with all fallback strategies
    const result = await fetchTranscript({
      url: url as string | undefined,
      audioUrl: audioUrl as string | undefined,
      language: language as string,
    });

    if (!result.success) {
      // Distinguish error severity for appropriate HTTP status
      if (result.error?.includes('url or audioUrl')) {
        return NextResponse.json(
          { success: false, error: result.error, transcript: '' },
          { status: 400 }
        );
      } else if (result.error?.includes('rate limit')) {
        return NextResponse.json(
          {
            success: false,
            error: result.error,
            retry_after: 60,
            transcript: '',
          },
          { status: 429 }
        );
      } else if (result.error?.includes('billing')) {
        return NextResponse.json(
          {
            success: false,
            error: result.error,
            details: 'Configure billing in Google Cloud and OpenAI console',
            transcript: '',
          },
          { status: 500 }
        );
      }

      // All strategies failed
      return NextResponse.json(
        {
          success: false,
          error: result.error || 'All transcription strategies failed',
          transcript: '',
        },
        { status: 503 }
      );
    }

    return NextResponse.json(result);
  } catch (error) {
    // Failures here can carry upstream provider text (OpenAI/Gemini/backend),
    // which may include account identifiers, quota state or partial API keys.
    // Log it server-side and return a fixed, static payload.
    console.error('Transcription route error:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Transcription failed',
        code: 'transcription_failed',
        transcript: '',
      },
      { status: 500 }
    );
  }
}
