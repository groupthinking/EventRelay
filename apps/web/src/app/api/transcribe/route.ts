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
 * Every error response carries a stable machine-readable `code`. The JSON-parse
 * and catch-all branches also fix their `error` string, because those paths can
 * carry raw upstream provider text (account IDs, quota state, partial API keys)
 * — that text is logged server-side only.
 *
 * The `!result.success` branches keep `fetchTranscript`'s own message in `error`.
 * That is safe only because every one of those values is now a fixed,
 * app-authored literal. Two of them were not, and were removed at the source in
 * `transcription-service.ts` rather than masked here:
 *   - the caller-supplied `audioUrl`'s HTTP status, which made this route a
 *     cross-origin probe, and
 *   - a message that varied on whether provider API keys were configured, which
 *     disclosed server configuration.
 * Both are logged server-side instead. Keep that invariant when adding a
 * strategy: anything interpolated into a `fetchTranscript` error reaches the
 * client verbatim through the branches below.
 *   - 400: Invalid input (missing URL, malformed JSON) — `input_required` / `invalid_json`
 *   - 429: Rate limited (implement backoff or upgrade service plan) — `rate_limited`
 *   - 500: Service unavailable (check API keys and billing) — `billing_not_configured`
 *   - 503: Cascading failures (all fallback strategies exhausted) — `transcription_unavailable`
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
          code: 'input_required',
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
          { success: false, error: result.error, code: 'input_required', transcript: '' },
          { status: 400 }
        );
      } else if (result.error?.includes('rate limit')) {
        return NextResponse.json(
          {
            success: false,
            error: result.error,
            code: 'rate_limited',
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
            code: 'billing_not_configured',
            // No `details` here: the remediation text named this deployment's
            // cloud and model vendors, and the PR that sanitized this route
            // stated `details` was gone from it. `code` is what clients branch on.
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
          code: 'transcription_unavailable',
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
