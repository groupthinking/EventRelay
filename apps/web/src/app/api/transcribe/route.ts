import { NextResponse } from 'next/server';
import { fetchTranscript } from '@/lib/transcription-service';
import { parseJsonSafely } from '@/lib/error-handling';

export const runtime = 'nodejs';
export const maxDuration = 120;

/**
 * POST /api/transcribe — parse JSON, then `fetchTranscript`.
 * 400 `input_required` / `invalid_json`, 429 `rate_limited`,
 * 500 `billing_not_configured` or `transcription_failed`,
 * 503 `transcription_unavailable`.
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
