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

// Backend URL with validation - skip if not a valid URL
const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

/**
 * POST /api/transcribe
 *
 * Multi-strategy transcript extraction:
 *   1. YouTube captions via backend (fast + free)
 *   2. OpenAI Responses API with web_search (finds transcripts online)
 *   3. Gemini fallback (if OpenAI unavailable)
 *   4. Direct audio STT via OpenAI Whisper
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

    // Strategy 1: Try YouTube transcript API via backend (fast + free)
    if (url && !audioUrl && BACKEND_AVAILABLE) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8_000);

        const ytResponse = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_url: url, language }),
          signal: controller.signal,
        }).finally(() => clearTimeout(timeout));

        if (ytResponse.ok) {
          const result = await ytResponse.json();

          // Handle transcript as segments array
          const segments = Array.isArray(result.transcript) ? result.transcript : [];
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

          // Handle transcript as { text: string }
          const transcriptText =
            typeof result.transcript === 'string'
              ? result.transcript
              : result.transcript?.text;
          if (typeof transcriptText === 'string' && transcriptText.length > 50) {
            return NextResponse.json({
              success: true,
              transcript: transcriptText,
              source: 'youtube',
              wordCount: transcriptText.split(/\s+/).length,
            });
          }
        }
      } catch {
        console.log('YouTube transcript unavailable, falling back to AI providers');
      }
    }

    // Strategy 2: OpenAI Responses API with web_search
    if (url && !audioUrl && process.env.OPENAI_API_KEY) {
      try {
        const response = await getOpenAI().responses.create({
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
      } catch (e) {
        console.warn('OpenAI web_search transcript failed:', e);
      }
    }

    // Strategy 3: Gemini fallback (when OpenAI unavailable)
    if (url && !audioUrl && process.env.GEMINI_API_KEY) {
      try {
        const model = getGemini().getGenerativeModel({
          model: 'gemini-2.0-flash',
          generationConfig: { temperature: 0.2 },
        });

        const result = await model.generateContent(
          `You are a video content transcription assistant. ` +
          `For the following YouTube video URL, provide a detailed transcript or content summary. ` +
          `Include all key points, technical details, quotes, and actionable insights. ` +
          `Be thorough and comprehensive.\n\nVideo URL: ${url}`
        );
        const text = result.response.text();

        if (text.length > 100) {
          return NextResponse.json({
            success: true,
            transcript: text,
            source: 'gemini',
            wordCount: text.split(/\s+/).length,
          });
        }
      } catch (e) {
        console.warn('Gemini transcript fallback failed:', e);
      }
    }

    // Strategy 4: Direct audio file transcription via OpenAI Whisper
    if (audioUrl && process.env.OPENAI_API_KEY) {
      const audioResponse = await fetch(audioUrl);
      if (!audioResponse.ok) {
        return NextResponse.json(
          { error: `Failed to fetch audio: ${audioResponse.status}` },
          { status: 400 },
        );
      }

      const audioBlob = await audioResponse.blob();
      const audioFile = new File([audioBlob], 'audio.mp3', { type: 'audio/mpeg' });

      const transcription = await getOpenAI().audio.transcriptions.create({
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

    // No strategy succeeded
    const hasKeys = !!(process.env.OPENAI_API_KEY || process.env.GEMINI_API_KEY);
    return NextResponse.json({
      success: false,
      error: hasKeys
        ? 'Could not transcribe video — all strategies failed'
        : 'No AI API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY in Vercel environment variables.',
      transcript: '',
    });
  } catch (error) {
    console.error('Transcription error:', error);
    const message = error instanceof Error ? error.message : String(error);

    return NextResponse.json({
      success: false,
      error: message.includes('API key')
        ? 'AI API key not configured. Set OPENAI_API_KEY or GEMINI_API_KEY.'
        : message,
      transcript: '',
    });
  }
}
