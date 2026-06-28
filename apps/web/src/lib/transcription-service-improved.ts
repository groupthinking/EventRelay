import 'server-only';

import OpenAI from 'openai';
import { fetchYouTubeMetadata, formatMetadataAsContext } from '@/lib/youtube-metadata';
import { getGeminiClient, hasGeminiKey } from '@/lib/gemini-client';
import { assertPublicHttpUrl } from '@/lib/ssrf-guard';
import { CircuitBreaker, retryWithBackoff, withTimeout } from '@/lib/error-handling';

let _openai: OpenAI | null = null;
function getOpenAI() {
  if (!_openai) _openai = new OpenAI();
  return _openai;
}

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

// Circuit breakers for external services
const backendCircuitBreaker = new CircuitBreaker(3, 60_000);
const geminiCircuitBreaker = new CircuitBreaker(5, 120_000);
const openaiCircuitBreaker = new CircuitBreaker(5, 120_000);

export interface TranscriptionOptions {
  url?: string;
  audioUrl?: string;
  language?: string;
}

export interface TranscriptionResult {
  success: boolean;
  transcript: string;
  segments?: any[];
  source?: string;
  wordCount?: number;
  metadata?: any;
  error?: string;
}

/**
 * Fetches transcript using multi-strategy fallback with improved error handling:
 * 1. Python backend (YouTube captions API) - with circuit breaker
 * 2. Gemini + Google Search Grounding - with exponential backoff
 * 3. OpenAI + Web Search - with rate limit handling
 * 4. Direct audio STT via OpenAI Whisper
 */
export async function fetchTranscript({
  url,
  audioUrl,
  language = 'en',
}: TranscriptionOptions): Promise<TranscriptionResult> {
  if (!url && !audioUrl) {
    return { success: false, error: 'url or audioUrl is required', transcript: '' };
  }

  // Strategy 1: Try YouTube transcript API via backend (fast + free)
  if (url && !audioUrl && BACKEND_AVAILABLE) {
    try {
      const result = await backendCircuitBreaker.execute(
        async () => {
          return await retryWithBackoff(
            async () => {
              const controller = new AbortController();
              const response = await withTimeout(
                fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    ...(process.env.EVENTRELAY_API_KEY
                      ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY }
                      : {}),
                  },
                  body: JSON.stringify({ video_url: url, language }),
                  signal: controller.signal,
                }),
                8_000,
                'Backend transcript request timeout'
              );

              if (!response.ok) {
                throw new Error(`Backend returned ${response.status}`);
              }

              return await response.json();
            },
            2, // 2 attempts max for backend
            1000
          );
        }
      );

      // Handle transcript as segments array
      const segments = Array.isArray(result.transcript) ? result.transcript : [];
      if (segments.length > 0) {
        const fullText = segments
          .map((s: { text?: string }) => s.text || '')
          .join(' ')
          .trim();

        if (fullText.length > 50) {
          return {
            success: true,
            transcript: fullText,
            segments,
            source: 'youtube',
            wordCount: fullText.split(/\s+/).length,
          };
        }
      }

      // Handle transcript as { text: string }
      const transcriptText =
        typeof result.transcript === 'string'
          ? result.transcript
          : result.transcript?.text;
      if (typeof transcriptText === 'string' && transcriptText.length > 50) {
        return {
          success: true,
          transcript: transcriptText,
          source: 'youtube',
          wordCount: transcriptText.split(/\s+/).length,
        };
      }
    } catch (error) {
      console.warn(
        'Backend transcript unavailable:',
        error instanceof Error ? error.message : String(error)
      );
      // Continue to fallback strategies
    }
  }

  // Fetch YouTube metadata (description, chapters, title)
  let metadata: Awaited<ReturnType<typeof fetchYouTubeMetadata>> = null;
  if (url) {
    try {
      metadata = await withTimeout(
        fetchYouTubeMetadata(url),
        5_000,
        'YouTube metadata fetch timeout'
      );
    } catch (error) {
      console.warn(
        'YouTube metadata fetch failed:',
        error instanceof Error ? error.message : String(error)
      );
      // Continue without metadata
    }
  }

  // Strategy 2: Gemini with Google Search grounding
  if (url && !audioUrl && hasGeminiKey()) {
    try {
      const result = await geminiCircuitBreaker.execute(
        async () => {
          return await retryWithBackoff(
            async () => {
              const ai = getGeminiClient();
              const metadataContext = metadata ? formatMetadataAsContext(metadata) : '';

              const result = await withTimeout(
                ai.models.generateContent({
                  model: 'gemini-3.1-pro-preview',
                  contents: `You are a video transcription assistant with access to Google Search.

For the following YouTube video, use your googleSearch tool to find the ACTUAL transcript,
description, and chapter content. The video creator often provides detailed descriptions
with chapter breakdowns — USE that metadata as high-quality structured content.

${metadataContext ? `KNOWN VIDEO METADATA:\n${metadataContext}\n` : ''}
Video URL: ${url}

INSTRUCTIONS:
1. Search for the video's transcript using Google Search.
2. If a spoken transcript is available, return it verbatim.
3. If not, reconstruct detailed content from the description, chapters, comments,
   and related articles found via search.
4. Be thorough — capture ALL key points, technical details, quotes, and actionable insights.
5. Include timestamps in [MM:SS] format where possible.
6. Do NOT return generic advice like "click Show Transcript" — return actual content.`,
                  config: {
                    temperature: 0.2,
                    tools: [{ googleSearch: {} }],
                  },
                }),
                30_000,
                'Gemini transcription timeout'
              );

              return result;
            },
            2, // 2 attempts max
            2000 // 2s base delay
          );
        }
      );

      const text = result.text ?? '';
      if (text.length > 100) {
        return {
          success: true,
          transcript: text,
          source: 'gemini-search',
          wordCount: text.split(/\s+/).length,
          metadata,
        };
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.warn('Gemini transcription failed:', errorMsg);

      // Handle specific errors
      if (errorMsg.includes('BILLING_DISABLED')) {
        console.error('Google Cloud billing disabled for Vertex AI - configure billing to use Gemini');
      } else if (errorMsg.includes('429') || errorMsg.includes('RESOURCE_EXHAUSTED')) {
        console.warn('Gemini rate limited, waiting before next attempt');
      }
    }
  }

  // Strategy 3: OpenAI with web search (Responses API)
  if (url && !audioUrl) {
    try {
      const result = await openaiCircuitBreaker.execute(
        async () => {
          return await retryWithBackoff(
            async () => {
              const openai = getOpenAI();

              const response = await withTimeout(
                openai.responses.create({
                  model: 'gpt-4o',
                  instructions: `You are a video content transcription assistant.
Given a YouTube URL, use web search to find the video's ACTUAL transcript or detailed content.
Return the full transcript text if available. If not, provide a comprehensive content summary
based on the video's description, chapters, and any available reviews or summaries.
Do NOT return instructions on how to find a transcript — return the actual content.
Be thorough — capture all key points, quotes, technical details, and chapter breakdowns.`,
                  tools: [{ type: 'web_search' as const }],
                  input: `Find and return the full transcript or detailed content of this video: ${url}`,
                }),
                30_000,
                'OpenAI transcription timeout'
              );

              return response;
            },
            2,
            3000
          );
        }
      );

      const text = result.output_text || '';
      if (text && text.length > 100) {
        return {
          success: true,
          transcript: text,
          source: 'openai-search',
          wordCount: text.split(/\s+/).length,
        };
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.warn('OpenAI transcription failed:', errorMsg);

      if (errorMsg.includes('429')) {
        console.warn('OpenAI rate limited - implement backoff or upgrade plan');
      }
    }
  }

  // Strategy 4: Direct audio STT via OpenAI Whisper
  if (audioUrl) {
    try {
      const result = await openaiCircuitBreaker.execute(
        async () => {
          return await retryWithBackoff(
            async () => {
              const openai = getOpenAI();
              const audioBuffer = await withTimeout(
                fetch(audioUrl).then(r => r.arrayBuffer()),
                30_000,
                'Audio download timeout'
              );

              const file = new File(
                [audioBuffer],
                'audio.mp3',
                { type: 'audio/mpeg' }
              );

              return await withTimeout(
                openai.audio.transcriptions.create({
                  file,
                  model: 'whisper-1',
                  language,
                } as any),
                60_000,
                'Whisper transcription timeout'
              );
            },
            1,
            0
          );
        }
      );

      if (result.text && result.text.length > 50) {
        return {
          success: true,
          transcript: result.text,
          source: 'whisper',
          wordCount: result.text.split(/\s+/).length,
        };
      }
    } catch (error) {
      console.error('Whisper transcription failed:', error);
    }
  }

  return {
    success: false,
    error:
      'All transcription strategies failed. Verify backend availability, Google/OpenAI API keys, and billing.',
    transcript: '',
  };
}
