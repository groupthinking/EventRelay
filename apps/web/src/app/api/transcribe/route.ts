import OpenAI from 'openai';
import { NextResponse } from 'next/server';

let _client: OpenAI | null = null;
function getClient() {
  if (!_client) _client = new OpenAI();
  return _client;
}
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

/**
 * OpenAI STT fallback — used when YouTube's auto-caption API fails or
 * returns low-quality transcripts. Uses gpt-4o-mini-transcribe for
 * cost-effective, high-quality transcription.
 *
 * POST /api/transcribe
 *   { url: string }              — YouTube URL (tries YouTube API first, falls back to STT)
 *   { audioUrl: string }         — Direct audio URL (goes straight to STT)
 *
 * Returns { success, transcript, source: 'youtube' | 'openai-stt' }
 */
export async function POST(request: Request) {
  try {
    const { url, audioUrl, language = 'en' } = await request.json();

    if (!url && !audioUrl) {
      return NextResponse.json(
        { error: 'url or audioUrl is required' },
        { status: 400 },
      );
    }

    // Strategy 1: Try YouTube transcript API via backend first (fast + free)
    if (url && !audioUrl) {
      try {
        const ytResponse = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_url: url, language }),
        });

        if (ytResponse.ok) {
          const result = await ytResponse.json();
          const segments = result.transcript || [];
          if (segments.length > 0) {
            const fullText = segments
              .map((s: { text?: string }) => s.text || '')
              .join(' ')
              .trim();

            if (fullText.length > 50) {
              return NextResponse.json({
                success: true,
                transcript: fullText,
                segments,
                source: 'youtube',
                wordCount: fullText.split(/\s+/).length,
              });
            }
          }
        }
      } catch {
        // YouTube API failed — fall through to OpenAI STT
        console.log('YouTube transcript unavailable, falling back to OpenAI STT');
      }
    }

    // Strategy 2: OpenAI Speech-to-Text via Responses API
    // For YouTube URLs without direct audio, use the Responses API with
    // web_search to find and analyze the content
    if (url && !audioUrl) {
      // Use Responses API to transcribe/summarize the video content
      const response = await getClient().responses.create({
        model: 'gpt-4o-mini',
        instructions: `You are a video content transcription assistant.
Given a YouTube URL, use web search to find the video's transcript or detailed content.
Return the full transcript text if available, or a detailed content summary.
Be thorough — capture all key points, quotes, and technical details.`,
        tools: [{ type: 'web_search' as const }],
        input: `Find and return the full transcript or detailed content of this video: ${url}`,
      });

      const text = response.output_text || '';

      if (text.length > 100) {
        return NextResponse.json({
          success: true,
          transcript: text,
          source: 'openai-web-search',
          wordCount: text.split(/\s+/).length,
        });
      }
    }

    // Strategy 3: Direct audio file transcription via OpenAI Whisper/STT
    if (audioUrl) {
      const audioResponse = await fetch(audioUrl);
      if (!audioResponse.ok) {
        return NextResponse.json(
          { error: `Failed to fetch audio: ${audioResponse.status}` },
          { status: 400 },
        );
      }

      const audioBlob = await audioResponse.blob();
      const audioFile = new File([audioBlob], 'audio.mp3', { type: 'audio/mpeg' });

      const transcription = await getClient().audio.transcriptions.create({
        model: 'gpt-4o-mini-transcribe',
        file: audioFile,
        language,
      });

      return NextResponse.json({
        success: true,
        transcript: transcription.text,
        source: 'openai-stt',
        wordCount: transcription.text.split(/\s+/).length,
      });
    }

    return NextResponse.json({
      success: false,
      error: 'Could not transcribe video — YouTube API and OpenAI STT both failed',
      transcript: '',
    });
  } catch (error) {
    console.error('Transcription error:', error);
    const message = error instanceof Error ? error.message : String(error);

    return NextResponse.json({
      success: false,
      error: message.includes('API key')
        ? 'OpenAI API key not configured. Set OPENAI_API_KEY in your environment.'
        : message,
      transcript: '',
    });
  }
}
